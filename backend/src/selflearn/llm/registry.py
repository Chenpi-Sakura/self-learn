"""LLM Provider 注册表。"""
from __future__ import annotations

from selflearn.config import get_settings
from selflearn.llm.base import BaseLLMAdapter


class LLMRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, BaseLLMAdapter] = {}

    def register(self, adapter: BaseLLMAdapter) -> None:
        self._adapters[adapter.provider_name] = adapter

    def get(self, name: str) -> BaseLLMAdapter:
        return self._adapters[name]

    def default(self) -> BaseLLMAdapter:
        s = get_settings()
        return self._adapters.get(s.llm_default_provider) or next(iter(self._adapters.values()))


llm_registry = LLMRegistry()