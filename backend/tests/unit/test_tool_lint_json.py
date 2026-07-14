"""tool.lint_json 单元测试 — Stage 3 § 9.2。"""
from __future__ import annotations

import pytest

from selflearn.tools.protocol import ToolRegistry, ToolResult


@pytest.mark.asyncio
async def test_lint_json_rejects_invalid() -> None:
    """tool.lint_json 必须用 jsonschema 校验，缺字段即拒收。"""
    result: ToolResult = await ToolRegistry.call(
        name="tool.lint_json",
        payload=[{"exercise_type": "single_choice", "prompt": "Q?", "correct_answer": "A",
                   "difficulty": 9, "score": 1.0}],  # difficulty 越界
        schema="exercise",
    )
    assert result.ok is False
    assert "difficulty" in (result.error or "") or "schema_violation" in (result.error or "")


@pytest.mark.asyncio
async def test_lint_json_accepts_valid() -> None:
    result: ToolResult = await ToolRegistry.call(
        name="tool.lint_json",
        payload=[{"exercise_type": "single_choice",
                   "prompt": "What is 2+2?",
                   "options": ["A", "B", "C", "D"],
                   "correct_answer": "A",
                   "explanation": "x",
                   "difficulty": 2,
                   "score": 1.5}],
        schema="exercise",
    )
    assert result.ok is True
    assert result.data["validated_count"] == 1