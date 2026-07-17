"""启动时确保唯一账户存在。

幂等：empty DB 时 INSERT 一行空 Profile；已有 noop。

KEEP_STUDENT 字面量必须与以下 3 处保持完全一致（Task 265 spec § 7）：
  - backend/scripts/purge_test_data.py:24
  - frontend/src/constants/account.ts
  - CLAUDE.md "E2E 测试数据清理" 小节
"""
from __future__ import annotations

from sqlalchemy import select

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory

KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"


async def ensure_keep_student() -> None:
    """幂等。空 DB 启动时 INSERT 一行空 Profile；存在则 noop。"""
    factory = get_session_factory()
    async with factory() as session:
        existing = (
            await session.execute(
                # 简化：用 student_id 而非 profile_id；Profile 表没有基于 student_id 的 PK。
                # 这里用 where 一次 select 即可（profile 表按 student_id 索引）。
                # 由于 Profile 表只允许"一学生一行"（按 § 5 决策），所以 first() 即可。
                select(Profile).where(Profile.student_id == KEEP_STUDENT)
            )
        ).scalars().first()
        if existing is not None:
            return
        session.add(Profile(student_id=KEEP_STUDENT))
        await session.commit()
