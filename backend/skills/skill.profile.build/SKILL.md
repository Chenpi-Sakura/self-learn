---
name: skill.profile.build
description: "Use when building a student's 6-dimension profile from input dimensions + tags. Outputs dimensions in kb/vp/as/ge/ept/fd short keys."
mcp_prefetch: []
mcp_tool_use: []
max_retries: 0
---

# Skill: 6 维画像构建

## Intent
读 payload.dimensions + tags，6 个维度键（knowledge_base / visual_preference / analytic_style / goal_employment / error_prone_type / focus_duration）映射成短名（kb / vp / as / ge / ept / fd），写 profiles 表。

## Validation Rules
- 6 维必须全填；任一缺失 → 默认 0.5
- dimensions 类型必须是 dict[str, number]
- tags 必须是 list[str]

## Output
- 短名 dimensions 字典（kb / vp / as / ge / ept / fd）
- profile_id (UUID)

## 实现说明（v1 架构，Python dispatch 内联执行）
- `scheduler._execute_profile_build()` 在 middleware 层直接处理
- 不调 LLM。Profile 构建是确定性逻辑 (long→short dimension mapping + DB upsert)
- 调用 MCP tool: `tool.create_profile`
- 推送 SSE 进度: `progress_publish(Stage.PROFILE, ...)`
- v2 计划: 启用 `mcp_tool_use` → 允许 LLM 实时调 `tool.create_profile`
