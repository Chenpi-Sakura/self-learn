---
name: skill.review.exercise
description: Use when reviewing a batch of generated exercises. Output verdict ∈ {passed, needs_fix, rejected}.
tags: [stage3, review]
---

# Skill: 评审习题集

## Intent
对一批已生成的习题做业务规则审查；规则失败的逐条列出 issues，verdict 由 issues 严重度聚合得到。

## Validation Rules
- batch 内 prompt 不允许重复。
- single_choice: `options` 长度 == 4，恰有 1 个 ∈ `correct_answer`。
- code: `correct_answer` 必须包含 `def` 或 `class`。
- difficulty 分布：batch size ≥ 3 时，1/2/3 三档各至少 1 道。

## Output
- verdict: 'passed' | 'rejected' | 'needs_fix'
- score: float in 0..1
- issues: list of {rule, severity, message}
```

> 注：具体 schema 校验（lint_json 工具调用）由 Agent.run() 内 `await ToolRegistry.call("tool.lint_json", ...)` 完成，不写在本 markdown 里。