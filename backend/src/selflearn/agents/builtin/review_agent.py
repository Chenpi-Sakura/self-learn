"""ReviewAgent: rule-based filtering (JSON validity / duplicate prompts / answer format / difficulty gradient)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import Envelope
from selflearn.skills.library import get as get_skill
from selflearn.tools.protocol import ToolRegistry


@dataclass
class Review:
    verdict: str  # "passed" | "rejected" | "needs_fix"
    score: float
    issues: list[dict[str, Any]] = field(default_factory=list)


class ReviewAgent(AbstractAgent):
    """skill.review.exercise: business-rule filter + Skill load for developer-doc-grade sanity check."""

    agent_id = "review-01"
    agent_type = "review"
    queue = "agent.review.work"

    async def run(self, env: Envelope) -> Envelope:
        return env  # pragma: no cover - synchronous call mode

    async def run_sync(self, env: Envelope, exercises: list[dict[str, Any]]) -> Review:
        return await self.review(exercises)

    async def review(self, exercises: list[dict[str, Any]]) -> Review:
        issues: list[dict[str, Any]] = []

        # 1. tool.lint_json first (cold post-validation)
        lint = await ToolRegistry.call(
            name="tool.lint_json", payload=exercises, schema="exercise"
        )
        if not lint.ok:
            return Review(
                verdict="rejected",
                score=0.0,
                issues=[{"rule": "lint_json", "severity": "high", "message": lint.error}],
            )

        # 2. business rules
        # 2a. duplicate prompt
        seen_prompts: set[str] = set()
        for ex in exercises:
            prompt = str(ex["prompt"])
            if prompt in seen_prompts:
                issues.append(
                    {
                        "rule": "duplicate_prompt",
                        "severity": "medium",
                        "message": f"duplicate prompt: {prompt}",
                    }
                )
            seen_prompts.add(prompt)

        # 2b. single_choice: options length == 4, and correct_answer ∈ options
        for ex in exercises:
            if ex["exercise_type"] == "single_choice":
                opts = ex.get("options") or []
                if len(opts) != 4:
                    issues.append(
                        {
                            "rule": "options_length",
                            "severity": "medium",
                            "message": (
                                f"prompt {str(ex['prompt'])[:20]} options length {len(opts)} != 4"
                            ),
                        }
                    )
                if ex["correct_answer"] not in opts:
                    issues.append(
                        {
                            "rule": "answer_not_in_options",
                            "severity": "high",
                            "message": f"answer {ex['correct_answer']} not in options {opts}",
                        }
                    )

        # 2c. difficulty distribution: when ≥3 items, all three classes present
        if len(exercises) >= 3:
            diffs = {int(ex["difficulty"]) for ex in exercises}
            if not {1, 2, 3}.issubset(diffs):
                issues.append(
                    {
                        "rule": "difficulty_gradient",
                        "severity": "low",
                        "message": f"difficulty coverage missing: present {sorted(diffs)}",
                    }
                )

        # 3. verdicts
        if any(i["severity"] == "high" for i in issues):
            return Review(verdict="rejected", score=0.0, issues=issues)
        if issues:
            return Review(verdict="needs_fix", score=0.6, issues=issues)

        # load skill for "looks-like" sanity check (developer doc: problem sets must pass business rules)
        get_skill("skill.review.exercise")
        return Review(verdict="passed", score=1.0, issues=[])