"""Profile 相关的 Pydantic 模型（v4 § 4.3 smoke 路由）。"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProfileInitRequest(BaseModel):
    student_id: UUID
    topic: str = Field(min_length=1, max_length=200)


class ProfileInitResponse(BaseModel):
    trace_id: str


class ProfileStatusResponse(BaseModel):
    trace_id: str
    status: str  # "running" | "completed" | "failed"
    reply: str | None = None


class ProfileBuildRequest(BaseModel):
    """Stage 3 /api/profile/build 入参：基础画像 + 维度/标签。"""

    student_id: UUID
    dimensions: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ProfileBuildResponse(BaseModel):
    trace_id: str


class ProfileDetailResponse(BaseModel):
    """Stage 4 spec § 4.1: GET /api/profile/{student_id} 出参。"""

    student_id: UUID
    dimensions: dict[str, float]
    tags: list[str]
    snapshot_count: int
    last_updated_at: datetime | None = None


class ProfileHistoryEntry(BaseModel):
    """Stage 4 spec § 5.3: 单条快照（演变迷你折线图数据点）。"""

    profile: dict[str, float]
    trigger: str
    created_at: datetime


class ProfileHistoryResponse(BaseModel):
    """Stage 4 spec § 5.3: GET /api/profile/{student_id}/history 出参。"""

    student_id: UUID
    snapshots: list[ProfileHistoryEntry] = Field(default_factory=list)