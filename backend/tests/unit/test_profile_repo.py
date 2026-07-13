"""Unit tests for ProfileRepository (Stage 4 Task 6; spec § 5.1 + § 5.3).

测试要点（spec § 5.1 / § 5.3）：
- apply_delta: 微调维度 + clamp [0, 1] + 写 ProfileSnapshot(trigger=level_completed)
- upsert:      student 不存在时创建；存在时更新（短路返回已存在）
- recent_snapshots: 按 created_at DESC 取最近 N 条

注：SQLite 不支持 JSONB，且 Base.metadata 上部分模型（map_nodes 等）的 FK 引用
不存在的 students 表，因此本测试用 AsyncMock + 镜像 QueryResult 行为覆盖 repo 接口
契约。Profile 字段类型 / JSONB 行为由 PG 集成测试在 testcontainers 层覆盖。
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from selflearn.domain.profile import Profile
from selflearn.domain.profile_snapshot import ProfileSnapshot
from selflearn.infra.repositories.profile_repo import ProfileRepository


_DEFAULT_DIMS_6: dict[str, float] = {
    "kb": 0.5, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5,
}


def _make_profile(student_id: UUID, dimensions: dict[str, Any] | None = None) -> Profile:
    """Memory-only Profile (无 DB attach)：用于 repo 接口契约测试。"""
    p = Profile(
        profile_id=uuid4(),
        student_id=student_id,
        dimensions=dimensions if dimensions is not None else dict(_DEFAULT_DIMS_6),
        tags=[],
    )
    return p


def _make_snapshot(student_id: UUID, profile: dict[str, float], trigger: str, created_at: Any) -> ProfileSnapshot:
    s = ProfileSnapshot(student_id=student_id, profile=profile, trigger=trigger)
    s.created_at = created_at
    return s


class _FakeScalars:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return list(self._items)


class _FakeResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def scalar_one_or_none(self) -> Any:
        return self._items[0] if self._items else None

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._items)


class _FakeSession:
    """最小 AsyncSession 替身：让 ProfileRepository 不依赖真实 PG/JSONB。

    - execute(stmt) → 根据语句目标 entity 路由到不同预存表（profiles / profile_snapshots）
    - flush() / add()       → no-op（对象已在内存）
    """

    def __init__(self) -> None:
        self.added: list[Any] = []
        self._profiles: dict[str, Profile] = {}

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def execute(self, stmt: Any) -> _FakeResult:
        # 从 stmt 提取目标 ORM 类与 where 子句（_get_by_student / recent_snapshots）
        from selflearn.domain import profile as _p
        from selflearn.domain import profile_snapshot as _s

        col_descs = stmt.column_descriptions
        if not col_descs:
            return _FakeResult([])
        entity = col_descs[0]["entity"]
        if entity is _p.Profile:
            sid = self._extract_student_id(stmt)
            hits = [v for v in self._profiles.values() if v.student_id == sid]
            return _FakeResult(hits)
        if entity is _s.ProfileSnapshot:
            sid = self._extract_student_id(stmt)
            snaps = [o for o in self.added if isinstance(o, _s.ProfileSnapshot) and o.student_id == sid]
            # recent_snapshots 默认按 created_at desc
            snaps.sort(key=lambda x: x.created_at, reverse=True)
            return _FakeResult(snaps)
        return _FakeResult([])

    @staticmethod
    def _extract_student_id(stmt: Any) -> Any:
        wc = getattr(stmt, "whereclause", None)
        if wc is None:
            return None
        right = getattr(wc, "right", None)
        if right is not None and hasattr(right, "value"):
            return right.value
        return None


@pytest.mark.asyncio
async def test_profile_repo_apply_delta_creates_snapshot() -> None:
    """apply_delta: 微调维度 + 写 ProfileSnapshot(trigger='level_completed')。"""
    sid = uuid4()
    sess = _FakeSession()
    existing = _make_profile(sid, dimensions=dict(_DEFAULT_DIMS_6))
    sess._profiles[str(sid)] = existing

    repo = ProfileRepository(sess)  # type: ignore[arg-type]
    new_dims = await repo.apply_delta(sid, {"kb": 0.05, "as": -0.02})

    assert new_dims["kb"] == pytest.approx(0.55, 0.01)
    assert new_dims["as"] == pytest.approx(0.48, 0.01)
    snaps = [o for o in sess.added if isinstance(o, ProfileSnapshot)]
    assert len(snaps) == 1
    assert snaps[0].trigger == "level_completed"
    assert snaps[0].student_id == sid
    assert snaps[0].profile["kb"] == pytest.approx(0.55, 0.01)


@pytest.mark.asyncio
async def test_apply_delta_clamps_to_unit_interval() -> None:
    """clamp [0, 1]：累加超出上下界应被截断。"""
    sid = uuid4()
    sess = _FakeSession()
    existing = _make_profile(
        sid,
        dimensions={"kb": 0.9, "vp": 0.1, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
    )
    sess._profiles[str(sid)] = existing

    repo = ProfileRepository(sess)  # type: ignore[arg-type]
    # kb + 0.5 → 应 clamp 到 1.0；vp - 0.5 → 应 clamp 到 0.0
    new_dims = await repo.apply_delta(sid, {"kb": 0.5, "vp": -0.5})

    assert new_dims["kb"] == pytest.approx(1.0, 0.001)
    assert new_dims["vp"] == pytest.approx(0.0, 0.001)


@pytest.mark.asyncio
async def test_recent_snapshots_orders_by_created_at_desc() -> None:
    sid = uuid4()
    sess = _FakeSession()
    existing = _make_profile(sid, dimensions=dict(_DEFAULT_DIMS_6))
    sess._profiles[str(sid)] = existing

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    snaps_in: list[ProfileSnapshot] = []
    for i, secs in enumerate([0, 60, 120]):
        s = _make_snapshot(
            sid,
            {"kb": 0.5 + i * 0.01, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
            "level_completed",
            now + timedelta(seconds=secs),
        )
        sess.add(s)
        snaps_in.append(s)

    repo = ProfileRepository(sess)  # type: ignore[arg-type]
    snaps = await repo.recent_snapshots(sid, limit=10)

    assert len(snaps) == 3
    # 最新的 created_at 是第 3 条（+120s），kb 应最大
    assert snaps[0].profile["kb"] == pytest.approx(0.52, 0.01)
    assert snaps[-1].profile["kb"] == pytest.approx(0.50, 0.01)


@pytest.mark.asyncio
async def test_upsert_creates_when_missing() -> None:
    """upsert: student 不存在时创建。"""
    sid = uuid4()
    sess = _FakeSession()

    repo = ProfileRepository(sess)  # type: ignore[arg-type]
    p = await repo.upsert(
        sid,
        {"kb": 0.7, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
        tags=["new"],
    )

    assert p.student_id == sid
    assert p.tags == ["new"]
    assert p.dimensions["kb"] == 0.7


@pytest.mark.asyncio
async def test_upsert_updates_when_existing() -> None:
    """upsert: student 已存在时覆盖 dimensions/tags 并返回同一行。"""
    sid = uuid4()
    sess = _FakeSession()
    existing = _make_profile(sid, dimensions=dict(_DEFAULT_DIMS_6))
    sess._profiles[str(sid)] = existing

    repo = ProfileRepository(sess)  # type: ignore[arg-type]
    p = await repo.upsert(
        sid,
        {"kb": 0.8, "vp": 0.4, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
        tags=["updated"],
    )

    assert p.profile_id == existing.profile_id
    assert p.dimensions["kb"] == 0.8
    assert p.tags == ["updated"]
