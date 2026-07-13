"""AOP HookBus（spec § 6.3）：进程内 RingBuffer，供 /debug/state 查询。"""
from __future__ import annotations

import collections
import threading
import time
from typing import Any


class HookBus:
    def __init__(self, maxlen: int = 500) -> None:
        self._ring: collections.deque[dict[str, Any]] = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def emit(self, kind: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._ring.append({"ts": time.time(), "kind": kind, **payload})

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._ring)

    def clear(self) -> None:
        with self._lock:
            self._ring.clear()


hook_bus = HookBus()
