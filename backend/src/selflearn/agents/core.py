"""LLMAgent: 1 个全能 Agent class。"""
from __future__ import annotations

from typing import Any

from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.llm.base import ChatMessage, ChatRequest
from selflearn.llm.registry import LLMRegistry


class LLMAgent:
    """通用 Agent：调 Skill → MCP 预拉 → LLM → 解析。"""

    def __init__(self, mcp_client: Any, llm_registry: Any) -> None:
        self.mcp: Any = mcp_client
        self.llm: Any = llm_registry

    async def run(self, skill_id: str, env: Envelope) -> str:
        """按 Skill 跑一次。

        Phase 3 简化版：prefetch + LLM + lint 重试；tool_use 循环在后续 task 加。
        """
        skill = await self.mcp.call("tool.fetch_skill", skill_id=skill_id)
        if not skill.get("ok"):
            raise AppError(ErrorCode.INTERNAL, f"fetch_skill failed: {skill.get('error')}")

        prefetch: dict[str, Any] = {}
        for tool in skill.get("mcp_prefetch", []):
            prefetch[tool] = await self.mcp.call(tool)

        prompt_args = {
            **prefetch,
            **self._env_args(env),
        }
        try:
            prompt_body = skill["body"].format(**prompt_args)
        except KeyError as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"skill prompt missing key: {e}. Skill={skill_id}",
            )

        max_retries = skill.get("max_retries", 0)
        schema = skill.get("output_schema")
        last_err: str | None = None

        for _ in range(max_retries + 1):
            # 调 LLM（v1: tool_use 跳过，mcp_tool_use=[] 默认）
            response = await self.llm.default().chat(
                ChatRequest(
                    messages=[
                        ChatMessage("system", prompt_body),
                        ChatMessage("user", str(env.payload)),
                    ],
                    reasoning=True,
                )
            )

            # v1: tool_use 循环留空（后续 task 加）
            # 现状 mcp_tool_use=[]，LLM 不会调 tool_use

            # lint（若 output_schema 存在）
            if schema:
                lint = await self.mcp.call(
                    "tool.lint_json", payload=response, schema_name=schema,
                )
                if lint.get("ok"):
                    return response
                last_err = lint.get("error", "lint_failed")
            else:
                return response

        raise AppError(
            ErrorCode.INTERNAL,
            f"llm_max_retries_exceeded: skill={skill_id} last_err={last_err}",
        )

    @staticmethod
    def _env_args(env: Envelope) -> dict[str, Any]:
        """把 envelope payload 暴露给 prompt 模板。"""
        return dict(env.payload or {})
