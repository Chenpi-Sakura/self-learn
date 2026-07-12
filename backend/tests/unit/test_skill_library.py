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