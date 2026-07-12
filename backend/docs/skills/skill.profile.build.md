---
name: skill.profile.build
description: Use when building initial 6-dimension profile for a new student. Each dimension is a float in [0, 1].
tags: [stage3, profile]
---

# Skill: 画像构建

## Intent
对学生做 5 轮对话，每轮收集 1 个维度的 [0, 1] 数值；最终输出 6 个维度的完整画像。

## Dimensions
- knowledge_base, visual_preference, analytic_style
- goal_employment, error_prone_type, focus_duration

## Validation Rules
- 每个 dimension ∈ [0, 1]。
- 必须全部 6 个维度齐全后才能写入 profiles 表。

## Common Mistakes
- 任意维度缺失即触发 NEEDS_REINPUT。
- 数值越界 (>1 或 <0) → LLM 必须重新抽取。
```

> 注：5 轮对话内容已在 Gateway 收齐，Agent.run() 仅读 payload.dimensions；调 LLM 做合理性 sanity check 由 Agent 代码用 ChatRequest 走，不写在这里。