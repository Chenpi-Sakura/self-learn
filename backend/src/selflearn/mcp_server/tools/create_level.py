"""tool.create_level: 写一个 Level 行（绑定 MapNode）。"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from selflearn.domain.level import Level
from selflearn.infra.db import get_session_factory


async def create_level(
    node_id: str,
    lecture_html: str | None = None,
) -> dict[str, Any]:
    """给一个 MapNode 创建 Level 行。

    lecture_html 是 spec backlog 中的字段（讲义系统上线后才有），当前 schema
    暂未实现该列——这里 getattr 防御性写入：列不存在则静默忽略。

    Returns: {"ok": True, "level_id": "..."} 或
             {"ok": False, "error": "invalid_uuid:<node_id>"}
    """
    try:
        node_uuid = UUID(node_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{node_id}"}

    factory = get_session_factory()
    async with factory() as session:
        level = Level(node_id=node_uuid, status="generated", form="exercise")
        if lecture_html is not None and hasattr(Level, "lecture_html"):
            setattr(level, "lecture_html", lecture_html)
        session.add(level)
        await session.commit()
        await session.refresh(level)
        return {"ok": True, "level_id": str(level.level_id)}
