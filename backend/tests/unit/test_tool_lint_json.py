"""tool.lint_json 单元测试 — Stage 3 § 9.2。"""
import asyncio

from selflearn.tools.protocol import ToolRegistry, ToolResult


def test_lint_json_rejects_invalid() -> None:
    """tool.lint_json 必须用 jsonschema 校验，缺字段即拒收。"""
    async def run() -> ToolResult:
        return await ToolRegistry.call(
            "tool.lint_json",
            payload=[{"exercise_type": "single_choice", "prompt": "Q?", "correct_answer": "A",
                       "difficulty": 9, "score": 1.0}],  # difficulty 越界
            schema="exercise",
        )

    res: ToolResult = asyncio.run(run())
    assert res.ok is False
    assert "difficulty" in (res.error or "") or "schema_violation" in (res.error or "")


def test_lint_json_accepts_valid() -> None:
    async def run() -> ToolResult:
        return await ToolRegistry.call(
            "tool.lint_json",
            payload=[{"exercise_type": "single_choice",
                       "prompt": "What is 2+2?",
                       "options": ["A", "B", "C", "D"],
                       "correct_answer": "A",
                       "explanation": "x",
                       "difficulty": 2,
                       "score": 1.5}],
            schema="exercise",
        )

    res: ToolResult = asyncio.run(run())
    assert res.ok is True
    assert res.data["validated_count"] == 1