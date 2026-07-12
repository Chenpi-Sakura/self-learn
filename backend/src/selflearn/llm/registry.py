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


def _register_default_adapters() -> None:
    """模块加载时注册默认 provider（mock），保证 worker / 单测都能调 llm_registry.default()。

    通过延迟导入避免 llm 包内部循环依赖。
    """
    from selflearn.llm.adapters.mock import MockLLMAdapter

    llm_registry.register(MockLLMAdapter())


_register_default_adapters()