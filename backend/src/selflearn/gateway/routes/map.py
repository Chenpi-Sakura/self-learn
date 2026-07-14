"""Map 路由（Stage 3）：生成初始藏宝图 / 拉取节点。"""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.infra.bus import publish_envelope
from selflearn.infra.db import get_session_factory
from selflearn.schemas.map import MapNodePosition, MapNodeResponse, MapNodesResponse


router = APIRouter(prefix="/api/map", tags=["map"])


class MapGenerateRequest(BaseModel):
    student_id: uuid.UUID


@router.post("/generate", status_code=202)
async def generate_map(body: MapGenerateRequest) -> dict[str, str]:
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.plan.generate"),
        payload={"student_id": str(body.student_id)},
    )
    await publish_envelope(env, routing_key="plan.skill.plan.generate")
    return {"trace_id": env.trace_id}


# ---------------------------------------------------------------------------
# Stage 4 扩展：GET /api/map/{student_id}/nodes（spec § 4.2，前端启动加载节点列表）
# ---------------------------------------------------------------------------


@router.get("/{student_id}/nodes", response_model=MapNodesResponse)
async def get_map_nodes(student_id: UUID) -> MapNodesResponse:
    """Stage 4 spec § 4.2: 加载藏宝图节点列表。

    按 student_id 过滤 MapNode，join KnowledgePoint 取 title，
    position 直接来自 ORM JSONB 字段（不要固定 0,0）。
    """
    from sqlalchemy import select  # noqa: PLC0415

    from selflearn.domain.knowledge_point import KnowledgePoint  # noqa: PLC0415
    from selflearn.domain.map_node import MapNode  # noqa: PLC0415

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(MapNode, KnowledgePoint.title)
            .join(KnowledgePoint, MapNode.kp_id == KnowledgePoint.kp_id)
            .where(MapNode.student_id == student_id)
        )
        rows = (await session.execute(stmt)).all()

    return MapNodesResponse(
        nodes=[
            MapNodeResponse(
                node_id=row[0].node_id,
                kp_id=row[0].kp_id,
                title=row[1],
                position=MapNodePosition(
                    x=float(row[0].position.get("x", 0.0)),
                    y=float(row[0].position.get("y", 0.0)),
                ),
                status=row[0].status,
            )
            for row in rows
        ]
    )