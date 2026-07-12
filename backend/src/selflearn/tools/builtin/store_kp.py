"""tool.store_kp: 写 KnowledgePoint 表（Stage 3 stub 用 SQLAlchemy）。"""
from __future__ import annotations

from typing import Any

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory
from selflearn.tools.protocol import Tool, ToolResult


class StoreKPTool(Tool):
    tool_name = "tool.store_kp"
    description = "插一条 knowledge_points 行，返回 kp_id"

    async def call(self, **kwargs: Any) -> ToolResult:
        subject: str = kwargs["subject"]
        title: str = kwargs["title"]
        description: str = kwargs["description"]
        difficulty: int = kwargs["difficulty"]
        prerequisites: list[str] | None = kwargs.get("prerequisites")
        factory = get_session_factory()
        async with factory() as session:
            kp = KnowledgePoint(
                subject=subject,
                title=title,
                description=description,
                difficulty=difficulty,
                prerequisites=prerequisites or [],
            )
            session.add(kp)
            await session.commit()
            await session.refresh(kp)
            return ToolResult(ok=True, data={"kp_id": str(kp.kp_id)})