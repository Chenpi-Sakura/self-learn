"""EventSource 真连 /api/resources/extract_topics/stream 接收 5 阶段进度。

仿 backend/tests/integration/test_smoke_mvp.py：注入 fakeredis，再用
ASGITransport 起 ASGI app，让 real httpx stream GET
/api/resources/extract_topics/stream。事件 producer 模拟真实 pipeline 节奏：
先发 running 再发 completed，中间留 50ms 间隔，让 consumer 一个一个消费（避免
单批 xread 把 5 阶段全部塞进同一 batch，再被 SSE wrapper 的 `return` 提前结束）。
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import fakeredis.aioredis as fakeaioredis
import pytest
from httpx import ASGITransport, AsyncClient

from selflearn.gateway.app import create_app
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.progress.stream import progress_consume, progress_publish

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def fake_redis() -> AsyncIterator[fakeaioredis.FakeRedis]:
    """注入 fakeredis 到 selflearn.infra.redis_client._client。"""
    import selflearn.infra.redis_client as rc

    fake = fakeaioredis.FakeRedis(decode_responses=True)
    original = rc._client
    rc._client = fake
    try:
        yield fake
    finally:
        rc._client = original
        await fake.aclose()


async def test_sse_pushes_5_stage_events_then_completed(fake_redis: fakeaioredis.FakeRedis) -> None:
    """模拟真实 pipeline 节奏：每个阶段 running+completed 间留 100ms 间隔。

    SSE consumer 按序推进，5 个阶段都能被前端看到（progressStatus 推进 + 终态
    completed）。这是 ProgressOverlay 实际使用的语义。
    """
    task_id = "integration-test-task-1234"

    expected_short_keys = {"parse", "llm", "validate", "write", "done"}

    # 模拟真实 pipeline 节奏：每个阶段先 running，再 completed，间隔 100ms
    # 让 consumer 一边消费一边 producer 推，避免 5 阶段挤在同一 xread batch 里
    # 让 wrapper `return` 提前结束。
    async def _producer() -> None:
        await asyncio.sleep(0.2)  # 等 SSE 客户端先连上
        for st in [
            Stage.EXTRACT_TOPICS_PARSE,
            Stage.EXTRACT_TOPICS_LLM,
            Stage.EXTRACT_TOPICS_VALIDATE,
            Stage.EXTRACT_TOPICS_WRITE,
            Stage.EXTRACT_TOPICS_DONE,
        ]:
            await progress_publish(
                task_id, ProgressEvent(stage=st, status="running")
            )
            await asyncio.sleep(0.1)
            await progress_publish(
                task_id, ProgressEvent(stage=st, status="completed")
            )
            await asyncio.sleep(0.1)

    app = create_app()
    transport = ASGITransport(app=app)

    received_stages: list[str] = []
    got_completed = False

    async with AsyncClient(transport=transport, base_url="http://test", timeout=20) as ac:
        # 启动 producer 与 SSE 连接并发
        producer_task = asyncio.create_task(_producer())

        async with ac.stream(
            "GET", f"/api/resources/extract_topics/stream?task_id={task_id}"
        ) as resp:
            assert resp.status_code == 200, await resp.aread()
            async for line in resp.aiter_lines():
                # SSE 行格式: "event: ..." / "data: {...}" / ""(分隔)
                if line.startswith("data:"):
                    payload_raw = line[len("data:"):].strip()
                    payload = json.loads(payload_raw)
                    # 终态事件：data 不含 stage，只有 status
                    if payload.get("status") == "completed" and "stage" not in payload:
                        got_completed = True
                        break
                    stage = payload.get("stage")
                    if stage and stage != "completed":
                        received_stages.append(stage)

        await producer_task

    assert got_completed, "SSE 必须 emit 一次 completed 终态"
    # 5 个阶段 short key 至少都被推到
    short_keys = {s.split(".")[-1] for s in received_stages}
    assert expected_short_keys <= short_keys, (
        f"missing stages {expected_short_keys - short_keys} in {received_stages}"
    )


async def test_sse_returns_error_event_when_pipeline_failed(
    fake_redis: fakeaioredis.FakeRedis,
) -> None:
    """当 producer 推一条 FAILED 后停止，SSE 必须 emit event: error 并终止。"""
    task_id = "integration-test-task-failed"

    async def _producer() -> None:
        await asyncio.sleep(0.2)
        await progress_publish(
            task_id,
            ProgressEvent(
                stage=Stage.EXTRACT_TOPICS_WRITE,
                status="failed",
                payload={"error": "synthetic db failure"},
            ),
        )

    app = create_app()
    transport = ASGITransport(app=app)

    text_chunks: list[str] = []
    async with AsyncClient(transport=transport, base_url="http://test", timeout=15) as ac:
        producer_task = asyncio.create_task(_producer())

        async with ac.stream(
            "GET", f"/api/resources/extract_topics/stream?task_id={task_id}"
        ) as resp:
            assert resp.status_code == 200
            async for chunk in resp.aiter_text():
                text_chunks.append(chunk)

        await producer_task

    text = "".join(text_chunks)
    assert "event: error" in text, f"expected event: error, got:\n{text}"
    assert "event: progress" in text, f"expected at least 1 progress event, got:\n{text}"
    # 终态 payload 应带原 error 字段
    assert "synthetic db failure" in text, f"error payload missing, got:\n{text}"


async def test_progress_consume_yields_all_events_for_extract_topics(
    fake_redis: fakeaioredis.FakeRedis,
) -> None:
    """直接验证 progress_consume 能消费 5 阶段事件（端到端 SSE 的内部支撑）。

    在事件全部预先写入的场景下，fakeredis 单次 xread 会一次返回 5 条；这里
    消费者循环 yield 后人工中断，证明确实能拿到 5 条不丢失（Fix A 的回归）。
    """
    task_id = "integration-test-task-consume"

    expected = [
        Stage.EXTRACT_TOPICS_PARSE,
        Stage.EXTRACT_TOPICS_LLM,
        Stage.EXTRACT_TOPICS_VALIDATE,
        Stage.EXTRACT_TOPICS_WRITE,
        Stage.EXTRACT_TOPICS_DONE,
    ]
    for st in expected:
        await progress_publish(task_id, ProgressEvent(stage=st, status="completed"))

    seen: list[str] = []

    async def collect() -> None:
        async for ev in progress_consume(task_id):
            seen.append(ev.stage.value)
            if len(seen) >= 5:
                return

    await asyncio.wait_for(collect(), timeout=5.0)
    assert seen == [s.value for s in expected]