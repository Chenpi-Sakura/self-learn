"""tool.apply_level_completion 行为测试。

覆盖：
- invalid_uuid
- level_not_found
- happy path（写 LevelCompletion + level.status=completed）
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from selflearn.domain.level import Level
from selflearn.domain.level_completion import LevelCompletion
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.apply_level_completion import apply_level_completion


@pytest.mark.asyncio(loop_scope="session")
async def test_apply_level_completion_invalid_uuid() -> None:
    """非法 UUID → ok=False + error 含 invalid_uuid。"""
    result = await apply_level_completion(
        level_id="not-a-uuid",
        student_id="some-student",
        score=0.8,
        answers={"q1": "a"},
    )
    assert result["ok"] is False
    assert "invalid_uuid" in result["error"]


@pytest.mark.asyncio(loop_scope="session")
async def test_apply_level_completion_level_not_found() -> None:
    """合法 UUID 但 Level 不存在 → ok=False + error=level_not_found。"""
    result = await apply_level_completion(
        level_id=str(uuid4()),
        student_id="some-student",
        score=0.5,
        answers={},
    )
    assert result["ok"] is False
    assert result["error"] == "level_not_found"


@pytest.mark.asyncio(loop_scope="session")
async def test_apply_level_completion_happy_path(setup_kp_and_node) -> None:
    """happy path：写 LevelCompletion + 把 level.status 设为 completed。"""
    student_id, kp_id, _ = setup_kp_and_node
    factory = get_session_factory()
    node_id: str
    level_id: str
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

        level = Level(node_id=node.node_id, status="generated", form="exercise")
        session.add(level)
        await session.commit()
        await session.refresh(level)
        level_id = str(level.level_id)

    answers = {"q1": "a", "q2": "b"}
    result = await apply_level_completion(
        level_id=level_id,
        student_id=student_id,
        score=0.85,
        answers=answers,
    )
    assert result["ok"] is True
    assert "completion_id" in result
    completion_uuid = UUID(result["completion_id"])
    assert result["score"] == 0.85

    # 校验 LevelCompletion 写入了
    async with factory() as session:
        stmt = select(LevelCompletion).where(
            LevelCompletion.completion_id == completion_uuid  # type: ignore[arg-type]
        )
        completion = (await session.execute(stmt)).scalars().first()
        assert completion is not None
        assert completion.student_id == student_id
        assert float(completion.score) == 0.85
        assert dict(completion.answers) == answers
        assert dict(completion.metrics) == {"items": len(answers)}

    # 校验 level.status = completed
    async with factory() as session:
        level_row = await session.get(Level, UUID(level_id))
        assert level_row is not None
        assert level_row.status == "completed"
