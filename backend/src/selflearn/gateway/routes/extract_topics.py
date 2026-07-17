"""提炼主题 POST 触发（SSE 流在 Task 3 加）。"""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks

from selflearn.agents.extract_topics import run_extract_topics
from selflearn.infra.redis_client import get_redis
from selflearn.schemas.extract_topics import (
    ExtractTopicsRequest,
    ExtractTopicsResponse,
)


router = APIRouter(prefix="/api/resources", tags=["extract_topics"])


@router.post("/extract_topics", response_model=ExtractTopicsResponse, status_code=202)
async def trigger(
    body: ExtractTopicsRequest, background_tasks: BackgroundTasks,
) -> ExtractTopicsResponse:
    task_id = str(uuid4())
    r = get_redis()
    # Task 3 SSE 路由会复用 stream:{task_id}；这里先 set 个 TTL 兜底标志，
    # 让 progress_publish 的 expire 不用依赖第一次写入时机。
    await r.set(f"stream:{task_id}", "running", ex=3600)
    # 走 BackgroundTasks 同进程执行（T1 ~ T3 阶段不做 worker 进程扩展）
    background_tasks.add_task(run_extract_topics, task_id, body.selected_resource_ids)
    return ExtractTopicsResponse(task_id=task_id)
