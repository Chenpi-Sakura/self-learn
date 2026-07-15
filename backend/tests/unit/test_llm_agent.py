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


@pytest.mark.asyncio
async def test_llm_agent_lint_retry(mock_mcp: MagicMock, mock_llm: MagicMock) -> None:
    """验证：lint 失败时重试 max_retries 次后通过。"""
    # lint_json 调用计数器：第一次 fail, 第二次 ok
    lint_call_count = {"n": 0}

    async def lint_side_effect(*args: object, **kwargs: object) -> dict[str, object]:
        lint_call_count["n"] += 1
        if lint_call_count["n"] == 1:
            return {"ok": False, "error": "bad"}
        return {"ok": True, "error": None}

    async def fetch_skill_side_effect(*args: object, **kwargs: object) -> dict[str, object]:
        return {
            "ok": True,
            "name": "skill.test",
            "description": "t",
            "body": "x",
            "output_schema": "schemas/exercise.json",
            "mcp_prefetch": [],
            "mcp_tool_use": [],
            "max_retries": 1,
        }

    async def mcp_router(tool: str, **kwargs: object) -> dict[str, object]:
        if tool == "tool.fetch_skill":
            return await fetch_skill_side_effect(**kwargs)
        if tool == "tool.lint_json":
            return await lint_side_effect(**kwargs)
        return {}

    mock_mcp.call.side_effect = mcp_router

    # 模拟 LLM 第一次坏（空数组 → schema 不需要 options, 但 prompt 不满足 minLength/required 字段），
    # 第二次返回合法 JSON
    valid_exercise = (
        '[{"exercise_type":"single_choice","prompt":"12345",'
        '"options":["a","b"],"correct_answer":"a",'
        '"explanation":"1234567890","difficulty":1,"score":1.0}]'
    )
    llm_call_count = {"n": 0}

    async def chat_side_effect(req: object) -> str:
        llm_call_count["n"] += 1
        if llm_call_count["n"] == 1:
            return "[]"  # bad: 空数组不算合法（schema 校验失败）
        return valid_exercise

    mock_llm.default.return_value.chat.side_effect = chat_side_effect

    agent = LLMAgent(mcp_client=mock_mcp, llm_registry=mock_llm)
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="user", id="test"),
        target=ActorRef(type="skill", id="skill.test"),
        payload={},
    )
    result = await agent.run("skill.test", env)

    assert llm_call_count["n"] == 2, "LLM 应该被调 2 次（1 次重试）"
    assert lint_call_count["n"] == 2, "lint_json 应该被调 2 次"
    assert result == valid_exercise, "最终应返回第二次（合法）的 LLM 输出"
