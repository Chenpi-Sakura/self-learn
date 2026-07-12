"""Agent 抽象基类（v4 § 2.1）。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from selflearn.core.envelope import Envelope


class AbstractAgent(ABC):
    agent_id: str
    agent_type: str
    skills: list[str]
    queue: str
    max_concurrency: int = 1

    @abstractmethod
    async def run(self, env: Envelope) -> Envelope:
        """处理一条入站信封，返回一条出站信封。"""
