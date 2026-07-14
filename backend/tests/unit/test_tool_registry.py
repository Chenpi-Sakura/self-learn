"""ToolRegistry 单元测试（T13.5 Task 7 配套）。"""
from __future__ import annotations

import pytest

from selflearn.tools.protocol import ToolRegistry, ToolResult


@pytest.mark.asyncio
async def test_tool_registry_call_missing_name_returns_error() -> None:
    """不传 name 时返回 missing_tool_name 错误。"""
    result = await ToolRegistry.call(payload="x")
    assert not result.ok
    assert result.error == "missing_tool_name"


@pytest.mark.asyncio
async def test_tool_registry_call_unknown_tool_returns_error() -> None:
    """name 不在 _tools 字典时返回 tool_not_found。"""
    result = await ToolRegistry.call(name="tool.does.not.exist")
    assert not result.ok
    assert "tool_not_found" in result.error


@pytest.mark.asyncio
async def test_tool_registry_call_known_tool_uses_name_kwarg() -> None:
    """name 作为 kwarg 传入时能找到对应 tool。"""
    # tool.fetch_template 已知存在
    result = await ToolRegistry.call(
        name="tool.fetch_template", template_name="exercise_generation_v1"
    )
    assert result.ok, result.error