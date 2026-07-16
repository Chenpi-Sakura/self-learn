"""Stage 4 Level schema（spec § 4.3 + ORM level/exercise 真实字段）。"""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ExerciseResponse(BaseModel):
    exercise_id: UUID
    prompt: str
    options: list[str] | None = None
    # ORM 字段叫 exercise_type；schema 字段叫 type（API 出参层命名）
    type: str


class LevelDetailResponse(BaseModel):
    level_id: UUID
    node_id: UUID
    status: str
    exercises: list[ExerciseResponse] = []
    lecture_html: str | None = None  # NULL 时前端显示"该关卡尚无讲义"