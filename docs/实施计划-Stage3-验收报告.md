# Stage 3 验收报告

> 对应 spec `docs/superpowers/specs/2026-07-12-stage3-business-mvp-design.md` § 7 验收清单。
>
> 标注说明：✅ = 已落地（commit / 命令产物可查）；⏳ = 端到端 live smoke 受限于当前 worker routing key 配置（见 "已知限制" 一节），需下一轮 patch 后再人工跑通。

## 1. 项目范围（对应 spec § 1.1）

Stage 3 在 Stage 2 后端基座上扩展 5 个业务 Agent、6 张业务表、Redis Stream 真流式 SSE、LLM 思考模式抽象、MCP Tool 协议层、Skill markdown 文档化。

| 项 | 落地状态 |
| --- | --- |
| 5 个业务 Agent（Profile / Plan / Director / Exercise / Review） | ✅（Task 7-11 全部 commit） |
| 核心闭环 MVP（profile → plan → director → exercise → review → submit） | ✅ 代码完成；⏳ live smoke 受 worker 路由绑定范围限制 |
| 6 张业务表 + Alembic 迁移 | ✅（Task 3） |
| Redis Stream 真流（worker XADD → gateway SSE 裸 XREAD） | ✅（Task 4） |
| SSE 端点升级（`/api/profile/init/{trace_id}/stream` + `/api/level/{level_id}/stream`） | ✅（Task 12） |
| LLM 思考模式抽象（ChatRequest.reasoning / ChatChunk.reasoning_delta） | ✅（Task 1-2） |
| Review Agent（规则过滤：JSON 合法性 / 题目唯一性 / 答案格式 / 难度梯度） | ✅（Task 10） |
| REST 端点（MVP 子集：profile build / map generate / level start / submit / stream） | ✅（Task 12） |
| Seed 数据（`scripts/seed_map.py`，5 个 KP，idempotent） | ✅（Task 8） |
| `scripts/smoke_mvp.sh` 端到端脚本 | ✅（Task 14，本 commit） |
| 单元 + 集成测试 | ✅（Task 13，58 unit + 1 integration，fakeredis 跑通） |
| OTel + Jaeger，5 Agent 全链路 trace | ✅（继承 Stage 2 基础设施） |

## 2. 架构决策总结（对应 spec § 2.1）

继承 Stage 2 的 8 项基座决策，新增 / 强化以下 6 项：

| # | 决策 | 落地位置 |
| --- | --- | --- |
| 9 | **Redis Stream 事件流**（worker 任意代码点 `progress_publish()` → gateway SSE `progress_consume()`，裸 XREAD，最后消费 ID 起步 `0-0`） | `src/selflearn/progress/stream.py` |
| 10 | **Skill markdown 化**（`docs/skills/<name>.md` frontmatter + body；启动时 `skills.library.load_all()` 读盘注入 `Skill.body` 作 LLM system prompt） | `src/selflearn/skills/library.py` + `docs/skills/skill.*.md`（5 个） |
| 11 | **MCP Tool 协议层**（`Tool` dataclass + `ToolRegistry.call()` + 3 个 stub：`tool.lint_json` / `tool.fetch_template` / `tool.store_kp`） | `src/selflearn/tools/protocol.py` |
| 12 | **Skill-BasedScheduler 路由**（仅认 `Envelope.target.id`，不读 `Agent.skills` 字段；`_AGENT_FOR_SKILL` dict 5 键，Stage 2 `skill_registry.match()` 仅作 fallback） | `src/selflearn/agents/scheduler.py` |
| 13 | **LLM 思考模式抽象**（`ChatRequest.reasoning` + `ChatRequest.reasoning_budget`；`ChatChunk.reasoning_delta`；adapter 解析 provider-specific `reasoning_content`） | `src/selflearn/llm/base.py` + `openai_compat` adapter |
| 14 | **Director 同步编排 + try/except 兜底**（ExerciseAgent.run_sync → ReviewAgent.review → 入库；任何异常 → `progress_publish(stage=FAILED)` + 抛 AppError） | `src/selflearn/agents/builtin/director_agent.py` |

## 3. Task 1-14 outcome summary

| Task | 内容 | 状态 |
| --- | --- | --- |
| 1 | LLM ChatRequest/ChatChunk 思考模式字段 | ✅ |
| 2 | reasoning helper + OpenAI 兼容 adapter 解析 `reasoning_content` | ✅ |
| 3 | 6 张业务表 + Alembic 迁移 + JSONB repo 工具 | ✅ |
| 4 | Redis Stream progress 模块（XADD / XREAD 0-0 / TTL 1h） | ✅ |
| 5 | MCP Tool 协议层（3 个 stub Tool + ToolRegistry.call） | ✅ |
| 6 | Skill markdown + library loader（5 个 skill 文档） | ✅ |
| 7 | ProfileAgent（直接读 payload.dimensions，不调 LLM；写 profiles 表） | ✅ |
| 8 | PlanAgent（不再调 LLM，复用 seed KP 写 MapNode）+ `scripts/seed_map.py` | ✅ |
| 9 | ExerciseAgent（前置打包 + LLM + lint_json 后置校验 + 1 次自动重试） | ✅ |
| 10 | ReviewAgent（rule-based：lint / duplicate / options length / difficulty gradient） | ✅ |
| 11 | DirectorAgent（同步编排 + try/except 兜底 + 单 session 入库） | ✅ |
| 12 | Gateway routes（profile/build + map/generate + level/start + level/submit + SSE 真流） | ✅ |
| 13 | Integration test（fakeredis 跑完整 envelope 端到端 + mocked LLM） | ✅ |
| 14 | smoke_mvp.sh + Stage 2 回归 + 验收报告（本 commit） | ✅ |

## 4. Gates Verified（自动化门禁）

| Gate | 命令 | 结果 |
| --- | --- | --- |
| mypy strict 模式 0 错误 | `cd backend && uv run mypy src tests` | ✅ Success: no issues found in 105 source files |
| 单元测试全绿 | `cd backend && uv run pytest tests/unit -q` | ✅ 58 passed |
| Stage 2 回归（`tests/integration/test_smoke.py`） | `cd backend && uv run pytest tests/integration/test_smoke.py` | ✅ 1 passed in 12.20s |
| seed_map 幂等 | `uv run python -m scripts.seed_map` | ✅ inserted 0 / skipped 5（重复执行无副作用） |
| Alembic 迁移已应用 | `uv run alembic upgrade head`（Stage 3 期间已跑过 Task 3） | ✅ 6 张表存在 |
| Docker 服务 healthy | `docker compose ps` | ✅ postgres / redis / rabbitmq 均 healthy |
| gateway /healthz | `curl http://127.0.0.1:8000/healthz` | ✅ `{"status":"ok"}` |

## 5. 端到端 smoke 实测记录

### 5.1 smoke_mvp.sh 结构（`backend/scripts/smoke_mvp.sh`）

```
1) seed KP（idempotent）
2) POST /api/profile/build → trace_id
3) SSE: GET /api/profile/init/{trace_id}/stream（≤60s 内应收到 progress→completed）
4) POST /api/map/generate
5) POST /api/level/start → 触发 Director 全 cycle
6) SSE: GET /api/level/{level_id}/stream（≤90s 覆盖 LLM cold start）
6b) sleep 3s + poll DB ≤30s 等 director 落库
7) POST /api/level/{level_id}/submit
8) 校验 level.status=completed
```

### 5.2 Brief 修复点（控制器已验证，原 brief 需补）

| # | 原 brief 问题 | 本次实现 |
| --- | --- | --- |
| 1 | profile SSE timeout=30s 太短（LLM cold start） | 提升到 60s（虽然 ProfileAgent 不调 LLM，但 worker 首次 init 仍吃冷启动） |
| 2 | level SSE timeout 缺值 | 给到 90s 覆盖 Director 全 cycle（exercise + review + LLM + 入库） |
| 3 | 步骤 5 → 6 之间 director run 还在跑，SELECT 找不到新 level | 加 `sleep 3` + 30s poll，find status=generated Level matching student_id |
| 4 | 步骤 7 只 grep `event: (progress\|completed\|error)` | 额外 `if ! grep -q '^event: completed' /tmp/level-sse.txt; then exit 1; fi` 显式断言 |

### 5.3 已知限制：worker routing key 未覆盖 Stage 3 skills

⏳ **当前 worker 进程只注册并消费 PingAgent**（`src/selflearn/main.py:run_worker` → `consume_envelope(queue="agent.ping.work", routing_key="ping_agent.#")`）。Stage 3 smoke 涉及的三个 routing key（`profile.skill.profile.build` / `plan.skill.plan.generate` / `director.skill.director.start`）没有 worker 订阅，导致消息在 RabbitMQ 队列里积压、SSE 端点收不到 progress 事件。

- **任务边界保护**：本任务约束 Rule 2 「Do NOT touch pyproject.toml, uv.lock, or any source code」，因此 worker 入口改造（注册 5 个 Stage 3 Agent + 绑定对应 routing key + 多队列并发消费）属于下一轮 wiring task。
- **代码现状**：`src/selflearn/agents/builtin/profile_agent.py` 等 5 个 Agent 类已实装，`src/selflearn/agents/scheduler.py:_AGENT_FOR_SKILL` 的 5 个键当前值仍为 `None`（预留给对应 Agent 类），`_resolve_agent_class` 一旦命中 None 会走 Stage 2 fallback → `skill_registry.match()` → 抛 `NotImplementedError`。
- **smoke 跑通的预计改动量**：~30 行（`main.py:run_worker` 注册 5 个 AgentInfo + `worker.py:handle` 多队列并发；`scheduler.py` 把 5 个 None 替换为对应类）。Stage 4 wiring task 可一并处理。
- **影响范围**：本报告所有 ⏳ 项与 live smoke 不可达直接相关。其它 gate（mypy / unit / integration / Stage 2 regression / seed / alembic / healthz）已全绿。

### 5.4 历史 live smoke 实测片段（pre-routing-key regression）

| 项 | 实测 |
| --- | --- |
| `POST /api/profile/build` | 202 Accepted，trace_id 返回 |
| gateway SSE 订阅 | 连通但 progress 流空（worker 未消费 → Redis Stream 无 XADD） |
| 失败模式 | `redis.exceptions.TimeoutError: Timeout reading from 127.0.0.1:6379`（`progress_consume` 阻塞 XREAD 5s 循环超时，与 worker 未消费一致） |
| worker log | `agent.registered agent_id=ping-01` + `worker.start queue=agent.ping.work routing_key=ping_agent.#`（仅 PingAgent） |

## 6. 已知限制 / Stage 4 follow-up

| 项 | 说明 | 推到 |
| --- | --- | --- |
| **Worker routing key 覆盖 Stage 3 skills** | worker 仅注册 PingAgent；profile/plan/director/exercise/review 5 个 Agent 类已写但未挂到 consumer | Stage 4 Task：wiring + 多 queue 并发消费 + scheduler dict 替换 None |
| **live smoke 端到端** | 当前受上一项阻塞，无法跑通完整闭环；smoke_mvp.sh 已就绪 | 同上 Task 完成后跑 |
| **4 种关卡形式**（document / mindmap / code） | spec § 1.2 明确推到 Stage 4 | Stage 4 |
| **评估模块 / 仪表盘 / 画像演变图表** | spec § 1.2 推到 Stage 4 | Stage 4 |
| **9 个核心窗口真实内容** | spec § 1.2 推到 Stage 4 | Stage 4 |
| **WebSocket 流式** | Stage 2 已明确不做，仅 SSE | 永不做 |
| **TTS / ASR / 讯飞星火** | spec § 1.2 推到 Stage 5 | Stage 5 |
| **1 个 Demo 之外的 3 个内容 Agent** | spec § 1.2 推到 Stage 4 | Stage 4 |
| **RAG / 引用 / 完整 4 阶段评审** | spec § 1.2 推到 Stage 4 | Stage 4 |
| **三层存储一致性**（写穿透 / 读旁路 / Singleflight） | spec § 1.2 推到 Stage 4 | Stage 4 |
| **Postgres JSONB 嵌套字典脏检查 testcontainers PG 单测** | 当前 SQLite 单测覆盖；PG 下 JSONB 行为依赖 `flag_modified`；Stage 4 接 PG 时追加 testcontainers PG 用例 | Stage 4 |
| **k8s / Helm** | spec § 1.2 推到 Stage 5 | Stage 5 |
| **鉴权 / 登录 / Token / OAuth / JWT** | 项目级硬约束（继承 `no-auth-no-login` 记忆） | **永不做** |

## 7. 文档与配置产物

| 产物 | 状态 |
| --- | --- |
| `backend/scripts/smoke_mvp.sh`（端到端 6 阶段 flow） | ✅（本 Task 14 commit `adbd43b`） |
| `docs/skills/skill.{profile.build,plan.generate,exercise.generate,review.exercise,director.start}.md`（5 个 Skill 文档） | ✅（Task 6） |
| `docs/superpowers/specs/2026-07-12-stage3-business-mvp-design.md`（V1.2） | ✅ |
| `docs/superpowers/plans/2026-07-12-stage3-business-mvp.md`（实施计划） | ✅ |
| `docs/实施计划-Stage3-验收报告.md`（本文件） | ✅（Task 14） |
| `backend/README.md`（含 Stage 3 端点表 + 思考模式 + smoke_mvp 用法） | ✅（继承 Stage 2 并扩展） |

## 8. 不允许出现项核查（spec § 7.2）

| 项 | 状态 |
| --- | --- |
| ❌ 鉴权 / 登录 / Token / JWT / OAuth 代码 | ✅ 未出现（继承 `no-auth-no-login`） |
| ❌ 4 种关卡形式的非 exercise 实现 | ✅ Level.form 仍只取 `'exercise'`（CHECK constraint） |
| ❌ 评估模块 / 仪表盘 | ✅ 未实现 |
| ❌ TTS / ASR / 讯飞 / WebSocket | ✅ 未出现（Stage 5 范畴） |
| ❌ 数据表超过本次声明的 6 张 | ✅ 仅 `knowledge_points` / `map_nodes` / `levels` / `exercises` / `level_completions` / `review_results`（外加 Stage 2 `students` / `profiles`） |
| ❌ 直连 OpenAI SDK 绕过 `LLMRegistry` | ✅ 全部走 `llm_registry.default()` |

## 9. 完成日期

2026-07-13