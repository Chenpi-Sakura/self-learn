"""ProfileSnapshot: 画像演变快照（Stage 4 spec § 5.3）。

写入触发：关卡完成时由 DirectorAgent 通过 ProfileRepository.apply_delta 调用。
读取触发：前端 GET /api/profile/{student_id}/history。
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    profile: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)  # 'level_completed' | 'manual_edit' | 'build'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
