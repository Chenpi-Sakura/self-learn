"""端到端 smoke（testcontainers 起 RabbitMQ + Redis；mock LLM + Postgres）。

本测试**不依赖 docker**，纯本地 Agent.run()：
- 验证 PingAgent.run() 能拿到 MockLLMAdapter 并产出 reply
- 校验 reply.action == "skill.completed"，reply.payload 含 "reply" key

依赖 llm_registry 模块加载时已注册 MockLLMAdapter（见 selflearn.llm.registry）。
"""
from __future__ import annotations

import pytest

from selflearn.agents.builtin.ping_agent import PingAgent
from selflearn.core.envelope import ActorRef, Envelope


@pytest.mark.asyncio
async def test_ping_agent_runs_locally() -> None:
    """纯本地端到端：不走 RabbitMQ，直接调 Agent.run() + 校验输出。"""
    agent = PingAgent()
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="test"),
        target=ActorRef(type="skill", id="skill.profile.init"),
        payload={"topic": "smoke"},
    )
    reply = await agent.run(env)
    assert reply.action == "skill.completed"
    assert "reply" in reply.payload