from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class MapNode(Base):
    __tablename__ = "map_nodes"
    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    kp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_points.kp_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    branch_type: Mapped[str] = mapped_column(String(32), nullable=False, default="main")
    position: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False, default=lambda: {"x": 0.0, "y": 0.0})
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('active','sleeping','completed','locked')", name="ck_mn_status"),
        CheckConstraint("branch_type IN ('main','interest')", name="ck_mn_branch"),
        Index("idx_map_nodes_student_status", "student_id", "status"),
    )