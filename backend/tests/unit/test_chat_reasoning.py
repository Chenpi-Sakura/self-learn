"""Stage 3: ChatRequest / ChatChunk 增加 reasoning 字段测试。"""
from __future__ import annotations

from selflearn.llm.base import ChatChunk, ChatMessage, ChatRequest


def test_chat_request_default_reasoning_off() -> None:
    req = ChatRequest(messages=[ChatMessage(role="user", content="hi")])
    assert req.reasoning is False
    assert req.reasoning_budget is None


def test_chat_chunk_accepts_reasoning_delta() -> None:
    chunk = ChatChunk(delta="", reasoning_delta="thinking...")
    assert chunk.delta == ""
    assert chunk.reasoning_delta == "thinking..."


def test_chat_chunk_normal_no_reasoning_field() -> None:
    chunk = ChatChunk(delta="hello")
    assert chunk.reasoning_delta is None


import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from selflearn.llm.adapters.mock import MockLLMAdapter
from selflearn.llm.base import ChatRequest, ChatMessage


def test_mock_adapter_chat_stream_yields_reasoning_when_requested() -> None:
    """Stage 3: MockLLMAdapter.chat_stream 在 reasoning=True 时额外 yield reasoning_delta。"""
    adapter = MockLLMAdapter()
    req = ChatRequest(
        messages=[ChatMessage(role="user", content="hi")],
        reasoning=True,
    )

    async def collect() -> list[ChatChunk]:
        chunks: list[ChatChunk] = []
        async for c in adapter.chat_stream(req):
            chunks.append(c)
        return chunks

    chunks = asyncio.run(collect())
    # Mock 至少要 yield 1 个 reasoning_delta + 1 个 delta（reasoning=True）
    assert any(c.reasoning_delta for c in chunks), "expected at least one reasoning_delta chunk"
    assert any(c.delta for c in chunks), "expected at least one content delta chunk"


def test_mock_adapter_chat_stream_no_reasoning_when_off() -> None:
    adapter = MockLLMAdapter()
    req = ChatRequest(
        messages=[ChatMessage(role="user", content="hi")],
        reasoning=False,
    )

    async def collect() -> list[ChatChunk]:
        chunks: list[ChatChunk] = []
        async for c in adapter.chat_stream(req):
            chunks.append(c)
        return chunks

    chunks = asyncio.run(collect())
    assert not any(c.reasoning_delta for c in chunks), "no reasoning_delta expected when reasoning=False"


def test_helper_extracts_json_from_fence() -> None:
    """core.thinking.extract_json_from_fence 处理 LLM 返回的 markdown 代码块。"""
    from selflearn.core.thinking import extract_json_from_fence

    raw = "思考过程...\n```json\n[{\"exercise_type\": \"single_choice\"}]\n```\n"
    parsed = extract_json_from_fence(raw)
    assert parsed == [{"exercise_type": "single_choice"}]


def test_helper_extracts_plain_json() -> None:
    from selflearn.core.thinking import extract_json_from_fence

    parsed = extract_json_from_fence('[{"k": 1}]')
    assert parsed == [{"k": 1}]