"""SkillBasedScheduler（P5 简化版 + Task 18 routing fix）。

P5 架构：worker 启动时构造 LLMAgent + ReviewStage。

`dispatch(env, agent, review)` 按 `env.target.id` 分支：

- `skill.director.start`       → `run_director_chain_with_retry`
                                 (P5 主入口：lecture + exercise×2 + review + 写库)
- `skill.profile.build`        → `agent.run(skill_id, env)`
                                 (单步：LLM 出 profile HTML；POST /api/profile/build)
- `skill.plan.generate`        → `agent.run(skill_id, env)`
                                 (单步：LLM 出 node list；POST /api/map/generate)
- 其它                         → log warning + return None（Stage 2 fallback / unknown）

profile.build / plan.generate 都是单步 Skill，不需要 review stage；
agent.run 返回的产物 caller 不关心（前端轮询 job 状态）。
"""
from __future__ import annotations

from typing import Any

from selflearn.agents.director import run_director_chain_with_retry
from selflearn.core.envelope import Envelope
from selflearn.core.logging import get_logger

log = get_logger("scheduler")

_DIRECTOR_SKILL = "skill.director.start"
_SINGLE_STEP_SKILLS = frozenset({"skill.profile.build", "skill.plan.generate"})


async def dispatch(
    env: Envelope,
    agent: Any | None = None,
    review: Any | None = None,
) -> Envelope | None:
    """P5 entry: 按 env.target.id 分支路由 envelope。

    P5 架构下 worker 必传 agent + review；如果有人裸调（无依赖）则抛 ValueError，
    防止静默回退到旧 Agent class（已删）。
    """
    if agent is None or review is None:
        raise ValueError(
            "P5 dispatch requires agent and review: "
            "worker must construct LLMAgent + ReviewStage and pass them in. "
            "Legacy dispatch_old has been removed."
        )

    target_id: str = env.target.id
    if target_id == _DIRECTOR_SKILL:
        await run_director_chain_with_retry(env, agent, review)
        return None

    if target_id in _SINGLE_STEP_SKILLS:
        # 单步 Skill：profile/build 出 HTML、plan/generate 出 node list；
        # LLM 产物以 string 形式返回，dispatch 不解析，frontend 轮询 job 状态。
        await agent.run(target_id, env)
        return None

    # Stage 2 fallback / 未知 skill：留日志便于排错，不抛（避免阻塞 worker）
    log.warning("scheduler.unknown_skill", skill_id=target_id)
    return None