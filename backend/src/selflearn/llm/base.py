"""LLM 抽象基类 + 数据类（v4 § 1.1 LLM Gateway）。"""
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


@dataclass
class ChatChunk:
    delta: str
    finish_reason: str | None = None
    usage: dict[str, object] | None = None


class BaseLLMAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def chat(self, req: ChatRequest) -> str:
        ...

    @abstractmethod
    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        if False:  # pragma: no cover
            yield ChatChunk(delta="")

    @abstractmethod
    async def health(self) -> bool:
        ...