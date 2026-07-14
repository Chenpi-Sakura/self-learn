"""Level 仓储：recent_scores 用于难度梯度计算（spec § 5.2）。"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from selflearn.domain.level_completion import LevelCompletion


class LevelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def recent_scores(self, student_id: UUID, limit: int = 3) -> list[float]:
        """取最近 N 次关卡完成分数（按 submitted_at DESC）。"""
        rs = (
            await self.session.execute(
                select(LevelCompletion.score)
                .where(LevelCompletion.student_id == student_id)
                .order_by(LevelCompletion.submitted_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [float(s) for s in rs]
