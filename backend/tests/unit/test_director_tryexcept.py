"""Director 链 try/except 单测。

P5 refactor: 旧的 `DirectorAgent.run` 包装层（selflearn.agents.builtin.director_agent）
已被删除；Director 链现在直接由 `run_director_chain` + `run_director_chain_with_retry`
暴露。失败时由 `worker.handle_with_dispatch` 捕获 AppError/Exception 并写 trace:status=failed。

本测试覆盖 Director 链失败路径：
1. 链内 MCP 调失败 → run_director_chain 抛 AppError（含原始 error message）。
2. run_director_chain_with_retry 多次失败后抛最后 1 次异常（retry 耗尽兜底）。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from selflearn.agents.director import run_director_chain, run_director_chain_with_retry
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError, ErrorCode


def _make_env(trace_id: str = "trace-try-except") -> Envelope:
    return Envelope(
        action="skill.execute",
        sender=ActorRef(type="test", id="unit"),
        target=ActorRef(type="skill", id="skill.director.start"),
        payload={"student_id": "s1"},
        trace_id=trace_id,
    )


@pytest.mark.asyncio
async def test_director_chain_propagates_app_error_on_mcp_failure() -> None:
    """MCP get_active_node 失败 → Director 链抛 AppError(INTERNAL)。"""
    agent = MagicMock()
    agent.mcp = MagicMock()
    agent.mcp.call = AsyncMock(return_value={"ok": False, "error": "db_unreachable"})
    review = MagicMock()

    env = _make_env("trace-mcp-fail")
    with pytest.raises(AppError) as exc_info:
        await run_director_chain(env, agent, review)

    assert exc_info.value.code == ErrorCode.INTERNAL
    assert "db_unreachable" in exc_info.value.message


@pytest.mark.asyncio
async def test_director_chain_propagates_app_error_on_lecture_rejected() -> None:
    """Lecture 被 review 拒 → 抛 AppError(INTERNAL) + lecture_rejected 标记。"""
    agent = MagicMock()
    agent.mcp = MagicMock()
    agent.mcp.call = AsyncMock(side_effect=lambda tool, **kwargs: {
        "tool.get_active_node": {"ok": True, "node_id": "n1", "kp_id": "k1", "status": "active", "position": {"x": 0, "y": 0}},
        "tool.get_kp": {"ok": True, "title": "T", "description": "x", "difficulty": 1, "prerequisites": []},
        "tool.get_recent_scores": [],
    }.get(tool, {}))
    agent.run = AsyncMock(return_value="<bad>")
    review = MagicMock()
    review.review_lecture = AsyncMock(return_value=MagicMock(verdict="rejected", issues=["no_h1"]))

    env = _make_env("trace-lec-reject")
    with pytest.raises(AppError) as exc_info:
        await run_director_chain(env, agent, review)
    assert exc_info.value.code == ErrorCode.INTERNAL
    assert "lecture_rejected" in exc_info.value.message
    assert "no_h1" in exc_info.value.message


@pytest.mark.asyncio
async def test_retry_does_not_swallow_app_error_after_exhaustion() -> None:
    """retry 包装：3 次都失败 → 抛最后 1 次 AppError（不让 worker 误以为成功）。"""
    agent = MagicMock()
    review = MagicMock()

    boom = AppError(ErrorCode.INTERNAL, "create_level: persistent_db_error")

    async def always_fail(env: Envelope, a: object, r: object) -> dict[str, object]:
        raise boom

    env = _make_env("trace-retry-exhaust")
    with pytest.raises(AppError) as exc_info:
        await run_director_chain_with_retry(
            env, agent, review, run_chain_fn=always_fail, max_attempts=3,
        )
    assert exc_info.value is boom
    assert "create_level: persistent_db_error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_retry_recovers_after_first_failure() -> None:
    """第 1 次失败 → 第 2 次成功（retry 真的生效）。"""
    agent = MagicMock()
    review = MagicMock()
    call_count = {"n": 0}

    async def flaky_chain(env: Envelope, a: object, r: object) -> dict[str, object]:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise AppError(ErrorCode.INTERNAL, "transient_failure")
        return {
            "level_id": "L1",
            "exercise_ids": [],
            "exercises_count": 0,
            "score": 1.0,
            "lecture_html_len": 0,
        }

    env = _make_env("trace-retry-recover")
    result = await run_director_chain_with_retry(
        env, agent, review, run_chain_fn=flaky_chain, max_attempts=3,
    )
    assert result["level_id"] == "L1"
    assert call_count["n"] == 2