"""Redis Stream 真流核心（V1.1 修复：last_id 从 0-0 起步）。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from selflearn.infra.redis_client import get_redis
from selflearn.observability.decorators import hook
from selflearn.progress.stages import ProgressEvent


PROGRESS_STREAM_PREFIX = "stream:"
PROGRESS_STREAM_TTL_SECONDS = 3600


@hook("progress.publish")
async def progress_publish(trace_id: str, event: ProgressEvent) -> None:
    """worker 任意代码点调用，往 stream:{trace_id} 写一条进度。"""
    r = get_redis()
    key = f"{PROGRESS_STREAM_PREFIX}{trace_id}"
    fields: Any = event.to_redis_fields()
    # redis-py stubs 在严格模式下要求 dict[Any, Any]（运行时 str→str 已合法）。
    await cast(Any, r.xadd)(key, fields, maxlen=100, approximate=True)
    await r.expire(key, PROGRESS_STREAM_TTL_SECONDS)


async def progress_consume(trace_id: str) -> AsyncIterator[ProgressEvent]:
    """Gateway SSE 端点调用，裸 XREAD 从 0-0 起步避免事件丢失。

    redis-py xread 返回类型在 stubs 里松散；运行时是
    list[tuple[str, list[tuple[str, dict[str, str]]]]]（decode_responses=True）。

    block=30000 (30s) 周期：
    - 实测 LLM 响应 41s-123s 不稳定，旧 block=5000 期间如遇 redis socket 抖动
      会抛 redis.TimeoutError，断开 SSE（前端看到"卡在 LLM"）
    - block=0 永久阻塞会让 sse_starlette 没机会 yield / flush，客户端 idle
      timeout 直接切断
    - 30s 是折中：远小于典型客户端 idle timeout (3min+)，又足够让 redis 撑过
      大部分临时抖动；如真 timeout，由内层 while 重试而不向上抛，避免 SSE
      因单次 redis 抖动断开（last_id 已在内存，进度不丢）。
    """
    r = get_redis()
    key = f"{PROGRESS_STREAM_PREFIX}{trace_id}"
    last_id: Any = "0-0"  # V1.1 关键修复
    while True:
        try:
            result: Any = await cast(Any, r.xread)({key: last_id}, block=30000, count=10)
        except Exception as _:  # noqa: BLE001 — redis.TimeoutError / ConnectionError 都不向上抛
            # 单次 xread 失败不终结 SSE 流：等待 1s 后重试。last_id 保留在内存，
            # 下次成功时会从断点继续读，不丢事件。
            import asyncio as _asyncio
            await _asyncio.sleep(1.0)
            continue
        if not result:
            continue
        for _stream_key, entries in result:
            for entry in entries:
                entry_id: Any = entry[0]
                raw_fields: Any = entry[1]
                fields_dict: dict[object, object] = dict(raw_fields)
                yield ProgressEvent.from_redis_fields(fields_dict)
                last_id = entry_id