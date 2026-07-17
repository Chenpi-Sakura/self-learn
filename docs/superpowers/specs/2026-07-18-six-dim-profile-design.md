# Task 363 — 六维画像冷启动生成（Onboarding）设计 Spec

> **For agentic workers:** 配套实施计划见 `docs/superpowers/plans/2026-07-18-six-dim-profile.md`（writing-plans skill 输出）。

**Goal:** 让首次进站的学生通过 8 道情境题（7 单选/多选 + 1 开放文本）触发 LLM 一次性评分，得到六维画像初始值（kb/vp/as/ge/ept/fd），写入 `Profile.dimensions` 并创建 trigger=`onboarding` 的 snapshot。

**Architecture:** 新增独立 onboarding 子系统 — 题库 JSON + LLM skill（`skill.profile.onboard`）+ MCP tool（`tool.onboard_profile`）+ HTTP 路由（`/api/onboarding/*`）+ 前端路由守卫 + `Onboarding.tsx` 全屏组件。**不动现有 Profile / ProfileSnapshot schema**，只复用 JSONB + 新增 snapshot.trigger=`"onboarding"`。

**Tech Stack:** FastAPI 路由 + LLMAgent 单 chat + sse_starlette（不用，onboarding 同步）+ React + vitest + pytest。

---

## Global Constraints

| # | 约束 | 来源 |
|---|------|------|
| 1 | 单账户 `KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"` 4 处硬编码保持一致 | `CLAUDE.md` |
| 2 | branch 直 main，不开 worktree | memory `no-worktrees-sdd` |
| 3 | 中文 commit message | `CLAUDE.md` |
| 4 | Docker 代理 `HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897` | `CLAUDE.md` |
| 5 | 无登录鉴权 | memory `no-auth-no-login` |
| 6 | 沿用 6 维短名 `kb/vp/as/ge/ept/fd`、长名 `knowledge_base/visual_preference/analytic_style/goal_employment/error_prone_type/focus_duration` | Stage 3 spec + Stage 4 spec + ProfileRadar.tsx |
| 7 | snapshot 字段名是 `profile`（不是 `dimensions`），snapshot 表用 JSON 不是 JSONB | 现有 `ProfileSnapshot` 模型 |
| 8 | 前端不引入新组件库，沿用 Notion Serif 风格 + HedvigLettersSerif 字体 + `ProgressOverlay` 同款遮罩 | 现有 `TreasureMap.tsx` / `ProgressOverlay.tsx` |
| 9 | 画像已是默认 0.5 时不能再 onboarding（防覆盖学习成果） | 路由层 409 |
| 10 | 路由文件加 CHANGELOG：onboarding 不动 envelope 同步总线 | bus 仅供异步 skill.execute |

---

## 已澄清的设计决策

| # | 决策 | 选择 |
|---|------|------|
| 1 | 交互形式 | 情境题（scenario），6 维各 1-2 题 |
| 2 | 触发时机 | **首次使用**（Profile 全 0.5 时） |
| 3 | 题型 | 7-8 题单选/多选 + 最后 1 题开放文本 |
| 4 | 题源 | **预制题库**（JSON 文件，可控、零额外 token） |
| 5 | 评分 | **单 LLM 一次性评分**（看到全量回答 + 6 维定义 → 输出 6 个 [0,1] 分 + reasoning） |
| 6 | 路由 | 独立 `/onboarding` 路由，全屏覆盖 |
| 7 | 提交模式 | 同步 HTTP（不走 envelope，30-60s 可接受） |

---

## 1. 数据模型

### 1.1 复用现有表，**不引入新 schema**

| 表 | 字段 | 用法 |
|----|------|------|
| `profiles` | `dimensions` JSONB | onboarding 后写入 6 个短 key |
| `profile_snapshots` | `profile` JSON | 新增 row，`trigger="onboarding"` |
| `profile_snapshots` | `trigger` String(32) | 已有枚举扩展，不需迁移（字段无 CHECK 约束） |

**关键决策**：6 个维度的定义（短/长名 + 中文 label）**全部已硬编码**于：

- `backend/src/selflearn/gateway/routes/profile.py:150-157` `_LONG_TO_SHORT`
- `backend/skills/skill.profile.build/SKILL.md:12`
- `frontend/src/components/ProfileRadar.tsx:17-24` `DIM_MAP`

新文件必须**沿用同一套名称**，不允许引入新维度。

### 1.2 题库 JSON 形状

文件 `backend/src/selflearn/data/onboarding_questions.json`：

```json
[
  {
    "id": "q1_kb",
    "dimension_hint": "kb",
    "type": "single",
    "prompt": "遇到一个全新概念，你的第一反应是？",
    "options": [
      { "id": "a", "label": "找它的定义和来源" },
      { "id": "b", "label": "看几个例子理解用法" },
      { "id": "c", "label": "直接动手试一下" },
      { "id": "d", "label": "找人讨论一下" }
    ]
  },
  {
    "id": "q7_open",
    "type": "open",
    "prompt": "请用一两句话描述：你理想的学习方式是什么？",
    "placeholder": "比如：我喜欢先看图，再看例子，最后总结..."
  }
]
```

**字段约定**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✓ | 全局唯一，格式 `q{N}_{hint}` |
| `dimension_hint` | string | 单选/多选必填 | 短名之一：`kb/vp/as/ge/ept/fd` |
| `type` | string | ✓ | `"single"` / `"multi"` / `"open"` |
| `prompt` | string | ✓ | 题干，中文 |
| `options` | list | 单选/多选必填 | `[{id, label}]`，id 用 `"a"/"b"/"c"/"d"` |
| `placeholder` | string | 开放题必填 | 提示语 |

**结构约束（被 `test_onboarding_questions_json.py` 强制）**：

1. 总数 7 ≤ N ≤ 8
2. 6 个短名各至少出现 1 次作为 `dimension_hint`
3. 最后 1 题 `type="open"` 且**没有** `dimension_hint`
4. 单选/多选题必须有 `options` 字段
5. 所有选项 `id` 在题内唯一

### 1.3 LLM Skill 输入/输出

`SKILL.md` 输出 JSON schema：

```json
{
  "type": "object",
  "properties": {
    "kb":  { "type": "number", "minimum": 0, "maximum": 1 },
    "vp":  { "type": "number", "minimum": 0, "maximum": 1 },
    "as":  { "type": "number", "minimum": 0, "maximum": 1 },
    "ge":  { "type": "number", "minimum": 0, "maximum": 1 },
    "ept": { "type": "number", "minimum": 0, "maximum": 1 },
    "fd":  { "type": "number", "minimum": 0, "maximum": 1 },
    "reasoning": { "type": "string" }
  },
  "required": ["kb","vp","as","ge","ept","fd","reasoning"]
}
```

**LLM 收到**：
- system prompt：`skill.profile.onboard/SKILL.md`（含 6 维长/短名定义 + 输入格式 + 输出 schema）
- user message：
  ```markdown
  ## Onboarding Questions
  ```json
  [{问题列表...}]
  ```

  ## Student Answers
  ```json
  [{question_id, choice, free_text?}, ...]
  ```
  ```

**LLM 返回**：6 个 [0,1] 分 + 100-200 字中文 reasoning（"AI 怎么给你评分的"，前端可展示在雷达图旁）。

---

## 2. 后端组件（3 个新文件 + 2 处修改）

### 2.1 `backend/skills/skill.profile.onboard/SKILL.md`

文件作用：LLM 的 prompt body（system message）。Markdown 格式与现有 `skill.lecture.generate`、`skill.exercise.generate` 一致。

**结构**：

```markdown
# Profile Onboard — 六维画像冷启动评分

你是 SelfLearn 的画像评估助手。下面有 {N} 道情境题 + 学生的回答。
请根据回答给出学生在 6 个维度上的评分（0.0 ~ 1.0）。

## 6 维度定义
- kb (knowledge_base 知识基础)：对新概念的接受速度
- vp (visual_preference 视觉偏好)：...
- as (analytic_style 分析风格)：...
- ge (goal_employment 求职目标)：...
- ept (error_prone_type 易错类型)：...
- fd (focus_duration 专注时长)：...

## 输入
- questions: JSON 数组，元素含 id/prompt/type/options/dimension_hint
- answers: JSON 数组，元素含 question_id/choice(s)/free_text

## 输出 JSON schema
```json
{...同 1.3...}
```

## 评分原则
- 单选/多选的选项无预设权重，按选项语义自由评分
- 开放题给出明确的维度信号
- reasoning 用中文，100-200 字
```

### 2.2 `backend/src/selflearn/mcp_server/tools/onboard_profile.py`

签名：

```python
async def onboard_profile(
    student_id: str,
    answers: list[dict[str, object]],  # [{question_id, choice, free_text?}]
    agent: LLMAgent,
) -> dict[str, object]:
    """LLM 单 chat 评分 → clamp → create_profile → snapshot."""
    ...
```

**职责**：
1. 调 `tool.get_profile(student_id)` 拿当前 dimensions
2. 若已非默认（6 维不全 0.5）→ 返回 `{ok: False, error: "already_onboarded"}`（路由层翻 409）
3. 构造 user message（questions + answers JSON 序列化）
4. 调 `agent.run("skill.profile.onboard", env)` — 内部走 prefetch + LLM + lint
5. **不传 envelope**：构造临时 Envelope only for `agent.run` 签名
6. 解析 lint 通过的 JSON，校验 6 维齐全 → 缺则补 0.5
7. clamp 到 [0,1]
8. 调 `tool.create_profile(student_id, dimensions=...)`（upsert）
9. 写 `ProfileSnapshot(student_id, profile=dimensions, trigger="onboarding")`
10. 返回 `{ok: True, dimensions, snapshot_id, reasoning}`

**异常路径**：
- LLM 返回非 JSON → AppError(INTERNAL, "onboard_lint_failed") → 路由层 500
- 缺维度 → log warn + 补 0.5（不影响主流程）
- DB 写失败 → AppError(INTERNAL, ...) → 路由层 500

### 2.3 `backend/src/selflearn/gateway/routes/onboarding.py`

```python
@router.get("/api/onboarding/questions")
async def get_questions() -> dict[str, object]:
    """读 JSON 返回；HTTP 缓存 10 分钟。"""

@router.post("/api/onboarding/submit", status_code=200)
async def submit(body: OnboardingSubmitRequest) -> dict[str, object]:
    """同步调 tool.onboard_profile；超时 120s。"""
```

**请求/响应模型**：

```python
class OnboardingAnswer(BaseModel):
    question_id: str
    choice: str | list[str] | None = None  # open 题时为 None
    free_text: str | None = None           # single/multi 时一般为空

class OnboardingSubmitRequest(BaseModel):
    student_id: str
    answers: list[OnboardingAnswer]

class OnboardingSubmitResponse(BaseModel):
    dimensions: dict[str, float]  # 6 个短 key
    reasoning: str
    snapshot_id: int
```

**错误码**：

| 情况 | HTTP | body |
|------|------|------|
| 正常 | 200 | `{dimensions, reasoning, snapshot_id}` |
| 已 onboarding | 409 | `{error: "already_onboarded"}` |
| LLM 失败 | 500 | `{error: "onboard_failed"}` |
| 超时 | 504 | `{error: "onboard_timeout"}` |
| answers 数量不匹配（≠ 题数） | 400 | `{error: "answers_mismatch"}` |

### 2.4 修改 `backend/src/selflearn/mcp_server/server.py`

注册 tool：

```python
from selflearn.mcp_server.tools.onboard_profile import onboard_profile

# 在现有 tool registry 列表中追加：
registry.register(onboard_profile)
```

### 2.5 修改 `backend/src/selflearn/main.py`

挂路由：

```python
from selflearn.gateway.routes.onboarding import router as onboarding_router

app.include_router(onboarding_router)
```

---

## 3. 前端组件（2 个新文件 + 1 处修改）

### 3.1 `frontend/src/api/onboarding.ts`

```typescript
export interface QuestionOption {
  id: string;
  label: string;
}
export interface Question {
  id: string;
  dimension_hint?: string;
  type: 'single' | 'multi' | 'open';
  prompt: string;
  options?: QuestionOption[];
  placeholder?: string;
}
export interface OnboardingAnswer {
  question_id: string;
  choice?: string | string[];
  free_text?: string;
}
export interface OnboardingSubmitResponse {
  dimensions: Record<string, number>;
  reasoning: string;
  snapshot_id: number;
}

export async function fetchOnboardingQuestions(): Promise<Question[]>
export async function submitOnboarding(
  studentId: string,
  answers: OnboardingAnswer[]
): Promise<OnboardingSubmitResponse>
```

### 3.2 `frontend/src/components/Onboarding.tsx`

**Props**：

```typescript
interface Props {
  studentId: string;
  onDone: (dimensions: Record<string, number>) => void;
}
```

**内部状态机**：

```
loading ──questions ok──▶ answering(qIdx 0..N-1) ──submit──▶ submitting
                                                       │
                                                       ├─success──▶ done
                                                       └─error────▶ answering(qIdx=N-1, 显示错误条)
```

**布局**：
- 全屏 fixed overlay（`position: fixed; inset: 0; background: #FBF7EC`）
- 顶部进度：`问题 {qIdx+1} / {N}` + 进度条
- 题干区域：`<h2>` 样式（Notion Serif 风格）
- 选项区域：
  - single：4 个垂直 radio 卡片（hover 高亮 `background: #F0EBDF`）
  - multi：4 个 checkbox 卡片
  - open：`<textarea>` + placeholder
- 底部按钮：`上一题` / `下一题`（最后一题变 `提交`）
- submitting：按钮变 spinner + "AI 正在评估你的回答..."
- 错误条：`<div style={{color: '#BC4749'}}>` + 重试按钮

**关键交互**：
- 第 1 题 `上一题` 禁用
- 最后一题必填（single 必选一个 / open 必填 ≥ 10 字）才能提交
- multi 题允许 0 个选择（视为跳过）
- `Esc` 不关闭（无 cancel）
- 答过的题可点进度条回看（但不能改答案，避免脏状态）

### 3.3 修改 `frontend/src/App.tsx`

**添加守卫**：

```typescript
import { useProfile } from './api/profile';
import { Onboarding } from './components/Onboarding';
import { isProfileInitialized } from './utils/profile';

function App() {
  const { studentId } = useSession();
  const { data: profile, isLoading, refetch } = useProfile(studentId);
  
  if (isLoading) return <LoadingScreen />;
  
  if (!isProfileInitialized(profile?.dimensions)) {
    return (
      <Onboarding
        studentId={studentId}
        onDone={() => refetch()}
      />
    );
  }
  
  return <MainApp />;
}
```

**新增工具函数** `frontend/src/utils/profile.ts`：

```typescript
export function isProfileInitialized(
  dims?: Record<string, number> | null
): boolean {
  if (!dims) return false;
  const SHORT_KEYS = ['kb','vp','as','ge','ept','fd'] as const;
  // 6 维全 0.5 → 未初始化
  return SHORT_KEYS.every((k) => Math.abs((dims[k] ?? 0.5) - 0.5) > 1e-6);
}
```

---

## 4. 数据流

### 4.1 首次进站流程

```
1. App 启动 → useProfile fetch
2. 后端 /api/profile/{student_id} → dimensions: null（profile 行不存在）
3. isProfileInitialized(null) → false
4. App 渲染 <Onboarding>
5. Onboarding useEffect → fetchOnboardingQuestions → 渲染第 1 题
6. 用户答完 8 题 → submitOnboarding POST /api/onboarding/submit
7. 后端 tool.onboard_profile:
   a. get_profile → dimensions: null（通过）
   b. agent.run("skill.profile.onboard") → LLM 返回 6 分
   c. clamp + 缺维度补 0.5
   d. create_profile upsert
   e. ProfileSnapshot insert (trigger="onboarding")
8. 路由返回 {dimensions, reasoning, snapshot_id}
9. Onboarding onDone → App refetch → Profile 现在有 6 维 → 渲染 MainApp
```

### 4.2 重复触发防护

```
- 路由层 /api/onboarding/submit 进入后 → tool.onboard_profile.get_profile
  - 若 dimensions 非空且不全 0.5 → {ok: false, error: "already_onboarded"}
  - 路由层 409
- 前端守卫 isProfileInitialized 返回 true → 不渲染 Onboarding
- 即使用户手动刷新 → 守卫再次拦截 → 看不到 onboarding
```

---

## 5. 错误处理（汇总）

| 失败点 | 检测位置 | 处理 | 用户体验 |
|--------|---------|------|---------|
| 题库 JSON 不存在/格式错 | 路由启动 | 启动时加载失败 → log error | 运维事故 |
| 用户重复进 onboarding | tool.onboard_profile.get_profile | 返回 `{ok: False, error: "already_onboarded"}` → 路由 409 | 前端守卫本就拦截，到不了 |
| answers 数量 ≠ 题数 | 路由 Pydantic 校验 | 400 `answers_mismatch` | 红色 toast |
| LLM 返回非 JSON | tool.onboard_profile agent.run | AppError → 路由 500 | 红色错误条 + "重新提交" |
| LLM 维度缺失 | tool.onboard_profile | 补 0.5 + log warn | 用户无感 |
| LLM 分数越界 | tool.onboard_profile | clamp [0,1] | 用户无感 |
| HTTP 超时 | 路由层（>120s） | 504 | "评估超时，请重试" |
| DB 写失败 | tool.onboard_profile create_profile | AppError → 路由 500 | "保存失败，请重试" |

---

## 6. 测试策略

### 6.1 后端（pytest）

| 文件 | 覆盖 |
|------|------|
| `tests/unit/test_onboarding_questions_json.py` | JSON 结构契约（8 题、6 维覆盖、最后 1 题 open） |
| `tests/unit/test_onboard_profile_tool.py` | tool.onboard_profile 主路径（mock LLM）+ clamp + 缺维度 + lint 失败 |
| `tests/unit/test_onboarding_route.py` | GET/POST 路由 + 409 + 400 + 500 |

### 6.2 前端（vitest）

| 文件 | 覆盖 |
|------|------|
| `frontend/src/components/__tests__/Onboarding.test.tsx` | 渲染 8 题 + 状态机 + submit + error 重试 |
| `frontend/src/utils/__tests__/profile.test.ts` | isProfileInitialized 三种 case（null/全 0.5/已填） |

### 6.3 端到端

- 更新 `backend/scripts/smoke_mvp.sh`：删 KEEP_STUDENT 的 Profile → 启动前端 → 走完 onboarding → 看到雷达图

---

## 7. Task 划分（实施计划会展开）

| Task | 范围 | 文件 |
|------|------|------|
| Task 1 | 题库 JSON + skill markdown + JSON 契约测试 | 2 新 + 1 测 |
| Task 2 | `tool.onboard_profile` + MCP server 注册 + 单测 | 1 新 + 1 改 + 1 测 |
| Task 3 | 路由 + 单测 | 1 新 + 1 测 |
| Task 4 | 前端 api + 组件 + 单测 | 2 新 + 1 测 |
| Task 5 | 守卫 + smoke 更新 + e2e | 1 改 + 1 新 + 1 改 |

---

## 8. 风险与权衡

| 风险 | 缓解 |
|------|------|
| LLM 单 chat 评分不稳定 | JSON schema 强制 + clamp 兜底 + lint 重试（已有 max_retries 机制） |
| 用户答得敷衍 | 单选题强制必答；开放题 ≥ 10 字（前端校验） |
| 题库过时 | dimension_hint 是软提示，LLM 自评为主 |
| 重复 onboarding 覆盖学习成果 | 路由层 409 + 前端守卫双保险 |
| 与 director `_compute_deltas` 冲突 | onboarding 写 dimensions 是 cold start；后续 director 只发 `kb`/`as` delta 在 onboarding 基础上叠加 — 语义清晰 |
| snapshot 字段名是 `profile` 不是 `dimensions`（历史遗留） | tool.onboard_profile 写 snapshot 时显式构造 `profile=dimensions`（避免误用字段名） |

---

## 9. 不做（YAGNI）

- 不做"重新评估"入口（用户原话选首次必填）
- 不做 LLM 动态出题（选预制题库）
- 不做题目权重表（选 LLM 单评）
- 不做"AI 画像解释"的多轮追问
- 不做 onboarding 历史时间轴 UI
- 不做多语言（中文 only，沿用现有约定）
- 不动 envelope 异步总线（onboarding 同步）
- 不动 Profile / ProfileSnapshot schema
- 不引入新维度名称
