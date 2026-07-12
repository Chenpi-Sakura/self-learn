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