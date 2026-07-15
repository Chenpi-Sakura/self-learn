---
name: skill.review.exercise.llm
description: Use when running LLM semantic review on a batch of exercises. Inputs are exercises list, kp_title, optional prior issues. Returns verdict ∈ {passed, needs_revision} and suggestions for revision.
output_schema: null
mcp_prefetch: []
mcp_tool_use: []
max_retries: 0
---

# Skill: LLM 语义审查

## Intent
调 LLM 检查习题的语义质量：
- 题目是否真的考 kp_title
- explanation 是否与 correct_answer 自洽
- 题目措辞是否清晰无歧义

## Input
- exercises: list[dict]
- kp_title: string
- prior_issues: list[dict] (optional, 上轮 LLM 给的)

## Output
- verdict: "passed" | "needs_revision"
- suggestions: list[str]  (给 exercise LLM 的修改意见)
- issues: list[{rule, severity, message}]

## 审查要点
- 题目 vs KP 一致性：题目应明确问 kp 涉及的概念
- 答案 vs 解释：correct_answer 应在 explanation 里有推理依据
- 难度匹配：difficulty 与实际题目深度一致
- 措辞：避免歧义、避免引导性问题
