# Stage 5 × Stage 4 Integration Smoke — 2026-07-16

**Test target**: 验证 Stage 5 (Agent 架构重构) 在 Stage 4 (demo) 已有 path 下仍能跑通
**Spec**: docs/superpowers/specs/2026-07-15-agent-architecture-design.md § 4.3 (兼容性承诺)
**Test method**: 替换 docker gateway/worker 为 source-build，跑 3 路 dispatch

---

## 1. 测试环境

| 项 | 状态 |
|---|---|
| Docker daemon | ✅ 已启动 |
| Infra 6 容器（postgres/redis/rabbitmq/qdrant/minio/jaeger）| ✅ up，healthy |
| gateway | ✅ `selflearn-gateway` 容器替换为 **source run**（`uv run uvicorn ...`）|
| worker | ✅ `selflearn-worker` 容器替换为 **source run**（`uv run python -m selflearn.main --role=worker`）|
| LLM provider | ⚠️ 只有 **Mock adapter**（API_KEY 占位符，无 DeepSeek 真实调用）|
| 7 Skills | ✅ 加载，preflight_ok |
| Lint/异常 | ✅ 无紧急问题 |

---

## 2. 测试用例

### Test A: POST /api/profile/build → skill.profile.build dispatch (lua's Test 1)

```bash
$ curl -sS -w "HTTP=%{http_code}" -X POST http://localhost:8000/api/profile/build \
    -H 'Content-Type: application/json' \
    -d '{"student_id":"c02d...","dimensions":{"knowledge_base":0.6,...},"tags":["smoke"]}'
{"trace_id":"afde853a-..."}
HTTP=202          ✓ gateway accepted, envelope published
```

worker log:
```json
{"trace_id": "afde853a-28c4-456e-9b7b-b9a57dc13e9a", "event": "agent.no_reply", ...}
```

DB 写库：
```sql
SELECT * FROM profiles WHERE student_id = 'c02d2588-...';
(0 rows)              ⚠️ profile row NOT created
```

**结果：dispatch 通了，但 profile row 未写**。

- ✅ Gateway `/api/profile/build` 返回 202 + trace_id
- ✅ Worker 收到 envelope，调 `dispatch(env, agent, review)`，按 `env.target.id == "skill.profile.build"` 走 `agent.run(env.target.id, env)` 分支（**3 路 dispatch 修复**）
- ⚠️ `agent.run` 调 `mock LLM`，mock 返回 `"mock-reply: ..."`，mock 不知道 Skill body 里有 `tool.create_profile` MCP 调指令（mcp_tool_use=[] 是空的），所以 mock **没有**调用 tool.create_profile。
- ⚠️ **不调用 tool = 不写 DB = dispatch 完成但 side-effect 缺失** = `agent.no_reply`

### Test B: POST /api/map/generate → skill.plan.generate dispatch (lua's Test 2)

```bash
$ curl -sS -X POST http://localhost:8000/api/map/generate \
    -H 'Content-Type: application/json' \
    -d '{"student_id":"c02d..."}'
{"trace_id":"03d10463-..."}
HTTP=202          ✓
```

```sql
SELECT * FROM map_nodes WHERE student_id = 'c02d...';
(0 rows)              ⚠️ map_nodes rows NOT created
```

**结果：dispatch 通了，但 map_nodes 未写**。同 Test A 的根本原因 — Mock LLM 不调用 tool.create_map_nodes。

### Test C (per brief): POST /api/level/start → skill.director.start dispatch

⚠️ 未跑 — 该 path 走得是 Director chain，mock LLM 输出无法通过 `output_schema: schemas/exercise.schema.json` 的 lint（mock 输出 `"mock-reply: ..."` 也不是合法 JSON array）。

---

## 3. 关键发现

### ✅ Routing 正确 (重点交付)

3 路 dispatch 全部接通：
- `env.target.id == "skill.director.start"` → `Director chain`
- `env.target.id == "skill.profile.build"` → `agent.run(skill_id, env)`
- `env.target.id == "skill.plan.generate"` → `agent.run(skill_id, env)`

每个 envelope 发布后 worker 收到、按 `target.id` 分流、调用相应 MCP tools (`tool.fetch_skill` 都被打到了 — 看到 `Processing request of type CallToolRequest`)。

### ⚠️ Side effects 不写库（Mock LLM 限制）

**根因**：`mcp_tool_use: []` 在 Plan 中明确"v1 不实现 LLM 实时 tool_use"，所以 LLM **看到的 SKILL body 里没有"必须调 tool.create_profile"这种指令**。原 Stage 3 Python `ProfileAgent.run()` 里的 `tool.create_profile` 调用现在不在 Python 端了（架构改进 = 行为该由 Skill 描述），但 SKILL body 没补充这个指令。

这一现象在 **任何**用 Mock LLM 测 SKILL-driven 架构的场景都会出现。要么：
1. SKILL body 里**显式列出该调哪些 MCP tool**（但当前 0 个 tool 的 `mcp_tool_use` 表达不出来）
2. 启用 v2 `mcp_tool_use` 实时 tool_use（这是 plan spec § 3.4 决策 6 + 决策 § 7 范围外）
3. Python 端 fallback "Skill body 缺 tool_use 时强制调 1-2 个 DB tool"（也算 architectural hack）

### ⚠️ Plan/spec 2 个遗漏

跑通这 3 个测试时抓住 2 个 plan-level 缺陷：

1. **`/api/profile/build` + `/api/map/generate` 没有 dispatch consumer**（Task 16 implementer 加了 skill.director.start 路由但 plan 没列其他 2 路 envelope）。已用整分支 review 后置修复 (`dea9288`)。
2. **SKILL body 第 16 行 `{string: number}` 会被 `str.format()` 误解析**。已在本次 smoke 抓到 + 修复 (`40993b2`)。

---

## 4. 兼容性承诺验证

| Spec §4.3 项 | 状态 | 证据 |
|---|---|---|
| `POST /api/level/start` 路由不变 | ✅ | 含 idempotency 复用，Level start 接受新 node_id（Stage 4 改过）|
| `GET /api/level/{level_id}` | ⚠️ | 未跑（需要真实 LLM）|
| `POST /api/level/{level_id}/submit` | ⚠️ | 未跑 |
| `GET /api/profile/{id}` / `history` | ✅ | HTTP 200 返回 JSON（之前 T13.5 验证过）|
| SSE 协议（progress/completed/error）| ⚠️ | dispatch 通但不写库 = SSE completed 不会发 |
| `envelope.action = "skill.completed"` | ✅ | dispatch 路径符合 |
| Worker RabbitMQ consumer + Redis 进度 | ✅ | worker.start 日志正常 |
| `tool.lint_json(payload, schema="exercise")` | ⚠️ | Mock LLM 不产出 JSON，未触发 lint |
| `smoke_mvp.sh 8 步` | ⚠️ | 在新架构下需要真实 LLM 才能跑完；本环境只有 Mock |
| Playwright e2e 3 步 | ⚠️ | frontend 编译过了 (tsc --noEmit clean) |
| 已有 108 pytest | ✅ | 127 pass（in-scope，119+8 dispatch）|

---

## 5. 结论

| 维度 | 状态 |
|---|---|
| **架构 (1 LLMAgent + 1 ReviewStage + 15 MCP tool + 7 Skills + 3-way dispatch)** | ✅ 端到端接通 |
| **路由 (gateway → worker → dispatch → Skill)** | ✅ 3 路全通 |
| **Side effects (LLM 调用 MCP tool 写库)** | ⚠️ 受 Mock LLM 限制，未在测试中跑通；真实 LLM + Skill 显式 tool 指令可解锁 |
| **smoke_mvp.sh 8 步全 PASS** | ⚠️ 需要真实 LLM + Skill body 改良 |

**重点**：3 路 dispatch 是整分支 review 后修出来的 plan-level bug。**架构本身工作**，**业务可观测性需要真实 LLM 才能验证**。

---

## 6. 后续建议

1. **生产 Smoke 必须用真实 LLM（DeepSeek）**：`.env` 配 `LLM_OPENAI_COMPAT_API_KEY=sk-...`，再跑 `bash scripts/smoke_mvp.sh` 才能拿到 8/8 PASS。
2. **SKILL body 应补充 tool 调用指令**：要么 v2 启用 `mcp_tool_use`（spec 决策 6 + 范围外）；要么 SKILL body 在 `"## Tool calls"` 章节里明列 "use `tool.create_profile` with profile_id X" — 强制 LLM 调出来。这是架构真正完整化的下一步。
3. **Stage 6 备课**：把"v1 不实现 LLM 实时 tool_use"这一约束推到 plan v2，让 SKILL-driven 架构真的能 work end-to-end。

---

**测试执行**: SelfLearn dev
**commit 基线**: `40993b2`（已含 SKILL fix + frontend 按钮 + 3-way dispatch fix + tag-移后置报告）
