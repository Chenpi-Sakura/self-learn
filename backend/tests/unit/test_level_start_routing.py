"""Task 257: POST /api/level/start 按 node_id 精确路由的回归测试。

Bug 背景：前端 TreasureMap 点击不同节点时讲义/习题不刷新。根因是
`start_level` 硬编码 `MapNode.status == "active"`，忽略前端传入的
`node_id`，导致所有请求都路由到同一个 active 节点的 in-flight Level。

修复：`LevelStartRequest` 加可选 `node_id`；有则精确按
`(student_id, node_id)` 查节点，没有则 fallback 到 `status="active"`。

测试风格沿用 tests/integration/test_api_gaps.py：mock get_session_factory
返回的 session，用 side_effect 依次返回多个 session.execute 结果。
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


import pytest
from httpx import ASGITransport, AsyncClient

from selflearn.core.envelope import Envelope
from selflearn.domain.level import Level
from selflearn.domain.map_node import MapNode
from selflearn.gateway.app import create_app
from selflearn.gateway.routes.level import LevelStartRequest, start_level


def _make_async_session_cm(mock_session: Any) -> Any:
    """构造一个能被 `async with factory() as session` 用的对象。"""

    class _CM:
        async def __aenter__(self) -> Any:
            return mock_session

        async def __aexit__(self, *args: object) -> None:
            pass

    return _CM()


def _make_fake_node(student_id: uuid.UUID, status: str = "active") -> MapNode:
    n = MapNode(
        student_id=str(student_id),
        kp_id=uuid.uuid4(),
        status=status,
        branch_type="main",
        position={"x": 0.1, "y": 0.2},
    )
    n.node_id = uuid.uuid4()
    return n


def _make_fake_level(
    node_id: uuid.UUID,
    status: str = "generated",
    lecture_html: str | None = "<h2>x</h2>",  # 默认非 NULL，旧测试不受影响
) -> Level:
    lv = Level(node_id=node_id, status=status, lecture_html=lecture_html)
    lv.level_id = uuid.uuid4()
    return lv


def _scalar_first_result(value: object) -> MagicMock:
    """构造 `session.execute(...).scalars().first()` 返回 value 的同步 Result。"""
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = value
    result.scalars.return_value = scalars
    return result


def _where_clause(sql: str) -> str:
    """取 SQL 里 WHERE 之后的部分（用于断言过滤条件，忽略 SELECT 列名）。"""
    parts = sql.split("WHERE", 1)
    return parts[1] if len(parts) > 1 else ""


def _capturing_session(results: list[MagicMock]) -> tuple[AsyncMock, list[str]]:
    """返回 (mock_session, captured_sql)。

    session.execute 依次吐出 results，并把每次传入的语句编译成 SQL 字符串
    存进 captured_sql，供测试断言 WHERE 子句是否真的按 node_id 过滤。
    """
    captured: list[str] = []
    it = iter(results)

    async def _execute(stmt: object, *args: object, **kwargs: object) -> MagicMock:
        try:
            captured.append(str(stmt))
        except Exception:  # noqa: BLE001 — 编译失败不该让测试崩
            captured.append("<uncompilable>")
        return next(it)

    session = AsyncMock()
    session.execute.side_effect = _execute
    return session, captured


@pytest.fixture
async def app_client() -> AsyncClient:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_start_level_with_node_id_returns_specific_level(
    app_client: AsyncClient,
) -> None:
    """前端传 node_id 且节点存在 + 有 in-flight Level → 复用该 node 的 level。"""
    sid = uuid.uuid4()
    node = _make_fake_node(sid, status="active")
    level = _make_fake_level(node.node_id)

    mock_session, captured = _capturing_session(
        [_scalar_first_result(node), _scalar_first_result(level)]
    )

    with patch(
        "selflearn.gateway.routes.level.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)
        resp = await app_client.post(
            "/api/level/start",
            json={"student_id": str(sid), "node_id": str(node.node_id)},
        )

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["level_id"] == str(level.level_id)
    assert data["node_id"] == str(node.node_id)
    assert data["reused"] is True
    # 核心断言：MapNode 查询的 WHERE 必须按 node_id 过滤（bug 时只按 status）
    assert "node_id" in _where_clause(captured[0])


@pytest.mark.asyncio
async def test_start_level_different_node_id_returns_different_level(
    app_client: AsyncClient,
) -> None:
    """核心回归：同一 student 传 2 个不同 node_id → 拿回 2 个不同的 level_id。"""
    sid = uuid.uuid4()
    node_a = _make_fake_node(sid, status="active")
    node_b = _make_fake_node(sid, status="active")
    level_a = _make_fake_level(node_a.node_id)
    level_b = _make_fake_level(node_b.node_id)

    # 请求 A：node_a → level_a
    session_a, captured_a = _capturing_session(
        [_scalar_first_result(node_a), _scalar_first_result(level_a)]
    )
    # 请求 B：node_b → level_b
    session_b, captured_b = _capturing_session(
        [_scalar_first_result(node_b), _scalar_first_result(level_b)]
    )

    with patch(
        "selflearn.gateway.routes.level.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(session_a)
        resp_a = await app_client.post(
            "/api/level/start",
            json={"student_id": str(sid), "node_id": str(node_a.node_id)},
        )
        factory_mock.return_value = lambda: _make_async_session_cm(session_b)
        resp_b = await app_client.post(
            "/api/level/start",
            json={"student_id": str(sid), "node_id": str(node_b.node_id)},
        )

    assert resp_a.status_code == 202, resp_a.text
    assert resp_b.status_code == 202, resp_b.text
    data_a = resp_a.json()
    data_b = resp_b.json()
    assert data_a["node_id"] == str(node_a.node_id)
    assert data_b["node_id"] == str(node_b.node_id)
    # 不同节点 → 不同 level_id（bug 时两者相同）
    assert data_a["level_id"] != data_b["level_id"]
    assert data_a["level_id"] == str(level_a.level_id)
    assert data_b["level_id"] == str(level_b.level_id)
    # 核心断言：两个请求的 MapNode 查询 WHERE 都必须按 node_id 过滤，
    # 否则 (bug) 两者都退化成 status='active' 的第一个节点。
    assert "node_id" in _where_clause(captured_a[0])
    assert "node_id" in _where_clause(captured_b[0])


@pytest.mark.asyncio
async def test_start_level_falls_back_to_active_when_no_node_id(
    app_client: AsyncClient,
) -> None:
    """不传 node_id → 走原 status='active' fallback 路径（向后兼容）。"""
    sid = uuid.uuid4()
    node = _make_fake_node(sid, status="active")
    level = _make_fake_level(node.node_id)

    mock_session, captured = _capturing_session(
        [_scalar_first_result(node), _scalar_first_result(level)]
    )

    with patch(
        "selflearn.gateway.routes.level.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)
        resp = await app_client.post(
            "/api/level/start",
            json={"student_id": str(sid)},  # 无 node_id
        )

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["level_id"] == str(level.level_id)
    assert data["node_id"] == str(node.node_id)
    assert data["reused"] is True
    # 向后兼容：无 node_id 时按 status 过滤，WHERE 不含 node_id 精确条件
    assert "status" in _where_clause(captured[0])
    assert "node_id" not in _where_clause(captured[0])


@pytest.mark.asyncio
async def test_start_level_unknown_node_id_returns_409(
    app_client: AsyncClient,
) -> None:
    """传不存在的 node_id → 409 node_not_found。"""
    sid = uuid.uuid4()
    unknown_node_id = uuid.uuid4()

    mock_session, _captured = _capturing_session([_scalar_first_result(None)])

    with patch(
        "selflearn.gateway.routes.level.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)
        resp = await app_client.post(
            "/api/level/start",
            json={"student_id": str(sid), "node_id": str(unknown_node_id)},
        )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "node_not_found"


@pytest.mark.asyncio
async def test_start_level_locked_node_id_returns_409(
    app_client: AsyncClient,
) -> None:
    """传 node_id 但节点 status='locked' → 409 node_locked，不查 Level。

    验证：节点已锁定（前置 KP 未完成），拒绝启动关卡，不复用 / 不发 envelope。
    """
    sid = uuid.uuid4()
    locked_node_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    locked_node = SimpleNamespace(
        node_id=locked_node_id,
        student_id=str(sid),
        status="locked",
    )

    mock_session, captured = _capturing_session(
        [_scalar_first_result(locked_node)]
    )

    with (
        patch("selflearn.gateway.routes.level.get_session_factory") as factory_mock,
        patch(
            "selflearn.gateway.routes.level.publish_envelope", new=AsyncMock()
        ) as pub_mock,
    ):
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)
        resp = await app_client.post(
            "/api/level/start",
            json={"student_id": str(sid), "node_id": str(locked_node_id)},
        )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "node_locked"
    # locked 路径不应进入 Level 查询（避免错误复用 completed 关卡），也不应发 envelope
    assert not any(
        "levels" in s.lower() for s in captured
    ), f"应跳过 Level 查询：{captured}"
    pub_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_level_skips_null_lecture_level(monkeypatch: pytest.MonkeyPatch) -> None:
    """lecture_html IS NULL 的关卡视为不可复用，触发新 envelope。"""
    factory = AsyncMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    null_level = _make_fake_level(uuid.uuid4(), status="generated", lecture_html=None)
    # node 查询也返回该 null_level（reuse 路径要走完）
    exec_result = MagicMock()
    exec_result.scalars.return_value.first.return_value = null_level
    session.execute = AsyncMock(return_value=exec_result)
    session.get = AsyncMock(return_value=MagicMock(status="active", student_id="s1"))

    published: list[Envelope] = []
    async def fake_publish(env: Envelope, routing_key: str) -> None:
        published.append(env)
    monkeypatch.setattr("selflearn.gateway.routes.level.publish_envelope", fake_publish)

    factory_ctx = MagicMock()
    factory_ctx.return_value = session  # get_session_factory()() -> session
    monkeypatch.setattr("selflearn.gateway.routes.level.get_session_factory", lambda: factory_ctx)

    body = LevelStartRequest(student_id="s1", node_id=str(uuid.uuid4()))
    resp = await start_level(body)

    assert resp["reused"] is False
    assert "trace_id" in resp
    assert len(published) == 1


@pytest.mark.asyncio
async def test_start_level_reuses_level_with_lecture(monkeypatch: pytest.MonkeyPatch) -> None:
    """lecture_html 非 NULL 的关卡正常复用。"""
    factory = AsyncMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    good_level = _make_fake_level(uuid.uuid4(), status="generated", lecture_html="<h2>核心</h2>")
    exec_result = MagicMock()
    exec_result.scalars.return_value.first.return_value = good_level
    session.execute = AsyncMock(return_value=exec_result)
    session.get = AsyncMock(return_value=MagicMock(status="active", student_id="s1"))

    published: list[Envelope] = []
    async def fake_publish(env: Envelope, routing_key: str) -> None:
        published.append(env)
    monkeypatch.setattr("selflearn.gateway.routes.level.publish_envelope", fake_publish)

    factory_ctx = MagicMock()
    factory_ctx.return_value = session
    monkeypatch.setattr("selflearn.gateway.routes.level.get_session_factory", lambda: factory_ctx)

    body = LevelStartRequest(student_id="s1", node_id=str(uuid.uuid4()))
    resp = await start_level(body)

    assert resp["reused"] is True
    assert resp["level_id"] == str(good_level.level_id)
    assert len(published) == 0
