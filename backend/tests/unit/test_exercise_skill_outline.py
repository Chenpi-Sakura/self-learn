"""Director chain 注入 lecture_outline 到 exercise env + exercise SKILL.md 引用要求。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.agents.director import run_director_chain


@pytest.mark.asyncio
async def test_director_chain_injects_lecture_outline_into_exercise_env() -> None:
    """lecture 跑完后，exercise 收到的 env.payload 应含 lecture_outline。"""
    # mock lecture LLM 输出（已 lint 后的 HTML，含 h2 + callout + example）
    lecture_html = (
        "<h2>核心概念</h2>"
        "<p>Self-attention 通过 query-key 内积...</p>"
        '<div class="callout">缩放因子是 √d_k</div>'
        '<div class="example">d_model=512, d_k=64 时</div>'
    )
    exercises = [
        {
            "exercise_type": "single_choice",
            "prompt": "缩放因子是？",
            "options": ["√d_k", "d_k", "d_model", "1"],
            "correct_answer": "√d_k",
            "explanation": "如讲义中所言...",
            "difficulty": 2,
            "score": 1.5,
        }
    ]

    # mock agent：lecture + exercise 两次调用
    agent = MagicMock()
    agent.mcp = MagicMock()
    agent.mcp.call = AsyncMock(side_effect=[
        # get_active_node
        {"ok": True, "node_id": "n1", "kp_id": "k1"},
        # get_kp
        {"ok": True, "kp_id": "k1", "title": "self-attention"},
        # get_recent_scores
        [],
        # create_level
        {"ok": True, "level_id": "l1"},
        # bulk_create_exercises
        {"ok": True, "exercise_ids": ["e1"]},
        # update_profile
        {"ok": True},
    ])
    agent.run = AsyncMock(side_effect=[lecture_html, exercises])

    review = MagicMock()
    review.review_lecture = AsyncMock(return_value=MagicMock(verdict="passed", issues=[], cleaned=None))
    review.review_exercise_business = AsyncMock(return_value=MagicMock(verdict="passed", issues=[]))
    review.review_exercise_llm = AsyncMock(return_value=MagicMock(
        verdict="passed", score=1.0, suggestions=[], issues=[],
    ))

    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="test", id="t"),
        target=ActorRef(type="skill", id="skill.director.start"),
        payload={"student_id": "s1", "node_id": "n1"},
    )

    await run_director_chain(env, agent, review)

    # 关键断言：agent.run 第二次调用（exercise）的 env 含 lecture_outline
    assert agent.run.call_count == 2
    exercise_env: Envelope = agent.run.call_args_list[1].args[1]
    assert "lecture_outline" in exercise_env.payload
    outline = exercise_env.payload["lecture_outline"]
    assert "核心概念" in outline["sections"]
    assert "缩放因子是 √d_k" in outline["callouts"]
    assert any("d_model=512" in e for e in outline["examples"])


def test_exercise_skill_md_requires_explanation_reference_lecture_outline() -> None:
    """exercise SKILL.md 必须明确要求 explanation 引用 lecture_outline + source_content_md。"""
    skill_path = Path(__file__).resolve().parents[2] / "skills" / "skill.exercise.generate" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    # 必须显式提到 lecture_outline
    assert "lecture_outline" in text
    # 必须明确要求 explanation 引用
    assert re.search(r"explanation.*引用.*lecture_outline", text, re.DOTALL) is not None
    # Task 6：exercise prefetch 现在含 tool.get_kp（用于 source_content_md 蒸馏切片引用）
    assert "tool.get_kp" in text
    # Task 6：必须要求 explanation 引用 source_content_md
    assert "source_content_md" in text
