"""ExerciseAgent: LLM 出题 + tool.lint_json + 1 次自动重试（V1.3 Rule #15 范例）。"""
from __future__ import annotations

from typing import Any

from selflearn.agents.base import AbstractAgent
from selflearn.agents.builtin._node_protocol import Node
from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.core.thinking import extract_json_from_fence
from selflearn.llm.base import ChatMessage, ChatRequest
from selflearn.llm.registry import llm_registry
from selflearn.skills.library import get as get_skill
from selflearn.tools.protocol import ToolRegistry


class ExerciseAgent(AbstractAgent):
    """skill.exercise.generate: 前置打包 → 调 LLM → 冷酷后置校验（最多 1 次重试）。"""

    agent_id = "exercise-01"
    agent_type = "exercise"
    queue = "agent.exercise.work"

    async def run(self, env: Envelope) -> Envelope:
        """Dispatcher 走 Envelope 入口（Stage 3 MVP 仅通过 Director 同步调用 run_sync）。"""
        return env  # pragma: no cover - 同步调用模式

    async def run_sync(
        self, env: Envelope, node: Node, difficulty: str = "medium"
    ) -> list[dict[str, Any]]:
        """Director 同步调；返回 list[dict]，由 Director 写库。

        V1.1 Rule #15: lint 拒收时抛 AppError，让 Director.try/except 兜底推 FAILED。
        """
        skill = get_skill("skill.exercise.generate")

        # 前置打包 1) 拉模板
        tmpl = await ToolRegistry.call(
            "tool.fetch_template", name="exercise_generation_v1"
        )
        if not tmpl.ok:
            raise AppError(ErrorCode.INTERNAL, f"fetch_template 失败: {tmpl.error}")

        # 前置打包 2) 一次性把所有输入塞进 ChatRequest
        # ChatRequest 当前 dataclass 无 `system` 字段；system 走 messages 中
        # role="system" 的 ChatMessage（与 ping_agent 一致）。
        # spec § 5.2: 把 difficulty 注入 prompt，让 LLM 按难度调整题目复杂度
        prompt = (
            skill.body
            + "\n\n" + tmpl.data["content"]
            + f"\n\n当前难度：{difficulty}（easy 偏概念辨析 / medium 偏应用 / hard 偏综合）"
        )
        req = ChatRequest(
            messages=[
                ChatMessage(role="system", content=prompt),
                ChatMessage(
                    role="user",
                    content=f"node_id={node.node_id}; kp_title={node.kp.title}",
                ),
            ],
            reasoning=True,
        )

        # 冷酷后置校验 + 1 次重试
        last_err: str | None = None
        for _attempt in range(2):
            raw = await llm_registry.default().chat(req)
            parsed = extract_json_from_fence(raw)
            lint = await ToolRegistry.call(
                "tool.lint_json", payload=parsed, schema="exercise"
            )
            if lint.ok:
                if not isinstance(parsed, list):
                    parsed = [parsed]
                return parsed  # type: ignore[return-value]
            last_err = lint.error

        raise AppError(ErrorCode.EXERCISE_INVALID, f"lint 重试失败: {last_err}")
