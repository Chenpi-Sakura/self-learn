"""启动入口：通过 --role 区分 gateway / worker / all。"""
from __future__ import annotations

import argparse
import asyncio
import sys


def parse_role() -> str:
    p = argparse.ArgumentParser()
    p.add_argument("--role", choices=["gateway", "worker", "all"], default="all")
    return p.parse_args().role


async def run_gateway() -> None:
    import uvicorn

    from selflearn.config import get_settings

    s = get_settings()
    uvicorn.run(
        "selflearn.gateway.app:create_app",
        factory=True,
        host=s.gateway_host,
        port=s.gateway_port,
        log_level=s.log_level.lower(),
    )


async def run_worker() -> None:
    """Worker 进程入口：setup_logging + setup_tracing + register skill + register_agent + consume。

    LLM adapter 由 selflearn.llm.registry 模块加载时自动注册（MockLLMAdapter），
    所以这里不需要显式 register。PingAgent.run() 调 llm_registry.default() 即可拿到 mock。
    """
    from selflearn.agents.worker import register_agent, run_worker as consume_loop
    from selflearn.config import get_settings
    from selflearn.core.logging import setup_logging
    from selflearn.core.tracing import setup_tracing
    from selflearn.infra.rabbit import setup_topology
    from selflearn.skills.builtin.ping import agent_info, register as register_skill
    from selflearn.skills.library import load_all

    s = get_settings()
    setup_logging(s.log_level)
    setup_tracing(s.otel_service_name + "-worker", s.otel_exporter_otlp_endpoint)
    load_all()
    register_skill()
    await setup_topology()
    register_agent(agent_info())
    await consume_loop(queue_name="agent.ping.work", routing_key="ping_agent.#")


def main() -> int:
    role = parse_role()
    if role == "gateway":
        asyncio.run(run_gateway())
    elif role == "worker":
        asyncio.run(run_worker())
    else:
        print("[main] role=all: run gateway + worker in same process (dev only)")
        asyncio.run(run_gateway())
    return 0


if __name__ == "__main__":
    sys.exit(main())
