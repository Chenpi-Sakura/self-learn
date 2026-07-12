"""Unit tests for BaseLLMAdapter / ChatRequest / MockLLMAdapter."""
from __future__ import annotations

import pytest

from selflearn.llm.adapters.mock import MockLLMAdapter
from selflearn.llm.base import ChatMessage, ChatRequest


@pytest.mark.asyncio
async def test_mock_chat_returns_text() -> None:
    a = MockLLMAdapter()
    req = ChatRequest(messages=[ChatMessage(role="user", content="ping")])
    out = await a.chat(req)
    assert "pong" in out.lower() or len(out) > 0


@pytest.mark.asyncio
async def test_mock_chat_stream_yields_multiple_chunks() -> None:
    a = MockLLMAdapter()
    req = ChatRequest(messages=[ChatMessage(role="user", content="hi")])
    chunks = [c async for c in a.chat_stream(req)]
    assert len(chunks) >= 2
    full = "".join(c.delta for c in chunks)
    assert full