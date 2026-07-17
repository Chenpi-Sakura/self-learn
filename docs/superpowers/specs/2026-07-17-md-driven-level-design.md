# 用户上传 md 驱动地图与关卡生成子系统

**日期**：2026-07-17
**状态**：spec 已批准（用户拍板 6 段）；待 writing-plans → SDD
**适配**：SelfLearn 现有 FastAPI + React + SQLAlchemy 2.0 + asyncio + Redis Stream 架构

---

## 1. 背景与目标

### 1.1 现有系统的关键缺口（已确认）

- 地图主题**完全 hard-coded**：seed_map.py 写死 5 个 KP（`subject="大语言模型"`），所有 student 看到同一张图
- `MapNode.kp_id → knowledge_points.{subject, title, description}` 是主题的**唯一来源**——profile 完全不参与主题选择
- 关卡生成为 KP 维度的"硬讲解"，无法融合学生私域材料

### 1.2 要达成的目标

1. 用户上传 1-4 份 .md 文件 → **提炼主题**（extract_topics）→ 生成新的 KP 列表 → 学生地图出现新节点
2. 地图可**重新生成**——根据新一轮选取的资料重做
3. 关卡生成时 LLM 拿到该 KP 的"提供的材料知识"，讲义/习题围绕它写
4. UI 上 5 阶段进度条**真实**反映后端阶段（不靠 setTimeout 假推进）
5. 冷启动 app 默认无窗口，必须先上传资料才能进入学习流

### 1.3 关键术语

| 词 | 含义 |
|----|------|
| **提炼主题**（extract_topics）/ "蒸馏" | 让 LLM 读用户 md 全文，吐出结构化 topics JSON（KP 草稿） |
| KP（KnowledgePoint） | 跨 student 共享字典表里的主题词条 |
| MapNode | student 私有主题实例（FK → KP），地图上画的就是它 |
| source_content_md | KP 字段，蒸馏时 LLM 抽取的"该 KP 最相关的 500-1500 字切片"，供后续讲义生成用 |

---

## 2. 数据模型

### 2.1 新表 `resources`（Task 1 引入）

```sql
CREATE TABLE resources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,                     -- 含 '/' 虚拟前缀（"深度学习/transformer/注意力.md"）
  content_md TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_resources_student_active
  ON resources(student_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_resources_student_name
  ON resources(student_id, name);
```

已拍板决定（A-E 用户答复）：
- **A：orphan KP 清理**：`DELETE FROM knowledge_points WHERE NOT EXISTS (SELECT 1 FROM map_nodes WHERE map_nodes.kp_id = knowledge_points.kp_id) AND source IS NOT NULL`
- **B：KP 字段类型**：`source VARCHAR(500) NULL`，`source_content_md TEXT NULL`
- **C：不加 `content_hash` 字段**
- **D：不加 `name` UNIQUE 约束**（允许同名）
- **E：软删除**（`deleted_at`，与其他表一致）

### 2.2 `knowledge_points` 加两列

```sql
ALTER TABLE knowledge_points
  ADD COLUMN source TEXT,                  -- "Transformer 详解.md"，可空
  ADD COLUMN source_content_md TEXT;       -- 该 KP 引用的 md 切片（≤1500 字）
```

KP 是跨 student 共享字典表；这两字段**只对**"由用户 md 蒸馏出来的 KP"有意义。seed_map.py 写死的老 KP 保持 NULL。

### 2.3 不新增的表 / 字段

| 不加 | 理由 |
|------|------|
| `kp_materials` 关联表 | 一个 KP 只对应一份 md 切片，1↔1 足够 |
| `task_progress` 持久化表 | SSE 走 Redis Stream，自动 TTL 清理 |
| `resources.parent_id` | 虚拟前缀模型不需要 |
| `resources.is_folder` | 同上 |
| `resources.content_hash` | 用户拍板不加 |
| `resources.name` UNIQUE | 用户拍板不加 |

### 2.4 FK 级联链确认（重生成整删安全）

```
map_nodes  --ondelete=CASCADE-->  levels  --ondelete=CASCADE-->  exercises
                                              └─ondelete=CASCADE-->  level_completions
map_nodes  --(no action)-->  knowledge_points      ← KP 是共享字典表，不级联
```

执行 `delete(map_nodes).where(student_id = X)` 时数据库层会清掉该 student 的 Level、Exercise、LevelCompletion，**KP 不动**——这是重生成安全的关键不变量。

---

## 3. 后端 API

### 3.1 资源 CRUD（Task 1）

| Method | Path | 用途 | 校验 |
|--------|------|------|------|
| POST | `/api/resources/upload` | multipart 上传 ≤4 个 .md | 单文件 ≤10MB、扩展名 `.md`、非 .md 拒绝 → 400 |
| GET | `/api/resources/list` | 列出该 student 未软删资源 | — |
| GET | `/api/resources/{id}` | 单 md 全文 | 软删的 404 |
| PUT | `/api/resources/{id}` | 改名/移动 | 校验非循环（`a/x.md` 不能改名为 `a/x/y.md`）、同名冲突 → 409 |
| DELETE | `/api/resources/{id}` | 软删 | 204 |

### 3.2 提炼主题触发（Task 2）

| Method | Path | 用途 |
|--------|------|------|
| POST | `/api/resources/extract_topics` | 触发提炼主题任务 |
| GET | `/api/resources/extract_topics/stream?task_id=...` | SSE 订阅进度 |

Body：
```json
{ "selected_resource_ids": ["uuid", ...] }
```

响应：`{ "task_id": "<uuid>" }`

POST 立即返回 task_id；后台异步在 FastAPI lifespan-managed task 里跑（用 `asyncio.create_task`，**不**走 RabbitMQ envelope；如未来要并行 worker 再改 MQ）。

### 3.3 后端提取主题 5 阶段

| 阶段 | stage 枚举值 | 干的事 | 典型耗时 | 失败模式 |
|------|------------|---------|---------|---------|
| 1. parse | `extract_topics.parse` | `SELECT resources WHERE id IN (...)`；拼成单字符串 | <100ms | DB 不可达 / 资源被软删 |
| 2. llm | `extract_topics.llm` | 1 次 LLM 调用，吐 topics JSON | 10-60s | LLM 超时 (>90s 推 failed) |
| 3. validate | `extract_topics.validate` | JSON schema 校验：1-8 条 topic、title/desc/prereqs/excerpt/source_resource_id 必填且类型对；excerpt 500-1500 字；source_resource_id 必须出现在 input | <50ms | JSON 不合规 → retry 最多 1 次；仍失败 → failed |
| 4. write | `extract_topics.write` | 事务式整删 + INSERT KP + INSERT MapNode（见 §4） | <500ms | DB 写入失败 |
| 5. done | `extract_topics.done` | 推 completed event with `created_node_ids` | <10ms | — |

已拍板的细节（A-D）：
- **A：orphan KP 清理**在 `write` 阶段跑（事务内）
- **B：非 .md → 400**，不尝试 PDF/DOCX 转 md
- **C：失败不留 DB 痕迹**，干净退出
- **D：超时 90s / 90s**（放宽），不阻塞前端

### 3.4 重生成时的整删与重建（事务内）

```sql
BEGIN;
-- [1] 整删该 student 的私有数据
DELETE FROM map_nodes WHERE student_id = :student_id;
--  → FK CASCADE 自动删 levels → exercises + level_completions
DELETE FROM level_completions WHERE student_id = :student_id;  -- 防御兜底
-- [2] 清理 orphan KP（仅清用户 md 蒸馏出来的）
DELETE FROM knowledge_points
  WHERE NOT EXISTS (SELECT 1 FROM map_nodes WHERE map_nodes.kp_id = knowledge_points.kp_id)
    AND source IS NOT NULL;
-- [3] INSERT 新 KP 与 MapNode
INSERT INTO knowledge_points (title, description, source, source_content_md)
  VALUES (...) RETURNING kp_id;
INSERT INTO map_nodes (student_id, kp_id, status, branch_type, position)
  VALUES (...);  -- position 按网格 (col, row) 自动算
COMMIT;
```

### 3.5 SSE EventSource 协议（沿用既有 + 加枚举）

`progress/stages.py` 追加：

```python
class Stage(str, Enum):
    # 既有：
    PROFILE_BUILD = "profile.build"
    PLAN_GENERATE = "plan.generate"
    DIRECTOR = "director"
    EXERCISE = "exercise"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    # 新加（Task 2）：
    EXTRACT_TOPICS_PARSE = "extract_topics.parse"
    EXTRACT_TOPICS_LLM = "extract_topics.llm"
    EXTRACT_TOPICS_VALIDATE = "extract_topics.validate"
    EXTRACT_TOPICS_WRITE = "extract_topics.write"
    EXTRACT_TOPICS_DONE = "extract_topics.done"
```

事件格式（仿 `profile.py:_stream_events`）：

```json
// event: progress
{ "stage": "extract_topics.llm", "status": "running|completed|failed", "payload": {...}, "timestamp": "..." }
// event: completed（终态）
{ "stage": "extract_topics.done", "status": "completed", "payload": {"created_node_ids": [...], "extracted_resource_count": 3}, "timestamp": "..." }
// event: error（任意阶段失败）
{ "stage": "extract_topics.<stage>", "status": "failed", "payload": {"error": "..."}, "timestamp": "..." }
```

### 3.6 `skill.resource.extract_topics` SKILL.md（新建）

路径：`backend/skills/skill.resource.extract_topics/SKILL.md`

```yaml
---
name: skill.resource.extract_topics
description: 从用户上传的 .md 资料中抽取主题，生成 KP 与 MapNode
input: { resources: [{ id, name, content_md }] }
output: { topics: [{ title, description, prerequisites, excerpt_text, source_resource_id }] }
---
你是一名教学设计师。下面是学生上传的多份 .md 学习资料。
任务：
  1. 通读所有资料，识别出 N 个（3-8 个）**不重叠的、互相有逻辑关联**的主题
  2. 每个主题对应一个"知识节点"，给学生后续学习
  3. 对每个主题，从原始资料中挑出**最相关的 500-1500 字片段**，作为后续关卡生成时的"提供的材料知识"
  4. 主题之间尽量体现先修关系（prerequisites 数组），但不强求
严格输出以下 JSON 格式（不要其它任何内容，不要 markdown fence）：
{
  "topics": [
    {
      "title": "主题名（≤30 字）",
      "description": "一段话描述（≤150 字）",
      "prerequisites": ["本次输出的其它主题 title"],
      "excerpt_text": "原资料中 500-1500 字摘录",
      "source_resource_id": "上面 input.resources 中的某个 id"
    }
  ]
}
```

---

## 4. 前端：三个窗口 + 引导卡 + 进度条

### 4.1 新增 appId 注册清单

| appId | 单/多实例 | Dock 图标 | WIN_CONTENT | 用途 |
|-------|---------|----------|-------------|------|
| `resource_library` | 单 | `❐ Res` | "资源管理器" | Finder 网格 + 上传 + MD 浏览器触发 |
| `extract_topics_dialog` | 单 | 无 | "生成地图对话框" | 资源多选 + 右下确认/取消 |
| `md_browser` | 单 | 无 | "MD 浏览器" | 只读 markdown 渲染 |

注册位置（必加，除非已存在）：
1. `frontend/src/types/window.ts` 的 `AppId` 联合 + `SINGLETON_APP_IDS`
2. `frontend/src/App.tsx` 的 `WIN_CONTENT` + `renderBody` switch
3. `frontend/src/components/Dock.tsx` 的 `items`（仅 `resource_library`）
4. `frontend/src/store/useWorkspace.ts` 的 `DEFAULT_WIN` — **不强制加**（openWindow fallback 已兜底生成居中 600×400 窗口）

### 4.2 进度条浮层（不注册 appId）

`<ProgressOverlay>` 组件：浮层覆盖在父窗口上方，任务完成或失败自动消失。

```tsx
<ProgressOverlay taskId={...} endpoint="/api/resources/extract_topics/stream" stages={[
  { key: "parse",    label: "加载资料" },
  { key: "llm",      label: "AI 抽取主题" },
  { key: "validate", label: "校验结构" },
  { key: "write",    label: "写入知识图谱" },
  { key: "done",     label: "完成" }
]} />
```

视觉（已确定横向串点）：

```
┌────────────────────────────────────────────────┐
│  提炼主题进度                                    │
│                                                │
│  ✓ ─── ✓ ─── ●  ─── ○  ─── ○                  │
│ 加载资料  AI抽取  校验  写入  完成             │
│                                                │
│  当前: AI 抽取主题（约 30s）                    │
└────────────────────────────────────────────────┘
```

- ✓ = 已完成（绿）
- ● = 进行中（蓝 + 脉冲）
- ○ = 等待中（灰）

**没有取消按钮**（任务跑完或失败两种结果）。

`<ProgressOverlay>` 通过 props 切换 stage 序列适配关卡生成：订阅 `/api/level/{level_id}/stream`，stages = `[{key:'outline',...},{key:'lecture_html',...},{key:'exercise',...},{key:'review',...}]`。

### 4.3 资源管理器布局

```
┌──────────────────────────────────────────────────────┐
│ 资源管理器                            [≡] [▢] [✕]    │
├──────────────────────────────────────────────────────┤
│ [⬆ 上传 .md] [🗺 用所选生成地图 (3)]                 │
├──────────────────────────────────────────────────────┤
│  📂 全部资源（4）                                    │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐                 │
│  │ 📄  │  │ 📄  │  │ 📁  │  │ 📄  │                 │
│  │笔记1│  │笔记2│  │深度 │  │笔记3│                 │
│  └─────┘  └─────┘  └─────┘  └─────┘                 │
│  ┌─────┐                                            │
│  │ 📄  │                                            │
│  │笔记4│                                            │
│  └─────┘                                            │
└──────────────────────────────────────────────────────┘
```

| 维度 | 实现 |
|------|------|
| 数据源 | `GET /api/resources/list`，上传/改名/删除后 invalidate |
| 路径解析 | `split('/')` 拆 name，第一段为顶层 folder；前端计算 pathTree 渲染 |
| 排序 | 按 name 升序，UTF-16 码点，中文按 Unicode 序 |
| 列数 | 视口宽 / 120px（最小缩略图宽），自适应 |
| 缩略图 | 文件/folder 图标；已点开过加 1px 边框 |
| 多选 | 单击 + 框选 + 长按 |
| 拖动 | HTML5 drag-drop；源 `setData('resource:id', id)`；drop 目标校验非循环后 PUT |
| 重命名 | 双击 label → input → Enter/blur 提交 |
| 删除 | 二次确认 → DELETE → 网格立即移除 |
| 按扩展名过滤上传 | `name.toLowerCase().endsWith('.md')` |

### 4.4 MD 浏览器布局

```
┌────────────────────────────────────────────────┐
│  MD 浏览器 — 笔记1.md            [≡] [▢] [✕]    │
├────────────────────────────────────────────────┤
│ [← 返回]  字号[A- A+]  字数: 1234  [复制]      │
├────────────────────────────────────────────────┤
│  （markdown 渲染：KaTeX + Mermaid + 代码高亮）│
│                                                │
└────────────────────────────────────────────────┘
```

`<MarkdownRenderer content={html} />` 组件：复用 `LecturePane` 渲染管线（懒加载 KaTeX `.mjs`、Mermaid、代码高亮、任务列表）。MD 浏览器与 LecturePane 共用此组件。

### 4.5 提取主题对话框

- 复用资源管理器的缩略图网格布局（`<ResourceListView>` 抽象组件）
- 顶部标题："选择要提炼的资料（已选 N 个）"
- 右下角："取消" + "确认提炼"（勾选为空时 disabled）
- 确认 → POST `/api/resources/extract_topics` → 拿 task_id → 关弹窗 → 浮层进度条出现
- 取消 → 关弹窗，不发请求

### 4.6 冷启动：默认空窗口 + 引导卡

```ts
// useWorkspace 初始 state 改造
windows: {},           // 启动不创建任何 window
focusedId: null,
```

引导卡（不写入 windows state，因此 closeWindow 不会影响）：

```
┌────────────────────────────────────────────────┐
│                                                │
│       开始上传你的学习资料                      │
│                                                │
│       上传 1-4 份 .md 文件，系统会从中         │
│       抽取主题，生成知识地图。                 │
│                                                │
│       [打开资源管理器]                          │
│                                                │
│       （也可以从 Dock 栏打开）                  │
│                                                │
└────────────────────────────────────────────────┘
```

第一个 window 创建后引导卡 unmount。task_progress 历史记不保留（v1）。

### 4.7 拖拽上传与按钮上传

- 顶部 `⬆ 上传 .md` 按钮触发隐藏 `<input type="file" accept=".md" multiple>`
- 整个资源管理器窗口监听 `dragover`/`drop`，接收 .md 文件
- 上传成功 → invalidate 资源列表 → 网格刷新；**不**自动触发提取主题

---

## 5. 实施：6 个 task 拆分

| # | Task | 关键改动 | 工作量 |
|---|------|---------|--------|
| 1 | **基础数据层** | `alembic` 新 resources 表 + KP 加 source/source_content_md 列；`domain/resource.py` ORM；`gateway/routes/resources.py` 4 个 CRUD 路由；单测 | 1-1.5 天 |
| 2 | **提取主题后端流程 + orphan KP 清理** | `skills/skill.resource.extract_topics/SKILL.md`；`agents/extract_topics.py` 5 阶段 + JSON schema + retry；`gateway/routes/extract_topics.py` POST 触发；`progress/stages.py` 加枚举；单测 | 2-3 天 |
| 3 | **SSE 流 + 进度条组件** | `gateway/routes/extract_topics.py` 加 GET /stream（仿 profile.py:_stream_events）；`frontend/src/components/ProgressOverlay.tsx` 浮层 5 阶段；`frontend/src/api/resources.ts` SSE 客户端封装 | 1-2 天 |
| 4 | **前端三大组件抽象** | `MarkdownRenderer.tsx` 抽出（KaTeX + Mermaid + 代码高亮）；`ResourceListView.tsx` 抽出（缩略图网格 + 排序 + 多选 + 拖动）；`LecturePane.tsx` 重构使用 MarkdownRenderer | 2 天 |
| 5 | **三窗口 + 引导卡 + 端到端** | 资源管理器、MD 浏览器、提取主题对话框三个 windows；引导卡；冷启动空 windows；端到端：上传 → 多选 → 提取主题对话框 → SSE 进度条 → 节点出现 | 2-3 天 |
| 6 | **director chain 注入 source_content_md + 关卡进度条复用** | `agents/core.py` prefetch 加 source_content_md；`skill.lecture.generate/SKILL.md` 系统提示词加"若 KP 含 source_content_md 请引用"；exercise 同上；ProgressOverlay 接关卡进度条 | 2 天 |

整体 10-13 天（2-3 周）。每个 task 走 SDD：implementer + task reviewer + 末尾 whole-branch review。

---

## 6. 测试、验证、不做的事、迁移、回滚

### 6.1 单测覆盖矩阵

| Task | 测试文件 | 关键断言 |
|------|---------|---------|
| 1 | `tests/unit/test_resources_crud.py` | >4 个拒绝 / >10MB 拒绝 / 非 .md 拒绝；虚拟前缀 PUT 非循环校验；软删过滤；KP migration 字段存在 |
| 2 | `tests/unit/test_extract_topics_pipeline.py` | 5 阶段 SSE 事件正确；JSON schema 失败 retry 1 次；事务回滚（注入 failure）；orphan KP 清理；MapNode FK CASCADE 清 Level/Exercise/Completion |
| 3 | `tests/integration/test_extract_topics_sse.py` | EventSource 真实连，5 个 progress + 1 个 completed |
| 4 | vitest: `MarkdownRenderer.test.tsx` / `ResourceListView.test.tsx` | KaTeX / Mermaid 解析；拖动触发 PUT |
| 5 | e2e 手动 + 关键 vitest | 端到端串联：上传 3 md → 多选 → 提取主题对话框 → SSE → 节点出现 → 引导卡消失 |
| 6 | `tests/unit/test_director_injects_source_content.py` | core.py prefetch 透传 source_content_md；lecture/exercise SKILL.md 模拟 LLM 调用时 prompt 含引用规则 |

### 6.2 全量验证

```bash
cd backend && uv run pytest tests/unit -p no:warnings    # 176 旧 + 6 task 新增
cd backend && uv run mypy src/selflearn                   # clean
cd backend && bash scripts/smoke_mvp.sh                   # 8/8
cd frontend && npm run build                              # tsc --noEmit + vite
```

### 6.3 端到端 demo 脚本（Task 5 末尾交付）

`scripts/e2e_md_driven.sh`（新增）：

```bash
#!/bin/bash
set -euo pipefail
mkdir -p /tmp/md_files
echo "# 自注意力机制\n\nSelf-Attention 让序列中每个位置都看其他位置..." > /tmp/md_files/01-self-attn.md
echo "# 多头注意力\n\n把多个 Self-Attention 并行..." > /tmp/md_files/02-multi-head.md
bash scripts/e2e_md_driven.sh /tmp/md_files/*.md

# 验收查询：
psql $DATABASE_URL -c "
  SELECT kp_id, title, source, LENGTH(source_content_md) AS excerpt_len
  FROM knowledge_points WHERE source IS NOT NULL;
  SELECT COUNT(*) FROM map_nodes WHERE student_id = '86820161-b0f0-455f-91b4-a69e49445bdf';
"
# 期望：2 个 KP、2 个 MapNode；lecture_html 含 "自注意力" 或 "Self-Attention"
```

### 6.4 不做的事（YAGNI 卡死）

| 不做 | 理由 |
|------|------|
| MinIO / Qdrant / Tika / OCR | md 文本够用；向量库推到 v2 |
| md 切片向量化 | LLM 直接读 excerpt_text |
| 跨 student KP 自动去重 | 重生成每次整删，无残留可能 |
| 资源上传并发进度条 | multipart 是同步接口 |
| 取消提取主题任务 | 已确定无取消按钮 |
| 文件夹右键重命名 | 虚拟前缀约束 |
| 多用户 / 权限 | KEEP_STUDENT 唯一账户 |
| 资源分享 / 导出 | 纯本地 |
| 大文件分片上传 | ≤10MB 已够 |
| 一次性大扫除脚本 | 运行时清理已足够 |
| 索引 / 全文检索 | excerpt_text 切片 LLM 直接处理 |
| `content_hash` 去重 | 用户拍板不加 |
| `resources.name` UNIQUE | 用户拍板不加 |

### 6.5 数据迁移与回滚

alembic migration 一次性创建：
1. 新表 `resources`
2. `knowledge_points` 加 `source VARCHAR(500) NULL` + `source_content_md TEXT NULL`

回滚：alembic `downgrade()` DROP 列 + DROP TABLE。

legacy 数据完全不动，老的 5 个 KP 没有 source 字段（NULL），与新流程并存。

### 6.6 风险与缓解

| 风险 | 缓解 |
|------|------|
| LLM 吐 topics JSON 不合规 | validate 严格 JSON schema + 最多 1 次整链重试 |
| LLM 输出 source_resource_id 引用不存在 | validate 拦；写库降级为 NULL + 日志告警 |
| 超长 md 爆 token | 前端 ≤10MB + 后端字符 >50 万硬拒 |
| 重生成被中断（关浏览器） | SSE 客户端关闭，后端 task 仍跑完；v1 不持久化 task_progress |
| FK CASCADE 误删 | 整删前 `count(map_nodes WHERE student_id = ?)` 留日志 |

---

## 7. 全局约束（与现有约定一致）

- 后端不引入新依赖（如有 mcp/nh3 之外的，需 spec 阶段说明）
- 不修改任何已有 alembic migration，仅新增一个独立 migration（down_revision = 当前 head）
- 中文 commit message
- Docker 构建：`HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897`
- 测试运行：`cd backend && uv run pytest -p no:warnings`
- branch 直接 main（CLAUDE.md + memory `no-worktrees-sdd`）
- 全程 TDD：先 failing test，再实现，再 verify
- 不重做 ReviewAgent / Director chain（仅追加 KP 字段读取和 SKILL.md prompt）
- 不做的事已在 §6.4 列出

---

## 8. 变更总结（和 v4 详细设计 §3.14 / §3.15.8 对照）

| v4 详细设计 | 本 spec | 偏离 |
|----------|----------|------|
| MinIO 存对象 | PG TEXT 存 md | 大文件场景未来要迁 MinIO |
| Qdrant 异步索引 | LLM 直接读 excerpt_text | 检索场景等真有切片再 |
| Tika 解析多格式 | 仅 .md | YAGNI |
| resource_files / level_bind_files | resources / KP.source_content_md | 简化为 KP 字段 |
| 评审 Agent 对用户私域放宽验证 | lecture / exercise SKILL.md 加"如 KP 含 source_content_md 则引用"软规则 | 不做 review_stage 改造 |
| `appId: resource_library` 全功能 | resource_library + md_browser + extract_topics_dialog 三窗口拆分 | 拆分更清晰 |

