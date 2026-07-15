"""tool.get_kp 行为测试。"""
from __future__ import annotations

import pytest

from selflearn.mcp_server.tools.get_kp import get_kp


@pytest.mark.asyncio(loop_scope="session")
async def test_get_kp_invalid_uuid() -> None:
    """非法 UUID 字符串 → ok=False + error 含 invalid_uuid。"""
    result = await get_kp("not-a-uuid")
    assert result["ok"] is False
    assert "invalid_uuid" in result["error"]


@pytest.mark.asyncio(loop_scope="session")
async def test_get_kp_existing(setup_kp_and_node) -> None:
    """存在的 KP → ok=True + 字段齐备。"""
    _, kp_id, _ = setup_kp_and_node
    result = await get_kp(str(kp_id))
    assert result["ok"] is True
    assert result["kp_id"] == str(kp_id)
    assert result["title"] == "test_kp"
    assert result["subject"] == "test"
    assert result["difficulty"] == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_get_kp_not_found() -> None:
    """合法 UUID 但 DB 不存在 → ok=False + error 含 kp_not_found。"""
    from uuid import uuid4

    result = await get_kp(str(uuid4()))
    assert result["ok"] is False
    assert "kp_not_found" in result["error"]