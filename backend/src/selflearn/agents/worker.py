"""Worker 进程主循环。"""
from __future__ import annotations

import asyncio
import time

from selflearn.agents.registry import AgentInfo, agent_registry
from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError
from selflearn.core.logging import get_logger
from selflearn.core.tracing import get_tracer
from selflearn.infra.bus import consume_envelope

log = get_logger("worker")


async def handle(env: Envelope) -> None:
    """Worker 主循环的每条消息处理函数。
    写 Redis 给 gateway 读（status + reply）+ publish reply envelope。"""
    from selflearn.agents.scheduler import dispatch
    from selflearn.infra.redis_client import get_redis
    from selflearn.infra.bus import publish_envelope

    tracer = get_tracer("worker")
    with tracer.start_as_current_span("agent.consume") as span:
        span.set_attribute("selflearn.trace_id", env.trace_id)
        r = get_redis()
        try:
            reply = await dispatch(env)
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


async def run_worker(queue_name: str, routing_key: str) -> None:
    log.info("worker.start", queue=queue_name, routing_key=routing_key)
    async for _ in consume_envelope(queue_name, routing_key, handle):
        await asyncio.sleep(0)


def register_agent(info: AgentInfo) -> None:
    agent_registry.register(info)
    log.info("agent.registered", agent_id=info.agent_id, skills=info.skills)


def heartbeat_loop(agent_id: str) -> None:
    while True:
        agent_registry.heartbeat(agent_id)
        time.sleep(10)
