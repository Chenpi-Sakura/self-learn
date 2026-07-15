"""tool.get_kps 行为测试。"""
from __future__ import annotations

from uuid import uuid4

import pytest

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.get_kps import get_kps


@pytest.mark.asyncio(loop_scope="session")
async def test_get_kps_limit() -> None:
    """插入 7 个 KP → limit=3 → 只返 3 个。"""
    factory = get_session_factory()
    async with factory() as session:
        for i in range(7):
            session.add(KnowledgePoint(
                kp_id=uuid4(),
                subject="test",
                title=f"kp_{i}",
                description=f"desc_{i}",
                difficulty=1,
                prerequisites=[],
            ))
        await session.commit()

    result = await get_kps(limit=3)
    assert len(result) == 3
    for kp in result:
        assert "kp_id" in kp
        assert "title" in kp
        assert "description" in kp
        assert "difficulty" in kp


@pytest.mark.asyncio(loop_scope="session")
async def test_get_kps_default_limit(setup_kp_and_node) -> None:
    """setup_kp_and_node 插入 1 个 KP → 默认 limit=5 → 至少返回 1 个。"""
    _, _, _ = setup_kp_and_node
    result = await get_kps()
    assert len(result) >= 1
