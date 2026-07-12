"""Unit tests for ExerciseAgent (Task 9).

V1.3 Rule #15 测试范例：前置打包 → LLM → 后置校验 + 1 次重试。

注意：patch 必须打在 `selflearn.agents.builtin.exercise_agent` 模块下的
`llm_registry` / `ToolRegistry` 名字，因为 agent 用了
`from ... import llm_registry`（不是属性查找）。
"""
import json
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from selflearn.tools.protocol import ToolResult

pytestmark = pytest.mark.asyncio


async def test_exercise_agent_lint_failure_raises() -> None:
    """Exercise Agent: tool.lint_json 拒收时抛 EXERCISE_INVALID（即便 2 次重试）。"""
    from selflearn.skills.library import load_all as _load_all
    _load_all()  # Ensure real SKILLS_DIR is loaded (worker does this on startup)

    # patch the local import name (not the module attribute) - exercise_agent does
    # `from selflearn.llm.registry import llm_registry`.
    with patch("selflearn.agents.builtin.exercise_agent.llm_registry") as mock_reg_local:
        mock_reg_local.default.return_value.chat = AsyncMock(
            return_value='[{"exercise_type":"single_choice","prompt":"Q?","correct_answer":"A"}]'  # 缺字段
        )

        with patch("selflearn.agents.builtin.exercise_agent.ToolRegistry.call") as mock_tool:
            # fetch_template succeeds; lint_json fails twice (1 attempt + 1 retry)
            def _fake_tool_call(*args: object, **kw: object) -> ToolResult:
                name = args[0] if args else kw.get("name", "")
                if name == "tool.fetch_template":
                    return ToolResult(ok=True, data={"content": "exercise tmpl"})
                return ToolResult(ok=False, error="schema_violation: 'difficulty' is a required property")

            mock_tool.side_effect = _fake_tool_call

            from selflearn.agents.builtin.exercise_agent import ExerciseAgent
            from selflearn.core.envelope import ActorRef, Envelope
            from selflearn.core.errors import AppError, ErrorCode

            # fake node 满足 Node protocol（仅需 node_id + kp）
            fake_kp = AsyncMock()
            fake_kp.title = "Mock KP"
            fake_node = AsyncMock()
            fake_node.node_id = UUID("00000000-0000-0000-0000-000000000001")
            fake_node.kp = fake_kp

            env = Envelope(
                action="skill.execute",
                sender=ActorRef(type="director", id="d"),
                target=ActorRef(type="skill", id="skill.exercise.generate"),
                payload={"node_id": str(fake_node.node_id)},
                trace_id="test-trace-1",
            )
            with pytest.raises(AppError) as exc:
                await ExerciseAgent().run_sync(env, node=fake_node)
            assert exc.value.code == ErrorCode.EXERCISE_INVALID


async def test_exercise_agent_returns_list_on_valid() -> None:
    from selflearn.skills.library import load_all as _load_all
    _load_all()  # Ensure real SKILLS_DIR is loaded (worker does this on startup)

    valid_json = json.dumps([{
        "exercise_type": "single_choice",
        "prompt": "Transformer 的核心是？",
        "options": ["RNN", "Self-Attention", "CNN", "GAN"],
        "correct_answer": "Self-Attention",
        "explanation": "Self-Attn 是 Transformer 的核心。",
        "difficulty": 2,
        "score": 1.5,
    }])

    with patch("selflearn.agents.builtin.exercise_agent.llm_registry") as mock_reg_local:
        mock_reg_local.default.return_value.chat = AsyncMock(return_value=valid_json)
        with patch("selflearn.agents.builtin.exercise_agent.ToolRegistry.call") as mock_tool:
            # fetch_template succeeds; lint_json succeeds
            def _fake_tool_call(*args: object, **kw: object) -> ToolResult:
                name = args[0] if args else kw.get("name", "")
                if name == "tool.fetch_template":
                    return ToolResult(ok=True, data={"content": "exercise tmpl"})
                return ToolResult(ok=True, data={"validated_count": 1})

            mock_tool.side_effect = _fake_tool_call

            from selflearn.agents.builtin.exercise_agent import ExerciseAgent
            from selflearn.core.envelope import ActorRef, Envelope

            fake_kp = AsyncMock()
            fake_kp.title = "Transformer 概览"
            fake_node = AsyncMock()
            fake_node.node_id = UUID("00000000-0000-0000-0000-000000000002")
            fake_node.kp = fake_kp

            env = Envelope(
                action="skill.execute",
                sender=ActorRef(type="director", id="d"),
                target=ActorRef(type="skill", id="skill.exercise.generate"),
                payload={"node_id": str(fake_node.node_id)},
                trace_id="test-trace-2",
            )
            result = await ExerciseAgent().run_sync(env, node=fake_node)
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["correct_answer"] == "Self-Attention"
