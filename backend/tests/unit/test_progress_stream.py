"""Redis Stream progress 模块单测。"""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from selflearn.progress.stages import ProgressEvent, Stage

pytestmark = pytest.mark.asyncio


async def test_progress_event_roundtrip() -> None:
    """ProgressEvent.to_redis_fields / from_redis_fields 必须可逆。"""
    e = ProgressEvent(
        stage=Stage.PROFILE,
        status="running",
        payload={"k": 1},
        timestamp=datetime(2026, 7, 12, 0, 0, 0),
    )
    fields = e.to_redis_fields()
    parsed = ProgressEvent.from_redis_fields({k: v for k, v in fields.items()})
    assert parsed.stage == Stage.PROFILE
    assert parsed.status == "running"
    assert parsed.payload == {"k": 1}


async def test_progress_consume_uses_0_0_cursor() -> None:
    """progress_consume 必须从 '0-0' 起步（V1.1 修复点）。"""
    with patch("selflearn.progress.stream.get_redis") as mock_get_redis:
        from selflearn.progress import stream as stream_mod

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        # mock xread 返回 1 条，然后空
        mock_redis.xread.side_effect = [
            [
                ("stream:abc", [("1-0", {"stage": "profile", "status": "running",
                                          "payload": "{}", "timestamp": "2026-07-12T00:00:00"})])
            ],
            [],
        ]

        consumed: list[ProgressEvent] = []

        async def collect() -> None:
            gen = stream_mod.progress_consume("abc")
            async for ev in gen:
                consumed.append(ev)
                if len(consumed) >= 1:
                    return

        await asyncio.wait_for(collect(), timeout=1.0)

        # 关键断言：第一次 xread 调用用的 last_id 必须是 "0-0"
        first_call = mock_redis.xread.call_args_list[0]
        assert first_call.args[0] == {"stream:abc": "0-0"}, (
            f"cursor must start at '0-0', got {first_call.args[0]}"
        )