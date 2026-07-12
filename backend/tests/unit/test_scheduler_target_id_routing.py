"""scheduler target.id 路由改造单测（Rule #13 第四子规则）。

验证：
1. Stage 2 `skill.profile.init`（装饰器路径）继续通过 skill_registry fallback 工作。
2. 任何 target.id 既不在 `_AGENT_FOR_SKILL`（值为非 None）也不在 skill_registry 时
   抛 NotImplementedError，且错误信息明确命名"Agent not yet implemented"。
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


def test_stage3_map_has_five_keys_with_none_placeholders() -> None:
    """Stage 3 路由表必须预占 5 个 target.id，全部为 None（避免 stub）。"""
    expected_keys = {
        "skill.profile.build",
        "skill.plan.generate",
        "skill.exercise.generate",
        "skill.review.exercise",
        "skill.director.start",
    }
    assert expected_keys.issubset(set(_AGENT_FOR_SKILL.keys()))
    for k in expected_keys:
        assert _AGENT_FOR_SKILL[k] is None, f"{k} should be None placeholder"


def test_stage2_fallback_via_skill_registry() -> None:
    """Stage 2 skill.profile.init 仍走 skill_registry 装饰器 fallback。"""
    from selflearn.skills.builtin import ping  # noqa: F401  确保 register() 副作用发生

    # 在主进程中 ping.register() 由 gateway/main 调用触发；测试里手动注册
    ping.register()
    resolved = _resolve_agent_class("skill.profile.init")
    assert resolved is not None, "Stage 2 fallback must resolve via skill_registry"


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
        _resolve_agent_class("skill.director.start")
    msg = str(exc_info.value)
    assert "skill.director.start" in msg
    assert "Agent not yet implemented" in msg
    assert "_AGENT_FOR_SKILL" in msg


def test_get_agent_class_for_skill_returns_none_for_unimplemented() -> None:
    """公开只读 API：未实现键返回 None，不抛错。"""
    assert get_agent_class_for_skill("skill.director.start") is None
    assert get_agent_class_for_skill("totally.unknown") is None


def test_resolve_uses_agent_for_skill_when_populated(monkeypatch: pytest.MonkeyPatch) -> None:
    """正向 case：`_AGENT_FOR_SKILL[target.id]` 非 None 时，_resolve_agent_class 直接返回该类。

    不走装饰器 fallback。验证 Rule #13 主路径在 Agent 类落地后真的能命中。
    """
    from selflearn.agents import scheduler as sched_mod

    class FakeProfileAgent(AbstractAgent):
        agent_id = "fake-profile-01"
        agent_type = "profile"
        skills: list[str] = []  # V1.3 deprecated 字段
        queue = "agent.profile.work"

        async def run(self, env: Envelope) -> Envelope:  # pragma: no cover - not invoked here
            return env

    monkeypatch.setitem(sched_mod._AGENT_FOR_SKILL, "skill.profile.build", FakeProfileAgent)

    resolved = _resolve_agent_class("skill.profile.build")
    assert resolved is FakeProfileAgent, (
        "main path should return the Agent class directly when _AGENT_FOR_SKILL has it"
    )


@pytest.mark.asyncio
async def test_dispatch_instantiates_agent_class_for_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    """正向 dispatch：_AGENT_FOR_SKILL 命中时，dispatch 实例化 Agent class 并调 .run(env)。

    FakeProfileAgent.run 收到 envelope 后返回一个 Envelope，dispatch 应原样回传。
    """
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