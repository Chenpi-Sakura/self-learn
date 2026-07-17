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
        # PEP 479：next(iter(...)) 在空 dict 上抛 StopIteration 会被 coroutine
        # 捕获为 RuntimeError。先取 .get()，失败时用 next(..., None) 而不是 bare next。
        adapter = self._adapters.get(s.llm_default_provider)
        if adapter is not None:
            return adapter
        adapter = next(iter(self._adapters.values()), None)
        if adapter is None:
            raise RuntimeError(
                f"no LLM adapters registered (requested default='{s.llm_default_provider}')"
            )
        return adapter


llm_registry = LLMRegistry()


def _register_default_adapters() -> None:
    """模块加载时按 Settings 注册默认 providers。
    - mock: 始终注册（CI / 离线 fallback）
    - openai_compat: 若 Settings 给了非占位 api_key 就注册
    """
    from selflearn.llm.adapters.mock import MockLLMAdapter
    from selflearn.llm.adapters.openai_compat import OpenAICompatAdapter
    from selflearn.config import get_settings
    from selflearn.core.logging import get_logger

    log = get_logger("llm.registry")
    s = get_settings()

    llm_registry.register(MockLLMAdapter())

    if (s.llm_openai_compat_api_key
            and s.llm_openai_compat_api_key != "sk-replace-me"):
        llm_registry.register(OpenAICompatAdapter(
            base_url=s.llm_openai_compat_base_url,
            api_key=s.llm_openai_compat_api_key,
            model=s.llm_openai_compat_model,
        ))
        log.info("llm.provider_registered", provider="openai_compat")
    else:
        log.warning("llm.provider_skipped", provider="openai_compat", reason="api_key not set")


_register_default_adapters()