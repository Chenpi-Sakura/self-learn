"""SkillBasedScheduler（P5 简化版）。

P5 架构：worker 启动时构造 LLMAgent + ReviewStage，所有 envelope 走
`dispatch(env, agent, review)` 路由到 Director chain。Director chain 内部
再按需调 LLMAgent.run(skill_id, env) 跑具体的 lecture / exercise / review 等子 skill。

旧 Stage 3 `_AGENT_FOR_SKILL` 路由表 + `dispatch_old` 已删除。
"""
from __future__ import annotations

from typing import Any

from selflearn.agents.director import run_director_chain_with_retry
from selflearn.core.envelope import Envelope
from selflearn.core.logging import get_logger

log = get_logger("scheduler")


async def dispatch(
    env: Envelope,
    agent: Any | None = None,
    review: Any | None = None,
) -> Envelope | None:
    """P5 唯一入口：调 Director chain。

    P5 架构下 worker 必传 agent + review；如果有人裸调（无依赖）则抛 ValueError，
    防止静默回退到旧 Agent class（已删）。
    """
    if agent is None or review is None:
        raise ValueError(
            "P5 dispatch requires agent and review: "
            "worker must construct LLMAgent + ReviewStage and pass them in. "
            "Legacy dispatch_old has been removed."
        )
    await run_director_chain_with_retry(env, agent, review)
    return None
