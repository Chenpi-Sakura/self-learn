"""PingAgent — smoke 用：调 1 次 LLM + 回复 pong。"""
from __future__ import annotations

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import Envelope
from selflearn.llm.base import ChatMessage, ChatRequest
from selflearn.llm.registry import llm_registry


class PingAgent(AbstractAgent):
    agent_id = "ping-01"
    agent_type = "ping"
    skills = ["skill.profile.init"]
    queue = "agent.ping.work"
    max_concurrency = 4

    async def run(self, env: Envelope) -> Envelope:
        req = ChatRequest(messages=[ChatMessage(role="user", content="ping")])
        llm = llm_registry.default()
        reply_text = await llm.chat(req)
        return Envelope(
            trace_id=env.trace_id,
            parent_id=env.span_id,
            action="skill.completed",
            sender=env.target,
            target=env.sender,
            payload={"reply": reply_text, "status": "completed"},
        )