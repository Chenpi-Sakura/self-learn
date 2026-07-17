"""resources CRUD 单测（含非循环 PUT 校验）。

用真实 DB（gateway app + get_session_factory 命中本地 Postgres），
每个测试自清理：上传的资源在结尾软删或直接 hard-delete，避免污染。
"""
from __future__ import annotations

from io import BytesIO
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from selflearn.domain.resource import Resource
from selflearn.gateway.app import create_app
from selflearn.infra.db import get_session_factory


def _client() -> AsyncClient:
    transport = ASGITransport(app=create_app())
    return AsyncClient(transport=transport, base_url="http://test")


async def _hard_delete(resource_id: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(Resource).where(Resource.id == UUID(resource_id)))
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_upload_rejects_non_md() -> None:
    async with _client() as ac:
        files = [("files", ("a.txt", BytesIO(b"x"), "text/plain"))]
        r = await ac.post("/api/resources/upload", files=files)
        assert r.status_code == 400


@pytest.mark.asyncio(loop_scope="session")
async def test_upload_rejects_more_than_4_files() -> None:
    async with _client() as ac:
        files = [
            ("files", (f"a{i}.md", BytesIO(b"# x"), "text/markdown")) for i in range(5)
        ]
        r = await ac.post("/api/resources/upload", files=files)
        assert r.status_code == 400


@pytest.mark.asyncio(loop_scope="session")
async def test_upload_then_list_then_get_then_delete() -> None:
    async with _client() as ac:
        files = [("files", ("笔记.md", BytesIO("# Title\n\nbody".encode()), "text/markdown"))]
        r = await ac.post("/api/resources/upload", files=files)
        assert r.status_code == 200
        body = r.json()
        rid = body["uploaded"][0]["id"]
        try:
            r = await ac.get("/api/resources/list")
            assert any(item["id"] == rid for item in r.json()["items"])

            r = await ac.get(f"/api/resources/{rid}")
            assert r.status_code == 200
            assert r.json()["content_md"] == "# Title\n\nbody"

            # 软删
            r = await ac.delete(f"/api/resources/{rid}")
            assert r.status_code == 204

            r = await ac.get(f"/api/resources/{rid}")
            assert r.status_code == 404
        finally:
            await _hard_delete(rid)


@pytest.mark.asyncio(loop_scope="session")
async def test_put_rejects_cycle() -> None:
    async with _client() as ac:
        files = [("files", ("a/x.md", BytesIO(b"# x"), "text/markdown"))]
        r = await ac.post("/api/resources/upload", files=files)
        rid = r.json()["uploaded"][0]["id"]
        try:
            # 试图改名为自身子路径 a/x.md/y（老名 a/x.md 的子路径，应 400）
            r = await ac.put(f"/api/resources/{rid}", json={"name": "a/x.md/y"})
            assert r.status_code == 400
        finally:
            await _hard_delete(rid)
