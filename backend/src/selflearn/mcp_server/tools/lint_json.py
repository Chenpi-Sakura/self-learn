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
        # 兼容 SKILL.md frontmatter 的多种写法：
        #   "schemas/exercise.schema.json"（目录前缀 + .json 后缀）
        #   "exercise.schema.json"       （仅 .json 后缀）
        #   "exercise.schema"            （仅 .schema 后缀）
        #   "exercise"                   （无后缀）
        # 所有形式都映射到 SCHEMA_DIR/<basename>.schema.json（当未带 .json 时）。
        p = Path(name)
        if p.suffix == ".json":
            filename = p.name
        elif p.suffix == ".schema":
            filename = f"{p.name}.json"
        else:
            filename = f"{p.name}.schema.json"
        path = SCHEMA_DIR / filename
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
        path = "/".join(str(p) for p in e.absolute_path) or "<root>"
        return {"ok": False, "error": f"schema_violation:{path}:{e.message}"}
    return {"ok": True, "error": None}
