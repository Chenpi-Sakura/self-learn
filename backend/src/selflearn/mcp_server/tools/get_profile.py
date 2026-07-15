"""tool.get_profile: 查 Profile。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory


async def get_profile(student_id: str) -> dict[str, Any]:
    """查 student_id 对应的 Profile。

    Returns: {"ok": True, "profile_id", "dimensions", "tags", "last_updated"} 或
             {"ok": False, "error": "profile_not_found"}
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Profile).where(Profile.student_id == student_id).limit(1)
        profile = (await session.execute(stmt)).scalars().first()
        if profile is None:
            return {"ok": False, "error": "profile_not_found"}
        return {
            "ok": True,
            "profile_id": str(profile.profile_id),
            "dimensions": dict(profile.dimensions or {}),
            "tags": list(profile.tags or []),
            "last_updated": profile.last_updated.isoformat() if profile.last_updated else None,
        }
