"""Map 路由（Stage 3）：生成初始藏宝图 / 拉取节点。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.infra.bus import publish_envelope


router = APIRouter(prefix="/api/map", tags=["map"])


class MapGenerateRequest(BaseModel):
    student_id: uuid.UUID


@router.post("/generate", status_code=202)
async def generate_map(body: MapGenerateRequest) -> dict[str, str]:
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.plan.generate"),
        payload={"student_id": str(body.student_id)},
    )
    await publish_envelope(env, routing_key="plan.skill.plan.generate")
    return {"trace_id": env.trace_id}