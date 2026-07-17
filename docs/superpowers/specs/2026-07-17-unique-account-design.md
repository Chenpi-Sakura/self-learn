# Task 265 — 唯一账户 + 全清 Demo 模式

> **For agentic workers:** 本 spec 是 Task 265 的"做什么、怎么做、不做什么"的权威来源。配套实施计划见 `docs/superpowers/plans/2026-07-17-unique-account.md`（SDD 阶段产出）。
>
> **继承文档**（继续生效，不重写、不修订）：
> - Stage 3 spec（`docs/superpowers/specs/2026-07-12-stage3-business-mvp-design.md`）
> - Stage 4 spec（`docs/superpowers/specs/2026-07-13-stage4-demo-integration-design.md`）
> - Task 261 spec（`docs/superpowers/specs/2026-07-16-html-lecture-design.md`）
> - 项目 CLAUDE.md（`CLAUDE.md` — KEEP_STUDENT 约定 + purge 约定）
> - 项目记忆：`[[no-auth-no-login]]`（鉴权 0 实现，不引入 login/token/JWT）

| 文档版本 | 日期 | 说明 |
|---|---|---|
| V1.0 | 2026-07-17 | 初稿。Task 265 = 唯一 KEEP_STUDENT 账户 + 全清 demo 模式（前端不再自生 UUID、不再有 sample 假数据、不再有 reset demo 按钮）。不动业务逻辑、不动 Stage 3/4 验收路径。 |

---

## 0. 编写目的与读法

本文档回答四个问题：

1. **Task 265 交付什么**：前端永用后端硬编码 KEEP_STUDENT（`86820161-b0f0-455f-91b4-a69e49445bdf`）；后端 startup 时 ensure 该账户存在（至少 Profile）；前端 demo 模式 100% 清掉
2. **不动什么**：Stage 3 业务 API 契约、Stage 4 学习闭环、Alembic migration、KEEP_STUDENT 之外的任何 UUID 都不存在
3. **架构怎么变**：前端 session.ts 同步取常量；后端 lifespan 启动钩子 ensure profile；`data/sample.ts` + `reset/ResetButton.tsx` 删除；所有 `import sample` 替换为真实后端数据
4. **怎么验证**：浏览器任意 localStorage 状态打开前端，UI 永远显示 KEEP_STUDENT；后端空 DB 启动后 GET `/api/profile` 返回真实空画像而非 500；前端 `npm run build` 0 type error

**读法建议**：
- § 1 范围与不在范围内
- § 2 决策表（核心 4 项）
- § 3 架构与目录
- § 4 API 契约与数据流
- § 5 实施任务分解
- § 6 错误 / 测试 / 验收

---

## 1. 范围与不在范围内

### 1.1 范围内（必须做）

1. **后端启动 ensure KEEP_STUDENT**：
   - 新增 `backend/src/selflearn/infra/seed_account.py`（或扩展 `infra/db.py`），导出 `async def ensure_keep_student()`
   - 该函数：检查 `Profile` 表里 `student_id == KEEP_STUDENT` 是否存在；不存在则 INSERT 一行 `Profile(student_id=KEEP_STUDENT, dimensions_json=...)`（空画像 JSON `{}`）
   - 在 `backend/src/selflearn/main.py` 的 FastAPI lifespan 启动钩子中调用一次
2. **前端硬编码 KEEP_STUDENT 常量**：
   - 新增 `frontend/src/constants/account.ts`：导出 `export const KEEP_STUDENT = '86820161-b0f0-455f-91b4-a69e49445bdf'`
   - 同步导出常量值字符串与字符串两端的注释解释来源（`backend/scripts/purge_test_data.py:24`）
3. **session.ts 重写**：
   - 删除 `KEY = 'selflearn.student_id'` localStorage KEY
   - 删除 `genId()` 函数与 `crypto.randomUUID` 引用
   - `studentId` 字段直接取 `KEEP_STUDENT` 常量
   - 删除 `reset()` 中的 `localStorage.removeItem(KEY)` 逻辑；保留 `location.reload()` 让用户可以"硬刷"
4. **彻底清 demo**：
   - 删除 `frontend/src/data/sample.ts` 整个文件
   - 删除 `frontend/src/reset/ResetButton.tsx` 整个文件
   - 删除 `frontend/src/components/TopBar.tsx:24-26` 中硬编码的"林"字 avatar 与 `import sample`；改为读 `useSession` 截断 `KEEP_STUDENT` 前 8 位或纯 icon
   - 排查并替换所有 `import ... from '../data/sample'` / `from '../../data/sample'` / `from './sample'` / `from '../reset/ResetButton'` 为真实后端调用或前端 fallback UI
5. **CLAUDE.md 清理**：
   - "E2E 测试数据清理"小节更新，purge_test_data.py 注释更新，明确它现在不只是"保 1 个账户"也是"清 demo 残留"

### 1.2 不在范围内（不要做）

1. **不动**：`alembic/versions/*` 任何 migration
2. **不动**：domain 模型（`Profile` / `Level` / `MapNode` / `Exercise` 等）
3. **不动**：Stage 3 业务 API 契约（`/api/level/start` 等）
4. **不动**：Stage 4 学习闭环（Hook 观测、Profile 动画、难度梯度）
5. **不动**：LecturePane / KaTeX 业务（用户当前痛点；Task 266 处理）
6. **不动**：treasure map 生成算法
7. **不引入**：任何用户注册 / 登录 / 鉴权 / 多用户切换 UI（项目记忆 `[[no-auth-no-login]]`）

---

## 2. 决策表

| # | 决策 | 理由 |
|---|------|------|
| 1 | **前端不发起 `/api/session/student` 请求**，直接同步用硬编码常量 `KEEP_STUDENT` | 部署场景："首次启动就一个账户"，不需要后端告知；少一层调用、少 500 风险面 |
| 2 | **后端 lifespan 仅 ensure Profile 存在**，不预置 MapNode | MapNode 由"生成地图"用户动作产生；预置会让用户每次进入看到一张默认地图，违反"硬刷行为确定"原则 |
| 3 | **`session.ts` 同步取常量**，不再 `useEffect` fetch | 常量硬编码，无运行时差异；同步代码简单且可读 |
| 4 | **彻底删除 demo 文件**，不留 mock 数据 + 空 placeholder | 占位 demo 数据会污染 UI、迷惑测试；清掉后所有路径"必须有真实后端响应"才能工作，强制回路真实 |
| 5 | **TopBar 显示 `KEEP_STUDENT` 前 8 位**（如 `ID · 86820161`），不显示中文字 | "林知遥" 是 sample 残留；用短 hash 既符合"技术 demo"风格又无假信息 |

---

## 3. 架构与目录

### 3.1 新增文件

```
backend/src/selflearn/infra/seed_account.py    # ensure_keep_student()
frontend/src/constants/account.ts              # KEEP_STUDENT 常量
```

### 3.2 修改文件

```
backend/src/selflearn/main.py                  # lifespan 启动钩子加 ensure_keep_student()
frontend/src/store/session.ts                  # 同步取常量、删 localStorage/genId
frontend/src/components/TopBar.tsx             # 删 "林" avatar、改真实 ID 显示
frontend/src/App.tsx / TreasureMap.tsx / ...   # 替换所有 import sample 的地方（具体清单在 T3）
frontend/CLAUDE.md（或根 CLAUDE.md）             # 清理 demo 残留说明
```

### 3.3 删除文件

```
frontend/src/data/sample.ts                    # 假节点 / 假画像 / 假 task / 假 chat
frontend/src/reset/ResetButton.tsx             # "重置 demo" 按钮
```

### 3.4 关键数据流

```
浏览器打开 localhost:5174
  └─> session.ts 同步 import KEEP_STUDENT 常量（无网络请求）
       └─> React subtree 全用 useSession 拿常量
            └─> 第一笔 API 请求（/api/level/start 等）
                 └─> 后端收到 KEEP_STUDENT
                      └─> lifespan 启动时确保 Profile 学生已 INSERT（idempotent）
                           └─> 处理业务
```

### 3.5 后端 startup 流程细节

```
FastAPI app = FastAPI(lifespan=...)
async def lifespan(app):
    await ensure_keep_student()    # 新增，幂等
    yield
    pass
```

`ensure_keep_student()`：
```python
KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"

async def ensure_keep_student() -> None:
    """幂等。空 DB 启动时 INSERT 一行空 Profile；存在则 noop。"""
    factory = get_session_factory()
    async with factory() as s:
        existing = await s.get(Profile, KEEP_STUDENT)
        if existing is None:
            s.add(Profile(student_id=KEEP_STUDENT, ...))
            await s.commit()
```

`Profile` 模型字段具体以 `backend/src/selflearn/domain/profile.py` 为准；本 spec 不假设字段名，由 subagent 在 task T2 自行读取。

---

## 4. API 契约与数据流

### 4.1 新 API

**无**。前端不引入新 endpoint；后端 ensure 只在 startup 跑，不暴露 HTTP。

### 4.2 现有 API 行为变化

| 路径 | 变化 |
|------|------|
| `GET /api/profile` | 行为不变；但**空 DB 启动后第一次请求不再 500**（Profile 行已被 ensure） |
| 任何 `student_id=KEEP_STUDENT` 的业务 API | 行为不变；只是前端不再传别的 student_id |

### 4.3 前端 store 变化

```ts
// frontend/src/store/session.ts —— 重写后
import { KEEP_STUDENT } from '../constants/account';

export const useSession = create<{ studentId: string; reset: () => void }>((set) => ({
  studentId: KEEP_STUDENT,    // 同步常量，无 fetch
  reset: () => {
    location.reload();         // 唯一副作用：硬刷
  },
}));
```

下游消费方（`useSession((s) => s.studentId)`）**不需要任何改动**，因为 hook 接口稳定。

---

## 5. 实施任务分解

按 SDD 顺序：

- **T1** 前端硬编码 KEEP_STUDENT 常量 + session.ts 重写（前端单测）
  - 文件：`frontend/src/constants/account.ts` (new), `frontend/src/store/session.ts` (modify)
  - 验收：`cd frontend && npm run build` 0 error；session.ts 没了 localStorage/genId；常量值 9c<=>86 前缀匹配 KEEP_STUDENT
  
- **T2** 后端 startup ensure KEEP_STUDENT + lifespan 钩子
  - 文件：`backend/src/selflearn/infra/seed_account.py` (new), `backend/src/selflearn/main.py` (modify), `backend/tests/unit/test_ensure_keep_student.py` (new)
  - 验收：单测覆盖"空 DB → ensure 后 Profile 存在"+"已有 → ensure 不重复 INSERT"；`cd backend && uv run pytest tests/unit/test_ensure_keep_student.py -p no:warnings` 全 pass

- **T3** 删 demo 文件 + 替换所有 sample import
  - 文件：删除 `frontend/src/data/sample.ts`、`frontend/src/reset/ResetButton.tsx`；修改 `frontend/src/components/TopBar.tsx`；修改所有 `import ... sample` 的代码（具体清单 subagent T3 自己 grep 出来）
  - **关键约束**：**不允许用空 placeholder 替代 sample 数据**——sample.ts 引用的地方必须走真实后端 API 或改为"加载中"占位
  - 验收：`cd frontend && npm run build` 0 error；前端 grep `'data/sample'` / `'reset/ResetButton'` 0 命中；TopBar.tsx 不再含"林"字符

- **T4** e2e 验证
  - 启动后端 + 前端，浏览器任意 localStorage 状态刷新 → 顶部永远显示 `ID · 86820161`
  - 空 DB 启动后端 → `curl GET /api/profile?student_id=KEEP_STUDENT` 返回 200 且 `dimensions` 为空对象
  - `cd backend && uv run pytest tests/unit -p no:warnings` 全 pass；mypy clean

### 5.1 任务间依赖

```
T1 (前端常量) ─┐
                ├─> T3 (删 demo) ─┐
T2 (后端 ensure) ┘                ├─> T4 (e2e)
                                  ┘
```

T1 / T2 可并行；T3 在 T1 完成后才能安全删引用；T4 在所有 T1-T3 完成后跑。

---

## 6. 错误 / 测试 / 验收

### 6.1 错误处理

| 场景 | 行为 |
|------|------|
| 后端 DB 启动失败 | lifespan 启动失败 → FastAPI 进程退出；与现状一致（不引入新失败模式） |
| ensure_keep_student() 第二次调用（同一进程 startup 已经被调用 + 测试重置 DB） | 单测隔离；生产 startup 不重入 |
| 前端 KEEP_STUDENT 常量与后端 DB KEEP_STUDENT 不一致 | 后端返回空（无 Profile 数据）；前端不会 crash，只是渲染空画像 |
| 前端 sample.ts 删除后某个旧 import 漏掉 | `npm run build` type-check 失败阻断交付；这是 T3 的核心防线 |

### 6.2 测试策略

- **T1**：jest/vitest 单测（如果项目有）覆盖 `useSession` 返回常量；否则 type-check + build 通过即可
- **T2**：pytest 单测：
  - `test_ensure_keep_student_creates_when_empty`：空 DB → Profile 行存在
  - `test_ensure_keep_student_idempotent`：再次调用 → DB 仍 1 行
- **T3**：手动 grep + build 即可（结构性 task，逻辑很少）
- **T4**：
  - 启动 docker compose（按 CLAUDE.md 注入 HTTP_PROXY）
  - curl `GET /api/profile?student_id=KEEP_STUDENT` → 200
  - 浏览器手测：硬刷两次，每次都看到 `ID · 86820161`

### 6.3 自审 Checklist（实施完成对照）

- [ ] 4 个 T 全部 commit，每个 T 独立 review 通过
- [ ] `cd frontend && npm run build` 0 error
- [ ] `cd backend && uv run pytest tests/unit -p no:warnings` 全 pass
- [ ] `cd backend && uv run mypy src/selflearn` clean
- [ ] 前端 grep `data/sample|reset/ResetButton|crypto.randomUUID|localStorage.getItem.*selflearn` 全部 0 命中
- [ ] 后端 grep `await ensure_keep_student()` 在 main.py lifespan 内 1 命中
- [ ] CLAUDE.md "E2E 测试数据清理"小节更新过
- [ ] 浏览器实测：localStorage 清空后刷新 → UI 显示 KEEP_STUDENT 短前缀，不是新 UUID

### 6.4 全局约束（继承自 CLAUDE.md + 项目记忆）

- branch：main（memory `no-worktrees-sdd`）
- 代理：`HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 docker compose build <svc>`（CLAUDE.md）
- 中文 commit message
- 不动 alembic migrations
- 不引入鉴权 / 登录 / token（`no-auth-no-login`）
- KEEP_STUDENT 字面量值：`"86820161-b0f0-455f-91b4-a69e49445bdf"`，与 `purge_test_data.py:24` 同源

---

## 7. KEEP_STUDENT 常量一致性矩阵

实施完成时，以下 4 个位置必须**字面量一致**：

| 位置 | 当前值 |
|------|--------|
| `backend/scripts/purge_test_data.py:24` | `"86820161-b0f0-455f-91b4-a69e49445bdf"` |
| `backend/src/selflearn/infra/seed_account.py` (T2 新增) | 同上 |
| `frontend/src/constants/account.ts` (T1 新增) | 同上 |
| `CLAUDE.md` "E2E 测试数据清理"小节 | 同上 |

任何不一致都会让 purge 与 ensure 对不上，subagent T2 commit 前必须字面量比对一次。

---

## 8. 风险与副作用

| 风险 | 缓解 |
|------|------|
| T3 删 sample.ts 后某些旧组件 import 路径找不到，build 挂 | 这正是我们想要的——阻断 build 当作"漏删清单"的 checkpoint。subagent T3 必须用 grep `from .+sample` 全扫、全部替换后再删文件 |
| 后端 startup 多一次 INSERT（Profile 行）会改变 `purge_test_data.py` 行为 | 已有脚本会一并 delete 非 KEEP_STUDENT 的 Profile 行，本任务的 ensure 只 INERT KEEP_STUDENT 行 → purge 不动 KEEP_STUDENT → 一致 |
| 真删除 sample 后前端部分窗口（比如 ProfileRadar）没有真实数据时变成白屏 | fallback UI 为"加载失败 / 暂无画像数据"（已有现成）。subagent T3 复用现有 fallback |
| TopBar 改 ID 显示，原"林" avatar 改成什么可能引起观感问题 | 用前 8 位 hash `ID · 86820161`；与现有 demo 视觉体例接近 |
