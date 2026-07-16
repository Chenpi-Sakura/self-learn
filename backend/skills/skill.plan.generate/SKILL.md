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

## 实现说明（v1 架构，Python dispatch 内联执行）
- `scheduler._execute_plan_generate()` 在 middleware 层直接处理
- 不调 LLM。Map 生成是确定性逻辑 (KP 读取 + 批量创建 MapNode row)
- 相关 MCP tool: `tool.create_map_nodes`
- 推送 SSE 进度: `progress_publish(Stage.PLAN, ...)`
- v2 计划: 启用 `mcp_tool_use` → 允许 LLM 实时调 `tool.create_map_nodes`
