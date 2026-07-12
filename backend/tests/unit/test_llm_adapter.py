"""Unit tests for OpenAICompatAdapter (respx-mocked)."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from selflearn.llm.adapters.openai_compat import OpenAICompatAdapter
from selflearn.llm.base import ChatMessage, ChatRequest


@pytest.mark.asyncio
async def test_chat_completion_success() -> None:
    adapter = OpenAICompatAdapter(
        base_url="https://api.test/v1", api_key="sk-x", model="test-model"
    )
    with respx.mock(base_url="https://api.test") as mock:
        mock.post("/v1/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {"content": "hello"}}]})
        )
        out = await adapter.chat(
            ChatRequest(messages=[ChatMessage(role="user", content="hi")])
        )
        assert out == "hello"


@pytest.mark.asyncio
async def test_health_ok() -> None:
    adapter = OpenAICompatAdapter(
        base_url="https://api.test/v1", api_key="sk-x", model="x"
    )
    with respx.mock(base_url="https://api.test") as mock:
        mock.get("/v1/models").mock(return_value=Response(200, json={"data": []}))
        assert await adapter.health() is True