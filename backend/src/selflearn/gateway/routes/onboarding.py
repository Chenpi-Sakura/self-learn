"""Onboarding 路由：GET 题库 / POST 提交（同步调 tool.onboard_profile）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from selflearn.schemas.onboarding import (
    OnboardingQuestionsResponse,
    OnboardingSubmitRequest,
    OnboardingSubmitResponse,
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

QUESTION_FILE = (
    Path(__file__).parent.parent.parent / "data/onboarding_questions.json"
)


def _load_questions() -> list[dict[str, Any]]:
    return json.loads(QUESTION_FILE.read_text(encoding="utf-8"))


def _build_agent() -> Any:
    """构造 LLMAgent 实例（路由层懒加载，避免 import 期副作用）。"""
    from selflearn.agents.core import LLMAgent
    from selflearn.llm.registry import llm_registry

    # _register_default_adapters() 已在 registry.py 模块导入时自动调用
    # MCP 客户端生命周期由外部管理，此处用 None 占位（单测会 mock 本函数）
    return LLMAgent(None, llm_registry)


async def _run_onboard(
    student_id: str, answers: list[dict[str, Any]], agent: Any
) -> dict[str, Any]:
    """调 tool.onboard_profile（tool 注册由 MCP server 维护）。"""
    from selflearn.mcp_server.tools.onboard_profile import onboard_profile
    return await onboard_profile(student_id, answers, agent)


@router.get("/questions", response_model=OnboardingQuestionsResponse)
async def get_questions() -> OnboardingQuestionsResponse:
    """读题库 JSON 返回（HTTP 缓存由前端控制）。"""
    return OnboardingQuestionsResponse(questions=_load_questions())


@router.post("/submit", response_model=OnboardingSubmitResponse)
async def submit(body: OnboardingSubmitRequest) -> OnboardingSubmitResponse | JSONResponse:
    """同步调 LLM 评分 → 返回 6 维分 + reasoning + snapshot_id。"""
    agent = _build_agent()
    answers_payload = [a.model_dump() for a in body.answers]
    result = await _run_onboard(body.student_id, answers_payload, agent)

    if result.get("ok"):
        return OnboardingSubmitResponse(
            dimensions=result["dimensions"],
            reasoning=result.get("reasoning", ""),
            snapshot_id=int(result["snapshot_id"]),
        )

    err = result.get("error", "unknown")
    if err == "already_onboarded":
        return JSONResponse(status_code=409, content={"error": "already_onboarded"})
    if err == "answers_mismatch":
        return JSONResponse(status_code=400, content={"error": "answers_mismatch"})
    # onboard_lint_failed / profile_write_failed 等
    return JSONResponse(status_code=500, content={"error": "onboard_failed"})
