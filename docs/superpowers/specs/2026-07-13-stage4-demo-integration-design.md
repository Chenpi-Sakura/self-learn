# Stage 4 — Demo 对接与学习闭环 — 设计文档

> **For agentic workers:** 本 spec 是 Stage 4 的"做什么、怎么做、不做什么"的权威来源。配套实施计划见 `docs/superpowers/plans/2026-07-13-stage4-demo-integration.md`（Plan 阶段产出文件，可能与此处 slug 略有差异）。
>
> **继承文档**（继续生效，不重写、不修订）：
> - v4 详细设计规格说明书（`docs/个性化学习多智能体系统详细设计规格说明书-v4.md`）
> - Stage 2 spec（`docs/superpowers/specs/2026-07-11-stage2-backend-foundation-design.md`）
> - Stage 3 spec（`docs/superpowers/specs/2026-07-12-stage3-business-mvp-design.md`）
> - Notion×UKIYO 衬线 demo 设计（`docs/superpowers/specs/2026-07-11-notion-ukiyo-serif-demo-design.md`）
> - 产品需求修订说明（`docs/产品需求修订说明.md`）
> - 项目记忆：`[[no-auth-no-login]]`（鉴权 0 实现）

| 文档版本 | 日期 | 说明 |
|---|---|---|
| V1.0 | 2026-07-13 | 初稿。Stage 3 完成 → Stage 4 = **前后端对接 + 学习闭环 3 点补丁 + AOP Hook 观测链**。**Demo 级目标**：跑通 Profile→关卡→答题→画像动画→画像演变核心闭环，不为生产化长期运行设计。 |

---

## 0. 编写目的与读法

本文档回答四个问题：

1. **Stage 4 交付什么**：前端 `frontend/`（原 demo-serif 重命名）与 Stage 3 后端对接；后端追加 Profile 动态更新 / 难度梯度 / 画像演变 三个学习闭环点；新增 AOP Hook 观测链
2. **用什么技术栈**：在 Stage 2/3 基础上新增 react-rnd（窗口拖拽）、OpenAI 兼容 LLM、AOP 装饰器 Hook
3. **观测链路怎么走**：3 个横切点（Envelope / LLM / progress_publish）→ RingBuffer → `/debug/state` JSON（仅开发期）
4. **怎么验证**：`scripts/smoke_mvp.sh`（Stage 3 已建）继续作为后端闭环门；前端新增 `frontend/e2e/smoke.spec.ts`（Playwright）跑通"打开页面 → 进关卡 → 答题 → 看到画像动"。

**读法建议**：
- § 1 范围与不在范围内（先看）
- § 2 决策表（核心，5 项新决策 + Stage 2/3 继承）
- § 3 架构与目录（实现依据）
- § 4 API 契约（前端可直接照此写代码）
- § 5 学习闭环三点补丁（后端增量）
- § 6 AOP Hook 观测链
- § 7 前端结构与窗口
- § 8 错误 / 测试 / 验收

---

## 1. 范围与不在范围内

### 1.1 Stage 4 范围内（必交付）

| 项 | 说明 |
|---|---|
| **目录重命名** | `demo-serif/` → `frontend/`（正式承担前端项目角色），更新引用 |
| **5 个 API 缺口补全** | `GET /api/profile/{student_id}` / `GET /api/map/{student_id}/nodes` / `GET /api/level/{level_id}` / SSE `completed` 事件 `profile` 字段 / SSE `completed` 事件 `level_id` 字段 |
| **学习闭环 3 点补丁** | Profile 动态更新 / 难度梯度 / 画像演变入库 |
| **1 张新表** | `profile_snapshots`（Alembic 迁移） |
| **AOP Hook 观测链** | 3 个横切点装饰器 / RingBuffer / `/debug/state` 路由 |
| **前端 4 段主线** | `api/` SSE 订阅 / `panes/` 3 窗口可拖拽 / `desk/` 桌面布局 / 画像动画 |
| **Playwright e2e** | `frontend/e2e/smoke.spec.ts` 跑通核心闭环 |

### 1.2 Stage 4 范围外（推到 Stage 5+）

| 项 | 推到 |
|---|---|
| 鉴权 / 登录 / Token | 永远不做（项目级硬约束） |
| 限速 / 熔断 / 多 provider fallback | Stage 5+ |
| TTS / ASR（讯飞） | Stage 5+ |
| 9 窗口全部实现 | 讲义/习题/AI 对话/藏宝图 本期；其余 5 个（代码实验室 / 笔记 / 思维导图 / 资源库 / 仪表盘）推 Stage 5+ |
| 向量库 / Qdrant 接入 | Stage 5+ |
| 自适应难度 UI（精通/探索模式切换） | v4 spec § 3 保留，Stage 4 仅后端计算、不做 UI |
| 自传资源（OCR / 拖拽绑定） | Stage 5+ |
| 评测模块 / 仪表盘 / 画像演变图表完整版 | Stage 4 仅 1 个迷你折线图，其他推 Stage 5+ |
| k8s / Helm / 生产化部署 | Stage 5+ |

### 1.3 项目级硬约束（继承自 Stage 3 § 1.3 + 全局 `[[no-auth-no-login]]`）

> **整个项目（所有阶段）都不需要登录 / 鉴权 / 会话 / Token / OAuth / JWT 任何形式。**

落地规则：
- 任何阶段、任何 task、任何 spec / plan / 文档中出现鉴权 / 登录 / 会话 / Token / JWT / OAuth / 账号 / 注册 / 注销 / 邮箱密码 / refresh token / `Depends(get_current_user)` / `auth.py` 等概念，**一律删除**
- 学生以**业务字段 `student_id`** 标识，请求体或路径直接传入
- `students` 表保留为业务主数据表，但不与任何 token 关联

---

## 2. 技术决策表（继承 Stage 2/3 + 新增 5 项）

### 2.1 继承自 Stage 2/3 的 14 项决策（继续生效，不重列）

完整 14 项见 Stage 3 spec § 2.1 + § 2.2。本 spec 仅强调 3 项对 Stage 4 强相关的：
- **决策 #3**：LLM 主路径 = **OpenAI 兼容**（DeepSeek / 通义千问）—— Stage 4 默认使用
- **决策 #5**：鉴权 = **不做**（项目级硬约束）
- **决策 #14**：状态走 PG（事务+查询）、热数据走 Redis（缓存 + Stream）—— Stage 4 数据布局沿用

### 2.2 Stage 4 新增的 5 项决策

| # | 决策点 | 决策 | 备选 | 决定理由 |
|---|---|---|---|---|
| 15 | **前端目录** | `demo-serif/` → 重命名为 `frontend/`，正式承担前端项目角色 | 保持 `demo-serif` 名 / 另起 `web/` | 用户已确认；语义清晰；`demo-serif` 原意为"视觉欣赏"，与"接后端"的真实职能不符 |
| 16 | **窗口拖拽库** | `react-rnd`（已广泛使用，TypeScript 一等支持） | react-mosaic / rc-resizable / 自研 | 零研发成本；3 个核心窗口规模足够；不引入额外概念 |
| 17 | **LLM 默认 Provider** | OpenAI 兼容接口（DeepSeek / 通义千问 / 自部署皆可） | 讯飞星火 / Mock | 用户已确认；Stage 3 OpenAI 适配器已实装可直接用；演示效果稳定 |
| 18 | **AOP Hook 注入方式** | **装饰器包装原函数**（`@hook("kind")` 包裹实现，业务函数保持原签名） | monkey-patch / 中间件 / 上下文管理器 / 切面框架 | 零业务代码改动；保留原函数可单元测试；可观测层独立可禁用 |
| 19 | **Hook 暴露形式** | RingBuffer（最近 500 条，进程内 deque）+ `/debug/state` GET 路由（仅 `settings.debug=True` 时挂载） | 写本地文件 / 推 Redis Stream / 调试页面 | 仅供开发期用；零外部依赖；MCP `list_network_requests` 可直接看 |

---

## 3. 架构与目录

### 3.1 进程拓扑（沿用 Stage 3，不变）

```
docker-compose.yml（继承）
├── postgres          # PostgreSQL 16
├── redis             # Redis 7（含 Stream 类型）
├── rabbitmq          # RabbitMQ 3.x
├── jaeger            # Jaeger all-in-one（Stage 4 继续开启，但不依赖）
├── gateway           # FastAPI gateway（REST + SSE）—— Stage 4 扩 5 端点
└── worker            # 消费进程（5 个 Agent 全部在内部）—— Stage 4 3 处微调
```

**新增**：`frontend/` 是独立 Vite + React 项目，**不**进 docker compose，由开发者本地 `npm run dev` 启动。

### 3.2 backend/ 目录变更（仅追加，不重写）

```
backend/
├── src/selflearn/
│   ├── observability/                   # 新增子模块
│   │   ├── __init__.py
│   │   ├── hooks.py                    # HookBus 单例 + 装饰器
│   │   ├── decorators.py               # @hook("kind") 实现
│   │   └── routes.py                   # /debug/state 路由（仅 debug=True 挂载）
│   ├── domain/
│   │   └── profile_snapshot.py         # 新增：ProfileSnapshot ORM
│   ├── gateway/routes/
│   │   ├── profile.py                  # 修改：加 GET /api/profile/{student_id}
│   │   ├── map.py                      # 修改：加 GET /api/map/{student_id}/nodes
│   │   └── level.py                    # 修改：加 GET /api/level/{level_id}
│   └── agents/builtin/
│       ├── profile_agent.py            # 修改：run() 末 publish 塞 profile 字段
│       └── director_agent.py           # 修改：run() 末 publish 塞 level_id 字段
├── migrations/versions/
│   └── <new>_stage4_profile_snapshots.py  # 新增：1 张表迁移
├── tests/
│   ├── unit/
│   │   ├── test_aop_hooks.py           # 新增
│   │   ├── test_profile_update.py      # 新增
│   │   ├── test_difficulty_gradient.py # 新增
│   │   └── test_profile_snapshot.py    # 新增
│   └── integration/
│       └── test_api_gaps.py            # 新增：5 个 API 缺口
```

### 3.3 frontend/ 目录变更（重命名 + 新增）

```
frontend/                                  # 原 demo-serif/，重命名
├── public/fonts/                          # 继承 FlyFlowerSong + HedvigLettersSerif
├── src/
│   ├── api/                               # 新增：与后端 REST + SSE 对接
│   │   ├── client.ts                      # fetch 封装
│   │   ├── profile.ts                     # build / getProfile
│   │   ├── map.ts                         # generate / getNodes
│   │   ├── level.ts                       # start / getLevel / submit
│   │   └── sse.ts                         # subscribeProgress(traceId, onEvent) 通用 SSE 订阅
│   ├── panes/                             # 新增：3 个核心窗口（react-rnd）
│   │   ├── LecturePane.tsx                # 讲义窗口（Markdown 渲染）
│   │   ├── ExercisePane.tsx               # 习题窗口（表单 + 提交）
│   │   └── ChatPane.tsx                   # AI 对话窗口
│   ├── desk/                              # 改：主桌面布局（左 1/3 + 右 2/3）
│   │   ├── Desktop.tsx                    # 主容器
│   │   ├── MapPanel.tsx                   # 左侧上部藏宝图
│   │   ├── ProfilePanel.tsx               # 左侧下部画像雷达图 + 演变迷你图
│   │   └── CalendarPanel.tsx              # 右侧毛玻璃日历（v4 § 1）
│   ├── store/                             # 新增：Zustand store
│   │   ├── profile.ts                     # 画像 + 演变历史
│   │   └── session.ts                     # student_id + trace 状态
│   └── ...原 demo-serif 内容保留（styles/ fonts.css 等）
├── e2e/                                   # 新增：Playwright
│   └── smoke.spec.ts                      # 跑通核心闭环
├── package.json                           # 增：react-rnd / zustand / @playwright/test
├── vite.config.ts
└── README.md                              # 改：写明"如何启动对接"
```

---

## 4. API 契约（前端可直接照此写代码）

### 4.1 Profile 链路

| Method | Path | 入参 | 出参 (JSON) | 用途 |
|---|---|---|---|---|
| POST | `/api/profile/build` | `{student_id: UUID, dimensions: {kb:0.6,...}, tags: ["smoke"]}` | `{trace_id: "abc-123"}` (202) | 触发画像构建 |
| GET | `/api/profile/init/{trace_id}/stream` | — | **SSE 流** | 实时进度 |
| GET | `/api/profile/init/{trace_id}/status` | — | `{trace_id, status, reply}` | 轮询 fallback |
| **POST** | `/api/profile/init` | `{student_id, topic}` | `{trace_id}` (202) | Stage 2 兼容入口（保留） |
| **GET** | **`/api/profile/{student_id}`** | — | `{student_id, dimensions: {kb, vp, as, ge, ept, fd}, tags: [...], snapshot_count: int}` | **新增**：启动时加载画像 |

**`GET /api/profile/{student_id}` 出参示例**：
```json
{
  "student_id": "550e8400-e29b-41d4-a716-446655440000",
  "dimensions": {
    "kb": 0.65, "vp": 0.50, "as": 0.72, "ge": 0.40, "ept": 0.55, "fd": 0.50
  },
  "tags": ["smoke", "frontend-demo"],
  "snapshot_count": 3,
  "last_updated_at": "2026-07-13T08:42:11Z"
}
```

### 4.2 Map 链路

| Method | Path | 入参 | 出参 (JSON) | 用途 |
|---|---|---|---|---|
| POST | `/api/map/generate` | `{student_id: UUID}` | `{trace_id}` (202) | 生成藏宝图 |
| **GET** | **`/api/map/{student_id}/nodes`** | — | `{nodes: [{node_id, kp_id, title, position: {x, y}, status: "available"\|"in_progress"\|"completed", parent_id}, ...]}` | **新增**：加载节点列表 |

### 4.3 Level 链路

| Method | Path | 入参 | 出参 (JSON) | 用途 |
|---|---|---|---|---|
| POST | `/api/level/start` | `{student_id: UUID}` | `{trace_id}` (202) | 启动关卡 |
| GET | `/api/level/{level_id}/stream?trace_id=xxx` | — | **SSE 流** | 关卡进度 |
| **GET** | **`/api/level/{level_id}`** | — | `{level_id, node_id, status, exercises: [{exercise_id, prompt, options, type}]}` | **新增**：加载关卡详情 |
| POST | `/api/level/{level_id}/submit` | `{answers: {exercise_id: answer}}` | `{status:"submitted", score:0.85}` | 提交答案 |

### 4.4 SSE 事件统一格式

每个事件两行：
```
event: <event_name>
data: <json_string>
```

事件类型与字段：

| event_name | data 字段 | 触发时机 | 备注 |
|---|---|---|---|
| `progress` | `{stage: "profile"\|"plan"\|"director"\|"exercise"\|"review", status: "running"\|"completed", payload: any}` | 每阶段发布进度 | 持续推送 |
| `completed` | `{status: "completed", payload: any}` | 最终成功 | **Stage 4 增强**：`payload` 内含 `profile`（Profile 完成时）或 `level_id` + `exercise_ids`（Director 完成时） |
| `error` | `{status: "failed", payload: {code: string, message: string}}` | 最终失败 | SSE 端点收到后关闭连接 |

### 4.5 完整 TypeScript 类型（前端可直接复制）

```typescript
// frontend/src/api/types.ts
export type Stage = "profile" | "plan" | "director" | "exercise" | "review";
export type ProfileDimensions = {
  kb: number; vp: number; as: number; ge: number; ept: number; fd: number;
};

export interface SSEEvent {
  event: "progress" | "completed" | "error";
  data:
    | { stage: Stage; status: string; payload: Record<string, unknown> }
    | { status: "completed"; payload: Record<string, unknown> }
    | { status: "failed"; payload: { code: string; message: string } };
}

export interface ProfileResponse {
  student_id: string;
  dimensions: ProfileDimensions;
  tags: string[];
  snapshot_count: number;
  last_updated_at: string;
}

export interface MapNode {
  node_id: string;
  kp_id: string;
  title: string;
  position: { x: number; y: number };
  status: "available" | "in_progress" | "completed" | "locked";
  parent_id: string | null;
}

export interface LevelDetail {
  level_id: string;
  node_id: string;
  status: "available" | "in_progress" | "completed";
  exercises: Array<{
    exercise_id: string;
    prompt: string;
    options?: string[];
    type: "single_choice" | "multi_choice" | "short_answer";
  }>;
}
```

---

## 5. 学习闭环三点补丁（后端增量）

### 5.1 Profile 动态更新

**位置**：`backend/src/selflearn/agents/builtin/profile_agent.py` 末尾追加（不重写）

```python
# profile_agent.py — run() 方法末尾
async def run(self, env: Envelope) -> Envelope:
    # ... 既有逻辑：读 Skill / 调 LLM / 解析 ...
    profile = {...}  # 已有
    student_id = env.payload["student_id"]

    # Stage 4 追加：写 profile 到 DB（如果已存在则合并 tags + 取最大 dimensions 值）
    await profile_repo.upsert(student_id, profile)

    # Stage 4 追加：发布带 profile 字段的 completed 事件
    await progress_publish(env.trace_id, ProgressEvent(
        stage=Stage.PROFILE,
        status="completed",
        payload={"profile": profile},  # ← 新增：前端可直接拿来动画
    ))
    return env
```

**触发时机**：每次关卡完成后由 DirectorAgent 在 `director_agent.py` 末调用 `update_profile(student_id, completion)`：
```python
# director_agent.py — 关卡提交回调
def _post_completion_update(self, student_id: str, completion: LevelCompletion) -> None:
    """Stage 4 增量：根据本次答题微调画像 + 写快照。"""
    score_ratio = completion.score / max(1.0, sum_ex_max_score)
    delta_kb = 0.05 if score_ratio >= 0.8 else (-0.03 if score_ratio < 0.5 else 0.0)
    delta_as = 0.02 if score_ratio >= 0.7 else -0.02
    new_dims = profile_repo.apply_delta(student_id, {"kb": delta_kb, "as": delta_as})
    profile_snapshots_repo.create(student_id, new_dims, trigger="level_completed")
```

### 5.2 难度梯度

**位置**：`backend/src/selflearn/agents/builtin/exercise_agent.py` 入口追加

```python
# exercise_agent.py — run() 入口
async def run(self, env: Envelope) -> Envelope:
    student_id = env.payload["student_id"]
    # Stage 4 追加：根据最近 3 次关卡得分映射难度
    recent_scores = level_repo.recent_scores(student_id, limit=3)
    avg_score = sum(recent_scores) / max(1, len(recent_scores))
    difficulty = "easy" if avg_score < 0.5 else ("medium" if avg_score < 0.8 else "hard")

    # ... 既有逻辑：将 difficulty 注入 LLM prompt ...
```

**实现方式**：在 Skill markdown（`docs/skills/skill.exercise.generate.md`）的 `body` 里加入一行：
> 根据 `difficulty ∈ {easy, medium, hard}` 调整题目复杂度：easy 偏概念辨析、medium 偏应用、hard 偏综合。

Skill loader 已支持（Stage 3 § 3.3 `skills/library.py`），无需改 Skill 加载机制。

### 5.3 画像演变入库

**位置**：第 5.1 节 `_post_completion_update` 已包含 `profile_snapshots_repo.create(...)`

**新表 DDL**（Alembic 迁移 `stage4_profile_snapshots`）：

```sql
CREATE TABLE profile_snapshots (
  id BIGSERIAL PRIMARY KEY,
  student_id UUID NOT NULL,
  profile JSONB NOT NULL,
  trigger VARCHAR(32) NOT NULL,    -- 'level_completed' | 'manual_edit' | 'build'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_profile_snapshots_student ON profile_snapshots (student_id, created_at DESC);
```

**查询接口**（前端用）：
- 集成进 `GET /api/profile/{student_id}` 的 `snapshot_count` 字段（已在 § 4.1）
- 详细演变历史走 `GET /api/profile/{student_id}/history?limit=30`（**Stage 4 新增**，返回最近 N 条快照）

---

## 6. AOP Hook 观测链

### 6.1 设计原则

- **零侵入**：3 个横切点装饰器包裹原函数，业务代码保持原签名
- **进程内**：RingBuffer（`collections.deque(maxlen=500)`）仅本进程；不跨进程聚合
- **仅 debug 期挂载**：`/debug/state` 路由仅 `settings.debug=True` 时注册

### 6.2 三横切点

| # | 包裹目标 | 装饰器 | 抓取字段 | 注入方式 |
|---|---|---|---|---|
| 1 | `publish_envelope` / `consume_envelope` | `@hook("envelope.publish")` / `@hook("envelope.consume")` | `trace_id / target.id / action / sender.type` | 装饰 `infra/bus.py` 中的 `publish_envelope` 函数 |
| 2 | `BaseLLMAdapter.chat` | `@hook("llm.call")` | `model / n_msgs / latency_ms / n_chunks / last_delta / last_reasoning` | 装饰 `llm/base.py` 中的 `chat` 抽象方法（**用 `__init_subclass__` 钩子自动给所有 adapter 加装**） |
| 3 | `progress_publish` | `@hook("progress.publish")` | `trace_id / stage / status / payload_size` | 装饰 `progress/stream.py` 中的 `progress_publish` 函数 |

### 6.3 HookBus 实现

```python
# backend/src/selflearn/observability/hooks.py
from __future__ import annotations
import collections
import threading
import time
from typing import Any

class HookBus:
    def __init__(self, maxlen: int = 500) -> None:
        self._ring: collections.deque[dict[str, Any]] = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def emit(self, kind: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._ring.append({
                "ts": time.time(),
                "kind": kind,
                **payload,
            })

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._ring)

    def clear(self) -> None:
        with self._lock:
            self._ring.clear()

hook_bus = HookBus()
```

### 6.4 装饰器实现

```python
# backend/src/selflearn/observability/decorators.py
from __future__ import annotations
import functools
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, overload

from selflearn.observability.hooks import hook_bus

P = ParamSpec("P")
R = TypeVar("R")


def hook(kind: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """无侵入装饰器：包一层 try/except 保证观测不影响业务。"""
    def deco(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
            t0 = time.perf_counter()
            try:
                result = await fn(*args, **kwargs)
                hook_bus.emit(kind, {"status": "ok", "latency_ms": int((time.perf_counter()-t0)*1000)})
                return result
            except Exception as e:
                hook_bus.emit(kind, {"status": "error", "error": str(e), "latency_ms": int((time.perf_counter()-t0)*1000)})
                raise
        return wrap
    return deco


# 流式版本（LLM chat）
def hook_stream(kind: str) -> Callable[..., Callable[..., AsyncIterator[Any]]]:
    def deco(fn: Callable[P, AsyncIterator[R]]) -> Callable[P, AsyncIterator[R]]:
        @functools.wraps(fn)
        async def wrap(*args: P.args, **kwargs: P.kwargs) -> AsyncIterator[R]:
            t0 = time.perf_counter()
            n = 0
            try:
                async for chunk in fn(*args, **kwargs):
                    n += 1
                    yield chunk
                hook_bus.emit(kind, {"status": "ok", "latency_ms": int((time.perf_counter()-t0)*1000), "n_chunks": n})
            except Exception as e:
                hook_bus.emit(kind, {"status": "error", "error": str(e)})
                raise
        return wrap
    return deco
```

### 6.5 暴露路由

```python
# backend/src/selflearn/observability/routes.py
from fastapi import APIRouter
from selflearn.observability.hooks import hook_bus

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/state")
async def state() -> dict:
    return {"events": hook_bus.snapshot()}
```

**挂载方式**（在 `gateway/app.py`）：
```python
from selflearn.config import get_settings
if get_settings().debug:
    from selflearn.observability.routes import router as debug_router
    app.include_router(debug_router)
```

### 6.6 我怎么看（MCP 使用方式）

调试时直接走 MCP 的 `list_network_requests` 看 `/debug/state` 调用，或在 Playwright / curl 调一次：
```bash
curl http://localhost:8000/debug/state | jq '.events[-20:]'
```
拿到最近 20 条事件，看到完整调用链。

---

## 7. 前端结构与窗口

### 7.1 启动入口

`frontend/src/main.tsx`：
1. 生成随机 `student_id`（首次访问时存 localStorage，后续复用）
2. 调 `GET /api/profile/{student_id}` 加载初始画像
3. 调 `GET /api/map/{student_id}/nodes` 加载藏宝图
4. 渲染 `<Desktop>` 主组件

### 7.2 主桌面布局（继承产品需求修订说明 § 1）

```
+--------------------------------------+--------------------------------------+
|  MapPanel (左 1/3 上)               |  CalendarPanel (右 2/3 毛玻璃)       |
|  - 节点列表 / 缩略图                 |  - 日历组件 / 今日计划                |
+--------------------------------------+                                      |
|  ProfilePanel (左 1/3 下)           |                                      |
|  - 雷达图 (6 维)                     |                                      |
|  - 演变迷你折线图                    |                                      |
+--------------------------------------+--------------------------------------+
| Dock: [讲义] [习题] [AI 对话] (可拖拽 react-rnd 窗口，从这里打开)            |
+---------------------------------------------------------------------------+
```

### 7.3 3 个可拖拽窗口

| 窗口 | 触发 | 内容来源 |
|---|---|---|
| `<LecturePane>` | 右键关卡节点 → "进入关卡" | `GET /api/level/{level_id}` 第一个 exercise 的 prompt + 关卡 metadata |
| `<ExercisePane>` | 与 LecturePane 联动打开 | 同上 exercises 列表（表单渲染） |
| `<ChatPane>` | Dock 点击 / 任意时刻可开 | 直连 LLM `/api/chat`（**Stage 4 新增** `/api/chat` POST 端点，转发到 OpenAI 兼容接口） |

**注**：3 窗口共享 Zustand store 里的 `current_level_id`，关闭其中任一不影响其余。

### 7.4 画像动画

```typescript
// frontend/src/desk/ProfilePanel.tsx
useEffect(() => {
  // 订阅 SSE：当前 trace 完成时收到 { payload: { profile } }
  const unsubscribe = subscribeProgress(traceId, (ev) => {
    if (ev.event === "completed" && ev.data.payload?.profile) {
      const newProfile = ev.data.payload.profile as ProfileDimensions;
      // 雷达图 0.5s 闪光 + 数值过渡动画（framer-motion 或纯 CSS transition）
      setProfile(newProfile);
    }
  });
  return unsubscribe;
}, [traceId]);
```

演变迷你折线图：`GET /api/profile/{student_id}/history?limit=10` → Recharts / Chart.js 简单折线。

---

## 8. 错误 / 测试 / 验收

### 8.1 错误处理

继承 Stage 3 § 6.1。Stage 4 新增：
- 前端 SSE 断连自动重试（指数退避，最多 3 次）
- 前端 5xx 显示 toast，不崩溃

### 8.2 测试矩阵

| 层 | 类型 | 工具 | 关键覆盖 |
|---|---|---|---|
| 后端单元 | `tests/unit/` | pytest + pytest-asyncio | `test_aop_hooks.py` / `test_profile_update.py` / `test_difficulty_gradient.py` / `test_profile_snapshot.py` |
| 后端集成 | `tests/integration/` | pytest + docker | `test_api_gaps.py`（5 个新端点） |
| 前端单元 | Vitest + @testing-library | — | SSE 订阅逻辑 / 画像动画触发 |
| 前端 e2e | Playwright | `frontend/e2e/smoke.spec.ts` | 打开页 → 进关卡 → 答题 → 看到画像动 |

### 8.3 质量门（每 Task 必跑）

- `uv run mypy src tests` → **0 errors**（继承 Stage 3 硬约束）
- `uv run pytest tests/unit -q` → 全绿
- `uv run pytest tests/integration -q` → 全绿（含 Stage 2 smoke 回归）
- `bash scripts/smoke_mvp.sh` → Stage 3 后端闭环仍通
- `cd frontend && npm run test:e2e` → Playwright 全绿

### 8.4 Stage 4 验收清单

1. ✅ `demo-serif/` 已重命名为 `frontend/`，引用已更新
2. ✅ 5 个 API 缺口全部存在并有集成测试：`GET /api/profile/{student_id}` / `GET /api/profile/{student_id}/history` / `GET /api/map/{student_id}/nodes` / `GET /api/level/{level_id}` / SSE completed 带 profile + level_id 字段
3. ✅ `profile_snapshots` 表已建，Alembic 迁移可回滚
4. ✅ AOP Hook 在 3 个横切点生效，`/debug/state` 可见完整事件流
5. ✅ 前端打开页面 → 看到藏宝图 + 画像雷达图 + 日历
6. ✅ 进入关卡 → 讲义 + 习题 + AI 对话 三窗口可拖拽
7. ✅ 答题提交后 → 画像雷达图 0.5s 闪光动画 + 演变迷你折线图新增一条
8. ✅ Playwright e2e 全绿
9. ✅ mypy 0 errors / 全部单测绿 / Stage 2 回归绿 / Stage 3 smoke 绿
10. ✅ tag `stage4-complete` 已打，远端已同步

---

## 9. 与 v4 / Stage 2 / Stage 3 的一致性

- **v4 spec**：完整保留；本 spec 仅说明 Demo 阶段实现取舍，不修订 v4
- **Stage 2**：后端基座 8 项决策 + 消息总线 + SkillBasedScheduler 全部沿用
- **Stage 3**：5 Agent + 6 业务表 + SSE 真流 + LLM reasoning 全部沿用；本 spec 仅追加 3 学习闭环点 + 1 张新表
- **demo-serif 设计**：Notion×UKIYO 配色 + 衬线字体 + 桌面布局全部沿用，重命名后承担前端项目角色

---

## 附录 A · Stage 4 与 Stage 3 工作量对比

| 维度 | Stage 3 (实装) | Stage 4 (本 spec) |
|---|---|---|
| 新增代码行估计 | ~3500 行（5 Agent + 6 表 + SSE + Skill + Tool） | ~1500 行（5 端点 + 1 表 + AOP + frontend 4 段） |
| 新增表 | 6 | 1 |
| 新增 API 端点 | 6 (profile build/init/status + map gen + level start/submit) | 5 (profile get / map nodes / level get / profile history / chat) |
| Agent 代码改动 | 5 个新文件 | 2 个微调（profile_agent + director_agent 末 publish 字段） |
| 前端代码 | 0（demo-serif 静态） | ~1200 行（api/ panes/ desk/ e2e/） |
| 测试 | unit 58 / integration 3 / Stage 2 1 | unit +18 / integration +5 / Playwright +1 |

---

## 附录 B · 不在 Stage 4 范围的明确清单（防止 scope creep）

- ❌ 任何鉴权 / 登录 / Token 代码（违反项目级硬约束）
- ❌ 讯飞 ASR/TTS（Stage 5+）
- ❌ 限速 / 熔断 / 多 provider 路由（Stage 5+）
- ❌ 9 窗口全部实现（仅 3 窗口 + 藏宝图）
- ❌ 自适应难度 UI 切换（仅后端计算）
- ❌ 自传资源 / OCR / 拖拽绑定（Stage 5+）
- ❌ 评测模块 / 完整仪表盘 / 画像演变图表完整版（仅迷你折线）
- ❌ 向量库 / Qdrant（Stage 5+）
- ❌ k8s / Helm / 生产化部署（Stage 5+）

---

**Self-Review Checklist**：
- [x] Spec coverage：v4 § 4.2（REST 端点）→ § 4；Stage 3 § 3 → § 5；产品需求说明 § 1 → § 7.2
- [x] Placeholder scan：无 TBD/TODO/"implement later"
- [x] Type consistency：Stage / SSEEvent / ProfileDimensions 与 Stage 3 `progress/stages.py` 一致
- [x] 项目级硬约束：明确声明不引入鉴权（§ 1.3）
- [x] 与 v4 spec 一致：仅声明范围取舍，不修订 v4 正文