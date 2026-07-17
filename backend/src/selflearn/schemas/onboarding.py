"""Onboarding 路由请求/响应 schema。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OnboardingAnswer(BaseModel):
    question_id: str
    choice: str | list[str] | None = None
    free_text: str | None = None


class OnboardingSubmitRequest(BaseModel):
    student_id: str
    answers: list[OnboardingAnswer] = Field(..., min_length=1)


class OnboardingSubmitResponse(BaseModel):
    dimensions: dict[str, float]
    reasoning: str
    snapshot_id: int


class OnboardingQuestionsResponse(BaseModel):
    questions: list[dict[str, Any]]
