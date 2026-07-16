"""Director 链：编排 lecture + exercise + review + 写库。"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from selflearn.agents.lecture_outline import extract_lecture_outline
from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.core.logging import get_logger
from selflearn.core.thinking import extract_json_from_fence
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.progress.stream import progress_publish

log = get_logger("director")


def _compute_difficulty(recent_scores: list[float]) -> str:
    if not recent_scores:
        return "medium"
    avg = sum(recent_scores) / len(recent_scores)
    if avg < 0.5:
        return "easy"
    if avg < 0.8:
        return "medium"
    return "hard"


def _compute_deltas(score: float) -> dict[str, float]:
    delta_kb = 0.05 if score >= 0.8 else (-0.03 if score < 0.5 else 0.0)
    delta_as = 0.02 if score >= 0.7 else -0.02
    return {"kb": delta_kb, "as": delta_as}


async def _publish(trace_id: str, stage: Stage, status: str, payload: dict[str, Any]) -> None:
    """进度推送容错：Redis 不可用时静默退化（不让 Director 链死于观测）。"""
    try:
        await progress_publish(trace_id, ProgressEvent(stage=stage, status=status, payload=payload))
    except Exception as e:  # noqa: BLE001
        log.warning("director.progress_publish_failed", trace_id=trace_id, error=str(e))


async def run_director_chain(
    env: Envelope, agent: Any, review: Any
) -> dict[str, Any]:
    """完整 Director 链。失败抛 AppError 由外层 retry 处理。"""
    trace_id = env.trace_id
    student_id = env.payload.get("student_id", "")

    # 1-3. 数据准备
    requested_node_id = env.payload.get("node_id")
    node = await agent.mcp.call(
        "tool.get_active_node", student_id=student_id, node_id=requested_node_id,
    )
    if not node.get("ok"):
        raise AppError(ErrorCode.INTERNAL, f"get_active_node: {node.get('error')}")
    kp = await agent.mcp.call("tool.get_kp", kp_id=node["kp_id"])
    if not kp.get("ok"):
        raise AppError(ErrorCode.INTERNAL, f"get_kp: {kp.get('error')}")
    recent = await agent.mcp.call("tool.get_recent_scores", student_id=student_id, limit=3)
    difficulty = _compute_difficulty(list(recent))

    # 4. lecture
    await _publish(trace_id, Stage.DIRECTOR, "running",
                   {"action": "lecture_generate", "node_id": node["node_id"]})
    lecture_html = await agent.run("skill.lecture.generate", env)
    await _publish(trace_id, Stage.DIRECTOR, "completed",
                   {"action": "lecture_generated", "lecture_html_len": len(lecture_html)})

    # 5. lecture 业务规则
    review_lec = await review.review_lecture(lecture_html)
    if review_lec.verdict == "rejected":
        raise AppError(ErrorCode.INTERNAL, f"lecture_rejected: {review_lec.issues}")

    # 5.5 提取讲义纲要，注入到 exercise env（让 exercise 的 explanation 引用讲义内容）
    lecture_outline = extract_lecture_outline(lecture_html)

    # 6. exercise 0-2 轮
    suggestions: list[str] = []
    exercises: list[dict[str, Any]] = []
    final_review: Any = None
    for revision in range(2):
        # 6a. 调 exercise skill
        env_ex = Envelope(
            action="skill.execute",
            sender=env.sender,
            target=env.target,
            payload={
                **env.payload,
                "node_id": node["node_id"],
                "kp_title": kp["title"],
                "difficulty": difficulty,
                "revision_suggestions": suggestions,
                "lecture_outline": lecture_outline,
            },
            trace_id=trace_id,
            parent_id=env.span_id,
        )
        exercises_raw = await agent.run("skill.exercise.generate", env_ex)
        try:
            exercises = extract_json_from_fence(exercises_raw) if isinstance(exercises_raw, str) else exercises_raw
        except (json.JSONDecodeError, ValueError) as e:
            raise AppError(ErrorCode.INTERNAL, f"exercise parse failed: {e}")

        # 6b. 业务规则（仅 revision 0）
        if revision == 0:
            review_biz = await review.review_exercise_business(exercises)
            if review_biz.verdict == "rejected":
                raise AppError(ErrorCode.INTERNAL, f"exercise_rejected: {review_biz.issues}")
            # needs_fix: log warn，不重做

        # 6c. LLM 语义审查
        review_llm = await review.review_exercise_llm(exercises, kp["title"], trace_id)
        final_review = review_llm

        if review_llm.verdict == "passed":
            break
        if revision == 1:
            log.warning("director.exercise_max_revisions_reached", trace_id=trace_id)
            break
        suggestions = review_llm.suggestions

    # 7. 写库
    level = await agent.mcp.call(
        "tool.create_level", node_id=node["node_id"], lecture_html=lecture_html
    )
    if not level.get("ok"):
        raise AppError(ErrorCode.INTERNAL, f"create_level: {level.get('error')}")

    bulk = await agent.mcp.call(
        "tool.bulk_create_exercises", level_id=level["level_id"], exercises=exercises
    )
    if not bulk.get("ok"):
        raise AppError(ErrorCode.INTERNAL, f"bulk_create_exercises: {bulk.get('error')}")

    # 8. 更新 profile
    score_ratio = final_review.score if final_review else 0.6
    deltas = _compute_deltas(score_ratio)
    await agent.mcp.call("tool.update_profile", student_id=student_id, deltas=deltas)

    return {
        "level_id": level["level_id"],
        "exercise_ids": bulk.get("exercise_ids", []),
        "exercises_count": len(exercises),
        "score": score_ratio,
        "lecture_html_len": len(lecture_html),
    }


async def run_director_chain_with_retry(
    env: Envelope,
    agent: Any,
    review: Any,
    max_attempts: int = 3,
    run_chain_fn: Callable[[Envelope, Any, Any], Awaitable[dict[str, Any]]] = run_director_chain,
) -> dict[str, Any]:
    """整链 retry 包装。失败重生成（依赖 level/start 路由幂等性）。"""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await run_chain_fn(env, agent, review)
        except Exception as error:  # noqa: BLE001
            last_error = error
            log.warning(
                "director.chain_retry",
                attempt=attempt + 1,
                max_attempts=max_attempts,
                error=repr(error),
            )

    assert last_error is not None
    raise last_error
