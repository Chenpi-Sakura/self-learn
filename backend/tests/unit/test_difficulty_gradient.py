"""spec § 5.2 难度梯度：基于最近 N 次关卡完成分数决定 easy/medium/hard。

P5 refactor: `_compute_difficulty` 已从已删除的 `builtin/director_agent.py`
迁移到 `selflearn.agents.director`（Director 链内部使用，见 director.py:18）。
这里作为业务规则单独测试。
"""
from selflearn.agents.director import _compute_difficulty


def test_difficulty_easy_when_low_scores() -> None:
    assert _compute_difficulty([0.3, 0.4, 0.2]) == "easy"


def test_difficulty_medium_when_mid_scores() -> None:
    assert _compute_difficulty([0.6, 0.7]) == "medium"


def test_difficulty_hard_when_high_scores() -> None:
    assert _compute_difficulty([0.9, 0.85, 0.95]) == "hard"


def test_difficulty_medium_when_no_history() -> None:
    assert _compute_difficulty([]) == "medium"