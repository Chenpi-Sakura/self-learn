"""ensure_keep_student 幂等性。"""
from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory
from selflearn.infra.seed_account import KEEP_STUDENT, ensure_keep_student


@pytest.mark.asyncio(loop_scope="session")
async def test_ensure_creates_when_empty() -> None:
    """空 DB 时调用后，Profile 表存在 KEEP_STUDENT 行。"""
    factory = get_session_factory()
    async with factory() as s:
        await s.execute(delete(Profile).where(Profile.student_id == KEEP_STUDENT))
        await s.commit()

    await ensure_keep_student()

    async with factory() as s:
        rows = (await s.execute(
            select(Profile).where(Profile.student_id == KEEP_STUDENT)
        )).scalars().all()
    assert len(rows) == 1, "expected exactly one Profile row for KEEP_STUDENT"
    assert rows[0].student_id == KEEP_STUDENT
    # 不假设 dimensions 默认值（可能是 {} 也可能是 None 等）；只断言行存在


@pytest.mark.asyncio(loop_scope="session")
async def test_ensure_idempotent_when_exists() -> None:
    """已有 Profile 行时再次调用，DB 仍只有 1 行（不重复 INSERT）。"""
    factory = get_session_factory()
    await ensure_keep_student()
    await ensure_keep_student()
    await ensure_keep_student()

    async with factory() as s:
        cnt = (await s.execute(
            select(Profile).where(Profile.student_id == KEEP_STUDENT)
        )).scalars().all()
    assert len(cnt) == 1, "ensure_keep_student must be idempotent"
