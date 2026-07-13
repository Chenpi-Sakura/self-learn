"""DirectorAgent try/except 兜底测试（Task 11，V1.1 修复）。

Director.run 任何未捕获异常必须先推 FAILED 进度事件，再抛 AppError。
避免 SSE 端点陷入死等。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


async def test_director_uncaught_exception_publishes_failed_and_raises() -> None:
    """Director.run 任何未捕获异常必须先推 FAILED 进度事件，再抛 AppError。

    V1.1 修复点：避免 SSE 端点陷入死等。
    """
    from selflearn.agents.builtin.director_agent import DirectorAgent
    from selflearn.core.envelope import ActorRef, Envelope
    from selflearn.core.errors import AppError, ErrorCode
    from selflearn.progress.stages import ProgressEvent, Stage

    # 让 Director 调 exercise_agent.run_sync(...) 时 throw → 让 `_run_inner` 内层跑不下去
    with patch("selflearn.agents.builtin.director_agent.exercise_agent") as mock_ex:
        mock_ex.run_sync = AsyncMock(side_effect=RuntimeError("boom in ExerciseAgent"))

        # 让 progress_publish 收集事件
        published: list[ProgressEvent] = []

        async def collect(trace_id: str, ev: ProgressEvent) -> None:
            published.append(ev)

        with patch(
            "selflearn.agents.builtin.director_agent.progress_publish",
            new=AsyncMock(side_effect=collect),
        ) as mock_pub:
            agent = DirectorAgent()
            env = Envelope(
                action="skill.execute",
                sender=ActorRef(type="gateway", id="g"),
                target=ActorRef(type="skill", id="skill.director.start"),
                payload={"student_id": "00000000-0000-0000-0000-000000000002"},
                trace_id="dir-test-1",
            )
            with pytest.raises(AppError) as exc:
                await agent.run(env)
            assert exc.value.code == ErrorCode.INTERNAL

        # 关键断言：失败时必须推过 FAILED 事件（含 code/message payload）
        failed = [e for e in published if e.stage == Stage.FAILED]
        assert failed, f"Director 必须推 FAILED 事件，实际 {published}"
        assert failed[0].status == "failed"
        assert "code" in failed[0].payload
