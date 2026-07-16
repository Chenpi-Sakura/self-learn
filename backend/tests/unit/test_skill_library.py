import pathlib
import tempfile

import pytest

from selflearn.skills.library import Skill, get, load_all


def test_load_all_reads_skill_markdown(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """New layout: each Skill is a directory containing SKILL.md.

    Mirrors the fixture pattern in test_skill_loader.py so we test the
    real Skill loading path with the new per-skill directory layout.
    """
    from selflearn.skills import library

    monkeypatch.setattr(library, "SKILLS_DIR", tmp_path)
    skill_dir = tmp_path / "skill.test.demo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: skill.test.demo\n"
        "description: test\n"
        "output_schema: schemas/demo.json\n"
        "---\n\n"
        "# demo body\n\nstep 1\n",
        encoding="utf-8",
    )
    load_all()
    s = get("skill.test.demo")
    assert isinstance(s, Skill)
    assert s.name == "skill.test.demo"
    assert s.output_schema == "schemas/demo.json"
    assert "# demo body" in s.body
    assert "step 1" in s.body


def test_get_missing_raises() -> None:
    with tempfile.TemporaryDirectory() as td:
        load_all(pathlib.Path(td))
        with pytest.raises(KeyError):
            get("nonexistent")


def test_load_all_loads_real_skills_directory() -> None:
    """Regression: production SKILLS_DIR must resolve to backend/skills/<id>/SKILL.md.

    Pins the *real* (no-monkeypatch) path against the layout introduced
    in Task 9 (migration away from docs/skills/*.md). Catches any future
    drift in the parents[] math that would silently produce 0 Skills.
    """
    load_all()  # no argument -> uses real SKILLS_DIR
    s = get("skill.exercise.generate")
    assert isinstance(s, Skill)
    assert s.name == "skill.exercise.generate"
    assert s.body.strip() != ""
    assert s.output_schema == "schemas/exercise.schema.json"
    # Sanity: production path now lives under backend/skills/ (Task 9 layout).
    # SKILLS_DIR = Path(library.py).resolve().parents[3] / "skills"
    # → backend/skills (sibling of backend/src/, NOT inside the python package).
    from selflearn.skills.library import SKILLS_DIR, _skill_library

    assert SKILLS_DIR.name == "skills"
    assert SKILLS_DIR.parent.name == "backend"
    # Project root name (not pytest tmp); whatever the repo is named on disk.
    assert SKILLS_DIR.parent.parent.name != "src"
    assert len(_skill_library) >= 5
