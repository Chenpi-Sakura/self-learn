"""ReviewStage: 业务规则 + LLM 语义审查。"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError, ErrorCode


@dataclass
class ReviewResult:
    verdict: str
    score: float = 0.0
    issues: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LLMReviewResult:
    verdict: str
    suggestions: list[str] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)


class ReviewStage:
    """Python 强制 stage：业务规则 (5 + lint) + LLM 语义审查。"""

    def __init__(self, llm_agent: Any, mcp: Any) -> None:
        self.llm = llm_agent
        self.mcp = mcp

    async def review_lecture(self, lecture_html: str) -> ReviewResult:
        """lecture 业务规则：lint_html + not_empty。"""
        issues: list[dict[str, Any]] = []
        if not lecture_html:
            return ReviewResult(
                verdict="rejected", score=0.0,
                issues=[{"rule": "not_empty", "severity": "high", "message": "lecture_html 为空"}],
            )
        lint = await self.mcp.call("tool.lint_html", html=lecture_html)
        if lint.get("is_empty"):
            issues.append({"rule": "not_empty", "severity": "high", "message": "lecture_html 清洗后为空"})
        if any(i["severity"] == "high" for i in issues):
            return ReviewResult(verdict="rejected", score=0.0, issues=issues)
        return ReviewResult(verdict="passed", score=1.0, issues=[])

    async def review_exercise_business(self, exercises: list[dict[str, Any]]) -> ReviewResult:
        issues: list[dict[str, Any]] = []
        lint = await self.mcp.call("tool.lint_json", payload=exercises, schema_name="exercise")
        if not lint.get("ok"):
            return ReviewResult(
                verdict="rejected", score=0.0,
                issues=[{"rule": "lint_json", "severity": "high", "message": lint.get("error", "lint_failed")}],
            )
        seen_prompts: set[str] = set()
        for ex in exercises:
            prompt = str(ex.get("prompt", ""))
            if prompt in seen_prompts:
                msg = "duplicate prompt: " + prompt[:20]
                issues.append({"rule": "duplicate_prompt", "severity": "medium", "message": msg})
            seen_prompts.add(prompt)
            if ex.get("exercise_type") == "single_choice":
                opts = ex.get("options") or []
                if len(opts) < 2:
                    msg = "options length " + str(len(opts)) + " < 2"
                    issues.append({"rule": "options_min", "severity": "medium", "message": msg})
                if ex.get("correct_answer") not in opts:
                    msg = "answer " + str(ex.get("correct_answer")) + " not in " + str(opts)
                    issues.append({"rule": "answer_not_in_options", "severity": "high", "message": msg})
        if len(exercises) >= 3:
            diffs = {int(ex.get("difficulty", 1)) for ex in exercises}
            if not {1, 2, 3}.issubset(diffs):
                msg = "missing difficulty in " + str(sorted(diffs))
                issues.append({"rule": "difficulty_gradient", "severity": "low", "message": msg})
        if any(i["severity"] == "high" for i in issues):
            return ReviewResult(verdict="rejected", score=0.0, issues=issues)
        if issues:
            return ReviewResult(verdict="needs_fix", score=0.6, issues=issues)
        return ReviewResult(verdict="passed", score=1.0, issues=[])

    async def review_exercise_llm(
        self, exercises: list[dict[str, Any]], kp_title: str, trace_id: str
    ) -> LLMReviewResult:
        """LLM 语义审查：调 LLMAgent 跑 skill.review.exercise.llm。"""
        import json
        raw = await self.llm.run(
            skill_id="skill.review.exercise.llm",
            env=Envelope(
                action="skill.execute",
                sender=ActorRef(type="review", id="stage"),
                target=ActorRef(type="skill", id="skill.review.exercise.llm"),
                payload={"exercises": exercises, "kp_title": kp_title, "trace_id": trace_id},
            ),
        )
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError) as e:
            raise AppError(ErrorCode.INTERNAL, "review_llm parse failed: " + str(e))
        if not isinstance(data, dict):
            data = {}
        return LLMReviewResult(
            verdict=data.get("verdict", "needs_revision"),
            suggestions=data.get("suggestions", []),
            issues=data.get("issues", []),
        )
