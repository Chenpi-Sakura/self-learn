"""LLM 抽象基类 + 数据类（v4 § 1.1 LLM Gateway；Stage 3 加 thinking）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None


@dataclass
class ChatRequest:
    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    stop: list[str] | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    # Stage 3 新增：思考模式
    reasoning: bool = False                # 调用方按需传入
    reasoning_budget: int | None = None    # 思考 token 上限（Claude 类需要显式传）


@dataclass
class ChatChunk:
    delta: str
    finish_reason: str | None = None
    usage: dict[str, object] | None = None
    # Stage 3 新增：思考过程增量（DeepSeek-R1 / 通义 QwQ 在 stream 中同时含 reasoning_content）
    reasoning_delta: str | None = None


class BaseLLMAdapter(ABC):
    """所有 LLM provider 必须实现的接口。"""

    provider_name: str

    @abstractmethod
    async def chat(self, req: ChatRequest) -> str: ...

    @abstractmethod
    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        if False:  # pragma: no cover
            yield ChatChunk(delta="")

    @abstractmethod
    async def health(self) -> bool: ...