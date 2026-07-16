"""Level 路由（Stage 3）：启动关卡 / 提交答案 / SSE 真流。

幂等性：POST /start 对给定节点复用其 in-flight（status='generated' 或
'in_progress'）关卡，避免重复调 LLM 出题。节点定位优先按前端传入的
node_id 精确匹配（点不同节点拿不同关卡）；未传 node_id 时 fallback 到
该 student 第一个 status='active' 节点（向后兼容）。
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.exercise import Exercise
from selflearn.domain.level import Level
from selflearn.domain.level_completion import LevelCompletion
from selflearn.domain.map_node import MapNode
from selflearn.infra.bus import publish_envelope
from selflearn.infra.db import get_session_factory
from selflearn.progress.stream import progress_consume
from selflearn.schemas.level import ExerciseResponse, LevelDetailResponse


router = APIRouter(prefix="/api/level", tags=["level"])


class LevelStartRequest(BaseModel):
    student_id: str
    node_id: str | None = None  # 新增：精确按节点启动/复用关卡（前端点不同节点时传）


class LevelSubmitRequest(BaseModel):
    answers: dict[str, object]  # exercise_id(str) -> answer


@router.post("/start", status_code=202)
async def start_level(body: LevelStartRequest) -> dict[str, object]:
    student_id = str(body.student_id)
    factory = get_session_factory()
    async with factory() as session:
        # 节点定位：
        # - 前端传了 node_id → 精确按 (student_id, node_id) 查（点不同节点拿不同关卡）
        # - 没传 → 向后兼容，fallback 到该 student 第一个 status='active' 节点
        if body.node_id is not None:
            node = (
                await session.execute(
                    select(MapNode)
                    .where(
                        MapNode.student_id == student_id,
                        MapNode.node_id == body.node_id,
                    )
                    .limit(1)
                )
            ).scalars().first()
            if node is None:
                raise HTTPException(status_code=409, detail="node_not_found")
            if node.status == "locked":
                # 前置知识点未完成，不允许启动
                raise HTTPException(status_code=409, detail="node_locked")
        else:
            node = (
                await session.execute(
                    select(MapNode)
                    .where(MapNode.student_id == student_id, MapNode.status == "active")
                    .limit(1)
                )
            ).scalars().first()
            if node is None:
                raise HTTPException(status_code=409, detail="no_active_node")

        # 幂等性：查该节点的 in-flight 关卡（status='generated' 或 'in_progress'）
        existing = (
            await session.execute(
                select(Level)
                .where(
                    Level.node_id == node.node_id,
                    Level.status.in_(("generated", "in_progress")),
                )
                .order_by(Level.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
        if existing is not None:
            # 复用：直接返回已有 level_id，不调 LLM
            return {
                "level_id": str(existing.level_id),
                "node_id": str(node.node_id),
                "reused": True,
            }

    # 无 in-flight 关卡 → 发 envelope 给 DirectorAgent 出题
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.director.start"),
        payload={"student_id": student_id, "node_id": str(node.node_id)},
    )
    await publish_envelope(env, routing_key="director.skill.director.start")
    return {"trace_id": env.trace_id, "node_id": str(node.node_id), "reused": False}


@router.get("/{level_id}/stream")
async def stream_level(level_id: UUID, trace_id: str) -> EventSourceResponse:
    async def event_gen() -> AsyncIterator[dict[str, str]]:
        async for ev in progress_consume(trace_id):
            data = json.dumps(
                {
                    "stage": ev.stage.value,
                    "status": ev.status,
                    "payload": ev.payload,
                },
                ensure_ascii=False,
            )
            yield {"event": "progress", "data": data}
            # Stage 4-fix: 按 status 终态判定关闭 SSE（与 profile 路由一致）
            if ev.status in ("completed", "failed"):
                final = json.dumps(
                    {"status": ev.status, "payload": ev.payload},
                    ensure_ascii=False,
                )
                yield {
                    "event": "completed" if ev.status == "completed" else "error",
                    "data": final,
                }
                return

    return EventSourceResponse(event_gen())


@router.post("/{level_id}/submit")
async def submit_level(level_id: UUID, body: LevelSubmitRequest) -> dict[str, object]:
    factory = get_session_factory()
    async with factory() as session:
        # Level 没有声明 relationship；用显式 JOIN 拿 student_id
        # 避免 lazy-load MissingGreenlet。
        stmt = (
            select(Level, MapNode.student_id)
            .join(MapNode, Level.node_id == MapNode.node_id)
            .where(Level.level_id == level_id)
        )
        row = (await session.execute(stmt)).first()
        if row is None:
            return {"status": "level_not_found"}
        level, student_id = row

        exs = (
            await session.execute(
                select(Exercise).where(Exercise.level_id == level_id)
            )
        ).scalars().all()

        score: float = 0.0
        for ex in exs:
            ans = body.answers.get(str(ex.exercise_id))
            if ans is not None and ans == ex.correct_answer:
                # ex.score 是 Numeric(4,2)；显式 cast 让 mypy 满意
                score += float(ex.score)

        completion = LevelCompletion(
            level_id=level_id,
            student_id=student_id,
            score=score,
            duration_seconds=0,
            answers={str(k): v for k, v in body.answers.items()},
            metrics={"items": len(exs)},
        )
        session.add(completion)
        level.status = "completed"
        await session.commit()
    return {"status": "submitted", "score": score}


@router.get("/{level_id}", response_model=LevelDetailResponse)
async def get_level(level_id: UUID) -> LevelDetailResponse:
    """Stage 4 spec § 4.3: 加载关卡详情（exercises + 题干）。"""
    factory = get_session_factory()
    async with factory() as session:
        level = await session.get(Level, level_id)
        if level is None:
            raise HTTPException(status_code=404, detail="level_not_found")
        exs = (
            await session.execute(
                select(Exercise).where(Exercise.level_id == level_id)
            )
        ).scalars().all()

    return LevelDetailResponse(
        level_id=level.level_id,
        node_id=level.node_id,
        status=level.status,
        lecture_html=level.lecture_html,
        exercises=[
            ExerciseResponse(
                exercise_id=ex.exercise_id,
                prompt=ex.prompt,
                options=list(ex.options) if ex.options else None,
                type=ex.exercise_type,  # ORM 字段叫 exercise_type
            )
            for ex in exs
        ],
    )