---
name: skill.exercise.generate
description: Use when generating exercises from a knowledge point. LLM must output JSON only; Agent is responsible for fetching prompt template and validating output.
tags: [stage3, exercise, generation]
output_schema: schemas/exercise.schema.json
---

# Skill: 生成合规习题

## Intent
根据 knowledge_point 生成 N 道习题，LLM 严格按 Output Schema 输出 JSON，不允许散文、不允许虚构字段。

## Output Schema
See `schemas/exercise.schema.json` — required fields: exercise_type, prompt, options, correct_answer, difficulty (1-3), score。

## Validation Rules
- batch 内 prompt 不允许重复。
- difficulty ∈ {1, 2, 3}。
- single_choice: `options` 长度 == 4，恰有 1 个 ∈ `correct_answer`。
- fill_blank: `correct_answer` 非空，prompt 含恰好一个 "____"。
- code: `correct_answer` 必须包含 Python `def` 或 `class` 定义。

## Common Mistakes
- LLM 返回夹杂散文 → 解析时必须用 extract-from-fence。
- difficulty 全部相同 → 必须按 1/2/3 大致均匀分布。
```

> 注：本 markdown 不写 `Call tool.fetch_template(...)` 之类的 Tool 调用指令。Tool 调用由 Agent 代码 `await ToolRegistry.call(...)` 硬编排完成。