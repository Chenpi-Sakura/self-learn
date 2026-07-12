"""MCP Tool 协议层（Stage 3 § 9.2）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


class Tool(ABC):
    tool_name: str
    description: str

    @abstractmethod
    async def call(self, **kwargs: Any) -> ToolResult: ...


class ToolRegistry:
    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        cls._tools[tool.tool_name] = tool

    @classmethod
    async def call(cls, name: str, **kwargs: Any) -> ToolResult:
        tool = cls._tools.get(name)
        if not tool:
            return ToolResult(ok=False, error=f"tool_not_found:{name}")
        try:
            return await tool.call(**kwargs)
        except Exception as e:  # noqa: BLE001
            return ToolResult(ok=False, error=repr(e))


def _register_default_tools() -> None:
    from selflearn.tools.builtin.lint_json import LintJsonTool
    from selflearn.tools.builtin.fetch_template import FetchTemplateTool
    from selflearn.tools.builtin.store_kp import StoreKPTool
    ToolRegistry.register(LintJsonTool())
    ToolRegistry.register(FetchTemplateTool())
    ToolRegistry.register(StoreKPTool())


_register_default_tools()