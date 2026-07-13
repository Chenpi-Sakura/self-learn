"""T5: /debug/state 路由（条件挂载）。

spec § 6.5 + § 10.7：仅当 settings.debug=True 时暴露；生产场景返回 404。
"""
from __future__ import annotations

import pytest

from selflearn.observability.hooks import hook_bus


@pytest.mark.asyncio
async def test_debug_state_returns_events(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "true")
    from selflearn.config import get_settings

    get_settings.cache_clear()
    s = get_settings()
    assert s.debug is True

    from fastapi.testclient import TestClient

    from selflearn.gateway.app import create_app

    app = create_app()
    client = TestClient(app)

    hook_bus.clear()
    hook_bus.emit("test.kind", {"foo": "bar"})

    resp = client.get("/debug/state")
    assert resp.status_code == 200, f"GET /debug/state 返回 {resp.status_code}"
    data = resp.json()
    assert "events" in data
    assert any(e["kind"] == "test.kind" for e in data["events"])


@pytest.mark.asyncio
async def test_debug_state_not_mounted_when_debug_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEBUG", raising=False)
    from selflearn.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from selflearn.gateway.app import create_app

    app = create_app()
    client = TestClient(app)
    resp = client.get("/debug/state")
    assert resp.status_code == 404
