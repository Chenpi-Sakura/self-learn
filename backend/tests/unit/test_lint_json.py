"""tool.lint_json 真验证测试（T13.5 Task 6 配套）。

不 mock lint_json，真实走 jsonschema 校验，确保 prompt 改了之后 LLM 输出能过 schema。
"""
from __future__ import annotations

import pytest

from selflearn.tools.builtin.lint_json import LintJsonTool


@pytest.mark.asyncio
async def test_lint_json_accepts_prompt_example_output() -> None:
    """prompt 给的示例输出形态必须能过 lint_json。

    这是 T13.5 Task 6 的回归保护：prompt 与 schema 必须严格对齐。
    """
    # 与 prompt 中的样例完全一致
    sample = [{
        "exercise_type": "single_choice",
        "prompt": "Transformer 中 self-attention 的核心公式中，缩放因子是？",
        "options": ["√d_k", "d_k", "d_model", "1"],
        "correct_answer": "√d_k",
        "explanation": "为防止 QK^T 的方差随维度 d_k 增大而爆炸，缩放因子是 √d_k。",
        "difficulty": 2,
        "score": 1.5,
    }]
    result = await LintJsonTool().call(payload=sample, schema="exercise")
    assert result.ok, f"lint 拒绝示例输出: {result.error}"


@pytest.mark.asyncio
async def test_lint_json_rejects_wrapped_dict() -> None:
    """LLM 经常把 exercises 包成 {exercises: [...]} 对象，schema 要求顶层 array，必须拒。"""
    wrapped = {"exercises": [{
        "exercise_type": "single_choice",
        "prompt": "any prompt",
        "correct_answer": "any",
        "explanation": "any explanation",
        "difficulty": 1,
        "score": 1.0,
    }]}
    result = await LintJsonTool().call(payload=wrapped, schema="exercise")
    assert not result.ok, "lint 不应接受 dict-wrapped 形式"


@pytest.mark.asyncio
async def test_lint_json_rejects_missing_explanation() -> None:
    """缺 explanation 字段必拒。"""
    incomplete = [{
        "exercise_type": "single_choice",
        "prompt": "any prompt",
        "correct_answer": "any",
        "difficulty": 1,
        "score": 1.0,
        # explanation 缺失
    }]
    result = await LintJsonTool().call(payload=incomplete, schema="exercise")
    assert not result.ok
    assert "explanation" in result.error


@pytest.mark.asyncio
async def test_lint_json_accepts_valid_array_from_string() -> None:
    """lint_json 接受 JSON 字符串形式（LLM 输出通常是 ```json\n[...]\n``` fence 后的字符串）。"""
    import json
    raw = json.dumps([{
        "exercise_type": "fill_blank",
        "prompt": "填空题示例",
        "correct_answer": "answer",
        "explanation": "explanation here",
        "difficulty": 2,
        "score": 1.0,
    }])
    result = await LintJsonTool().call(payload=raw, schema="exercise")
    assert result.ok, f"lint 拒字符串: {result.error}"
