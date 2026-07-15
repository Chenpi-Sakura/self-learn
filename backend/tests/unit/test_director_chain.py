"""Director 链单测。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from selflearn.agents.director import run_director_chain
from selflearn.core.envelope import Envelope, ActorRef


@pytest.fixture
def mock_agent_review():
    agent = MagicMock()
    agent.run = AsyncMock()
    agent.mcp = MagicMock()
    agent.mcp.call = AsyncMock()
    review = MagicMock()
    review.review_lecture = AsyncMock()
    review.review_exercise_business = AsyncMock()
    review.review_exercise_llm = AsyncMock()
    return agent, review


@pytest.mark.asyncio
async def test_director_chain_happy_path(mock_agent_review):
    agent, review = mock_agent_review
    # MCP 预拉返回
    agent.mcp.call.side_effect = lambda tool, **kwargs: {
        "tool.get_active_node": {"ok": True, "node_id": "n1", "kp_id": "k1", "status": "active", "position": {"x": 0, "y": 0}},
        "tool.get_kp": {"ok": True, "title": "Transformer", "description": "x", "difficulty": 1, "prerequisites": []},
        "tool.get_recent_scores": [],
        "tool.create_level": {"ok": True, "level_id": "L1"},
        "tool.bulk_create_exercises": {"ok": True, "exercise_ids": ["e1"]},
        "tool.update_profile": {"ok": True},
    }.get(tool, {})

    # LLM 调 lecture + exercise
    agent.run.side_effect = [
        "<h1>讲义</h1>",  # lecture_html
        '[{"exercise_type":"single_choice","prompt":"Q","options":["A","B"],"correct_answer":"A","explanation":"xxxxxxxxxxxxxxxxxxxx","difficulty":1,"score":1.0}]',  # exercises
    ]

    review.review_lecture.return_value = MagicMock(verdict="passed")
    review.review_exercise_business.return_value = MagicMock(verdict="passed")
    review.review_exercise_llm.return_value = MagicMock(verdict="passed", score=1.0)

    env = Envelope(action="skill.execute", sender=ActorRef(type="gateway", id="g"),
                    target=ActorRef(type="skill", id="skill.director.start"),
                    payload={"student_id": "s1"})
    result = await run_director_chain(env, agent, review)
    assert result["level_id"] == "L1"
    # verify lecture + exercise 各调 1 次
    assert agent.run.call_count == 2
    # verify create_level + bulk_create + update_profile
    called_tools = [c.args[0] for c in agent.mcp.call.call_args_list]
    assert "tool.create_level" in called_tools
    assert "tool.bulk_create_exercises" in called_tools
    assert "tool.update_profile" in called_tools


@pytest.mark.asyncio
async def test_director_chain_exercise_revision(mock_agent_review):
    """exercise needs_revision → 跑 2 轮。"""
    agent, review = mock_agent_review
    agent.mcp.call.side_effect = lambda tool, **kwargs: {
        "tool.get_active_node": {"ok": True, "node_id": "n1", "kp_id": "k1", "status": "active", "position": {"x": 0, "y": 0}},
        "tool.get_kp": {"ok": True, "title": "T", "description": "x", "difficulty": 1, "prerequisites": []},
        "tool.get_recent_scores": [],
        "tool.create_level": {"ok": True, "level_id": "L1"},
        "tool.bulk_create_exercises": {"ok": True, "exercise_ids": ["e1"]},
        "tool.update_profile": {"ok": True},
    }.get(tool, {})

    agent.run.side_effect = [
        "<h1>讲义</h1>",
        '[{"exercise_type":"single_choice","prompt":"Q1","options":["A","B"],"correct_answer":"A","explanation":"xxxxxxxxxxxxxxxxxxxx","difficulty":1,"score":1.0}]',
        '[{"exercise_type":"single_choice","prompt":"Q2","options":["A","B"],"correct_answer":"B","explanation":"yyyyyyyyyyyyyyyyyyyy","difficulty":1,"score":1.0}]',  # 修订版
    ]
    review.review_lecture.return_value = MagicMock(verdict="passed")
    review.review_exercise_business.return_value = MagicMock(verdict="passed")
    review.review_exercise_llm.side_effect = [
        MagicMock(verdict="needs_revision", suggestions=["改 explanation"], score=0.5),
        MagicMock(verdict="passed", score=1.0),
    ]
    env = Envelope(action="skill.execute", sender=ActorRef(type="gateway", id="g"),
                    target=ActorRef(type="skill", id="skill.director.start"),
                    payload={"student_id": "s1"})
    result = await run_director_chain(env, agent, review)
    # exercise 调了 2 次（revision 0 + 1）
    assert agent.run.call_count == 3  # lecture + exercise×2
    # LLM 审查也跑 2 次
    assert review.review_exercise_llm.call_count == 2
