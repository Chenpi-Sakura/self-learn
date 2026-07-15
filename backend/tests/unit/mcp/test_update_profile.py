"""tool.update_profile 行为测试。

覆盖：
- profile_not_found
- 应用 delta + clamp 到 [0, 1]
- 多次累加 + clamp 上界
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.update_profile import update_profile


@pytest.mark.asyncio(loop_scope="session")
async def test_update_profile_not_found(setup_kp_and_node) -> None:
    """student_id 不存在时 → ok=False + error 含 profile_not_found。"""
    student_id, _, _ = setup_kp_and_node
    result = await update_profile(student_id, deltas={"kb": 0.1})
    assert result["ok"] is False
    assert "profile_not_found" in result["error"]


@pytest.mark.asyncio(loop_scope="session")
async def test_update_profile_apply_delta(setup_kp_and_node) -> None:
    """存在 Profile 时：delta 被加到对应维度 + 返回新 dimensions。"""
    student_id, _, _ = setup_kp_and_node
    factory = get_session_factory()
    async with factory() as session:
        session.add(Profile(
            student_id=student_id,
            dimensions={"kb": 0.5, "as": 0.5},
            tags=[],
            last_updated=datetime.now(timezone.utc),
        ))
        await session.commit()

    result = await update_profile(student_id, deltas={"kb": 0.2, "as": -0.1})
    assert result["ok"] is True
    dims = result["dimensions"]
    assert abs(dims["kb"] - 0.7) < 1e-9
    assert abs(dims["as"] - 0.4) < 1e-9


@pytest.mark.asyncio(loop_scope="session")
async def test_update_profile_clamps_to_unit_interval(setup_kp_and_node) -> None:
    """累加多次 delta 后值必须 clamp 到 [0, 1]。"""
    student_id, _, _ = setup_kp_and_node
    factory = get_session_factory()
    async with factory() as session:
        session.add(Profile(
            student_id=student_id,
            dimensions={"kb": 0.9},
            tags=[],
            last_updated=datetime.now(timezone.utc),
        ))
        await session.commit()

    # +0.5 应被 clamp 到 1.0
    result = await update_profile(student_id, deltas={"kb": 0.5})
    assert result["ok"] is True
    assert result["dimensions"]["kb"] == 1.0

    # 再 -0.5（从 1.0 起算）应回到 0.5
    result2 = await update_profile(student_id, deltas={"kb": -0.5})
    assert result2["ok"] is True
    assert abs(result2["dimensions"]["kb"] - 0.5) < 1e-9

    # 再 -1.0 应被 clamp 到 0.0
    result3 = await update_profile(student_id, deltas={"kb": -1.0})
    assert result3["ok"] is True
    assert result3["dimensions"]["kb"] == 0.0
