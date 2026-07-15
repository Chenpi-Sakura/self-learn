"""tool.create_profile: 写 Profile（upsert：存在则覆盖）。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory


async def create_profile(
    student_id: str,
    dimensions: dict[str, Any],
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """upsert Profile：存在则覆盖 dimensions/tags/last_updated，否则新建。

    Returns: {"ok": True, "profile_id", "updated"} （updated=True 表示覆盖路径）
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Profile).where(Profile.student_id == student_id).limit(1)
        existing = (await session.execute(stmt)).scalars().first()
        if existing is not None:
            existing.dimensions = dimensions
            existing.tags = tags or []
            existing.last_updated = datetime.now(timezone.utc)
            await session.commit()
            return {"ok": True, "profile_id": str(existing.profile_id), "updated": True}

        profile = Profile(
            student_id=student_id,
            dimensions=dimensions,
            tags=tags or [],
            last_updated=datetime.now(timezone.utc),
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return {"ok": True, "profile_id": str(profile.profile_id), "updated": False}
