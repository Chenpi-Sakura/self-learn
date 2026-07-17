"""Map 路由（Stage 3）：生成初始藏宝图 / 拉取节点。"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.infra.bus import publish_envelope
from selflearn.infra.db import get_session_factory
from selflearn.schemas.map import MapNodePosition, MapNodeResponse, MapNodesResponse


router = APIRouter(prefix="/api/map", tags=["map"])


class MapGenerateRequest(BaseModel):
    student_id: str


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
async def get_map_nodes(student_id: str) -> MapNodesResponse:
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

    def _position_xy(pos: dict[str, object]) -> tuple[float, float]:
        """兼容两套 position schema:
        - 新: {"x": float, "y": float}
        - 老: {"col": int, "row": int} (extract_topics 流水线写入, 网格坐标)
        前端 TreasureMap 需要浮点字段; 老数据按 col→x、row→y 映射 (1 cell = 1 unit)。
        """
        if "x" in pos or "y" in pos:
            return (float(str(pos.get("x", 0))), float(str(pos.get("y", 0))))
        return (float(str(pos.get("col", 0))), float(str(pos.get("row", 0))))

    return MapNodesResponse(
        nodes=[
            MapNodeResponse(
                node_id=row[0].node_id,
                kp_id=row[0].kp_id,
                title=row[1],
                position=MapNodePosition(
                    x=_position_xy(row[0].position)[0],
                    y=_position_xy(row[0].position)[1],
                ),
                status=row[0].status,
            )
            for row in rows
        ]
    )