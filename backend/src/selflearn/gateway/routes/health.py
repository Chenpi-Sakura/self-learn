"""/healthz + /readyz 端点（v4 § 4.4 路由表）。"""
from __future__ import annotations

from fastapi import APIRouter

from selflearn.infra import db, rabbit, redis_client

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, object]:
    checks = {
        "postgres": await db.health(),
        "redis": await redis_client.health(),
        "rabbitmq": await rabbit.health(),
    }
    all_ok = all(checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}