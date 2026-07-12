"""scheduler target.id 路由改造单测（Rule #13 第四子规则）。

验证：
1. Stage 2 `skill.profile.init`（装饰器路径）继续通过 skill_registry fallback 工作。
2. 任何 target.id 既不在 `_AGENT_FOR_SKILL`（值为非 None）也不在 skill_registry 时
   抛 NotImplementedError，且错误信息明确命名"Agent not yet implemented"。
"""
from __future__ import annotations

import pytest

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