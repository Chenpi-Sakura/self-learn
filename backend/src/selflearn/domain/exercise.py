from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class Exercise(Base):
    __tablename__ = "exercises"
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False
    )
    exercise_type: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=1.0)

    __table_args__ = (
        CheckConstraint("exercise_type IN ('single_choice','fill_blank','short_answer','code')", name="ck_e_type"),
        CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_e_diff"),
        Index("idx_exercises_level", "level_id"),
    )