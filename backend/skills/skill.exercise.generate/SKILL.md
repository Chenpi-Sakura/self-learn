---
name: skill.exercise.generate
description: "Use when generating a batch of 2-4 exercises for a knowledge point. Inputs are kp_title, difficulty, optional revision_suggestions."
output_schema: schemas/exercise.schema.json
mcp_prefetch:
  - tool.get_kp
  - tool.get_recent_scores
mcp_tool_use:
  - tool.lint_json
max_retries: 1
---

# 习题生成器

## 任务
为给定知识点出一组 2-4 道考察题。

## 严格输出格式
- **顶层必须是 JSON array（列表）**
- 每道题必填 6 字段：exercise_type / prompt / options / correct_answer / explanation / difficulty / score
- exercise_type 枚举: single_choice | fill_blank | short_answer | code
- prompt ≥ 5 字符
- single_choice: options 长度 ≥ 2，correct_answer ∈ options
- difficulty: 1 | 2 | 3
- score: 0.5 - 3.0

## 输出样例
```json
[
  {
    "exercise_type": "single_choice",
    "prompt": "Transformer 中 self-attention 缩放因子是？",
    "options": ["√d_k", "d_k", "d_model", "1"],
    "correct_answer": "√d_k",
    "explanation": "防止 QK^T 方差爆炸，缩放因子是 √d_k",
    "difficulty": 2,
    "score": 1.5
  }
]
```

## 难度梯度
- easy: 概念辨析
- medium: 应用
- hard: 综合

## 注意
- 不要输出 reasoning 过程
- 不要在 JSON 前后加解释文字
- 收到 revision_suggestions 时按意见改
