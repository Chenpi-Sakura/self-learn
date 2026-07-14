"""Stage 4 API 5 缺口补全测试（T7+T8+T9+T10 集中放这里）。

T7: GET /api/profile/{student_id} — 启动时加载画像（spec § 4.1）。
T8: GET /api/profile/{student_id}/history — 演变迷你折线图（spec § 5.3）。
T9: GET /api/map/{student_id}/nodes — 启动时加载藏宝图节点列表（spec § 4.2）。

mock 模式：profile 表含 JSONB/PgUUID/FK，SQLite fixture 不兼容，
故直接 mock 路由层调用的具体函数（ProfileRepository._get_by_student /
recent_snapshots + get_session_factory 返回的 mock session.execute），
断言响应 JSON 字段对。参考 Stage 3 tests/unit/test_sse_endpoint.py。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.domain.map_node import MapNode
from selflearn.domain.profile import Profile
from selflearn.domain.profile_snapshot import ProfileSnapshot
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


def _make_fake_snapshot(
    student_id: uuid.UUID,
    kb_value: float,
    trigger: str = "level_completed",
    created_at: datetime | None = None,
) -> ProfileSnapshot:
    """构造未 attached 的 ProfileSnapshot 对象（mock 返回值用）。"""
    s = ProfileSnapshot(
        student_id=student_id,
        profile={"kb": kb_value, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
        trigger=trigger,
    )
    s.created_at = created_at or datetime(2026, 7, 13, 10, 0, 0, tzinfo=timezone.utc)
    return s


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


@pytest.mark.asyncio
async def test_get_profile_history_returns_snapshots_in_desc_order(
    app_client: AsyncClient,
) -> None:
    """history 端点：返回 N 条按 created_at DESC 的快照。"""
    sid = uuid.uuid4()
    fake_snap_1 = _make_fake_snapshot(sid, kb_value=0.50, created_at=datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc))
    fake_snap_2 = _make_fake_snapshot(sid, kb_value=0.60, created_at=datetime(2026, 7, 13, 11, 0, tzinfo=timezone.utc))
    fake_snap_3 = _make_fake_snapshot(sid, kb_value=0.70, created_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc))

    async def fake_recent_snapshots(
        self: ProfileRepository,
        student_id: uuid.UUID,
        limit: int = 10,
    ) -> list[ProfileSnapshot]:
        # 真实 repo 已经按 created_at DESC 返回；这里 fake 也按 DESC 顺序给
        return [fake_snap_3, fake_snap_2, fake_snap_1] if student_id == sid else []

    mock_session = AsyncMock()
    with patch.object(
        ProfileRepository, "recent_snapshots", new=fake_recent_snapshots
    ), patch(
        "selflearn.gateway.routes.profile.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)

        resp = await app_client.get(f"/api/profile/{sid}/history?limit=10")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["student_id"] == str(sid)
    assert len(data["snapshots"]) == 3
    # 最新一条 kb=0.70（fake_snap_3）
    assert data["snapshots"][0]["profile"]["kb"] == 0.7
    assert data["snapshots"][0]["trigger"] == "level_completed"
    assert "created_at" in data["snapshots"][0]
    # 最早一条 kb=0.50
    assert data["snapshots"][-1]["profile"]["kb"] == 0.5


@pytest.mark.asyncio
async def test_get_profile_history_respects_limit(app_client: AsyncClient) -> None:
    """limit=2 时只返回 2 条。"""
    sid = uuid.uuid4()
    fake_snaps = [
        _make_fake_snapshot(sid, kb_value=0.5 + i * 0.01, created_at=datetime(2026, 7, 13, 10, i, tzinfo=timezone.utc))
        for i in range(3)
    ]

    async def fake_recent_snapshots_limited(
        self: ProfileRepository,
        student_id: uuid.UUID,
        limit: int = 10,
    ) -> list[ProfileSnapshot]:
        return fake_snaps[:limit] if student_id == sid else []

    mock_session = AsyncMock()
    with patch.object(
        ProfileRepository, "recent_snapshots", new=fake_recent_snapshots_limited
    ), patch(
        "selflearn.gateway.routes.profile.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)

        resp = await app_client.get(f"/api/profile/{sid}/history?limit=2")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["snapshots"]) == 2


def _make_fake_map_node(
    student_id: uuid.UUID,
    kp_id: uuid.UUID,
    status: str = "active",
    position: dict[str, float] | None = None,
) -> MapNode:
    """构造未 attached 的 MapNode 对象（mock 返回值用）。"""
    n = MapNode(
        student_id=student_id,
        kp_id=kp_id,
        status=status,
        branch_type="main",
        position=position or {"x": 0.5, "y": 0.3},
    )
    n.node_id = uuid.uuid4()  # 确保 PK 存在（ORM default 在 PG 才生效，fake 需手动）
    return n


@pytest.mark.asyncio
async def test_get_map_nodes_returns_list(app_client: AsyncClient) -> None:
    """map nodes 端点：返回按 student_id 过滤的节点列表。"""
    sid = uuid.uuid4()
    kp1_id = uuid.uuid4()
    kp2_id = uuid.uuid4()
    fake_node1 = _make_fake_map_node(sid, kp1_id, status="active", position={"x": 0.1, "y": 0.2})
    fake_node2 = _make_fake_map_node(sid, kp2_id, status="completed", position={"x": 0.5, "y": 0.5})
    fake_node_other = _make_fake_map_node(uuid.uuid4(), uuid.uuid4(), status="locked")

    # 路由逻辑：session.execute(select(MapNode, KP.title).join(...).where(student_id==sid))
    # mock 整个 query chain 返回 fake rows
    fake_rows = [
        (fake_node1, "Attention 机制"),
        (fake_node2, "Self-Attention"),
    ]

    mock_session = AsyncMock()
    mock_result = MagicMock()  # sync result, 同 T7 历史教训
    mock_result.all.return_value = fake_rows
    mock_session.execute.return_value = mock_result

    with patch(
        "selflearn.gateway.routes.map.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)

        resp = await app_client.get(f"/api/map/{sid}/nodes")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "nodes" in data
    assert len(data["nodes"]) == 2

    # 第一个节点：active status + (0.1, 0.2)
    n1 = data["nodes"][0]
    assert n1["node_id"] == str(fake_node1.node_id)
    assert n1["kp_id"] == str(kp1_id)
    assert n1["title"] == "Attention 机制"
    assert n1["position"]["x"] == pytest.approx(0.1, 0.001)
    assert n1["position"]["y"] == pytest.approx(0.2, 0.001)
    assert n1["status"] == "active"

    # 第二个节点：completed + (0.5, 0.5)
    n2 = data["nodes"][1]
    assert n2["status"] == "completed"
    assert n2["title"] == "Self-Attention"


@pytest.mark.asyncio
async def test_get_map_nodes_empty_when_no_match(app_client: AsyncClient) -> None:
    """student 无节点时返回 nodes=[]。"""
    sid = uuid.uuid4()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    with patch(
        "selflearn.gateway.routes.map.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)

        resp = await app_client.get(f"/api/map/{sid}/nodes")

    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
