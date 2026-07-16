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
    """Return valid fixed outputs for each Director LLM stage.

    - lecture skill: returns a lecture with h2 + callout so outline extractor finds them.
    - exercise skill: returns an exercise whose explanation references the callout
      text, proving lecture_outline was injected into the exercise env and used.
    """

    async def chat(self, req):  # type: ignore[no-untyped-def]
        system = req.messages[0].content
        if system == "skill.review.exercise.llm":
            return json.dumps({"verdict": "passed", "score": 1.0, "suggestions": [], "issues": []})
        if system == "skill.exercise.generate":
            return json.dumps([
                {
                    "exercise_type": "single_choice",
                    "prompt": "缩放因子是？",
                    "options": ["√d_k", "d_k"],
                    "correct_answer": "√d_k",
                    "explanation": "根据讲义核心概念中的 callout，缩放因子是 √d_k，用以稳定 softmax 方差。",
                    "difficulty": 1,
                    "score": 1.0,
                }
            ])
        # skill.lecture.generate：包含 h2 标题 + div.callout，使 lecture_outline
        # 能抽到 sections + callouts，供 exercise 引用。
        return (
            '<h2>核心概念</h2>'
            '<p>self-attention 用 query/key/value 计算注意力权重。</p>'
            '<div class="callout">缩放因子是 √d_k，用以稳定 softmax 方差。</div>'
            '<p>本节到此为止。</p>'
        )


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


@pytest.mark.asyncio(loop_scope="session")
async def test_director_e2e_lecture_outline_explanation_aligned(
    setup_kp_and_node: tuple[str, UUID, None],
) -> None:
    """端到端：lecture_html 写入 + lecture_outline 注入 + exercise explanation 引用 outline。

    跑一次完整 Director 链，再用真 SQLAlchemy session 读 Level + Exercise 行，断言：
    1) level.lecture_html 非空且包含结构化标记（h2 + div.callout）
    2) exercise.explanation 至少 30 字
    3) exercise.explanation 首句包含 lecture 的 callout 文本片段（"缩放因子" / "√d_k"），
       证明 lecture_outline 被注入 exercise env 并被 LLM 实际采用。
    """
    from sqlalchemy import select

    from selflearn.domain.exercise import Exercise
    from selflearn.domain.level import Level

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

    level_id = result["level_id"]
    exercise_ids = result["exercise_ids"]
    assert level_id and len(exercise_ids) == 1

    # DB 断言：lecture_html 写入 + explanation 引用 outline
    async with factory() as session:
        level = await session.get(Level, UUID(level_id))
        assert level is not None, f"Level {level_id} not found"
        assert level.lecture_html, "lecture_html 未写入"
        assert "<h2>" in level.lecture_html, "lecture_html 缺 h2 标题"
        assert 'class="callout"' in level.lecture_html, "lecture_html 缺 callout"

        stmt = select(Exercise).where(Exercise.exercise_id == UUID(exercise_ids[0]))
        ex = (await session.execute(stmt)).scalars().one()
        assert ex.explanation, "exercise.explanation 为空"
        assert len(ex.explanation) >= 30, (
            f"explanation 过短 ({len(ex.explanation)} 字): {ex.explanation!r}"
        )
        # 首句应引用 lecture_outline 中的 callout 文本片段
        first_sentence = ex.explanation.split("。", 1)[0]
        assert ("缩放因子" in first_sentence) or ("√d_k" in first_sentence), (
            f"explanation 首句未引用 lecture_outline: {first_sentence!r}"
        )
