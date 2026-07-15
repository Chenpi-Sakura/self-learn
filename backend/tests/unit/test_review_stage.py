"""ReviewStage 行为测试。"""
from __future__ import annotations
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import pytest
from selflearn.agents.review_stage import LLMReviewResult, ReviewResult, ReviewStage


@pytest.fixture
def mock_deps() -> tuple[ReviewStage, MagicMock, MagicMock]:
    llm = MagicMock()
    mcp = MagicMock()
    mcp.call = AsyncMock()
    return ReviewStage(llm_agent=llm, mcp=mcp), llm, mcp


@pytest.mark.asyncio
async def test_review_lecture_clean_html(mock_deps: tuple[ReviewStage, MagicMock, MagicMock]) -> None:
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"cleaned": "<h1>标题</h1><p>正文</p>", "is_empty": False}
    result = await rs.review_lecture("<h1>标题</h1><p>正文</p>")
    assert result.verdict == "passed"


@pytest.mark.asyncio
async def test_review_lecture_empty_html(mock_deps: tuple[ReviewStage, MagicMock, MagicMock]) -> None:
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"cleaned": "", "is_empty": True}
    result = await rs.review_lecture("")
    assert result.verdict == "rejected"
    assert any(i["rule"] == "not_empty" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_business_passed(mock_deps: tuple[ReviewStage, MagicMock, MagicMock]) -> None:
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": True, "error": None}
    exercises: list[dict[str, Any]] = [
        {"exercise_type": "single_choice", "prompt": "Q1 题目", "options": ["A", "B"], "correct_answer": "A", "explanation": "解析", "difficulty": 1, "score": 1.0},
        {"exercise_type": "single_choice", "prompt": "Q2 题目", "options": ["A", "B"], "correct_answer": "B", "explanation": "解析", "difficulty": 2, "score": 1.0},
        {"exercise_type": "single_choice", "prompt": "Q3 题目", "options": ["A", "B"], "correct_answer": "A", "explanation": "解析", "difficulty": 3, "score": 1.0},
    ]
    result = await rs.review_exercise_business(exercises)
    assert result.verdict == "passed"


@pytest.mark.asyncio
async def test_review_exercise_business_duplicate_prompt(mock_deps: tuple[ReviewStage, MagicMock, MagicMock]) -> None:
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": True, "error": None}
    exercises: list[dict[str, Any]] = [
        {"exercise_type": "single_choice", "prompt": "相同", "options": ["A", "B"], "correct_answer": "A", "explanation": "x" * 20, "difficulty": 1, "score": 1.0},
        {"exercise_type": "single_choice", "prompt": "相同", "options": ["A", "B"], "correct_answer": "B", "explanation": "y" * 20, "difficulty": 2, "score": 1.0},
    ]
    result = await rs.review_exercise_business(exercises)
    assert result.verdict == "needs_fix"
    assert any(i["rule"] == "duplicate_prompt" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_business_options_min(mock_deps: tuple[ReviewStage, MagicMock, MagicMock]) -> None:
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": True, "error": None}
    exercises: list[dict[str, Any]] = [
        {"exercise_type": "single_choice", "prompt": "题目 12345", "options": ["A"], "correct_answer": "A", "explanation": "x" * 20, "difficulty": 1, "score": 1.0},
    ]
    result = await rs.review_exercise_business(exercises)
    assert result.verdict == "needs_fix"
    assert any(i["rule"] == "options_min" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_business_answer_not_in_options(mock_deps: tuple[ReviewStage, MagicMock, MagicMock]) -> None:
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": True, "error": None}
    exercises: list[dict[str, Any]] = [
        {"exercise_type": "single_choice", "prompt": "题目 12345", "options": ["A", "B"], "correct_answer": "X", "explanation": "x" * 20, "difficulty": 1, "score": 1.0},
    ]
    result = await rs.review_exercise_business(exercises)
    assert result.verdict == "rejected"
    assert any(i["rule"] == "answer_not_in_options" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_business_lint_failed(mock_deps: tuple[ReviewStage, MagicMock, MagicMock]) -> None:
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": False, "error": "schema_violation"}
    result = await rs.review_exercise_business([])
    assert result.verdict == "rejected"
    assert any(i["rule"] == "lint_json" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_llm_passed(mock_deps: tuple[ReviewStage, MagicMock, MagicMock]) -> None:
    rs, llm, mcp = mock_deps
    llm.run = AsyncMock(return_value='{"verdict": "passed", "suggestions": [], "issues": []}')
    result = await rs.review_exercise_llm([], "自注意力", "trace-1")
    assert result.verdict == "passed"


@pytest.mark.asyncio
async def test_review_exercise_llm_needs_revision(mock_deps: tuple[ReviewStage, MagicMock, MagicMock]) -> None:
    rs, llm, mcp = mock_deps
    llm.run = AsyncMock(return_value='{"verdict": "needs_revision", "suggestions": ["explanation 错"], "issues": []}')
    result = await rs.review_exercise_llm([], "自注意力", "trace-1")
    assert result.verdict == "needs_revision"
    assert "explanation 错" in result.suggestions
