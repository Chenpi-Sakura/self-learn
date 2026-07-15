# Agent 架构重构（Skill-driven + LLMAgent + MCP） — Design

**日期**：2026-07-15
**作者**：SelfLearn dev
**状态**：📐 Design（已澄清，待用户审）
**关联 backlog**：
- `docs/superpowers/backlog/2026-07-15-html-lecture.md`（讲义 — 受本 spec 决定影响）
- 本 spec **不实现讲义**，讲义作为本 spec 落地后的下一个任务

---

## 一、目标

把现状 5 个 Python `Agent` class 收敛为 1 个 `LLMAgent` + 1 个 `ReviewStage`，所有行为由 `SKILL.md` 描述，所有 DB 读写走 MCP Server（1 个 stdio 进程）。**改行为 = 改 Skill，不动 Python 代码。**

## 二、问题陈述

### 现状

`backend/src/selflearn/agents/builtin/` 有 5 个 class：`director_agent.py` / `exercise_agent.py` / `review_agent.py` / `plan_agent.py` / `profile_agent.py`。每个 class 在 Python 里**写死**了：
- 调 LLM / 不调 LLM
- 拼 prompt 的方式
- 调哪个 tool
- 重试策略
- 失败行为

`agents/scheduler.py:_AGENT_FOR_SKILL` 是**硬连接 map**（5 个 key），按 `env.target.id` 选 class。`docs/skills/*.md` 已经是声明式 Skill 文档（带 frontmatter + body），但**只是给 LLM 看的 prompt 片段**——不决定 Agent 行为。

DB 读写全部 `from selflearn.infra.db import get_session_factory()` 直接走 SQLAlchemy，**Agent 知道 ORM 细节**。ReviewAgent 现状是 4 条 Python `for` 循环 + 1 个 `tool.lint_json` 调，业务规则 5 条（duplicate_prompt / options_length == 4 / answer_not_in_options / difficulty_gradient / lint_json）。**不调 LLM 做语义审查**。

### 问题

1. **行为绑死在 Python**：换业务规则 / 改 prompt / 换重试策略 = 改代码 + 发版
2. **5 个 class 重复 boilerplate**：每个都写 progress_publish / try/except / 写 reply envelope
3. **Review 缺语义层**：题目 JSON 过了 lint 但内容胡说的，review 抓不出来
4. **DB 访问无收口**：Agent 直接 ORM，跨 5 个 class 散落
5. **Skill 文档 ≠ 行为描述**：现有 5 个 Skill md 没有 mcp_prefetch / tool_use 等结构化字段，Agent 不知道该调什么 MCP

## 三、目标架构

### 3.1 核心组件

| 组件 | 数量 | 职责 |
|---|---|---|
| **LLMAgent** | 1 | 通用执行器。加载 Skill → MCP 预拉 → 拼 prompt → 调 LLM → lint → 返回 |
| **ReviewStage** | 1 | 强制 Python stage。业务规则（5 条 + lint）+ LLM 语义审查 |
| **Director 链** | 1 | 编排：lecture → lecture review → exercise（≤2 轮）→ exercise review（双步骤）→ 写库 |
| **MCP Server** | 1 | stdio 进程，15 个 tool（3 utility + 12 DB） |
| **Skill md** | 7 | Anthropic `SKILL.md` 格式：frontmatter（mcp_prefetch / mcp_tool_use / output_schema / max_retries）+ body（prompt 模板） |

### 3.2 数据流图

```
┌────────────────────────────────────────────────────────────────────┐
│ Gateway (HTTP 路由 — 保留不变)                                       │
│  POST /api/level/start {student_id, node_id}                        │
│  → level.py 查 in-flight 关卡 / 复用 or 发 envelope                 │
└────────────────────────────────────────────────────────────────────┘
                              ↓ envelope (target.id = "skill.director.start")
┌────────────────────────────────────────────────────────────────────┐
│ Worker (RabbitMQ consumer — 保留不变)                                │
│  scheduler.dispatch(env)                                            │
│    → 选 Skill (按 target.id)，不再选 Agent class                    │
│    → LLMAgent.run(skill_id, env)                                    │
└────────────────────────────────────────────────────────────────────┘
                              ↓ LLMAgent 内部
┌────────────────────────────────────────────────────────────────────┐
│ 1. mcp.call("tool.fetch_skill", skill_id)          → Skill 文档    │
│ 2. mcp.call(*skill.mcp_prefetch)                   → 预拉数据      │
│ 3. 拼 prompt = skill.body.format(**prefetch)                        │
│ 4. 调 LLM，tools=skill.mcp_tool_use (v1 空 list)                   │
│ 5. mcp.call("tool.lint_json", llm_output, skill.output_schema)      │
│ 6. 失败重试（max_retries=skill.max_retries）                        │
│ 7. parse(output, output_schema) → 返回 typed                       │
└────────────────────────────────────────────────────────────────────┘
                              ↓ 结果
┌────────────────────────────────────────────────────────────────────┐
│ Director 链 — run_director_chain()                                  │
│  lecture.generate → review_lecture → exercise.generate (≤2 轮) →   │
│  review_exercise_business (仅第 1 轮) → review_exercise_llm (每轮) │
│  → mcp.create_level + mcp.bulk_create_exercises → mcp.update_profile│
│  → SSE COMPLETED                                                    │
│                                                                    │
│  整链 retry 包装 (max_attempts=3，失败重生成)                         │
└────────────────────────────────────────────────────────────────────┘
```

### 3.3 Skill 清单（7 个）

```
backend/skills/
├── skill.profile.build/SKILL.md
├── skill.plan.generate/SKILL.md
├── skill.exercise.generate/SKILL.md          # 现状重写
├── skill.review.exercise.business/SKILL.md   # ★ 新增 — 业务规则描述
├── skill.review.exercise.llm/SKILL.md         # ★ 新增 — LLM 语义审查 prompt
├── skill.lecture.generate/SKILL.md           # ★ 新增 — 讲义生成 prompt (本 spec 不实现讲义，但 Skill 文件预留)
└── skill.director.start/SKILL.md              # 现状改写 — 链编排描述
```

**SKILL.md 模板**：

```yaml
---
name: skill-name-kebab-case
description: Use when [triggering conditions]. Output [format].
output_schema: schemas/<name>.schema.json
mcp_prefetch:
  - tool.get_kp
  - tool.get_recent_scores
mcp_tool_use: []                   # v1: 空 list（不实现 LLM 实时 tool_use）
max_retries: 1
---

# Skill Name

## 任务
[Markdown prompt template — 由 LLM 看到]

## 输入
- field_1: 描述
- field_2: 描述

## 输出
[schema 描述]

## 严格约束
- ...
```

### 3.4 MCP Server 设计

**1 个 stdio 进程**：`python -m selflearn.mcp_server`，使用 `mcp.server.fastmcp.FastMCP`。

**15 个 tool**：

| # | 工具 | 类别 | 入参 → 出参 |
|---|---|---|---|
| 1 | `tool.fetch_skill` | utility | `skill_id` → `Skill` (含 name/description/body/output_schema/mcp_prefetch/mcp_tool_use/max_retries) |
| 2 | `tool.lint_json` | utility | `payload, schema_name` → `{ok, error}` |
| 3 | `tool.lint_html` | utility | `html, allowed_classes` → `{cleaned, is_empty}` (用 nh3) |
| 4 | `tool.get_active_node` | DB | `student_id` → `{node_id, kp_id, status, position}` |
| 5 | `tool.get_kp` | DB | `kp_id` → `{kp_id, subject, title, description, difficulty, prerequisites}` |
| 6 | `tool.get_recent_scores` | DB | `student_id, limit=3` → `list[float]` |
| 7 | `tool.get_profile` | DB | `student_id` → `{dimensions, tags, last_updated}` |
| 8 | `tool.create_profile` | DB | `student_id, dimensions, tags` → `{profile_id}` |
| 9 | `tool.get_existing_nodes` | DB | `student_id` → `list[Node]` |
| 10 | `tool.get_kps` | DB | `limit=5` → `list[KP]` |
| 11 | `tool.create_map_nodes` | DB | `student_id, kp_id_list, positions` → `list[node_id]` |
| 12 | `tool.create_level` | DB | `node_id, lecture_html` → `{level_id}` |
| 13 | `tool.bulk_create_exercises` | DB | `level_id, exercises` → `list[exercise_id]` |
| 14 | `tool.update_profile` | DB | `student_id, deltas` → `{profile, snapshot_id}` |
| 15 | `tool.apply_level_completion` | DB | `level_id, student_id, score, answers` → `{completion_id}` |

**`tool.lint_html` 实现**：用 `nh3.clean()`，白名单标签 = `{h1,h2,h3,p,ul,ol,li,strong,em,code,pre,blockquote,table,thead,tbody,tr,th,td,br,hr,span,div}`，class 属性过滤到 `allowed_classes`（`callout / formula / example / katex`）。

### 3.5 Review Stage 设计

**两步骤**：

```python
class ReviewStage:
    async def review_lecture(lecture_html: str) -> ReviewResult:
        # 业务规则（2 条）：lint_html + not_empty
        # rejected → 整链失败

    async def review_exercise_business(exercises: list[dict]) -> ReviewResult:
        # 业务规则（5 条）：lint_json + duplicate_prompt + options_min(>=2)
        # + answer_not_in_options + difficulty_gradient
        # rejected → 整链失败
        # needs_fix → log warn，写库照常

    async def review_exercise_llm(exercises, kp_title, trace_id) -> LLMReviewResult:
        # 调 LLMAgent 跑 skill.review.exercise.llm
        # 产出 {verdict: passed|needs_revision, suggestions: list[str], issues: list[dict]}
        # needs_revision → 喂 suggestions 给第 2 轮 exercise LLM（业务 issues 不喂）
```

**业务规则改动**（vs. 现状）：
- `options_length == 4` → `options_min >= 2`（你说"≥2 即可"）
- `duplicate_prompt` 保留
- `answer_not_in_options` 保留
- `difficulty_gradient` 保留
- `lint_json` 保留

### 3.6 Director 链流程

```
run_director_chain_with_retry(env, agent, review, max_attempts=3):
  for attempt in range(max_attempts):
    try:
      return await run_director_chain(env, agent, review)
    except (AppError, DBError) as e:
      log warning + retry
  raise

run_director_chain(env, agent, review):
  1. node = await mcp.call("tool.get_active_node", student_id)
  2. kp = await mcp.call("tool.get_kp", kp_id=node.kp_id)
  3. recent = await mcp.call("tool.get_recent_scores", student_id, limit=3)
  4. difficulty = compute_difficulty(recent)

  5. lecture_html = await agent.run("skill.lecture.generate", env)
  6. review_lec = await review.review_lecture(lecture_html)
     if review_lec.verdict == "rejected": raise AppError

  7. for revision in [0, 1]:                          # 最多 2 轮
       exercises = await agent.run("skill.exercise.generate", env_with_suggestions)
       if revision == 0:
         review_biz = await review.review_exercise_business(exercises)
         if review_biz.verdict == "rejected": raise AppError
         # needs_fix: log warn，不重做
       review_llm = await review.review_exercise_llm(exercises, kp.title, trace_id)
       if review_llm.verdict == "passed": break
       if revision == 1: log warning + break
       suggestions = review_llm.suggestions          # 第 2 轮喂 LLM suggestions

  8. level = await mcp.call("tool.create_level", node_id, lecture_html)
  9. await mcp.call("tool.bulk_create_exercises", level_id, exercises)
  10. deltas = compute_deltas(final_review.score)
  11. await mcp.call("tool.update_profile", student_id, deltas)
  12. SSE COMPLETED
```

**失败策略**（AppError code 列表）：

| 失败 | AppError code | 行为 |
|---|---|---|
| MCP 预拉任意 fail | `mcp_prefetch_failed` | retry (max_attempts=3) |
| lecture LLM lint 失败 | `lecture_llm_failed` | retry |
| lecture 业务规则 rejected | `lecture_rejected` | retry |
| exercise LLM lint 失败 | `exercise_llm_failed` | retry |
| exercise 业务规则 rejected | `exercise_rejected` | retry |
| exercise LLM needs_revision × 2 | `exercise_max_revisions` | retry (warn log) |
| 写库 fail | `db_write_failed` | retry (整链重生成) |
| update_profile fail | `profile_update_failed` | retry (level 已建, profile 未更新) |

### 3.7 失败处理总则

**整链重生成** = retry 整 `run_director_chain()`。依赖现状 `level/start` 路由的幂等性（已实现，reused: true）：
- attempt 1: 调 LLM 出题 → 写库失败 → 留下 in-flight 关卡
- attempt 2: `level/start` 路由发现 in-flight → **但 retry 是在 worker 内部重跑**（不是新 envelope）→ **不依赖路由幂等性**

**注意**：worker 内部 retry 不会重新走路由的幂等检查。retry 失败时：
- DB 里的 in-flight level 由下次启动时清理（或者**保留**，由下次 `level/start` 复用）
- 这意味着 retry 的代价：每次多花一次 LLM 调用

**最大 retry = 3**：避免无限循环。

## 四、范围

### 4.1 改动文件清单

**新建**：
```
src/selflearn/mcp_server/
    __init__.py
    __main__.py
    server.py
    tools/__init__.py
    tools/fetch_skill.py
    tools/lint_json.py
    tools/lint_html.py
    tools/get_active_node.py
    tools/get_kp.py
    tools/get_recent_scores.py
    tools/get_profile.py
    tools/create_profile.py
    tools/get_existing_nodes.py
    tools/get_kps.py
    tools/create_map_nodes.py
    tools/create_level.py
    tools/bulk_create_exercises.py
    tools/update_profile.py
    tools/apply_level_completion.py
src/selflearn/agents/core.py                    # LLMAgent
src/selflearn/agents/review_stage.py            # ReviewStage
src/selflearn/agents/director.py                # Director 链
backend/skills/skill.profile.build/SKILL.md
backend/skills/skill.plan.generate/SKILL.md
backend/skills/skill.exercise.generate/SKILL.md
backend/skills/skill.review.exercise.business/SKILL.md
backend/skills/skill.review.exercise.llm/SKILL.md
backend/skills/skill.lecture.generate/SKILL.md
backend/skills/skill.director.start/SKILL.md
tests/unit/mcp/test_fetch_skill.py
tests/unit/mcp/test_lint_json.py
tests/unit/mcp/test_lint_html.py
tests/unit/mcp/test_get_active_node.py
... (15 tool tests)
tests/unit/test_llm_agent.py
tests/unit/test_review_stage.py
tests/unit/test_director_chain.py
tests/integration/test_mcp_client.py
tests/integration/test_director_e2e.py
```

**修改**：
```
src/selflearn/agents/scheduler.py              # 删 _AGENT_FOR_SKILL map，保留 dispatch 入口
src/selflearn/agents/builtin/                  # 5 个文件移到 _legacy/ 并加 deprecation warning
src/selflearn/skills/library.py                # Skill dataclass 加 mcp_prefetch / mcp_tool_use / max_retries
src/selflearn/main.py                          # 启动 MCP client + LLMAgent
pyproject.toml                                 # 加 mcp + nh3 依赖
backend/alembic/versions/<new>.py              # 暂不需要（lecture_html 是 backlog 另一 PR）
```

**删除**（无保留）：
```
src/selflearn/agents/builtin/director_agent.py       # 迁到 _legacy
src/selflearn/agents/builtin/exercise_agent.py
src/selflearn/agents/builtin/review_agent.py
src/selflearn/agents/builtin/plan_agent.py
src/selflearn/agents/builtin/profile_agent.py
src/selflearn/tools/                                 # 整个目录（被 mcp_server 取代）
src/selflearn/tools/builtin/fetch_template.py
src/selflearn/tools/builtin/lint_json.py
src/selflearn/tools/builtin/store_kp.py
src/selflearn/tools/protocol.py
backend/docs/skills/                                 # 整个目录（迁到 backend/skills/）
backend/prompts/exercise_generation_v1.yaml          # 内容迁到 skill.exercise.generate/SKILL.md
backend/prompts/review_exercise_v1.yaml              # 内容迁到 skill.review.exercise.business/SKILL.md
```

### 4.2 实施顺序（5 个 phase，每个独立可测）

| Phase | 内容 | 验证 |
|---|---|---|
| **P1. MCP Server** | 15 个 tool + stdio 启动 + FastMCP | 每个 tool 1 单测；用真 stdio client 跑通 list_tools / call_tool |
| **P2. Skill 目录迁移** | 5 个旧 Skill 移到 `backend/skills/<id>/SKILL.md`，加 frontmatter；新增 2 个 Skill | `load_all()` 加载 7 个；frontmatter 解析单测 |
| **P3. LLMAgent + ReviewStage** | `agents/core.py` + `agents/review_stage.py` | 单测覆盖 prefetch / prompt / lint / retry / 业务规则 / LLM 审查 |
| **P4. Director 链 + Retry** | `agents/director.py` 实现链 + retry 包装 | 单测覆盖 revision 0/1 / retry 0-3；集成测试 mock LLM 跑通 |
| **P5. 删除旧代码** | 删 5 个旧 Agent class、删 tools/、删 backend/docs/skills/、改 scheduler.py | 旧测试 108 全 PASS + 新增 35-40 个全 PASS + mypy clean + smoke + Playwright |

### 4.3 兼容性

| 旧 API/行为 | 新架构保持 |
|---|---|
| `POST /api/level/start` 路由 | ✅ 完全不变（含幂等性） |
| `GET /api/level/{level_id}` | ✅ 完全不变（响应字段不变） |
| `POST /api/level/{level_id}/submit` | ✅ 完全不变 |
| `GET /api/profile/{id}` / `history` | ✅ 完全不变 |
| SSE 协议（event: progress / completed / error） | ✅ 完全不变 |
| `envelope.action = "skill.completed"` 协议 | ✅ 完全不变 |
| Worker 的 RabbitMQ 消费 + 进度推 Redis | ✅ 完全不变 |
| `tool.lint_json(payload, schema="exercise")` 入参/出参 | ✅ 保持（同名 MCP tool 替代） |
| `smoke_mvp.sh` 8/8 | ✅ 保持 |
| Playwright e2e 3/3 | ✅ 保持 |
| 已有 108 个 pytest | ✅ 全部保持 PASS（API 形态不变） |

## 五、测试策略

### 5.1 单元测试（新增 30-40 个）

**MCP tool 单测**（15 个）：
- 每个 tool 1 个 `tests/unit/mcp/test_<name>.py`
- 用真 DB（testcontainers 或 in-memory SQLite 不支持 JSONB → 用真 PG container）
- 覆盖：happy path + 入参校验 + 错误返回

**LLMAgent 单测**（2-3 个）：
- mock MCPClient + LLM
- 覆盖：prefetch 顺序 / prompt 拼装 / lint 重试 / tool_use 循环（v1 空 list）

**ReviewStage 单测**（2-3 个）：
- mock LLMAgent + MCPClient
- 覆盖：lint_html / not_empty / 5 业务规则 / LLM 语义审查 verdict

**Director 链单测**（2-3 个）：
- mock LLMAgent + ReviewStage + MCP
- 覆盖：链顺序 / revision 0/1 / retry 0-3 / SSE 事件

**Skill loader 单测**（1-2 个）：
- frontmatter 解析 / 7 个 Skill 必填字段校验

### 5.2 集成测试（新增 3-5 个）

- `test_mcp_client_integration.py`：用真 stdio 起 MCP server
- `test_director_e2e.py`：mock LLM + 真 DB 跑通整链
- `test_skill_to_chain.py`：验证 Skill frontmatter → Director 链可执行

### 5.3 端到端验收

- `pytest tests/` 全 PASS（旧 108 + 新增 35-40 = 约 150）
- `mypy src/selflearn` clean
- `bash scripts/smoke_mvp.sh` 8/8 PASS
- Playwright `e2e/smoke.spec.ts` 3/3 PASS

## 六、风险与缓解

| 风险 | 缓解 |
|---|---|
| MCP stdio 通信慢 | 单条 call 30ms（本地），整链 5-10 call → 最多 500ms 开销，可接受 |
| nh3 不支持中文 HTML 属性 | 不用 attribute 用 class，OK |
| LLM tool_use 失控 | v1 `mcp_tool_use=[]` 默认空，**不实现** |
| 旧测试破 | API 形态不变是硬约束（§ 4.3） |
| `tool.fetch_skill` 读不到 md | 启动 fail-fast（preflight check） |
| 改完发现 review LLM 太慢 | `enable_llm_review=False` 开关可降级 |

## 七、范围外（明确不做）

- ❌ LLM 实时 tool_use 调用（v1）
- ❌ 讲义 HTML 实际生成（backlog 另一 PR，本 spec 只预留 `skill.lecture.generate`）
- ❌ 图片 / 视频 / iframe
- ❌ 代码执行沙箱
- ❌ 历史关卡补讲义
- ❌ Alembic 自动迁移（DB schema 变更在别的 PR）
- ❌ 回退机制（一次性重构，不留 _legacy/）

## 八、决策记录

| # | 决策 | 选择 |
|---|---|---|
| 1 | Agent class 数 | 1（LLMAgent） |
| 2 | Skill 文件 | 目录 + SKILL.md（Anthropic 规范） |
| 3 | MCP Server | 1 个独立进程，stdio |
| 4 | MCP 实现 | 改造现有 tools/builtin/ 走 MCP 协议（最终 15 个 tool） |
| 5 | DB 读写 | 走 MCP（不直连 ORM） |
| 6 | Agent ↔ MCP 模式 | 预拉（必填） + 预留 Tool Use（v1 空 list） |
| 7 | 迁移路径 | 一次性重构（不留 _legacy/） |
| 8 | 行为切换 | 靠不同 Skill 文件 |
| 9 | Review Stage | Python 强制 stage，业务规则（5 条 + lint_json）+ LLM 语义审查 |
| 10 | Review 双步骤 | needs_fix log warn + 写库；needs_revision 喂 LLM suggestions 给第 2 轮 |
| 11 | Review 业务规则跑几次 | lecture 1 次 + exercise 第 1 轮 1 次 |
| 12 | options_length 规则 | 改为 `options_min >= 2` |
| 13 | 数据脏处理 | 整链 retry（max_attempts=3） |
| 14 | Skill 数量 | 7（5 旧 + 2 新） |
| 15 | 实施顺序 | P1→P2→P3→P4→P5 |

## 九、关联文档

- `docs/superpowers/backlog/2026-07-15-html-lecture.md`（讲义 — 后续任务）
- `docs/superpowers/reports/2026-07-14-stage4-complete.md`（Stage 4 验收基线）
- `docs/superpowers/specs/2026-07-13-stage4-demo-integration-design.md`（Stage 4 设计）

---

**审稿人请检查**：

1. § 3.1 组件清单 + § 3.2 数据流图是否清晰？
2. § 3.4 MCP tool 15 个的划分是否合理？
3. § 3.6 Director 链流程是否完整？
4. § 4.2 实施顺序 5 个 phase 是否合理？
5. § 4.3 兼容性承诺是否足够？
6. § 7 范围外是否有遗漏？

**审完后回复**："批准" / "修改 X" / "重做 Y"。
