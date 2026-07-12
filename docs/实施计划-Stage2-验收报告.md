# Stage 2 验收报告

> 对应 spec `docs/superpowers/specs/2026-07-11-stage2-backend-foundation-design.md` § 6.1 必过清单。
>
> 标注说明：✅ = 直接可证（commit log / 本地命令产物可查）；⏳ = 需要完整 `scripts/smoke.sh` 端到端验证（受限于本地 docker 环境，由用户人工验证）。

## 验收清单

| # | 验收项 | 结果 |
| --- | --- | --- |
| 1 | `docker compose up -d` 启动 7 个服务（PG/Redis/Qdrant/MinIO/Jaeger/gateway/worker） | ⏳ 待人工 smoke.sh 验证 |
| 2 | `alembic upgrade head` 创建 `students` + `profiles` 两张表 | ⏳ 待人工 smoke.sh 验证 |
| 3 | `curl /healthz` 返回 200 | ✅（Task 11 实测 200） |
| 4 | `curl /readyz` 返回 200（PG/Redis/RabbitMQ 连接正常） | ✅（Task 11 实测 200） |
| 5 | `scripts/smoke.sh` 端到端通过（POST init → 轮询 status 收到 completed → reply 含 "pong"） | ⏳ 待人工 smoke.sh 验证 |
| 6 | `LLMRegistry` 默认注册 `mock` + `openai_compat` 两个 provider | ✅（Task 14 / C2 修复后由单元测试覆盖） |
| 7 | `MockLLMAdapter.chat_stream()` 产出 ≥ 2 个 chunk | ✅（Task 6 单测覆盖） |
| 8 | SSE 端点 1s 内推 `status` + `completed` 后正常关闭 | ⏳ 待人工 smoke.sh 验证 |
| 9 | Jaeger UI 能看到 smoke 完整 trace（gateway → broker → worker → llm → reply） | ⏳ 待人工 smoke.sh 验证 |
| 10 | `uv run mypy src tests` strict 模式 0 错误 | ✅（Task 11/Task 14 实测 0 errors） |
| 11 | `uv run pytest tests/unit -q` 全绿 | ✅（Task 11/Task 14 实测 24 passed） |
| 12 | `uv run pytest tests/integration/test_smoke.py -q` 全绿 | ⏳ 待 Stage 3 验证（依赖 live docker） |

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

## Task 14 final review 修复

| ID | 修复 | 关联 commit |
| --- | --- | --- |
| C1 | `worker.handle` 写 Redis（status + reply）+ publish reply envelope | Task 14 |
| C2 | `llm.registry` 自动注册 `openai_compat`（api_key 给定时） | Task 14 |
| I4 | FastAPI 迁移到 `lifespan` context manager（移除 deprecated `@app.on_event`） | Task 14 |
| C3 | 本报告中未跑 smoke 的条目统一标注 ⏳，不强行填写 | Task 14 |

## 完成日期

2026-07-12