"""tool.update_profile: 给指定 student 的 Profile 应用 kb/as 等维度的 delta。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory


async def update_profile(
    student_id: str,
    deltas: dict[str, float],
) -> dict[str, Any]:
    """应用维度 delta + clamp 到 [0, 1] + 写 profile_snapshot（如表存在）。

    Returns: {"ok": True, "dimensions": {...}, "snapshot_id": str | None} 或
             {"ok": False, "error": "profile_not_found"}

    注意：profile_snapshots 是手动 CREATE 的（Stage 4 报告遗留），
    本 tool 防御性写：模块/表缺失时静默 skip。
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Profile).where(Profile.student_id == student_id).limit(1)
        profile = (await session.execute(stmt)).scalars().first()
        if profile is None:
            return {"ok": False, "error": "profile_not_found"}

        # 应用 delta（clamp 到 [0, 1]）
        new_dims: dict[str, float] = dict(profile.dimensions or {})
        for k, v in deltas.items():
            cur = float(new_dims.get(k, 0.5))
            new_dims[k] = max(0.0, min(1.0, cur + v))
        profile.dimensions = new_dims
        profile.last_updated = datetime.now(timezone.utc)
        await session.commit()

        # 写 profile_snapshot（表/模块缺失时静默）
        snapshot_id: str | None = None
        try:
            from selflearn.domain.profile_snapshot import ProfileSnapshot

            snap = ProfileSnapshot(
                student_id=student_id,
                profile=dict(new_dims),
                trigger="level_completed",
            )
            session.add(snap)
            try:
                await session.commit()
                await session.refresh(snap)
                snapshot_id = str(snap.id)
            except Exception:
                await session.rollback()  # 表不存在 — silent skip
        except ImportError:
            pass  # 模块缺失 — silent skip

        return {"ok": True, "dimensions": new_dims, "snapshot_id": snapshot_id}
