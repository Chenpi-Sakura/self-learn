"""tool.get_recent_scores: 查最近 N 次关卡完成分数。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from selflearn.domain.level_completion import LevelCompletion
from selflearn.infra.db import get_session_factory


async def get_recent_scores(student_id: str, limit: int = 3) -> list[float]:
    """返回 student_id 最近 limit 次 level_completion.score（按 submitted_at DESC）。"""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(LevelCompletion.score)
            .where(LevelCompletion.student_id == student_id)
            .order_by(LevelCompletion.submitted_at.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()
        return [float(s) for s in rows]