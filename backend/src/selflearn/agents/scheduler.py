"""SkillBasedScheduler（v4 § 2.1.4）。"""
from __future__ import annotations

from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.skills.base import skill_registry


async def dispatch(env: Envelope) -> Envelope | None:
    skill_name = env.target.id
    handler = skill_registry.match(skill_name)
    if handler is None:
        raise AppError(ErrorCode.SKILL_NOT_FOUND, f"no handler for skill: {skill_name}")
    result = await handler(env)
    if isinstance(result, Envelope):
        return result
    return None