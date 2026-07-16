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
async def test_dispatch_other_target_id_logs_warning_and_returns_none() -> None:
    """target.id 既非 director.start 也非 profile.build/plan.generate →
    不进 Director chain、不调 LLMAgent，只打 warning log 然后 return None
    （Stage 2 fallback / 未知 skill，不阻塞 worker）。
    """
    env = _make_env("skill.exercise.generate")
    agent = MagicMock()
    agent.run = AsyncMock()
    review = MagicMock()

    with patch(
        "selflearn.agents.scheduler.run_director_chain_with_retry",
        new=AsyncMock(),
    ) as chain_mock:
        reply = await dispatch(env, agent=agent, review=review)

    chain_mock.assert_not_awaited()
    agent.run.assert_not_awaited()
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


@pytest.mark.asyncio
async def test_dispatch_routes_profile_build_to_llmagent() -> None:
    """target.id='skill.profile.build' → 调 agent.run(target, env)，不走 Director chain。

    profile.build 是单步 Skill（不需要 review），直接 LLMAgent.run 出 profile
    HTML 即可；gateway POST /api/profile/build 才会发这个 envelope。
    """
    env = _make_env("skill.profile.build")
    agent = MagicMock()
    agent.run = AsyncMock(return_value="<html>profile</html>")
    review = MagicMock()

    with patch(
        "selflearn.agents.scheduler.run_director_chain_with_retry",
        new=AsyncMock(),
    ) as chain_mock:
        reply = await dispatch(env, agent=agent, review=review)

    # profile.build 必须走 LLMAgent.run，绝不能进 Director chain
    chain_mock.assert_not_awaited()
    agent.run.assert_awaited_once_with("skill.profile.build", env)
    # Profile skill 只产出 HTML 字符串，dispatch 不关心；前端轮询状态。
    assert reply is None


@pytest.mark.asyncio
async def test_dispatch_routes_plan_generate_to_llmagent() -> None:
    """target.id='skill.plan.generate' → 调 agent.run(target, env)，不走 Director chain。

    plan.generate 是单步 Skill（不需要 review），直接 LLMAgent.run 出 node list；
    gateway POST /api/map/generate 才会发这个 envelope。
    """
    env = _make_env("skill.plan.generate")
    agent = MagicMock()
    agent.run = AsyncMock(return_value='[{"node_id":"n1"}]')
    review = MagicMock()

    with patch(
        "selflearn.agents.scheduler.run_director_chain_with_retry",
        new=AsyncMock(),
    ) as chain_mock:
        reply = await dispatch(env, agent=agent, review=review)

    # plan.generate 必须走 LLMAgent.run，绝不能进 Director chain
    chain_mock.assert_not_awaited()
    agent.run.assert_awaited_once_with("skill.plan.generate", env)
    assert reply is None