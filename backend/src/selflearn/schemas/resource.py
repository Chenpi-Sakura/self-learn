"""资源请求/响应 Pydantic schema（Task 1）。"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResourceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    size_bytes: int
    created_at: datetime


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    content_md: str
    size_bytes: int
    created_at: datetime


class ResourceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=1000)


class ResourceUploadItem(BaseModel):
    id: UUID
    name: str
    size_bytes: int


class ResourceUploadResponse(BaseModel):
    uploaded: list[ResourceUploadItem]
