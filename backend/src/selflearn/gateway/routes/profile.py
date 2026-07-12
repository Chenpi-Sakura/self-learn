"""Profile 路由 — POST /init + GET /status + GET /stream (SSE)（v4 § 3.6 SSE 骨架）。"""
from __future__ import annotations

import asyncio
import json

from collections.abc import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.infra.bus import publish_envelope
from selflearn.infra.redis_client import get_redis
from selflearn.schemas.profile import (
    ProfileInitRequest,
    ProfileInitResponse,
    ProfileStatusResponse,
)

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _coerce_str(v: object) -> str | None:
    if v is None:
        return None
    if isinstance(v, bytes):
        return v.decode("utf-8")
    return str(v)


@router.post("/init", response_model=ProfileInitResponse, status_code=202)
async def init_profile(body: ProfileInitRequest) -> ProfileInitResponse:
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.profile.init"),
        payload={"student_id": str(body.student_id), "topic": body.topic},
    )
    r = get_redis()
    await r.set(f"trace:{env.trace_id}:status", "running", ex=60)
    await publish_envelope(env, routing_key="profile.skill.profile.init")
    return ProfileInitResponse(trace_id=env.trace_id)


@router.get("/init/{trace_id}/status", response_model=ProfileStatusResponse)
async def get_status(trace_id: str) -> ProfileStatusResponse:
    r = get_redis()
    status_raw = await r.get(f"trace:{trace_id}:status")
    reply_raw = await r.get(f"trace:{trace_id}:reply")
    status_str = _coerce_str(status_raw) or "unknown"
    reply_str = _coerce_str(reply_raw)
    return ProfileStatusResponse(trace_id=trace_id, status=status_str, reply=reply_str)


@router.get("/init/{trace_id}/stream")
async def stream_init(trace_id: str) -> EventSourceResponse:
    async def event_gen() -> AsyncIterator[dict[str, str]]:
        r = get_redis()
        try:
            # Stage 2 fallback：轮询 ≤ 1s 拿结果
            for _ in range(10):
                status_str = _coerce_str(await r.get(f"trace:{trace_id}:status")) or "running"
                yield {"event": "status", "data": status_str}
                if status_str in ("completed", "failed"):
                    reply = _coerce_str(await r.get(f"trace:{trace_id}:reply"))
                    payload = json.dumps({"status": status_str, "reply": reply})
                    yield {
                        "event": "completed" if status_str == "completed" else "error",
                        "data": payload,
                    }
                    return
                await asyncio.sleep(0.1)
            yield {"event": "error", "data": json.dumps({"status": "timeout"})}
        finally:
            pass  # Stage 3 加 Redis Stream 订阅清理

    return EventSourceResponse(event_gen())