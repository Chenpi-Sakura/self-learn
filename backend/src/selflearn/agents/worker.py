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
    tracer = get_tracer("worker")
    with tracer.start_as_current_span("agent.consume") as span:
        span.set_attribute("selflearn.trace_id", env.trace_id)
        from selflearn.agents.scheduler import dispatch  # 避免循环导入

        try:
            reply = await dispatch(env)
            if reply:
                # 占位：Task 9 实现 publish reply
                log.info("agent.reply_pending", trace_id=env.trace_id, action=reply.action)
        except AppError as e:
            log.warning("agent.app_error", code=e.code.value, msg=e.message)
        except Exception as e:  # noqa: BLE001
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
