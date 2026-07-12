# Stage 3 — 核心业务 MVP — 设计文档

> **For agentic workers:** 本 spec 是 Stage 3 的"做什么、怎么做、不做什么"的权威来源。配套实施计划见 `docs/superpowers/plans/2026-07-12-stage3-business-mvp.md`（Plan 阶段产出文件，可能与此处 slug 略有差异）。
>
> 配套文档：
> - Stage 2 spec：`docs/superpowers/specs/2026-07-11-stage2-backend-foundation-design.md`（所有 Stage 2 决策与基座约束继续生效）
> - 项目记忆：`[[no-auth-no-login]]`（鉴权 0 实现）
>
> **修订记录：**
> - V1.0 (2026-07-12) — 初稿
> - **V1.1 (2026-07-12) — Patch：4 项工程漏洞修复**
>   - last_id 由 `"$"` 改为 `"0-0"`（消除"前端建连前已写入事件"的竞态）
>   - `AGENT_TIMEOUT` 由 30s 放宽到 **120s**（5 阶段同步叠加 + 思考模式慢调用）
>   - 全文档去除 `XREAD GROUP`，统一改用 **裸 `XREAD`**（不需要 consumer group / XACK）
>   - `DirectorAgent.run` 加 **try/except 兜底**，失败时 `progress_publish(stage=FAILED)` 后抛 AppError，避免 SSE 端点死等
> - **V1.1 — Skill / MCP 重设**（基于 `superpowers:writing-skills` 视角）：
>   - Skill 重新定义：**Skill = 流程模板**（可复用步骤序列 + 提示词模板），**不是** Agent 注册中心
>   - 新增 § 9 MCP Tool 协议层：Agent 通过 `ToolRegistry` 接入 3 个 stub Tool（lint / fetch / store），不直连外部系统
> - **V1.2 (2026-07-12) — Skill 重设计哲学对齐**（基于 `superpowers:writing-skills` 完整解读）：
>   - Skill **彻底剥离装饰器模式** → 改为 **`docs/skills/<name>.md` markdown 文档**，启动时由 `skills/library.py` 读盘载入
>   - Skill 作为 **Agent 行为约束器**（prompt 注入 + 结构化校验），**不是**注册中心、不是 Python 装饰器
>   - § 9 重写为 **Skill ↔ Tool ↔ Agent 三者边界说明**，明确「Skill=说明书 / Tool=扳手 / Agent=执行者」
>   - Stage 2 SkillBasedScheduler 保留 gateway 入口薄壳，但 Skill 名字不再来自装饰器字符串
>   - 删除 `src/selflearn/skills/builtin/*.py` 装饰器代码 → 改 `src/selflearn/skills/library.py`（loader）+ `docs/skills/` Skill 文档

| 文档版本 | 修订日期 | 修订人 | 修订说明 |
| --- | --- | --- | --- |
| V1.0 | 2026-07-12 | 团队 | Stage 3 初稿。基于已交付的 Stage 2 后端基座，扩展到 5 个业务 Agent + Redis Stream 真流式 SSE + LLM 思考模式 + 6 张业务表。**MVP 范围——只跑通核心闭环，4 种关卡形式 / 评估模块 / TTS-ASR / 仪表盘 / 9 窗口真实内容均推到 Stage 4/5**。**项目级约束：完全不做鉴权 / 登录**（参见 [[no-auth-no-login]]）。 |
| V1.1 | 2026-07-12 | 团队 | Patch: (a) 4 项工程漏洞修复（last_id `0-0` / timeout 120s / 裸 XREAD / Director try-except）；(b) Skill 重设 = 流程模板（去装饰器 + 去全局注册表）；(c) 新增 § 9 MCP Tool 协议层（Tool / ToolRegistry / 3 个 stub Tool） |
| V1.2 | 2026-07-12 | 团队 | Skill 哲学对齐：完全去掉装饰器模式 → Skill = `docs/skills/<name>.md` markdown 文档，启动时 `skills/library.py` 读盘载入；§ 9 重写为 Skill ↔ Tool ↔ Agent 三者边界说明；删除 `skills/builtin/*.py` Python 装饰器代码 |

---

## 0. 编写目的与读法

本文档回答四个问题：

1. **Stage 3 交付什么**：5 个 Agent + Redis Stream 真流式 SSE + 思考模式抽象 + 6 张业务表 + 完整闭环 smoke
2. **用什么技术栈**：在 Stage 2 8 项决策基础上，新增 Redis Stream（事件流推送）+ LLM `reasoning_content` 字段
3. **消息怎么流**：单 Redis Stream 拓扑（worker 任意点 XADD → gateway SSE 裸 XREAD）
4. **怎么验证**：`scripts/smoke_mvp.sh` 端到端跑通 "profile → plan → director → exercise → review → submit"

**读法建议**：
- § 1 范围与不在范围内（先看）
- § 2 决策表（核心，8+3 项）
- § 3 架构与目录（实现依据）
- § 4 消息流与 SSE 推送（关键路径）
- § 5 数据模型（6 张新表 DDL + JSONB 脏检查陷阱）
- § 6 错误 / 测试 / 可观测性（质量门）
- § 7 验收（不可漏）
- § 8 与 Stage 2 / v4 详细设计文档的一致性

---

## 1. 范围与不在范围内

### 1.1 Stage 3 范围内（必交付）

| 项 | 说明 |
| --- | --- |
| **5 个业务 Agent** | `ProfileAgent` / `PlanAgent` / `DirectorAgent` / `ExerciseAgent` / `ReviewAgent` |
| **核心闭环 MVP** | "画像构建 → 藏宝图生成 → 进关卡 → 出题 → 评审 → 提交完成" 全链路可跑 |
| **6 张新业务表** | `knowledge_points` / `map_nodes` / `levels` / `exercises` / `level_completions` / `review_results` + Alembic 迁移 |
| **Redis Stream 真流** | worker 任意点 `progress_publish()` → gateway SSE 端点 `XREAD` 阻塞读 → 真流分块 |
| **SSE 端点升级** | `/api/profile/init/{trace_id}/stream` 与新增 `/api/level/{level_id}/stream` 订阅 Redis Stream |
| **LLM 思考模式抽象** | `ChatRequest.reasoning` + `ChatRequest.reasoning_budget`；`ChatChunk.reasoning_delta`；adapter 解析 `reasoning_content` |
| **评审 Agent（规则过滤）** | JSON 合法性 / 题目唯一性 / 答案格式 / 难度梯度 |
| **REST 端点（MVP 子集）** | profile build / map generate / level start / submit / status / stream |
| **Seed 数据** | 从 demo-serif 现有 Map 节点抽 5-10 个知识点 + 关卡结构 |
| **`scripts/smoke_mvp.sh`** | 端到端跑通：build → SSE 收 6 段 progress → submit → score |
| **测试** | 单元 + 集成（testcontainers 起真实 Redis Stream 跑通） |
| **可观测性** | OTel + Jaeger，5 个 Agent 全链路 trace |

### 1.2 Stage 3 范围外（推到 Stage 4+）

| 项 | 推到 |
| --- | --- |
| 4 种关卡形式（📖/🤖/💻/🎯） | Stage 4（文档 / 思维导图 / 代码 / 听力） |
| 评估模块 / 仪表盘 / 画像演变图表 | Stage 4 |
| 9 个核心窗口的真实内容 | Stage 4 |
| WebSocket 流式（Stage 2 已说明 Stage 3 仍走 SSE） | 永不做，仅 SSE |
| TTS / ASR / 讯飞星火 | Stage 5 |
| 1 个 Demo 之外的 3 个内容 Agent（导图 / 文档 / 代码） | Stage 4 |
| 评审 Agent 的 RAG / 引用 / 完整 4 阶段 | Stage 4 |
| 三层存储一致性（写穿透 / 读旁路 / Singleflight） | Stage 4 |
| v4 § 5.3.2 完整 25 张表 | Stage 4+ 按需 ALTER |
| OAuth / JWT / 登录 / 会话 | **永远不做**（项目级硬约束） |
| k8s / Helm | Stage 5 |

### 1.3 项目级硬约束（继承自 [[no-auth-no-login]]）

> **整个项目（所有阶段）都不需要登录 / 鉴权 / 会话 / Token / OAuth / JWT 任何形式。**

落地规则：
- 任何阶段、任何 task、任何 spec / plan / 文档中出现鉴权 / 登录 / 会话 / Token / JWT / OAuth / 账号 / 注册 / 注销 / 邮箱密码 / refresh token / `Depends(get_current_user)` / `auth.py` 等概念，**一律删除**
- 学生以**业务字段 `student_id`** 标识，请求体或路径直接传入
- `students` 表保留为业务主数据表，但不与任何 token 关联

---

## 2. 技术决策表（继承 Stage 2 + 新增 3 项）

### 2.1 继承自 Stage 2 的 8 项（继续生效）

| # | 决策点 | 决策 |
| --- | --- | --- |
| 1 | Agent 框架 | 自研 `BaseAgent` + `SkillBasedScheduler` |
| 2 | 消息总线 | RabbitMQ |
| 3 | LLM 主路径 | OpenAI 兼容（DeepSeek / 通义千问） |
| 4 | Web 框架 | FastAPI |
| 5 | 鉴权 | 不做（项目级硬约束） |
| 6 | 容器化 | docker-compose |
| 7 | ORM | SQLAlchemy 2.x async + Alembic |
| 8 | 监控 | OTel + Jaeger |

### 2.2 Stage 3 新增的决策

| # | 决策点 | 决策 | 备选 | 决定理由 |
| --- | --- | --- | --- | --- |
| 9 | 进程拓扑 | **单一 worker 容器（Stage 2 现状）、同镜像多实例可扩展** | 按 Agent 类型拆容器 / 集群化部署 | 5 个 Agent 加起来 QPS 仍低；多实例只要多部署一即可；避免镜像重复 |
| 10 | Director 调度 | **同步序列调 + Redis Stream 真流推送** | 纯序列调（无流式）/ 全异步信封编排 | 内部代码简单线性、SSE 流式不变；外部用户体验跟异步一致 |
| 11 | SSE 后端方案 | **单一 Redis Stream `stream:{trace_id}` · 各阶段 XADD · gateway 裸 XREAD** | 多 Stream 按阶段拆 / RabbitMQ 共享拓扑 / Redis Pub/Sub | 实现最简，游标从 `0-0` 起步可拿全历史；与 RabbitMQ 拓扑零耦合 |
| 12 | 数据库表数 | **6 张新表**（不含 Stage 2 已建 `students` / `profiles`） | 一次拿 25 张全部 / 全部走 Redis JSON | MVP 闭门验证设计；ALTER 留给 Stage 4 |
| 13 | LLM 思考模式启用 | **按 `ChatRequest` 字段 `reasoning` 默认 `False`** | 全局开关 / 按 Agent 类型预设 | 调用方按需传入，最灵活也最显式 |
| 14 | 存储布局 | **状态走 PG（事务+查询）、热数据走 Redis（缓存 + Stream）** | 全 PG / 全 Redis | MVP 边界清晰；状态持久化靠 PG、流推送靠 Redis |

### 2.3 关联选型（已敲定，不在 8+3 项决策里）

- 包管理 / 运行：uv
- Python：3.12（沿用 Stage 2 锁定）
- Redis Stream 客户端：redis-py 5.x async（`xadd` / `xread`，**不使用** `xreadgroup` / consumer group）
- Alembic：Stage 2 已用，Stage 3 新增 1 个 revision

---

## 3. 架构与目录

### 3.1 进程拓扑（沿用 Stage 2）

```
docker-compose.yml
├── postgres          # PostgreSQL 16
├── redis             # Redis 7（含 Stream 类型）
├── qdrant            # Qdrant v1.7+（Stage 3 暂不创建 collection，留接口）
├── minio             # MinIO
├── jaeger            # Jaeger all-in-one
├── gateway           # FastAPI gateway（REST + SSE）
└── worker            # 消费进程（5 个 Agent 全部在内部）
```

**Stage 3 拓扑变化**：仅 redis 多了 Stream 用法（XADD / 裸 XREAD，从 0-0 起步）；其他无变。

### 3.2 backend/ 新增与修改

```
backend/
├── migrations/
│   └── versions/
│       └── <new>_stage3_business_tables.py   ← 新增 6 张表的迁移
├── scripts/
│   ├── smoke_mvp.sh                          ← 新增：MVP 闭环端到端
│   ├── smoke.sh                              ← Stage 2 已建，仍跑
│   └── seed_map.py                           ← 新增：从 demo-serif 抽 5-10 个知识点
├── src/selflearn/
│   ├── core/
│   │   ├── envelope.py        # 修改：action 增加 progress 子集枚举（可选，仅文档）
│   │   └── thinking.py        # 新增：LLM 思考模式辅助（解析 reasoning_content）
│   ├── llm/
│   │   ├── base.py            # 修改：ChatRequest.reasoning, reasoning_budget；ChatChunk.reasoning_delta
│   │   ├── adapters/
│   │   │   ├── mock.py        # 修改：chat_stream yield reasoning_delta
│   │   │   └── openai_compat.py  # 修改：chat_stream 同时取 reasoning_content
│   ├── progress/              # 新增子模块
│   │   ├── stream.py          # progress_publish / progress_consume（Redis Stream 包装）
│   │   └── stages.py          # Stage 枚举 + ProgressEvent dataclass
│   ├── tools/                 # 新增：MCP Tool 协议层（见 § 9）
│   │   ├── protocol.py        # Tool / ToolResult 接口、ToolRegistry 单例
│   │   └── builtin/
│   │       ├── lint_json.py       # Tool: tool.lint_json（stub：jsonschema 规则校验）
│   │       ├── fetch_template.py  # Tool: tool.fetch_template（stub：读 prompts/*.yaml）
│   │       └── store_kp.py        # Tool: tool.store_kp（stub：本地 dict，Stage 4 接真）
│   ├── skills/                # V1.2 重设：Skill = markdown 文档 + Agent 加载为 prompt/约束器
│   │   ├── library.py              # 从 docs/skills/*.md 加载 Skill 对象到进程内 skill_library
│   │   └── loader.py              # Skill 解析（frontmatter + body）→ Skill 对象
│   └── builtin/                # ⚠️ 重要：Skill 不在这里写代码，仅是一些具体 Skill 的 Builder/Loader 助手
│       └── # （如 exercise_builder.py 提供「从 Skill 拿模板字段」的便捷函数）
├── docs/skills/                # ★ Skill 的真正存储位置——markdown 文档
│   ├── skill.exercise.generate.md   # 「如何生成合规习题」流程说明书
│   ├── skill.review.exercise.md     # 「如何评审」流程说明书
│   ├── skill.profile.build.md       # 「画像构建」流程说明书
│   ├── skill.plan.generate.md       # 「藏宝图生成」流程说明书
│   └── skill.director.start.md      # 「Director 推进」流程说明书
├── agents/builtin/
│   ├── profile_agent.py        # Agent 代码；通过 skills.library.get("profile.build") 加载 Skill 内容作 system prompt
│   ├── plan_agent.py
│   ├── director_agent.py       # 同步序列调，含 try/except（见 § 3.4）
│   ├── exercise_agent.py
│   └── review_agent.py
│   ├── domain/
│   │   ├── knowledge_point.py # 新增
│   │   ├── map_node.py        # 新增
│   │   ├── level.py           # 新增
│   │   ├── exercise.py        # 新增
│   │   ├── level_completion.py# 新增
│   │   └── review_result.py   # 新增
│   ├── gateway/routes/
│   │   ├── profile.py         # 修改：init 改为 build + SSE 订阅 stream
│   │   ├── map.py             # 新增
│   │   └── level.py           # 新增
│   └── schemas/
│       └── progress.py        # 新增：Stage enum + ProgressEvent Pydantic
└── tests/
    ├── unit/
    │   ├── test_thinking.py           # 新增
    │   ├── test_chat_stream_reasoning.py  # 新增
    │   ├── test_progress_stream.py    # 新增（mock Redis）
    │   ├── test_exercise_agent.py     # 新增
    │   └── test_review_agent.py       # 新增
    └── integration/
        ├── test_smoke_mvp.py          # 新增（testcontainers 起真实 Redis Stream）
        └── test_smoke.py              # Stage 2 已有，仍跑
```

### 3.3 关键模块职责

**`progress/stream.py` —— Redis Stream 真流核心**：

```python
# progress/stream.py
from redis.asyncio import Redis
from selflearn.config import get_settings

PROGRESS_STREAM_PREFIX = "stream:"
PROGRESS_STREAM_TTL_SECONDS = 3600  # 1 小时回收

async def progress_publish(trace_id: str, event: ProgressEvent) -> None:
    """worker 任意代码点调用，往 Redis Stream 写一条进度。"""
    r: Redis = get_redis()
    key = f"{PROGRESS_STREAM_PREFIX}{trace_id}"
    await r.xadd(key, event.to_redis_fields(), maxlen=100, approximate=True)
    await r.expire(key, PROGRESS_STREAM_TTL_SECONDS)


async def progress_consume(trace_id: str) -> AsyncIterator[ProgressEvent]:
    """Gateway SSE 端点调用，从 Stream 阻塞读。

    ⚠️ **关键修复（V1.1）**：游标必须从 `"0-0"` 开始，而非 `"$"`。
    - `"$"` = "只接收连接后新到的消息"——前端 POST 后到 GET 这两次网络请求间隙，
      Worker 可能已写完好几条 progress。前端用 `$` 接入，会错过所有历史事件，
      SSE 端点陷入死等。
    - `"0-0"` = "从头读"——前端连上瞬间拿回所有已发事件，再继续阻塞等后续。
    每个 trace_id 独立一个 Stream key，从头读不会带来性能问题。
    """
    r: Redis = get_redis()
    key = f"{PROGRESS_STREAM_PREFIX}{trace_id}"
    last_id = "0-0"  # ← V1.1 修复：从 0-0 起步，避免事件丢失
    while True:
        result = await r.xread({key: last_id}, block=5000, count=10)
        if not result:
            continue  # block 超时，重试（说明 stream 暂时没新事件）
        for _, entries in result:
            for entry_id, fields in entries:
                yield ProgressEvent.from_redis_fields(fields)
                last_id = entry_id
```

**`progress/stages.py` —— Stage 枚举与事件类型**：

```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class Stage(str, Enum):
    PROFILE = "profile"
    PLAN = "plan"
    DIRECTOR = "director"
    EXERCISE = "exercise"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    stage: Stage
    status: str            # "running" | "completed" | "failed"
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_redis_fields(self) -> dict[str, str]:
        return {
            "stage": self.stage.value,
            "status": self.status,
            "payload": json.dumps(self.payload, ensure_ascii=False),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_redis_fields(cls, fields: dict[bytes | str, bytes | str]) -> "ProgressEvent":
        decoded = {k.decode() if isinstance(k, bytes) else k:
                   v.decode() if isinstance(v, bytes) else v
                   for k, v in fields.items()}
        return cls(
            stage=Stage(decoded["stage"]),
            status=decoded["status"],
            payload=json.loads(decoded["payload"]),
            timestamp=datetime.fromisoformat(decoded["timestamp"]),
        )
```

### 3.4 Director Agent 同步序列调 + 流推送

```python
# agents/builtin/director_agent.py
class DirectorAgent(AbstractAgent):
    """Director 单进程内同步序列调 Profile → Plan → Exercise → Review。

    ⚠️ V1.1 修复：必须 try/except 兜底。
    失败场景：LLM 返回不合规 JSON / 网络断开 / 解析异常 / DB 写入冲突。
    若不 catch：
      - Director 进程崩溃
      - Redis Stream 没有 Stage.FAILED 事件写入
      - Gateway SSE 端点 XREAD 死循环 continue
      - 前端无限转圈
    所以：任何异常必须捕获 → 推送 FAILED 进度 → 抛 AppError 让上层记录 trace。
    """
    agent_id = "director-01"
    # 注：Agent 类不声明 skills = [...]。Skill 在 run() 内通过 skill_library.get(...) 动态获取。

    async def run(self, env: Envelope) -> Envelope:
        trace_id = env.trace_id
        try:
            # 1. 选节点（v4 § 3.13 选第一个 active 节点）
            await progress_publish(trace_id, ProgressEvent(
                stage=Stage.DIRECTOR, status="running",
                payload={"action": "select_node"}
            ))
            node = await self._select_first_active_node(env.payload["student_id"])

            # 2. 同步调 Exercise Agent（直接函数调用，不绕 RabbitMQ）
            await progress_publish(trace_id, ProgressEvent(
                stage=Stage.EXERCISE, status="running",
                payload={"node_id": str(node.node_id)}
            ))
            exercises = await exercise_agent.run_sync(env, node)
            await progress_publish(trace_id, ProgressEvent(
                stage=Stage.EXERCISE, status="completed",
                payload={"count": len(exercises)}
            ))

            # 3. 同步调 Review Agent
            await progress_publish(trace_id, ProgressEvent(
                stage=Stage.REVIEW, status="running"
            ))
            review = await review_agent.run_sync(env, exercises)
            await progress_publish(trace_id, ProgressEvent(
                stage=Stage.REVIEW, status="completed",
                payload={"verdict": review.verdict, "issues_count": len(review.issues)}
            ))

            # 4. 写库（levels + exercises + review_results 表）
            await self._persist(node, exercises, review)

            # 5. 推 completed 进度
            await progress_publish(trace_id, ProgressEvent(
                stage=Stage.COMPLETED, status="completed",
                payload={"level_id": str(self._level_id), "exercises_count": len(exercises)}
            ))

            return Envelope(
                action="skill.completed",
                sender=ActorRef(type="agent", id=self.agent_id),
                target=ActorRef(type="gateway", id=env.sender.id),
                payload={"level_id": str(self._level_id), "exercises": exercises_as_dict},
                trace_id=trace_id,
                parent_id=env.span_id,
            )

        except AppError:
            # 业务异常：包一层带 trace_id 的 FAILED 进度后上抛
            await self._emit_failed(trace_id, "agent_internal_error", "Director 处理失败")
            raise
        except Exception as e:  # noqa: BLE001
            # 兜底：任何意外（LLM 解析 / 网络 / DB）都推到 Stream 一个 FAILED
            await self._emit_failed(trace_id, "internal_unhandled", repr(e))
            log.error("director.unhandled_exception", trace_id=trace_id, error=repr(e))
            raise AppError(ErrorCode.INTERNAL, "Director 处理失败", trace_id=trace_id) from e

    async def _emit_failed(self, trace_id: str, code: str, message: str) -> None:
        """推一条 FAILED 进度让前端 SSE 端点跳出死等。"""
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.FAILED, status="failed",
            payload={"code": code, "message": message}
        ))
```

---

## 4. 消息流与 SSE 真流

### 4.1 总体消息流

```
client (curl / SSE EventSource)
   │
   │ POST /api/profile/build {student_id, topic}
   ▼
gateway/routes/profile.py
   │ 1. 创建 trace_id
   │ 2. XADD stream:{trace_id} {stage:profile, status:"pending"}
   │ 3. publish envelope {action:"skill.execute", target.director?}
   │    routing key = profile.skill.profile.build
   │ 4. 立即返回 { trace_id }
   │
   ▼
worker (单进程消费)
   │
   ├─ ProfileAgent.run(env)         ← XADD stream progress (running → completed)
   │     ├─ 5 轮对话（mock 即可）+ LLM call
   │     ├─ 写 profiles 表
   │     └─ publish envelope {director}
   │
   ├─ PlanAgent.run(env)            ← XADD stream progress (running → completed)
   │     ├─ 调 LLM 生成藏宝图
   │     ├─ 写 knowledge_points + map_nodes 表
   │     └─ publish envelope {director}
   │
   ├─ DirectorAgent.run(env)        ← 核心编排
   │     ├─ XADD {director running + select_node}
   │     ├─ 同步调 Exercise Agent.run_sync()    ← 内部 await
   │     │   ├─ LLM call（reasoning=True）
   │     │   ├─ 解析 JSON → 写 exercises 表
   │     │   └─ XADD {exercise running → completed}
   │     ├─ 同步调 Review Agent.run_sync()
   │     │   ├─ 规则过滤（JSON / 重复 / 答案格式）
   │     │   ├─ 写 review_results 表
   │     │   └─ XADD {review running → completed}
   │     ├─ 写 levels 表
   │     └─ XADD {completed}
   │
   ▼
gateway SSE 端点（订阅 stream）
   │ XREAD stream:{trace_id} BLOCK 5000
   │     → 推送 SSE: event="progress" data=ProgressEvent JSON
   │     → 收到 COMPLETED 事件后推送 SSE: event="completed" data=final_result
   │     → 连接关闭
```

### 4.2 SSE 事件契约（升级版，兼容 Stage 2）

| event | data JSON | 何时推送 | 兼容性 |
|-------|-----------|---------|--------|
| `progress` | `{"stage": str, "status": str, "payload": {...}, "timestamp": iso}` | Agent 每个阶段开始 / 完成时 | Stage 3 新增 |
| `reasoning` | `{"delta": str}` | `ChatRequest.reasoning=True` 时逐 chunk | Stage 3 新增 |
| `chunk` | `{"delta": str}` | `chat_stream` 每个非推理 chunk | Stage 3 新增 |
| `completed` | `{"trace_id, level_id, exercises, review_verdict, ...}` | Director 全部跑完 | Stage 2 已有、扩展 payload |
| `error` | `{"code": "ErrorCode", "message": str}` | 出错时 | Stage 2 已有 |

**关键约束**（破坏即报错）：
- 路径固定：`/api/profile/init/{trace_id}/stream`、`/api/level/{level_id}/stream`
- 事件名固定：上表 5 类，新增必须 `feature_event` 命名
- `Content-Type: text/event-stream`（sse-starlette 自动设置）
- 断线清理：Gateway 端 `try/finally` 关闭 XREAD

### 4.3 ErrorCode 增量

Stage 2 已有 8 个；Stage 3 新增：

```python
EXERCISE_INVALID = "EXERCISE_INVALID"      # 评审拒绝、JSON 不合法
REVIEW_REJECTED  = "REVIEW_REJECTED"       # 评审严格拒收（需要重新生成）
STREAM_TIMEOUT   = "STREAM_TIMEOUT"        # Redis Stream 阻塞读取超时
```

---

## 5. 数据模型（6 张新表）

### 5.1 ER 总图

```
students (Stage 2)
   ↓ 1:N
profiles (Stage 2，dimensions JSONB)
   ↓ 1:N (按 student)
map_nodes (新增)
   ↓ 1:N
levels (新增)
   ↓ 1:N
exercises (新增)
   ↓
review_results (新增) ← chain by level_id
   ↓
knowledge_points (新增，独立字典表，按 kp_id 反查)

level_completions (新增) ← 学生提交记录，按 level_id
```

### 5.2 6 张新表 DDL

```sql
-- knowledge_points —— 知识点字典表
CREATE TABLE knowledge_points (
    kp_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject        VARCHAR(128) NOT NULL,
    title          VARCHAR(255) NOT NULL,
    description    TEXT NOT NULL,
    difficulty     SMALLINT NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    prerequisites  JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_kp_subject ON knowledge_points(subject);


-- map_nodes —— 藏宝图节点
CREATE TABLE map_nodes (
    node_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id     UUID NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    kp_id          UUID NOT NULL REFERENCES knowledge_points(kp_id),
    status         VARCHAR(32) NOT NULL DEFAULT 'active',  -- active/sleeping/completed/locked
    branch_type    VARCHAR(32) NOT NULL DEFAULT 'main',    -- main/interest
    position       JSONB NOT NULL DEFAULT '{"x":0,"y":0}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_map_nodes_student_status ON map_nodes(student_id, status);


-- levels —— 关卡
CREATE TABLE levels (
    level_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id        UUID NOT NULL REFERENCES map_nodes(node_id) ON DELETE CASCADE,
    status         VARCHAR(32) NOT NULL DEFAULT 'generated',
    form           VARCHAR(32) NOT NULL DEFAULT 'exercise',  -- MVP 只用 exercise
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_levels_node ON levels(node_id);


-- exercises —— 题目
CREATE TABLE exercises (
    exercise_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level_id       UUID NOT NULL REFERENCES levels(level_id) ON DELETE CASCADE,
    exercise_type  VARCHAR(32) NOT NULL,           -- single_choice/fill_blank/short_answer/code
    prompt         TEXT NOT NULL,
    options        JSONB NOT NULL DEFAULT '[]'::jsonb,
    correct_answer TEXT NOT NULL,
    explanation    TEXT NOT NULL,
    difficulty     SMALLINT NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
    score          NUMERIC(4,2) NOT NULL DEFAULT 1.0
);
CREATE INDEX idx_exercises_level ON exercises(level_id);


-- level_completions —— 关卡完成记录
CREATE TABLE level_completions (
    completion_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level_id          UUID NOT NULL REFERENCES levels(level_id) ON DELETE CASCADE,
    student_id        UUID NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    score             NUMERIC(5,2) NOT NULL,
    duration_seconds  INTEGER NOT NULL,
    answers           JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics           JSONB NOT NULL DEFAULT '{}'::jsonb,
    submitted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_lc_student ON level_completions(student_id);
CREATE INDEX idx_lc_level ON level_completions(level_id);


-- review_results —— 评审结果
CREATE TABLE review_results (
    review_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level_id       UUID NOT NULL REFERENCES levels(level_id) ON DELETE CASCADE,
    verdict        VARCHAR(32) NOT NULL,            -- passed/rejected/needs_fix
    score          NUMERIC(4,2) NOT NULL,
    issues         JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_rr_level ON review_results(level_id);
```

### 5.3 ⚠️ JSONB 脏检查陷阱（实现注意事项）

> 这是 SQLAlchemy 2.x async + JSONB 的已知坑。Stage 3 必须全栈规避。

**问题**：
```python
profile.dimensions["knowledge_base"] = 0.8   # ⚠️ 不触发 dirty tracking
await session.commit()                        # JSONB 字段不变
```

**解决**（统一封装在 `domain/*.py` 仓库层）：

```python
# 仅供演示，具体在 plan 中由实现 agent 设计
from sqlalchemy.orm.attributes import flag_modified

class ProfileRepository:
    async def update_dimension(self, session: AsyncSession, profile: Profile,
                               dim_name: str, value: float) -> None:
        new_dims = {**profile.dimensions, dim_name: value}   # 整体替换
        profile.dimensions = new_dims                        # 直接赋值
        # 或者显式 flag_modified：
        # flag_modified(profile, "dimensions")
        await session.flush()
```

**统一规则（必须遵守）**：
- JSONB 字段就字典序新对象的引用，**不**就地 mutate
- 多步批量更新走"读 dict → 改 → 整体回写"
- 单测覆盖：mutate 后必须能被 `await session.refresh(profile)` 读到新值

---

## 6. 错误处理、测试、可观测性

### 6.1 错误处理（继承 + 增量）

| 错误码 | HTTP | 触发 | Stage |
|--------|------|------|-------|
| `ENVELOPE_INVALID` | 400 | 信封字段缺失 / 类型错 | 2 |
| `SKILL_NOT_FOUND` | 422 | SkillBasedScheduler 找不到匹配 Agent | 2 |
| `AGENT_TIMEOUT` | 504 | Director 整体运行超过 120s（V1.1 从 30s 放宽——5 阶段同步叠加 + 思考模式慢调用） | 2 |
| `LLM_RATE_LIMIT` | 429 | LLM 429 | 2 |
| `LLM_UPSTREAM` | 502 | LLM 5xx / 网络错 | 2 |
| `DB_CONFLICT` | 409 | 唯一约束冲突 | 2 |
| `INTERNAL` | 500 | 其他 | 2 |
| **`EXERCISE_INVALID`** | 422 | 题目 LLM 输出不合规（评审 Agent 无法修复） | **3 新增** |
| **`REVIEW_REJECTED`** | 422 | 评审严格拒收（Director 触发二次生成） | **3 新增** |
| **`STREAM_TIMEOUT`** | 504 | Redis Stream 阻塞读取超时（gateway SSE 端点） | **3 新增** |

### 6.2 测试策略

**单元测试（新增 5 个文件）**：
- `test_thinking.py` — 思考模式 helper（reasoning_content 解析）
- `test_chat_stream_reasoning.py` — `chat_stream` 同时 yield delta + reasoning_delta
- `test_progress_stream.py` — `progress_publish / progress_consume` 用 mock Redis 验证序列化
- `test_exercise_agent.py` — LLM mock 输出 → 解析 JSON → 写表
- `test_review_agent.py` — 规则过滤（JSON 合法 / 题目重复 / 答案格式 / 难度梯度）

**集成测试（新增 1 个 + Stage 2 已有）**：
- `test_smoke_mvp.py` — testcontainers 起真实 Redis Stream，跑完整 MVP 闭环

**覆盖率**：核心组件 > 70%

**每 task 验证**：`uv run mypy src` + `uv run pytest tests/unit -q` 必须 0 错。

### 6.3 可观测性

| Span 名 | 属性 | 位置 |
|---------|------|------|
| `agent.{name}.run` | agent.name, trace_id, level_id | 各 Agent run |
| `progress.publish` | stream.key, stage | progress_publish 内 |
| `stream.read` | stream.key, block_ms, count | progress_consume 内 |
| `review.rule` | rule.name, passed | ReviewAgent 规则过滤内 |

每条 Span 必须带 `envelope.trace_id`（与 Stage 2 一致）。

---

## 7. 验收

### 7.1 必过清单

- [ ] `alembic upgrade head` 创建 6 张新表（`knowledge_points` / `map_nodes` / `levels` / `exercises` / `level_completions` / `review_results`）
- [ ] `scripts/seed_map.py` 种子 5-10 个 `knowledge_points`
- [ ] `POST /api/profile/build` 触发 → SSE 1s 内收到第 1 个 `progress` 事件（stage=profile）
- [ ] `scripts/smoke_mvp.sh` 端到端跑通：
  - POST `/api/profile/build` → trace_id 返回
  - SSE 持续订阅 `/api/level/{level_id}/stream` 依次收到：
    - `progress` stage=profile (running → completed)
    - `progress` stage=plan (running → completed)
    - `progress` stage=director (running)
    - `progress` stage=exercise (running → completed, items=N)
    - `progress` stage=review (running → completed, verdict=passed)
    - `completed` (含 level_id, exercises)
  - POST `/api/level/{level_id}/submit` → score > 0 / level status = completed
- [ ] **LLM 抽象层**：`BaseLLMAdapter` 支持 `ChatRequest.reasoning=True`，mock + openai_compat adapter 流中能产生 `reasoning_delta` chunk
- [ ] **Redis Stream 真流**：worker 端 `XADD` 一条 progress 后，gateway SSE `XREAD` 立即收到（< 200ms）；游标从 `0-0` 起步，连上前已写入的事件全部能拿到
- [ ] **评审 Agent**：能拒收 JSON 非法 / 题目重复 / 答案格式错误的习题集合
- [ ] **Skill markdown 化（V1.2）**：`docs/skills/skill.exercise.generate.md` 等 Skill 文档存在；`skills.library.load_all()` 启动时读盘；Agent 通过 `skill_library.get(name)` 加载 Skill.body 作为 LLM system prompt
- [ ] **Skill 与 Tool 边界**：Agent 同时使用 Skill（注入 prompt）和 Tool（拿数据/做校验），二者**不混合** —— Skill 不调 ToolRegistry，Tool 不注入 prompt
- [ ] **MCP Tool 协议**：`tools/protocol.py` 提供 `Tool` 接口与 `ToolRegistry.call()`；3 个 stub Tool（`tool.lint_json` / `tool.fetch_template` / `tool.store_kp`）已注册；Exercise Agent 通过 `ToolRegistry` 调 lint_json（不直连 jsonschema）
- [ ] **JSONB 字段**：单测覆盖 — `dimensions` 字典就字段序更新可被刷出
- [ ] `level_completions` 表写入字段齐全（score / duration_seconds / answers / metrics）
- [ ] `uv run mypy src tests` 0 错误（strict 模式）
- [ ] `uv run pytest tests/unit -q` 全绿
- [ ] `uv run pytest tests/integration/test_smoke_mvp.py -q` 全绿
- [ ] `uv run pytest tests/integration/test_smoke.py -q`（Stage 2 smoke）仍全绿（向后兼容）
- [ ] Jaeger UI 完整 trace：profile → plan → director → exercise → review → submit
- [ ] `backend/README.md` 更新（端点表 + 思考模式用法 + smoke_mvp 用法）

### 7.2 不允许出现（继承 Stage 2 § 6.2）

- ❌ 鉴权 / 登录 / Token / JWT / OAuth 代码
- ❌ 4 种关卡形式的非 exercise 实现
- ❌ 评估模块 / 仪表盘
- ❌ TTS / ASR / 讯飞 / WebSocket
- ❌ 数据表超过本次声明的 6 张（新增 / ALTER 留给 Stage 4）
- ❌ 直连 OpenAI SDK 绕过 `LLMRegistry`

### 7.3 风险与应对

| 风险 | 概率 | 应对 |
|------|------|------|
| Redis Stream 在新版 redis-py 5 异步客户端的兼容性 | 中 | 锁 redis-py>=5.0.4；单测覆盖 XADD / XREAD；实战前在 staging 跑通 |
| 同步序列调让总时长叠加（5 个 LLM 调用串行可能 30s+） | 高 | AGENT_TIMEOUT 放宽到 120s（V1.1）；Plan/Exercise 不强制同步等完整结果；Director 错位 × 提交后后台继续跑 |
| **Director 同步调用缺异常兜底**（V1.1 新增） | 高 | DirectorAgent.run 外层 try/except，任何异常 → progress_publish(stage=FAILED) → 抛 AppError。SSE 端点必须能识别 FAILED 事件后关闭连接 |
| Exercise Agent LLM 输出 JSON 经常不合规 | 高 | 强制 prompt 模板；Review Agent 拒收；1 次自动重试 |
| Postgres JSONB 嵌套字典脏检查失效 | 中 | Repo 层统一封装：走整体赋值 或 `flag_modified`；单测覆盖 |
| MVP 后 demo 质量不高 | 中 | 评审 Agent 把关 reject ≥40% 内容；人工巡检；seed_map 补中 |
| Map 生成 LLM 节点重复 / 环路 | 中 | Plan Agent 加约束节点唯一；Review Agent 触发二次生成 |
| Stage 2 现有 smoke 被反向破坏 | 低 | 跨仓在 Stage 2 spec 上加“Stage 3 不能破坏 Stage 2 smoke”的活跨测验证 |

---

## 8. 与 Stage 2 / v4 详细设计文档的一致性

### 8.1 Stage 2 决策链锁仔与衔接

| Stage 2 项 | Stage 3 衔接 |
|------------|---------------|
| 8 项决策 | 全部继承（见 § 2.1） |
| SkillBasedScheduler | Stage 3 5 个新 Agent 都走 skill 路由 |
| LLM Registry + mock + openai_compat | + adapter 修改（§ 3.2、§ 4） |
| `BaseLLMAdapter` + `chat_stream` | 保持兼容 + 加 `reasoning` 字段 |
| SSE 端点骨架（轮询） | Stage 3 升级为 Redis Stream 真流 |
| Smoke 闭环 POST /api/profile/init | Stage 3 改名为 `POST /api/profile/build` 业务含义更准；Stage 2 init 路径仍保留为兼容别名 |
| RabbitMQ 拓扑 | Stage 3 沿用；不新增队列 |
| OTel | Stage 3 新增 4 类 Span |

### 8.2 v4 详细设计文档对齐

| v4 节号 | 状态 | 说明 |
|---------|------|------|
| § 2.1.4 SkillBasedScheduler | 部分 | Stage 3 5 个新 skill 注册 |
| § 2.4.1 首次访问 → 画像构建 | 实现 | 去掉“登录”字眼 |
| § 2.4.2 画像更新公式 | 部分 | 量化指标表表存在；公式推到 Stage 4 |
| § 3.13 关卡 完整流程 | 部分 | MVP 取 subset：Profile → Plan → Director → Exercise → Review |
| § 4.1 7 类 WebSocket 事件 | 不实现 | 仅 SSE（Stage 2 已说明） |
| § 4.2 REST 17 个端点 | 部分 | Stage 3 子集：profile / map / level / submit |
| § 5.3.2 25 张表 | 部分 | Stage 3 取 6 张 |
| § 5.6 三层存储一致性 | 不实现 | Stage 4 |
| § 2.5 评审 Agent 协议 | 部分 | 仅规则过滤 |

---

## 9. Skill 与 MCP Tool 协边界说明（V1.2 重设）

> 本节解决两件事：(a) **Skill 在本项目中到底是什么**；(b) **MCP Tool 协议契约**。这两个问题之前混在一起，导致第一稿把 Skill 设计成"装饰器 + 全局注册表"，错位。V1.2 重设基于 `superpowers:writing-skills` 的设计哲学——Skill 是**给未来 agent 的可复用参考指南**，不是 Python 装饰器。

### 9.1 Skill = Markdown 说明书 + Agent 加载器

**Skill 在本项目中是「Agent 行为约束器」**，具体含义：

- **形态**：`docs/skills/<skill_name>.md` 的 markdown 文件，含 YAML frontmatter + Markdown 正文
- **职责**：告诉 Agent "做这件事时按这个规范来" —— 通过 **prompt 注入** + **结构化约束** 两种方式
- **生命周期**：进程启动时由 `skills/library.py` 读盘载入为 `Skill` 对象到 `skill_library` 单例
- **调用**：Agent 通过 `skill_library.get("skill.exercise.generate")` 拿到 Skill 对象，**用 Skill.body 作为 system prompt**，用 Skill.output_schema / validation_rules 作为 LLM 输出的结构化校验

**V1.3 数据流哲学：开发者"前置打包 + 冷酷后置校验 + 1 次重试"**

Stage 3 的流水线架构假定开发者（即写 Agent 业务逻辑的人）对每项 LLM 任务的输入数据需求是**完全已知**的——因为业务场景固定（出题 / 评审 / 画像 / 藏宝图），不存在"我不知道该喂什么"的开放场景。因此：

1. **前置打包（Pre-fetching）**：在 Agent.run() 内，开发者主动完成所有数据准备工作，然后一次性把全部原材料喂给 LLM。
   - **上下文数据注入**：用 Python 代码查 DB，把节点、知识点、profile 等结构化数据拼成字符串直接塞进 ChatMessage.content，例如 `content=f"node_id={node.node_id}, kp_title={node.kp.title}, kp_desc={node.kp.description}"`。
   - **规则与模板注入**：Agent 主动 `await ToolRegistry.call("tool.fetch_template", name=...)` 拉取 prompt 模板，与 `Skill.body` 中的业务规则合并，拼成完整的 system prompt。
   - **结果**：LLM 启动推理的那一刻，它所需的全部知识点细节、输出格式要求、业务约束都已经躺在它的上下文里；**LLM 无需也无法再发起任何额外数据获取动作**。

2. **冷酷后置校验**：前置注入的数据如因任何原因存在歧义，流水线**不指望 LLM 能自我反省**，而是用纯代码做拦截：
   - **结构校验**：LLM 输出完成后，Agent 立刻 `await ToolRegistry.call("tool.lint_json", payload=parsed, schema="exercise")`，严格按 jsonschema 检查输出。
   - **业务评审**：结构 OK 后交由下一节点 ReviewAgent 做规则过滤（唯一性、难度梯度、code 必含 def/class 等）。
   - **容错重试**：若 lint_json 抛 `EXERCISE_INVALID`，Agent 内部触发**最多 1 次自动重试**（同一模板、同一上下文，仅在 user message 中追加"上一次输出未通过校验，请重试并严格遵守 schema"），重试仍失败则抛 `EXERCISE_INVALID` 上抛，不写库、不进 Review。

**Skill markdown 文档 V1.2 约束**（重要）：

1. Skill = 纯业务说明书 + LLM system prompt 源，**禁止**写入 Tool 调用指令 / 工具名提示 / `ToolRegistry.call(...)` 之类的内容。原因：Skill.body 直接喂给 LLM，LLM 没有 function_call 能力，写了只会污染输出、引发解析崩溃。
2. Skill 仅描述：**意图 / 数据格式校验规则 / 输出 Schema / 业务硬约束**。
3. Tool 的实际调用由 Agent.run() 用 Python `await ToolRegistry.call(...)` 硬编排，编排顺序写在 Agent 代码里，不写在 Skill 里。
4. Skill 不描述"前置要查哪些表""要调哪个 tool 取模板"——这些是 Agent 在 run() 内硬编码的工程步骤，不属于业务约束。

**示例 Skill 文档**（`docs/skills/skill.exercise.generate.md`）：

```markdown
---
name: skill.exercise.generate
description: Use when generating exercises from a knowledge point. Output must match the exercise schema and pass business validation rules.
tags: [stage3, exercise, generation]
output_schema: schemas/exercise.schema.json
---

# Skill: 生成合规习题

## Intent
根据 knowledge_point 生成 N 道符合 difficulty 梯度与 schema 的习题。LLM 只负责按 schema 输出 JSON；不允许输出多余文字、不允许虚构字段。

## Output Schema
See `schemas/exercise.schema.json` — required fields: exercise_type, prompt, options, correct_answer, difficulty (1-3), score。

## Validation Rules
- 不允许 batch 内 prompt 重复。
- difficulty 必须 ∈ {1, 2, 3}。
- single_choice: `options` 长度 == 4，恰有 1 个 ∈ `correct_answer`。
- fill_blank: `correct_answer` 非空，prompt 含恰好一个 "____"。
- code: `correct_answer` 必须包含 Python `def` 或 `class` 定义。

## Common Mistakes
- LLM 返回夹杂散文 → 解析时必须用 extract-from-fence。
- difficulty 全部相同 → 必须按 1/2/3 大致均匀分布。
```

> 注：本 markdown 不写 `Call tool.fetch_template(...)` 这类 Tool 调用指令。所有 Tool 调用都在 Agent 代码中按固定顺序 `await` 完成。Skill 是"做什么 + 怎么算合法"，Agent 是"按这个流程硬编排"。

**Agent 加载 Skill 的代码形态**：

```python
# skills/library.py
from pathlib import Path
import frontmatter  # python-frontmatter package
from selflearn.core.logging import get_logger

log = get_logger("skills")

class Skill:
    def __init__(self, name: str, description: str, body: str, output_schema_path: str | None):
        self.name = name
        self.description = description
        self.body = body
        self.output_schema_path = output_schema_path


_skill_library: dict[str, Skill] = {}


def load_all(skills_dir: Path = Path("docs/skills")) -> None:
    """进程启动时调一次。"""
    for md_path in skills_dir.glob("*.md"):
        post = frontmatter.load(md_path)
        if "name" not in post.metadata:
            log.warning("skills.skip_missing_name", path=str(md_path))
            continue
        skill = Skill(
            name=post.metadata["name"],
            description=post.metadata.get("description", ""),
            body=post.content,
            output_schema_path=post.metadata.get("output_schema"),
        )
        _skill_library[skill.name] = skill
    log.info("skills.loaded", count=len(_skill_library))


def get(name: str) -> Skill:
    if name not in _skill_library:
        raise KeyError(f"skill_not_loaded:{name}（需在 docs/skills/{name}.md 加文档，或调 load_all()）")
    return _skill_library[name]
```

**Agent 用 Skill 的代码形态**（**重要：Agent 不声明 skills = [...]**）：

- Skill 由 Envelope 的 `target.id` 与 Markdown 文件名直接匹配（路由靠 target.id，不靠静态注册）
- Agent 内**禁止**声明 `skills = [...]` 类属性或方法
- Agent 在 `run()` 内需要 Skill 时直接调 `skill_library.get("skill.exercise.generate")` 拿 Skill 对象，再用 `Skill.body` 作为 system prompt
- ToolRegistry 仅在 Agent 内显式调用，**不**出现在 Skill markdown 中

```python
# agents/builtin/exercise_agent.py
from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import Envelope
from selflearn.llm.registry import llm_registry
from selflearn.skills.library import get as get_skill
from selflearn.tools.protocol import ToolRegistry


class ExerciseAgent(AbstractAgent):
    agent_id = "exercise-01"

    async def run_sync(self, env: Envelope, node) -> list:
        skill = get_skill("skill.exercise.generate")  # 加载 Skill 文档

        # 1. 取模板
        tmpl = await ToolRegistry.call("tool.fetch_template", name="exercise_generation_v1")

        # 2. system prompt = Skill.body + 模板（Skill 是约束器，模板是参数）
        req = ChatRequest(
            messages=[ChatMessage(role="user", content=f"node_id={node.node_id}, kp_title={node.kp.title}")],
            system=skill.body + "\n\n" + tmpl.data["content"],
            reasoning=True,
        )

        # 3. LLM 调用
        raw = await llm_registry.default().chat(req)

        # 4. Skill 自带 output_schema → 转 tool.lint_json 参数校验
        lint = await ToolRegistry.call("tool.lint_json", payload=raw, schema="exercise")
        if not lint.ok:
            raise AppError(ErrorCode.EXERCISE_INVALID, lint.error)

        # 5. 反序列化入库
        ...
```

### 9.2 MCP Tool 协议层

> **Stage 3 起，MCP Tool 不能继续是占位壳了。** Tool 与 Skill 分工：Tool 是 Agent 与外部数据 / 系统交互的**能力协议层**，Skill 是约束 Agent 行为的**文档**。Agent 在 Skill 约束的步骤里调 Tool 拿数据。

**Tool 协议契约**：

```python
# tools/protocol.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


class Tool(ABC):
    """MCP Tool = 一项可调用能力。Agent 通过 ToolRegistry.call() 调。"""

    tool_name: str
    description: str

    @abstractmethod
    async def call(self, **kwargs: Any) -> ToolResult:
        ...


class ToolRegistry:
    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        cls._tools[tool.tool_name] = tool

    @classmethod
    async def call(cls, name: str, **kwargs: Any) -> ToolResult:
        tool = cls._tools.get(name)
        if not tool:
            return ToolResult(ok=False, error=f"tool_not_found:{name}")
        try:
            return await tool.call(**kwargs)
        except Exception as e:  # noqa: BLE001
            return ToolResult(ok=False, error=repr(e))


_register_default_tools()  # 在 tools/builtin/*.py 里完成
```

**Stage 3 必须落地的 3 个 stub Tool**：

| Tool 名 | 职责 | MVP stub 实现 | Stage 4 升级 |
|---------|------|----------------|--------------|
| `tool.lint_json` | 校验题目 JSON 是否合法 | `jsonschema` 包对照 `schemas/exercise.schema.json` 校验 | 接 MCP `jsonschema` server |
| `tool.fetch_template` | 拉取题目 / 评审模板（YAML） | 读 `selflearn/prompts/*.yaml` 本地文件 | 接 MinIO / 配置中心 |
| `tool.store_kp` | 知识点写库 | 直接调 SQLAlchemy repo 插表 | 接向量库（Qdrant）+ PG 双写 |

**关键约束**：
- Agent 调 Tool 不经过 RabbitMQ / LLM function_call；纯 Python `await` 调用
- Tool 是**能力复用单元**，不是 Agent 之间通信的载体
- Stage 4 接真 MCP server 时，仅替换 `ToolRegistry._tools` 来源，Agent 代码 0 改动

### 9.3 Skill ↔ Tool ↔ Agent 三者边界

| 维度 | Skill（markdown 文档） | Tool（可调用能力） | Agent（代码逻辑） |
|------|------------------------|---------------------|-------------------|
| 形态 | `.md` 文件 + frontmatter | Python 类继承 `Tool` | Python 类继承 `AbstractAgent` |
| 关心什么 | "做这件事按什么规范" | "我能提供什么能力" | "我要做什么、怎么做" |
| 注册到 | `skill_library`（启动时读盘） | `ToolRegistry`（启动时注册） | DI 容器 / 模块级单例 |
| 调用方 | Agent 调 `skill_library.get(name)` | Agent 调 `ToolRegistry.call(name, **kwargs)` | — |
| LLM 关系 | Skill.body 注入到 system prompt | Tool 通常不调 LLM（除非 tool 自己需要） | Agent 组合 Skill + Tool 完成工作 |
| 失败模式 | Skill 文档缺失 → KeyError | Tool 不存在 → 返回 ToolResult(ok=False) | Agent 处理 ToolResult.ok 失败重试或抛 AppError |
| Stage 3 示例 | `docs/skills/skill.exercise.generate.md` | `LintJsonTool` 类 | `ExerciseAgent.run_sync()` |

**三者协作示例**（Exercise Agent 出题）：

```
Agent (ExerciseAgent.run_sync)
  │
  │ 1. skill_library.get("skill.exercise.generate") → Skill 对象
  │      │
  │      └── Skill.body + output_schema 用于 step 2/3/4
  │
  │ 2. ToolRegistry.call("tool.fetch_template") ─────────────► Tool (FetchTemplateTool)
  │
  │ 3. llm_registry.default().chat(req with Skill.body as system)  ◄── LLM
  │
  │ 4. ToolRegistry.call("tool.lint_json") ────────────────────► Tool (LintJsonTool)
  │      │
  │      └── 用 Skill.output_schema 指定的 schema 校验输出
  │
  ▼
入库 exercises 表
```

**Skill 与 Tool 的核心区分**：
- **Skill 是规范**（"按这个流程做"）—— Agent 用 Skill 约束**自己**的行为
- **Tool 是能力**（"这个能力我可以调用"）—— Agent 用 Tool **拿数据或做校验**

### 9.4 与 Stage 2 SkillBasedScheduler 衔接

Stage 2 的 `SkillBasedScheduler`（`agents/scheduler.py`）是个**gateway 入口薄壳**：HTTP 请求带 envelope 进来 → scheduler 看 `target.id` 决定交给哪个 Agent.handle。本质是个**字符串路由表**。

V1.2 重设不破坏 Stage 2，**只改变 Skill 的组织方式**：
- Stage 2：`@skill("name")` 装饰器 + 全局 `skill_registry.register()` —— 这是错误的设计
- Stage 3 V1.2：`docs/skills/<name>.md` markdown 文档 + 启动时 `skills.library.load_all()` 读盘

Stage 2 的 SkillBasedScheduler 仍可用，但 `skill.name` 字段不再来自装饰器字符串，而来自 `envelope.target.id` → 与 `docs/skills/<id>.md` 文件名匹配。

---

```python
# tools/protocol.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


class Tool(ABC):
    """MCP Tool 协议——一个 Tool 是一个可调用能力。

    设计原则（基于 superpowers:writing-skills 关于 Skill 的视角）：
    - Tool = "我能做什么"（能力），Agent = "我要做什么"（编排）
    - Skill = "做这件事的标准步骤"（流程模板）
    - Agent 在 Skill 流程的某一步调 Tool 拿数据
    """

    tool_name: str      # 例如 "tool.lint_json"
    description: str    # 给 LLM 看的能力描述（Stage 4 接真 MCP 用）

    @abstractmethod
    async def call(self, **kwargs: Any) -> ToolResult:
        """统一签名：kwargs 与 Tool 自身定义的 input_schema 一致。"""


class ToolRegistry:
    """进程内 MCP Tool 注册中心（Stage 3 用单例，Stage 4 换成真 MCP client）。

    用法：
        result = await ToolRegistry.call("tool.lint_json", payload=raw_text, schema=...)
    """

    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        cls._tools[tool.tool_name] = tool

    @classmethod
    async def call(cls, name: str, **kwargs: Any) -> ToolResult:
        tool = cls._tools.get(name)
        if not tool:
            return ToolResult(ok=False, error=f"tool_not_found:{name}")
        try:
            return await tool.call(**kwargs)
        except Exception as e:  # noqa: BLE001
            return ToolResult(ok=False, error=repr(e))


_register_default_tools()  # 在 tools/builtin/*.py 里完成
```

---

## 10. 配套文档

- 实施计划：`docs/superpowers/plans/2026-07-12-stage3-business-mvp.md`（下一步）
- 验收报告：`docs/实施计划-Stage3-验收报告.md`（Stage 3 末尾产出）
- 决策记忆：`[[no-auth-no-login]]` / `[[stage3-llm-thinking-mode]]`（闭合后两条记忆可删）

---

> 文档结束。本 spec 是 Stage 3 子项目的实施依据，补充 Stage 2 基座而**不修改** Stage 2 决策。
