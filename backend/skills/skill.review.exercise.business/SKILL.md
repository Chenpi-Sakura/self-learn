---
name: skill.review.exercise.business
description: "Use when running business-rule checks on a batch of exercises. Returns verdict ∈ {passed, rejected, needs_fix} and issues list."
mcp_prefetch: []
mcp_tool_use:
  - tool.lint_json
max_retries: 0
---

# Skill: 业务规则审查

## Intent
对一批习题做业务规则审查；规则失败列出 issues，verdict 由 issues 严重度聚合。

## Validation Rules
- lint_json 必过
- batch 内 prompt 不允许重复
- single_choice: options 长度 ≥ 2
- single_choice: correct_answer ∈ options
- code: correct_answer 必须包含 "def" 或 "class"
- difficulty 分布：batch size ≥ 3 时 1/2/3 各至少 1 道

## Output
- verdict: passed | rejected | needs_fix
- score: float 0..1
- issues: list[{rule, severity, message}]
