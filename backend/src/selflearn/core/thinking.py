"""LLM 思考模式辅助（Stage 3 新增）。"""
from __future__ import annotations

import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json_from_fence(raw: str) -> object:
    """从 LLM 输出中提取 JSON。优先取 ```json fence；其次尝试整段 parse。
    返回已反序列化对象（list / dict）；raise json.JSONDecodeError。"""
    matches = _FENCE_RE.findall(raw)
    if matches:
        return json.loads(matches[0])
    return json.loads(raw)
