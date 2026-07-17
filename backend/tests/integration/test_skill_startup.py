"""验证 7 个 Skill 全部加载。"""
from selflearn.skills.library import load_all, _skill_library

EXPECTED = {
    "skill.profile.build",
    "skill.plan.generate",
    "skill.exercise.generate",
    "skill.review.exercise.business",
    "skill.review.exercise.llm",
    "skill.lecture.generate",
    "skill.director.start",
    # Task 2 added 8th skill：提炼主题流水线
    "skill.resource.extract_topics",
}


def test_seven_skills_loaded() -> None:
    load_all()
    loaded = set(_skill_library.keys())
    missing = EXPECTED - loaded
    assert not missing, f"missing skills: {missing}"
    extra = loaded - EXPECTED
    assert not extra, f"unexpected skills: {extra}"
