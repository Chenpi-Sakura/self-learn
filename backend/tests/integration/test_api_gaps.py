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
from selflearn.domain.level import Level
from selflearn.domain.exercise import Exercise


def _make_fake_profile(student_id: uuid.UUID) -> Profile:
    """构造未 attached 的 Profile 对象（mock 返回值用）。"""
    p = Profile(
        profile_id=uuid.uuid4(),
        student_id=student_id,
        # Stage 4-fix: fixture 用 DB 真实存储格式（长名）+ API 层做长→短映射
        dimensions={"knowledge_base": 0.7, "visual_preference": 0.5, "analytic_style": 0.6,
                    "goal_employment": 0.4, "error_prone_type": 0.5, "focus_duration": 0.5},
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
        # Stage 4-fix: 长名 + API 层做长→短映射
        profile={"knowledge_base": kb_value, "visual_preference": 0.5, "analytic_style": 0.5,
                 "goal_employment": 0.5, "error_prone_type": 0.5, "focus_duration": 0.5},
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
        self: ProfileRepository, student_id: str
    ) -> Profile | None:
        return fake if student_id == str(sid) else None

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
        self: ProfileRepository, student_id: str
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
        student_id: str,
        limit: int = 10,
    ) -> list[ProfileSnapshot]:
        # 真实 repo 已经按 created_at DESC 返回；这里 fake 也按 DESC 顺序给
        return [fake_snap_3, fake_snap_2, fake_snap_1] if student_id == str(sid) else []

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
        student_id: str,
        limit: int = 10,
    ) -> list[ProfileSnapshot]:
        return fake_snaps[:limit] if student_id == str(sid) else []

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


def _make_fake_level(
    level_id: uuid.UUID,
    node_id: uuid.UUID | None = None,
    status: str = "generated",
) -> Level:
    """构造未 attached 的 Level 对象（mock 返回值用）。"""
    lv = Level(
        node_id=node_id or uuid.uuid4(),
        status=status,
    )
    lv.level_id = level_id  # 确保 PK 存在
    return lv


def _make_fake_exercise(
    level_id: uuid.UUID,
    prompt: str,
    exercise_type: str = "single_choice",
    options: list[str] | None = None,
) -> Exercise:
    """构造未 attached 的 Exercise 对象。"""
    ex = Exercise(
        level_id=level_id,
        exercise_type=exercise_type,
        prompt=prompt,
        options=options or [],
        correct_answer="A",
    )
    ex.exercise_id = uuid.uuid4()
    return ex


@pytest.mark.asyncio
async def test_get_level_returns_exercises(app_client: AsyncClient) -> None:
    """level 端点：返回关卡详情 + exercise 列表。"""
    level_id = uuid.uuid4()
    node_id = uuid.uuid4()
    fake_level = _make_fake_level(level_id, node_id=node_id, status="in_progress")
    fake_ex1 = _make_fake_exercise(
        level_id, prompt="What is attention?", exercise_type="single_choice",
        options=["A", "B", "C"],
    )
    fake_ex2 = _make_fake_exercise(
        level_id, prompt="Explain Q/K/V.", exercise_type="short_answer",
    )

    # session.get(Level, level_id) 返回 fake_level
    # session.execute(select(Exercise).where(...)).scalars().all() 返回 [fake_ex1, fake_ex2]
    mock_session = AsyncMock()

    async def fake_get(model: type, key: object) -> object:
        if model is Level and key == level_id:
            return fake_level
        return None

    mock_session.get = fake_get

    mock_result = MagicMock()  # sync result, 同 T7 历史教训
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [fake_ex1, fake_ex2]
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch(
        "selflearn.gateway.routes.level.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)

        resp = await app_client.get(f"/api/level/{level_id}")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["level_id"] == str(level_id)
    assert data["node_id"] == str(node_id)
    assert data["status"] == "in_progress"
    assert len(data["exercises"]) == 2

    # 第一题：single_choice
    ex1 = data["exercises"][0]
    assert ex1["prompt"] == "What is attention?"
    assert ex1["type"] == "single_choice"
    assert ex1["options"] == ["A", "B", "C"]

    # 第二题：short_answer + options=None
    ex2 = data["exercises"][1]
    assert ex2["type"] == "short_answer"
    assert ex2["options"] is None


@pytest.mark.asyncio
async def test_get_level_404_when_not_found(app_client: AsyncClient) -> None:
    """level_id 不存在时返回 404。"""
    level_id = uuid.uuid4()
    mock_session = AsyncMock()

    async def fake_get_none(model: type, key: object) -> object:
        return None

    mock_session.get = fake_get_none

    with patch(
        "selflearn.gateway.routes.level.get_session_factory"
    ) as factory_mock:
        factory_mock.return_value = lambda: _make_async_session_cm(mock_session)

        resp = await app_client.get(f"/api/level/{level_id}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "level_not_found"


@pytest.mark.asyncio
async def test_profile_agent_sse_completed_includes_profile_field() -> None:
    """SSE completed 事件 payload 必须含 profile（含 dimensions + tags），供前端雷达图动画。

    spec § 10.3 line 670-671 + § 7.4 line 552。直接 mock progress_publish，调用
    ProfileAgent.run()，断言最后一次 publish 的 ProgressEvent.payload 含
    profile.dimensions（用 spec 缩写键 kb/vp/as/ge/ept/fd）+ profile.tags。
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from selflearn.agents.builtin.profile_agent import ProfileAgent
    from selflearn.core.envelope import ActorRef, Envelope
    from selflearn.progress.stages import Stage
    from selflearn.skills.library import load_all

    # ProfileAgent.run() 会 get_skill("skill.profile.build") 做 sanity check → 需先加载
    load_all()

    # 用 Stage 3 测试同样的 mock 模式（参考 test_profile_agent.py:15-53）
    fake_uuid = "11111111-2222-3333-4444-666666666666"
    fake_session = AsyncMock()
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock(
        side_effect=lambda obj: setattr(obj, "profile_id", __import__("uuid").UUID(fake_uuid))
    )

    with patch("selflearn.agents.builtin.profile_agent.get_session_factory") as mock_factory, \
         patch("selflearn.agents.builtin.profile_agent.progress_publish", new=AsyncMock()) as mock_pub:
        factory_callable = MagicMock()
        factory_callable.return_value.__aenter__ = AsyncMock(return_value=fake_session)
        factory_callable.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = factory_callable

        env = Envelope(
            action="skill.execute",
            sender=ActorRef(type="gateway", id="g"),
            target=ActorRef(type="skill", id="skill.profile.build"),
            payload={
                "student_id": "00000000-0000-0000-0000-000000000002",
                # Stage 3 长名（ProfileAgent.DIMENSION_KEYS 实际期望）
                "dimensions": {k: 0.5 for k in [
                    "knowledge_base", "visual_preference", "analytic_style",
                    "goal_employment", "error_prone_type", "focus_duration",
                ]},
                "tags": ["integration-test"],
            },
        )

        await ProfileAgent().run(env)

    # 找最后一次 progress_publish（Stage.PROFILE, "completed"）的 payload
    completed_call = next(
        c for c in mock_pub.call_args_list
        if c.args[1].stage == Stage.PROFILE and c.args[1].status == "completed"
    )
    payload = completed_call.args[1].payload

    # 断言：含 profile 字段
    assert "profile" in payload, f"SSE completed payload 缺 profile 字段：{payload}"
    profile = payload["profile"]
    assert "dimensions" in profile
    assert "tags" in profile

    # 维度键用 spec 缩写（前端 § 7.4 line 553 直接读 as ProfileDimensions）
    dims = profile["dimensions"]
    assert set(dims.keys()) == {"kb", "vp", "as", "ge", "ept", "fd"}, \
        f"维度键必须用 spec 缩写：{sorted(dims.keys())}"
    assert dims["kb"] == 0.5  # knowledge_base → kb

    # tags 透传
    assert profile["tags"] == ["integration-test"]

    # 既有 profile_id 字段保留（兼容 reply envelope 测试）
    assert "profile_id" in payload


@pytest.mark.asyncio
async def test_director_sse_completed_includes_level_id_and_exercise_ids() -> None:
    """SSE completed 事件 payload 必须包含 level_id + exercise_ids（spec § 4.4 + § 10.3）。

    简化策略：不真起 DirectorAgent.run()（涉及 LLM + 多表 + 5 步串联），
    直接调 _run_inner 之外的最小路径 + mock 关键依赖（exercise_agent.run_sync /
    review_agent.review / get_session_factory / progress_publish）。
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from selflearn.agents.builtin import director_agent as director_mod
    from selflearn.agents.builtin import exercise_agent, review_agent
    from selflearn.agents.builtin.exercise_agent import ExerciseAgent
    from selflearn.agents.builtin.review_agent import ReviewAgent
    from selflearn.core.envelope import ActorRef, Envelope
    from selflearn.domain.map_node import MapNode
    from selflearn.domain.level import Level
    from selflearn.domain.exercise import Exercise
    from selflearn.progress.stages import Stage, ProgressEvent
    from selflearn.skills.library import load_all

    # DirectorAgent._run_inner 会 get_skill("skill.director.start") → 需先加载所有 skill
    load_all()

    sid = uuid.uuid4()
    node_id = uuid.uuid4()
    kp_id = uuid.uuid4()
    fake_node = MapNode(student_id=sid, kp_id=kp_id, status="active")
    fake_node.node_id = node_id
    fake_node.kp = MagicMock(title="Attention")  # type: ignore[attr-defined]

    fake_level = Level(node_id=node_id, status="generated", form="exercise")
    fake_level.level_id = uuid.uuid4()

    fake_ex1 = Exercise(level_id=fake_level.level_id, exercise_type="single_choice",
                        prompt="Q1", options=["A"], correct_answer="A")
    fake_ex1.exercise_id = uuid.uuid4()
    fake_ex2 = Exercise(level_id=fake_level.level_id, exercise_type="short_answer",
                        prompt="Q2", options=[], correct_answer="answer")
    fake_ex2.exercise_id = uuid.uuid4()

    # review.score = 0.9 (high → kb delta +0.05)
    fake_review = MagicMock(verdict="accepted", score=0.9, issues=[])

    fake_session = AsyncMock()

    # session.execute 多种返回：scalar/.first/.all
    # 1) select(MapNode).where(...).scalars().first() → fake_node
    # 2) LevelRepository.recent_scores: select(score).where(...).scalars().all() → []
    # 3) ExerciseRepository.bulk_create 返回 [fake_ex1, fake_ex2]
    # 4) ProfileRepository.apply_delta / .upsert / recent_snapshots 等的内部 execute

    # bulk_create 是 repo 方法，需要 patch 返回 [fake_ex1, fake_ex2]
    async def fake_bulk_create(level_id: object, ex_dicts: list[object]) -> list[Exercise]:
        return [fake_ex1, fake_ex2]

    # Stage 4-fix: director 改为 `ExerciseAgent().run_sync(...)` 类实例调用，
    # patch 类方法而不是模块属性。
    with patch.object(director_mod, "get_session_factory") as mock_factory, \
         patch.object(ExerciseAgent, "run_sync", new=AsyncMock(return_value=[
             {"exercise_type": "single_choice", "prompt": "Q1"},
             {"exercise_type": "short_answer", "prompt": "Q2"},
         ])), \
         patch.object(ReviewAgent, "review", new=AsyncMock(return_value=fake_review)), \
         patch("selflearn.agents.builtin.director_agent.ExerciseRepository") as mock_repo_cls, \
         patch("selflearn.agents.builtin.director_agent.LevelRepository") as mock_level_repo_cls, \
         patch("selflearn.agents.builtin.director_agent.ProfileRepository") as mock_profile_repo_cls, \
         patch.object(director_mod, "progress_publish", new=AsyncMock()) as mock_pub:
        factory_callable = MagicMock()
        factory_callable.return_value.__aenter__ = AsyncMock(return_value=fake_session)
        factory_callable.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = factory_callable
        mock_repo_cls.return_value.bulk_create = fake_bulk_create
        mock_level_repo_cls.return_value.recent_scores = AsyncMock(return_value=[])
        mock_profile_repo_cls.return_value.apply_delta = AsyncMock(return_value={
            "kb": 0.55, "vp": 0.5, "as": 0.52, "ge": 0.5, "ept": 0.5, "fd": 0.5,
        })

        env = Envelope(
            action="skill.execute",
            sender=ActorRef(type="gateway", id="g"),
            target=ActorRef(type="skill", id="skill.director.start"),
            payload={"student_id": str(sid)},
        )

        # 关键：让 select(MapNode).scalars().first() 返回 fake_node
        async def fake_execute_with_node(stmt: object) -> object:
            m = MagicMock()
            m.scalars.return_value.first.return_value = fake_node
            m.scalars.return_value.all.return_value = []
            m.scalar_one.return_value = 0
            return m

        fake_session.execute = fake_execute_with_node

        # Level.flush() 后才能拿到 level.level_id — fake_level 已预设
        async def fake_flush() -> None:
            pass

        fake_session.flush = fake_flush
        fake_session.add = MagicMock()
        fake_session.commit = AsyncMock()

        reply = await director_mod.DirectorAgent().run(env)

    # 断言 reply.payload 含 level_id（Stage 3 兼容）
    assert "level_id" in reply.payload

    # 找最后一次 COMPLETED publish 的 payload
    completed_call = next(
        c for c in mock_pub.call_args_list
        if c.args[1].stage == Stage.COMPLETED and c.args[1].status == "completed"
    )
    payload = completed_call.args[1].payload
    assert "level_id" in payload
    assert "exercise_ids" in payload
    assert len(payload["exercise_ids"]) == 2
    # 既有的 exercises_count 字段保留
    assert payload["exercises_count"] == 2
    # 新增 score 字段
    assert payload["score"] == pytest.approx(0.9, 0.01)
