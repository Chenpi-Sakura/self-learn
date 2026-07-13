"""MVP 端到端集成测试（V1.1: last_id=0-0 起步 + Director FAILED 传播验证）。

本测试**不依赖 docker / 外部 Redis**：通过 fakeredis 在内存中模拟 Redis Streams，
验证 Stage 3 两个关键修复点。

- Fix A (Task 4): progress_consume 必须能从 0-0 起步读到写入的全部历史事件，
  而不是只从订阅时刻开始消费（避免前端漏掉早期 PROFILE / PLAN 进度）。
- Fix B (Task 11): 业务失败路径（此处用 progress_publish 直推 FAILED 模拟
  DirectorAgent._emit_failed）写入的 Stage.FAILED 事件必须可在流上被消费到。
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import fakeredis.aioredis as fakeaioredis
import pytest

from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.progress.stream import progress_consume, progress_publish

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def fake_redis() -> AsyncIterator[fakeaioredis.FakeRedis]:
    """提供一个 fakeredis 异步客户端并注入 selflearn.infra.redis_client._client。

    yield 后恢复原状，避免污染其它测试。
    """
    import selflearn.infra.redis_client as rc

    fake = fakeaioredis.FakeRedis(decode_responses=True)
    original = rc._client
    rc._client = fake
    try:
        yield fake
    finally:
        rc._client = original
        await fake.aclose()


async def test_progress_consume_reads_history_from_zero(fake_redis: fakeaioredis.FakeRedis) -> None:
    """V1.1 Fix A：先写 3 条 progress，再从 0-0 消费，必须能拿到全部 3 条。

    如果 last_id 错误地起步为 '$'（仅订阅新事件），前 2 条会丢失，本测试 FAIL。
    """
    trace_id = "integ-history-zero"

    # 写入 3 条进度（消费者尚未启动）
    await progress_publish(trace_id, ProgressEvent(stage=Stage.PROFILE, status="running"))
    await progress_publish(trace_id, ProgressEvent(stage=Stage.PROFILE, status="completed"))
    await progress_publish(trace_id, ProgressEvent(stage=Stage.PLAN, status="running"))

    seen: list[tuple[str, str]] = []

    async def collect() -> None:
        async for ev in progress_consume(trace_id):
            seen.append((ev.stage.value, ev.status))
            if len(seen) >= 3:
                return

    await asyncio.wait_for(collect(), timeout=5.0)

    assert ("profile", "running") in seen
    assert ("profile", "completed") in seen
    assert ("plan", "running") in seen


async def test_director_fail_publishes_failed_event(fake_redis: fakeaioredis.FakeRedis) -> None:
    """V1.1 Fix B：失败事件必须可被消费到（Stage.FAILED 传播验证）。

    模拟 DirectorAgent 失败路径（Task 11）：run() 捕获异常后
    _emit_failed() 推一条 Stage.FAILED 进度。验证 SSE 消费者能拿到。
    """
    trace_id = "integ-fail-direct"

    # 模拟 DirectorAgent._emit_failed 的写入
    await progress_publish(
        trace_id,
        ProgressEvent(
            stage=Stage.FAILED,
            status="failed",
            payload={"code": "agent_internal_error", "message": "synthetic failure"},
        ),
    )

    seen: list[ProgressEvent] = []

    async def collect() -> None:
        async for ev in progress_consume(trace_id):
            seen.append(ev)
            if ev.stage == Stage.FAILED:
                return

    await asyncio.wait_for(collect(), timeout=5.0)

    assert any(e.stage == Stage.FAILED for e in seen), (
        f"expected Stage.FAILED in stream, got stages: {[e.stage for e in seen]}"
    )
    failed_event = next(e for e in seen if e.stage == Stage.FAILED)
    assert failed_event.payload.get("code") == "agent_internal_error"
