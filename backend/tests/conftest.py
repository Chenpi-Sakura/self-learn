"""公共测试 fixture。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory


@pytest.fixture
def any_int() -> int:
    return 42


@pytest_asyncio.fixture(loop_scope="session")
async def setup_kp_and_node() -> AsyncIterator[tuple[str, UUID, None]]:
    """插入 1 个 KP + 返回 (student_id, kp_id, node_id=None)。

    node_id 留 None：调用方按需再插 MapNode。
    """
    student_id = str(uuid4())
    kp_id = uuid4()
    factory = get_session_factory()
    async with factory() as session:
        kp = KnowledgePoint(
            kp_id=kp_id,
            subject="test",
            title="test_kp",
            description="desc",
            difficulty=1,
            prerequisites=[],
        )
        session.add(kp)
        await session.commit()
    yield student_id, kp_id, None
