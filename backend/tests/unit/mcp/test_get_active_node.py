"""tool.get_active_node 行为测试。"""
from __future__ import annotations

import pytest

from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.get_active_node import get_active_node


@pytest.mark.asyncio(loop_scope="session")
async def test_get_active_node_returns_active(setup_kp_and_node) -> None:
    """有 active 节点时返回。"""
    student_id, kp_id, _ = setup_kp_and_node
    factory = get_session_factory()
    async with factory() as session:
        session.add(MapNode(
            student_id=student_id,
            kp_id=kp_id,
            status="active",
            branch_type="main",
            position={"x": 30.0, "y": 0.0},
        ))
        await session.commit()

    result = await get_active_node(student_id)
    assert result["ok"] is True
    assert result["kp_id"] == str(kp_id)
    assert result["status"] == "active"
    assert result["position"] == {"x": 30.0, "y": 0.0}


@pytest.mark.asyncio(loop_scope="session")
async def test_get_active_node_none_when_no_active(setup_kp_and_node) -> None:
    """无 active 节点时返回 ok=False + error。"""
    student_id, _, _ = setup_kp_and_node
    result = await get_active_node(student_id)
    assert result["ok"] is False
    assert "no_active_node" in result["error"]
