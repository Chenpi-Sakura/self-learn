---
name: skill.exercise.generate
description: "Use when generating a batch of 2-4 exercises for a knowledge point. Inputs are kp_title, difficulty, lecture_outline (讲义纲要，用于 explanation 引用), optional revision_suggestions."
output_schema: schemas/exercise.schema.json
mcp_prefetch:
  - tool.get_recent_scores
  # lecture_outline 不通过 prefetch 走 —— 它在 env.payload 里（director.py 注入）
mcp_tool_use:
  - tool.lint_json
max_retries: 1
---

# 习题生成器

## 任务
为给定知识点出一组 2-4 道考察题。**每道题的 explanation 字段必须显式引用 lecture_outline 中的内容**（让讲义与答案解释互为补充，学生做完题看 explanation 时能直接串回讲义）。

## 输入（来自 prefetch + env.payload）
- tool.get_recent_scores → 最近 3 次得分
- tool.get_kp → {title, description, difficulty, prerequisites, source, source_content_md}
  - **source_content_md**（可选）：蒸馏切片，如有，**explanation 必须显式引用其中片段**，引用方式："如讲义『XXX』中所言：..."，或在首句标注"参考自 XXX.md"。
  - **source**（可选）：来源 md 文件名。
- env.payload.lecture_outline → 讲义结构化纲要：
  ```json
  {
    "sections": ["核心概念：self-attention", "..."],
    "callouts": ["缩放因子是 √d_k，防止方差爆炸"],
    "examples": ["d_model=512, d_k=64 时..."]
  }
  ```
- env.payload.kp_title → 知识点标题
- env.payload.difficulty → easy / medium / hard
- env.payload.revision_suggestions → 第二轮 review LLM 给的修改意见（仅 revision 1 时存在）

## explanation 字段强制要求
每道题的 explanation 必须：
1. **首句引用 lecture_outline 中的某个 section / callout / example**（用"如讲义『XXX』所言：..." 或 "讲义中提到：..." 等显式引用形式）
2. **如 `tool.get_kp.source_content_md` 非空，必须从其中挑一句作为引子**（"如材料『XXX.md』中提到：..."），让题目锚定到蒸馏切片
3. 解释为什么正确答案是这个（不是机械重复题干）
4. 简要指出其他选项错在哪（如果是 single_choice）

## 示例
```json
[
  {
    "exercise_type": "single_choice",
    "prompt": "Transformer 中 self-attention 缩放因子是？",
    "options": ["√d_k", "d_k", "d_model", "1"],
    "correct_answer": "√d_k",
    "explanation": "如讲义『关键细节』中所言：缩放因子是 √d_k，目的是防止 QK^T 方差爆炸。其他选项错在：d_k 是未缩放的，会导致 softmax 进入饱和区；d_model 是模型维度，跟缩放无关；1 是无缩放，效果等同于 d_k。",
    "difficulty": 2,
    "score": 1.5
  }
]
```

## 严格输出格式
- **顶层必须是 JSON array（列表）**
- 每道题必填 7 字段：exercise_type / prompt / options / correct_answer / explanation / difficulty / score
- exercise_type 枚举: single_choice | fill_blank | short_answer | code
- prompt ≥ 5 字符
- single_choice: options 长度 ≥ 2，correct_answer ∈ options
- difficulty: 1 | 2 | 3
- score: 0.5 - 3.0
- **explanation ≥ 30 字符**（避免 LLM 输出 "对，就是这个" 这种空洞答案）

## 难度梯度
- easy: 概念辨析
- medium: 应用
- hard: 综合

## 注意
- 不要输出 reasoning 过程
- 不要在 JSON 前后加解释文字
- 收到 revision_suggestions 时按意见改
