"""Profile + ProfileSnapshot repository (Stage 4 spec § 5.1 + § 5.3).

apply_delta: 关卡完成后微调 6 维 + 写快照（clamp [0,1]）。
upsert:       ProfileAgent 初始构建画像。
recent_snapshots: T8 history 路由用。
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from selflearn.domain.profile import Profile
from selflearn.domain.profile_snapshot import ProfileSnapshot

_DEFAULT_DIMS: dict[str, float] = {
    "kb": 0.5, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5,
}


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_by_student(self, student_id: UUID) -> Profile | None:
        rs = await self.session.execute(
            select(Profile).where(Profile.student_id == student_id)
        )
        return rs.scalar_one_or_none()

    async def upsert(
        self,
        student_id: UUID,
        profile: dict[str, float],
        tags: list[str] | None = None,
    ) -> Profile:
        existing = await self._get_by_student(student_id)
        if existing is not None:
            existing.dimensions = profile
            if tags is not None:
                existing.tags = tags
            await self.session.flush()
            return existing
        new = Profile(
            profile_id=uuid4(),
            student_id=student_id,
            dimensions=profile,
            tags=tags or [],
        )
        self.session.add(new)
        await self.session.flush()
        return new

    async def apply_delta(
        self,
        student_id: UUID,
        delta: dict[str, float],
        trigger: str = "level_completed",
    ) -> dict[str, float]:
        """应用 delta 到现有 dimensions（clamp [0,1]）并写 snapshot。"""
        profile = await self.upsert(student_id, dict(_DEFAULT_DIMS))
        new_dims: dict[str, Any] = dict(profile.dimensions)
        for k, v in delta.items():
            if k in new_dims and isinstance(new_dims[k], (int, float)) and isinstance(v, (int, float)):
                new_dims[k] = max(0.0, min(1.0, float(new_dims[k]) + float(v)))
        profile.dimensions = new_dims  # JSONB 整体替换（不可就地 mutate）
        snapshot = ProfileSnapshot(
            student_id=student_id, profile=new_dims, trigger=trigger
        )
        self.session.add(snapshot)
        await self.session.flush()
        return new_dims

    async def recent_snapshots(
        self,
        student_id: UUID,
        limit: int = 10,
    ) -> list[ProfileSnapshot]:
        rs = await self.session.execute(
            select(ProfileSnapshot)
            .where(ProfileSnapshot.student_id == student_id)
            .order_by(ProfileSnapshot.created_at.desc())
            .limit(limit)
        )
        return list(rs.scalars().all())
