"""tool.lint_json 行为测试。"""
import pytest
from selflearn.mcp_server.tools.lint_json import lint_json

@pytest.mark.asyncio
async def test_lint_json_valid_array():
    result = await lint_json([{"exercise_type":"single_choice","prompt":"题目至少 5 字符","options":["A","B","C","D"],"correct_answer":"A","explanation":"解析至少 10 字符以上","difficulty":1,"score":1.0}], "exercise")
    assert result["ok"] is True

@pytest.mark.asyncio
async def test_lint_json_missing_field():
    result = await lint_json([{ "exercise_type":"single_choice", "prompt":"题目至少 5 字符", "options":["A","B"], "correct_answer":"A", "difficulty":1, "score":1.0}], "exercise")
    assert result["ok"] is False and "explanation" in result["error"]

@pytest.mark.asyncio
async def test_lint_json_schema_not_found():
    result = await lint_json([], "nonexistent_schema")
    assert result["ok"] is False and "schema_not_found" in result["error"]
