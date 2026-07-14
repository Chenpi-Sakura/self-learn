"""Level 路由（Stage 3）：启动关卡 / 提交答案 / SSE 真流。"""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

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
    student_id: uuid.UUID


class LevelSubmitRequest(BaseModel):
    answers: dict[str, object]  # exercise_id(str) -> answer


@router.post("/start", status_code=202)
async def start_level(body: LevelStartRequest) -> dict[str, str]:
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.director.start"),
        payload={"student_id": str(body.student_id)},
    )
    await publish_envelope(env, routing_key="director.skill.director.start")
    return {"trace_id": env.trace_id}


@router.get("/{level_id}/stream")
async def stream_level(level_id: uuid.UUID, trace_id: str) -> EventSourceResponse:
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
            if ev.stage.value in ("completed", "failed"):
                final = json.dumps(
                    {"status": ev.status, "payload": ev.payload},
                    ensure_ascii=False,
                )
                yield {
                    "event": "completed" if ev.stage.value == "completed" else "error",
                    "data": final,
                }
                return

    return EventSourceResponse(event_gen())


@router.post("/{level_id}/submit")
async def submit_level(
    level_id: uuid.UUID, body: LevelSubmitRequest
) -> dict[str, object]:
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
async def get_level(level_id: uuid.UUID) -> LevelDetailResponse:
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