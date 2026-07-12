"""PlanAgent: 根据 profile 生成 5-10 个 MapNode。"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.progress.stream import progress_publish
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.skills.library import get as get_skill


class PlanAgent(AbstractAgent):
    """skill.plan.generate: 根据 profile 调 LLM 生成 5-10 个 KP + MapNode。

    Stage 3 MVP：不再调 LLM，直接复用 `scripts/seed_map.py` 已 seed 的 KP（取前 N 条），为每个 KP 创建一个 status=active / branch_type=main / position=(idx*100, 0) 的 MapNode。
    """

    agent_id = "plan-01"
    agent_type = "plan"
    queue = "agent.plan.work"

    async def run(self, env: Envelope) -> Envelope:
        trace_id = env.trace_id
        student_id_raw = env.payload["student_id"]
        student_id = UUID(student_id_raw) if isinstance(student_id_raw, str) else student_id_raw

        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.PLAN, status="running",
            payload={"student_id": str(student_id)},
        ))

        # 加载 Skill 做 sanity check（Intent / Validation Rules 是开发者文档）
        skill = get_skill("skill.plan.generate")
        assert skill.name == "skill.plan.generate"

        factory = get_session_factory()
        async with factory() as session:
            stmt = select(KnowledgePoint).limit(5)
            kps = (await session.execute(stmt)).scalars().all()

            node_ids: list[str] = []
            for idx, kp in enumerate(kps):
                node = MapNode(
                    student_id=student_id,
                    kp_id=kp.kp_id,
                    status="active",
                    branch_type="main",
                    position={"x": float(idx * 100), "y": 0.0},
                )
                session.add(node)
                await session.flush()
                node_ids.append(str(node.node_id))
            await session.commit()

        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.PLAN, status="completed",
            payload={"node_count": len(node_ids), "node_ids": node_ids},
        ))

        return Envelope(
            action="skill.completed",
            sender=ActorRef(type="agent", id=self.agent_id),
            target=ActorRef(type="gateway", id=env.sender.id),
            payload={"node_count": len(node_ids), "node_ids": node_ids},
            trace_id=trace_id,
            parent_id=env.span_id,
        )