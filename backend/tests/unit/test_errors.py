"""Unit tests for AppError / ErrorCode."""
from selflearn.core.errors import AppError, ErrorCode


def test_app_error_default_status() -> None:
    err = AppError(ErrorCode.INTERNAL, "boom")
    assert err.http_status == 500


def test_app_error_custom_status() -> None:
    err = AppError(ErrorCode.LLM_RATE_LIMIT, "slow", http_status=429)
    assert err.http_status == 429


def test_error_code_string_values() -> None:
    assert ErrorCode.SKILL_NOT_FOUND.value == "SKILL_NOT_FOUND"