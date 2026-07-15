"""MCP 测试专用 conftest：DB-touching test 共享 session-scope event loop。

pytest-asyncio 在 function-scope loop 下，跨 test 时 asyncpg 连接仍绑定
到上一个 loop → RuntimeError('Event loop is closed'). 给所有 DB-touching
test 共享一个 session-scope event loop 即可避免。
"""
from __future__ import annotations

import asyncio

import pytest_asyncio


@pytest_asyncio.fixture(loop_scope="session", scope="session")
def session_event_loop():  # type: ignore[no-untyped-def]
    """Session-scoped event loop fixture; DB tests 通过 marker 绑定到它。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()