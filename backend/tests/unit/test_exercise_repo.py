"""Unit test for ExerciseRepository.bulk_create (Task 10)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from selflearn.infra.repositories.exercise_repo import ExerciseRepository


@pytest.mark.asyncio
async def test_bulk_create_adds_each_item() -> None:
    """bulk_create must call session.add() per item + commit at least once."""
    fake_session = MagicMock()
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()

    repo = ExerciseRepository(fake_session)

    items = [
        {
            "exercise_type": "single_choice",
            "prompt": "Q?",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "x",
            "difficulty": 1,
            "score": 1.5,
        }
    ]
    level_id = UUID("11111111-1111-1111-1111-111111111111")

    # bulk_create returns list[Exercise]; after add+commit it select()s them back.
    fake_session.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )
    )

    result = await repo.bulk_create(level_id, items)
    assert fake_session.add.call_count == 1
    assert fake_session.commit.await_count >= 1
    assert isinstance(result, list)