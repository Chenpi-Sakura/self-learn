"""SkillBasedScheduler（P5 简化版 + Task 18 routing fix + post-smoke fix）。

P5 架构：worker 启动时构造 LLMAgent + ReviewStage。

`dispatch(env, agent, review)` 按 `env.target.id` 分支：

- `skill.director.start`       → `run_director_chain_with_retry`
                                 (P5 主入口：lecture + exercise×2 + review + 写库)
- `skill.profile.build`        → 内联 Python 逻辑（维度映射 + 写库 + SSE progress）
- `skill.plan.generate`        → 内联 Python 逻辑（创建 MapNodes + SSE progress）
- 其它                         → log warning + return None（Stage 2 fallback / unknown）

**profile.build / plan.generate 设计决策**：原 Stage 3 是纯 Python（无 LLM 调用）：
- profile.build 仅做 long→short 维度键映射 + 写 profiles 表
- plan.generate 仅批量创建 MapNode 行（根据 KP 列表）
LLM 不参与业务逻辑，只在 SKILL body 里"流式化"，但 v1 mcp_tool_use=[]
不允许 LLM 实时调 tool。所以这两个 Skill 用确定性 Python 完成，避免
"Mock LLM 不写库 / DeepSeek 不按 SKILL body 调 tool" 的双坑。

return None → worker 走 agent.no_reply 路径，Redis status=completed；
SSE 通过 progress_publish 直接 fire 事件（无需 reply envelope）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from selflearn.agents.director import run_director_chain_with_retry
from selflearn.core.envelope import Envelope
from selflearn.core.logging import get_logger
from selflearn.infra.db import get_session_factory
from selflearn.infra.repositories.profile_repo import ProfileRepository
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.progress.stream import progress_publish

log = get_logger("scheduler")

_DIRECTOR_SKILL = "skill.director.start"
_DETERMINISTIC_SKILLS = frozenset({"skill.profile.build", "skill.plan.generate"})

# long → short key mapping（Profile/ProfileRepository 都用短键）
_DIM_KEY_MAP: dict[str, str] = {
    "knowledge_base": "kb",
    "visual_preference": "vp",
    "analytic_style": "as",
    "goal_employment": "ge",
    "error_prone_type": "ept",
    "focus_duration": "fd",
}


async def _execute_profile_build(env: Envelope) -> None:
    """skill.profile.build — 内联 Python 实现（不再调 LLM）。"""
    trace_id = env.trace_id
    student_id = str(env.payload.get("student_id", ""))
    if not student_id:
        log.warning("skill.profile_build.no_student_id", trace_id=trace_id)
        return

    await progress_publish(trace_id, ProgressEvent(
        stage=Stage.PROFILE, status="running",
        payload={"student_id": student_id, "action": "mapping_dimensions"},
    ))

    payload_dim = env.payload.get("dimensions") or {}
    if not isinstance(payload_dim, dict):
        payload_dim = {}
    # map long → short, 默认 0.5
    dimensions: dict[str, float] = {}
    for long_k, short_k in _DIM_KEY_MAP.items():
        v = payload_dim.get(long_k, 0.5)
        try:
            dimensions[short_k] = float(v) if isinstance(v, (int, float)) else 0.5
        except (TypeError, ValueError):
            dimensions[short_k] = 0.5
    tags_raw = env.payload.get("tags", [])
    tags: list[str] = list(tags_raw) if isinstance(tags_raw, list) else []

    factory = get_session_factory()
    async with factory() as session:
        repo = ProfileRepository(session)
        profile = await repo.upsert(student_id, dimensions, tags)
        await session.commit()
        await session.refresh(profile)
        profile_id = str(profile.profile_id)

    await progress_publish(trace_id, ProgressEvent(
        stage=Stage.PROFILE, status="completed",
        payload={"student_id": student_id, "profile_id": profile_id,
                 "profile": dimensions, "tags": tags},
    ))
    log.info("skill.profile_build.completed", trace_id=trace_id,
             student_id=student_id, profile_id=profile_id)


async def _execute_plan_generate(env: Envelope) -> None:
    """skill.plan.generate — 内联 Python 实现。

    v1: 调 mcp_tool.create_map_nodes 完成 MapNode 批量插入。失败时回退到
    Profile/PlanAgent 旧路径（直接 SQLAlchemy 写入 MapNode）。
    """
    trace_id = env.trace_id
    student_id = str(env.payload.get("student_id", ""))
    if not student_id:
        log.warning("skill.plan_generate.no_student_id", trace_id=trace_id)
        return

    await progress_publish(trace_id, ProgressEvent(
        stage=Stage.PLAN, status="running",
        payload={"student_id": student_id, "action": "fetching_kps"},
    ))

    # 幂等：如果已存在任何 MapNode，直接 skip
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import select, func
        from selflearn.domain.map_node import MapNode
        from selflearn.domain.knowledge_point import KnowledgePoint

        existing_count = (await session.execute(
            select(func.count()).select_from(MapNode).where(MapNode.student_id == student_id)
        )).scalar_one()
        if existing_count > 0:
            await progress_publish(trace_id, ProgressEvent(
                stage=Stage.PLAN, status="completed",
                payload={"student_id": student_id, "node_count": existing_count,
                         "skipped": True},
            ))
            return

        # 取 5 个 KP（按创建顺序稳定）
        kps = (await session.execute(
            select(KnowledgePoint).order_by(KnowledgePoint.kp_id).limit(5)
        )).scalars().all()

        if len(kps) < 5:
            await progress_publish(trace_id, ProgressEvent(
                stage=Stage.PLAN, status="failed",
                payload={"error": f"need >= 5 KPs, got {len(kps)}"},
            ))
            return

        node_ids: list[str] = []
        for idx, kp in enumerate(kps):
            row = 0 if idx < 3 else 1
            col = idx if idx < 3 else idx - 3
            position = {"x": float(col * 120 + 30), "y": float(row * 70)}
            node = MapNode(
                node_id=uuid4(),
                student_id=student_id,
                kp_id=kp.kp_id,
                status="active",
                branch_type="main",
                position=position,
            )
            session.add(node)
            node_ids.append(str(node.node_id))
        await session.commit()

    await progress_publish(trace_id, ProgressEvent(
        stage=Stage.PLAN, status="completed",
        payload={"student_id": student_id, "node_ids": node_ids, "node_count": len(node_ids)},
    ))
    log.info("skill.plan_generate.completed", trace_id=trace_id,
             student_id=student_id, node_count=len(node_ids))


async def dispatch(
    env: Envelope,
    agent: Any | None = None,
    review: Any | None = None,
) -> Envelope | None:
    """P5 entry: 按 env.target.id 分支路由 envelope。

    P5 架构下 worker 必传 agent + review；如果有人裸调（无依赖）则抛 ValueError，
    防止静默回退到旧 Agent class（已删）。
    """
    if agent is None or review is None:
        raise ValueError(
            "P5 dispatch requires agent and review: "
            "worker must construct LLMAgent + ReviewStage and pass them in. "
            "Legacy dispatch_old has been removed."
        )

    target_id: str = env.target.id
    if target_id == _DIRECTOR_SKILL:
        await run_director_chain_with_retry(env, agent, review)
        return None

    if target_id in _DETERMINISTIC_SKILLS:
        if target_id == "skill.profile.build":
            await _execute_profile_build(env)
        elif target_id == "skill.plan.generate":
            await _execute_plan_generate(env)
        return None

    # Stage 2 fallback / 未知 skill：留日志便于排错，不抛（避免阻塞 worker）
    log.warning("scheduler.unknown_skill", skill_id=target_id)
    return None
