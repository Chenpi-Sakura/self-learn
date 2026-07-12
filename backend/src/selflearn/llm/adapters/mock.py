"""Mock LLM Adapter（Stage 3: 支持 reasoning 字段）。"""
from __future__ import annotations

from collections.abc import AsyncIterator

from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatRequest


class MockLLMAdapter(BaseLLMAdapter):
    """不走网络；reasoning=True 时额外 yield reasoning_delta。"""

    provider_name = "mock"

    async def chat(self, req: ChatRequest) -> str:
        return f"mock-reply: {req.messages[-1].content[:32]} -> pong"

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        if req.reasoning:
            yield ChatChunk(delta="", reasoning_delta="mock-think: ...", finish_reason=None)
            yield ChatChunk(delta="", reasoning_delta="  planning next steps", finish_reason=None)
        yield ChatChunk(delta="mock chunk 1", finish_reason=None)
        yield ChatChunk(delta="mock chunk 2", finish_reason=None)
        yield ChatChunk(delta="", finish_reason="stop")

    async def health(self) -> bool:
        return True
