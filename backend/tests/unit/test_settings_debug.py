"""T1: settings.debug 字段验证。"""
from __future__ import annotations


def test_settings_has_debug_field() -> None:
    from selflearn.config import get_settings
    s = get_settings()
    assert hasattr(s, "debug"), "settings.debug 字段缺失"
    assert isinstance(s.debug, bool), "settings.debug 应为 bool"


def test_settings_debug_default_false() -> None:
    from selflearn.config import get_settings
    s = get_settings()
    assert s.debug is False, "settings.debug 默认应 False"