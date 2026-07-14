"""Stage 4 API 5 缺口补全测试（T7+T8+T9+T10 集中放这里）。

T7: GET /api/profile/{student_id} — 启动时加载画像（spec § 4.1）。

mock 模式：profile 表含 JSONB/PgUUID/FK，SQLite fixture 不兼容，
故直接 mock 路由层调用的具体函数（ProfileRepository._get_by_student
+ get_session_factory 返回的 mock session.execute），
断言响应 JSON 字段对。参考 Stage 3 tests/unit/test_sse_endpoint.py。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from selflearn.domain.profile import Profile
from selflearn.gateway.app import create_app
from selflearn.infra.repositories.profile_repo import ProfileRepository


def _make_fake_profile(student_id: uuid.UUID) -> Profile:
    """构造未 attached 的 Profile 对象（mock 返回值用）。"""
    p = Profile(
        profile_id=uuid.uuid4(),
        student_id=student_id,
        dimensions={"kb": 0.7, "vp": 0.5, "as": 0.6, "ge": 0.4, "ept": 0.5, "fd": 0.5},
        tags=["demo"],
    )
    p.last_updated = datetime(2026, 7, 13, 10, 0, 0, tzinfo=timezone.utc)
    return p


def _make_async_session_cm(mock_session: Any) -> Any:
    """构造一个能被 `async with factory() as session` 用的对象。"""

    class _CM:
        async def __aenter__(self) -> Any:
            return mock_session

        async def __aexit__(self, *args: object) -> None:
            pass

    return _CM()


@pytest.fixture
async def app_client() -> AsyncClient:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_profile_returns_dimensions_and_tags(app_client: AsyncClient) -> None:
    sid = uuid.uuid4()
    fake = _make_fake_profile(sid)

    async def fake_get_by_student(
        self: ProfileRepository, student_id: uuid.UUID
    ) -> Profile | None:
        return fake if student_id == sid else None

    mock_session = AsyncMock()
    # 注意：session.execute 是 awaitable，但 execute() 返回的 Result.scalar_one 是同步方法，
    # 故 Result 用 MagicMock（不要 AsyncMock），否则 scalar_one() 会变成 awaitable。
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 3
    mock_session.execute.return_value = mock_result

    with patch.object(
        ProfileRepository, "_get_by_student", new=fake_get_by_student
    ), patch(
        "selflearn.gateway.routes.profile.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)

        resp = await app_client.get(f"/api/profile/{sid}")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["student_id"] == str(sid)
    assert data["dimensions"]["kb"] == 0.7
    assert "demo" in data["tags"]
    assert data["snapshot_count"] == 3
    assert data["last_updated_at"] is not None


@pytest.mark.asyncio
async def test_get_profile_404_when_not_found(app_client: AsyncClient) -> None:
    sid = uuid.uuid4()

    async def fake_get_by_student_none(
        self: ProfileRepository, student_id: uuid.UUID
    ) -> Profile | None:
        return None

    mock_session = AsyncMock()

    with patch.object(
        ProfileRepository, "_get_by_student", new=fake_get_by_student_none
    ), patch(
        "selflearn.gateway.routes.profile.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)

        resp = await app_client.get(f"/api/profile/{sid}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "profile_not_found"