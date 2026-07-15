"""LLMAgent 行为测试。"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from selflearn.agents.core import LLMAgent
from selflearn.core.envelope import ActorRef, Envelope


@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    mcp.call = AsyncMock()
    return mcp


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.default.return_value.chat = AsyncMock()
    return llm


@pytest.mark.asyncio
async def test_llm_agent_runs_skill_with_prefetch(mock_mcp, mock_llm):
    """验证：调 fetch_skill → prefetch → 拼 prompt → 调 LLM。"""
    mock_mcp.call.side_effect = lambda tool, **kwargs: {
        "tool.fetch_skill": {
            "ok": True,
            "name": "skill.test",
            "description": "test",
            "body": "Title: {tool_get_kp}",
            "output_schema": None,
            "mcp_prefetch": ["tool_get_kp"],
            "mcp_tool_use": [],
            "max_retries": 0,
        },
        "tool_get_kp": {
            "ok": True,
            "title": "Transformer",
            "description": "x",
        },
    }[tool]

    mock_llm.default.return_value.chat.return_value = "ok"

    agent = LLMAgent(mcp_client=mock_mcp, llm_registry=mock_llm)
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="user", id="test"),
        target=ActorRef(type="skill", id="skill.test"),
        payload={"title": "自注意力"},
    )
    result = await agent.run("skill.test", env)

    assert result == "ok"
    assert any(c.args[0] == "tool.fetch_skill" for c in mock_mcp.call.call_args_list)
    assert any(c.args[0] == "tool_get_kp" for c in mock_mcp.call.call_args_list)
    chat_call = mock_llm.default.return_value.chat.call_args
    messages = chat_call[0][0].messages
    assert "Transformer" in messages[0].content
