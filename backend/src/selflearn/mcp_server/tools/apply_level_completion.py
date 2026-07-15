"""tool.apply_level_completion: 写 LevelCompletion 行 + 把对应 Level 标记为 completed。"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from selflearn.domain.level import Level
from selflearn.domain.level_completion import LevelCompletion
from selflearn.infra.db import get_session_factory


async def apply_level_completion(
    level_id: str,
    student_id: str,
    score: float,
    answers: dict[str, Any],
) -> dict[str, Any]:
    """写 LevelCompletion 行 + level.status='completed'。

    Returns: {"ok": True, "completion_id": "...", "score": float} 或
             {"ok": False, "error": "invalid_uuid:<level_id>" / "level_not_found"}
    """
    try:
        level_uuid = UUID(level_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{level_id}"}

    factory = get_session_factory()
    async with factory() as session:
        level = await session.get(Level, level_uuid)
        if level is None:
            return {"ok": False, "error": "level_not_found"}

        completion = LevelCompletion(
            level_id=level_uuid,
            student_id=student_id,
            score=score,
            duration_seconds=0,
            answers=answers,
            metrics={"items": len(answers)},
        )
        session.add(completion)
        level.status = "completed"
        await session.commit()
        await session.refresh(completion)
        return {
            "ok": True,
            "completion_id": str(completion.completion_id),
            "score": score,
        }
