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

from uuid import UUID

from sqlalchemy import select

from selflearn.agents.base import AbstractAgent
from selflearn.agents.builtin import exercise_agent, review_agent
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.core.logging import get_logger
from selflearn.domain.level import Level
from selflearn.domain.map_node import MapNode
from selflearn.domain.review_result import ReviewResult
from selflearn.infra.db import get_session_factory
from selflearn.infra.repositories.exercise_repo import ExerciseRepository
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
            await self._emit_failed(trace_id, "internal_unhandled", repr(e))
            log.error("director.unhandled_exception", trace_id=trace_id, error=repr(e))
            raise AppError(ErrorCode.INTERNAL, "Director 处理失败", trace_id=trace_id) from e

    async def _run_inner(self, env: Envelope) -> Envelope:
        trace_id = env.trace_id
        skill = get_skill("skill.director.start")

        student_id_raw = env.payload["student_id"]
        student_id = UUID(student_id_raw) if isinstance(student_id_raw, str) else student_id_raw

        # 1. 选第一个 active 节点
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.DIRECTOR, status="running",
            payload={"action": "select_node", "student_id": str(student_id)},
        ))
        factory = get_session_factory()
        async with factory() as session:
            stmt = select(MapNode).where(
                MapNode.student_id == student_id, MapNode.status == "active"
            ).limit(1)
            node = (await session.execute(stmt)).scalars().first()
            if node is None:
                raise AppError(ErrorCode.INTERNAL, "无 active 节点，请先跑 plan.generate")
            # node 满足 Node Protocol（MapNode ORM 实体）
            node.kp  # type: ignore[attr-defined]  # noqa: B018  触发 lazy load；Stage 4 改 joined load

        # 2. 同步调 Exercise Agent
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.EXERCISE, status="running",
            payload={"node_id": str(node.node_id)},
        ))
        ex_dicts = await exercise_agent.run_sync(env, node)  # type: ignore[attr-defined]
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.EXERCISE, status="completed", payload={"count": len(ex_dicts)}
        ))

        # 3. 同步调 Review Agent
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.REVIEW, status="running"
        ))
        review = await review_agent.review(ex_dicts)  # type: ignore[attr-defined]
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
            _ = await ExerciseRepository(session).bulk_create(level_id, ex_dicts)

            session.add(ReviewResult(
                level_id=level_id, verdict=review.verdict,
                score=review.score, issues=review.issues,
            ))
            await session.commit()

        # 5. 推 completed
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.COMPLETED, status="completed",
            payload={"level_id": str(level_id), "exercises_count": len(ex_dicts)},
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
