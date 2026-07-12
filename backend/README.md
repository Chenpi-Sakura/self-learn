# selflearn 后端（Stage 2）

Stage 2 后端地基：消息总线、Agent Runtime、LLM 抽象层、REST 路由、smoke 闭环。

> **项目级硬约束**：本项目所有阶段**完全不做鉴权 / 登录 / Token / JWT / OAuth**（参见项目记忆 `no-auth-no-login`）。

---

## 启动

```bash
cd backend

# 1. 复制环境变量模板
cp .env.example .env

# 2. 启动基础设施（PostgreSQL / Redis / Qdrant / MinIO / RabbitMQ / Jaeger）
docker compose up -d

# 3. 等待服务健康后执行数据库迁移
uv run alembic upgrade head

# 4. 写入 demo student（用于 smoke 验证）
uv run python -m scripts.seed_dev

# 5. 构建并启动 gateway + worker
docker compose up -d --build gateway worker
```

> **Windows 用户**：建议使用 WSL2。直接 docker-compose 在 Windows 上拉镜像较慢。

---

## 端到端 smoke

```bash
cd backend
bash scripts/smoke.sh
```

脚本会：
1. 起 6 个基础设施服务（PG / Redis / Qdrant / MinIO / RabbitMQ / Jaeger）
2. 等待健康检查通过
3. 执行 Alembic 迁移 + seed demo student
4. 构建并启动 gateway + worker
5. `POST /api/profile/init` → 拿 trace_id
6. 轮询 `/api/profile/init/{trace_id}/status`（硬超时 10s）直到 `completed`
7. 校验 reply 包含 `pong`
8. `curl -N /api/profile/init/{trace_id}/stream` 验证 SSE 至少推送一条 `completed` 事件

---

## 切换 LLM Provider

`LLMRegistry` 默认注册 `mock` + `openai_compat` 两个 provider。`.env` 配置：

```env
# 默认 provider：mock / openai_compat / ifly_spark
LLM_DEFAULT_PROVIDER=mock

# OpenAI 兼容 provider（DeepSeek / 通义千问 / OpenAI）
LLM_OPENAI_COMPAT_BASE_URL=https://api.deepseek.com/v1
LLM_OPENAI_COMPAT_API_KEY=sk-xxx
LLM_OPENAI_COMPAT_MODEL=deepseek-chat

# 熔断器（连续失败次数 / 冷却时间）
LLM_CB_FAILURE_THRESHOLD=5
LLM_CB_COOLDOWN_SECONDS=30
```

`ifly_spark` provider 仅占位（`health()` 返回 False），凭据依赖 Stage 5 接入。

---

## 关键路由

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/healthz` | liveness（仅返回 200） |
| GET | `/readyz` | readiness（检查 PG/Redis/RabbitMQ 连接） |
| POST | `/api/profile/init` | 触发 smoke skill（`skill.profile.init`），返回 `trace_id` |
| GET | `/api/profile/init/{trace_id}/status` | 状态查询（polling 兼容） |
| GET | `/api/profile/init/{trace_id}/stream` | SSE 流式（Stage 2 仅推 `status` + `completed` 事件；流式分块逻辑推到 Stage 3） |

Stage 2 不实现 WebSocket 流式推送。

---

## 决策表

见 `docs/superpowers/specs/2026-07-11-stage2-backend-foundation-design.md` § 2。8 项核心决策：

1. Agent 框架：自研 `BaseAgent`
2. 消息总线：RabbitMQ
3. LLM 主路径：OpenAI 兼容（DeepSeek / 通义千问）
4. Web 框架：FastAPI
5. 鉴权：**不做**（项目级硬约束）
6. 容器化：docker-compose
7. ORM：SQLAlchemy 2.x async + Alembic
8. 监控：OTel + Jaeger

外加：LLM 抽象（`BaseLLMAdapter` + `LLMRegistry`）+ SSE 骨架（端点契约提前定）。

---

## 测试与质量门

```bash
cd backend

# mypy strict 模式（关闭 misc / no-any-return 以兼容 SQLAlchemy 2.x）
uv run mypy src tests

# 单元测试
uv run pytest tests/unit -q

# 集成测试（testcontainers 起真实 PG/Redis/RabbitMQ）
uv run pytest tests/integration -q

# 全套
uv run pytest -q
```

预期：mypy 0 错 + pytest 全绿。

---

## 可观测性

- **OTel**：通过 OTLP gRPC 导出到 Jaeger（端口 4317）
- **Jaeger UI**：http://localhost:16686 —— 可看到 smoke 完整调用链（gateway → broker → worker → llm → reply）
- **日志**：`core/logging.py` 输出 JSON 到 stdout，每条带 `trace_id` / `level` / `service` / `msg`

---

## 目录结构

```
backend/
├── pyproject.toml        # uv 项目
├── uv.lock               # lock（须 commit）
├── README.md             # 本文件
├── .env.example          # 环境变量模板
├── .gitignore            # 防 .env / __pycache__ 等误提交
├── docker-compose.yml    # 7 服务编排
├── Dockerfile            # gateway + worker 共享镜像
├── alembic.ini
├── migrations/versions/  # Alembic
├── scripts/
│   ├── seed_dev.py       # 种子 demo student
│   └── smoke.sh          # 端到端 smoke
├── src/selflearn/
│   ├── main.py           # --role=gateway|worker|all
│   ├── config.py
│   ├── core/             # envelope / errors / logging / tracing
│   ├── gateway/          # FastAPI 装配 + 路由
│   ├── agents/           # BaseAgent + Scheduler + Worker + Registry
│   ├── llm/              # BaseLLMAdapter + Registry + adapters
│   ├── skills/           # @skill 装饰器 + 内置 skill
│   ├── mcp/              # 占位（Stage 3+）
│   ├── infra/            # db / redis / qdrant / minio / rabbit
│   ├── domain/           # ORM 模型（Stage 2: student + profile）
│   └── schemas/          # Pydantic
└── tests/
    ├── unit/             # 9 个单测文件
    └── integration/      # test_smoke.py（testcontainers）
```

---

## 项目级硬约束

> **完全不做鉴权 / 登录 / 会话 / Token / OAuth / JWT / refresh token / `auth.py` 任何形式。**

- 学生以业务字段 `student_id` 标识，请求体或路径直接传入
- 后端不做"这是谁"的判断；不存在 `Depends(get_current_user)`
- v4 详细设计文档 § 4.2 中涉及 `/api/auth/*` 的端点全部不实现
- v4 § 2.4.1 "初次登录 → 画像构建" 改写为"首次访问 → 画像构建"（无登录步骤）

详见项目记忆 `no-auth-no-login`。

---

## Stage 3+ 待办（不在 Stage 2 范围）

- 17 个 REST 端点完整实现
- SSE 流式分块 + 重连机制（Worker 端 `chat_stream` → Redis Stream → Gateway SSE）
- 8 个内容子 Agent（文档 / 导图 / 习题 / 代码 / 评审 / 画像 / 规划 / 总监）
- Skill 全集 + MCP Tool 全集
- 讯飞星火 provider 实装
- TTS / ASR（Stage 5）
- 评估模块 / 仪表盘 / k8s

详见 spec § 1.2。