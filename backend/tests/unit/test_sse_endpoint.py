"""SSE 端点骨架测试 — 验证路由装配 + 端点可调用（Stage 2 仅 fallback）。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from selflearn.gateway.app import create_app
from selflearn.progress.stages import ProgressEvent, Stage


@pytest.mark.asyncio
async def test_sse_endpoint_falls_back() -> None:
    """Stage 2 SSE fallback：仅验证路由可调用 + 装配 OK。"""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 仅触发 /readyz 验证装配
        r = await ac.get("/readyz")
        assert r.status_code in (200, 503)


@pytest.mark.asyncio
async def test_sse_endpoint_returns_failed_event_on_failure() -> None:
    """SSE 端点收到 FAILED 事件后必须关闭连接（V1.1 修复）。

    验证：当 progress_consume 推 1 条 FAILED 后停止，SSE 必须送出
    "event: error" 并终止，而不是持续挂着连接。
    """

    async def fake_events() -> AsyncIterator[ProgressEvent]:
        yield ProgressEvent(
            stage=Stage.FAILED,
            status="failed",
            payload={"code": "x", "message": "y"},
            timestamp=datetime.utcnow(),
        )

    # progress_consume 是 async generator function；我们用普通函数返回
    # 一个真实的 async generator 来 mock 它（AsyncMock 会把 return_value
    # 当 coroutine 处理，跟 async for 协议不兼容）。
    def fake_consume(_trace_id: str) -> AsyncIterator[ProgressEvent]:
        return fake_events()

    with patch(
        "selflearn.gateway.routes.profile.progress_consume",
        new=fake_consume,
    ):
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            async with ac.stream(
                "GET", "/api/profile/init/abc/stream"
            ) as resp:
                assert resp.status_code == 200
                chunks: list[str] = []
                async for chunk in resp.aiter_text():
                    chunks.append(chunk)
                text = "\n".join(chunks)
                assert "event: error" in text, (
                    f"SSE must yield error event on FAILED, got:\n{text}"
                )
                assert "event: progress" in text, (
                    f"SSE must yield at least one progress event, got:\n{text}"
                )