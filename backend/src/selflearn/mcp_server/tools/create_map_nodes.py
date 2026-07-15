"""tool.create_map_nodes: 批量创建 MapNode。"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory


async def create_map_nodes(
    student_id: str,
    kp_id_list: list[str],
    positions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """批量创建 MapNode。positions 可选（默认两行排列）。

    Returns: {"ok": True, "node_ids": [...]} 或
             {"ok": False, "error": "invalid_uuid:<kp_id>"}
    """
    factory = get_session_factory()
    async with factory() as session:
        node_ids: list[str] = []
        for idx, kp_id in enumerate(kp_id_list):
            try:
                kp_uuid = UUID(kp_id)
            except ValueError:
                return {"ok": False, "error": f"invalid_uuid:{kp_id}"}
            if positions and idx < len(positions):
                pos = positions[idx]
            else:
                row = 0 if idx < 3 else 1
                col = idx if idx < 3 else idx - 3
                pos = {"x": float(col * 120 + 30), "y": float(row * 70)}
            node = MapNode(
                student_id=student_id,
                kp_id=kp_uuid,
                status="active",
                branch_type="main",
                position=pos,
            )
            session.add(node)
            await session.flush()
            node_ids.append(str(node.node_id))
        await session.commit()
        return {"ok": True, "node_ids": node_ids}
