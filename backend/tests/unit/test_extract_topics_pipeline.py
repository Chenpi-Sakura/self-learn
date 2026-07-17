"""提炼主题 5 阶段流水线 + JSON schema + 重试 + 孤儿 KP 清理 + 事务回滚。

覆盖矩阵（plan §3.3 / Step 7）：
- _validate_topics 纯函数 3 个
  1. well-formed（含自指 prereq 丢弃）
  2. excerpt 太短拒
  3. source_resource_id 不在 input 拒
- pipeline 行为 3 个
  4. happy path：mock LLM 返回有效 JSON，发布 5 阶段事件
  5. LLM 返回坏 JSON → 1 次重试成功
  6. LLM 两次都坏 → validate failed 事件 + 退出
- 事务回滚 1 个
  7. DB 抛错 → write failed 事件
- orphan KP 清理 1 个
  8. 跑完 happy path 后 KP 数 == drafts 数（写入了 drafts 数目的 KP / MapNode）

测试策略：
- progress_publish / LLMRegistry / DB session 全部 mock
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from selflearn.agents.extract_topics import (
    TOPIC_SCHEMA,
    _validate_topics,
    run_extract_topics,
)
from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory  # noqa: F401  仅为澄清 import


# ---------- 1. _validate_topics 纯函数 ----------

def _good_topic(title: str, source: str = "abc") -> dict[str, Any]:
    return {
        "title": title,
        "description": "d" * 50,
        "prerequisites": [],
        "excerpt_text": "x" * 600,
        "source_resource_id": source,
    }


def test_validate_topics_accepts_well_formed_and_drops_self_ref() -> None:
    """well-formed 接受；自指 prereq（title 引用自己）被丢弃。"""
    valid = {
        "topics": [
            _good_topic("T1"),
            _good_topic("T2"),
            _good_topic("T3"),
        ]
    }
    # 在 T1 上加一个自指 prereq（应被丢弃）
    valid["topics"][0]["prerequisites"] = ["T1"]
    drafts = _validate_topics(valid, {"abc"})
    assert len(drafts) == 3
    titles = {d.title for d in drafts}
    assert titles == {"T1", "T2", "T3"}
    t1 = next(d for d in drafts if d.title == "T1")
    assert "T1" not in t1.prerequisites  # self-ref 必被丢


def test_validate_topics_rejects_excerpt_too_short() -> None:
    """excerpt_text < 500 → 拒。"""
    bad = {"topics": [
        {**_good_topic("T1"), "excerpt_text": "x" * 100},
        _good_topic("T2"),
        _good_topic("T3"),
    ]}
    with pytest.raises(Exception):
        _validate_topics(bad, {"abc"})


def test_validate_topics_rejects_source_not_in_input() -> None:
    """source_resource_id 必须在 input_ids 中。"""
    bad = {
        "topics": [
            _good_topic("T1", source="ghost"),
            _good_topic("T2", source="ghost"),
            _good_topic("T3", source="ghost"),
        ]
    }
    with pytest.raises(Exception):
        _validate_topics(bad, {"abc"})


# ---------- pipeline 行为（mock LLM + mock progress_publish） ----------

def _valid_llm_json(rows: list[MagicMock]) -> str:
    rid = str(rows[0].id)
    return json.dumps({
        "topics": [
            _good_topic("T1", rid),
            _good_topic("T2", rid),
            _good_topic("T3", rid),
        ]
    })


def _make_fake_rows(n: int = 3) -> list[MagicMock]:
    """构造 Resource ORM 行替身。"""
    rows: list[MagicMock] = []
    for i in range(n):
        r = MagicMock()
        r.id = uuid4()
        r.name = f"notes{i}.md"
        r.content_md = "x" * 300
        r.student_id = UUID("86820161-b0f0-455f-91b4-a69e49445bdf")
        rows.append(r)
    return rows


class _FakeScalarsAll:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return list(self._items)


class _FakeResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def scalars(self) -> _FakeScalarsAll:
        return _FakeScalarsAll(self._items)


class _BeginCM:
    """`async with session.begin():` 上下文管理器替身。"""

    def __init__(self, session: "_FakeSessionCM") -> None:
        self.session = session

    async def __aenter__(self) -> "_FakeSessionCM":
        return self.session

    async def __aexit__(self, *exc: Any) -> None:
        pass


class _FakeSessionCM:
    """async with factory() as session 的最小替身，覆盖 pipeline 用到的接口。"""

    def __init__(self, rows: list[Any] | None = None, *, raise_on_write: bool = False) -> None:
        self.rows = rows or []
        self.raise_on_write = raise_on_write
        self.added: list[Any] = []
        self.deleted: list[Any] = []
        self._committed = False

    async def __aenter__(self) -> "_FakeSessionCM":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        pass

    async def execute(self, stmt: Any) -> _FakeResult:
        # 所有 select 路由都返回预设 rows；update/delete 同样丢回 dummy result
        return _FakeResult(self.rows)

    def begin(self) -> _BeginCM:
        return _BeginCM(self)

    def add(self, obj: Any) -> None:
        self.added.append(obj)
        if isinstance(obj, KnowledgePoint):
            obj.kp_id = uuid4()
        if isinstance(obj, MapNode):
            obj.node_id = uuid4()

    async def flush(self) -> None:
        if self.raise_on_write:
            raise RuntimeError("simulated db failure")

    async def delete(self, obj: Any) -> None:
        self.deleted.append(obj)

    async def commit(self) -> None:
        self._committed = True


@pytest.mark.asyncio(loop_scope="session")
async def test_pipeline_publishes_5_stages_on_success() -> None:
    """happy path：5 阶段事件按顺序发布，结尾 done。"""
    rows = _make_fake_rows(3)
    fake_session = _FakeSessionCM(rows)
    events: list[tuple[str, str]] = []

    async def fake_publish(_tid: str, ev: Any) -> None:
        events.append((ev.stage.value, ev.status))

    with patch("selflearn.agents.extract_topics.progress_publish", new=AsyncMock(side_effect=fake_publish)), \
         patch("selflearn.agents.extract_topics.LLMAgent") as mock_agent_cls, \
         patch("selflearn.agents.extract_topics.get_session_factory", return_value=lambda: fake_session), \
         patch("selflearn.agents.extract_topics.llm_registry"):
        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value=_valid_llm_json(rows))
        mock_agent_cls.return_value = agent_instance

        await run_extract_topics("tid-success", [r.id for r in rows])

    stages = [e[0] for e in events]
    assert "extract_topics.parse" in stages
    assert "extract_topics.llm" in stages
    assert "extract_topics.validate" in stages
    assert "extract_topics.write" in stages
    assert "extract_topics.done" in stages
    # 最后一条必须是 done
    assert events[-1] == ("extract_topics.done", "completed")


@pytest.mark.asyncio(loop_scope="session")
async def test_pipeline_retries_once_when_llm_returns_bad_json() -> None:
    """第 1 次 LLM 返回坏 JSON，第 2 次返回合法 → 走完流程。"""
    rows = _make_fake_rows(3)
    fake_session = _FakeSessionCM(rows)
    events: list[tuple[str, str, dict[str, Any]]] = []

    async def fake_publish(_tid: str, ev: Any) -> None:
        events.append((ev.stage.value, ev.status, ev.payload))

    call_n = {"n": 0}

    async def fake_run(skill_id: str, env: Any) -> str:
        call_n["n"] += 1
        if call_n["n"] == 1:
            return "{not json"
        return _valid_llm_json(rows)

    with patch("selflearn.agents.extract_topics.progress_publish", new=AsyncMock(side_effect=fake_publish)), \
         patch("selflearn.agents.extract_topics.LLMAgent") as mock_agent_cls, \
         patch("selflearn.agents.extract_topics.get_session_factory", return_value=lambda: fake_session), \
         patch("selflearn.agents.extract_topics.llm_registry"):
        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(side_effect=fake_run)
        mock_agent_cls.return_value = agent_instance
        await run_extract_topics("tid-retry", [r.id for r in rows])

    assert call_n["n"] == 2
    llm_running = [e for e in events if e[0] == "extract_topics.llm" and e[1] == "running"]
    assert len(llm_running) == 2
    # 第二次 running 应带 retry=True
    second_payload = llm_running[1][2]
    assert second_payload.get("retry") is True
    # 最终是 done completed
    assert events[-1][0] == "extract_topics.done"
    assert events[-1][1] == "completed"


@pytest.mark.asyncio(loop_scope="session")
async def test_pipeline_marks_validate_failed_after_two_bad_llm_attempts() -> None:
    """LLM 两次都坏 → validate failed 事件 + 退出。"""
    rows = _make_fake_rows(3)
    fake_session = _FakeSessionCM(rows)
    events: list[tuple[str, str, dict[str, Any]]] = []

    async def fake_publish(_tid: str, ev: Any) -> None:
        events.append((ev.stage.value, ev.status, ev.payload))

    with patch("selflearn.agents.extract_topics.progress_publish", new=AsyncMock(side_effect=fake_publish)), \
         patch("selflearn.agents.extract_topics.LLMAgent") as mock_agent_cls, \
         patch("selflearn.agents.extract_topics.get_session_factory", return_value=lambda: fake_session), \
         patch("selflearn.agents.extract_topics.llm_registry"):
        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(side_effect=["bad", "still bad"])
        mock_agent_cls.return_value = agent_instance
        await run_extract_topics("tid-fail", [r.id for r in rows])

    statuses = {s: st for s, st, _ in events}
    assert statuses["extract_topics.validate"] == "failed"
    assert "extract_topics.write" not in statuses
    assert "extract_topics.done" not in statuses


@pytest.mark.asyncio(loop_scope="session")
async def test_pipeline_db_write_failure_marks_write_failed() -> None:
    """事务内 flush 抛错 → write failed 事件，不推 done。"""
    rows = _make_fake_rows(3)
    fake_session = _FakeSessionCM(rows, raise_on_write=True)
    events: list[tuple[str, str]] = []

    async def fake_publish(_tid: str, ev: Any) -> None:
        events.append((ev.stage.value, ev.status))

    with patch("selflearn.agents.extract_topics.progress_publish", new=AsyncMock(side_effect=fake_publish)), \
         patch("selflearn.agents.extract_topics.LLMAgent") as mock_agent_cls, \
         patch("selflearn.agents.extract_topics.get_session_factory", return_value=lambda: fake_session), \
         patch("selflearn.agents.extract_topics.llm_registry"):
        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value=_valid_llm_json(rows))
        mock_agent_cls.return_value = agent_instance
        await run_extract_topics("tid-dbfail", [r.id for r in rows])

    statuses = {s: st for s, st in events}
    assert statuses["extract_topics.write"] == "failed"
    assert "extract_topics.done" not in statuses


@pytest.mark.asyncio(loop_scope="session")
async def test_pipeline_writes_drafts_as_kps_and_nodes() -> None:
    """happy path 时：应给每个 draft INSERT 一个 KP + 一个 MapNode（用 mock session 计 add 次数）。"""
    rows = _make_fake_rows(3)
    fake_session = _FakeSessionCM(rows)
    events: list[tuple[str, str]] = []

    async def fake_publish(_tid: str, ev: Any) -> None:
        events.append((ev.stage.value, ev.status))

    with patch("selflearn.agents.extract_topics.progress_publish", new=AsyncMock(side_effect=fake_publish)), \
         patch("selflearn.agents.extract_topics.LLMAgent") as mock_agent_cls, \
         patch("selflearn.agents.extract_topics.get_session_factory", return_value=lambda: fake_session), \
         patch("selflearn.agents.extract_topics.llm_registry"):
        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value=_valid_llm_json(rows))
        mock_agent_cls.return_value = agent_instance
        await run_extract_topics("tid-orphan", [r.id for r in rows])

    kp_added = [o for o in fake_session.added if isinstance(o, KnowledgePoint)]
    node_added = [o for o in fake_session.added if isinstance(o, MapNode)]
    assert len(kp_added) == 3
    assert len(node_added) == 3
    # write 阶段完成 + done 阶段完成
    assert ("extract_topics.write", "completed") in events
    assert ("extract_topics.done", "completed") in events


# ---------------------------------------------------------------------------
# B1-fix: 超时常量稳定性 (上游 LLM 响应波动 40s-100s, 旧值 90s 易 race)
# ---------------------------------------------------------------------------


def test_timeouts_above_observed_llm_latency() -> None:
    """实测 LLM 响应时间 41s-94s 不等, 常量必须留出 ≥150s 缓冲."""
    from selflearn.agents.extract_topics import TIMEOUT_LLM_SEC, TIMEOUT_TOTAL_SEC

    assert TIMEOUT_LLM_SEC >= 150, (
        f"TIMEOUT_LLM_SEC={TIMEOUT_LLM_SEC} 低于观察到的 P99≈94s, "
        "需 ≥150s 避免 race condition"
    )
    assert TIMEOUT_TOTAL_SEC >= 180, (
        f"TIMEOUT_TOTAL_SEC={TIMEOUT_TOTAL_SEC} 总预算不足以覆盖 "
        "parse(~1s) + llm(~94s) + validate+write(~1s)"
    )
    # 总超时必须 ≥ 单次 LLM 超时
    assert TIMEOUT_TOTAL_SEC > TIMEOUT_LLM_SEC
