"""tool.bulk_create_exercises 行为测试。"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from selflearn.domain.exercise import Exercise
from selflearn.domain.level import Level
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.bulk_create_exercises import bulk_create_exercises


async def _setup_level(student_id: str, kp_id: UUID) -> str:
    """辅助：插入 KP+MapNode+Level，返回 level_id 字符串。"""
    factory = get_session_factory()
    async with factory() as session:
        node = MapNode(
            student_id=student_id,
            kp_id=kp_id,
            status="active",
            branch_type="main",
            position={"x": 30.0, "y": 0.0},
        )
        session.add(node)
        await session.flush()
        node_uuid = node.node_id
        level = Level(node_id=node_uuid, status="generated", form="exercise")
        session.add(level)
        await session.commit()
        await session.refresh(level)
        return str(level.level_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_bulk_create_exercises_happy_path(setup_kp_and_node) -> None:
    """传入 3 个 exercise → ok=True + 3 个 exercise_id。"""
    student_id, kp_id, _ = setup_kp_and_node
    level_id = await _setup_level(student_id, kp_id)
    factory = get_session_factory()

    exercises = [
        {
            "exercise_type": "single_choice",
            "prompt": "1+1=?",
            "options": ["1", "2", "3"],
            "correct_answer": "2",
            "explanation": "因为 1+1=2",
            "difficulty": 1,
            "score": 1.0,
        },
        {
            "exercise_type": "fill_blank",
            "prompt": "2*2=?",
            "correct_answer": "4",
        },
        {
            "exercise_type": "short_answer",
            "prompt": "解释欧几里得算法",
            "correct_answer": "求最大公约数",
            "difficulty": 2,
        },
    ]
    result = await bulk_create_exercises(level_id=level_id, exercises=exercises)
    assert result["ok"] is True
    assert len(result["exercise_ids"]) == 3

    # 校验 default 字段值
    async with factory() as session:
        for idx, ex_id in enumerate(result["exercise_ids"]):
            stmt = select(Exercise).where(Exercise.exercise_id == UUID(ex_id))  # type: ignore[arg-type]
            ex = (await session.execute(stmt)).scalars().first()
            assert ex is not None
            if idx == 0:
                assert ex.options == ["1", "2", "3"]
                assert ex.explanation == "因为 1+1=2"
                assert ex.difficulty == 1
                assert float(ex.score) == 1.0
            elif idx == 1:
                assert ex.options == []
                assert ex.explanation == ""
                assert ex.difficulty == 1
            elif idx == 2:
                assert ex.difficulty == 2


@pytest.mark.asyncio(loop_scope="session")
async def test_bulk_create_exercises_empty_list(setup_kp_and_node) -> None:
    """空列表 → ok=True + 空 exercise_ids。"""
    student_id, kp_id, _ = setup_kp_and_node
    level_id = await _setup_level(student_id, kp_id)
    result = await bulk_create_exercises(level_id=level_id, exercises=[])
    assert result["ok"] is True
    assert result["exercise_ids"] == []


@pytest.mark.asyncio(loop_scope="session")
async def test_bulk_create_exercises_invalid_uuid() -> None:
    """非法 UUID → ok=False。"""
    result = await bulk_create_exercises(
        level_id="not-a-uuid",  # type: ignore[arg-type]
        exercises=[
            {
                "exercise_type": "single_choice",
                "prompt": "x",
                "correct_answer": "x",
            }
        ],
    )
    assert result["ok"] is False
    assert "invalid_uuid" in result["error"]


@pytest.mark.asyncio(loop_scope="session")
async def test_bulk_create_exercises_nonexistent_level(setup_kp_and_node) -> None:
    """合法 UUID 但 level 不存在 → 抛 IntegrityError，工具返回 ok=False。"""
    student_id, kp_id, _ = setup_kp_and_node  # noqa: F841
    fake_level_id = str(uuid4())
    result = await bulk_create_exercises(
        level_id=fake_level_id,
        exercises=[
            {
                "exercise_type": "single_choice",
                "prompt": "x",
                "correct_answer": "x",
            }
        ],
    )
    assert result["ok"] is False
    assert "error" in result
