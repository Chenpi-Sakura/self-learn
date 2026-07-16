from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class Level(Base):
    __tablename__ = "levels"
    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("map_nodes.node_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generated")
    form: Mapped[str] = mapped_column(String(32), nullable=False, default="exercise")
    lecture_html: Mapped[str | None] = mapped_column(String(50000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("form IN ('exercise','document','mindmap','code')", name="ck_l_form"),
        Index("idx_levels_node", "node_id"),
    )