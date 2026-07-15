---
name: skill.lecture.generate
description: Use when generating HTML lecture for a knowledge point. Outputs sanitized HTML in white-list tags + pre-defined classes (callout/formula/example). (Placeholder — implementation deferred to backlog 2026-07-15-html-lecture.)
output_schema: null
mcp_prefetch:
  - tool.get_kp
  - tool.get_recent_scores
mcp_tool_use:
  - tool.lint_html
max_retries: 1
---

# Skill: 讲义生成（占位）

## Intent
为知识点生成 HTML 讲义，800-1500 字，白名单标签 + 预定义 class + KaTeX 公式。

## Output
- lecture_html: string (sanitized HTML)

## Status
本 Skill 是预留占位，关联 backlog `docs/superpowers/backlog/2026-07-15-html-lecture.md`。当前 Phase 不调用。
