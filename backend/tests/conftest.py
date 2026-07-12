"""公共测试 fixture。"""
from __future__ import annotations

import pytest


@pytest.fixture
def any_int() -> int:
    return 42
