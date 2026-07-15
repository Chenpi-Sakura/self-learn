"""Skill loader 行为测试。"""
from __future__ import annotations

import pytest

from selflearn.skills.library import Skill, get, load_all


@pytest.fixture
def tmp_skills_dir(tmp_path, monkeypatch):
    from selflearn.skills import library

    monkeypatch.setattr(library, "SKILLS_DIR", tmp_path)
    return tmp_path


def test_load_skill_with_frontmatter(tmp_skills_dir):
    skill_dir = tmp_skills_dir / "skill.test"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: skill.test\n"
        "description: Use when testing.\n"
        "output_schema: schemas/test.json\n"
        "mcp_prefetch:\n  - tool.a\n  - tool.b\n"
        "mcp_tool_use:\n  - tool.c\n"
        "max_retries: 2\n"
        "---\n\n# Body content\n",
        encoding="utf-8",
    )
    load_all()
    s = get("skill.test")
    assert isinstance(s, Skill)
    assert s.name == "skill.test"
    assert s.mcp_prefetch == ["tool.a", "tool.b"]
    assert s.mcp_tool_use == ["tool.c"]
    assert s.max_retries == 2
    assert "Body content" in s.body


def test_load_skill_missing_name_skipped(tmp_skills_dir):
    skill_dir = tmp_skills_dir / "skill.bad"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: no name\n---\nbody\n",
        encoding="utf-8",
    )
    load_all()
    with pytest.raises(KeyError):
        get("skill.bad")
