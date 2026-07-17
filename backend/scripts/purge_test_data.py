"""一次性清场脚本：保留 `86820161-b0f0-455f-91b4-a69e49445bdf` 一个学生。

- 其他所有 student_id 的 MapNode / Level / Exercise / LevelCompletion / Profile / ProfileSnapshot 全删
- 保留账号的 9 个 NULL-lecture level 也删（让 /start 重新生成讲义）
- 保留账号的 3 个非 NULL lecture level 不动
- 不备份

⚠️ 删前会 print 计数确认；删后 print 剩余计数。
"""
from __future__ import annotations

import asyncio

from sqlalchemy import delete, select, func

from selflearn.domain.exercise import Exercise
from selflearn.domain.level import Level
from selflearn.domain.level_completion import LevelCompletion
from selflearn.domain.map_node import MapNode
from selflearn.domain.profile import Profile
from selflearn.domain.profile_snapshot import ProfileSnapshot
from selflearn.infra.db import get_session_factory

KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"


async def _counts() -> dict[str, int]:
    factory = get_session_factory()
    async with factory() as s:

        async def cnt(stmt) -> int:
            return (await s.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0

        return {
            "students_total": await cnt(select(MapNode.student_id)),
            "levels_total": await cnt(select(Level.level_id)),
            "exercises_total": await cnt(select(Exercise.exercise_id)),
            "completions_total": await cnt(select(LevelCompletion.completion_id)),
            "profiles_total": await cnt(select(Profile.profile_id)),
            "snapshots_total": await cnt(select(ProfileSnapshot.id)),
        }


async def _purge() -> dict[str, int]:
    factory = get_session_factory()
    async with factory() as s:
        # 1. 拿到「要保留的 node_id 集合」= KEEP_STUDENT 的 MapNode
        keep_node_ids = set(
            (await s.execute(
                select(MapNode.node_id).where(MapNode.student_id == KEEP_STUDENT)
            )).scalars().all()
        )

        # ===== 第一刀：删 KEEP_STUDENT 之外的所有学生数据 =====
        other_node_ids_subq = select(MapNode.node_id).where(MapNode.student_id != KEEP_STUDENT)
        other_level_ids_subq = select(Level.level_id).where(Level.node_id.in_(other_node_ids_subq))

        # LevelCompletion / Exercise 通过 level_id 删
        await s.execute(delete(LevelCompletion).where(LevelCompletion.level_id.in_(other_level_ids_subq)))
        await s.execute(delete(Exercise).where(Exercise.level_id.in_(other_level_ids_subq)))
        await s.execute(delete(Level).where(Level.node_id.in_(other_node_ids_subq)))
        await s.execute(delete(MapNode).where(MapNode.student_id != KEEP_STUDENT))
        # profile / snapshot 整表重建
        await s.execute(delete(ProfileSnapshot).where(ProfileSnapshot.student_id != KEEP_STUDENT))
        await s.execute(delete(Profile).where(Profile.student_id != KEEP_STUDENT))

        # ===== 第二刀：删 KEEP_STUDENT 的 NULL-lecture level =====
        my_null_level_subq = (
            select(Level.level_id)
            .where(Level.node_id.in_(keep_node_ids))
            .where(Level.lecture_html.is_(None))
        )
        await s.execute(delete(LevelCompletion).where(LevelCompletion.level_id.in_(my_null_level_subq)))
        await s.execute(delete(Exercise).where(Exercise.level_id.in_(my_null_level_subq)))
        await s.execute(delete(Level).where(Level.lecture_html.is_(None)).where(Level.node_id.in_(keep_node_ids)))

        await s.commit()

    return await _counts()


async def main() -> None:
    print(f"[purge] KEEP_STUDENT = {KEEP_STUDENT}")
    before = await _counts()
    print(f"[purge] before: {before}")
    print("[purge] running DELETE…")
    after = await _purge()
    print(f"[purge] after:  {after}")
    print(f"[purge] delta:  students {before['students_total'] - after['students_total']}, "
          f"levels {before['levels_total'] - after['levels_total']}, "
          f"exercises {before['exercises_total'] - after['exercises_total']}, "
          f"completions {before['completions_total'] - after['completions_total']}, "
          f"snapshots {before['snapshots_total'] - after['snapshots_total']}")


if __name__ == "__main__":
    asyncio.run(main())
