"""tool.create_profile 行为测试。"""
from __future__ import annotations

import pytest

from selflearn.mcp_server.tools.create_profile import create_profile


@pytest.mark.asyncio(loop_scope="session")
async def test_create_profile_new(setup_kp_and_node) -> None:
    """student_id 无 Profile → 新建，updated=False。"""
    student_id, _, _ = setup_kp_and_node
    result = await create_profile(
        student_id,
        dimensions={"kb": 0.7},
        tags=["new"],
    )
    assert result["ok"] is True
    assert result["updated"] is False


@pytest.mark.asyncio(loop_scope="session")
async def test_create_profile_update_existing(setup_kp_and_node) -> None:
    """student_id 已有 Profile → upsert 覆盖，updated=True。"""
    student_id, _, _ = setup_kp_and_node
    await create_profile(student_id, dimensions={"kb": 0.5}, tags=[])
    result = await create_profile(student_id, dimensions={"kb": 0.8}, tags=["upd"])
    assert result["ok"] is True
    assert result["updated"] is True
