"""启动入口：通过 --role 区分 gateway / worker / all。"""
from __future__ import annotations

import argparse
import asyncio
import sys

from selflearn.core.logging import get_logger

log = get_logger("main")


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
    """Worker 进程入口：P5 新架构 — LLMAgent + ReviewStage + Director chain 串起来。

    - 订阅单队列 `agent.mvp.work`（topic exchange EX配 `#`），
      全部 envelope 走 Director chain（dispatch(env, agent, review)）。
    - LLM adapter 由 selflearn.llm.registry 模块加载时自动注册（MockLLMAdapter），
      这里不需要显式 register。
    """
    from selflearn.agents.core import LLMAgent
    from selflearn.agents.review_stage import ReviewStage
    from selflearn.agents.scheduler import dispatch
    from selflearn.agents.worker import run_worker as consume_loop
    from selflearn.config import get_settings
    from selflearn.core.logging import setup_logging
    from selflearn.core.envelope import Envelope
    from selflearn.core.tracing import setup_tracing
    from selflearn.infra.rabbit import setup_topology
    from selflearn.llm.registry import llm_registry
    from selflearn.mcp_client import mcp_client_lifespan
    from selflearn.skills.library import _skill_library, load_all

    s = get_settings()
    setup_logging(s.log_level)
    setup_tracing(s.otel_service_name + "-worker", s.otel_exporter_otlp_endpoint)
    load_all()
    expected_skills = {
        "skill.lecture.generate",
        "skill.exercise.generate",
        "skill.review.exercise.llm",
        "skill.director.start",
    }
    loaded = set(_skill_library.keys())
    missing = expected_skills - loaded
    if missing:
        raise RuntimeError(f"skills_missing:{sorted(missing)}")
    log.info("skills.preflight_ok", count=len(loaded))
    await setup_topology()

    async with mcp_client_lifespan() as mcp:
        agent = LLMAgent(mcp, llm_registry)
        review = ReviewStage(agent, mcp)

        async def director_dispatch(env: Envelope) -> Envelope | None:
            return await dispatch(env, agent, review)

        await consume_loop(
            queue_name="agent.mvp.work",
            routing_key="#",
            dispatch_fn=director_dispatch,
        )


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
