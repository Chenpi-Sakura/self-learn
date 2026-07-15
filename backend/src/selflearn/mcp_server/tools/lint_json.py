"""tool.lint_json: jsonschema 校验。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_DIR = Path(__file__).resolve().parents[4] / "schemas"
_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def _load_schema(name: str) -> dict[str, Any]:
    if name not in _SCHEMA_CACHE:
        path = SCHEMA_DIR / f"{name}.schema.json"
        _SCHEMA_CACHE[name] = json.loads(path.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE[name]


async def lint_json(payload: Any, schema_name: str) -> dict[str, Any]:
    """校验 LLM 输出的 JSON 是否符合 schema。"""
    try:
        data = json.loads(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"json_decode_error:{e}"}
    try:
        target = _load_schema(schema_name)
    except FileNotFoundError:
        return {"ok": False, "error": f"schema_not_found:{schema_name}"}
    try:
        jsonschema.validate(instance=data, schema=target)
    except jsonschema.ValidationError as e:
        return {"ok": False, "error": f"schema_violation:{e.message}"}
    return {"ok": True, "error": None}
