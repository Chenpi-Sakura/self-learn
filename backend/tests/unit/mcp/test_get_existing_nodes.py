"""tool.get_existing_nodes 行为测试。"""
from __future__ import annotations

import pytest

from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.get_existing_nodes import get_existing_nodes


@pytest.mark.asyncio(loop_scope="session")
async def test_get_existing_nodes_empty(setup_kp_and_node) -> None:
    """student_id 无节点 → 返回空列表。"""
    student_id, _, _ = setup_kp_and_node
    result = await get_existing_nodes(student_id)
    assert result == []


@pytest.mark.asyncio(loop_scope="session")
async def test_get_existing_nodes_returns_all(setup_kp_and_node) -> None:
    """student_id 有节点 → 全部返回（字段齐备）。"""
    student_id, kp_id, _ = setup_kp_and_node
    factory = get_session_factory()
    async with factory() as session:
        for i, status in enumerate(["active", "sleeping", "completed"]):
            session.add(MapNode(
                student_id=student_id,
                kp_id=kp_id,
                status=status,
                branch_type="main",
                position={"x": float(i * 120 + 30), "y": 0.0},
            ))
        await session.commit()

    result = await get_existing_nodes(student_id)
    assert len(result) == 3
    statuses = {n["status"] for n in result}
    assert statuses == {"active", "sleeping", "completed"}
    for n in result:
        assert "node_id" in n
        assert "kp_id" in n
        assert n["kp_id"] == str(kp_id)
        assert "status" in n
        assert "position" in n
