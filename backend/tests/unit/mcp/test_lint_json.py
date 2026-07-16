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

@pytest.mark.asyncio
async def test_lint_json_valid_array_with_full_schema_path():
    """兼容 SKILL.md frontmatter 的 'schemas/exercise.schema.json' 写法。"""
    result = await lint_json(
        [{"exercise_type":"single_choice","prompt":"题目至少 5 字符","options":["A","B","C","D"],"correct_answer":"A","explanation":"解析至少 10 字符以上","difficulty":1,"score":1.0}],
        "schemas/exercise.schema.json",
    )
    assert result["ok"] is True

@pytest.mark.asyncio
async def test_lint_json_valid_array_with_schema_no_json():
    """兼容 'exercise.schema'（带 .schema 但不带 .json 后缀）。"""
    result = await lint_json(
        [{"exercise_type":"single_choice","prompt":"题目至少 5 字符","options":["A","B","C","D"],"correct_answer":"A","explanation":"解析至少 10 字符以上","difficulty":1,"score":1.0}],
        "exercise.schema",
    )
    assert result["ok"] is True

@pytest.mark.asyncio
async def test_lint_json_valid_array_with_dot_json_only():
    """兼容 'exercise.schema.json'（带 .json 后缀，无目录前缀）。"""
    result = await lint_json(
        [{"exercise_type":"single_choice","prompt":"题目至少 5 字符","options":["A","B","C","D"],"correct_answer":"A","explanation":"解析至少 10 字符以上","difficulty":1,"score":1.0}],
        "exercise.schema.json",
    )
    assert result["ok"] is True

@pytest.mark.asyncio
async def test_lint_json_valid_fenced_json():
    """兼容 LLM 把 JSON 包在 ```json ... ``` code fence 里的常见输出形式。"""
    fenced = '```json\n[\n  {"exercise_type":"single_choice","prompt":"题目至少 5 字符","options":["A","B","C","D"],"correct_answer":"A","explanation":"解析至少 10 字符以上","difficulty":1,"score":1.0}\n]\n```'
    result = await lint_json(fenced, "schemas/exercise.schema.json")
    assert result["ok"] is True

@pytest.mark.asyncio
async def test_lint_json_invalid_fenced_json_returns_decode_error():
    """fence 内的内容不是 JSON，应返回 json_decode_error。"""
    fenced = '```json\nthis is not json\n```'
    result = await lint_json(fenced, "schemas/exercise.schema.json")
    assert result["ok"] is False
    assert "json_decode_error" in result["error"] or "schema_violation" in result["error"]
