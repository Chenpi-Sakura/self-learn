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


async def test_review_failed_event_contains_traceback() -> None:
    """ReviewAgent.review 抛异常时，推 FAILED 事件 payload 含 tb（stage=review）。"""
    from unittest.mock import AsyncMock, patch

    from selflearn.progress.stages import ProgressEvent, Stage

    published: list[ProgressEvent] = []

    async def collect(trace_id: str, ev: ProgressEvent) -> None:
        published.append(ev)

    # 直接 patch ToolRegistry.call 抛错（绕过其内置 try/except 包 ToolResult 的兜底）。
    # 注意：patch 路径必须是 selflearn.tools.protocol.ToolRegistry.call（不是 review_agent 模块的），
    # 因为 review_agent.py 用的是 `from ... import ToolRegistry`，访问 .call 会沿 MRO 找。
    async def fake_call(**kwargs: object) -> object:  # noqa: ARG001
        raise ValueError("boom_review_tb")

    with patch("selflearn.tools.protocol.ToolRegistry.call",
               side_effect=fake_call), \
         patch("selflearn.agents.builtin.review_agent.progress_publish",
               new=AsyncMock(side_effect=collect)):
        with pytest.raises(Exception):
            await ReviewAgent().review(
                [
                    {
                        "prompt": "Q?",
                        "exercise_type": "single_choice",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "x",
                        "difficulty": 1,
                        "score": 1.0,
                    },
                ],
                trace_id="rev-tb-test",
            )

    failed = [e for e in published if e.stage == Stage.REVIEW]
    assert failed, "FAILED event 必须推 (stage=REVIEW)"
    assert failed[0].payload.get("tb"), "FAILED payload 必须含 tb 字段"
    assert "boom_review_tb" in failed[0].payload["tb"]