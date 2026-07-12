"""熔断器（v4 § 2.6 降级）。"""
from __future__ import annotations

import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._opened_at is None:
            return CircuitState.CLOSED
        if (time.time() - self._opened_at) >= self.reset_timeout:
            return CircuitState.HALF_OPEN
        return CircuitState.OPEN

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold and self._opened_at is None:
            self._opened_at = time.time()

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def allow(self) -> bool:
        return self.state != CircuitState.OPEN