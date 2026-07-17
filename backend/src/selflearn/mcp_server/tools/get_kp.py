"""tool.get_kp: 查 KnowledgePoint。"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory


async def get_kp(kp_id: str) -> dict[str, Any]:
    """查 KnowledgePoint。

    Returns: {"ok": True, "kp_id", "subject", "title", "description",
              "difficulty", "prerequisites", "source", "source_content_md"}
              或 {"ok": False, "error"}

    Task 6: 透传 source/source_content_md，供 director chain prefetch 注入
            lecture / exercise skill 的 LLM prompt。
    """
    try:
        kp_uuid = UUID(kp_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{kp_id}"}

    factory = get_session_factory()
    async with factory() as session:
        kp = await session.get(KnowledgePoint, kp_uuid)
        if kp is None:
            return {"ok": False, "error": f"kp_not_found:{kp_id}"}
        return {
            "ok": True,
            "kp_id": str(kp.kp_id),
            "subject": kp.subject,
            "title": kp.title,
            "description": kp.description,
            "difficulty": kp.difficulty,
            "prerequisites": list(kp.prerequisites or []),
            "source": kp.source,
            "source_content_md": kp.source_content_md,
        }
