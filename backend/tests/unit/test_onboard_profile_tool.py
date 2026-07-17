"""tool.onboard_profile 单测：mock LLM 路径 + clamp + 缺维度 + 重复 onboarding。"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from selflearn.mcp_server.tools.onboard_profile import onboard_profile


def _fake_env() -> dict[str, Any]:
    return {
        "trace_id": "test-trace",
        "sender": {"type": "test", "id": "test"},
        "target": {"type": "skill", "id": "skill.profile.onboard"},
        "payload": {"student_id": "sid"},
    }


def _fake_agent(llm_output: str) -> MagicMock:
    """Mock LLMAgent.run 返回固定字符串。"""
    agent = MagicMock()
    agent.run = AsyncMock(return_value=llm_output)
    return agent


def _good_dims_payload() -> str:
    return json.dumps(
        {
            "kb": 0.72,
            "vp": 0.55,
            "as": 0.80,
            "ge": 0.30,
            "ept": 0.65,
            "fd": 0.45,
            "reasoning": "从你的回答来看...",
        },
        ensure_ascii=False,
    )


@pytest.mark.asyncio
async def test_onboard_profile_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """正常：LLM 返回合规 JSON → tool 写 profile + snapshot，返回 ok=True。"""
    created: list[dict] = []
    snapshots: list[dict] = []

    async def fake_get_profile(student_id: str) -> dict:
        return {"ok": False, "error": "profile_not_found"}

    async def fake_create_profile(student_id: str, dimensions: dict, tags: list | None = None) -> dict:
        created.append({"student_id": student_id, "dimensions": dimensions, "tags": tags})
        return {"ok": True, "profile_id": "pid-123", "updated": False}

    async def fake_write_snapshot(student_id: str, profile: dict, trigger: str) -> int:
        snapshots.append({"student_id": student_id, "profile": profile, "trigger": trigger})
        return 42

    monkeypatch.setattr(
        "selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile
    )
    monkeypatch.setattr(
        "selflearn.mcp_server.tools.onboard_profile.create_profile", fake_create_profile
    )
    monkeypatch.setattr(
        "selflearn.mcp_server.tools.onboard_profile._write_snapshot", fake_write_snapshot
    )

    agent = _fake_agent(_good_dims_payload())
    answers = [{"question_id": "q1_kb", "choice": "a"}]

    result = await onboard_profile("sid", answers, agent)

    assert result["ok"] is True
    assert result["dimensions"]["kb"] == 0.72
    assert result["dimensions"]["as"] == 0.80
    assert result["snapshot_id"] == 42
    assert created[0]["tags"] == ["onboarded"]
    assert snapshots[0]["trigger"] == "onboarding"


@pytest.mark.asyncio
async def test_onboard_profile_clamp_out_of_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 返回 1.5 / -0.3 → tool clamp 到 [0,1]。"""
    async def fake_get_profile(student_id: str) -> dict:
        return {"ok": False, "error": "profile_not_found"}

    async def fake_create_profile(student_id: str, dimensions: dict, tags: list | None = None) -> dict:
        return {"ok": True, "profile_id": "p", "updated": False}

    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile)
    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.create_profile", fake_create_profile)
    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile._write_snapshot",
                        AsyncMock(return_value=1))

    payload = json.dumps({
        "kb": 1.5, "vp": -0.3, "as": 0.5,
        "ge": 0.5, "ept": 0.5, "fd": 0.5,
        "reasoning": "test",
    })
    agent = _fake_agent(payload)

    result = await onboard_profile("sid", [], agent)

    assert result["ok"] is True
    assert result["dimensions"]["kb"] == 1.0
    assert result["dimensions"]["vp"] == 0.0


@pytest.mark.asyncio
async def test_onboard_profile_missing_dim_defaults_to_half(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 只返回 4 维 → 缺维度补 0.5。"""
    async def fake_get_profile(student_id: str) -> dict:
        return {"ok": False, "error": "profile_not_found"}

    async def fake_create_profile(student_id: str, dimensions: dict, tags: list | None = None) -> dict:
        return {"ok": True, "profile_id": "p", "updated": False}

    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile)
    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.create_profile", fake_create_profile)
    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile._write_snapshot",
                        AsyncMock(return_value=1))

    payload = json.dumps({
        "kb": 0.7, "vp": 0.3, "as": 0.5, "ge": 0.5,
        "reasoning": "缺 ept 和 fd",
    })
    agent = _fake_agent(payload)

    result = await onboard_profile("sid", [], agent)

    assert result["dimensions"]["kb"] == 0.7
    assert result["dimensions"]["ept"] == 0.5  # 补默认
    assert result["dimensions"]["fd"] == 0.5


@pytest.mark.asyncio
async def test_onboard_profile_already_initialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Profile 已有非默认 dimensions → 返回 already_onboarded，不调 LLM。"""
    async def fake_get_profile(student_id: str) -> dict:
        return {
            "ok": True,
            "profile_id": "p",
            "dimensions": {"kb": 0.8, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
            "tags": [],
        }

    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile)

    agent = _fake_agent(_good_dims_payload())
    result = await onboard_profile("sid", [], agent)

    assert result == {"ok": False, "error": "already_onboarded"}
    agent.run.assert_not_called()  # LLM 不能被调


@pytest.mark.asyncio
async def test_onboard_profile_lint_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 返回完全非 JSON → 返回 onboard_lint_failed。"""
    async def fake_get_profile(student_id: str) -> dict:
        return {"ok": False, "error": "profile_not_found"}

    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile)

    agent = _fake_agent("not json at all")
    result = await onboard_profile("sid", [], agent)

    assert result["ok"] is False
    assert result["error"] == "onboard_lint_failed"