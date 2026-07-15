"""tool.get_profile 行为测试。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.get_profile import get_profile


@pytest.mark.asyncio(loop_scope="session")
async def test_get_profile_not_found(setup_kp_and_node) -> None:
    """student_id 不存在时 → ok=False + error 含 profile_not_found。"""
    student_id, _, _ = setup_kp_and_node
    result = await get_profile(student_id)
    assert result["ok"] is False
    assert "profile_not_found" in result["error"]


@pytest.mark.asyncio(loop_scope="session")
async def test_get_profile_existing(setup_kp_and_node) -> None:
    """存在的 Profile → ok=True + 字段齐备。"""
    student_id, _, _ = setup_kp_and_node
    factory = get_session_factory()
    async with factory() as session:
        session.add(Profile(
            student_id=student_id,
            dimensions={"kb": 0.5, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
            tags=["smoke"],
            last_updated=datetime.now(timezone.utc),
        ))
        await session.commit()

    result = await get_profile(student_id)
    assert result["ok"] is True
    assert result["dimensions"]["kb"] == 0.5
    assert result["tags"] == ["smoke"]
