"""SkillBasedScheduler（v4 § 2.1.4）。

Stage 3 V1.3 路由改造（Rule #13 第四子规则）：
- 主路径：`_AGENT_FOR_SKILL[target.id]`（仅 target.id，不读 skills 字段、不读装饰器）。
- 缺失回退：`skill_registry.match(target.id)`（保留 Stage 2 `skill.profile.init`）。
- 都没有：抛 NotImplementedError，明确指出尚未实现的 Agent 类。
- Stage 3 Agent 全部实装（Task 7-11）→ `_AGENT_FOR_SKILL` 5 个键映射到真实 Agent 类。
"""
from __future__ import annotations

from typing import Any

from selflearn.agents.base import AbstractAgent
from selflearn.agents.builtin.director_agent import DirectorAgent
from selflearn.agents.builtin.exercise_agent import ExerciseAgent
from selflearn.agents.builtin.plan_agent import PlanAgent
from selflearn.agents.builtin.profile_agent import ProfileAgent
from selflearn.agents.builtin.review_agent import ReviewAgent
from selflearn.agents.director import run_director_chain_with_retry
from selflearn.core.envelope import Envelope
from selflearn.core.logging import get_logger
from selflearn.skills.base import skill_registry

log = get_logger("scheduler")


# Stage 3 routing map (Rule #13 第四子规则):
# - 仅 envelope.target.id 命中此表 → 走 Agent class（无装饰器，无 skills 字段依赖）。
# - 5 个值已实装（Task 7-11），全部映射到对应的 Agent 类。
_AGENT_FOR_SKILL: dict[str, type[AbstractAgent] | None] = {
    "skill.profile.build": ProfileAgent,    # Task 7
    "skill.plan.generate": PlanAgent,        # Task 8
    "skill.exercise.generate": ExerciseAgent, # Task 9
    "skill.review.exercise": ReviewAgent,    # Task 10
    "skill.director.start": DirectorAgent,   # Task 11
}


def _resolve_agent_class(skill_id: str):  # type: ignore[no-untyped-def]
    """按 target.id 解析 Agent 类：主路径 → 装饰器 fallback → 报错。

    返回类型在运行时可能是 `type[AbstractAgent]`（主路径）也可能是
    `SkillHandler`（Stage 2 装饰器 fallback），故不静态标注。
    """
    cls = _AGENT_FOR_SKILL.get(skill_id)
    if cls is not None:
        return cls

    # Stage 2 fallback：skill_registry（@skill 装饰器路径，PingAgent 走这里）
    handler = skill_registry.match(skill_id)
    if handler is not None:
        return handler

    raise NotImplementedError(
        f"Agent not yet implemented for {skill_id!r}: "
        f"add the class to `_AGENT_FOR_SKILL` in agents/scheduler.py."
    )


async def dispatch_old(env: Envelope) -> Envelope | None:
    """Stage 3 兼容入口：按 target.id 路由旧 Agent class。"""
    skill_id = env.target.id
    handler_or_cls = _resolve_agent_class(skill_id)

    # Stage 3 主路径：Agent class 实例化 + run()
    if isinstance(handler_or_cls, type) and issubclass(handler_or_cls, AbstractAgent):
        agent = handler_or_cls()
        result = await agent.run(env)
    else:
        # Stage 2 fallback 路径：装饰器 handler 直接 await
        result = await handler_or_cls(env)

    if isinstance(result, Envelope):
        return result
    return None


async def dispatch(
    env: Envelope,
    agent: Any | None = None,
    review: Any | None = None,
) -> Envelope | None:
    """统一入口：P4 调 Director；无依赖时保留 Stage 3 兼容路由。"""
    if agent is None or review is None:
        return await dispatch_old(env)
    if env.target.id != "skill.director.start":
        log.warning("scheduler.non_director_skill", skill_id=env.target.id)
    await run_director_chain_with_retry(env, agent, review)
    return None


def get_agent_class_for_skill(skill_id: str) -> type[AbstractAgent] | None:
    """公开只读入口（Stage 3 其它模块可查询，但严禁外部修改 dict）。"""
    return _AGENT_FOR_SKILL.get(skill_id)
