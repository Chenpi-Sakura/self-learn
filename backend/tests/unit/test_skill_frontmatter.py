"""验证 5 个老 Skill 的 frontmatter 合法 + 路径正确。"""
import pytest
import yaml
from pathlib import Path
from selflearn.skills.library import load_all, get

SKILLS = [
    "skill.profile.build",
    "skill.plan.generate",
    "skill.exercise.generate",
    "skill.review.exercise.business",
    "skill.director.start",
]


def test_all_skills_loadable():
    load_all()
    for s in SKILLS:
        skill = get(s)
        assert skill.name == s
        assert skill.description.startswith("Use when")
        assert isinstance(skill.mcp_prefetch, list)
        assert isinstance(skill.mcp_tool_use, list)
        assert isinstance(skill.max_retries, int)


def test_skill_files_on_disk():
    from selflearn.skills.library import SKILLS_DIR
    for s in SKILLS:
        path = SKILLS_DIR / s / "SKILL.md"
        assert path.exists(), f"missing: {path}"
