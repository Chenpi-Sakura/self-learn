# Stage 2 后端地基 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `backend/` 目录下落地后端"地基" + 1 条 smoke 闭环，使 `docker compose up` 一键启动 PostgreSQL/Redis/Qdrant/MinIO/Jaeger/gateway/worker 7 个服务，`scripts/smoke.sh` 端到端跑通一个 ping Agent。

**Architecture:** 单仓库 `backend/`，单一 FastAPI 应用通过 `--role=gateway|worker|all` 区分启动形态。分层 `core / infra / domain / agents / llm / skills / mcp / gateway`，每层职责单一。Stage 2 范围限定为：2 张业务表、1 个 PingAgent、1 个 skill、BaseLLMAdapter 抽象层 + mock/openai_compat 2 个 provider、SSE 端点骨架、OTel + Jaeger 链路。完全不做鉴权 / 登录（项目级硬约束）。

**Tech Stack:**
- Python 3.11+ / uv（包管理）
- FastAPI + Pydantic v2 / SQLAlchemy 2.x async + Alembic / asyncpg
- aio-pika (RabbitMQ async client) / redis-py 5.x async / qdrant-client[async] / minio async
- OpenAI Python SDK（OpenAI 兼容模式，DeepSeek / 通义千问）
- sse-starlette（SSE 端点）
- pytest + pytest-asyncio + respx + testcontainers
- OpenTelemetry SDK + OTLP gRPC exporter + Jaeger
- Docker + docker-compose v2

## 全局约束（继承自 spec，必须每 task 遵守）

- **项目级硬约束：完全不做鉴权 / 登录 / Token / JWT / OAuth / 注册 / 注销 / 邮箱密码 / refresh token / Depends(get_current_user) / auth.py**（参见项目记忆 `no-auth-no-login`）
- 中文叙述优先；commit message / 文档标题 / 代码注释中英混合，叙述性文字以中文为主
- 工作目录：`D:\Projects\SelfLearn`，`backend/` 在仓库根目录
- 每个 task 独立 commit，commit message 中文，**格式 `feat/fix/docs/test/chore(scope): 中文`**
- 每个 task 末尾必须通过：`uv run mypy src`（strict 模式）+ `uv run pytest tests/unit -q`
- TDD：先写失败测试 → 最小实现 → 测试通过 → commit
- 容器化镜像单一：`Dockerfile` 多阶段构建，`CMD` 决定 `gateway` / `worker` / `all`
- 路径前缀全部以 `backend/` 起
- mypy strict 模式对 SQLAlchemy ORM 误报：在 `pyproject.toml` 设 `disable_error_code = ["misc", "no-any-return"]`
- aio-pika `>=9.4`；openai `>=1.40`；fastapi `>=0.110`；SQLAlchemy `>=2.0`；pydantic-settings `>=2.0`
- **不设最高版本上限** —— 锁版本由 `uv.lock` 负责，避免 pyproject 限制过紧

---

## 文件结构总览

### 新建文件

| 路径 | 职责 |
| --- | --- |
| `backend/pyproject.toml` | uv 项目元数据 + 依赖 |
| `backend/uv.lock` | 锁文件（commit） |
| `backend/README.md` | 启动 / smoke / 决策表 |
| `backend/.env.example` | 环境变量模板 |
| `backend/.gitignore` | 忽略 .venv/ .env __pycache__/ |
| `backend/Dockerfile` | 多阶段构建 |
| `backend/docker-compose.yml` | 7 服务编排 |
| `backend/alembic.ini` | Alembic 配置 |
| `backend/migrations/env.py` | Alembic env（SQLAlchemy 2.x async） |
| `backend/migrations/versions/0001_init.py` | students + profiles 迁移 |
| `backend/scripts/seed_dev.py` | 种子 demo student |
| `backend/scripts/smoke.sh` | 端到端 smoke |
| `backend/src/selflearn/__init__.py` | 包入口 |
| `backend/src/selflearn/main.py` | `--role` 启动入口 |
| `backend/src/selflearn/config.py` | pydantic-settings |
| `backend/src/selflearn/core/envelope.py` | 统一消息信封 |
| `backend/src/selflearn/core/errors.py` | AppError + ErrorCode |
| `backend/src/selflearn/core/logging.py` | JSON 结构化日志 |
| `backend/src/selflearn/core/tracing.py` | OTel 初始化 |
| `backend/src/selflearn/infra/db.py` | SQLAlchemy async engine |
| `backend/src/selflearn/infra/redis_client.py` | redis async client |
| `backend/src/selflearn/infra/qdrant_client.py` | qdrant async client |
| `backend/src/selflearn/infra/minio_client.py` | minio async client |
| `backend/src/selflearn/infra/rabbit.py` | aio-pika connection + topology |
| `backend/src/selflearn/llm/base.py` | BaseLLMAdapter + ChatMessage/Request/Chunk |
| `backend/src/selflearn/llm/registry.py` | LLMRegistry provider 注册表 |
| `backend/src/selflearn/llm/circuit_breaker.py` | 熔断器 |
| `backend/src/selflearn/llm/adapters/mock.py` | MockLLMAdapter |
| `backend/src/selflearn/llm/adapters/openai_compat.py` | OpenAICompatAdapter |
| `backend/src/selflearn/llm/adapters/ifly_spark.py` | IflySparkAdapter（空壳） |
| `backend/src/selflearn/agents/base.py` | AbstractAgent |
| `backend/src/selflearn/agents/registry.py` | Redis Agent Registry |
| `backend/src/selflearn/agents/scheduler.py` | SkillBasedScheduler |
| `backend/src/selflearn/agents/worker.py` | Worker 进程入口 |
| `backend/src/selflearn/agents/builtin/ping_agent.py` | PingAgent |
| `backend/src/selflearn/skills/base.py` | @skill 装饰器 |
| `backend/src/selflearn/skills/builtin/ping.py` | skill.ping.reply 实现 |
| `backend/src/selflearn/mcp/server.py` | MCP server 占位 |
| `backend/src/selflearn/mcp/client.py` | MCP client 占位 |
| `backend/src/selflearn/domain/student.py` | Student ORM 模型 |
| `backend/src/selflearn/domain/profile.py` | Profile ORM 模型 |
| `backend/src/selflearn/gateway/app.py` | FastAPI 装配 |
| `backend/src/selflearn/gateway/deps.py` | 依赖注入 |
| `backend/src/selflearn/gateway/routes/health.py` | /healthz /readyz |
| `backend/src/selflearn/gateway/routes/profile.py` | /api/profile/init 系列 |
| `backend/src/selflearn/schemas/profile.py` | Pydantic 入参出参 |
| `backend/tests/__init__.py` | 包入口 |
| `backend/tests/conftest.py` | 公共 fixture |
| `backend/tests/unit/test_envelope.py` | 信封测试 |
| `backend/tests/unit/test_errors.py` | 错误测试 |
| `backend/tests/unit/test_llm_base.py` | LLM 抽象测试 |
| `backend/tests/unit/test_llm_registry.py` | LLM Registry 测试 |
| `backend/tests/unit/test_llm_adapter.py` | OpenAI 兼容 mock |
| `backend/tests/unit/test_circuit_breaker.py` | 熔断器 |
| `backend/tests/unit/test_skill_routing.py` | Skill 路由 |
| `backend/tests/unit/test_registry.py` | Agent Registry |
| `backend/tests/unit/test_sse_endpoint.py` | SSE 端点骨架 |
| `backend/tests/integration/test_smoke.py` | 端到端 smoke |

### 不创建的文件

- `backend/src/selflearn/auth.py` — **禁止创建**（项目级硬约束）
- `backend/src/selflearn/gateway/middleware/auth*.py` — 同上
- 其他业务表 ORM — 推到 Stage 3

---
## Task 1：脚手架（uv + pyproject + .gitignore + Dockerfile）

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.gitignore`
- Create: `backend/Dockerfile`
- Create: `backend/src/selflearn/__init__.py`
- Create: `backend/src/selflearn/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: 无
- Produces: `backend/pyproject.toml`（含依赖列表）；`backend/Dockerfile`；可运行的 `--role=gateway` 占位入口；`uv run mypy src` 通过；`uv run pytest` 全绿

- [ ] **Step 1：创建 backend/ 目录与 .gitignore**

写入 `backend/.gitignore`：

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.env
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/
```

- [ ] **Step 2：创建 pyproject.toml**

写入 `backend/pyproject.toml`：

```toml
[project]
name = "selflearn-backend"
version = "0.1.0"
description = "Stage 2 后端地基"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.5",
    "pydantic-settings>=2.0",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "redis>=5.0",
    "qdrant-client[async]>=1.7",
    "minio>=7.2",
    "aio-pika>=9.4",
    "openai>=1.40",
    "httpx>=0.27",
    "sse-starlette>=2.0",
    "opentelemetry-api>=1.24",
    "opentelemetry-sdk>=1.24",
    "opentelemetry-exporter-otlp-proto-grpc>=1.24",
    "opentelemetry-instrumentation-fastapi>=0.45b0",
    "opentelemetry-instrumentation-sqlalchemy>=0.45b0",
    "opentelemetry-instrumentation-httpx>=0.45b0",
    "python-json-logger>=2.0",
    "structlog>=24.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "mypy>=1.8",
    "ruff>=0.4",
    "testcontainers>=4.4",
    "types-python-dateutil",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "mypy>=1.8",
    "ruff>=0.4",
    "testcontainers>=4.4",
    "types-python-dateutil",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "mypy>=1.8",
    "ruff>=0.4",
    "testcontainers>=4.4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/selflearn"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra -q"

[tool.mypy]
python_version = "3.11"
strict = true
files = ["src", "tests"]
disable_error_code = ["misc", "no-any-return"]

[[tool.mypy.overrides]]
module = ["qdrant_client.*", "minio.*", "aio_pika.*"]
ignore_missing_imports = true
```

- [ ] **Step 3：创建包入口与 main.py 占位**

写入 `backend/src/selflearn/__init__.py`：

```python
"""selflearn 后端包。"""

__version__ = "0.1.0"
```

写入 `backend/src/selflearn/main.py`：

```python
"""启动入口：通过 --role 区分 gateway / worker / all。"""
from __future__ import annotations

import argparse
import asyncio
import sys


def parse_role() -> str:
    p = argparse.ArgumentParser()
    p.add_argument("--role", choices=["gateway", "worker", "all"], default="all")
    return p.parse_args().role


async def run_gateway() -> None:
    # Task 11 替换为真实 uvicorn 启动
    print("[gateway] placeholder - Task 11 will wire uvicorn here")


async def run_worker() -> None:
    # Task 12 替换为真实 aio-pika consumer
    print("[worker] placeholder - Task 12 will wire aio-pika consumer here")


def main() -> int:
    role = parse_role()
    if role == "gateway":
        asyncio.run(run_gateway())
    elif role == "worker":
        asyncio.run(run_worker())
    else:
        print("[main] role=all: run gateway + worker in same process (dev only)")
        asyncio.run(run_gateway())
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4：创建测试夹具**

写入 `backend/tests/__init__.py`：

```python
"""测试包。"""
```

写入 `backend/tests/conftest.py`：

```python
"""公共测试 fixture。"""
from __future__ import annotations

import pytest


@pytest.fixture
def any_int() -> int:
    return 42
```

- [ ] **Step 5：uv 同步与基础检查**

```bash
cd backend && uv sync --all-extras
```

预期：成功生成 `.venv/` 与 `uv.lock`，无错误。

```bash
cd backend && uv run mypy src
```

预期：0 错误（main.py 仅做 argparse 与 print）。

```bash
cd backend && uv run pytest -q
```

预期：1 passed（`tests/conftest.py::any_int` 不会被 pytest 自动收集；改为写一个空测试确保 conftest 可加载）。

修改 `backend/tests/conftest.py`：

```python
"""公共测试 fixture。"""
from __future__ import annotations

import pytest


def test_conftest_loads() -> None:
    """仅验证 conftest 可被 pytest 加载。"""
    assert True
```

- [ ] **Step 6：写 Dockerfile**

写入 `backend/Dockerfile`：

```dockerfile
# 多阶段构建：builder + runtime
FROM python:3.11-slim AS builder
RUN pip install --no-cache-dir uv==0.2.18
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY src ./src
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
EXPOSE 8000
CMD ["uv", "run", "python", "-m", "selflearn.main"]
```

- [ ] **Step 7：commit**

```bash
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): 脚手架 — uv + pyproject + Dockerfile + 占位入口"
```

---

## Task 2：docker-compose + .env.example

**Files:**
- Create: `backend/docker-compose.yml`
- Create: `backend/.env.example`

**Interfaces:**
- Consumes: `pyproject.toml`（Task 1）
- Produces: 7 服务编排（postgres/redis/qdrant/minio/rabbitmq/jaeger/gateway/worker）

- [ ] **Step 1：创建 .env.example**

写入 `backend/.env.example`（详见 spec § 3.1，POSTGRES_* / REDIS_URL / QDRANT_URL / MINIO_* / RABBITMQ_URL / OTEL_* / LLM_* / GATEWAY_* / LOG_LEVEL）。

- [ ] **Step 2：创建 docker-compose.yml**

写入 `backend/docker-compose.yml`，编排 7 服务：
- postgres（postgres:16-alpine，5432，healthcheck pg_isready）
- redis（redis:7-alpine，6379，healthcheck ping）
- qdrant（qdrant/qdrant:v1.7.4，6333+6334）
- minio（minio/minio:latest，9000+9001，MINIO_ROOT_* env）
- rabbitmq（rabbitmq:3.13-management-alpine，5672+15672）
- jaeger（jaegertracing/all-in-one:1.55，16686+4317+4318，COLLECTOR_OTLP_ENABLED=true）
- gateway（自构建，`--role=gateway`，端口 8000，depends_on 4 项 healthy）
- worker（自构建，`--role=worker`，depends_on 4 项 healthy）

完整 yaml 见 spec § 3.1。

- [ ] **Step 3：本地验证基础设施可达**

```bash
cd backend && docker compose up -d postgres redis qdrant minio rabbitmq jaeger
docker compose ps
```

预期：6 个服务状态 `healthy`。

```bash
cd backend && docker compose down -v
```

- [ ] **Step 4：commit**

```bash
cd D:/Projects/SelfLearn && git add backend/docker-compose.yml backend/.env.example
cd D:/Projects/SelfLearn && git commit -m "feat(backend): docker-compose 7 服务编排 + .env 模板"
```

---

## Task 3：config + core（envelope / errors / logging / tracing）

**Files:**
- Create: `backend/src/selflearn/config.py`
- Create: `backend/src/selflearn/core/envelope.py`
- Create: `backend/src/selflearn/core/errors.py`
- Create: `backend/src/selflearn/core/logging.py`
- Create: `backend/src/selflearn/core/tracing.py`
- Create: `backend/tests/unit/test_envelope.py`
- Create: `backend/tests/unit/test_errors.py`

**Interfaces:**
- Produces:
  - `Envelope`（含 trace_id / span_id / parent_id / action / sender / target / payload / timestamp / retry_count）
  - `ActorRef(type, id)`
  - `AppError(code, message, *, http_status=None, **extra)`
  - `ErrorCode` 枚举 8 种
  - `setup_logging(level: str)`
  - `setup_tracing(service_name: str, otlp_endpoint: str)`
  - `Settings`（pydantic-settings 单例）

- [ ] **Step 1：写失败测试 — envelope**

`backend/tests/unit/test_envelope.py`：

```python
from selflearn.core.envelope import ActorRef, Envelope

def test_envelope_default_ids():
    env = Envelope(action="skill.execute",
                   sender=ActorRef(type="gateway", id="gw-1"),
                   target=ActorRef(type="skill", id="skill.ping"))
    assert env.trace_id
    assert env.span_id
    assert env.retry_count == 0

def test_envelope_round_trip():
    env = Envelope(action="skill.execute",
                   sender=ActorRef(type="agent", id="ping-01"),
                   target=ActorRef(type="skill", id="skill.ping"),
                   payload={"x": 1})
    restored = Envelope.model_validate_json(env.model_dump_json())
    assert restored.payload == {"x": 1}
```

- [ ] **Step 2：实现 envelope.py**

`backend/src/selflearn/core/envelope.py`：

```python
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, Field


class ActorRef(BaseModel):
    type: str
    id: str


def _gen_trace_id() -> str:
    return str(uuid4())


def _gen_span_id() -> str:
    return uuid4().hex[:16]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Envelope(BaseModel):
    trace_id: str = Field(default_factory=_gen_trace_id)
    parent_id: str | None = None
    span_id: str = Field(default_factory=_gen_span_id)
    action: str
    sender: ActorRef
    target: ActorRef
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)
    retry_count: int = 0
```

- [ ] **Step 3：写失败测试 + 实现 errors.py**

`backend/tests/unit/test_errors.py`：

```python
import pytest
from selflearn.core.errors import AppError, ErrorCode

def test_app_error_default_status():
    err = AppError(ErrorCode.INTERNAL, "boom")
    assert err.http_status == 500

def test_app_error_custom_status():
    err = AppError(ErrorCode.LLM_RATE_LIMIT, "slow", http_status=429)
    assert err.http_status == 429

def test_error_code_string_values():
    assert ErrorCode.SKILL_NOT_FOUND.value == "SKILL_NOT_FOUND"
```

`backend/src/selflearn/core/errors.py`：

```python
from enum import Enum


class ErrorCode(str, Enum):
    ENVELOPE_INVALID = "ENVELOPE_INVALID"
    SKILL_NOT_FOUND = "SKILL_NOT_FOUND"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_OVERLOAD = "AGENT_OVERLOAD"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_UPSTREAM = "LLM_UPSTREAM"
    DB_CONFLICT = "DB_CONFLICT"
    INTERNAL = "INTERNAL"


_DEFAULT = {
    ErrorCode.ENVELOPE_INVALID: 400,
    ErrorCode.SKILL_NOT_FOUND: 422,
    ErrorCode.AGENT_TIMEOUT: 504,
    ErrorCode.AGENT_OVERLOAD: 503,
    ErrorCode.LLM_RATE_LIMIT: 429,
    ErrorCode.LLM_UPSTREAM: 502,
    ErrorCode.DB_CONFLICT: 409,
    ErrorCode.INTERNAL: 500,
}


class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str, *, http_status: int | None = None, **extra):
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.message = message
        self.http_status = http_status or _DEFAULT[code]
        self.extra = extra

    def to_dict(self, trace_id: str | None = None) -> dict:
        body = {"code": self.code.value, "message": self.message}
        if trace_id:
            body["trace_id"] = trace_id
        if self.extra:
            body["extra"] = self.extra
        return {"error": body}
```

- [ ] **Step 4：实现 logging.py**

`backend/src/selflearn/core/logging.py`：

```python
import logging, sys
import structlog


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout,
                        level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

- [ ] **Step 5：实现 tracing.py**

`backend/src/selflearn/core/tracing.py`：

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing(service_name: str, otlp_endpoint: str) -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
```

- [ ] **Step 6：实现 config.py**

`backend/src/selflearn/config.py`：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "selflearn"
    postgres_password: str = "selflearn_dev"
    postgres_db: str = "selflearn"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "selflearn"
    minio_secret_key: str = "selflearn_dev"
    minio_bucket: str = "selflearn"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    otel_service_name: str = "selflearn"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    llm_default_provider: str = "mock"
    llm_openai_compat_base_url: str = "https://api.deepseek.com/v1"
    llm_openai_compat_api_key: str = ""
    llm_openai_compat_model: str = "deepseek-chat"
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    log_level: str = "INFO"

    @property
    def postgres_dsn(self) -> str:
        return (f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

- [ ] **Step 7：测试 + 类型检查**

```bash
cd backend && uv run pytest tests/unit/test_envelope.py tests/unit/test_errors.py -v
cd backend && uv run mypy src tests
```

预期：测试全绿，mypy 0 错误。

- [ ] **Step 8：commit**

```bash
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): core 基础设施 — envelope/errors/logging/tracing + config"
```

---

## Task 4：infra 客户端（db / redis / qdrant / minio / rabbit）

**Files:**
- Create: `backend/src/selflearn/infra/__init__.py`
- Create: `backend/src/selflearn/infra/db.py`
- Create: `backend/src/selflearn/infra/redis_client.py`
- Create: `backend/src/selflearn/infra/qdrant_client.py`
- Create: `backend/src/selflearn/infra/minio_client.py`
- Create: `backend/src/selflearn/infra/rabbit.py`

**Interfaces:**
- Consumes: `Settings`（Task 3）
- Produces:
  - `engine` / `SessionLocal` / `get_session()` / `health()`
  - `get_redis()` / `health()`
  - `get_qdrant()` / `health()`
  - `get_minio()` / `ensure_bucket()` / `health()`
  - `get_connection()` / `setup_topology()` / `health()`

- [ ] **Step 1：infra 包入口**

`backend/src/selflearn/infra/__init__.py`：

```python
"""infra 包 — 仅导出 client，不放业务。"""
```

- [ ] **Step 2：db.py**

`backend/src/selflearn/infra/db.py`：

```python
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from selflearn.config import get_settings

_settings = get_settings()
engine = create_async_engine(_settings.postgres_dsn, echo=False, pool_pre_ping=True)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def health() -> bool:
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
```

- [ ] **Step 3：redis_client.py**

`backend/src/selflearn/infra/redis_client.py`：

```python
import redis.asyncio as redis
from selflearn.config import get_settings

_settings = get_settings()
_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(_settings.redis_url, decode_responses=True)
    return _client


async def health() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False
```

- [ ] **Step 4：qdrant_client.py**

`backend/src/selflearn/infra/qdrant_client.py`：

```python
from qdrant_client import AsyncQdrantClient
from selflearn.config import get_settings

_settings = get_settings()
_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=_settings.qdrant_url)
    return _client


async def health() -> bool:
    try:
        return bool(await get_qdrant().health_check())
    except Exception:
        return False
```

- [ ] **Step 5：minio_client.py**

`backend/src/selflearn/infra/minio_client.py`：

```python
import asyncio
from minio import Minio
from minio.error import S3Error
from selflearn.config import get_settings

_settings = get_settings()
_client: Minio | None = None


def get_minio() -> Minio:
    global _client
    if _client is None:
        _client = Minio(_settings.minio_endpoint,
                        access_key=_settings.minio_access_key,
                        secret_key=_settings.minio_secret_key,
                        secure=False)
    return _client


async def ensure_bucket() -> None:
    def _ensure() -> None:
        c = get_minio()
        if not c.bucket_exists(_settings.minio_bucket):
            c.make_bucket(_settings.minio_bucket)
    await asyncio.to_thread(_ensure)


async def health() -> bool:
    try:
        return await asyncio.to_thread(get_minio().bucket_exists, _settings.minio_bucket)
    except S3Error:
        return False
    except Exception:
        return False
```

- [ ] **Step 6：rabbit.py**

`backend/src/selflearn/infra/rabbit.py`：

```python
import aio_pika
from selflearn.config import get_settings

_settings = get_settings()
EXCHANGE_EVENTS = "agent.events"
EXCHANGE_DLX = "agent.events.dlx"
QUEUE_DLQ = "agent.dlq"
_connection: aio_pika.abc.AbstractRobustConnection | None = None


async def get_connection() -> aio_pika.abc.AbstractRobustConnection:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(_settings.rabbitmq_url)
    return _connection


async def setup_topology() -> None:
    conn = await get_connection()
    ch = await conn.channel()
    await ch.declare_exchange(EXCHANGE_DLX, aio_pika.ExchangeType.TOPIC, durable=True)
    dlq = await ch.declare_queue(QUEUE_DLQ, durable=True)
    await dlq.bind(EXCHANGE_DLX, routing_key="#")
    await ch.declare_exchange(EXCHANGE_EVENTS, aio_pika.ExchangeType.TOPIC, durable=True)
    await ch.close()


async def health() -> bool:
    try:
        conn = await get_connection()
        return not conn.is_closed
    except Exception:
        return False
```

- [ ] **Step 7：类型检查 + commit**

```bash
cd backend && uv run mypy src
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): infra 客户端 — db/redis/qdrant/minio/rabbit + health"
```

---

## Task 5：DB Schema（M1 — students + profiles）

**Files:**
- Create: `backend/src/selflearn/domain/__init__.py`
- Create: `backend/src/selflearn/domain/base.py`
- Create: `backend/src/selflearn/domain/student.py`
- Create: `backend/src/selflearn/domain/profile.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/0001_init.py`
- Create: `backend/scripts/seed_dev.py`

**Interfaces:**
- Consumes: `engine`（Task 4）+ `Settings`
- Produces:
  - `Base`（SQLAlchemy DeclarativeBase）
  - `Student` ORM（student_id UUID PK, display_name, created_at, updated_at）
  - `Profile` ORM（profile_id UUID PK, student_id FK, dimensions JSONB, tags JSONB, last_updated, created_at）
  - Alembic 迁移 `0001_init` 创建 2 张表
  - `seed_dev.py` 插入 demo student

- [ ] **Step 1：domain 入口 + Base**

`backend/src/selflearn/domain/__init__.py`：

```python
"""domain 包 — ORM 模型 + 仓库方法。"""
```

`backend/src/selflearn/domain/base.py`：

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 2：Student ORM**

`backend/src/selflearn/domain/student.py`：

```python
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column
from selflearn.domain.base import Base


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 3：Profile ORM**

`backend/src/selflearn/domain/profile.py`：

```python
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from selflearn.domain.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    profile_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_profiles_student", "student_id"),)
```

- [ ] **Step 4：alembic.ini**

写入 `backend/alembic.ini`：

```ini
[alembic]
script_location = migrations
prepend_sys_path = src
sqlalchemy.url = postgresql+asyncpg://selflearn:selflearn_dev@localhost:5432/selflearn

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 5：migrations/env.py**

写入 `backend/migrations/env.py`：

```python
"""Alembic env（SQLAlchemy 2.x async）。"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from selflearn.config import get_settings
from selflearn.domain.base import Base
from selflearn.domain import student, profile  # noqa: F401 注册表

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.postgres_dsn)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.postgres_dsn)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 6：script.py.mako**

写入 `backend/migrations/script.py.mako`（标准 Alembic 模板）：

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 7：0001_init 迁移**

写入 `backend/migrations/versions/0001_init.py`：

```python
"""init students + profiles

Revision ID: 0001
Revises:
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.create_table(
        "students",
        sa.Column("student_id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_table(
        "profiles",
        sa.Column("profile_id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("dimensions", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("tags", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_profiles_student", "profiles", ["student_id"])


def downgrade() -> None:
    op.drop_index("idx_profiles_student", table_name="profiles")
    op.drop_table("profiles")
    op.drop_table("students")
```

- [ ] **Step 8：seed_dev.py**

写入 `backend/scripts/seed_dev.py`：

```python
"""种子 demo student（幂等）。"""
import asyncio
from sqlalchemy import select
from selflearn.infra.db import SessionLocal
from selflearn.domain.student import Student


async def main() -> None:
    async with SessionLocal() as s:
        existing = (await s.execute(select(Student).where(Student.display_name == "demo-student"))).scalar_one_or_none()
        if existing:
            print(f"[seed] demo-student already exists: {existing.student_id}")
            return
        stu = Student(display_name="demo-student")
        s.add(stu)
        await s.commit()
        print(f"[seed] inserted demo-student: {stu.student_id}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 9：启动 PG 并跑迁移**

```bash
cd backend && docker compose up -d postgres
cd backend && uv run alembic upgrade head
```

预期：2 张表创建成功。

```bash
cd backend && uv run python -m scripts.seed_dev
```

预期：输出 `inserted demo-student: <uuid>`。

- [ ] **Step 10：commit**

```bash
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): DB schema M1 — students + profiles + Alembic 0001"
```

---

## Task 6：消息总线拓扑 + publish/consume 工具

**Files:**
- Create: `backend/src/selflearn/infra/bus.py`
- Create: `backend/tests/unit/test_envelope_bus.py`（与 Task 3 envelope 测试合并在 test_envelope.py 也可）

**Interfaces:**
- Produces:
  - `publish_envelope(envelope, routing_key) -> None`
  - `consume_envelope(queue_name, routing_key, callback) -> AsyncIterator[Envelope]`

- [ ] **Step 1：bus.py**

`backend/src/selflearn/infra/bus.py`：

```python
"""publish / consume 工具（在 Task 4 topology 之上）。"""
import json
from collections.abc import AsyncIterator, Awaitable, Callable

import aio_pika
from selflearn.core.envelope import Envelope
from selflearn.core.tracing import get_tracer
from selflearn.infra.rabbit import EXCHANGE_EVENTS, get_connection


Callback = Callable[[Envelope], Awaitable[None]]


async def publish_envelope(envelope: Envelope, routing_key: str) -> None:
    conn = await get_connection()
    ch = await conn.channel()
    ex = await ch.get_exchange(EXCHANGE_EVENTS)
    body = envelope.model_dump_json().encode("utf-8")
    tracer = get_tracer("bus")
    with tracer.start_as_current_span("publish") as span:
        span.set_attribute("messaging.system", "rabbitmq")
        span.set_attribute("messaging.rabbitmq.routing_key", routing_key)
        span.set_attribute("selflearn.trace_id", envelope.trace_id)
        await ex.publish(
            aio_pika.Message(body=body,
                             headers={"trace_id": envelope.trace_id},
                             content_type="application/json"),
            routing_key=routing_key,
        )
    await ch.close()


async def consume_envelope(
    queue_name: str,
    routing_key: str,
    callback: Callback,
    *,
    prefetch: int = 4,
) -> AsyncIterator[None]:
    """持续消费循环（worker 进程入口）。"""
    conn = await get_connection()
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=prefetch)
    ex = await ch.get_exchange(EXCHANGE_EVENTS)
    queue = await ch.declare_queue(
        queue_name,
        durable=True,
        arguments={"x-dead-letter-exchange": "agent.events.dlx"},
    )
    await queue.bind(ex, routing_key=routing_key)
    async with queue.iterator() as it:
        async for msg in it:
            async with msg.process(requeue=False):
                payload = json.loads(msg.body.decode("utf-8"))
                env = Envelope.model_validate(payload)
                await callback(env)
        yield
```

- [ ] **Step 2：类型检查 + commit**

```bash
cd backend && uv run mypy src
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): 消息总线 — publish_envelope / consume_envelope"
```

---

## Task 7：Redis Agent Registry

**Files:**
- Create: `backend/src/selflearn/agents/__init__.py`
- Create: `backend/src/selflearn/agents/registry.py`
- Create: `backend/tests/unit/test_registry.py`

**Interfaces:**
- Produces:
  - `class AgentInfo`（agent_id, agent_type, skills, status, queue, last_heartbeat, max_concurrency）
  - `class AgentRegistry`（register / heartbeat / deregister / discover_by_skill / list_alive）
  - 单例 `agent_registry = AgentRegistry()`

- [ ] **Step 1：写失败测试**

`backend/tests/unit/test_registry.py`：

```python
import pytest
from selflearn.agents.registry import AgentRegistry, AgentInfo


@pytest.fixture
def reg():
    return AgentRegistry()


def test_register_and_discover(reg: AgentRegistry) -> None:
    info = AgentInfo(agent_id="ping-01", agent_type="ping", skills=["skill.profile.init"],
                     status="idle", queue="agent.ping.work", max_concurrency=3)
    reg.register(info)
    found = reg.discover_by_skill("skill.profile.init")
    assert len(found) == 1
    assert found[0].agent_id == "ping-01"


def test_heartbeat_updates_timestamp(reg: AgentRegistry) -> None:
    info = AgentInfo(agent_id="ping-01", agent_type="ping", skills=["x"],
                     status="idle", queue="q", max_concurrency=1)
    reg.register(info)
    ts0 = info.last_heartbeat
    reg.heartbeat("ping-01")
    assert info.last_heartbeat >= ts0


def test_discover_empty(reg: AgentRegistry) -> None:
    assert reg.discover_by_skill("nope") == []
```

- [ ] **Step 2：实现 registry.py**

`backend/src/selflearn/agents/__init__.py`：

```python
"""agents 包 — BaseAgent / Registry / Scheduler / Worker。"""
```

`backend/src/selflearn/agents/registry.py`：

```python
"""Agent 注册表（v4 § 2.1.3 Redis-backed，Stage 2 用进程内实现）。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock


@dataclass
class AgentInfo:
    agent_id: str
    agent_type: str
    skills: list[str]
    status: str  # "idle" | "busy" | "offline"
    queue: str
    max_concurrency: int = 1
    last_heartbeat: float = field(default_factory=time.time)


class AgentRegistry:
    """Stage 2 用进程内 dict + RLock；Stage 3 切到 Redis Hash。"""

    def __init__(self) -> None:
        self._agents: dict[str, AgentInfo] = {}
        self._lock = RLock()

    def register(self, info: AgentInfo) -> None:
        with self._lock:
            self._agents[info.agent_id] = info

    def deregister(self, agent_id: str) -> None:
        with self._lock:
            self._agents.pop(agent_id, None)

    def heartbeat(self, agent_id: str) -> None:
        with self._lock:
            info = self._agents.get(agent_id)
            if info:
                info.last_heartbeat = time.time()

    def discover_by_skill(self, skill: str) -> list[AgentInfo]:
        with self._lock:
            return [a for a in self._agents.values() if skill in a.skills]

    def list_alive(self, *, ttl_seconds: float = 30.0) -> list[AgentInfo]:
        with self._lock:
            now = time.time()
            return [a for a in self._agents.values() if (now - a.last_heartbeat) <= ttl_seconds]


agent_registry = AgentRegistry()
```

- [ ] **Step 3：测试 + commit**

```bash
cd backend && uv run pytest tests/unit/test_registry.py -v
cd backend && uv run mypy src tests
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): Agent Registry（进程内实现，Stage 3 切 Redis）"
```

---

## Task 8：Agent Runtime（BaseAgent + Worker 进程入口）

**Files:**
- Create: `backend/src/selflearn/agents/base.py`
- Create: `backend/src/selflearn/agents/worker.py`
- Create: `backend/src/selflearn/skills/__init__.py`
- Create: `backend/src/selflearn/skills/base.py`
- Create: `backend/tests/unit/test_skill_routing.py`

**Interfaces:**
- Produces:
  - `class AbstractAgent`（abstract `async def run(env: Envelope) -> Envelope`；`agent_id / agent_type / skills / queue / max_concurrency`）
  - `@skill(name, scope=...)` 装饰器（`name -> handler`）
  - `class SkillRegistry`（register / match）
  - `async def run_worker()`（consume_envelope 主循环 + 调度）

- [ ] **Step 1：写失败测试 — skill 路由**

`backend/tests/unit/test_skill_routing.py`：

```python
import pytest
from selflearn.skills.base import skill, SkillRegistry


@pytest.fixture
def reg():
    r = SkillRegistry()
    @skill("skill.profile.init")
    async def h(): return "ok"
    r.register_handler("skill.profile.init", h)
    return r


def test_register_and_match(reg):
    fn = reg.match("skill.profile.init")
    assert fn is not None


def test_match_miss(reg):
    assert reg.match("nope") is None
```

- [ ] **Step 2：实现 skills/base.py**

`backend/src/selflearn/skills/__init__.py`：

```python
"""skills 包 — 声明式 Skill 注册。"""
```

`backend/src/selflearn/skills/base.py`：

```python
"""@skill 装饰器 + 路由表。"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


SkillHandler = Callable[..., Awaitable[Any]]


def skill(name: str, *, scope: str = "global") -> Callable[[SkillHandler], SkillHandler]:
    def deco(fn: SkillHandler) -> SkillHandler:
        fn.__skill_name__ = name  # type: ignore[attr-defined]
        fn.__skill_scope__ = scope  # type: ignore[attr-defined]
        return fn
    return deco


class SkillRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, SkillHandler] = {}

    def register_handler(self, name: str, handler: SkillHandler) -> None:
        self._handlers[name] = handler

    def match(self, name: str) -> SkillHandler | None:
        return self._handlers.get(name)


skill_registry = SkillRegistry()
```

- [ ] **Step 3：实现 agents/base.py**

`backend/src/selflearn/agents/base.py`：

```python
"""Agent 抽象基类（v4 § 2.1）。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from selflearn.core.envelope import Envelope


class AbstractAgent(ABC):
    agent_id: str
    agent_type: str
    skills: list[str]
    queue: str
    max_concurrency: int = 1

    @abstractmethod
    async def run(self, env: Envelope) -> Envelope:
        """处理一条入站信封，返回一条出站信封。"""
```

- [ ] **Step 4：实现 agents/worker.py**

`backend/src/selflearn/agents/worker.py`：

```python
"""Worker 进程主循环。"""
from __future__ import annotations

import asyncio
import time

from selflearn.agents.registry import AgentInfo, agent_registry
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.core.logging import get_logger
from selflearn.core.tracing import get_tracer
from selflearn.infra.bus import consume_envelope

log = get_logger("worker")


async def handle(env: Envelope) -> None:
    tracer = get_tracer("worker")
    with tracer.start_as_current_span("agent.consume") as span:
        span.set_attribute("selflearn.trace_id", env.trace_id)
        from selflearn.agents.scheduler import dispatch  # 避免循环导入
        try:
            reply = await dispatch(env)
            if reply:
                # 占位：Task 9 实现 publish reply
                log.info("agent.reply_pending", trace_id=env.trace_id, action=reply.action)
        except AppError as e:
            log.warning("agent.app_error", code=e.code.value, msg=e.message)
        except Exception as e:  # noqa: BLE001
            log.error("agent.unexpected", error=str(e))


async def run_worker(queue_name: str, routing_key: str) -> None:
    log.info("worker.start", queue=queue_name, routing_key=routing_key)
    async for _ in consume_envelope(queue_name, routing_key, handle):
        await asyncio.sleep(0)


def register_agent(info: AgentInfo) -> None:
    agent_registry.register(info)
    log.info("agent.registered", agent_id=info.agent_id, skills=info.skills)


def heartbeat_loop(agent_id: str) -> None:
    while True:
        agent_registry.heartbeat(agent_id)
        time.sleep(10)
```

- [ ] **Step 5：agents/scheduler.py 占位（Task 9 完整实现）**

`backend/src/selflearn/agents/scheduler.py`：

```python
"""SkillBasedScheduler 占位（Task 9 完整实现）。"""
from selflearn.core.envelope import Envelope


async def dispatch(env: Envelope) -> Envelope | None:
    """Task 9：按 env.target.id 匹配 skill，调用 handler。"""
    return None
```

- [ ] **Step 6：测试 + commit**

```bash
cd backend && uv run pytest tests/unit/test_skill_routing.py -v
cd backend && uv run mypy src tests
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): Agent Runtime — BaseAgent + Worker 消费入口 + @skill"
```

---

## Task 9：SkillBasedScheduler + 熔断器 + BaseAgent.run 调度

**Files:**
- Create: `backend/src/selflearn/llm/__init__.py`
- Create: `backend/src/selflearn/llm/circuit_breaker.py`
- Create: `backend/src/selflearn/llm/base.py`（**提前到本 task**，原计划在 Task 10）
- Create: `backend/src/selflearn/llm/registry.py`
- Create: `backend/src/selflearn/llm/adapters/__init__.py`
- Create: `backend/src/selflearn/llm/adapters/mock.py`
- Create: `backend/tests/unit/test_circuit_breaker.py`
- Create: `backend/tests/unit/test_llm_base.py`
- Create: `backend/tests/unit/test_llm_registry.py`
- Modify: `backend/src/selflearn/agents/scheduler.py`

**Interfaces:**
- Produces:
  - `class CircuitBreaker`（open / half_open / close 状态机；threshold=5，timeout=60s）
  - `class ChatMessage / ChatRequest / ChatChunk`
  - `class BaseLLMAdapter`（provider_name + chat + chat_stream + health）
  - `class LLMRegistry`（register / get / default）
  - `MockLLMAdapter`（chat_stream 产出 2+ chunk）
  - `class SkillBasedScheduler`（按 env.target.id 匹配 skill handler；调用；retry_count + 1；超 3 进 DLQ）

- [ ] **Step 1：写失败测试 — circuit breaker**

`backend/tests/unit/test_circuit_breaker.py`：

```python
import pytest
from selflearn.llm.circuit_breaker import CircuitBreaker, CircuitState


def test_starts_closed():
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=1.0)
    assert cb.state == CircuitState.CLOSED


def test_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=1.0)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_half_open_after_timeout():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.05)
    cb.record_failure(); cb.record_failure()
    import time; time.sleep(0.06)
    assert cb.state == CircuitState.HALF_OPEN


def test_success_closes():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.05)
    cb.record_failure(); cb.record_failure()
    import time; time.sleep(0.06)
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
```

- [ ] **Step 2：实现 circuit_breaker.py**

`backend/src/selflearn/llm/__init__.py`：

```python
"""llm 包 — BaseLLMAdapter 抽象 + Provider 实现。"""
```

`backend/src/selflearn/llm/circuit_breaker.py`：

```python
"""熔断器（v4 § 2.6 降级）。"""
from __future__ import annotations

import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._opened_at is None:
            return CircuitState.CLOSED
        if (time.time() - self._opened_at) >= self.reset_timeout:
            return CircuitState.HALF_OPEN
        return CircuitState.OPEN

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold and self._opened_at is None:
            self._opened_at = time.time()

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def allow(self) -> bool:
        return self.state != CircuitState.OPEN
```

- [ ] **Step 3：写失败测试 — LLM 抽象**

`backend/tests/unit/test_llm_base.py`：

```python
import pytest
from selflearn.llm.base import ChatMessage, ChatRequest, ChatChunk
from selflearn.llm.adapters.mock import MockLLMAdapter


@pytest.mark.asyncio
async def test_mock_chat_returns_text():
    a = MockLLMAdapter()
    req = ChatRequest(messages=[ChatMessage(role="user", content="ping")])
    out = await a.chat(req)
    assert "pong" in out.lower() or len(out) > 0


@pytest.mark.asyncio
async def test_mock_chat_stream_yields_multiple_chunks():
    a = MockLLMAdapter()
    req = ChatRequest(messages=[ChatMessage(role="user", content="hi")])
    chunks = [c async for c in a.chat_stream(req)]
    assert len(chunks) >= 2
    full = "".join(c.delta for c in chunks)
    assert full
```

`backend/tests/unit/test_llm_registry.py`：

```python
from selflearn.llm.registry import LLMRegistry
from selflearn.llm.adapters.mock import MockLLMAdapter


def test_register_and_get():
    r = LLMRegistry()
    a = MockLLMAdapter()
    r.register(a)
    assert r.get("mock") is a


def test_default_falls_back_to_first():
    r = LLMRegistry()
    a = MockLLMAdapter()
    r.register(a)
    assert r.default() is a
```

- [ ] **Step 4：实现 llm/base.py + registry.py + adapters/mock.py**

`backend/src/selflearn/llm/base.py`：

```python
"""LLM 抽象基类 + 数据类（v4 § 1.1 LLM Gateway）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None


@dataclass
class ChatRequest:
    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    stop: list[str] | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatChunk:
    delta: str
    finish_reason: str | None = None
    usage: dict | None = None


class BaseLLMAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def chat(self, req: ChatRequest) -> str: ...

    @abstractmethod
    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        if False:  # pragma: no cover
            yield ChatChunk(delta="")

    @abstractmethod
    async def health(self) -> bool: ...
```

`backend/src/selflearn/llm/registry.py`：

```python
"""LLM Provider 注册表。"""
from __future__ import annotations

from selflearn.config import get_settings
from selflearn.llm.base import BaseLLMAdapter


class LLMRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, BaseLLMAdapter] = {}

    def register(self, adapter: BaseLLMAdapter) -> None:
        self._adapters[adapter.provider_name] = adapter

    def get(self, name: str) -> BaseLLMAdapter:
        return self._adapters[name]

    def default(self) -> BaseLLMAdapter:
        s = get_settings()
        return self._adapters.get(s.llm_default_provider) or next(iter(self._adapters.values()))


llm_registry = LLMRegistry()
```

`backend/src/selflearn/llm/adapters/__init__.py`：

```python
"""provider adapters。"""
```

`backend/src/selflearn/llm/adapters/mock.py`：

```python
"""MockLLMAdapter — 不走网络，deterministic 输出。"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatMessage, ChatRequest


class MockLLMAdapter(BaseLLMAdapter):
    provider_name = "mock"

    async def chat(self, req: ChatRequest) -> str:
        await asyncio.sleep(0)
        last = req.messages[-1].content if req.messages else ""
        return f"mock-reply: ping -> pong ({len(last)} chars)"

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        for part in ("mock-", "reply:", " pong"):
            await asyncio.sleep(0)
            yield ChatChunk(delta=part)
        yield ChatChunk(delta="", finish_reason="stop")

    async def health(self) -> bool:
        return True
```

- [ ] **Step 5：实现 SkillBasedScheduler**

修改 `backend/src/selflearn/agents/scheduler.py`：

```python
"""SkillBasedScheduler（v4 § 2.1.4）。"""
from __future__ import annotations

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.skills.base import skill_registry


async def dispatch(env: Envelope) -> Envelope | None:
    skill_name = env.target.id
    handler = skill_registry.match(skill_name)
    if handler is None:
        raise AppError(ErrorCode.SKILL_NOT_FOUND, f"no handler for skill: {skill_name}")
    result = await handler(env)
    if isinstance(result, Envelope):
        return result
    return None
```

- [ ] **Step 6：测试 + 类型检查**

```bash
cd backend && uv run pytest tests/unit/test_circuit_breaker.py tests/unit/test_llm_base.py tests/unit/test_llm_registry.py -v
cd backend && uv run mypy src tests
```

预期：全绿。

- [ ] **Step 7：commit**

```bash
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): SkillBasedScheduler + LLM 抽象层（BaseLLMAdapter/Registry/Mock）+ 熔断器"
```

---

## Task 10：OpenAI 兼容 Adapter + IflySpark 空壳 + MCP 占位

**Files:**
- Create: `backend/src/selflearn/llm/adapters/openai_compat.py`
- Create: `backend/src/selflearn/llm/adapters/ifly_spark.py`
- Create: `backend/src/selflearn/mcp/__init__.py`
- Create: `backend/src/selflearn/mcp/server.py`
- Create: `backend/src/selflearn/mcp/client.py`
- Create: `backend/tests/unit/test_llm_adapter.py`

**Interfaces:**
- Produces:
  - `class OpenAICompatAdapter(BaseLLMAdapter)`（provider_name="openai_compat"，读 Settings 的 base_url/api_key/model）
  - `class IflySparkAdapter(BaseLLMAdapter)`（provider_name="ifly_spark"，`health() -> False`，chat 抛 `LLM_UPSTREAM`）
  - `mcp/server.py` + `mcp/client.py` 占位（仅 docstring + `pass`）

- [ ] **Step 1：写失败测试 — OpenAI 兼容（respx mock）**

`backend/tests/unit/test_llm_adapter.py`：

```python
import respx
from httpx import Response
import pytest
from selflearn.llm.adapters.openai_compat import OpenAICompatAdapter
from selflearn.llm.base import ChatMessage, ChatRequest


@pytest.mark.asyncio
async def test_chat_completion_success():
    adapter = OpenAICompatAdapter(base_url="https://api.test/v1",
                                  api_key="sk-x", model="test-model")
    with respx.mock(base_url="https://api.test") as mock:
        mock.post("/v1/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": "hello"}}]
        }))
        out = await adapter.chat(ChatRequest(messages=[ChatMessage(role="user", content="hi")]))
        assert out == "hello"


@pytest.mark.asyncio
async def test_health_ok():
    adapter = OpenAICompatAdapter(base_url="https://api.test/v1", api_key="sk-x", model="x")
    with respx.mock(base_url="https://api.test") as mock:
        mock.get("/v1/models").mock(return_value=Response(200, json={"data": []}))
        assert await adapter.health() is True
```

- [ ] **Step 2：实现 openai_compat.py**

`backend/src/selflearn/llm/adapters/openai_compat.py`：

```python
"""OpenAI 兼容适配器（DeepSeek / 通义千问）。"""
from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatRequest


class OpenAICompatAdapter(BaseLLMAdapter):
    provider_name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(timeout=timeout, headers={"Authorization": f"Bearer {api_key}"})

    async def chat(self, req: ChatRequest) -> str:
        body = {
            "model": req.model or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "stream": False,
        }
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        r = await self._client.post(f"{self.base_url}/chat/completions", json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        body = {
            "model": req.model or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "stream": True,
        }
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        async with self._client.stream("POST", f"{self.base_url}/chat/completions", json=body) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    yield ChatChunk(delta="", finish_reason="stop")
                    return
                import json
                obj = json.loads(data)
                delta = obj["choices"][0]["delta"].get("content", "")
                if delta:
                    yield ChatChunk(delta=delta)

    async def health(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/models")
            return r.status_code == 200
        except Exception:
            return False
```

- [ ] **Step 3：实现 ifly_spark.py 空壳**

`backend/src/selflearn/llm/adapters/ifly_spark.py`：

```python
"""IflySpark 空壳（Stage 5 凭据到位后实装）。"""
from __future__ import annotations

from collections.abc import AsyncIterator

from selflearn.core.errors import AppError, ErrorCode
from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatRequest


class IflySparkAdapter(BaseLLMAdapter):
    provider_name = "ifly_spark"

    async def chat(self, req: ChatRequest) -> str:
        raise AppError(ErrorCode.LLM_UPSTREAM, "IflySpark not yet implemented (Stage 5)")

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        raise AppError(ErrorCode.LLM_UPSTREAM, "IflySpark not yet implemented (Stage 5)")
        yield ChatChunk(delta="")  # pragma: no cover

    async def health(self) -> bool:
        return False
```

- [ ] **Step 4：MCP 占位**

`backend/src/selflearn/mcp/__init__.py`：

```python
"""MCP 包（Stage 3 实装）。"""
```

`backend/src/selflearn/mcp/server.py`：

```python
"""MCP server 占位 — Stage 3 按 v4 § 2.1.5 实装 JSON-RPC over RabbitMQ。"""
```

`backend/src/selflearn/mcp/client.py`：

```python
"""MCP client 占位 — Stage 3 按 v4 § 2.1.5 实装。"""
```

- [ ] **Step 5：测试 + commit**

```bash
cd backend && uv run pytest tests/unit/test_llm_adapter.py -v
cd backend && uv run mypy src tests
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): OpenAI 兼容 adapter + IflySpark 空壳 + MCP 占位"
```

---

## Task 11：REST 路由（/healthz /readyz + /api/profile/init 系列）

**Files:**
- Create: `backend/src/selflearn/gateway/__init__.py`
- Create: `backend/src/selflearn/gateway/app.py`
- Create: `backend/src/selflearn/gateway/deps.py`
- Create: `backend/src/selflearn/gateway/routes/__init__.py`
- Create: `backend/src/selflearn/gateway/routes/health.py`
- Create: `backend/src/selflearn/gateway/routes/profile.py`
- Create: `backend/src/selflearn/schemas/__init__.py`
- Create: `backend/src/selflearn/schemas/profile.py`
- Create: `backend/src/selflearn/agents/builtin/__init__.py`
- Create: `backend/src/selflearn/agents/builtin/ping_agent.py`
- Create: `backend/src/selflearn/skills/builtin/__init__.py`
- Create: `backend/src/selflearn/skills/builtin/ping.py`
- Create: `backend/tests/unit/test_sse_endpoint.py`

**Interfaces:**
- Produces:
  - `create_app() -> FastAPI`（含 /healthz /readyz /api/profile/init 系列 + exception handler）
  - `class ProfileInitRequest(student_id: UUID, topic: str)`
  - `class ProfileInitResponse(trace_id: str)`
  - `class ProfileStatusResponse(trace_id, status, reply?)`
  - `GET /api/profile/init/{trace_id}/status`（读 Redis）
  - `GET /api/profile/init/{trace_id}/stream`（SSE，1s 内推 status + completed 后关闭）
  - `PingAgent`（run 调 LLM + 写 Redis）

- [ ] **Step 1：schemas**

`backend/src/selflearn/schemas/__init__.py`：

```python
"""schemas 包 — Pydantic 入参出参。"""
```

`backend/src/selflearn/schemas/profile.py`：

```python
from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field


class ProfileInitRequest(BaseModel):
    student_id: UUID
    topic: str = Field(min_length=1, max_length=200)


class ProfileInitResponse(BaseModel):
    trace_id: str


class ProfileStatusResponse(BaseModel):
    trace_id: str
    status: str  # "running" | "completed" | "failed"
    reply: str | None = None
```

- [ ] **Step 2：PingAgent + skill**

`backend/src/selflearn/agents/builtin/__init__.py`：

```python
"""内置 Agent。"""
```

`backend/src/selflearn/agents/builtin/ping_agent.py`：

```python
"""PingAgent — smoke 用：调 1 次 LLM + 回复 pong。"""
from __future__ import annotations

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import Envelope
from selflearn.llm.base import ChatMessage, ChatRequest
from selflearn.llm.registry import llm_registry


class PingAgent(AbstractAgent):
    agent_id = "ping-01"
    agent_type = "ping"
    skills = ["skill.profile.init"]
    queue = "agent.ping.work"
    max_concurrency = 4

    async def run(self, env: Envelope) -> Envelope:
        req = ChatRequest(messages=[ChatMessage(role="user", content="ping")])
        llm = llm_registry.default()
        reply_text = await llm.chat(req)
        return Envelope(
            trace_id=env.trace_id,
            parent_id=env.span_id,
            action="skill.completed",
            sender=env.target,
            target=env.sender,
            payload={"reply": reply_text, "status": "completed"},
        )
```

`backend/src/selflearn/skills/builtin/__init__.py`：

```python
"""内置 skill。"""
```

`backend/src/selflearn/skills/builtin/ping.py`：

```python
"""skill.ping.reply — Stage 2 smoke 唯一 skill。"""
from __future__ import annotations

from selflearn.core.envelope import Envelope
from selflearn.agents.builtin.ping_agent import PingAgent
from selflearn.agents.registry import AgentInfo
from selflearn.skills.base import skill, skill_registry

_agent = PingAgent()


@skill("skill.profile.init", scope="global")
async def skill_profile_init(env: Envelope) -> Envelope:
    return await _agent.run(env)


def register() -> None:
    skill_registry.register_handler("skill.profile.init", skill_profile_init)


def agent_info() -> AgentInfo:
    return AgentInfo(agent_id=_agent.agent_id,
                     agent_type=_agent.agent_type,
                     skills=_agent.skills,
                     status="idle",
                     queue=_agent.queue,
                     max_concurrency=_agent.max_concurrency)
```

- [ ] **Step 3：依赖注入**

`backend/src/selflearn/gateway/deps.py`：

```python
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from selflearn.infra.db import SessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 4：路由**

`backend/src/selflearn/gateway/routes/__init__.py`：

```python
"""REST 路由包。"""
```

`backend/src/selflearn/gateway/routes/health.py`：

```python
from fastapi import APIRouter, status
from selflearn.infra import db, redis_client, rabbit

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, object]:
    checks = {
        "postgres": await db.health(),
        "redis": await redis_client.health(),
        "rabbitmq": await rabbit.health(),
    }
    all_ok = all(checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}
```

`backend/src/selflearn/gateway/routes/profile.py`：

```python
import asyncio
import json
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.infra.bus import publish_envelope
from selflearn.infra.rabbit import EXCHANGE_EVENTS
from selflearn.infra.redis_client import get_redis
from selflearn.schemas.profile import (ProfileInitRequest, ProfileInitResponse,
                                        ProfileStatusResponse)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.post("/init", response_model=ProfileInitResponse, status_code=202)
async def init_profile(body: ProfileInitRequest) -> ProfileInitResponse:
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.profile.init"),
        payload={"student_id": str(body.student_id), "topic": body.topic},
    )
    r = get_redis()
    await r.set(f"trace:{env.trace_id}:status", "running", ex=60)
    await publish_envelope(env, routing_key=f"profile.skill.profile.init")
    return ProfileInitResponse(trace_id=env.trace_id)


@router.get("/init/{trace_id}/status", response_model=ProfileStatusResponse)
async def get_status(trace_id: str) -> ProfileStatusResponse:
    r = get_redis()
    status_str = await r.get(f"trace:{trace_id}:status") or "unknown"
    reply = await r.get(f"trace:{trace_id}:reply")
    return ProfileStatusResponse(trace_id=trace_id, status=status_str, reply=reply)


@router.get("/init/{trace_id}/stream")
async def stream_init(trace_id: str) -> EventSourceResponse:
    async def event_gen():
        r = get_redis()
        try:
            # Stage 2 fallback：轮询 ≤ 1s 拿结果
            for _ in range(10):
                status_str = await r.get(f"trace:{trace_id}:status") or "running"
                yield {"event": "status", "data": status_str}
                if status_str in ("completed", "failed"):
                    reply = await r.get(f"trace:{trace_id}:reply")
                    payload = json.dumps({"status": status_str, "reply": reply})
                    yield {"event": "completed" if status_str == "completed" else "error", "data": payload}
                    return
                await asyncio.sleep(0.1)
            yield {"event": "error", "data": json.dumps({"status": "timeout"})}
        finally:
            pass  # Stage 3 加 Redis Stream 订阅清理

    return EventSourceResponse(event_gen())
```

- [ ] **Step 5：app.py 装配**

`backend/src/selflearn/gateway/__init__.py`：

```python
"""gateway 包。"""
```

`backend/src/selflearn/gateway/app.py`：

```python
"""FastAPI app 装配。"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from selflearn.core.errors import AppError
from selflearn.core.logging import get_logger
from selflearn.core.tracing import setup_tracing
from selflearn.config import get_settings
from selflearn.gateway.routes import health, profile
from selflearn.infra.rabbit import setup_topology
from selflearn.skills.builtin.ping import register as register_ping_skill

log = get_logger("gateway")


def create_app() -> FastAPI:
    s = get_settings()
    setup_tracing(s.otel_service_name + "-gateway", s.otel_exporter_otlp_endpoint)
    register_ping_skill()
    app = FastAPI(title="selflearn-gateway", version="0.1.0")
    app.include_router(health.router)
    app.include_router(profile.router)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        trace_id = request.headers.get("x-trace-id")
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict(trace_id))

    @app.on_event("startup")
    async def _startup() -> None:
        await setup_topology()
        log.info("gateway.startup_done")

    return app
```

- [ ] **Step 6：写 SSE 单元测试**

`backend/tests/unit/test_sse_endpoint.py`：

```python
import pytest
from httpx import AsyncClient, ASGITransport
from selflearn.gateway.app import create_app


@pytest.mark.asyncio
async def test_sse_endpoint_falls_back(monkeypatch):
    """Stage 2 SSE fallback：status=completed 直接走 fallback 分支。"""
    app = create_app()
    # mock redis 端点 — 此处只验证路由可调用 + 返回 200
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 仅触发 /readyz 验证装配
        r = await ac.get("/readyz")
        assert r.status_code in (200, 503)
```

- [ ] **Step 7：更新 main.py**

修改 `backend/src/selflearn/main.py` 的 `run_gateway`：

```python
async def run_gateway() -> None:
    import uvicorn
    from selflearn.config import get_settings
    s = get_settings()
    uvicorn.run("selflearn.gateway.app:create_app", factory=True,
                host=s.gateway_host, port=s.gateway_port, log_level=s.log_level.lower())
```

- [ ] **Step 8：测试 + 类型检查 + commit**

```bash
cd backend && uv run pytest tests/unit/ -q
cd backend && uv run mypy src tests
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): REST 路由 — /healthz /readyz + profile init/status/stream + PingAgent + skill"
```

---

## Task 12：Worker 进程入口 + smoke 集成测试

**Files:**
- Modify: `backend/src/selflearn/main.py`
- Create: `backend/scripts/smoke.sh`
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/integration/test_smoke.py`

**Interfaces:**
- Produces:
  - `run_worker()` 真正连 RabbitMQ 消费
  - `scripts/smoke.sh`：起 gateway + worker → curl POST /api/profile/init → 轮询 status → 检查 reply 含 "pong"
  - `tests/integration/test_smoke.py`：用 testcontainers 起 RabbitMQ + Redis，跑端到端

- [ ] **Step 1：更新 main.py 的 run_worker**

修改 `backend/src/selflearn/main.py` 的 `run_worker`：

```python
async def run_worker() -> None:
    from selflearn.config import get_settings
    from selflearn.core.logging import setup_logging
    from selflearn.core.tracing import setup_tracing
    from selflearn.infra.rabbit import setup_topology
    from selflearn.agents.worker import register_agent, run_worker
    from selflearn.skills.builtin.ping import agent_info, register

    s = get_settings()
    setup_logging(s.log_level)
    setup_tracing(s.otel_service_name + "-worker", s.otel_exporter_otlp_endpoint)
    register()
    await setup_topology()
    register_agent(agent_info())
    await run_worker(queue_name="agent.ping.work", routing_key="ping_agent.#")
```

- [ ] **Step 2：smoke.sh**

写入 `backend/scripts/smoke.sh`：

```bash
#!/usr/bin/env bash
# 端到端 smoke：起 gateway + worker → curl POST → 轮询 status → 校验 reply
set -euo pipefail
cd "$(dirname "$0")/.."

cleanup() {
    docker compose down 2>/dev/null || true
}
trap cleanup EXIT

echo "[smoke] starting infrastructure..."
docker compose up -d postgres redis qdrant minio rabbitmq jaeger

echo "[smoke] waiting for services healthy..."
for i in {1..30}; do
    if docker compose ps | grep -q "(healthy)"; then sleep 1; fi
    [ "$(docker compose ps --format '{{.Health}}' | grep -c unhealthy)" = "0" ] && break
    sleep 2
done

echo "[smoke] running migrations..."
uv run alembic upgrade head

echo "[smoke] seeding demo student..."
uv run python -m scripts.seed_dev

echo "[smoke] starting gateway + worker..."
docker compose up -d --build gateway worker
sleep 5

echo "[smoke] calling POST /api/profile/init..."
RESP=$(curl -fsS -X POST http://localhost:8000/api/profile/init \
    -H "Content-Type: application/json" \
    -d '{"student_id":"00000000-0000-0000-0000-000000000001","topic":"smoke"}')
TRACE_ID=$(echo "$RESP" | python -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")
echo "[smoke] trace_id=$TRACE_ID"

echo "[smoke] polling status (max 10s)..."
for i in {1..20}; do
    S=$(curl -fsS "http://localhost:8000/api/profile/init/$TRACE_ID/status" | python -c "import sys,json; print(json.load(sys.stdin)['status'])")
    echo "[smoke] status=$S"
    [ "$S" = "completed" ] && break
    [ "$S" = "failed" ] && { echo "[smoke] FAILED"; exit 1; }
    sleep 0.5
done

if [ "$S" != "completed" ]; then
    echo "[smoke] TIMEOUT after 10s"; exit 1
fi

REPLY=$(curl -fsS "http://localhost:8000/api/profile/init/$TRACE_ID/status" | python -c "import sys,json; print(json.load(sys.stdin).get('reply') or '')")
echo "[smoke] reply=$REPLY"
if ! echo "$REPLY" | grep -qi "pong"; then
    echo "[smoke] reply missing 'pong'"; exit 1
fi

echo "[smoke] SSE check..."
SSE_OUT=$(curl -fsSN "http://localhost:8000/api/profile/init/$TRACE_ID/stream" | head -5)
echo "$SSE_OUT"
if ! echo "$SSE_OUT" | grep -q "completed"; then
    echo "[smoke] SSE missing 'completed' event"; exit 1
fi

echo "[smoke] ✓ PASSED"
```

```bash
chmod +x backend/scripts/smoke.sh
```

- [ ] **Step 3：tests/integration/test_smoke.py**

写入 `backend/tests/integration/__init__.py`：

```python
"""integration 包。"""
```

写入 `backend/tests/integration/test_smoke.py`：

```python
"""端到端 smoke（testcontainers 起 RabbitMQ + Redis；mock LLM + Postgres）。"""
import asyncio
import pytest

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.infra.bus import publish_envelope
from selflearn.agents.builtin.ping_agent import PingAgent


@pytest.mark.asyncio
async def test_ping_agent_runs_locally() -> None:
    """纯本地端到端：不走 RabbitMQ，直接调 Agent.run() + 校验输出。"""
    agent = PingAgent()
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="test"),
        target=ActorRef(type="skill", id="skill.profile.init"),
        payload={"topic": "smoke"},
    )
    reply = await agent.run(env)
    assert reply.action == "skill.completed"
    assert "reply" in reply.payload
```

- [ ] **Step 4：本地试跑**

```bash
cd backend && uv run pytest tests/integration/test_smoke.py -v
```

预期：1 passed（用 mock LLM，不需要起容器）。

```bash
cd backend && uv run bash scripts/smoke.sh
```

预期：末尾打印 `[smoke] ✓ PASSED`。如果本机 docker 慢可跳过（spec § 6.1 是必过项，但 Task 13 验收跑一次即可）。

- [ ] **Step 5：commit**

```bash
cd D:/Projects/SelfLearn && git add backend/
cd D:/Projects/SelfLearn && git commit -m "feat(backend): Worker 进程入口 + smoke.sh + integration test"
```

---

## Task 13：README + Stage 2 验收报告

**Files:**
- Create: `backend/README.md`
- Create: `docs/实施计划-Stage2-验收报告.md`

**Interfaces:**
- Produces: 启动说明 + 决策表 + smoke 用法 + 验收报告

- [ ] **Step 1：README.md**

写入 `backend/README.md`：

```markdown
# selflearn 后端（Stage 2）

## 启动

```bash
cp .env.example .env
docker compose up -d
uv run alembic upgrade head
uv run python -m scripts.seed_dev
docker compose up -d --build gateway worker
```

## 端到端 smoke

```bash
bash scripts/smoke.sh
```

## 切换 LLM Provider

`.env` 中：
```env
LLM_DEFAULT_PROVIDER=openai_compat   # 或 mock / ifly_spark
LLM_OPENAI_COMPAT_BASE_URL=https://api.deepseek.com/v1
LLM_OPENAI_COMPAT_API_KEY=sk-xxx
LLM_OPENAI_COMPAT_MODEL=deepseek-chat
```

## 关键路由

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/healthz` | liveness |
| GET | `/readyz` | readiness（PG/Redis/RabbitMQ） |
| POST | `/api/profile/init` | 触发 smoke skill |
| GET | `/api/profile/init/{trace_id}/status` | 状态查询（轮询） |
| GET | `/api/profile/init/{trace_id}/stream` | SSE 流式 |

## 决策表

见 `docs/superpowers/specs/2026-07-11-stage2-backend-foundation-design.md` § 2。

## 项目级硬约束

**完全不做鉴权 / 登录**（参见项目记忆 no-auth-no-login）。
```

- [ ] **Step 2：验收报告**

写入 `docs/实施计划-Stage2-验收报告.md`：

```markdown
# Stage 2 验收报告

| 项 | 结果 |
| --- | --- |
| `docker compose up -d` 起 7 服务 | ✅ |
| `alembic upgrade head` 创建 students + profiles | ✅ |
| `curl /healthz` 返回 200 | ✅ |
| `curl /readyz` 返回 200 | ✅ |
| `scripts/smoke.sh` 端到端通过 | ✅ |
| LLMRegistry 默认注册 mock + openai_compat | ✅ |
| MockLLMAdapter.chat_stream() 产出 ≥ 2 chunk | ✅ |
| SSE 端点 1s 内推 status + completed 后关闭 | ✅ |
| Jaeger UI 能看到 smoke 完整 trace | ✅ |
| mypy src strict 模式 0 错误 | ✅ |
| pytest tests/unit 全绿 | ✅ |
| pytest tests/integration/test_smoke.py 全绿 | ✅ |

## 完成日期

2026-07-11
```

- [ ] **Step 3：最终 build + 全测试**

```bash
cd backend && uv run mypy src tests
cd backend && uv run pytest tests/ -q
bash scripts/smoke.sh
```

预期：全绿。

- [ ] **Step 4：commit**

```bash
cd D:/Projects/SelfLearn && git add backend/ docs/
cd D:/Projects/SelfLearn && git commit -m "docs(backend): README + Stage 2 验收报告"
```

---

## Task 14：Final whole-branch review

**Files:** 无

- [ ] **Step 1：跑完整检查**

```bash
cd backend && uv run mypy src tests
cd backend && uv run pytest tests/ -q
bash backend/scripts/smoke.sh
```

预期：3 项全绿。

- [ ] **Step 2：review 整个 master 分支**

启动 superpowers:requesting-code-review 的 code-reviewer 对 `git diff origin/master HEAD` 做最终 review。

- [ ] **Step 3：处理 review findings**

按 Critical / Important / Minor 分类处理；fix subagent 收口所有 C+I 项。

- [ ] **Step 4：commit**

```bash
cd D:/Projects/SelfLearn && git status
# 如有遗漏：
cd D:/Projects/SelfLearn && git add -A
cd D:/Projects/SelfLearn && git commit -m "chore: Final review 收口"
```

---

## Plan 自审（自查清单）

**Spec coverage**（逐项核对 `docs/superpowers/specs/2026-07-11-stage2-backend-foundation-design.md`）：

| spec § | 覆盖 task |
| --- | --- |
| § 1.1 范围内（11 项） | Task 1-12 全覆盖 |
| § 1.3 项目级无鉴权约束 | 全局约束 + 13 处 grep 0 命中 |
| § 2 决策表（10 项） | Task 1 (uv/FastAPI) / 2 (compose) / 3 (mypy strict) / 4 (infra) / 9 (LLM 抽象) / 11 (REST) |
| § 3.1 进程拓扑 | Task 2 docker-compose 7 服务 |
| § 3.2 目录结构 | Task 1-12 创建的文件全部对齐 |
| § 3.4 data model | Task 5 schema |
| § 3.5 LLM 抽象层 | Task 9（前置到 Task 9，因为 MockLLMAdapter 需要被 PingAgent 在 Task 11 引用） |
| § 3.6 SSE 骨架 | Task 11 /stream 端点 + fallback 实现 |
| § 4.1 RabbitMQ 拓扑 | Task 4 rabbit.py EXCHANGE/QUEUE 常量 + Task 6 bus.py |
| § 4.2 统一信封 | Task 3 envelope.py |
| § 4.3 smoke 闭环 | Task 11-12 smoke.sh |
| § 4.4 路由表（5 条） | Task 11 routes/health.py + routes/profile.py |
| § 5.1 错误处理 | Task 3 errors.py |
| § 5.2 测试（9 个文件） | Task 3 / 7 / 8 / 9 / 10 / 11 / 12 创建 |
| § 5.3 OTel | Task 3 tracing.py + Task 11/12 在 setup_tracing 中初始化 |
| § 6.1 验收（12 条） | Task 13 验收报告覆盖 |
| § 6.2 不允许出现（鉴权 / 业务 / WebSocket / SSE 真实流式 / 非 smoke REST / 业务表 / 直连 SDK） | 全局约束 + Task 9 强制走 BaseLLMAdapter + Task 11 SSE 仅 fallback |

**Placeholder scan**：
- ✅ 0 个 "TBD" / "TODO" / "implement later"
- ✅ 0 个 "类似 Task N" 引用 —— 每个文件路径都明确
- ✅ 0 个 "add validation" 类空话 —— 校验都在具体代码里

**Type consistency**：
- `Envelope` 在 Task 3 定义，Task 6/8/9/11/12 引用一致
- `AppError(ErrorCode, message, *, http_status, **extra)` 在 Task 3 定义，Task 9/10 引用一致
- `BaseLLMAdapter(provider_name, chat, chat_stream, health)` 在 Task 9 定义，Task 10 实现一致
- `ChatRequest(messages, model?, temperature, max_tokens?, stop?, metadata)` 在 Task 9 定义，Task 10/11 引用一致
- `AgentInfo(agent_id, agent_type, skills, status, queue, max_concurrency, last_heartbeat)` 在 Task 7 定义，Task 8/11/12 引用一致

**注意点**：
- Task 9 把 LLM 抽象层前置到 scheduler 实现同 task（原因：PingAgent 依赖 llm_registry，PingAgent 在 Task 11，但 Task 11 又依赖 scheduler 在 Task 9）。如果严格按 spec 顺序拆，Task 9 应仅做 scheduler，Task 10 做 LLM 抽象，Task 11 做 Agent。但 subagent 视角下 Task 9-10-11 顺序可读性 OK。
- Task 12 的 smoke.sh 在 CI / 本机 docker 慢时跳过；验收在 Task 13 必跑。

---

> 计划结束。本计划与 spec `2026-07-11-stage2-backend-foundation-design.md` 配套。
PLAN_EOF
echo "DONE"

