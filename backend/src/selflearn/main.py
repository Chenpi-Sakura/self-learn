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

    Stage 3 wiring（Rule #13 第四子规则 + Task 12 brief）：
    - 订阅单队列 `agent.mvp.work`（topic exchange EXCHANGE_EVENTS 通配 `#`），
      所有 5 个 Stage 3 Agent（Profile / Plan / Exercise / Review / Director）+ Stage 2 PingAgent
      共享同一个 consume_loop；路由分派完全交给 SkillBasedScheduler（_AGENT_FOR_SKILL + skill_registry fallback）。
    - 每个 Agent 都注册到 worker's agent_registry（保持 Stage 2 register_agent 语义）；
      实际 Agent class 入口通过 dispatch(env) 拿到 target.id 命中。
    - LLM adapter 由 selflearn.llm.registry 模块加载时自动注册（MockLLMAdapter），
      所以这里不需要显式 register。
    """
    from selflearn.agents.builtin.director_agent import DirectorAgent
    from selflearn.agents.builtin.exercise_agent import ExerciseAgent
    from selflearn.agents.builtin.plan_agent import PlanAgent
    from selflearn.agents.builtin.profile_agent import ProfileAgent
    from selflearn.agents.builtin.review_agent import ReviewAgent
    from selflearn.agents.registry import AgentInfo
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
    # Register PingAgent（Stage 2 兼容）
    register_agent(agent_info())
    # Register 5 个 Stage 3 Agent（仅占 agent_registry，路由靠 SkillBasedScheduler）
    for agent_cls in (ProfileAgent, PlanAgent, ExerciseAgent, ReviewAgent, DirectorAgent):
        info = AgentInfo(
            agent_id=agent_cls.agent_id,
            agent_type=agent_cls.agent_type,
            skills=getattr(agent_cls, "skills", []),
            status="idle",
            queue=agent_cls.queue,
            max_concurrency=agent_cls.max_concurrency,
        )
        register_agent(info)
    # 单队列 + topic 通配 `#` → 所有 envelope 走 SkillBasedScheduler.dispatch
    await consume_loop(queue_name="agent.mvp.work", routing_key="#")


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
