"""验证 KP 加 source/source_content_md 字段 + resources 表迁移生效（live DB 升 head）。"""
from __future__ import annotations

import pytest
from sqlalchemy import inspect

from selflearn.infra.db import get_session_factory


@pytest.mark.asyncio(loop_scope="session")
async def test_kp_has_source_columns_after_migration() -> None:
    factory = get_session_factory()
    async with factory() as session:
        conn = await session.connection()

        def _cols(sync_conn: object) -> set[str]:
            insp = inspect(sync_conn)
            return {c["name"] for c in insp.get_columns("knowledge_points")}

        cols = await conn.run_sync(_cols)
        assert "source" in cols
        assert "source_content_md" in cols


@pytest.mark.asyncio(loop_scope="session")
async def test_resources_table_exists_after_migration() -> None:
    factory = get_session_factory()
    async with factory() as session:
        conn = await session.connection()

        def _tables(sync_conn: object) -> list[str]:
            insp = inspect(sync_conn)
            return insp.get_table_names()

        tables = await conn.run_sync(_tables)
        assert "resources" in tables
