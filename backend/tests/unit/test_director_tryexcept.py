"""DirectorAgent try/except 兜底测试（Task 11，V1.1 修复）。

Director.run 任何未捕获异常必须先推 FAILED 进度事件，再抛 AppError。
避免 SSE 端点陷入死等。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


async def test_director_uncaught_exception_publishes_failed_and_raises() -> None:
    """ExerciseAgent.run_sync 抛异常时，Director 必须推 FAILED + 抛 AppError(INTERNAL)。"""
    from selflearn.agents.builtin.director_agent import DirectorAgent
    from selflearn.core.envelope import ActorRef, Envelope
    from selflearn.core.errors import AppError, ErrorCode
    from selflearn.progress.stages import ProgressEvent, Stage

    published: list[ProgressEvent] = []

    async def collect(trace_id: str, ev: ProgressEvent) -> None:
        published.append(ev)

    # mock get_skill 避免 KeyError
    fake_skill = MagicMock()
    fake_skill.body = "skill body"
    # mock session 返回 active node
    fake_node = MagicMock()
    fake_node.node_id = "00000000-0000-0000-0000-000000000aaa"
    fake_node.kp.title = "Mock KP"

    with patch("selflearn.agents.builtin.director_agent.get_skill", return_value=fake_skill), \
         patch("selflearn.agents.builtin.director_agent.ExerciseAgent") as mock_ex_cls, \
         patch("selflearn.agents.builtin.director_agent.progress_publish",
               new=AsyncMock(side_effect=collect)), \
         patch("selflearn.agents.builtin.director_agent.get_session_factory") as mock_factory:
        mock_ex_cls.return_value.run_sync = AsyncMock(side_effect=RuntimeError("boom in ExerciseAgent"))
        # 让 _run_inner 的 active node 查询返回 fake_node
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value.execute.return_value.scalars.return_value.first.return_value = fake_node
        mock_factory.return_value.return_value = mock_session

        agent = DirectorAgent()
        env = Envelope(
            action="skill.execute",
            sender=ActorRef(type="gateway", id="g"),
            target=ActorRef(type="skill", id="skill.director.start"),
            payload={"student_id": "00000000-0000-0000-0000-000000000aaa"},
            trace_id="dir-fail-test",
        )
        with pytest.raises(AppError) as exc:
            await agent.run(env)

    failed = [e for e in published if e.stage == Stage.FAILED]
    assert failed, f"Director 必须推 FAILED 事件，实际 {published}"
    assert exc.value.code == ErrorCode.INTERNAL


async def test_director_failed_event_contains_traceback() -> None:
    """ExerciseAgent.run_sync 抛异常时，FAILED 事件 payload 必须含 tb 字段。"""
    from contextlib import asynccontextmanager
    from selflearn.agents.builtin.director_agent import DirectorAgent
    from selflearn.core.envelope import ActorRef, Envelope
    from selflearn.progress.stages import ProgressEvent, Stage

    published: list[ProgressEvent] = []

    async def collect(trace_id: str, ev: ProgressEvent) -> None:
        published.append(ev)

    fake_skill = MagicMock()
    fake_skill.body = "skill body"
    fake_node = MagicMock()
    fake_node.node_id = "00000000-0000-0000-0000-000000000bbb"
    fake_node.kp.title = "Mock KP"

    @asynccontextmanager
    async def fake_session_cm():
        yield AsyncMock()

    def fake_factory() -> object:
        return fake_session_cm()

    with patch("selflearn.agents.builtin.director_agent.get_skill", return_value=fake_skill), \
         patch("selflearn.agents.builtin.director_agent.ExerciseAgent") as mock_ex_cls, \
         patch("selflearn.agents.builtin.director_agent.progress_publish",
               new=AsyncMock(side_effect=collect)), \
         patch("selflearn.agents.builtin.director_agent.get_session_factory", return_value=fake_factory):
        # 让 _run_inner 的 node 查询正常返回 fake_node，再让 run_sync 抛 ValueError
        # 第一个 session（node 查询）：让 execute().scalars().first() 返回 fake_node
        # 第二个 session（difficulty 查询）：允许空 recent_scores
        call_count = {"n": 0}

        async def fake_execute(stmt: object) -> object:  # noqa: ARG001
            r = MagicMock()
            r.scalars.return_value.first.return_value = fake_node
            call_count["n"] += 1
            return r

        # 通过 patch factory 的实现来控制 session 的 execute 行为
        @asynccontextmanager
        async def cm_node_query():
            s = AsyncMock()
            s.execute = fake_execute
            yield s

        @asynccontextmanager
        async def cm_difficulty_query():
            s = AsyncMock()
            r = MagicMock()
            r.scalars.return_value.all.return_value = []  # 无历史分数 → medium
            s.execute.return_value = r
            yield s

        @asynccontextmanager
        async def cm_unused():
            yield AsyncMock()

        sessions = iter([cm_node_query(), cm_difficulty_query(), cm_unused(), cm_unused()])

        def factory_seq() -> object:
            return next(sessions)

        with patch("selflearn.agents.builtin.director_agent.get_session_factory", return_value=factory_seq):
            mock_ex_cls.return_value.run_sync = AsyncMock(side_effect=ValueError("boom_with_tb"))

            agent = DirectorAgent()
            env = Envelope(
                action="skill.execute",
                sender=ActorRef(type="gateway", id="g"),
                target=ActorRef(type="skill", id="skill.director.start"),
                payload={"student_id": "00000000-0000-0000-0000-000000000bbb"},
                trace_id="dir-tb-test",
            )
            with pytest.raises(Exception):
                await agent.run(env)

    failed = [e for e in published if e.stage == Stage.FAILED]
    assert failed, "FAILED event 必须推"
    assert failed[0].payload.get("tb"), "FAILED payload 必须含 tb 字段"
    assert "boom_with_tb" in failed[0].payload["tb"]