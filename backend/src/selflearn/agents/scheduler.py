"""SkillBasedScheduler（v4 § 2.1.4）。

Stage 3 V1.3 路由改造（Rule #13 第四子规则）：
- 主路径：`_AGENT_FOR_SKILL[target.id]`（仅 target.id，不读 skills 字段、不读装饰器）。
- 缺失回退：`skill_registry.match(target.id)`（保留 Stage 2 `skill.profile.init`）。
- 都没有：抛 NotImplementedError，明确指出尚未实现的 Agent 类。
- Stage 3 Agent 尚未落地 → `_AGENT_FOR_SKILL` 5 个键先以 `None` 占位（Task 7-11 实装）
  ，避免循环依赖与 stub 噪音。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import Envelope
from selflearn.skills.base import skill_registry

if TYPE_CHECKING:
    from selflearn.agents.builtin.profile_agent import ProfileAgent  # noqa: F401, TCH004  # Task 7
    from selflearn.agents.builtin.plan_agent import PlanAgent  # noqa: F401, TCH004  # Task 8
    from selflearn.agents.builtin.exercise_agent import ExerciseAgent  # noqa: F401, TCH004  # Task 9
    from selflearn.agents.builtin.review_agent import ReviewAgent  # type: ignore[import-untyped]  # noqa: F401, TCH004  # Task 10
    from selflearn.agents.builtin.director_agent import DirectorAgent  # type: ignore[import-untyped]  # noqa: F401, TCH004  # Task 11


# Stage 3 routing map (Rule #13 第四子规则):
# - 仅 envelope.target.id 命中此表 → 走 Agent class（无装饰器，无 skills 字段依赖）。
# - 5 个值暂为 None，避免 Task 4 提前依赖 Task 7-11 Agent 模块造成循环。
#   每个 None 必须在对应 Agent 实装时替换为 `MyAgent` 类（Task 7 / 8 / 9 / 10 / 11）。
_AGENT_FOR_SKILL: dict[str, type[AbstractAgent] | None] = {
    "skill.profile.build": None,      # TODO Task 7: ProfileAgent
    "skill.plan.generate": None,      # TODO Task 8: PlanAgent
    "skill.exercise.generate": None,  # TODO Task 9: ExerciseAgent
    "skill.review.exercise": None,    # TODO Task 10: ReviewAgent
    "skill.director.start": None,     # TODO Task 11: DirectorAgent
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
        f"add the class to `_AGENT_FOR_SKILL` in agents/scheduler.py "
        f"(TODO references Task 7/8/9/10/11)."
    )


async def dispatch(env: Envelope) -> Envelope | None:
    """仅认 envelope.target.id 的路由入口（Rule #13 第四子规则主路径）。"""
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


def get_agent_class_for_skill(skill_id: str) -> type[AbstractAgent] | None:
    """公开只读入口（Stage 3 其它模块可查询，但严禁外部修改 dict）。"""
    return _AGENT_FOR_SKILL.get(skill_id)