"""Task 262: 一次性回填脚本 — 找到 lecture_html IS NULL 的 Level，删除后重跑
Director 链重新生成（Task 261 之后，exercise.explanation 才会引用 lecture_outline）。

用法:
    uv run python -m scripts.backfill_lecture_html
    uv run python -m scripts.backfill_lecture_html --dry-run
    uv run python -m scripts.backfill_lecture_html --limit 10 --sleep 3

幂等：执行前 SELECT WHERE lecture_html IS NULL；处理完每个 node 后立即重新 SELECT。
失败重试友好：单个 node 失败只 print error 继续下一个。

成本控制：
  - 每次默认最多 50 个 node（--limit）
  - 每次迭代间隔 2s（--sleep，避免触发 LLM rate limit）
  - dry-run 模式只打印不动手
"""
from __future__ import annotations

import argparse
import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select

from selflearn.agents.core import LLMAgent
from selflearn.agents.director import run_director_chain_with_retry
from selflearn.agents.review_stage import ReviewStage
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.exercise import Exercise
from selflearn.domain.level import Level
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.llm.registry import LLMRegistry
from selflearn.mcp_client import mcp_client_lifespan


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill lecture_html for NULL levels.")
    p.add_argument("--dry-run", action="store_true",
                   help="仅列出受影响的 node_ids，不执行删除/重生成。")
    p.add_argument("--limit", type=int, default=50,
                   help="本次最多处理的关卡数（默认 50）。")
    p.add_argument("--sleep", type=float, default=2.0,
                   help="每个 node 之间的间隔秒数（默认 2.0）。")
    return p.parse_args()


async def _list_null_lecture_nodes(limit: int) -> list[tuple[str, str]]:
    """返回 [(node_id, student_id), ...]，每个 node 取最新一条 NULL lecture 的 Level。"""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(Level.node_id, func.max(Level.created_at).label("max_created"))
            .where(Level.lecture_html.is_(None))
            .group_by(Level.node_id)
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()
        results: list[tuple[str, str]] = []
        for node_id, _max_created in rows:
            mn = await session.get(MapNode, node_id)
            if mn is None:
                print(f"[backfill] WARN: node {node_id} 找不到 MapNode 记录，跳过")
                continue
            results.append((str(node_id), str(mn.student_id)))
        return results


async def _delete_null_lecture_level(node_id: str) -> str | None:
    """删除该 node 的 lecture_html IS NULL 的 Level，返回被删除的 level_id。"""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(Level)
            .where(Level.node_id == UUID(node_id), Level.lecture_html.is_(None))
            .order_by(Level.created_at.desc())
            .limit(1)
        )
        level = (await session.execute(stmt)).scalars().first()
        if level is None:
            return None
        level_id = level.level_id
        # FK ondelete=CASCADE 在 domain/level.py:17 已声明；显式 delete 更稳。
        await session.execute(delete(Exercise).where(Exercise.level_id == level_id))
        await session.delete(level)
        await session.commit()
        return str(level_id)


async def _regenerate(
    node_id: str, student_id: str, mcp: Any, agent: Any, review: Any
) -> dict[str, Any]:
    """通过 run_director_chain_with_retry 重新生成关卡。"""
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="script", id="backfill_lecture_html"),
        target=ActorRef(type="skill", id="skill.director.start"),
        payload={"student_id": student_id, "node_id": node_id},
    )
    return await run_director_chain_with_retry(env, agent, review)


async def main() -> None:
    args = _parse_args()
    print(f"[backfill] start: dry_run={args.dry_run} limit={args.limit} sleep={args.sleep}")

    targets = await _list_null_lecture_nodes(args.limit)
    print(f"[backfill] found {len(targets)} node(s) with lecture_html IS NULL")

    if args.dry_run:
        for node_id, student_id in targets:
            print(f"[backfill] would_process node_id={node_id} student_id={student_id}")
        print("[backfill] dry-run done")
        return

    if not targets:
        print("[backfill] nothing to do")
        return

    registry = LLMRegistry()
    success = 0
    failed = 0
    async with mcp_client_lifespan() as mcp:
        agent = LLMAgent(mcp, registry)
        review = ReviewStage(agent, mcp)
        for idx, (node_id, student_id) in enumerate(targets):
            print(f"[backfill] ({idx + 1}/{len(targets)}) node_id={node_id} student_id={student_id}")
            try:
                deleted_level_id = await _delete_null_lecture_level(node_id)
                print(f"[backfill]   deleted level_id={deleted_level_id}")
                result = await _regenerate(node_id, student_id, mcp, agent, review)
                print(
                    f"[backfill]   regenerated: new_level_id={result['level_id']} "
                    f"exercises={result['exercises_count']}"
                )
                success += 1
            except Exception as e:  # noqa: BLE001 — 单条失败不影响后续
                failed += 1
                print(f"[backfill]   ERROR: {type(e).__name__}: {e}")
            if idx + 1 < len(targets):
                await asyncio.sleep(args.sleep)

    print(f"[backfill] done: success={success} failed={failed} total={len(targets)}")


if __name__ == "__main__":
    asyncio.run(main())