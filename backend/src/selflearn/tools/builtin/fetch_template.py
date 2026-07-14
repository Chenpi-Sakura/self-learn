"""tool.fetch_template: 从本地 YAML 读 prompt 模板（Stage 3 stub）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from selflearn.tools.protocol import Tool, ToolResult


PROMPT_DIR = Path(__file__).resolve().parents[4] / "prompts"


class FetchTemplateTool(Tool):
    tool_name = "tool.fetch_template"
    description = "读 prompts/{name}.yaml 模板内容，返回 string"

    async def call(self, **kwargs: Any) -> ToolResult:
        # T13.5 Task 7: ToolRegistry.call 把 name 收进 kwargs 后 pop 出去，
        # tool 内部可以用任意参数名。保留 template_name + name 两套 key 兼容。
        name: str = kwargs.get("template_name") or kwargs.get("name", "")
        path = PROMPT_DIR / f"{name}.yaml"
        if not path.exists():
            return ToolResult(ok=False, error=f"template_not_found:{name}")
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            return ToolResult(ok=False, error=repr(e))
        return ToolResult(ok=True, data={"name": name, "content": content})