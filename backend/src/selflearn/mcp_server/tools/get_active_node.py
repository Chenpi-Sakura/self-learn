"""tool.get_active_node: 查学生当前节点（支持精确按 node_id 路由）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory


async def get_active_node(student_id: str, node_id: str | None = None) -> dict[str, Any]:
    """查 student_id 下指定节点（精确路由）或第一个 active 节点（fallback）。

    Args:
        student_id: 学生 ID
        node_id: 可选；传入则精确按 (student_id, node_id) 查，未传则 fallback 到
                 该 student 第一个 status='active' 的节点。

    Returns: {"ok": True, "node_id", "kp_id", "status", "position"} 或
             {"ok": False, "error": "no_active_node" | "node_not_found"}
    """
    factory = get_session_factory()
    async with factory() as session:
        if node_id is not None:
            # 精确路由：POST /start 把用户点的 node_id 传下来，Director 应当按它生成关卡
            stmt = (
                select(MapNode)
                .where(MapNode.student_id == student_id, MapNode.node_id == node_id)
                .limit(1)
            )
            node = (await session.execute(stmt)).scalars().first()
            if node is None:
                return {"ok": False, "error": "node_not_found"}
        else:
            # 向后兼容：第一个 status=active 的节点
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
