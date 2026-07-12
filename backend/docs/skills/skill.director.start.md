---
name: skill.director.start
description: Use when starting a level from the first active map node. Director is the orchestrator; sub-agent calls are hardcoded in Agent code.
tags: [stage3, director]
---

# Skill: 关卡推进（Director）

## Intent
为学生选定当前第一个 status=active 的 MapNode，串起"出题 → 评审 → 入库"完整流程，写入 levels + exercises + review_results 表。

## Validation Rules
- 必须存在至少 1 个 active 节点，否则抛 NO_ACTIVE_NODE。
- 必须完整跑完 出题 + 评审；任何阶段失败 → 整流程失败，不写库。
- Exercise 必须通过 Review.verdict ∈ {passed, needs_fix}；verdict=rejected → 整流程失败。

## Failure Handling
- 任何异常必须 try/except 捕获 → push progress(FAILED, payload={code, message}) → 抛 AppError。
- SSE 端点看到 FAILED 后关闭连接，前端可识别为中断。
```

> 注：选节点 / 调 ExerciseAgent.run_sync / 调 ReviewAgent.review / 写库 这一串动作由 DirectorAgent.run() 用 Python 代码硬编排完成，不写在本 markdown 里。