"""scheduler P5 dispatch 单测。

P5 架构：worker 启动时构造 LLMAgent + ReviewStage，所有 envelope 走
`dispatch(env, agent, review)` 路由到 Director chain。

验证：
1. 必须传 agent + review；不传抛 ValueError（防止静默回退到旧 Agent class）。
2. target.id == 'skill.director.start' 时调 `run_director_chain_with_retry`。
3. 任何其它 target.id 走相同的 Director chain（P5 统一入口），由 Director
   内部按需调子 skill；不要在 dispatch 层做 skill-id 路由判定。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from selflearn.agents.scheduler import dispatch
from selflearn.core.envelope import ActorRef, Envelope


def _make_env(target_id: str = "skill.director.start") -> Envelope:
    return Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="test"),
        target=ActorRef(type="skill", id=target_id),
        payload={"student_id": "s1"},
    )


@pytest.mark.asyncio
async def test_dispatch_requires_agent_and_review() -> None:
    """P5: 不传 agent/review 必须显式抛错（防止裸调回退到旧路径）。"""
    env = _make_env()

    with pytest.raises(ValueError) as exc_info:
        await dispatch(env, agent=None, review=None)
    msg = str(exc_info.value)
    assert "P5 dispatch requires agent and review" in msg
    assert "Legacy dispatch_old has been removed" in msg


@pytest.mark.asyncio
async def test_dispatch_requires_agent_when_review_only() -> None:
    """只传 review 仍必须抛错。"""
    env = _make_env()
    review = MagicMock()

    with pytest.raises(ValueError) as exc_info:
        await dispatch(env, agent=None, review=review)
    assert "P5 dispatch requires agent and review" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dispatch_requires_review_when_agent_only() -> None:
    """只传 agent 仍必须抛错。"""
    env = _make_env()
    agent = MagicMock()

    with pytest.raises(ValueError) as exc_info:
        await dispatch(env, agent=agent, review=None)
    assert "P5 dispatch requires agent and review" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dispatch_director_start_calls_chain_with_retry() -> None:
    """target.id='skill.director.start' → 调 run_director_chain_with_retry。"""
    env = _make_env("skill.director.start")
    agent = MagicMock()
    review = MagicMock()

    fake_result: dict[str, object] = {
        "level_id": "L1",
        "exercise_ids": ["e1"],
        "exercises_count": 1,
        "score": 1.0,
        "lecture_html_len": 100,
    }

    with patch(
        "selflearn.agents.scheduler.run_director_chain_with_retry",
        new=AsyncMock(return_value=fake_result),
    ) as chain_mock:
        reply = await dispatch(env, agent=agent, review=review)

    chain_mock.assert_awaited_once_with(env, agent, review)
    # Director chain 自己负责 publish reply；P5 dispatch 返回 None 让 worker
    # 走 no_reply 分支（reply 由 chain 内部异步 publish）。
    assert reply is None


@pytest.mark.asyncio
async def test_dispatch_other_target_id_still_uses_director_chain() -> None:
    """P5 统一入口：target.id 非 director.start 也走同一条 Director chain
    （Director 内部按 env 内容判断；dispatch 层不做 skill-id 路由）。"""
    env = _make_env("skill.exercise.generate")
    agent = MagicMock()
    review = MagicMock()

    with patch(
        "selflearn.agents.scheduler.run_director_chain_with_retry",
        new=AsyncMock(return_value={"level_id": "L1"}),
    ) as chain_mock:
        reply = await dispatch(env, agent=agent, review=review)

    chain_mock.assert_awaited_once_with(env, agent, review)
    assert reply is None


@pytest.mark.asyncio
async def test_dispatch_propagates_chain_exception() -> None:
    """Director chain 抛异常时 dispatch 不吞，直接向上传。"""
    env = _make_env("skill.director.start")
    agent = MagicMock()
    review = MagicMock()

    boom = RuntimeError("director_chain_exploded")
    with patch(
        "selflearn.agents.scheduler.run_director_chain_with_retry",
        new=AsyncMock(side_effect=boom),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            await dispatch(env, agent=agent, review=review)
    assert exc_info.value is boom