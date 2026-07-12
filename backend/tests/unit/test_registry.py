"""Agent Registry 单元测试 — Stage 2 进程内实现。"""
from __future__ import annotations

import pytest

from selflearn.agents.registry import AgentInfo, AgentRegistry


@pytest.fixture
def reg() -> AgentRegistry:
    return AgentRegistry()


def test_register_and_discover(reg: AgentRegistry) -> None:
    info = AgentInfo(
        agent_id="ping-01",
        agent_type="ping",
        skills=["skill.profile.init"],
        status="idle",
        queue="agent.ping.work",
        max_concurrency=3,
    )
    reg.register(info)
    found = reg.discover_by_skill("skill.profile.init")
    assert len(found) == 1
    assert found[0].agent_id == "ping-01"


def test_heartbeat_updates_timestamp(reg: AgentRegistry) -> None:
    info = AgentInfo(
        agent_id="ping-01",
        agent_type="ping",
        skills=["x"],
        status="idle",
        queue="q",
        max_concurrency=1,
    )
    reg.register(info)
    ts0 = info.last_heartbeat
    reg.heartbeat("ping-01")
    assert info.last_heartbeat >= ts0


def test_discover_empty(reg: AgentRegistry) -> None:
    assert reg.discover_by_skill("nope") == []
