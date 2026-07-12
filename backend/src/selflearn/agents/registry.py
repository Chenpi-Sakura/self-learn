"""Agent 注册表（v4 § 2.1.3 Redis-backed，Stage 2 用进程内实现）。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock


@dataclass
class AgentInfo:
    agent_id: str
    agent_type: str
    skills: list[str]
    status: str  # "idle" | "busy" | "offline"
    queue: str
    max_concurrency: int = 1
    last_heartbeat: float = field(default_factory=time.time)


class AgentRegistry:
    """Stage 2 用进程内 dict + RLock；Stage 3 切到 Redis Hash。"""

    def __init__(self) -> None:
        self._agents: dict[str, AgentInfo] = {}
        self._lock = RLock()

    def register(self, info: AgentInfo) -> None:
        with self._lock:
            self._agents[info.agent_id] = info

    def deregister(self, agent_id: str) -> None:
        with self._lock:
            self._agents.pop(agent_id, None)

    def heartbeat(self, agent_id: str) -> None:
        with self._lock:
            info = self._agents.get(agent_id)
            if info:
                info.last_heartbeat = time.time()

    def discover_by_skill(self, skill: str) -> list[AgentInfo]:
        with self._lock:
            return [a for a in self._agents.values() if skill in a.skills]

    def list_alive(self, *, ttl_seconds: float = 30.0) -> list[AgentInfo]:
        with self._lock:
            now = time.time()
            return [a for a in self._agents.values() if (now - a.last_heartbeat) <= ttl_seconds]


agent_registry = AgentRegistry()
