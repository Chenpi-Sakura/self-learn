"""Unit tests for LLMRegistry."""
from __future__ import annotations

from selflearn.llm.adapters.mock import MockLLMAdapter
from selflearn.llm.registry import LLMRegistry


def test_register_and_get() -> None:
    r = LLMRegistry()
    a = MockLLMAdapter()
    r.register(a)
    assert r.get("mock") is a


def test_default_falls_back_to_first() -> None:
    r = LLMRegistry()
    a = MockLLMAdapter()
    r.register(a)
    assert r.default() is a