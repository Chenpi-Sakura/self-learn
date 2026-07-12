"""IflySpark 空壳（Stage 5 凭据到位后实装）。"""
from __future__ import annotations

from collections.abc import AsyncIterator

from selflearn.core.errors import AppError, ErrorCode
from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatRequest


class IflySparkAdapter(BaseLLMAdapter):
    provider_name = "ifly_spark"

    async def chat(self, req: ChatRequest) -> str:
        raise AppError(ErrorCode.LLM_UPSTREAM, "IflySpark not yet implemented (Stage 5)")

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        raise AppError(ErrorCode.LLM_UPSTREAM, "IflySpark not yet implemented (Stage 5)")
        yield ChatChunk(delta="")  # pragma: no cover

    async def health(self) -> bool:
        return False