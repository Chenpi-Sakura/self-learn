"""Onboarding 题库 JSON 契约测试 — 防止后续改题库破坏 LLM skill prompt 输入。"""
from __future__ import annotations

import json
from pathlib import Path

QUESTION_FILE = Path(__file__).resolve().parents[2] / "src" / "selflearn" / "data" / "onboarding_questions.json"  # 从 backend/ 跑
SHORT_KEYS = {"kb", "vp", "as", "ge", "ept", "fd"}


def _load() -> list[dict]:
    return json.loads(QUESTION_FILE.read_text(encoding="utf-8"))


def test_total_count_between_7_and_8() -> None:
    qs = _load()
    assert 7 <= len(qs) <= 8, f"题数应在 7-8，实际 {len(qs)}"


def test_all_six_dimensions_covered_as_hint() -> None:
    qs = _load()
    hinted = {q.get("dimension_hint") for q in qs if "dimension_hint" in q}
    missing = SHORT_KEYS - hinted
    assert not missing, f"6 维未被 dimension_hint 覆盖: {missing}"


def test_last_question_is_open_type() -> None:
    qs = _load()
    last = qs[-1]
    assert last["type"] == "open", f"最后一题应 open，实际 {last['type']}"
    assert "placeholder" in last and last["placeholder"], "开放题需 placeholder"


def test_single_questions_have_options() -> None:
    qs = _load()
    for q in qs:
        if q["type"] in ("single", "multi"):
            assert "options" in q, f"题 {q['id']} 缺 options"
            assert len(q["options"]) >= 3, f"题 {q['id']} 选项数应 >= 3"
            ids = [o["id"] for o in q["options"]]
            assert len(ids) == len(set(ids)), f"题 {q['id']} 选项 id 重复"


def test_all_ids_unique() -> None:
    qs = _load()
    ids = [q["id"] for q in qs]
    assert len(ids) == len(set(ids)), f"题 id 重复: {ids}"