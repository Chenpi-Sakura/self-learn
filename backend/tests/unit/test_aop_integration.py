"""AOP 横切点集成测试：envelope.publish / progress.publish 触发 hook。"""
from unittest.mock import AsyncMock, patch

import pytest

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.observability.hooks import hook_bus


@pytest.mark.asyncio
async def test_publish_envelope_emits_hook_event() -> None:
    hook_bus.clear()

    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gw", id="t"),
        target=ActorRef(type="skill", id="skill.profile.build"),
    )

    with patch("selflearn.infra.bus.get_connection") as conn_mock:
        conn_mock.return_value = AsyncMock()
        from selflearn.infra.bus import publish_envelope

        await publish_envelope(env, routing_key="test.key")

    snap = hook_bus.snapshot()
    assert any(
        e["kind"] == "envelope.publish" and e["status"] == "ok" for e in snap
    ), f"publish_envelope 未触发 hook: {snap}"


@pytest.mark.asyncio
async def test_progress_publish_emits_hook_event() -> None:
    """progress_publish 是横切点之一。"""
    hook_bus.clear()

    # progress/stream.py 无 _publish_to_redis helper；它调用 get_redis() 后 xadd/expire。
    # patch get_redis 返回 AsyncMock，避免连真实 Redis。
    with patch("selflearn.progress.stream.get_redis") as redis_mock:
        redis_mock.return_value = AsyncMock()
        from selflearn.progress.stages import ProgressEvent, Stage
        from selflearn.progress.stream import progress_publish

        await progress_publish(
            "trace-test",
            ProgressEvent(stage=Stage.PROFILE, status="running"),
        )

    snap = hook_bus.snapshot()
    assert any(
        e["kind"] == "progress.publish" and e["status"] == "ok" for e in snap
    ), f"progress_publish 未触发 hook: {snap}"
