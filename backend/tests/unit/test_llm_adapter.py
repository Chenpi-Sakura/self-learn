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


@pytest.mark.asyncio
async def test_chat_with_reasoning_uses_streaming_and_assembles_content() -> None:
    """reasoning=True 时 chat() 走 chat_stream 路径；reasoning-only chunk 不应炸。"""
    adapter = OpenAICompatAdapter(
        base_url="https://api.test/v1", api_key="sk-x", model="r1"
    )
    # 模拟阿里云兼容 endpoint：先吐 2 个 reasoning-only chunk（无 choices）
    # 然后 1 个 content chunk，最后 [DONE]
    sse_body = (
        'data: {"choices":[],"id":"x"}\n\n'
        'data: {"choices":[],"id":"y"}\n\n'
        'data: {"choices":[{"delta":{"content":"ANSWER"}}]}\n\n'
        'data: [DONE]\n\n'
    ).encode()

    with respx.mock(base_url="https://api.test") as mock:
        mock.post("/v1/chat/completions").mock(
            return_value=Response(
                200,
                headers={
                    "content-type": "text/event-stream",
                    "transfer-encoding": "chunked",
                },
                content=sse_body,
            )
        )
        out = await adapter.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content="hi")],
                reasoning=True,
            )
        )
        assert out == "ANSWER"