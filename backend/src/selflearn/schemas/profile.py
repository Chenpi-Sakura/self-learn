"""Profile 相关的 Pydantic 模型（v4 § 4.3 smoke 路由）。"""
from __future__ import annotations

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