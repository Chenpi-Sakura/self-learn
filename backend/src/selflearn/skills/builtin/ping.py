"""skill.ping.reply — Stage 2 smoke 唯一 skill。"""
from __future__ import annotations

from selflearn.agents.builtin.ping_agent import PingAgent
from selflearn.agents.registry import AgentInfo
from selflearn.core.envelope import Envelope
from selflearn.skills.base import skill, skill_registry

_agent = PingAgent()


@skill("skill.profile.init", scope="global")
async def skill_profile_init(env: Envelope) -> Envelope:
    return await _agent.run(env)


def register() -> None:
    skill_registry.register_handler("skill.profile.init", skill_profile_init)


def agent_info() -> AgentInfo:
    return AgentInfo(
        agent_id=_agent.agent_id,
        agent_type=_agent.agent_type,
        skills=_agent.skills,
        status="idle",
        queue=_agent.queue,
        max_concurrency=_agent.max_concurrency,
    )