"""Agent 抽象基类（v4 § 2.1）。

Stage 3 V1.3 兼容性说明（Rule #13 第三子规则）：
- `skills` 类属性仅保留以满足 Stage 2 AgentInfo dataclass 的字段需求；
  Stage 3 起 Agent 类**禁止**在 run() 内通过 `self.skills` 做 Skill 路由
  ——Skill 与 Agent 的绑定完全靠 `Envelope.target.id` ↔
  `docs/skills/<id>.md` 文件名匹配。Agent 在 run() 内需要时直接
  `skill_library.get(...)`，不靠任何静态注册表。
- 字段标 `@deprecated` 仅作类型占位；SkillBasedScheduler 不再读取此字段。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from selflearn.core.envelope import Envelope


class AbstractAgent(ABC):
    agent_id: str
    agent_type: str
    # V1.3 deprecated: Stage 3 起路由仅认 envelope.target.id；保留仅为 Stage 2 AgentInfo 兼容。
    skills: ClassVar[list[str]]
    queue: str
    max_concurrency: int = 1

    @abstractmethod
    async def run(self, env: Envelope) -> Envelope:
        """处理一条入站信封，返回一条出站信封。"""
