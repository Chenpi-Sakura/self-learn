"""提炼主题 5 阶段流水线（Task 2）。

依赖：
- selflearn.domain.resource.Resource
- selflearn.domain.map_node.MapNode
- selflearn.domain.knowledge_point.KnowledgePoint
- selflearn.progress.{progress_publish, Stage, ProgressEvent}
- selflearn.agents.core.LLMAgent
- selflearn.llm.registry.LLMRegistry
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from selflearn.agents.core import LLMAgent
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.domain.map_node import MapNode
from selflearn.domain.resource import Resource
from selflearn.infra.db import get_session_factory
from selflearn.llm.registry import llm_registry
from selflearn.mcp_client import mcp_client_lifespan
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.progress.stream import progress_publish


TIMEOUT_LLM_SEC = 150
TIMEOUT_TOTAL_SEC = 180


@dataclass
class TopicDraft:
    title: str
    description: str
    prerequisites: list[str]
    excerpt_text: str
    source_resource_id: str


# 模块内 schema（不依赖外部 json 文件）
TOPIC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 30},
                    "description": {"type": "string", "minLength": 1, "maxLength": 200},
                    "prerequisites": {"type": "array", "items": {"type": "string"}},
                    "excerpt_text": {"type": "string", "minLength": 500, "maxLength": 1500},
                    "source_resource_id": {"type": "string", "format": "uuid"},
                },
                "required": [
                    "title", "description", "prerequisites",
                    "excerpt_text", "source_resource_id",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["topics"],
    "additionalProperties": False,
}


class _SchemaValidationError(Exception):
    pass


def _validate_topics(data: dict[str, Any], input_ids: set[str]) -> list[TopicDraft]:
    """最简 JSON schema 校验（含 source_resource_id 必须在 input ids 中）。"""
    if not isinstance(data, dict) or "topics" not in data:
        raise _SchemaValidationError("missing topics")
    raw_topics = data["topics"]
    if not isinstance(raw_topics, list) or not (3 <= len(raw_topics) <= 8):
        raise _SchemaValidationError("topics length 3-8 required")
    titles_seen: set[str] = set()
    drafts: list[TopicDraft] = []
    for t in raw_topics:
        if not isinstance(t, dict):
            raise _SchemaValidationError("topic must be object")
        try:
            title = str(t["title"]).strip()
            desc = str(t["description"]).strip()
            prereqs = list(t["prerequisites"])
            excerpt = str(t["excerpt_text"])
            src_id = str(t["source_resource_id"])
        except (KeyError, TypeError) as e:
            raise _SchemaValidationError(f"field missing: {e}") from e
        if not (1 <= len(title) <= 30):
            raise _SchemaValidationError("title length 1-30")
        if not (1 <= len(desc) <= 200):
            raise _SchemaValidationError("description length 1-200")
        if not (500 <= len(excerpt) <= 1500):
            raise _SchemaValidationError("excerpt_text length 500-1500")
        if src_id not in input_ids:
            raise _SchemaValidationError(f"source_resource_id {src_id} not in input")
        if title in titles_seen:
            raise _SchemaValidationError(f"duplicate title: {title}")
        titles_seen.add(title)
        drafts.append(
            TopicDraft(
                title=title,
                description=desc,
                # 自指 prereq 丢弃；只在前面已出现的 title 里保留
                prerequisites=[p for p in prereqs if p in titles_seen and p != title],
                excerpt_text=excerpt,
                source_resource_id=src_id,
            )
        )
    return drafts


async def run_extract_topics(task_id: str, selected_ids: list[UUID]) -> None:
    """5 阶段流水线入口。失败会推 status=failed。"""
    try:
        await asyncio.wait_for(
            _run_pipeline(task_id, selected_ids), timeout=TIMEOUT_TOTAL_SEC
        )
    except asyncio.TimeoutError:
        await progress_publish(
            task_id,
            ProgressEvent(
                stage=Stage.EXTRACT_TOPICS_LLM,
                status="failed",
                payload={"error": "total timeout"},
            ),
        )


async def _run_pipeline(task_id: str, selected_ids: list[UUID]) -> None:
    factory = get_session_factory()

    # 1. parse
    await progress_publish(
        task_id,
        ProgressEvent(stage=Stage.EXTRACT_TOPICS_PARSE, status="running"),
    )
    try:
        async with factory() as session:
            rows = (
                await session.execute(
                    select(Resource).where(
                        Resource.id.in_(selected_ids),
                        Resource.deleted_at.is_(None),
                    )
                )
            ).scalars().all()
            if not rows:
                await progress_publish(
                    task_id,
                    ProgressEvent(
                        stage=Stage.EXTRACT_TOPICS_PARSE,
                        status="failed",
                        payload={"error": "no resources found"},
                    ),
                )
                return
            resources_payload = [
                {"id": str(r.id), "name": r.name, "content_md": r.content_md}
                for r in rows
            ]
            student_id = rows[0].student_id
            input_ids = {str(r.id) for r in rows}
    except Exception as e:  # noqa: BLE001
        await progress_publish(
            task_id,
            ProgressEvent(
                stage=Stage.EXTRACT_TOPICS_PARSE,
                status="failed",
                payload={"error": f"db parse failed: {type(e).__name__}: {e}"},
            ),
        )
        return
    await progress_publish(
        task_id,
        ProgressEvent(
            stage=Stage.EXTRACT_TOPICS_PARSE,
            status="completed",
            payload={
                "byte_count": sum(len(r["content_md"]) for r in resources_payload),
            },
        ),
    )

    # 2. llm（最多 1 次重试）：mcp_client_lifespan 包住 LLM 调用，
    #    LLMAgent 需要真 mcp client 来 fetch_skill（不能用 None）。
    drafts: list[TopicDraft] = []
    last_error: str = ""
    async with mcp_client_lifespan() as mcp:
        for attempt in range(2):
            if attempt == 0:
                await progress_publish(
                    task_id,
                    ProgressEvent(stage=Stage.EXTRACT_TOPICS_LLM, status="running"),
                )
            else:
                await progress_publish(
                    task_id,
                    ProgressEvent(
                        stage=Stage.EXTRACT_TOPICS_LLM,
                        status="running",
                        payload={"retry": True, "last_error": last_error},
                    ),
                )
            registry = llm_registry
            agent = LLMAgent(mcp_client=mcp, llm_registry=registry)
            env = Envelope(
                action="skill.execute",
                sender=ActorRef(type="script", id="extract_topics"),
                target=ActorRef(
                    type="skill", id="skill.resource.extract_topics"
                ),
                payload={"resources": resources_payload},
            )
            try:
                response_text = await asyncio.wait_for(
                    agent.run("skill.resource.extract_topics", env),
                    timeout=TIMEOUT_LLM_SEC,
                )
            except asyncio.TimeoutError:
                await progress_publish(
                    task_id,
                    ProgressEvent(
                        stage=Stage.EXTRACT_TOPICS_LLM,
                        status="failed",
                        payload={"error": f"llm timeout >{TIMEOUT_LLM_SEC}s"},
                    ),
                )
                return
            except Exception as e:  # noqa: BLE001 — 任何未预期异常（无 adapter / MCP 错 / JSON 错）都推 failed
                await progress_publish(
                    task_id,
                    ProgressEvent(
                        stage=Stage.EXTRACT_TOPICS_LLM,
                        status="failed",
                        payload={"error": f"{type(e).__name__}: {e}"},
                    ),
                )
                return

            # parse output → schema validate
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as e:
                last_error = f"json decode: {e}"
                continue
            try:
                drafts = _validate_topics(data, input_ids)
                break
            except _SchemaValidationError as e:
                last_error = str(e)
                continue

    if not drafts:
        await progress_publish(
            task_id,
            ProgressEvent(
                stage=Stage.EXTRACT_TOPICS_VALIDATE,
                status="failed",
                payload={
                    "error": f"schema rejected after 2 attempts: {last_error}",
                },
            ),
        )
        return

    await progress_publish(
        task_id,
        ProgressEvent(
            stage=Stage.EXTRACT_TOPICS_LLM,
            status="completed",
            payload={"topic_count": len(drafts)},
        ),
    )
    # 3. validate
    await progress_publish(
        task_id,
        ProgressEvent(stage=Stage.EXTRACT_TOPICS_VALIDATE, status="running"),
    )
    await progress_publish(
        task_id,
        ProgressEvent(
            stage=Stage.EXTRACT_TOPICS_VALIDATE,
            status="completed",
            payload={"draft_count": len(drafts)},
        ),
    )

    # 4. write (整删 + INSERT KP + INSERT MapNode，事务)
    await progress_publish(
        task_id,
        ProgressEvent(stage=Stage.EXTRACT_TOPICS_WRITE, status="running"),
    )
    created_node_ids: list[str] = []
    try:
        async with factory() as session:
            async with session.begin():
                # 整删该 student 的私有地图（FK CASCADE 清 Level/Exercise/Completion）
                await session.execute(
                    delete(MapNode).where(MapNode.student_id == str(student_id))
                )
                # 孤儿 KP 清理（仅清"由用户 md 蒸馏出来的 KP"：source is not null
                # 且没有 MapNode.kp_id 引用它）
                orphan_kps = (
                    await session.execute(
                        select(KnowledgePoint).where(
                            KnowledgePoint.source.is_not(None),
                            ~select(MapNode.kp_id)
                            .where(MapNode.kp_id == KnowledgePoint.kp_id)
                            .exists(),
                        )
                    )
                ).scalars().all()
                for kp in orphan_kps:
                    await session.delete(kp)
                # INSERT 新 KP 和 MapNode
                for col, draft in enumerate(drafts):
                    src_name = next(
                        (
                            r["name"]
                            for r in resources_payload
                            if r["id"] == draft.source_resource_id
                        ),
                        None,
                    )
                    kp = KnowledgePoint(
                        subject="用户提炼",
                        title=draft.title,
                        description=draft.description,
                        difficulty=2,
                        prerequisites=draft.prerequisites,
                        source=src_name,
                        source_content_md=draft.excerpt_text,
                    )
                    session.add(kp)
                    await session.flush()
                    node = MapNode(
                        student_id=str(student_id),
                        kp_id=kp.kp_id,
                        status="active",
                        branch_type="main",
                        position={"col": col % 5, "row": col // 5},
                    )
                    session.add(node)
                    await session.flush()
                    created_node_ids.append(str(node.node_id))
    except Exception as e:  # noqa: BLE001
        await progress_publish(
            task_id,
            ProgressEvent(
                stage=Stage.EXTRACT_TOPICS_WRITE,
                status="failed",
                payload={
                    "error": f"db write failed: {type(e).__name__}: {e}",
                },
            ),
        )
        return

    await progress_publish(
        task_id,
        ProgressEvent(
            stage=Stage.EXTRACT_TOPICS_WRITE,
            status="completed",
            payload={"created_node_ids": created_node_ids},
        ),
    )
    # 5. done
    await progress_publish(
        task_id,
        ProgressEvent(
            stage=Stage.EXTRACT_TOPICS_DONE,
            status="completed",
            payload={
                "created_node_ids": created_node_ids,
                "extracted_resource_count": len(resources_payload),
            },
        ),
    )
