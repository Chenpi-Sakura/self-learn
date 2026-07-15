"""LLMAgent: 1 个全能 Agent class。"""
from __future__ import annotations

from typing import Any

from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.llm.base import ChatMessage, ChatRequest
from selflearn.llm.registry import LLMRegistry


class LLMAgent:
    """通用 Agent：调 Skill → MCP 预拉 → LLM → 解析。"""

    def __init__(
        self,
        mcp_client: Any | None = None,
        llm_registry: Any | None = None,
        *,
        mcp: Any | None = None,
        llm: Any | None = None,
    ) -> None:
        self.mcp: Any = mcp_client if mcp is None else mcp
        self.llm: Any = llm_registry if llm is None else llm

    async def run(self, skill_id: str, env: Envelope) -> Any:
        """按 Skill 跑一次。

        Phase 3 简化版：prefetch + LLM + parse；lint 在 Task 13 加；tool_use 循环在后续 task 加。
        """
        skill = await self.mcp.call("tool.fetch_skill", skill_id=skill_id)
        if not skill.get("ok"):
            raise AppError(ErrorCode.INTERNAL, f"fetch_skill failed: {skill.get('error')}")

        prefetch: dict[str, Any] = {}
        for tool in skill.get("mcp_prefetch", []):
            prefetch[tool] = await self.mcp.call(tool)

        prompt_args = {
            **prefetch,
            **{tool.replace(".", "_"): value for tool, value in prefetch.items()},
            **self._env_args(env),
        }
        try:
            prompt_body = skill["body"].format(**prompt_args)
        except KeyError as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"skill prompt missing key: {e}. Skill={skill_id}",
            )

        response = await self.llm.default().chat(
            ChatRequest(
                messages=[
                    ChatMessage("system", prompt_body),
                    ChatMessage("user", str(env.payload)),
                ],
                reasoning=True,
            )
        )
        return response.content

    @staticmethod
    def _env_args(env: Envelope) -> dict[str, Any]:
        """把 envelope payload 暴露给 prompt 模板。"""
        return dict(env.payload or {})
