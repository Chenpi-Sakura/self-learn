# 讲义 HTML（Lecture）— Design

**日期**：2026-07-16
**作者**：SelfLearn dev
**状态**：📐 Design（已澄清，待用户审）
**关联 backlog**：`docs/superpowers/backlog/2026-07-15-html-lecture.md`（已落地为本文档）
**前置依赖**：P5 Agent 架构（`docs/superpowers/reports/2026-07-15-agent-architecture.md`）已落地

---

## 一、目标

让 `levels` 表多一个 `lecture_html` 字段，Director 关卡生成链路多一次 LLM 调用产出一段白名单约束的 HTML 讲义（含 KaTeX 公式），前端 `LecturePane` 渲染该 HTML 替代当前的"显示第一道题 prompt"占位。

**文字模态范围**（本 spec 实现）：HTML 文本 + KaTeX 公式（行内 `$...$` + 块级 `$$...$$`）。
**图片模态**（**不属于本 spec**）：由用户在后续独立任务实现。

---

## 二、问题陈述

### 现状

`backend/src/selflearn/agents/director.py:67` 已经预留 `agent.run("skill.lecture.generate", env)` 调用，但 `backend/skills/skill.lecture.generate/SKILL.md` 是占位文件（`output_schema: null`，body 只写"本 Skill 是预留占位"），Director chain 实际跑时 LLM 收到一个空骨架 prompt，返回内容**不可控**。

前端 `frontend/src/panes/LecturePane.tsx:14` 是占位实现：

```tsx
const first = lv.exercises[0];
setContent(first ? `[${lv.exercises.length} 题] ${first.prompt}` : '关卡无题目');
```

只显示题数 + 第一题题干，没有任何"讲义"概念。

`backend/src/selflearn/mcp_server/tools/create_level.py:31` 已经接受 `lecture_html` 入参但用 `hasattr(Level, "lecture_html")` 防御性写入 —— 字段在 ORM 里**不存在**。

`backend/src/selflearn/domain/level.py` 没有 `lecture_html` 字段；`backend/src/selflearn/schemas/level.py` 的 `LevelDetailResponse` 也没该字段；数据库 `levels` 表也没该列。

### 问题

1. 学生在关卡里看不到讲解，题目做完也不知道为什么对/错
2. 当前 LecturePane 拿第一题题干当讲义用，信息密度为 0
3. P5 Director chain 已经预留了 lecture 调用点，但配套的 SKILL.md / ORM / schema / 前端渲染都没补上
4. KaTeX 公式是技术讲义的高频需求（自注意力 / 矩阵 / 微积分），没有任何方案支持

---

## 三、目标架构

### 3.1 数据流

```
Frontend                Gateway               Worker (Director chain)              DB (Postgres)
   │                       │                          │                                │
   │ POST /api/level/start │                          │                                │
   │ {student_id,node_id}  │                          │                                │
   ├──────────────────────>│                          │                                │
   │                       │ publish_envelope         │                                │
   │                       │ target=skill.director.start                              │
   │                       ├─────────────────────────>│                                │
   │                       │                          │                                │
   │                       │                          │ 1. get_active_node (env.payload.node_id 精确路由)
   │                       │                          ├──────────────────────────────>│
   │                       │                          │ 2. get_kp                      │
   │                       │                          ├──────────────────────────────>│
   │                       │                          │ 3. get_recent_scores           │
   │                       │                          ├──────────────────────────────>│
   │                       │                          │                                │
   │                       │                          │ 4. LLMAgent.run("skill.lecture.generate") ─> DeepSeek
   │                       │                          │ <─ lecture_html (raw string)
   │                       │                          │                                │
   │                       │                          │ 5. ReviewStage.review_lecture(html)
   │                       │                          │    verdict=rejected → AppError → 整链 retry
   │                       │                          │                                │
   │                       │                          │ 5.5 _extract_lecture_outline(html)
   │                       │                          │   → {sections, callouts, examples}
   │                       │                          │   注入到下一轮 exercise env.payload
   │                       │                          │                                │
   │                       │                          │ 6. LLMAgent.run("skill.exercise.generate")
   │                       │                          │    user_msg 含 lecture_outline  │
   │                       │                          │ ─> DeepSeek                    │
   │                       │                          │ <─ exercises JSON (每题 explanation 引用 lecture_outline)
   │                       │                          │ 7. review_exercise_biz (rev 0) + review_exercise_llm (rev 0/1)
   │                       │                          │                                │
   │                       │                          │ 8. tool.create_level(node_id, lecture_html)
   │                       │                          │    → 截断到 50000 → INSERT     │
   │                       │                          ├──────────────────────────────>│
   │                       │                          │ 9. tool.bulk_create_exercises  │
   │                       │                          ├──────────────────────────────>│
   │                       │                          │ 10. tool.update_profile        │
   │                       │                          ├──────────────────────────────>│
   │                       │                          │                                │
   │ <─ SSE COMPLETED    │ <─ SSE COMPLETED        │                                │
   │                       │                          │                                │
   │ GET /api/level/{id}   │                          │                                │
   ├──────────────────────>│ SELECT level WHERE ...  │                                │
   │ <─ {lecture_html,...} │ <─────────────────────┤                                │
```

**关键点**：Director chain 不改（已预留调用点），tool.create_level 已接受 lecture_html 入参（去掉 hasattr 防御 + 加截断），主要工作量在 schema/ORM/SKILL.md/前端渲染四个增量改动。

### 3.2 核心组件清单

| 组件 | 类型 | 状态 | 改动 |
|---|---|---|---|
| `Level.lecture_html` | ORM 字段 | 新增 | `String(50000), nullable=True` |
| Alembic migration | DB schema | 新增 | `op.add_column("levels", "lecture_html", String(50000))` |
| `LevelDetailResponse.lecture_html` | Pydantic schema | 新增 | `str \| None` |
| `tool.create_level` | MCP DB tool | 修改 | 截断 lecture_html 到 50000；去掉 hasattr 防御 |
| `tool.lint_html` | MCP utility | 不改 | 已实现 nh3 白名单清洗 |
| `skill.lecture.generate/SKILL.md` | Skill 声明 | 重写 | 知识点讲解 prompt（不含题目答案解释） |
| `_extract_lecture_outline` | Agent 工具函数 | 新增 | 从 lecture_html 提取 {sections, callouts, examples} 三类纲要注入 exercise env |
| `skill.exercise.generate/SKILL.md` | Skill 声明 | 修改 | prefetch 去掉 `tool.get_kp`；explanation 强制首句引用 lecture_outline |
| `Director chain` (`agents/director.py`) | 编排器 | 修改 | lecture 后跑 `_extract_lecture_outline`，结果注入 exercise env.payload |
| `ReviewStage.review_lecture` | Review stage | 不改 | 已实现 lint_html + not_empty |
| `Gateway GET /api/level/{id}` | API 路由 | 修改 | 返回 lecture_html 字段 |
| `LecturePane.tsx` | 前端组件 | 重写 | 渲染 lecture_html（dangerouslySetInnerHTML） |
| `lecture.css` | 前端样式 | 新增 | 米黄底 + 靛蓝标题 + 朱红强调 + 楷体 |
| `katex` | 前端依赖 | 新增 | code-splitting 懒加载 |

### 3.3 白名单约束

#### HTML 标签白名单（来自 `tool.lint_html`）

```
h1, h2, h3, p, ul, ol, li, strong, em, code, pre,
blockquote, table, thead, tbody, tr, th, td, br, hr, span, div
```

**讲义实际只用**：h2, h3, p, ul, ol, li, strong, em, code, pre, blockquote, div, span
（其它 9 个保留是因为 `tool.lint_html` 是公共 utility，可能其他场景需要）

#### class 白名单（讲义专用）

| class | 用途 | 样式 |
|---|---|---|
| `callout` | 关键提示 | 左侧 4px 朱红竖条 + 浅红底 |
| `formula` | 公式块 | 白底 + 1px border + 等宽字体 |
| `example` | 举例 | 浅米底 + 左侧 2px 靛蓝边 + 楷体 |
| `katex` / `katex-display` | KaTeX 渲染节点 | 由 KaTeX 自动包裹 |

#### 严禁元素

- `<script>` / `<style>` / `<iframe>` / `<img>` / `<video>` / `<svg>`
- `onclick` / `onerror` / `onload` 等事件属性
- 任何 `href` / `src` 外部 URL
- `<h1>`（讲义嵌入已有页面，h1 属于宿主页面）
- `style="..."` 内联样式
- 任何 font 标签

---

## 四、数据模型变更

### 4.1 Alembic migration

新文件：`backend/migrations/versions/<hash>_add_lecture_html.py`

```python
"""add lecture_html to levels

Revision ID: <hash>
Revises: f1963078e4e4  # stage4_profile_snapshots (当前 head)
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa

revision = "<hash>"
down_revision = "f1963078e4e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "levels",
        sa.Column("lecture_html", sa.String(50000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("levels", "lecture_html")
```

### 4.2 ORM 字段

`backend/src/selflearn/domain/level.py` 加：

```python
lecture_html: Mapped[str | None] = mapped_column(String(50000), nullable=True)
```

位置：放在 `form` 字段之后、`created_at` 之前。

### 4.3 Pydantic schema

`backend/src/selflearn/schemas/level.py` 的 `LevelDetailResponse` 加：

```python
lecture_html: str | None = None  # NULL 时前端显示"该关卡尚无讲义"
```

### 4.4 类型 / 长度选型理由

| 候选 | 上限 | 风险 |
|---|---|---|
| `String(20000)`（backlog 草案） | 2 万字符 | KaTeX 公式密集型讲义（5-10 个公式）容易截断 |
| **`String(50000)`**（本 spec） | 5 万字符 | 覆盖 99% 公式密集讲义；同时防 LLM 异常爆 DB（1 万关卡 ≈ 500MB） |
| `Text` | ~1GB | 灵活性最高但无防御（LLM 异常输出可能撑爆一行） |

**选 50000**。

---

## 五、后端实现

### 5.1 tool.create_level 截断逻辑

`backend/src/selflearn/mcp_server/tools/create_level.py`：

```python
"""tool.create_level: 写一个 Level 行（绑定 MapNode）。"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from selflearn.core.logging import get_logger
from selflearn.domain.level import Level
from selflearn.infra.db import get_session_factory

log = get_logger("create_level")

MAX_LECTURE_HTML_LEN = 50000


async def create_level(
    node_id: str,
    lecture_html: str | None = None,
) -> dict[str, Any]:
    """给一个 MapNode 创建 Level 行。

    lecture_html 是讲义 HTML（nh3 白名单清洗后）。
    若超过 MAX_LECTURE_HTML_LEN，截断并 log warn（prompt 已有 800-1500 字约束，截断是兜底）。

    Returns: {"ok": True, "level_id": "..."} 或
             {"ok": False, "error": "invalid_uuid:<node_id>"}
    """
    try:
        node_uuid = UUID(node_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{node_id}"}

    factory = get_session_factory()
    async with factory() as session:
        truncated_html: str | None = None
        if lecture_html is not None:
            if len(lecture_html) > MAX_LECTURE_HTML_LEN:
                log.warning(
                    "create_level.lecture_html_truncated",
                    orig_len=len(lecture_html),
                    max_len=MAX_LECTURE_HTML_LEN,
                )
                truncated_html = lecture_html[:MAX_LECTURE_HTML_LEN]
            else:
                truncated_html = lecture_html

        level = Level(
            node_id=node_uuid,
            status="generated",
            form="exercise",
            lecture_html=truncated_html,
        )
        session.add(level)
        await session.commit()
        await session.refresh(level)
        return {"ok": True, "level_id": str(level.level_id)}
```

### 5.2 skill.lecture.generate SKILL.md 重写

`backend/skills/skill.lecture.generate/SKILL.md` 从占位改为真实 prompt 模板：

```yaml
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
```

### 5.3 Director chain 的 lecture_outline 提取与传递

Director chain 在 lecture 跑完后、exercise 跑前，把 `lecture_html` 提取为 `lecture_outline`（结构化纲要）注入到 exercise 的 env.payload：

```python
# backend/src/selflearn/agents/director.py  (新增步骤 4.5)
# 4. lecture 生成
lecture_html = await agent.run("skill.lecture.generate", env)

# 4.5 提取讲义纲要，注入到 exercise env（让 exercise 的 explanation 引用讲义内容）
lecture_outline = _extract_lecture_outline(lecture_html)

# 5. lecture 业务规则（lint_html + not_empty）
review_lec = await review.review_lecture(lecture_html)
if review_lec.verdict == "rejected":
    raise AppError(...)

# 6. exercise 0-2 轮
for revision in range(2):
    env_ex = Envelope(
        ...
        payload={
            **env.payload,
            "node_id": node["node_id"],
            "kp_title": kp["title"],
            "difficulty": difficulty,
            "revision_suggestions": suggestions,
            "lecture_outline": lecture_outline,   # ★ 新增：让 exercise LLM 写 explanation 时引用讲义
        },
        ...
    )
    ...
```

新工具函数 `_extract_lecture_outline`（放在 `backend/src/selflearn/agents/director.py` 或独立 `backend/src/selflearn/agents/lecture_outline.py`）：

```python
"""lecture_outline: 从 lecture_html 提取结构化纲要供 exercise LLM 引用。"""
from __future__ import annotations

import re

_OUTLINE_RE_SECTION = re.compile(r"<h[23][^>]*>(.*?)</h[23]>", re.DOTALL)
_OUTLINE_RE_CALLOUT = re.compile(r'<div class="callout"[^>]*>(.*?)</div>', re.DOTALL)
_OUTLINE_RE_EXAMPLE = re.compile(r'<div class="example"[^>]*>(.*?)</div>', re.DOTALL)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


def _strip_tags(html_fragment: str) -> str:
    """去掉 HTML 标签 + 收尾空白。"""
    return _TAG_STRIP_RE.sub("", html_fragment).strip()


def extract_lecture_outline(lecture_html: str) -> dict[str, list[str]]:
    """从 lecture_html 提取结构化纲要，供 exercise LLM 在 explanation 里引用。

    Returns:
        {
            "sections": ["核心概念：self-attention", ...],  # h2/h3 标题
            "callouts": ["缩放因子是 √d_k...", ...],       # callout 块文本
            "examples": ["d_model=512 时...", ...],         # example 块文本
        }
    """
    return {
        "sections": [_strip_tags(m) for m in _OUTLINE_RE_SECTION.findall(lecture_html)],
        "callouts": [_strip_tags(m) for m in _OUTLINE_RE_CALLOUT.findall(lecture_html)],
        "examples": [_strip_tags(m) for m in _OUTLINE_RE_EXAMPLE.findall(lecture_html)],
    }
```

**为什么不直接传 lecture_html 给 exercise LLM**：HTML 含大量标签字符，挤占 LLM 上下文且增加 token 成本；结构化纲要（标题 + 关键块文本）能让 LLM 更精准地引用讲义。

**为什么不让 LLM 自己解析 lecture_html**：可控性差（LLM 看到完整 HTML 容易分心去"重写讲义"），显式纲要约束 LLM 只用纲要引用。

### 5.4 skill.exercise.generate SKILL.md 改动

`backend/skills/skill.exercise.generate/SKILL.md` 在现有版本基础上加 lecture_outline 引用要求 + 调整 prefetch：

```yaml
---
name: skill.exercise.generate
description: "Use when generating a batch of 2-4 exercises for a knowledge point. Inputs are kp_title, difficulty, lecture_outline (讲义纲要，用于 explanation 引用), optional revision_suggestions."
output_schema: schemas/exercise.schema.json
mcp_prefetch:
  - tool.get_recent_scores            # 改：去掉 tool.get_kp（lecture 已用过）
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
2. 解释为什么正确答案是这个（不是机械重复题干）
3. 简要指出其他选项错在哪（如果是 single_choice）

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
```

### 5.5 ReviewStage.review_lecture（已实现，确认逻辑）

`backend/src/selflearn/agents/review_stage.py:32-45` 的现有实现：

```python
async def review_lecture(self, lecture_html: str) -> ReviewResult:
    issues: list[dict[str, Any]] = []
    if not lecture_html:
        return ReviewResult(
            verdict="rejected", score=0.0,
            issues=[{"rule": "not_empty", "severity": "high", "message": "lecture_html 为空"}],
        )
    lint = await self.mcp.call("tool.lint_html", html=lecture_html)
    if lint.get("is_empty"):
        issues.append({"rule": "not_empty", "severity": "high", "message": "lecture_html 清洗后为空"})
    if any(i["severity"] == "high" for i in issues):
        return ReviewResult(verdict="rejected", score=0.0, issues=issues)
    return ReviewResult(verdict="passed", score=1.0, issues=[])
```

**不变** —— 已实现 lint_html + not_empty，符合本 spec 的 review 要求。

### 5.6 Gateway GET /api/level/{level_id}

`backend/src/selflearn/gateway/routes/level.py:179-205` 的现有 `get_level` 加一行：

```python
return LevelDetailResponse(
    level_id=level.level_id,
    node_id=level.node_id,
    status=level.status,
    lecture_html=level.lecture_html,  # 新增
    exercises=[...],
)
```

---

## 六、前端实现

### 6.1 types.ts 加字段

`frontend/src/api/types.ts` 的 `LevelDetail` 加：

```typescript
export interface LevelDetail {
  level_id: string;
  node_id: string;
  status: string;
  exercises: ExerciseResponse[];
  lecture_html: string | null;  // 新增：NULL 时显示"该关卡尚无讲义"
}
```

### 6.2 LecturePane 重写

`frontend/src/panes/LecturePane.tsx`：

```tsx
import { useEffect, useState } from 'react';
import { getLevel } from '../api/level';

export function LecturePane({ levelId }: { levelId: string }) {
  const [state, setState] = useState<
    | { loaded: false }
    | { loaded: true; html: string | null }
  >({ loaded: false });

  useEffect(() => {
    if (!levelId) return;
    getLevel(levelId)
      .then((lv) => setState({ loaded: true, html: lv.lecture_html ?? null }))
      .catch(() => setState({ loaded: true, html: null }));
  }, [levelId]);

  // 加载中
  if (!state.loaded) {
    return <div style={{ padding: 16, height: '100%', overflow: 'auto' }}>加载讲义...</div>;
  }

  // 没讲义（旧关卡 / 生成失败）
  if (!state.html) {
    return (
      <div
        style={{
          padding: 16,
          color: '#6B6B70',
          fontFamily: 'HedvigLettersSerif, serif',
        }}
      >
        该关卡尚无讲义，请重新启动关卡
      </div>
    );
  }

  // 渲染讲义（依赖后端 nh3 白名单清洗，不在前端二次清洗）
  return (
    <div
      className="lecture"
      style={{
        padding: 16,
        height: '100%',
        overflow: 'auto',
        fontFamily: 'HedvigLettersSerif, serif',
      }}
      dangerouslySetInnerHTML={{ __html: state.html }}
    />
  );
}
```

### 6.3 KaTeX 懒加载

**为什么不放主 bundle**：KaTeX ~280KB CSS + ~200KB JS，所有页面加载会浪费。LecturePane 不是首屏必需元素，懒加载合理。

实现方式（在 `LecturePane.tsx` 加 `useEffect`）：

```tsx
useEffect(() => {
  if (!state.loaded || !state.html) return;
  // KaTeX 已在 npm 依赖里；动态 import 让它独立 chunk
  Promise.all([
    import('katex/dist/katex.min.css'),
    import('katex'),
    import('katex/dist/contrib/auto-render.min.js'),
  ]).then(([, katex, autoRenderMod]) => {
    const autoRender = (autoRenderMod as any).default;
    const root = document.querySelector('.lecture') as HTMLElement | null;
    if (root) {
      autoRender.render(root, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
        ],
        throwOnError: false,
      });
    }
  });
}, [state.loaded, state.html]);
```

### 6.4 lecture.css 样式

新文件 `frontend/src/styles/lecture.css`：

```css
/* 讲义样式（UKIYO × Notion 主题） */
.lecture {
  background: #FBF7EC;        /* 米黄底（比 --paper 略深） */
  font-family: HedvigLettersSerif, "STKaiti", "KaiTi", serif;
  color: #1A1A1A;
  line-height: 1.7;
}
.lecture h2 {
  color: #1B3B6F;             /* 靛蓝（= --indigo） */
  font-family: "STSong", "SimSun", "Times New Roman", serif;
  border-bottom: 1px solid rgba(27, 59, 111, 0.15);
  padding-bottom: 4px;
  margin-top: 24px;
}
.lecture h3 {
  color: #1B3B6F;
  font-family: "STSong", "SimSun", "Times New Roman", serif;
  margin-top: 16px;
}
.lecture p {
  margin: 12px 0;
}
.lecture ul, .lecture ol {
  padding-left: 24px;
}
.lecture code {
  font-family: "SF Mono", Consolas, monospace;
  background: rgba(27, 59, 111, 0.05);
  padding: 1px 4px;
  border-radius: 2px;
}
.lecture pre {
  background: #FFF;
  border: 1px solid rgba(27, 59, 111, 0.15);
  padding: 8px 12px;
  overflow-x: auto;
}
.lecture .callout {
  border-left: 4px solid #BC4749;  /* 朱红（= --vermilion） */
  background: rgba(188, 71, 73, 0.06);
  padding: 8px 12px;
  margin: 12px 0;
  border-radius: 0 4px 4px 0;
}
.lecture .formula {
  background: #FFF;
  border: 1px solid rgba(27, 59, 111, 0.15);
  padding: 12px;
  margin: 12px 0;
  font-family: "SF Mono", Consolas, monospace;
  text-align: center;
  overflow-x: auto;
}
.lecture .example {
  background: rgba(27, 59, 111, 0.04);
  border-left: 2px solid rgba(27, 59, 111, 0.3);
  padding: 8px 12px;
  margin: 12px 0;
  font-family: "STKaiti", "KaiTi", serif;
}
.lecture blockquote {
  border-left: 3px solid rgba(27, 59, 111, 0.3);
  margin: 12px 0;
  padding-left: 12px;
  color: #6B6B70;
  font-style: italic;
}
```

引入到 `LecturePane.tsx` 顶部：

```tsx
import '../styles/lecture.css';
```

### 6.5 新增依赖

`frontend/package.json` 加：

```json
"dependencies": {
  "katex": "^0.16.11",
  ...
}
```

---

## 七、错误处理矩阵

| 错误 | 表现 | 处理 |
|---|---|---|
| LLM 返回空字符串 | `lecture_html=""` | `review_lecture` 返回 rejected → Director 抛 `lecture_rejected` → 整链 retry（max_attempts=3） |
| LLM 返回纯文本无 HTML | `lint_html` 清洗后可能为空 | `is_empty=True` → rejected → 整链 retry |
| LLM 返回含 `<script>` | `lint_html` 剥掉 → 清洗后变短 | 不直接 reject，看 `not_empty` 是否过；纯 script 时清洗后空 → reject |
| LLM 返回超 50000 字符 | `tool.create_level` 截断 + log warn | **不 reject**，写库照常（prompt 主约束，截断兜底） |
| DB migration 失败 | 启动时 alembic 报错 | worker fail-fast（与现状一致） |
| `tool.create_level` DB 写失败 | 返回 `{ok:false}` | Director 抛 `db_write_failed` → 整链 retry（依赖 level/start 路由幂等性复用 in-flight） |
| 旧关卡 `lecture_html=NULL` | `get_level` 返回 `lecture_html=null` | 前端显示"该关卡尚无讲义，请重新启动关卡" |
| 讲义 LLM 超时 | DeepSeek API 超时 | LLMAgent retry（max_retries=1）+ Director 整链 retry（max_attempts=3） |
| KaTeX 懒加载失败 | 公式显示为 `$...$` 字面 | 显示降级，KaTeX 不阻断页面 |
| 前端 lecture_html 含 KaTeX 但 KaTeX 未加载完 | 公式显示字面 | KaTeX 加载完（毫秒级）后渲染 |

---

## 八、兼容性承诺

| 旧行为 | 新行为 |
|---|---|
| LecturePane 显示 `[N 题] <第一题 prompt>` | 渲染 `lecture_html`；NULL 时显示"该关卡尚无讲义" |
| 旧关卡 `lecture_html=NULL` | 兼容：前端显示占位提示 |
| `LevelDetailResponse` 字段不变 | 新增 `lecture_html: str \| None`，向下兼容（旧调用方忽略新字段） |
| `tool.create_level` 已接受 lecture_html 但 `hasattr` 防御 | 新行为：真写入，去掉防御 + 加截断 |
| Director chain 已预留 lecture 调用 | **改**：lecture 后跑 `_extract_lecture_outline` → 注入到 exercise env.payload；exercise LLM 拿到 lecture_outline 后写 explanation 引用讲义内容 |
| `tool.lint_html` 已实现白名单清洗 | 不改 |
| `ReviewStage.review_lecture` 已实现 lint + not_empty | 不改 |
| 无新增后端依赖（mcp / nh3 已存在） | 无 |
| 新增前端依赖 `katex` | code-splitting 懒加载（不污染主 bundle） |
| 无 alembic 自动迁移 | 新增一个 migration；运行命令 `cd backend && alembic upgrade head`（dev） / `docker compose run --rm backend alembic upgrade head`（容器） |
| `skill.exercise.generate/SKILL.md` 旧 mcp_prefetch 含 `tool.get_kp` | 去掉（lecture 阶段已用过，避免重复）；新增 `lecture_outline`（来自 env.payload 而非 prefetch）；explanation 必填 ≥30 字 + 首句引用 lecture_outline |

---

## 九、测试策略

### 9.1 单元测试（新增 ~8 个）

| 文件 | 测试 |
|---|---|
| `tests/unit/test_create_level.py` | lecture_html 入参正常；lecture_html 超过 50000 截断；lecture_html=None 不写列 |
| `tests/unit/test_review_stage.py` | review_lecture 接受合法 HTML 返回 passed；空字符串返回 rejected；lint_html 后空字符串返回 rejected |
| `tests/unit/mcp/test_lint_html.py` | 已有（如缺则补）：`<script>` 剥除；`onclick` 剥除；不允许 class 剥除 |
| `tests/unit/test_lecture_outline.py`（新文件）| `_extract_lecture_outline` 抽 h2/h3、callout、example；HTML 标签剥除；空 lecture_html 返回空字典；嵌套标签正确处理 |

### 9.2 集成测试（新增 1-2 个）

`tests/integration/test_director_e2e.py`：
- mock LLM 两次（lecture + exercise），验证 director chain 跑完
- 验证 `level.lecture_html` 写入 DB（非空）
- 验证 `tool.create_level` 截断逻辑
- 验证 exercise LLM 收到的 env.payload 里有 `lecture_outline` 字段（含 sections/callouts/examples）

`tests/unit/test_exercise_skill_outline.py`（新文件）：
- 验证 exercise LLM mock 收到的 user_msg 含 lecture_outline JSON 块
- 验证 mock 返回的 exercise 的 explanation 字段长度 ≥ 30 字

### 9.3 端到端验收

- `pytest tests/` 全 PASS（旧 151 + 新增 ~9-10 = 约 160-161）
- `mypy src/selflearn` clean
- `bash scripts/smoke_mvp.sh` 8/8 PASS（兼容性验证）
- 浏览器实测 3 个不同节点 → LecturePane 渲染讲义（公式正常）+ ExercisePane 做题看 explanation 能直接串回讲义内容
- 容器内 spot-check：取一个 level.exercise.explanation，验证首句包含 lecture_outline 中某个 callout / section 文本片段

### 9.4 前端验证（手工 + e2e）

- Playwright `e2e/smoke.spec.ts` 3/3 PASS（兼容性）
- 手工：打开 TreasureMap，点 3 个节点，看 LecturePane 是否渲染讲义（含公式的 LaTeX → KaTeX）

---

## 十、风险与缓解

| 风险 | 缓解 |
|---|---|
| LLM 输出 HTML 不稳定 | 白名单清洗（已实现） + 长度截断（新增） |
| KaTeX 包体积 ~480KB | code-splitting 懒加载（仅 LecturePane 挂载时 import） |
| KaTeX 大公式渲染慢 | `auto-render` 默认支持 inline / display；不阻断页面 |
| `lecture_html=NULL` 的旧关卡 | 前端显示"该关卡尚无讲义"，引导用户重启 |
| LLM 输出公式格式错误（缺 `$`） | KaTeX `throwOnError: false`，降级显示原文不报错 |
| Director chain 失败重试消耗 LLM 配额 | 已有 max_attempts=3 兜底；超过则关卡创建失败 |
| 历史关卡 lecture_html=NULL | 不主动迁移（明示范围外） |

---

## 十一、范围外（明确不做）

- ❌ 图片 / 视频 / iframe（v1）—— **图片模态由用户后续独立实现**
- ❌ 代码执行沙箱
- ❌ 讲义编辑 / 版本管理
- ❌ 历史关卡补讲义（NULL 占位即可）
- ❌ DOMPurify 前端二次清洗（依赖后端 nh3 已足够）
- ❌ 讲义 LLM 二次审查（仅 lint_html + not_empty）
- ❌ 重做 ReviewAgent / Director chain
- ❌ 实时预览讲义（仅静态渲染）
- ❌ 讲义导出（PDF / Markdown）
- ❌ KaTeX pre-render（前端 client-side render 即可）

---

## 十二、实施顺序

| Phase | 内容 | 验证 | 预估 |
|---|---|---|---|
| **P1. 数据层** | migration + ORM 字段 + schema 字段 + tool.create_level 截断 + 单测 | alembic upgrade head 在容器跑通；get_level 返回 lecture_html（NULL）；create_level 截断单测 | 0.5 天 |
| **P2. SKILL + Director chain 联调** | 重写 lecture SKILL.md（纯讲解） + 改 exercise SKILL.md（引用 outline） + 新增 `_extract_lecture_outline` + Director chain 注入 outline + 容器内 LLM 真实调用 | worker 跑一次 /start，DB 里 lecture_html 非空；exercise.explanation 显式引用 lecture_outline；review_lecture verdict=passed | 0.5 天 |
| **P3. 前端渲染** | types + LecturePane + lecture.css + KaTeX 懒加载 | 浏览器打开关卡，lecture pane 显示讲义（公式正常） | 0.5 天 |
| **P4. 回归** | pytest 全套 + 端到端 smoke + 3 节点实测（含 outline 引用检查） | pytest 全 PASS；用户验收 | 0.5 天 |

**总预估**：2 天（1 个完整工作日 + 1 个回归日）。

---

## 十三、决策记录

| # | 决策 | 选择 | 理由 |
|---|---|---|---|
| 1 | Agent 调用形态 | LLMAgent + skill.lecture.generate（与 exercise 统一） | P5 架构已预留调用点，统一架构降低复杂度 |
| 2 | 存储格式 | DB 存 HTML（`level.lecture_html`） | 简单；前端只渲染，不解析 |
| 3 | 字段类型 | String(50000) | 给 KaTeX 公式密集讲义留余地；防止 LLM 异常爆 DB |
| 4 | HTML 约束 | 白名单标签（tool.lint_html 已实现）+ 4 个预定义 class | 后端 nh3.clean 防御 XSS；class 限定样式语义 |
| 5 | 公式渲染 | KaTeX（前端懒加载） | 技术讲义高频需求；code-splitting 控包体积 |
| 6 | 长度处理 | prompt 约束 800-1500 字 + 后端硬截断 50000 兜底 | 主约束在前端 prompt；截断是兜底不阻断 |
| 7 | 旧关卡兼容 | NULL 占位 + "该关卡尚无讲义" | 不主动迁移（明示范围外） |
| 8 | 视觉风格 | 复用 design tokens：靛蓝/朱红/米黄 + 楷体 | 与全局 UKIYO × Notion 主题一致 |
| 9 | 失败策略 | 整链 retry（max_attempts=3），失败则关卡创建失败 | 用户开不到关卡是明显信号，便于调试 |
| 10 | Review 处理 | 仅 lint_html + not_empty，不调 LLM | 讲义质量天花板在生成阶段；审查增成本不增收益 |
| 11 | 前端 XSS 防御 | 不做（依赖后端 nh3） | 项目无登录无鉴权，损失有限；简化前端代码 |
| 12 | KaTeX 加载 | code-splitting 懒加载（Promise.all + dynamic import） | LecturePane 非首屏必需；懒加载控包体积 |
| 13 | 实施顺序 | P1 数据层 → P2 后端 + P3 前端（并行） → P4 回归 | 数据层决定 schema；前后端并行加速 |
| 14 | 模态范围 | **文字模态**（HTML + KaTeX）我做；**图片模态**由用户后续独立实现 | 用户分工 |
| 15 | 讲义与答案解释分工 | **讲义 = 纯知识点讲解**（不含题目答案）；**答案解释 = exercise LLM 在 explanation 字段显式引用讲义纲要** | 用户反馈：讲义应超越单次题目，做到"学完能懂"。两道 LLM 调用分工明确：lecture 教概念，exercise 让学生通过题目答案串回讲义 |
| 16 | 讲义-答案解释对齐方式 | 提取 `_extract_lecture_outline(html)` → `{sections, callouts, examples}` 三类结构化纲要 → 注入 exercise env.payload → exercise LLM 写 explanation 时显式引用纲要条目 | 不直接传 lecture_html（标签噪音挤占 LLM 上下文）；不让 LLM 自己解析 HTML（可控性差）。显式纲要约束 LLM 只用纲要引用 |
| 17 | exercise SKILL.md 必填字段调整 | 新增 **explanation ≥ 30 字符** + **首句引用 lecture_outline** 强制要求 | 防 LLM 输出"对，就是这个"空洞答案；保证学生看完 explanation 能直接串回讲义 |

---

## 十四、关联文档

- `docs/superpowers/backlog/2026-07-15-html-lecture.md`（原始 backlog）
- `docs/superpowers/specs/2026-07-15-agent-architecture-design.md`（P5 架构，Director chain 已预留 lecture 调用）
- `docs/superpowers/reports/2026-07-15-agent-architecture.md`（P5 落地报告）
- `backend/src/selflearn/mcp_server/tools/lint_html.py`（白名单清洗已实现）
- `backend/src/selflearn/agents/director.py:67`（Director chain 已预留 lecture 调用）

---

**审稿人请检查**：

1. § 3 数据流是否清晰？
2. § 4 数据模型变更（migration + ORM + schema）是否完整？
3. § 5 后端实现（截断 + SKILL.md + ReviewStage 复用）是否合理？
4. § 6 前端实现（LecturePane 重写 + KaTeX 懒加载 + lecture.css）是否完整？
5. § 8 兼容性承诺是否覆盖了所有旧行为？
6. § 9 测试策略是否足够？
7. § 12 实施顺序 4 个 phase 是否合理？
8. § 13 决策记录 14 条是否需要补充？

**审完后回复**："批准" / "修改 X" / "重做 Y"。