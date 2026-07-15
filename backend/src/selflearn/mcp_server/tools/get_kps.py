"""tool.get_kps: 批量查 KnowledgePoint（默认 5 条）。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory


async def get_kps(limit: int = 5) -> list[dict[str, Any]]:
    """查 KnowledgePoint 前 N 条。

    Returns: list of {"kp_id", "title", "description", "difficulty"}
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(KnowledgePoint).limit(limit)
        kps = (await session.execute(stmt)).scalars().all()
        return [
            {
                "kp_id": str(k.kp_id),
                "title": k.title,
                "description": k.description,
                "difficulty": k.difficulty,
            }
            for k in kps
        ]
