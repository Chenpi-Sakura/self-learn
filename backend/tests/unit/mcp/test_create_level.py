"""tool.create_level 行为测试。"""
from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from selflearn.domain.level import Level
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.create_level import create_level


@pytest.mark.asyncio(loop_scope="session")
async def test_create_level_happy_path_no_lecture(setup_kp_and_node) -> None:
    """最小入参：node_id → 1 个 Level，status=generated/form=exercise。"""
    student_id, kp_id, _ = setup_kp_and_node
    factory = get_session_factory()
    node_id: str
    async with factory() as session:
        node = MapNode(
            student_id=student_id,
            kp_id=kp_id,
            status="active",
            branch_type="main",
            position={"x": 30.0, "y": 0.0},
        )
        session.add(node)
        await session.commit()
        await session.refresh(node)
        node_id = str(node.node_id)

    result = await create_level(node_id=node_id)
    assert result["ok"] is True
    assert "level_id" in result
    level_uuid = UUID(result["level_id"])

    # 校验 DB 中的记录
    async with factory() as session:
        stmt = select(Level).where(Level.level_id == level_uuid)  # type: ignore[arg-type]
        level = (await session.execute(stmt)).scalars().first()
        assert level is not None
        assert level.status == "generated"
        assert level.form == "exercise"
        assert level.node_id == UUID(node_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_create_level_with_lecture_html(setup_kp_and_node) -> None:
    """传 lecture_html → 不报错（schema 当前无此列会被 getattr 跳过）。"""
    student_id, kp_id, _ = setup_kp_and_node
    factory = get_session_factory()
    node_id: str
    async with factory() as session:
        node = MapNode(
            student_id=student_id,
            kp_id=kp_id,
            status="active",
            branch_type="main",
            position={"x": 30.0, "y": 0.0},
        )
        session.add(node)
        await session.commit()
        await session.refresh(node)
        node_id = str(node.node_id)

    # 防御性写入：当前 schema 没有 lecture_html，getattr 跳过，不报错即可
    result = await create_level(node_id=node_id, lecture_html="<h1>hi</h1>")
    assert result["ok"] is True
    assert "level_id" in result


@pytest.mark.asyncio(loop_scope="session")
async def test_create_level_invalid_uuid() -> None:
    """非法 UUID → ok=False + error 含 invalid_uuid。"""
    result = await create_level(node_id="not-a-uuid")
    assert result["ok"] is False
    assert "invalid_uuid" in result["error"]
