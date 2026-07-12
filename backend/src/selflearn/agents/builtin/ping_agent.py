"""PingAgent — smoke 用：调 1 次 LLM + 回复 pong。

Stage 3 V1.3 兼容性说明（Rule #13 第三子规则）：
- `skills` 类属性仅保留为 Stage 2 AgentInfo dataclass 兼容字段。
- Stage 3 路由（SkillBasedScheduler / SkillLibrary）**不**读取此字段；
  Stage 3 起 Skill 与 Agent 的绑定完全靠 `Envelope.target.id` ↔
  `docs/skills/<id>.md` 文件名匹配。
"""
from __future__ import annotations

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import Envelope
from selflearn.llm.base import ChatMessage, ChatRequest
from selflearn.llm.registry import llm_registry


class PingAgent(AbstractAgent):
    agent_id = "ping-01"
    agent_type = "ping"
    # V1.3 deprecated: Stage 3 路由仅认 envelope.target.id；保留仅为 Stage 2 AgentInfo dataclass 兼容。
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