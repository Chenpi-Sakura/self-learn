"""Onboarding HTTP 路由测试。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from selflearn.gateway.routes.onboarding import router


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_get_questions_returns_8(client: TestClient) -> None:
    res = client.get("/api/onboarding/questions")
    assert res.status_code == 200
    data = res.json()
    assert "questions" in data
    assert 7 <= len(data["questions"]) <= 8


def test_post_submit_success(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    async def fake_onboard(student_id, answers, agent):
        return {
            "ok": True,
            "dimensions": {"kb": 0.7, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
            "reasoning": "ok",
            "snapshot_id": 99,
        }

    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._run_onboard",
        fake_onboard,
    )

    payload = {
        "student_id": "sid",
        "answers": [
            {"question_id": "q1_kb", "choice": "a"},
        ],
    }
    res = client.post("/api/onboarding/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["dimensions"]["kb"] == 0.7
    assert data["snapshot_id"] == 99


def test_post_submit_already_onboarded(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    async def fake_onboard(student_id, answers, agent):
        return {"ok": False, "error": "already_onboarded"}

    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._run_onboard", fake_onboard
    )
    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._build_agent",
        lambda: MagicMock(),
    )

    res = client.post(
        "/api/onboarding/submit",
        json={"student_id": "sid", "answers": [{"question_id": "q1_kb", "choice": "a"}]},
    )
    assert res.status_code == 409
    assert res.json()["error"] == "already_onboarded"


def test_post_submit_answers_mismatch(client: TestClient) -> None:
    """answers 为空 → Pydantic min_length=1 → 422。"""
    res = client.post(
        "/api/onboarding/submit",
        json={"student_id": "sid", "answers": []},
    )
    assert res.status_code == 422


def test_post_submit_llm_failure(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    async def fake_onboard(student_id, answers, agent):
        return {"ok": False, "error": "onboard_lint_failed"}

    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._run_onboard", fake_onboard
    )
    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._build_agent",
        lambda: MagicMock(),
    )

    res = client.post(
        "/api/onboarding/submit",
        json={"student_id": "sid", "answers": [{"question_id": "q1_kb", "choice": "a"}]},
    )
    assert res.status_code == 500
    assert res.json()["error"] == "onboard_failed"
