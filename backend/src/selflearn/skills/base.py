"""@skill 装饰器 + 路由表。"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


SkillHandler = Callable[..., Awaitable[Any]]


def skill(name: str, *, scope: str = "global") -> Callable[[SkillHandler], SkillHandler]:
    def deco(fn: SkillHandler) -> SkillHandler:
        fn.__skill_name__ = name  # type: ignore[attr-defined]
        fn.__skill_scope__ = scope  # type: ignore[attr-defined]
        return fn

    return deco


class SkillRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, SkillHandler] = {}

    def register_handler(self, name: str, handler: SkillHandler) -> None:
        self._handlers[name] = handler

    def match(self, name: str) -> SkillHandler | None:
        return self._handlers.get(name)


skill_registry = SkillRegistry()
