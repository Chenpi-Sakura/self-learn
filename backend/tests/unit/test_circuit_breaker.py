"""Unit tests for CircuitBreaker."""
from __future__ import annotations

import time

from selflearn.llm.circuit_breaker import CircuitBreaker, CircuitState


def test_starts_closed() -> None:
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=1.0)
    assert cb.state == CircuitState.CLOSED


def test_opens_after_threshold() -> None:
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=1.0)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_half_open_after_timeout() -> None:
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.05)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.06)
    assert cb.state == CircuitState.HALF_OPEN


def test_success_closes() -> None:
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.05)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.06)
    cb.record_success()
    assert cb.state == CircuitState.CLOSED