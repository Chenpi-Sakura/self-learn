# Stage 2 后端地基 — 设计文档

> **For agentic workers:** 本 spec 是 Stage 2 的"做什么、怎么做、不做什么"的权威来源。配套实施计划见 `docs/superpowers/plans/2026-07-11-stage2-backend-foundation.md`。

| 文档版本 | 修订日期 | 修订人 | 修订说明 |
| --- | --- | --- | --- |
| V1.0 | 2026-07-11 | 团队 | Stage 2 初稿。基于 `docs/详细设计规格说明书-v4.md` 第二、四、五部分，明确后端地基的范围、决策、消息流、smoke 闭环。**项目级约束：完全不做鉴权 / 登录**（参见 [[no-auth-no-login]]）。 |

---

## 0. 编写目的与读法

本文档是 Stage 2 的设计规范，回答四个问题：

1. **Stage 2 交付什么**：地基 + 1 条 smoke 闭环
2. **用什么技术栈**：8 项决策已敲定
3. **消息怎么流**：拓扑、信封、路由
4. **怎么验证**：smoke 端到端

**与现有文档的关系**：
- `docs/详细设计规格说明书-v4.md` 是**业务层权威**——本章不重新设计业务，只落实"用什么技术实现它"
- `docs/实施计划书.md § 3 Stage 2` 是**战略层路线图**——本章是它的**技术细节展开**
- `docs/需求规格说明书-v3.md` 是**需求基线**——本章不重新讨论需求

**读法建议**：
- § 1 范围与不在范围内（先看）
- § 2 决策表（核心）
- § 3 架构与目录（实现依据）
- § 4 消息流（关键路径）
- § 5 错误 / 测试 / 可观测性（质量门）
- § 6 验收（不可漏）

---

## 1. 范围与不在范围内

### 1.1 Stage 2 范围内（必交付）

| 项 | 说明 |
| --- | --- |
| **代码骨架** | `backend/` 目录 + uv + pyproject + Dockerfile |
| **基础设施** | docker-compose 一键启动 6 服务（PostgreSQL / Redis / Qdrant / MinIO / gateway / worker）+ Jaeger |
| **统一消息信封** | v4 § 2.2.1 的 Envelope 实现 + aio-pika publish/consume |
| **数据库 Schema（M1）** | 仅 v4 § 5.3 的 `students` + `profiles` 两张表 + Alembic 迁移 |
| **Registry** | Redis-backed Agent Registry（register / heartbeat / discover） |
| **Agent Runtime** | `BaseAgent` 抽象类 + Worker 进程消费入口 + 生命周期 |
| **SkillBasedScheduler** | 按 skill 路由到 Agent + 重试 + DLQ |
| **LLM Gateway** | OpenAI 兼容适配器（DeepSeek / 通义千问）+ 熔断器 |
| **REST 路由（M1）** | `/healthz` `/readyz` + smoke 路由 `/api/profile/init` + 状态查询 |
| **PingAgent（smoke）** | 自研 Agent 实现 `skill.ping.reply`：调 1 次 LLM + 回复 pong |
| **Smoke 闭环** | `scripts/smoke.sh` 端到端跑通 curl → gateway → broker → worker → LLM → reply |
| **可观测性** | OTel + Jaeger，smoke 调用链可视化 |
| **文档** | `backend/README.md` + Stage 2 验收报告 |

### 1.2 Stage 2 范围外（推到 Stage 3+）

| 项 | 推到 |
| --- | --- |
| 其他 23 张表（v4 § 5.3.2） | Stage 3 按领域服务分批建 |
| 17 个 REST 端点完整实现 | Stage 3 起按 `routes/` 目录逐文件落地 |
| 7 类 WebSocket 事件 | Stage 3 起；Stage 2 只走 polling 状态查询 |
| 8 个内容子 Agent（文档 / 导图 / 习题 / 代码 / 评审 / 画像 / 规划 / 总监） | Stage 3 按业务闭环分批实现 |
| Skill 全集（v4 § 2.1.4） | Stage 3+ 按 `@skill()` 装饰器逐个补 |
| MCP Tool 全集 | Stage 3+ |
| 讯飞星火适配器 | Stage 5（凭据依赖） |
| OAuth / JWT / 登录 / 会话 | **永远不做**——项目级约束（参见 [[no-auth-no-login]]） |
| 关卡资源生成 / 评审 / 业务编排 | Stage 3 |
| TTS / ASR（讯飞） | Stage 5 |
| 评估模块 / 仪表盘数据 | Stage 4 |
| 9 个核心窗口的真实内容 | Stage 4 |
| k8s / Helm | Stage 5 |
| 单测覆盖率 > 50% | Stage 5 |

### 1.3 项目级硬约束（继承自 [[no-auth-no-login]]）

> **整个项目（所有阶段）都不需要登录 / 鉴权 / 会话 / Token / OAuth / JWT 任何形式。**

落地规则：
- 任何阶段、任何 task、任何 spec / plan / 文档中出现鉴权 / 登录 / 会话 / Token / JWT / OAuth / 账号 / 注册 / 注销 / 邮箱密码 / refresh token / `Depends(get_current_user)` / `auth.py` 等概念，**一律删除**
- 学生以**业务字段 `student_id`** 标识，请求体或路径直接传入；后端不做"这是谁"的判断
- `students` 表保留为业务主数据表，但字段不再承担"鉴权主语"角色，不与任何 token 关联
- v4 详细设计文档 § 4.2 中涉及 `/api/auth/*` 的端点全部不实现
- v4 § 2.4.1 "初次登录 → 画像构建" 改写为"首次访问 → 画像构建"（无登录步骤）

---

## 2. 技术决策表（已敲定 8 项）

| # | 决策点 | 决策 | 备选 | 决定理由 |
| --- | --- | --- | --- | --- |
| 1 | Agent 框架 | **自研 BaseAgent** | LangGraph / CrewAI / AutoGen | v4 § 2.1.4 要求 SkillBasedScheduler 自研机制；外部框架抽象与 v4 § 2.1.4 难对齐；自研代码量可控 |
| 2 | 消息总线 | **RabbitMQ** | Redis Stream / NATS | v4 § 1.1 明文规定；Topic Exchange + DLX 与 v4 § 2.6 重试降级契合 |
| 3 | LLM 主路径 | **OpenAI 兼容**（DeepSeek / 通义千问） | 讯飞星火 / Ollama 本地 | 凭据可控、OpenAI 协议最通用；Stage 5 加讯飞适配器 |
| 4 | Web 框架 | **FastAPI** | Flask | 异步原生 + Pydantic + OpenAPI 自动生成 |
| 5 | 鉴权 | **不做**（项目级硬约束） | JWT / OAuth / mock | 见 [[no-auth-no-login]] |
| 6 | 容器化 | **docker-compose** | k8s / supervisord | 单机一键起 6 服务最直观 |
| 7 | ORM | **SQLAlchemy 2.x async + Alembic** | SQLModel / asyncpg 手写 | v4 § 5.3.2 表多关系重；2.x 的 `Mapped[]` 类型提示 + Alembic 迁移为事实标准 |
| 8 | 监控 | **OTel + Jaeger** | Prometheus / Sentry | v4 § 2.2.1 明文要求每条 Agent 消息带 TraceID |

**关联选型**（不在 8 项决策里但已确定）：
- 包管理 / 运行：**uv**（轻量、快）
- Python：**3.11+**
- LLM 客户端：**httpx + openai SDK（OpenAI 兼容模式）**
- RabbitMQ 客户端：**aio-pika**
- Qdrant 客户端：**qdrant-client[async]**
- 测试：**pytest + pytest-asyncio + testcontainers-python**
- Mypy：**strict 模式**

---

## 3. 架构与目录

### 3.1 进程拓扑

```
docker-compose.yml
├── postgres          # PostgreSQL 16，端口 5432
├── redis             # Redis 7，端口 6379
├── qdrant            # Qdrant v1.7+，端口 6333 (HTTP) / 6334 (gRPC)
├── minio             # MinIO，端口 9000 (API) / 9001 (Console)
├── jaeger            # Jaeger all-in-one，端口 16686 (UI) / 4317 (OTLP gRPC)
├── gateway           # FastAPI gateway（REST）
└── worker            # Agent 消费进程（可水平扩展）
```

`gateway` 与 `worker` **共享同一份镜像**，通过 `CMD ["uv", "run", "python", "-m", "selflearn.main", "--role=gateway"]` 或 `--role=worker` 区分。

### 3.2 backend/ 目录

```
backend/
├── pyproject.toml            # uv 项目
├── uv.lock
├── README.md
├── .env.example
├── docker-compose.yml
├── Dockerfile                # 多阶段构建
├── alembic.ini
├── migrations/
│   └── versions/
├── scripts/
│   ├── seed_dev.py           # 种子 demo student
│   └── smoke.sh              # 端到端 smoke
├── src/selflearn/
│   ├── main.py               # --role=gateway|worker|all
│   ├── config.py             # pydantic-settings
│   ├── core/                 # 横切
│   │   ├── envelope.py       # 统一消息信封
│   │   ├── tracing.py        # OTel 初始化
│   │   ├── logging.py        # JSON 结构化日志
│   │   └── errors.py         # AppError + ErrorCode
│   ├── gateway/
│   │   ├── app.py            # FastAPI() 装配
│   │   ├── deps.py           # DB session / Redis 等依赖注入
│   │   └── routes/
│   │       ├── health.py     # /healthz, /readyz
│   │       └── profile.py    # smoke 路由
│   ├── agents/
│   │   ├── base.py           # AbstractAgent
│   │   ├── scheduler.py      # SkillBasedScheduler
│   │   ├── registry.py       # Agent Registry
│   │   ├── worker.py         # Worker 进程入口
│   │   └── builtin/
│   │       └── ping_agent.py
│   ├── llm/
│   │   ├── gateway.py
│   │   ├── adapters/
│   │   │   └── openai_compat.py
│   │   └── circuit_breaker.py
│   ├── skills/
│   │   ├── base.py           # @skill 装饰器
│   │   └── builtin/
│   │       └── ping.py
│   ├── mcp/
│   │   ├── server.py         # 占位骨架（Stage 3+）
│   │   └── client.py         # 占位骨架
│   ├── infra/
│   │   ├── db.py
│   │   ├── redis_client.py
│   │   ├── qdrant_client.py
│   │   ├── minio_client.py
│   │   └── rabbit.py
│   ├── domain/               # Stage 2 仅实现 student.py + profile.py
│   │   ├── student.py
│   │   ├── profile.py
│   │   └── _placeholder.py   # 其余 23 张表的占位
│   └── schemas/
│       └── profile.py
└── tests/
    ├── unit/
    │   ├── test_envelope.py
    │   ├── test_skill_routing.py
    │   ├── test_registry.py
    │   ├── test_llm_adapter.py
    │   └── test_circuit_breaker.py
    └── integration/
        └── test_smoke.py
```

### 3.3 分层原则

- `core/` 横切：任何层都引用
- `infra/` 外部资源 client：仅导出 client，不放业务
- `domain/` 领域模型：SQLAlchemy ORM + 仓库方法
- `gateway/` 仅路由 + 装配，不放业务逻辑
- `agents/` 进程内 Agent 实例 + 调度；`llm/` LLM 适配；`skills/` 声明式注册；`mcp/` 协议占位
- **Stage 2 范围**：`student` + `profile` 两张表 + `PingAgent` + 1 个 skill；其余推到 Stage 3

### 3.4 数据模型（Stage 2 M1）

`students` 表（v4 § 5.3.2 学生与画像 - students）：

```sql
CREATE TABLE students (
    student_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name   VARCHAR(64)  NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

`profiles` 表（v4 § 5.3.2 学生与画像 - profiles）：

```sql
CREATE TABLE profiles (
    profile_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id     UUID NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    dimensions     JSONB NOT NULL DEFAULT '{}'::jsonb,  -- 6 维数值
    tags           JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_updated   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_profiles_student ON profiles(student_id);
```

**注意**：v4 § 5.3.2 完整 `students` 表带更多字段（`current_subject_id`、`lifecycle_state` 等），Stage 2 只取最小字段集。完整字段在 Stage 3 按需 ALTER。

---

## 4. 消息流与 smoke 闭环

### 4.1 RabbitMQ 拓扑

```
Exchange: agent.events       (topic, durable)
  ├─ Queue: agent.ping_agent.work
  │    binding key: ping_agent.#
  ├─ Queue: agent.profile.work
  │    binding key: profile.#
  └─ Queue: agent.dlq              # 死信
       binding key: #

Exchange: agent.events.dlx  (topic, durable)
  └─ Queue: agent.dlq       (durable)
```

- **routing key 命名**：`<agent_type>.<skill>.<action>`，例如 `ping_agent.skill.ping.reply`
- **DLX 配置**：每个业务队列声明 `x-dead-letter-exchange = agent.events.dlx`
- **Prefetch**：Worker 端 `basic_qos(prefetch_count=4)`

### 4.2 统一消息信封（v4 § 2.2.1）

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4

class ActorRef(BaseModel):
    type: str  # "agent" | "gateway" | "user" | "skill"
    id: str

class Envelope(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_id: str | None = None
    span_id: str = Field(default_factory=lambda: str(uuid4().hex[:16]))
    action: str                        # "skill.execute" | "agent.heartbeat" | ...
    sender: ActorRef
    target: ActorRef
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = 0
```

### 4.3 Smoke 闭环路径

```
client (curl)
   │
   │ POST /api/profile/init
   │   body: {"student_id": "demo-student", "topic": "smoke"}
   ▼
gateway/routes/profile.py
   │ 1. Pydantic 校验 body
   │ 2. publish envelope { action="skill.execute",
   │                       target={type:"skill", id:"skill.profile.init"},
   │                       payload={...} } 到 agent.events
   │    routing key = profile.skill.profile.init
   │ 3. 立即返回 { trace_id: "..." }
   │
   ▼
agents/worker.py 消费
   │ 1. SkillBasedScheduler.match("skill.profile.init")
   │      → 命中 PingAgent（smoke 阶段注册唯一）
   │ 2. PingAgent.run(envelope)
   │      ├─ registry.update_heartbeat()
   │      ├─ llm.chat([{role:"user", content: "ping"}])  ← OpenAI 兼容
   │      └─ publish reply envelope { action="skill.completed",
   │                                  target={type:"gateway", id:"smoke"},
   │                                  payload={ reply: "...pong..." } }
   │
   ▼
gateway 轮询路由 /api/profile/init/{trace_id}/status
   │ 4. Redis 查 status:trace_id → completed / running / failed
   │ 5. 返回 { status, reply, ... }
```

### 4.4 路由表

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/healthz` | liveness（仅返回 200） |
| GET | `/readyz` | readiness（检查 PG/Redis/RabbitMQ 连接） |
| POST | `/api/profile/init` | 触发 smoke skill，返回 trace_id |
| GET | `/api/profile/init/{trace_id}/status` | 状态查询 |

**Stage 2 暂不实现**：SSE / WebSocket 流式推送（推到 Stage 3）。

---

## 5. 错误处理、测试、可观测性

### 5.1 错误处理

**核心异常**（`core/errors.py`）：

```python
class ErrorCode(str, Enum):
    ENVELOPE_INVALID = "ENVELOPE_INVALID"
    SKILL_NOT_FOUND  = "SKILL_NOT_FOUND"
    AGENT_TIMEOUT    = "AGENT_TIMEOUT"
    AGENT_OVERLOAD   = "AGENT_OVERLOAD"
    LLM_RATE_LIMIT   = "LLM_RATE_LIMIT"
    LLM_UPSTREAM     = "LLM_UPSTREAM"
    DB_CONFLICT      = "DB_CONFLICT"
    INTERNAL         = "INTERNAL"

class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str, *, http_status: int = 500, **extra):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.extra = extra
```

**错误码 → HTTP 状态映射**：

| 错误码 | HTTP | 触发场景 |
| --- | --- | --- |
| `ENVELOPE_INVALID` | 400 | 信封字段缺失 / 类型错 |
| `SKILL_NOT_FOUND` | 422 | SkillBasedScheduler 找不到匹配 Agent |
| `AGENT_TIMEOUT` | 504 | Agent 运行超过 15s |
| `AGENT_OVERLOAD` | 503 | 队列满 / Agent concurrency 满 |
| `LLM_RATE_LIMIT` | 429 | LLM 429 |
| `LLM_UPSTREAM` | 502 | LLM 5xx / 网络错 |
| `DB_CONFLICT` | 409 | 唯一约束冲突 |
| `INTERNAL` | 500 | 其他 |

**响应格式**：

```json
{ "error": { "code": "SKILL_NOT_FOUND", "message": "...", "trace_id": "..." } }
```

**Agent 层重试**：retry_count ≤ 3 进队列重投；> 3 进 DLQ 并发布 `skill.failed` 事件（信封 action=`skill.failed`）。

### 5.2 测试策略

**单元测试**（pytest + pytest-asyncio）：
- `test_envelope.py` — 信封序列化 / 反序列化 / trace_id 生成
- `test_skill_routing.py` — SkillBasedScheduler 按 skill 名匹配
- `test_registry.py` — Agent 注册 / 心跳 / 下线 / discover
- `test_llm_adapter.py` — OpenAI 兼容协议 mock 重放（respx / httpx mock）
- `test_circuit_breaker.py` — 熔断 open/half-open/close 转换

**集成测试**：
- `test_smoke.py` — 起真实 RabbitMQ + Redis + Postgres（testcontainers），跑 ping/pong 端到端

**覆盖率目标**：核心组件 > 70%，Stage 2 总体 ≥ 50%。

**每 task 验证**：`uv run mypy src` + `uv run pytest tests/unit -q` 必须 0 错。

### 5.3 可观测性

**OTel 埋点**：

| 位置 | Span 名 | 属性 |
| --- | --- | --- |
| Gateway REST | `http.{method}.{path}` | http.status_code, trace_id |
| Worker consume | `agent.consume` | agent.type, skill, envelope.trace_id |
| LLM 调用 | `llm.chat` | model, prompt_tokens, completion_tokens, latency_ms |
| DB 调用 | `db.{verb}` | db.system, db.statement |

**导出**：OTLP gRPC → Jaeger（4317 端口）；docker-compose 加 `jaeger` 服务。

**日志**：`core/logging.py` 输出 JSON 到 stdout，每条带 `trace_id` / `level` / `service`（gateway / worker）/ `msg`。

**Stage 2 验收**：Jaeger UI 上能看到 smoke 一次完整调用链（gateway → broker → worker → llm → reply）。

---

## 6. 验收（不可漏）

### 6.1 必过清单

- [ ] `docker compose up -d` 启动 7 个服务（PG/Redis/Qdrant/MinIO/Jaeger/gateway/worker）
- [ ] `alembic upgrade head` 成功，2 张表创建
- [ ] `curl /healthz` 返回 200
- [ ] `curl /readyz` 返回 200（PG/Redis/RabbitMQ 连接正常）
- [ ] `scripts/smoke.sh` 端到端通过：
  - POST /api/profile/init 拿到 trace_id
  - GET /api/profile/init/{trace_id}/status 轮询（每 500ms 一次，硬超时 10s）内收到 completed
  - reply 字段非空且包含 "pong"
- [ ] Jaeger UI 上能看到 smoke 完整 trace
- [ ] `uv run mypy src` 0 错误（strict 模式）
- [ ] `uv run pytest tests/unit -q` 全绿
- [ ] `uv run pytest tests/integration/test_smoke.py -q` 全绿
- [ ] `backend/README.md` 写明启动步骤 + smoke 用法 + 决策表

### 6.2 不允许出现

- ❌ 任何鉴权 / 登录 / Token / JWT / OAuth 代码（参见 [[no-auth-no-login]]）
- ❌ 业务逻辑实现（关卡 / 画像生成算法 / 藏宝图生成 / 评审）—— Stage 3+ 范畴
- ❌ WebSocket / SSE 流式推送 —— Stage 3 范畴
- ❌ 17 个 REST 端点的非 smoke 部分 —— Stage 3+ 范畴
- ❌ 业务表（除 students + profiles）—— Stage 3+ 范畴

### 6.3 风险与应对

| 风险 | 概率 | 应对 |
| --- | --- | --- |
| uv 在 Windows 平台兼容 | 中 | 备 pip + venv；CI 用 Linux |
| aio-pika 与 RabbitMQ 3.13+ 协议兼容性 | 低 | 锁定 `pika>=1.3,<2` / `aio-pika>=9.4` |
| OpenAI 兼容端点协议差异（DeepSeek vs 通义） | 中 | adapter 抽象化，统一 base_url / api_key 注入 |
| docker-compose 在 WSL / Windows 启动慢 | 中 | 文档写明 Linux 优先；Windows 用户用 WSL2 |
| mypy strict 模式对 SQLAlchemy 2.x ORM 误报 | 中 | 在 `pyproject.toml` 关 `disable_error_code = ["misc", "no-any-return"]` |

---

## 7. 与 v4 详细设计文档的一致性

本章为 v4 § 1.1、§ 2.1、§ 2.2、§ 2.6、§ 4.1（部分）、§ 4.2（部分）、§ 5.3（最小子集）、§ 5.4（最小子集）、§ 5.5（不实现）、§ 5.6（不实现）的**技术实现层细化**。

**未实现**（按范围外）：
- v4 § 2.4 核心协作流程
- v4 § 2.5 评审 Agent 协议
- v4 § 3.6 流式渲染协议（除 status polling）
- v4 § 3.13 关卡完整流程
- v4 § 5.5 向量存储（Stage 2 仅装 Qdrant 实例，不创建 collection）
- v4 § 5.6 三层存储一致性（Stage 2 仅写读穿透）
- v4 § 2.7 用户资源注入

---

## 8. 配套文档

- 实施计划：`docs/superpowers/plans/2026-07-11-stage2-backend-foundation.md`（待写）
- 验收报告：`docs/实施计划-Stage2-验收报告.md`（Stage 2 末尾产出）
- 决策记忆：`[[no-auth-no-login]]`

---

> 文档结束。本 spec 与 v4 详细设计文档 / 实施计划书配套，是 Stage 2 子项目的实施依据。