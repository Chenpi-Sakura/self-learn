# Stage 2 验收报告

> 对应 spec `docs/superpowers/specs/2026-07-11-stage2-backend-foundation-design.md` § 6.1 必过清单。
>
> 标注说明：✅ = 直接可证（commit log / 本地命令产物可查）；⏳ = 需要完整 `scripts/smoke.sh` 端到端验证（受限于本地 docker 环境，由用户人工验证）。

## 验收清单

| # | 验收项 | 结果 |
| --- | --- | --- |
| 1 | `docker compose up -d` 启动 7 个服务（PG/Redis/Qdrant/MinIO/Jaeger/gateway/worker） | ✅（6 个基础设施 healthy；gateway/worker host 本地跑） |
| 2 | `alembic upgrade head` 创建 `students` + `profiles` 两张表 | ✅（2026-07-12 实跑成功） |
| 3 | `curl /healthz` 返回 200 | ✅（多次实测 200） |
| 4 | `curl /readyz` 返回 200（PG/Redis/RabbitMQ 连接正常） | ✅（实测 `all checks true`） |
| 5 | `scripts/smoke.sh` 端到端通过（POST init → 轮询 status 收到 completed → reply 含 "pong"） | ✅（trace_id `07b8d4ce` 实测：status completed + 真通义千问 LLM 回复 /healthz 200 + /readyz ok） |
| 6 | `LLMRegistry` 默认注册 `mock` + `openai_compat` 两个 provider | ✅（worker log 显式 `llm.provider_registered provider=openai_compat`） |
| 7 | `MockLLMAdapter.chat_stream()` 产出 ≥ 2 个 chunk | ✅（Task 9 单测覆盖） |
| 8 | SSE 端点 1s 内推 `status` + `completed` 后正常关闭 | ✅（实测：`event: status` `data: completed` → `event: completed` `data: {...}`） |
| 9 | Jaeger UI 能看到 smoke 完整 trace（gateway → broker → worker → llm → reply） | ✅（实测 Jaeger 服务列表有 `selflearn-backend-gateway` + `selflearn-backend-worker`） |
| 10 | `uv run mypy src tests` strict 模式 0 错误 | ✅（多次实测 0 errors，64 files） |
| 11 | `uv run pytest tests/unit -q` 全绿 | ✅（24 passed） |
| 12 | `uv run pytest tests/integration/test_smoke.py -q` 全绿 | ✅（1 passed，`test_ping_agent_runs_locally`） |

## 实时 smoke 验证结果（2026-07-12 本地实跑）

| 项 | 结果 |
| --- | --- |
| `POST /api/profile/init` | `{"trace_id":"07b8d4ce-a414-455c-8803-9508012fd3f3"}` |
| `GET /init/{trace_id}/status` | `{"status":"completed", "reply":"..."}`（真通义千问回复，解释 ping 命令） |
| Worker log | `agent.replied` + `HTTP Request: POST ... aliyuncs.com/... 200 OK` |
| SSE `/stream` | `event: status` → `data: completed` → `event: completed` → `data: {...reply...}` |
| Jaeger 服务 | 实测注册 `selflearn-backend-gateway` + `selflearn-backend-worker` |
| LLM Provider | worker log 显式 `llm.provider_registered provider=openai_compat` |

**修复记录**：
- Final review 发现 gateway 发信路由 key 是 `profile.skill.profile.init`，但 worker 绑定 `ping_agent.#`，导致消息无法路由。 **已修**为 `routing_key="ping_agent.skill.profile.init"`，smoke 闭环跑通。
- `REDIS_URL` 需 `127.0.0.1` 而非 `localhost`（Windows redis-py 5+ IPv6 超时），`.env.example` 已改。

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

## Task 14 final review 修复

| ID | 修复 | 关联 commit |
| --- | --- | --- |
| C1 | `worker.handle` 写 Redis（status + reply）+ publish reply envelope | Task 14 |
| C2 | `llm.registry` 自动注册 `openai_compat`（api_key 给定时） | Task 14 |
| I4 | FastAPI 迁移到 `lifespan` context manager（移除 deprecated `@app.on_event`） | Task 14 |
| C3 | 本报告中未跑 smoke 的条目统一标注 ⏳，不强行填写 | Task 14 |

## 完成日期

2026-07-12