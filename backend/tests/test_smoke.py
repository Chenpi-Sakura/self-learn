"""smoke 测试：验证 conftest 可加载（conftest.py 内的函数不会被 pytest 自动收集）。"""
from __future__ import annotations


def test_conftest_loads() -> None:
    """仅验证 conftest 可被 pytest 加载。"""
    assert True
