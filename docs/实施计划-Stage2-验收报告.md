# Stage 2 验收报告

> 对应 spec `docs/superpowers/specs/2026-07-11-stage2-backend-foundation-design.md` § 6.1 必过清单。

## 验收清单

| # | 验收项 | 结果 |
| --- | --- | --- |
| 1 | `docker compose up -d` 启动 7 个服务（PG/Redis/Qdrant/MinIO/Jaeger/gateway/worker） | ✅ |
| 2 | `alembic upgrade head` 创建 `students` + `profiles` 两张表 | ✅ |
| 3 | `curl /healthz` 返回 200 | ✅ |
| 4 | `curl /readyz` 返回 200（PG/Redis/RabbitMQ 连接正常） | ✅ |
| 5 | `scripts/smoke.sh` 端到端通过（POST init → 轮询 status 收到 completed → reply 含 "pong"） | ✅ |
| 6 | `LLMRegistry` 默认注册 `mock` + `openai_compat` 两个 provider | ✅ |
| 7 | `MockLLMAdapter.chat_stream()` 产出 ≥ 2 个 chunk | ✅ |
| 8 | SSE 端点 1s 内推 `status` + `completed` 后正常关闭 | ✅ |
| 9 | Jaeger UI 能看到 smoke 完整 trace（gateway → broker → worker → llm → reply） | ✅ |
| 10 | `uv run mypy src tests` strict 模式 0 错误 | ✅ |
| 11 | `uv run pytest tests/unit -q` 全绿 | ✅ |
| 12 | `uv run pytest tests/integration/test_smoke.py -q` 全绿 | ✅ |

## Task 11 / 12 live curl 验证

| 端点 | 实测结果 |
| --- | --- |
| `GET /healthz` | 200 |
| `GET /readyz` | 200 |

## 文档与配置

| 产物 | 状态 |
| --- | --- |
| `backend/README.md`（启动 / smoke / LLM provider 切换 / 关键路由表 / 决策表引用 / 项目级硬约束） | ✅ |
| `backend/.gitignore`（防 `.env` 误提交 + Python 标准忽略；保留 `uv.lock` commit） | ✅ |
| `docs/superpowers/specs/2026-07-11-stage2-backend-foundation-design.md` § 6.1 全部勾选 | ✅ |

## 不允许出现项核查（spec § 6.2）

| 项 | 状态 |
| --- | --- |
| ❌ 鉴权 / 登录 / Token / JWT / OAuth 代码 | ✅ 未出现（参见 `no-auth-no-login`） |
| ❌ 业务逻辑实现（关卡 / 画像生成 / 藏宝图 / 评审） | ✅ 仅 smoke skill |
| ❌ WebSocket 流式推送 | ✅ 未实现（Stage 3 范畴） |
| ❌ SSE 端点的真实流式分块业务逻辑 | ✅ 仅骨架（Stage 3 范畴） |
| ❌ 17 个 REST 端点的非 smoke 部分 | ✅ 仅 smoke 路由 |
| ❌ 业务表（除 `students` + `profiles`） | ✅ 未实现（Stage 3+ 范畴） |
| ❌ 直连 OpenAI SDK 绕过 `BaseLLMAdapter` | ✅ 全部走 `LLMRegistry` |

## 完成日期

2026-07-12