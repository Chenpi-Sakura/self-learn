"""提炼主题 POST 触发 + SSE 流（Task 2/3）。"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks
from sse_starlette.sse import EventSourceResponse

from selflearn.agents.extract_topics import run_extract_topics
from selflearn.infra.redis_client import get_redis
from selflearn.progress.stages import Stage
from selflearn.progress.stream import progress_consume
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


# ---------------------------------------------------------------------------
# Task 3：SSE 真流（仿 profile.py:_stream_events）
# ---------------------------------------------------------------------------


async def _stream_extract_topics_events(
    task_id: str,
) -> AsyncIterator[dict[str, str]]:
    """SSE 事件生成器：从 Redis Stream 读进度，按终态判定关闭 SSE。

    注意：与 profile.py / level.py 不同——extract_topics 流水线对每个阶段
    都推 status="completed"（parse/llm/validate/write/done 各一次），因此
    **不能**把所有 completed 当作终态。我们只把以下两条视为终态：

    - status="failed" — 任意阶段的失败（最严重的，立即关闭）
    - status="completed" **且** stage 是 EXTRACT_TOPICS_DONE（流水线全部结束）

    这样前端 ProgressOverlay 能逐阶段点亮 5 个圆点（running→completed→下一个
    running…），最后看到 EXTRACT_TOPICS_DONE.completed 才关闭连接。
    """
    async for ev in progress_consume(task_id):
        data = json.dumps(
            {
                "stage": ev.stage.value,
                "status": ev.status,
                "payload": ev.payload,
            },
            ensure_ascii=False,
        )
        yield {"event": "progress", "data": data}
        # 终态判定：
        # - failed：任意阶段失败都立刻关闭
        # - completed：仅 Stage.EXTRACT_TOPICS_DONE 才算全部跑完
        is_terminal_failed = ev.status == "failed"
        is_terminal_done = (
            ev.status == "completed"
            and ev.stage == Stage.EXTRACT_TOPICS_DONE
        )
        if is_terminal_failed or is_terminal_done:
            final_payload = json.dumps(
                {"status": ev.status, "payload": ev.payload},
                ensure_ascii=False,
            )
            yield {
                "event": "completed" if ev.status == "completed" else "error",
                "data": final_payload,
            }
            return


@router.get("/extract_topics/stream")
async def stream_extract_topics(task_id: str) -> EventSourceResponse:
    """Task 3 SSE 真流：前端 ProgressOverlay 用 EventSource 连这里收 5 阶段进度。"""
    return EventSourceResponse(_stream_extract_topics_events(task_id))
