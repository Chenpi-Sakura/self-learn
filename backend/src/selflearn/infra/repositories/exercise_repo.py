"""Exercise repository (Task 10; JSONB written via whole-list assignment).

Lifecycle contract: this repository `add`s entities and commits inside the
caller-opened session. Stage 4's Unit of Work will strip the commit out and
let the caller (Director) own transaction boundaries — repository becomes a
pure `add` shim.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from selflearn.domain.exercise import Exercise


class ExerciseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(
        self, level_id: uuid.UUID, items: list[dict[str, Any]]
    ) -> list[Exercise]:
        """Whole-list write: add each item individually; commit once; then select PK-populated Exercise list."""
        for it in items:
            ex = Exercise(
                level_id=level_id,
                exercise_type=it["exercise_type"],
                prompt=it["prompt"],
                options=it.get("options", []),
                correct_answer=it["correct_answer"],
                explanation=it.get("explanation", ""),
                difficulty=it["difficulty"],
                score=it["score"],
            )
            self.session.add(ex)
        await self.session.commit()

        stmt = select(Exercise).where(Exercise.level_id == level_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())