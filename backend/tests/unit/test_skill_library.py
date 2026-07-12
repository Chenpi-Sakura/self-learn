import pathlib
import tempfile

import pytest

from selflearn.skills.library import Skill, get, load_all


def test_load_all_reads_skill_markdown(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("selflearn.skills.library.SKILLS_DIR", tmp_path)
    (tmp_path / "skill.test.demo.md").write_text(
        "---\n"
        "name: skill.test.demo\n"
        "description: test\n"
        "---\n\n"
        "# demo body\n\nstep 1\n", encoding="utf-8"
    )
    load_all(tmp_path)
    s = get("skill.test.demo")
    assert isinstance(s, Skill)
    assert s.name == "skill.test.demo"
    assert "# demo body" in s.body
    assert "step 1" in s.body


def test_get_missing_raises() -> None:
    with tempfile.TemporaryDirectory() as td:
        load_all(pathlib.Path(td))
        with pytest.raises(KeyError):
            get("nonexistent")


def test_load_all_loads_real_skills_directory() -> None:
    """Regression: production SKILLS_DIR must resolve to backend/docs/skills/.

    Previously this pointed at the repo root (parents[4]) which silently
    produced 0 Skills at runtime. This test exercises the *real* path
    (no monkeypatch) to catch any future drift in the parents[] math.
    """
    load_all()  # no argument -> uses real SKILLS_DIR
    s = get("skill.exercise.generate")
    assert isinstance(s, Skill)
    assert s.name == "skill.exercise.generate"
    assert s.body.strip() != ""
    assert s.output_schema == "schemas/exercise.schema.json"
    # Sanity: we ship 5 Skill markdown docs; assert at least the one we know.
    from selflearn.skills.library import SKILLS_DIR, _skill_library

    assert SKILLS_DIR.name == "skills"
    assert SKILLS_DIR.parent.name == "docs"
    assert len(_skill_library) >= 5