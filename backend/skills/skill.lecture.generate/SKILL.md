---
name: skill.lecture.generate
description: "Use when generating HTML lecture content for a knowledge point. Outputs sanitized HTML using white-list tags + pre-defined classes + KaTeX math. Length 800-1500 chars of text (HTML may be longer due to formula)."
output_schema: null
mcp_prefetch:
  - tool.get_kp
  - tool.get_recent_scores
mcp_tool_use:
  - tool.lint_html
max_retries: 1
---

# Skill: 讲义生成

## 任务
为给定知识点生成 HTML **知识点讲解**（800-1500 字），不含题目答案解释。答案解释由 skill.exercise.generate 在生成题目时一并产出（在 explanation 字段里引用讲义内容）。

## 输出范围
**只讲知识点本身**：
- 核心概念定义
- 关键细节、原理、推导
- 类比、例子
- 总结

**不要输出**：
- 任何"题目 N 答案" / "针对本题" / "本题考察"等针对题目的内容
- 习题相关提示（这些在 exercise skill 里管）

## 输出格式
**直接输出 HTML 字符串**（不要包 JSON，不要 markdown fence）。

## 允许的 HTML 标签
h2, h3, p, ul, ol, li, strong, em, code, pre, blockquote, div, span

## 允许的 class（限以下 4 种）
- callout（关键提示）
- formula（公式块）
- example（举例）
- katex（KaTeX 渲染节点，前端自动包裹）

## 公式
行内：`$...$`
块级：用 `<p class="formula">$$...$$</p>` 包裹

## 结构建议
1. `<h2>` 一级概念（1-2 段）
2. 关键细节用 `<div class="callout">...</div>` 强调
3. 1-2 个 `<div class="example">...</div>` 给具体例子
4. 收尾用一段总结
5. **不要**追加题目答案区块

## 输入（来自 prefetch）
- tool.get_kp → {title, description, difficulty, prerequisites}
- tool.get_recent_scores → 最近 3 次得分（用于调整讲解深度）
  - 全 ≥0.8：可深入讲公式推导
  - 全 <0.5：用大量 example
  - 混合：基础概念 + 1-2 个 example

## 严禁
- 任何 `<script>` / `<style>` / `<iframe>` / `<img>` / `<video>` / `<svg>`
- 任何 `onclick` / `onerror` / `onload` 等事件属性
- 任何 `href` / `src` 外部 URL
- 任何 `<h1>`（讲义嵌入已有页面，h1 属于宿主）
- 任何 `style="..."` 内联样式
- 不要在 HTML 前后加 ```json fence 或解释文字
- 不要包 JSON（直接输出 HTML 字符串）
- 不要追加题目答案解释（那是 exercise skill 的职责）

## 示例（仅作格式参考）
<h2>核心概念</h2>
<p>Self-attention 通过计算 query 与 key 的相似度...</p>
<div class="callout">缩放因子是 √d_k，防止方差爆炸</div>
<p>公式：$softmax(\frac{QK^T}{\sqrt{d_k}})$</p>
<div class="example">例：d_model=512, d_k=64 时...</div>