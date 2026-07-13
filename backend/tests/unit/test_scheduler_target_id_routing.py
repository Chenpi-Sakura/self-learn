"""scheduler target.id 路由改造单测（Rule #13 第四子规则）。

验证：
1. Stage 2 `skill.profile.init`（装饰器路径）继续通过 skill_registry fallback 工作。
2. Stage 3 五个 target.id（skill.profile.build / skill.plan.generate / skill.exercise.generate
   / skill.review.exercise / skill.director.start）现在映射到真实的 Agent 类。
3. 任何未知的 target.id 抛 NotImplementedError，且错误信息明确命名"Agent not yet implemented"。
"""
from __future__ import annotations

import pytest

from selflearn.agents.base import AbstractAgent
from selflearn.agents.scheduler import (
    _AGENT_FOR_SKILL,
    _resolve_agent_class,
    dispatch,
    get_agent_class_for_skill,
)
from selflearn.core.envelope import ActorRef, Envelope


def test_stage3_map_has_five_keys_with_agent_classes() -> None:
    """Stage 3 路由表必须预占 5 个 target.id，全部映射到 AbstractAgent 子类。"""
    expected_keys = {
        "skill.profile.build",
        "skill.plan.generate",
        "skill.exercise.generate",
        "skill.review.exercise",
        "skill.director.start",
    }
    assert expected_keys.issubset(set(_AGENT_FOR_SKILL.keys()))
    for k in expected_keys:
        cls = _AGENT_FOR_SKILL[k]
        assert cls is not None, f"{k} must be wired to an Agent class"
        assert isinstance(cls, type) and issubclass(cls, AbstractAgent), (
            f"{k} must map to an AbstractAgent subclass"
        )


def test_stage2_fallback_via_skill_registry() -> None:
    """Stage 2 skill.profile.init 仍走 skill_registry 装饰器 fallback。"""
    from selflearn.skills.builtin import ping  # noqa: F401

    ping.register()
    resolved = _resolve_agent_class("skill.profile.init")
    assert resolved is not None


@pytest.mark.asyncio
async def test_dispatch_stage2_skill_profile_init_returns_envelope() -> None:
    """Stage 2 smoke 路径：dispatch(skill.profile.init) 返回 Envelope。"""
    from selflearn.skills.builtin import ping  # noqa: F401
    ping.register()

    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="test"),
        target=ActorRef(type="skill", id="skill.profile.init"),
        payload={"topic": "smoke"},
    )
    reply = await dispatch(env)
    assert reply is not None
    assert reply.action == "skill.completed"
    assert "reply" in reply.payload


def test_unknown_skill_raises_not_implemented() -> None:
    """未实现的 target.id 必须抛 NotImplementedError 且信息明确。"""
    with pytest.raises(NotImplementedError) as exc_info:
        _resolve_agent_class("skill.totally.fictional.skill")
    msg = str(exc_info.value)
    assert "skill.totally.fictional.skill" in msg
    assert "Agent not yet implemented" in msg
    assert "_AGENT_FOR_SKILL" in msg


def test_get_agent_class_for_skill_returns_none_for_unknown() -> None:
    """公开只读 API：未知键返回 None，不抛错。"""
    assert get_agent_class_for_skill("skill.totally.fictional.skill") is None
    assert get_agent_class_for_skill("totally.unknown") is None


def test_resolve_uses_agent_for_skill_when_populated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """正向 case：`_AGENT_FOR_SKILL[target.id]` 非 None 时直接返回该类。"""
    from selflearn.agents import scheduler as sched_mod

    class FakeProfileAgent(AbstractAgent):
        agent_id = "fake-profile-01"
        agent_type = "profile"
        skills: list[str] = []
        queue = "agent.profile.work"

        async def run(self, env: Envelope) -> Envelope:  # pragma: no cover
            return env

    monkeypatch.setitem(sched_mod._AGENT_FOR_SKILL, "skill.profile.build", FakeProfileAgent)
    resolved = _resolve_agent_class("skill.profile.build")
    assert resolved is FakeProfileAgent


@pytest.mark.asyncio
async def test_dispatch_instantiates_agent_class_for_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """正向 dispatch：_AGENT_FOR_SKILL 命中时实例化 Agent class 并调 .run(env)。"""
    from selflearn.agents import scheduler as sched_mod

    captured: dict[str, object] = {}

    class FakeProfileAgent(AbstractAgent):
        agent_id = "fake-profile-01"
        agent_type = "profile"
        skills: list[str] = []
        queue = "agent.profile.work"

        def __init__(self) -> None:
            self.instantiated = True

        async def run(self, env: Envelope) -> Envelope:
            captured["env"] = env
            captured["instantiated"] = self.instantiated
            return Envelope(
                action="skill.completed",
                sender=env.target,
                target=env.sender,
                payload={"ok": True},
            )

    monkeypatch.setitem(sched_mod._AGENT_FOR_SKILL, "skill.profile.build", FakeProfileAgent)

    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="test"),
        target=ActorRef(type="skill", id="skill.profile.build"),
        payload={"k": 1},
    )
    reply = await dispatch(env)

    assert isinstance(reply, Envelope)
    assert reply.action == "skill.completed"
    assert reply.payload == {"ok": True}
    assert captured["env"] is env
    assert captured["instantiated"] is True
