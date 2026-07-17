from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    kp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    prerequisites: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_content_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_kp_difficulty"),
        Index("idx_kp_subject", "subject"),
    )