# Stage 4 验收报告 — SelfLearn Demo 端到端集成

**日期**：2026-07-14
**对应 spec**：docs/superpowers/specs/2026-07-13-stage4-demo-integration-design.md
**对应 plan**：docs/superpowers/plans/2026-07-13-stage4-demo-integration.md
**对应补充 plan**：docs/superpowers/plans/2026-07-14-t13.5-demo-truly-end-to-end.md
**对应报告**：docs/superpowers/reports/2026-07-14-t13.5.md

## TL;DR

Stage 4 Demo 集成完成。`/api/level/start` 端到端跑通——DirectorAgent 走完 Exercise（真 LLM）→ Review → Profile 更新 → 写库全链路，DB 真实记录。前端 4 段主线（API + Desk + Windows + 画像动画）交付，Playwright e2e 3/3 PASS。

## 范围 vs 实际交付

### Spec § 1.1 范围

| Spec 项 | 状态 | 证据 |
| --- | --- | --- |
| § 1.1 目录重命名 → Task 1 | ✅ | task 1 commit + frontend/backend 代码搜索无 demo-serif |
| § 1.1 5 API 缺口 | ✅ | tasks 7-12 完成；T11/T12 SSE 字段补 |
| § 1.1 学习闭环 3 点 | ✅ | tasks 6/11/12；spec § 5.1/§ 5.2/§ 5.3 |
| § 1.1 1 张新表 | ✅ | profile_snapshots（task 2）|
| § 1.1 AOP Hook | ✅ | tasks 3/4/5；HookBus + 3 横切点装饰器 |
| § 1.1 frontend 4 段 | ✅ | task 13；4 段主线（api + desk + panes + 画像动画） |
| § 1.1 Playwright e2e | ✅ | task 14；3/3 PASS |

## 测试结果

### pytest
- 全套：**108 passed**（含 T13.5 新增 8 个测试 + T9 smoke 全部）
- pre-existing 失败：test_plan_agent（base commit 也失败）+ test_scheduler_target_id_routing（test-ordering flakiness）
- mypy src/selflearn：**Success: no issues found in 85 source files**

### Playwright e2e（task 14）
- 3/3 PASS：
  - 页面加载后看到藏宝图与画像（.tm-svg + .pr-svg 可见）
  - CORS：无浏览器层 CORS 报错
  - profile / map API 调用成功（200）

### smoke_mvp.sh（T13.5 端到端）
- 8 步全 PASS：
  - 1) seed KP ✅
  - 2) POST /api/profile/build ✅
  - 3) SSE profile init（progress + completed）✅
  - 4) POST /api/map/generate ✅
  - 5) POST /api/level/start ✅
  - 6) SSE director（director → exercise → review → completed）✅
  - 7) POST /api/level/{id}/submit ✅
  - 8) level.status=completed ✅

### DB 验证
- `levels`：端到端生成新 level（status=completed，form=exercise）
- `exercises`：每个 level 3 道题
- `review_results`：verdict=needs_fix, score=0.6
- `profile_snapshots`：1 条 level_completed trigger

### LLM 真调用
- 阿里云 MaaS DeepSeek 真实调通
- prompt 强化后 lint_json 不再拒
- review 真给出 verdict+score
- profile 真增量更新（kb delta=-0.03, as delta=-0.02）

## 5 API 缺口补齐证据

| 缺口 | 路由 | 实现 |
| --- | --- | --- |
| GET /api/profile/{id} | T7 | `backend/src/selflearn/gateway/routes/profile.py:133` |
| GET /api/profile/{id}/history | T8 | `backend/src/selflearn/gateway/routes/profile.py:186` |
| GET /api/map/{id}/nodes | T9 | `backend/src/selflearn/gateway/routes/map.py` |
| GET /api/level/{id} | T10 | `backend/src/selflearn/gateway/routes/level.py:117` |
| POST /api/level/{id}/submit | T12 | `backend/src/selflearn/gateway/routes/level.py:74` |

## 1 张新表 + 迁移

- `profile_snapshots`：BigSerial PK + student_id(String 36) + profile(JSON) + trigger(String 32) + created_at(TIMESTAMPTZ)
- Alembic migration：当前未走（手动 CREATE）—— Stage 4 收尾件

## AOP Hook 3 横切点证据

- `backend/src/selflearn/observability/decorators.py`：HookBus + envelope/llm/progress 装饰器
- 3 横切点：
  - envelope: 进出打印 actor + trace_id
  - llm: 每次 LLM 调用打印 prompt + response
  - progress: 每次 progress_publish 打印事件
- 入口：`@hook("envelope.publish")` / `@hook("llm.chat")` / `@hook("progress.publish")`

## 学习闭环 3 点

| 闭环点 | 位置 | 证据 |
| --- | --- | --- |
| Profile 自动更新 | DirectorAgent._run_inner step 4.5 | `director_agent.py:135-139`，apply_delta 写 profile_snapshots |
| 难度梯度 | DirectorAgent._compute_difficulty | `director_agent.py:168-177`，基于最近 3 次关卡分数 |
| 画像演变 | ProfileRepository.recent_snapshots | `profile_repo.py:76-87`，按 created_at DESC |

## frontend 4 段交付物

1. **API 层**：`frontend/src/api/{profile,map,level}.ts` + client.ts
2. **Desk 层**：TopBar + 重置 demo 按钮
3. **Panes 层**：4 个默认 windows（treasure_map / today / profile / chat）
4. **画像动画**：ProfileRadar 雷达图 + TreasureMap 节点连线

## 已知遗留与 Stage 5+ 列表

1. **profile_snapshots 表用手动 CREATE**，未走 Alembic
2. **smoke_mvp.sh 仍用 `uv run`**，Windows 环境退化
3. **level.py / profile.py SSE 重复**——`_stream_events` / `event_gen` 两处复制
4. **节点 status 翻转**（MapNode.active → completed 视觉）
5. **5174 CORS、worker 'smoke' warning、student.py 死代码**
6. **流式 reasoning 仍走 chat_stream 拼 content**
7. **test_scheduler_target_id_routing.py 全套跑 flakiness**——event loop 共享状态

## Commit 列表（Stage 4 总）

```
git log --oneline stage3-complete..HEAD | wc -l
```

实际 T13.5 + T14 共 14 个 commits。

## Tag

`stage4-complete`（HEAD）

## 后续

用户已确认：Stage 4 完成后进入反复端到端测试调优阶段。视觉测试（你）+ 文本模态（我）。