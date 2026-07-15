---
name: skill.director.start
description: "Use when starting a level generation chain. Chains lecture.generate → review.lecture → exercise.generate (≤2 revisions) → review.exercise (business + llm) → write DB."
mcp_prefetch:
  - tool.get_active_node
  - tool.get_kp
  - tool.get_recent_scores
mcp_tool_use: []
max_retries: 0
---

# Skill: Director 关卡编排

## Intent
编排端到端关卡生成链。失败重试 3 次（整链重生成）。

## Chain
1. node = mcp.get_active_node(student_id)
2. kp = mcp.get_kp(node.kp_id)
3. recent = mcp.get_recent_scores(student_id, limit=3)
4. difficulty = compute_difficulty(recent)
5. lecture_html = LLMAgent.run("skill.lecture.generate")
6. review_lec = ReviewStage.review_lecture(lecture_html)  # rejected → 整链失败
7. for revision in [0, 1]:
     exercises = LLMAgent.run("skill.exercise.generate", suggestions=...)
     if revision == 0:
       review_biz = ReviewStage.review_exercise_business(exercises)  # rejected → 整链失败
     review_llm = ReviewStage.review_exercise_llm(exercises, kp.title)
     if passed: break
     suggestions = review_llm.suggestions
8. level = mcp.create_level(node_id, lecture_html)
9. mcp.bulk_create_exercises(level_id, exercises)
10. deltas = compute_deltas(final_review.score)
11. mcp.update_profile(student_id, deltas)
12. SSE COMPLETED

## Failure Strategy
- MCP 预拉失败 → retry 整链
- LLM lint 失败 → retry 单步
- 业务规则 rejected → retry 整链
- 写库失败 → retry 整链（依赖 idempotency）
- max_attempts = 3
