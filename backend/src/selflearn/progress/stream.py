"""Redis Stream 真流核心（V1.1 修复：last_id 从 0-0 起步）。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from selflearn.infra.redis_client import get_redis
from selflearn.progress.stages import ProgressEvent


PROGRESS_STREAM_PREFIX = "stream:"
PROGRESS_STREAM_TTL_SECONDS = 3600


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
    """
    r = get_redis()
    key = f"{PROGRESS_STREAM_PREFIX}{trace_id}"
    last_id: Any = "0-0"  # V1.1 关键修复
    while True:
        result: Any = await cast(Any, r.xread)({key: last_id}, block=5000, count=10)
        if not result:
            continue
        for _stream_key, entries in result:
            for entry in entries:
                entry_id: Any = entry[0]
                raw_fields: Any = entry[1]
                fields_dict: dict[object, object] = dict(raw_fields)
                yield ProgressEvent.from_redis_fields(fields_dict)
                last_id = entry_id