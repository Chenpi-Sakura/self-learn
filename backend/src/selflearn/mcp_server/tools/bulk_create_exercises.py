"""tool.bulk_create_exercises: 给 Level 批量创建 Exercise 行。"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from selflearn.domain.exercise import Exercise
from selflearn.infra.db import get_session_factory


async def bulk_create_exercises(
    level_id: str,
    exercises: list[dict[str, Any]],
) -> dict[str, Any]:
    """批量创建 Exercise 行。

    每个 ex dict 字段：
      - exercise_type: str（必填）
      - prompt: str（必填）
      - options: list[str]（默认 []）
      - correct_answer: 任意类型（强制 str 化）
      - explanation: str（默认 ""）
      - difficulty: int（默认 1，范围 1-3）
      - score: float（默认 1.0）

    Returns: {"ok": True, "exercise_ids": [...]} 或
             {"ok": False, "error": "..."}
             错误情形：1) invalid_uuid  2) level_id 不存在（FK 失败）
    """
    try:
        level_uuid = UUID(level_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{level_id}"}

    factory = get_session_factory()
    try:
        async with factory() as session:
            ex_ids: list[str] = []
            for ex in exercises:
                ex_row = Exercise(
                    level_id=level_uuid,
                    exercise_type=ex["exercise_type"],
                    prompt=ex["prompt"],
                    options=ex.get("options", []),
                    correct_answer=str(ex["correct_answer"]),
                    explanation=ex.get("explanation", ""),
                    difficulty=int(ex.get("difficulty", 1)),
                    score=float(ex.get("score", 1.0)),
                )
                session.add(ex_row)
                await session.flush()
                ex_ids.append(str(ex_row.exercise_id))
            await session.commit()
            return {"ok": True, "exercise_ids": ex_ids}
    except IntegrityError as e:
        return {"ok": False, "error": f"integrity_error:{e.orig.__class__.__name__}"}
