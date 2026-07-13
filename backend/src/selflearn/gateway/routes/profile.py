"""Profile 路由 — POST /init (Stage 2) + POST /build (Stage 3) + GET /status + GET /stream (SSE)。

SSE 实现：Stage 3 真流（progress_consume → Redis XREAD from 0-0）。
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.infra.bus import publish_envelope
from selflearn.infra.redis_client import get_redis
from selflearn.progress.stream import progress_consume
from selflearn.schemas.profile import (
    ProfileBuildRequest,
    ProfileBuildResponse,
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


# ---------------------------------------------------------------------------
# Stage 2 兼容入口（不要改：smoke 测试依赖）
# ---------------------------------------------------------------------------


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
    await publish_envelope(env, routing_key="ping_agent.skill.profile.init")
    return ProfileInitResponse(trace_id=env.trace_id)


@router.get("/init/{trace_id}/status", response_model=ProfileStatusResponse)
async def get_status(trace_id: str) -> ProfileStatusResponse:
    r = get_redis()
    status_raw = await r.get(f"trace:{trace_id}:status")
    reply_raw = await r.get(f"trace:{trace_id}:reply")
    status_str = _coerce_str(status_raw) or "unknown"
    reply_str = _coerce_str(reply_raw)
    return ProfileStatusResponse(trace_id=trace_id, status=status_str, reply=reply_str)


# ---------------------------------------------------------------------------
# Stage 3 扩展：/build 入参 + SSE 真流（V1.1 修复：FAILED 关闭连接）
# ---------------------------------------------------------------------------


@router.post("/build", response_model=ProfileBuildResponse, status_code=202)
async def build_profile(body: ProfileBuildRequest) -> ProfileBuildResponse:
    """Stage 3 入口：触发 ProfileAgent 生成初始画像（dimensions + tags）。"""
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.profile.build"),
        payload={
            "student_id": str(body.student_id),
            "dimensions": body.dimensions,
            "tags": body.tags,
        },
    )
    r = get_redis()
    await r.set(f"trace:{env.trace_id}:status", "running", ex=3600)
    await publish_envelope(env, routing_key="profile.skill.profile.build")
    return ProfileBuildResponse(trace_id=env.trace_id)


async def _stream_events(trace_id: str) -> AsyncIterator[dict[str, str]]:
    """SSE 事件生成器：从 Redis Stream 读取进度，FAILED/COMPLETED 时关闭。"""
    async for ev in progress_consume(trace_id):
        data = json.dumps(
            {
                "stage": ev.stage.value,
                "status": ev.status,
                "payload": ev.payload,
            },
            ensure_ascii=False,
        )
        yield {"event": "progress", "data": data}
        if ev.stage.value in ("completed", "failed"):
            final_payload = json.dumps(
                {"status": ev.status, "payload": ev.payload},
                ensure_ascii=False,
            )
            yield {
                "event": "completed" if ev.stage.value == "completed" else "error",
                "data": final_payload,
            }
            return


@router.get("/init/{trace_id}/stream")
async def stream_init(trace_id: str) -> EventSourceResponse:
    """Stage 3 SSE 真流（替代 Stage 2 轮询 fallback）。"""
    return EventSourceResponse(_stream_events(trace_id))