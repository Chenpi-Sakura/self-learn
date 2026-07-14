"""DirectorAgent: 同步序列调 Exercise + Review，含 try/except 兜底（V1.1 修复）。

前置编排：
1. SELECT 第一个 active MapNode（无则抛 INTERNAL）
2. exercise_agent.run_sync(env, node)  —— 任何 AppError/Exception 都向上传递
3. review_agent.review(ex_dicts)       —— 同上
4. rejected 时抛 EXERCISE_INVALID
5. 单 session 内写 Level + Exercise 列表 + ReviewResult（用 ExerciseRepository.bulk_create）
6. 推 COMPLETED 进度，返回 Envelope
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from selflearn.agents.base import AbstractAgent
from selflearn.agents.builtin.exercise_agent import ExerciseAgent
from selflearn.agents.builtin.review_agent import ReviewAgent
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.core.logging import get_logger
from selflearn.domain.level import Level
from selflearn.domain.map_node import MapNode
from selflearn.domain.review_result import ReviewResult
from selflearn.infra.db import get_session_factory
from selflearn.infra.repositories.exercise_repo import ExerciseRepository
from selflearn.infra.repositories.level_repo import LevelRepository
from selflearn.infra.repositories.profile_repo import ProfileRepository
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.progress.stream import progress_publish
from selflearn.skills.library import get as get_skill


log = get_logger("director")


class DirectorAgent(AbstractAgent):
    """skill.director.start: 关卡推进 orchestrator（出题 → 评审 → 入库）。"""

    agent_id = "director-01"
    agent_type = "director"
    queue = "agent.director.work"

    async def run(self, env: Envelope) -> Envelope:
        """V1.1: 必须 try/except 包全部子调用，失败推 FAILED 后抛 AppError。"""
        trace_id = env.trace_id
        try:
            return await self._run_inner(env)
        except AppError:
            await self._emit_failed(trace_id, "agent_internal_error", "Director 处理失败")
            raise
        except Exception as e:  # noqa: BLE001
            import traceback
            log.error("director.unhandled_exception", trace_id=trace_id, error=repr(e), tb=traceback.format_exc())
            raise AppError(ErrorCode.INTERNAL, "Director 处理失败", trace_id=trace_id) from e

    async def _run_inner(self, env: Envelope) -> Envelope:
        trace_id = env.trace_id
        skill = get_skill("skill.director.start")

        student_id_raw = env.payload["student_id"]
        student_id: str = str(student_id_raw) if not isinstance(student_id_raw, str) else student_id_raw

        # 1. 选第一个 active 节点
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.DIRECTOR, status="running",
            payload={"action": "select_node", "student_id": str(student_id)},
        ))
        factory = get_session_factory()
        async with factory() as session:
            stmt = (
                select(MapNode)
                .where(MapNode.student_id == student_id, MapNode.status == "active")
                .options(joinedload(MapNode.kp))
                .limit(1)
            )
            log.info("director.query_node", student_id=student_id)
            node = (await session.execute(stmt)).scalars().first()
            log.info("director.node_selected", node_id=str(node.node_id) if node else None)
            if node is None:
                raise AppError(ErrorCode.INTERNAL, "无 active 节点，请先跑 plan.generate")
            # joinedload 已把 kp 一起拉出来；exercise_agent 后面访问 node.kp.title 不会 lazy-load 报错
            kp_title = node.kp.title
            log.info("director.kp_title", title=kp_title)

        # 2. 同步调 Exercise Agent（spec § 5.2 难度梯度先算）
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.EXERCISE, status="running",
            payload={"node_id": str(node.node_id)},
        ))
        # spec § 5.2: 难度梯度（基于最近 3 次关卡完成分数）
        async with factory() as session:
            recent = await LevelRepository(session).recent_scores(student_id, limit=3)
        difficulty = _compute_difficulty(recent)
        log.info("director.difficulty_chosen", difficulty=difficulty, recent=recent)
        ex_dicts = await ExerciseAgent().run_sync(env, str(node.node_id), kp_title, difficulty=difficulty)
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.EXERCISE, status="completed", payload={"count": len(ex_dicts)}
        ))

        # 3. 同步调 Review Agent
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.REVIEW, status="running"
        ))
        review = await ReviewAgent().review(ex_dicts)
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.REVIEW, status="completed",
            payload={"verdict": review.verdict, "issues_count": len(review.issues)},
        ))

        if review.verdict == "rejected":
            raise AppError(ErrorCode.EXERCISE_INVALID,
                           f"Review rejected: {len(review.issues)} issues")

        # 4. 写库（单 session 内 Level + ExerciseRepository + ReviewResult）
        async with factory() as session:
            level = Level(node_id=node.node_id, status="generated", form="exercise")
            session.add(level)
            await session.flush()
            level_id = level.level_id

            # ExerciseRepository commit 后 select 拿 PK 实体的 list
            ex_list = await ExerciseRepository(session).bulk_create(level_id, ex_dicts)

            session.add(ReviewResult(
                level_id=level_id, verdict=review.verdict,
                score=review.score, issues=review.issues,
            ))
            await session.commit()

        # 4.5 spec § 5.1: 关卡完成后根据 review.score 微调 kb / as + 写 snapshot
        score_ratio = review.score  # ReviewAgent 给的 0.0 - 1.0
        delta_kb = 0.05 if score_ratio >= 0.8 else (-0.03 if score_ratio < 0.5 else 0.0)
        delta_as = 0.02 if score_ratio >= 0.7 else -0.02
        async with factory() as session:
            await ProfileRepository(session).apply_delta(
                student_id, {"kb": delta_kb, "as": delta_as}
            )
            await session.commit()

        # 5. 推 completed（保留 level_id + exercises_count 兼容；追加 exercise_ids + score）
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.COMPLETED, status="completed",
            payload={
                "level_id": str(level_id),
                "exercise_ids": [str(ex.exercise_id) for ex in ex_list],
                "exercises_count": len(ex_dicts),
                "score": score_ratio,
            },
        ))

        return Envelope(
            action="skill.completed",
            sender=ActorRef(type="agent", id=self.agent_id),
            target=ActorRef(type="gateway", id=env.sender.id),
            payload={"level_id": str(level_id), "exercises_count": len(ex_dicts)},
            trace_id=trace_id,
            parent_id=env.span_id,
        )

    async def _emit_failed(self, trace_id: str, code: str, message: str) -> None:
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.FAILED, status="failed",
            payload={"code": code, "message": message},
        ))


def _compute_difficulty(recent_scores: list[float]) -> str:
    """spec § 5.2: 平均分 < 0.5 → easy；< 0.8 → medium；其余 → hard。无历史 → medium。"""
    if not recent_scores:
        return "medium"
    avg = sum(recent_scores) / len(recent_scores)
    if avg < 0.5:
        return "easy"
    if avg < 0.8:
        return "medium"
    return "hard"
