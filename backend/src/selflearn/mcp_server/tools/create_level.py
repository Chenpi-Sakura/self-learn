"""tool.create_level: 写一个 Level 行（绑定 MapNode）。"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from selflearn.core.logging import get_logger
from selflearn.domain.level import Level
from selflearn.infra.db import get_session_factory

log = get_logger("create_level")

MAX_LECTURE_HTML_LEN = 50000


async def create_level(
    node_id: str,
    lecture_html: str | None = None,
) -> dict[str, Any]:
    """给一个 MapNode 创建 Level 行。

    lecture_html 是讲义 HTML（nh3 白名单清洗后）。
    若超过 MAX_LECTURE_HTML_LEN，截断并 log warn（prompt 已有 800-1500 字约束，截断是兜底）。

    Returns: {"ok": True, "level_id": "..."} 或
             {"ok": False, "error": "invalid_uuid:<node_id>"}
    """
    try:
        node_uuid = UUID(node_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{node_id}"}

    factory = get_session_factory()
    async with factory() as session:
        truncated_html: str | None = None
        if lecture_html is not None:
            if len(lecture_html) > MAX_LECTURE_HTML_LEN:
                log.warning(
                    "create_level.lecture_html_truncated",
                    orig_len=len(lecture_html),
                    max_len=MAX_LECTURE_HTML_LEN,
                )
                truncated_html = lecture_html[:MAX_LECTURE_HTML_LEN]
            else:
                truncated_html = lecture_html

        level = Level(
            node_id=node_uuid,
            status="generated",
            form="exercise",
            lecture_html=truncated_html,
        )
        session.add(level)
        await session.commit()
        await session.refresh(level)
        return {"ok": True, "level_id": str(level.level_id)}