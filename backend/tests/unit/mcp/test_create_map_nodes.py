"""tool.create_map_nodes 行为测试。"""
from __future__ import annotations

from uuid import uuid4

import pytest

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.create_map_nodes import create_map_nodes


@pytest.mark.asyncio(loop_scope="session")
async def test_create_map_nodes_empty_kp_list() -> None:
    """空 kp_id_list → ok=True + 空 node_ids。"""
    student_id = str(uuid4())
    result = await create_map_nodes(student_id, kp_id_list=[])
    assert result["ok"] is True
    assert result["node_ids"] == []


@pytest.mark.asyncio(loop_scope="session")
async def test_create_map_nodes_invalid_uuid() -> None:
    """非法 UUID 字符串 → ok=False + error 含 invalid_uuid。"""
    student_id = str(uuid4())
    result = await create_map_nodes(student_id, kp_id_list=["not-a-uuid"])
    assert result["ok"] is False
    assert "invalid_uuid" in result["error"]


@pytest.mark.asyncio(loop_scope="session")
async def test_create_map_nodes_happy_path_with_positions(setup_kp_and_node) -> None:
    """传入 positions → 用传入的 position。"""
    student_id, kp_id, _ = setup_kp_and_node
    positions = [{"x": 100.0, "y": 200.0}]
    result = await create_map_nodes(
        student_id,
        kp_id_list=[str(kp_id)],
        positions=positions,
    )
    assert result["ok"] is True
    assert len(result["node_ids"]) == 1
    node_id = result["node_ids"][0]
    # 验证 DB 里 position 是传入值
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import select
        from selflearn.domain.map_node import MapNode
        stmt = select(MapNode).where(MapNode.node_id == node_id)  # type: ignore[arg-type]
        node = (await session.execute(stmt)).scalars().first()
        assert node is not None
        assert node.position == {"x": 100.0, "y": 200.0}
        assert node.status == "active"
        assert node.branch_type == "main"


@pytest.mark.asyncio(loop_scope="session")
async def test_create_map_nodes_default_positions() -> None:
    """不传 positions → 用默认两行排列（前 3 个 y=0, 后 2 个 y=70）。"""
    student_id = str(uuid4())
    factory = get_session_factory()
    kp_ids: list[str] = []
    async with factory() as session:
        for i in range(5):
            kp_id = uuid4()
            session.add(KnowledgePoint(
                kp_id=kp_id,
                subject="test",
                title=f"kp_{i}",
                description=f"desc_{i}",
                difficulty=1,
                prerequisites=[],
            ))
            kp_ids.append(str(kp_id))
        await session.commit()

    result = await create_map_nodes(student_id, kp_id_list=kp_ids)
    assert result["ok"] is True
    assert len(result["node_ids"]) == 5

    # 验证默认 position：idx 0,1,2 → y=0; idx 3,4 → y=70
    from sqlalchemy import select
    from selflearn.domain.map_node import MapNode
    async with factory() as session:
        for idx, node_id in enumerate(result["node_ids"]):
            stmt = select(MapNode).where(MapNode.node_id == node_id)  # type: ignore[arg-type]
            node = (await session.execute(stmt)).scalars().first()
            assert node is not None
            expected_y = 0.0 if idx < 3 else 70.0
            assert node.position["y"] == expected_y
