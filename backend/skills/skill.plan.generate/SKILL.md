---
name: skill.plan.generate
description: "Use when generating a treasure map of 5-10 knowledge points for a new student. Idempotent: skips if nodes exist."
mcp_prefetch:
  - tool.get_existing_nodes
  - tool.get_kps
mcp_tool_use: []
max_retries: 0
---

# Skill: 藏宝图生成

## Intent
为新学生生成 5-10 个 MapNode；已有节点则跳过（幂等）。

## Validation Rules
- 已有任何 MapNode → 跳过
- KP 数 < 5 → 报错

## Output
- node_ids: list[UUID]
