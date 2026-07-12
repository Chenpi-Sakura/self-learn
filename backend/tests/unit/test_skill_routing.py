"""@skill 装饰器 + SkillRegistry 路由测试。"""
from __future__ import annotations

import pytest

from selflearn.skills.base import SkillRegistry, skill


@pytest.fixture
def reg() -> SkillRegistry:
    r = SkillRegistry()

    @skill("skill.profile.init")
    async def h() -> str:
        return "ok"

    r.register_handler("skill.profile.init", h)
    return r


def test_register_and_match(reg: SkillRegistry) -> None:
    fn = reg.match("skill.profile.init")
    assert fn is not None


def test_match_miss(reg: SkillRegistry) -> None:
    assert reg.match("nope") is None
