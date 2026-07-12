"""Unit tests for ReviewAgent (Task 10)."""
from __future__ import annotations

import pytest

from selflearn.agents.builtin.review_agent import ReviewAgent

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _load_skills() -> None:
    from selflearn.skills.library import load_all

    load_all()  # Worker does this on startup; tests need it for skill.review.exercise


async def test_review_passes_valid_exercises() -> None:
    exercises = [
        {
            "prompt": f"Question number {i}?",
            "exercise_type": "single_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "x",
            "difficulty": d,
            "score": 1.0,
        }
        for i, d in enumerate([1, 2, 3])
    ]
    review = await ReviewAgent().review(exercises)
    assert review.verdict == "passed"
    assert review.score == pytest.approx(1.0)


async def test_review_flags_duplicate_prompts() -> None:
    exercises = [
        {
            "prompt": "Duplicate question prompt?",
            "exercise_type": "single_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "x",
            "difficulty": 1,
            "score": 1.0,
        },
        {
            "prompt": "Duplicate question prompt?",
            "exercise_type": "single_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "x",
            "difficulty": 2,
            "score": 1.0,
        },
    ]
    review = await ReviewAgent().review(exercises)
    assert review.verdict == "needs_fix"
    assert any(i["rule"] == "duplicate_prompt" for i in review.issues)


async def test_review_rejects_choice_with_no_matching_answer() -> None:
    exercises = [
        {
            "prompt": "What is the answer?",
            "exercise_type": "single_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "Z",
            "explanation": "x",
            "difficulty": 1,
            "score": 1.0,
        },
    ]
    review = await ReviewAgent().review(exercises)
    assert review.verdict in ("rejected", "needs_fix")
    assert any(
        "answer" in (i.get("rule") or "") or "options" in (i.get("rule") or "")
        for i in review.issues
    )