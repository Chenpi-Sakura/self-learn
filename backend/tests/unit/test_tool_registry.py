"""ToolRegistry 单元测试 — Stage 3 § 9.2。"""
import asyncio

from selflearn.tools.protocol import ToolResult, ToolRegistry


def test_tool_not_found_returns_error() -> None:
    async def run() -> ToolResult:
        return await ToolRegistry.call("tool.does.not_exist")

    res: ToolResult = asyncio.run(run())
    assert isinstance(res, ToolResult)
    assert res.ok is False
    assert "tool_not_found" in (res.error or "")