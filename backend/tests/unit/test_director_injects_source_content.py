"""验证 get_kp MCP tool（director chain 的 prefetch 入口）返回 source_content_md。

Task 6 目标：
- director chain 调用 `tool.get_kp`（prefetch 拉取 KP）→ 结果需含 source_content_md。
- 该字段会被注入 lecture / exercise skill 的 LLM prompt，让讲义/题目引用蒸馏切片。

本测试只测 MCP tool 的返回值（prefetch 透传的源头）；director chain 的拼装
由已有 test_director_chain.py / test_exercise_skill_outline.py 覆盖。
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.get_kp import get_kp


@pytest.mark.asyncio(loop_scope="session")
async def test_get_kp_includes_source_content_md() -> None:
    """get_kp 必须返回 source_content_md 字段（distill 切片），prefetch 透传用。"""
    kp_id = uuid4()
    factory = get_session_factory()
    sample_md = "x" * 800  # 800 字

    async with factory() as session:
        await session.execute(
            insert(KnowledgePoint).values(
                kp_id=kp_id,
                subject="用户提炼",
                title="T1",
                description="desc",
                difficulty=2,
                prerequisites=[],
                source="01-self-attn.md",
                source_content_md=sample_md,
            )
        )
        await session.commit()

    result = await get_kp(str(kp_id))

    assert result["ok"] is True
    assert result["source"] == "01-self-attn.md"
    assert result["source_content_md"] == sample_md
    assert result["source_content_md"].startswith("x")


@pytest.mark.asyncio(loop_scope="session")
async def test_get_kp_source_fields_nullable(setup_kp_and_node) -> None:
    """未提炼过的 KP（source/source_content_md = NULL）→ 字段仍存在但为 None。"""
    _, kp_id, _ = setup_kp_and_node
    result = await get_kp(str(kp_id))
    assert result["ok"] is True
    assert "source" in result
    assert "source_content_md" in result
    assert result["source"] is None
    assert result["source_content_md"] is None