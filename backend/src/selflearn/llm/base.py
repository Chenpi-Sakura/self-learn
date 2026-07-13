"""LLM 抽象基类 + 数据类（v4 § 1.1 LLM Gateway；Stage 3 加 thinking）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from selflearn.observability.decorators import hook_stream


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

    def __init_subclass__(cls, **kwargs: object) -> None:
        """所有 LLM adapter 子类自动给 chat_stream() 装 @hook_stream('llm.call')。

        用 cls.__dict__.get 只取当前类直接定义的版本（不沿父类链拿已装饰版本），
        再用 _is_hook_wrapped 标记防重复包装。
        """
        super().__init_subclass__(**kwargs)
        original = cls.__dict__.get("chat_stream")
        if original is not None and not getattr(original, "_is_hook_wrapped", False):
            wrapped = hook_stream("llm.call")(original)
            wrapped._is_hook_wrapped = True  # type: ignore[attr-defined]
            cls.chat_stream = wrapped  # type: ignore[method-assign]