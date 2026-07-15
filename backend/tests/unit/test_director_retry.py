"""Director retry 包装测试。"""
from unittest.mock import MagicMock

import pytest

from selflearn.agents.director import run_director_chain_with_retry
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError, ErrorCode


@pytest.mark.asyncio
async def test_retry_on_db_write_failure_then_success() -> None:
    """第 1 次写库失败 → 第 2 次成功。"""
    agent = MagicMock()
    review = MagicMock()
    call_count = {"n": 0}

    async def fake_chain(env: Envelope, a: object, r: object) -> dict[str, object]:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise AppError(ErrorCode.INTERNAL, "create_level: db_error")
        return {
            "level_id": "L1",
            "exercise_ids": [],
            "exercises_count": 0,
            "score": 1.0,
            "lecture_html_len": 100,
        }

    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="test", id="unit"),
        target=ActorRef(type="skill", id="skill.director.start"),
        payload={"student_id": "s1"},
    )
    result = await run_director_chain_with_retry(
        env, agent, review, run_chain_fn=fake_chain, max_attempts=3,
    )
    assert result["level_id"] == "L1"
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_retry_exhausted_raises_last_error() -> None:
    """3 次都失败抛最后 1 次异常。"""
    agent = MagicMock()
    review = MagicMock()

    async def always_fail(env: Envelope, a: object, r: object) -> dict[str, object]:
        raise AppError(ErrorCode.INTERNAL, "persistent_failure")

    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="test", id="unit"),
        target=ActorRef(type="skill", id="skill.director.start"),
        payload={"student_id": "s1"},
    )
    with pytest.raises(AppError) as exc:
        await run_director_chain_with_retry(
            env, agent, review, run_chain_fn=always_fail, max_attempts=3,
        )
    assert "persistent_failure" in str(exc.value)
