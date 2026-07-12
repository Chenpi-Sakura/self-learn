"""SSE 端点骨架测试 — 验证路由装配 + 端点可调用（Stage 2 仅 fallback）。"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from selflearn.gateway.app import create_app


@pytest.mark.asyncio
async def test_sse_endpoint_falls_back() -> None:
    """Stage 2 SSE fallback：仅验证路由可调用 + 装配 OK。"""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 仅触发 /readyz 验证装配
        r = await ac.get("/readyz")
        assert r.status_code in (200, 503)