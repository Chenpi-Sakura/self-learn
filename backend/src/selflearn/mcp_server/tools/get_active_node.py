"""tool.get_active_node: 查学生当前第一个 active 节点。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory


async def get_active_node(student_id: str) -> dict[str, Any]:
    """查 student_id 下第一个 status=active 的 MapNode。

    Returns: {"ok": True, "node_id", "kp_id", "status", "position"} 或
             {"ok": False, "error": "no_active_node"}
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(MapNode)
            .where(MapNode.student_id == student_id, MapNode.status == "active")
            .limit(1)
        )
        node = (await session.execute(stmt)).scalars().first()
        if node is None:
            return {"ok": False, "error": "no_active_node"}
        return {
            "ok": True,
            "node_id": str(node.node_id),
            "kp_id": str(node.kp_id),
            "status": node.status,
            "position": node.position,
        }
