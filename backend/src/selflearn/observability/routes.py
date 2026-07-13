"""AOP /debug/state 路由（spec § 6.5）。仅在 settings.debug=True 时挂载。"""
from __future__ import annotations

from fastapi import APIRouter

from selflearn.observability.hooks import hook_bus


router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/state")
async def state() -> dict[str, list[dict[str, object]]]:
    return {"events": hook_bus.snapshot()}
