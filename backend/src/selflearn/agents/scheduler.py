"""SkillBasedScheduler 占位（Task 9 完整实现）。"""
from __future__ import annotations

from selflearn.core.envelope import Envelope


async def dispatch(env: Envelope) -> Envelope | None:
    """Task 9：按 env.target.id 匹配 skill，调用 handler。"""
    return None
