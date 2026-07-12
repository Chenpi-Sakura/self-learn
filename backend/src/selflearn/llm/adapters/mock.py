"""MockLLMAdapter — 不走网络，deterministic 输出。"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatRequest


class MockLLMAdapter(BaseLLMAdapter):
    provider_name = "mock"

    async def chat(self, req: ChatRequest) -> str:
        await asyncio.sleep(0)
        last = req.messages[-1].content if req.messages else ""
        return f"mock-reply: ping -> pong ({len(last)} chars)"

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        for part in ("mock-", "reply:", " pong"):
            await asyncio.sleep(0)
            yield ChatChunk(delta=part)
        yield ChatChunk(delta="", finish_reason="stop")

    async def health(self) -> bool:
        return True