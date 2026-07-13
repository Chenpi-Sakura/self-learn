"""无侵入 AOP 装饰器（spec § 6.4）。"""
from __future__ import annotations

import functools
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from selflearn.observability.hooks import hook_bus

P = ParamSpec("P")
R = TypeVar("R")


def hook(kind: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """包一层 try/except + HookBus.emit，业务异常不被吞。"""
    def deco(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
            t0 = time.perf_counter()
            try:
                result = await fn(*args, **kwargs)
                hook_bus.emit(kind, {
                    "status": "ok",
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                })
                return result
            except Exception as e:
                hook_bus.emit(kind, {
                    "status": "error",
                    "error": str(e),
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                })
                raise
        return wrap
    return deco


def hook_stream(kind: str) -> Callable[..., Callable[..., AsyncIterator[Any]]]:
    """流式版本：包装 AsyncIterator 输出，统计 chunk 数与总延迟。"""
    def deco(fn: Callable[P, AsyncIterator[R]]) -> Callable[P, AsyncIterator[R]]:
        @functools.wraps(fn)
        async def wrap(*args: P.args, **kwargs: P.kwargs) -> AsyncIterator[R]:
            t0 = time.perf_counter()
            n = 0
            try:
                async for chunk in fn(*args, **kwargs):
                    n += 1
                    yield chunk
                hook_bus.emit(kind, {
                    "status": "ok",
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                    "n_chunks": n,
                })
            except Exception as e:
                hook_bus.emit(kind, {"status": "error", "error": str(e), "n_chunks": n})
                raise
        return wrap
    return deco
