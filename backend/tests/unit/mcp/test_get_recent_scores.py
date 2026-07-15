"""tool.get_recent_scores 行为测试。"""
from __future__ import annotations

from uuid import uuid4

import pytest

from selflearn.domain.level_completion import LevelCompletion
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.get_recent_scores import get_recent_scores


@pytest.mark.asyncio(loop_scope="session")
async def test_get_recent_scores_empty(setup_kp_and_node) -> None:
    """无 score 记录 → 返回空 list。"""
    student_id, _, _ = setup_kp_and_node
    scores = await get_recent_scores(student_id, limit=3)
    assert scores == []


@pytest.mark.asyncio(loop_scope="session")
async def test_get_recent_scores_returns_recent_first() -> None:
    """按 submitted_at DESC 排序,limit 截断。

    LevelCompletion FK → levels → map_nodes → knowledge_points. 直接建一条
    最小链路: KnowledgePoint + MapNode + Level + LevelCompletion。
    """
    from datetime import datetime, timedelta, timezone
    from selflearn.domain.knowledge_point import KnowledgePoint
    from selflearn.domain.level import Level
    from selflearn.domain.map_node import MapNode

    student_id = str(uuid4())
    kp_id = uuid4()
    # Postgres column is TIMESTAMP WITHOUT TIME ZONE → 用 naive UTC
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    factory = get_session_factory()
    async with factory() as session:
        kp = KnowledgePoint(
            kp_id=kp_id,
            subject="test",
            title="recent_scores_kp",
            description="d",
            difficulty=1,
            prerequisites=[],
        )
        session.add(kp)
        await session.flush()

        node = MapNode(
            student_id=student_id,
            kp_id=kp_id,
            status="active",
            branch_type="main",
            position={"x": 0.0, "y": 0.0},
        )
        session.add(node)
        await session.flush()
        levels: list[Level] = []
        for i in range(5):
            lv = Level(
                node_id=node.node_id,
            )
            session.add(lv)
            levels.append(lv)
        await session.flush()

        for i, (lv, score) in enumerate(zip(levels, [60.0, 70.0, 80.0, 90.0, 100.0])):
            session.add(LevelCompletion(
                level_id=lv.level_id,
                student_id=student_id,
                score=score,
                duration_seconds=60,
                answers={},
                metrics={},
                submitted_at=now - timedelta(minutes=10 - i),
            ))
        await session.commit()

    scores = await get_recent_scores(student_id, limit=3)
    assert scores == [100.0, 90.0, 80.0]
