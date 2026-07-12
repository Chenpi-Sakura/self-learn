"""tool.lint_json: jsonschema 校验 LLM 输出的 JSON。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from selflearn.tools.protocol import Tool, ToolResult


SCHEMA_DIR = Path(__file__).resolve().parents[4] / "schemas"

_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def _load_schema(name: str) -> dict[str, Any]:
    if name not in _SCHEMA_CACHE:
        path = SCHEMA_DIR / f"{name}.schema.json"
        _SCHEMA_CACHE[name] = json.loads(path.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE[name]


class LintJsonTool(Tool):
    tool_name = "tool.lint_json"
    description = "用 jsonschema 校验 LLM 输出的 JSON 是否符合业务 schema"

    async def call(self, **kwargs: Any) -> ToolResult:
        payload: str | list[Any] | dict[str, Any] = kwargs["payload"]
        schema: str = kwargs.get("schema", "exercise")
        try:
            data = json.loads(payload) if isinstance(payload, str) else payload
        except json.JSONDecodeError as e:
            return ToolResult(ok=False, error=f"json_decode_error:{e}")

        target = _load_schema(schema)
        try:
            jsonschema.validate(instance=data, schema=target)
        except jsonschema.ValidationError as e:
            return ToolResult(ok=False, error=f"schema_violation:{e.message}")

        return ToolResult(
            ok=True,
            data={"validated_count": len(data) if isinstance(data, list) else 1},
        )