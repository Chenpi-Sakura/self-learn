"""提炼主题 POST 触发 + 响应 Pydantic schema（Task 2）。"""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ExtractTopicsRequest(BaseModel):
    selected_resource_ids: list[UUID] = Field(min_length=1, max_length=10)


class ExtractTopicsResponse(BaseModel):
    task_id: str
