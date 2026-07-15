"""Director 链端到端：真 DB + 真 MCP server + 固定 LLM。"""
from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest

from selflearn.agents.core import LLMAgent
from selflearn.agents.director import run_director_chain_with_retry
from selflearn.agents.review_stage import ReviewStage
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.llm.adapters.mock import MockLLMAdapter
from selflearn.llm.registry import LLMRegistry
from selflearn.mcp_client import mcp_client_lifespan


class E2EMCPClient:
    """Use the real MCP client except for skill bodies needed by the LLM fixture."""

    def __init__(self, real_mcp: object) -> None:
        self._real_mcp = real_mcp

    async def call(self, tool: str, **kwargs: object) -> object:
        if tool == "tool.fetch_skill":
            skill_id = str(kwargs["skill_id"])
            return {
                "ok": True,
                "body": skill_id,
                "mcp_prefetch": [],
                "mcp_tool_use": [],
                "max_retries": 0,
                "output_schema": None,
            }
        return await self._real_mcp.call(tool, **kwargs)  # type: ignore[attr-defined]


class DirectorMockAdapter(MockLLMAdapter):
    """Return valid fixed outputs for each Director LLM stage."""

    async def chat(self, req):  # type: ignore[no-untyped-def]
        system = req.messages[0].content
        if system == "skill.review.exercise.llm":
            return json.dumps({"verdict": "passed", "score": 1.0, "suggestions": [], "issues": []})
        if system == "skill.exercise.generate":
            return json.dumps([
                {
                    "exercise_type": "single_choice",
                    "prompt": "2 + 2 = ?",
                    "options": ["3", "4"],
                    "correct_answer": "4",
                    "explanation": "Two plus two equals four.",
                    "difficulty": 1,
                    "score": 1.0,
                }
            ])
        return "<h1>Test lecture</h1><p>Two plus two equals four.</p>"


@pytest.mark.asyncio(loop_scope="session")
async def test_director_e2e_with_mock_llm(
    setup_kp_and_node: tuple[str, UUID, None],
) -> None:
    """Director 通过真 MCP stdio 读写测试数据库并完成整链。"""
    student_id, kp_id, _ = setup_kp_and_node
    node_id = uuid4()
    factory = get_session_factory()
    async with factory() as session:
        session.add(MapNode(
            node_id=node_id,
            student_id=student_id,
            kp_id=kp_id,
            status="active",
            branch_type="main",
            position={"x": 0.0, "y": 0.0},
        ))
        await session.commit()

    registry = LLMRegistry()
    registry.register(DirectorMockAdapter())
    async with mcp_client_lifespan() as real_mcp:
        mcp = E2EMCPClient(real_mcp)
        agent = LLMAgent(mcp, registry)
        review = ReviewStage(agent, mcp)
        env = Envelope(
            action="skill.execute",
            sender=ActorRef(type="gateway", id="integration"),
            target=ActorRef(type="skill", id="skill.director.start"),
            payload={"student_id": student_id},
        )
        result = await run_director_chain_with_retry(env, agent, review)

    assert result["level_id"]
    assert result["exercises_count"] == 1
    assert len(result["exercise_ids"]) == 1
