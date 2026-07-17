"""tool.onboard_profile — 6 维画像冷启动生成。

LLM 单 chat 评分（基于 8 道情境题回答）→ clamp + 缺维度兜底 → create_profile + snapshot。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError
from selflearn.core.logging import get_logger
from selflearn.core.thinking import extract_json_from_fence
from selflearn.domain.profile_snapshot import ProfileSnapshot
from selflearn.infra.db import get_session_factory

from selflearn.mcp_server.tools.create_profile import create_profile
from selflearn.mcp_server.tools.get_profile import get_profile

log = get_logger("onboard_profile")

DIM_SHORT_KEYS = ("kb", "vp", "as", "ge", "ept", "fd")
DEFAULT_DIM_VALUE = 0.5


def _is_initialized(dims: dict[str, Any] | None) -> bool:
    """Profile 已有非默认 dimensions 视为已 onboarding。"""
    if not dims:
        return False
    return any(
        abs(float(dims.get(k, DEFAULT_DIM_VALUE)) - DEFAULT_DIM_VALUE) > 1e-6
        for k in DIM_SHORT_KEYS
    )


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _normalize_dims(raw: dict[str, Any]) -> dict[str, float]:
    """6 维齐全 + clamp [0,1] + 缺失补 0.5。"""
    out: dict[str, float] = {}
    for k in DIM_SHORT_KEYS:
        v = raw.get(k)
        if isinstance(v, (int, float)):
            out[k] = round(_clamp(float(v)), 2)
        else:
            out[k] = DEFAULT_DIM_VALUE
    return out


async def _write_snapshot(student_id: str, profile: dict[str, float], trigger: str) -> int:
    """写 ProfileSnapshot（trigger="onboarding"）。返回 snapshot.id。"""
    factory = get_session_factory()
    async with factory() as session:
        snap = ProfileSnapshot(
            student_id=student_id,
            profile=profile,
            trigger=trigger,
            created_at=datetime.now(timezone.utc),
        )
        session.add(snap)
        await session.commit()
        await session.refresh(snap)
        return int(snap.id)


async def onboard_profile(
    student_id: str,
    answers: list[dict[str, Any]],
    agent: Any,
) -> dict[str, Any]:
    """LLM 单 chat 评分 → clamp → create_profile + snapshot。

    Returns:
      成功：{"ok": True, "dimensions", "reasoning", "snapshot_id"}
      已 onboarding：{"ok": False, "error": "already_onboarded"}
      lint 失败：{"ok": False, "error": "onboard_lint_failed"}
    """
    # 1. 防御：已 onboarding 直接拒绝
    existing = await get_profile(student_id)
    if existing.get("ok") and _is_initialized(existing.get("dimensions")):
        return {"ok": False, "error": "already_onboarded"}

    # 2. 加载题目 JSON（供 LLM 评分参考）
    questions_path = (
        Path(__file__).resolve().parents[4]
        / "src" / "selflearn" / "data" / "onboarding_questions.json"
    )
    questions = json.loads(questions_path.read_text(encoding="utf-8"))

    # 3. 构造 envelope + 调 LLM skill（走 agent.run 走 lint 链）
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="tool", id="onboard_profile"),
        target=ActorRef(type="skill", id="skill.profile.onboard"),
        payload={
            "student_id": student_id,
            "questions": questions,
            "answers": answers,
        },
    )
    try:
        llm_output = await agent.run("skill.profile.onboard", env)
    except AppError as e:
        log.warning("onboard_profile.agent_run_failed", error=str(e))
        return {"ok": False, "error": "onboard_lint_failed"}

    # 4. 解析 LLM JSON（容错：fence/裸 JSON 都行）
    try:
        parsed = extract_json_from_fence(llm_output) if isinstance(llm_output, str) else llm_output
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if not isinstance(parsed, dict):
            raise ValueError("LLM output is not a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        log.warning("onboard_profile.parse_failed", error=str(e), raw=llm_output[:200])
        return {"ok": False, "error": "onboard_lint_failed"}

    # 5. 归一化（clamp + 缺维度补 0.5）
    dimensions = _normalize_dims(parsed)
    reasoning = str(parsed.get("reasoning", ""))

    # 6. 写 profile + snapshot
    create_result = await create_profile(student_id, dimensions, tags=["onboarded"])
    if not create_result.get("ok"):
        return {"ok": False, "error": "profile_write_failed"}

    snapshot_id = await _write_snapshot(student_id, dimensions, trigger="onboarding")

    return {
        "ok": True,
        "dimensions": dimensions,
        "reasoning": reasoning,
        "snapshot_id": snapshot_id,
    }