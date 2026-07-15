"""Worker 进程主循环。"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import time

from selflearn.agents.registry import AgentInfo, agent_registry
from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError
from selflearn.core.logging import get_logger
from selflearn.core.tracing import get_tracer
from selflearn.infra.bus import consume_envelope

log = get_logger("worker")


async def handle(env: Envelope) -> None:
    """Stage 3-compatible message handler using the legacy scheduler."""
    await handle_with_dispatch(env, dispatch_fn=None)


async def handle_with_dispatch(
    env: Envelope,
    dispatch_fn: Callable[[Envelope], Awaitable[Envelope | None]] | None,
) -> None:
    """Handle one message with an optionally injected async dispatcher."""
    # 防御：replies 走 dispatch 会撞 target.id='smoke'（sender.id），_AGENT_FOR_SKILL 找不到。
    # skill.completed 是 5 个 Stage 3 Agent + PingAgent 唯一终止 action。
    if env.action == "skill.completed":
        log.info("agent.skip_reply", trace_id=env.trace_id, action=env.action)
        return
    from selflearn.infra.redis_client import get_redis
    from selflearn.infra.bus import publish_envelope

    if dispatch_fn is None:
        from selflearn.agents.scheduler import dispatch_old

        dispatch_fn = dispatch_old

    tracer = get_tracer("worker")
    with tracer.start_as_current_span("agent.consume") as span:
        span.set_attribute("selflearn.trace_id", env.trace_id)
        r = get_redis()
        try:
            reply = await dispatch_fn(env)
            if reply:
                await r.set(f"trace:{reply.trace_id}:status",
                            str(reply.payload.get("status", "completed")), ex=60)
                if "reply" in reply.payload:
                    await r.set(f"trace:{reply.trace_id}:reply",
                                str(reply.payload["reply"]), ex=60)
                await publish_envelope(reply, routing_key=f"skill.{reply.action}")
                log.info("agent.replied", trace_id=reply.trace_id, action=reply.action)
            else:
                await r.set(f"trace:{env.trace_id}:status", "completed", ex=60)
                await r.set(f"trace:{env.trace_id}:reply", "", ex=60)
                log.info("agent.no_reply", trace_id=env.trace_id)
        except AppError as e:
            await r.set(f"trace:{env.trace_id}:status", "failed", ex=60)
            await r.set(f"trace:{env.trace_id}:reply", f"error: {e.message}", ex=60)
            log.warning("agent.app_error", code=e.code.value, msg=e.message)
        except Exception as e:  # noqa: BLE001
            await r.set(f"trace:{env.trace_id}:status", "failed", ex=60)
            await r.set(f"trace:{env.trace_id}:reply", f"error: {e!s}", ex=60)
            log.error("agent.unexpected", error=str(e))


async def run_worker(
    queue_name: str,
    routing_key: str,
    dispatch_fn: Callable[[Envelope], Awaitable[Envelope | None]] | None = None,
) -> None:
    log.info("worker.start", queue=queue_name, routing_key=routing_key)

    async def callback(env: Envelope) -> None:
        await handle_with_dispatch(env, dispatch_fn)

    async for _ in consume_envelope(queue_name, routing_key, callback):
        await asyncio.sleep(0)


def register_agent(info: AgentInfo) -> None:
    agent_registry.register(info)
    log.info("agent.registered", agent_id=info.agent_id, skills=info.skills)


def heartbeat_loop(agent_id: str) -> None:
    while True:
        agent_registry.heartbeat(agent_id)
        time.sleep(10)
