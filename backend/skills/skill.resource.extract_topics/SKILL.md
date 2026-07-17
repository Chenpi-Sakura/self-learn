---
name: skill.resource.extract_topics
description: "Use when extracting topics (KP draft) from a student's uploaded .md learning materials. Input is a list of resources, output is a topics JSON. Each topic contains excerpt_text sourced from the input materials for later lecture/exercise skill injection."
output_schema: schemas/extract_topics.schema.json
mcp_prefetch: []
mcp_tool_use:
  - tool.lint_json
max_retries: 1
---

# 主题提炼器

## 任务
你是教学设计师。下面是学生上传的多份 .md 学习资料。
任务：
  1. 通读所有资料，识别 N 个（3-8 个）**不重叠、互相有逻辑关联**的主题
  2. 每个主题对应一个"知识节点"，给学生后续学习
  3. 对每个主题，从原始资料中挑出**最相关的 500-1500 字片段**，作为后续关卡生成的"提供的材料知识"
  4. 主题之间尽量体现先修关系（prerequisites），但不强求

## 输入（env.payload）
```json
{
  "resources": [
    {"id": "uuid", "name": "Transformer 详解.md", "content_md": "..."}
  ]
}
```

## 严格输出 JSON（不要 markdown fence，不要其它任何内容）
{
  "topics": [
    {
      "title": "主题名（≤30 字）",
      "description": "一段话描述（≤150 字）",
      "prerequisites": ["本次输出的其它主题 title，不在本数组内的被丢弃"],
      "excerpt_text": "原资料中 500-1500 字摘录，必须能从某份 input.resources.content_md 中找到（按字符串包含）",
      "source_resource_id": "上面 input.resources 中某个资源 id"
    }
  ]
}

约束：
- topics 长度 3-8
- 每条 excerpt_text 必须是某一 input.resources.content_md 的连续子字符串（防止幻觉）
- source_resource_id 必须在 input.resources 出现过
