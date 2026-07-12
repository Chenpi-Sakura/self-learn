---
name: skill.plan.generate
description: Use when generating treasure map (MapNodes + KnowledgePoints) from a built profile. Output is a list of map nodes with embedded KP info.
tags: [stage3, plan]
---

# Skill: 藏宝图生成

## Intent
根据学生 profile.dimensions 生成 5-10 个 MapNode，每个 MapNode 携带一个 KnowledgePoint。

## Validation Rules
- node_count ∈ [5, 10]。
- 每个 node 必含 kp_title / kp_description / difficulty / prerequisites。
- prerequisites 必须引用已存在的 KP id（允许空 list）。
- difficulty ∈ {1, 2, 3}。
```

> 注：KP 落库（store_kp 工具调用）由 Agent.run() 内 `await ToolRegistry.call("tool.store_kp", ...)` 完成，不写在本 markdown 里。