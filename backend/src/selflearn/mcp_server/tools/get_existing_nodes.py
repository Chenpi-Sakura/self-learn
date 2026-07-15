"""tool.get_existing_nodes: 查学生所有 MapNode。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory


async def get_existing_nodes(student_id: str) -> list[dict[str, Any]]:
    """查 student_id 下所有 MapNode。

    Returns: list of {"node_id", "kp_id", "status", "position"}
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(MapNode).where(MapNode.student_id == student_id)
        nodes = (await session.execute(stmt)).scalars().all()
        return [
            {
                "node_id": str(n.node_id),
                "kp_id": str(n.kp_id),
                "status": n.status,
                "position": n.position,
            }
            for n in nodes
        ]
