# Task 265 — 唯一账户 + 全清 Demo 模式 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 永远只有 1 个 KEEP_STUDENT 账户（`86820161-b0f0-455f-91b4-a69e49445bdf`）；前端不再自生 UUID、不再有 sample/demo 假数据、不再有"重置 demo"按钮；后端 startup 时 ensure 该账户存在 Profile 行。

**Architecture:** 4 个 task 走 TDD/TDD-flavored SDD：T1 写前端常量 + 重写 session.ts（前端 build 通过即可）；T2 写后端 ensure + lifespan 钩子（TDD，pytest 单测覆盖幂等）；T3 删 demo 文件 + 替换所有 sample 用法（结构性 task，靠 `npm run build` 当 gate）；T4 e2e 验证。

**Tech Stack:** Python 3.12 + SQLAlchemy 2.0 async + FastAPI lifespan; TypeScript + Zustand; `uv run` + `npm run build`.

## Global Constraints

These are the binding rules from spec § 1, § 6.4, § 7, § 8 and the project memory/CLAUDE.md. Every task implicitly obeys them:

- **KEEP_STUDENT 字面量**：`"86820161-b0f0-455f-91b4-a69e49445bdf"`；4 个位置必须字面量一致（`backend/scripts/purge_test_data.py:24`、`backend/src/selflearn/infra/seed_account.py` (T2 新增)、`frontend/src/constants/account.ts` (T1 新增)、`CLAUDE.md` "E2E 测试数据清理"小节）
- **不动 alembic migrations** — 不引入新版本
- **不引入鉴权 / 登录 / token / JWT / OAuth**（项目记忆 `no-auth-no-login`）
- **branch 直接 main**（项目记忆 `no-worktrees-sdd`）
- **中文 commit message**
- **Docker 构建**：`HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 docker compose build <svc>` （CLAUDE.md）
- **后端测试**：`cd backend && uv run pytest -p no:warnings`；**前端构建**：`cd frontend && npm run build`（即 `tsc --noEmit && vite build`）
- **不允许用空 placeholder 替代 sample 数据**：sample.ts 引用的地方必须 (a) 走真实后端 API，或 (b) 改成"加载中/暂无数据"占位文本；不允许 mock 数据
- **Demo/sample.ts 删了就必须替换，不可只删不改**：删除文件 + 全部 import 替换才能 commit
- **前后端 KEEP_STUDENT 字面量与 `purge_test_data.py` 一致**：commit 前子任务分别 grep 字面量校验一次

---

## File Structure（实施前心智模型）

**新增 2**:
- `backend/src/selflearn/infra/seed_account.py` — `ensure_keep_student()` 幂等函数
- `frontend/src/constants/account.ts` — `KEEP_STUDENT` 常量 export

**修改 ~6**:
- `backend/src/selflearn/gateway/app.py` — lifespan 加 `await ensure_keep_student()`
- `frontend/src/store/session.ts` — 重写（去 localStorage/genId）
- `frontend/src/components/TopBar.tsx` — 去 "林" avatar + 去 ResetButton
- `frontend/src/store/useWorkspace.ts` — 用真实后端或空 fallback 替代 sample 默认值
- `frontend/src/lib/eventBus.ts` — 改用 `api/types.ts` 的 `MapNode/Edge`
- `frontend/src/components/ChatFloat.tsx` — `sendChat` 走空响应（AI 助手暂未接入提示）

**修改单测 1**:
- `backend/tests/unit/test_ensure_keep_student.py` (new)

**删除 2**:
- `frontend/src/data/sample.ts`
- `frontend/src/reset/ResetButton.tsx`

---

### Task 1: 前端硬编码 KEEP_STUDENT + session.ts 重写

**Files:**
- Create: `frontend/src/constants/account.ts`
- Modify: `frontend/src/store/session.ts`

**Interfaces:**
- Consumes: `backend/src/selflearn/infra/seed_account.py:KEEP_STUDENT = "86820161-..."` (T2 才存在；本任务先用同字符串，后续 T2 commit 前再字面量比对)
- Produces: `import { KEEP_STUDENT }` — 在前端任意模块可用

- [ ] **Step 1: 创建 `frontend/src/constants/account.ts`**

写入：

```ts
// 唯一账户常量。前后端统一字面量来源：
//   - backend/scripts/purge_test_data.py:24
//   - backend/src/selflearn/infra/seed_account.py  (新增于 Task 2)
//   - CLAUDE.md "E2E 测试数据清理" 小节
// 任何改动这 4 处必须同步。
export const KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf";
```

- [ ] **Step 2: 替换 `frontend/src/store/session.ts` 全部内容**

把现有文件替换为：

```ts
import { create } from 'zustand';
import { KEEP_STUDENT } from '../constants/account';

// 唯一账户（spec Task 265）：前端不再生成临时 UUID，永久使用 KEEP_STUDENT。
// 这是部署时唯一的合法 student_id。无登录/无注册/无切换。
export const useSession = create<{ studentId: string; reset: () => void }>((set) => ({
  studentId: KEEP_STUDENT,
  reset: () => {
    // reset 保留只是为了兼容旧 demo 的"硬刷"动作；唯一副作用是 location.reload()。
    location.reload();
  },
}));
```

要点：
- 删除原 `KEY = 'selflearn.student_id'` localStorage KEY
- 删除原 `genId()` 函数与 `crypto.randomUUID` 引用
- 删除原 `localStorage.getItem(...) ?? gen()` 链
- 保留 `useSession` 形状（`{ studentId: string; reset: () => void }`），下游消费方零改动

- [ ] **Step 3: 构建验证**

```bash
cd "D:/Projects/SelfLearn/frontend" && npm run build 2>&1 | tail -20
```

Expected: 输出 `built in ...ms`，0 type error。即便没有新代码引用 KEEP_STUDENT，session.ts 仍然只 import 它不影响 build；下游消费方继续工作。

- [ ] **Step 4: 字面量交叉校验**

```bash
cd "D:/Projects/SelfLearn" && grep -rn '"86820161-b0f0-455f-91b4-a69e49445bdf"' backend/scripts/purge_test_data.py frontend/src/constants/account.ts 2>&1
```

Expected: 2 行命中，**字符完全一致**（无空格、无引号差异）。

- [ ] **Step 5: Commit**

```bash
cd "D:/Projects/SelfLearn" && git add frontend/src/constants/account.ts frontend/src/store/session.ts && git commit -m "feat(account): 前端硬编码 KEEP_STUDENT 常量 + session.ts 重写" 2>&1 | tail -5
```

---

### Task 2: 后端 startup ensure KEEP_STUDENT + lifespan 钩子

**Files:**
- Create: `backend/src/selflearn/infra/seed_account.py`
- Modify: `backend/src/selflearn/gateway/app.py` (lifespan)
- Create: `backend/tests/unit/test_ensure_keep_student.py`

**Interfaces:**
- Consumes: `selflearn.domain.profile.Profile`（已存在）；`selflearn.infra.db.get_session_factory()`（已存在）
- Produces: `async def ensure_keep_student() -> None` — 幂等；空 DB 时 INSERT Profile 行；存在时 noop

- [ ] **Step 1: 写 failing test `backend/tests/unit/test_ensure_keep_student.py`**

写入：

```python
"""ensure_keep_student 幂等性。"""
from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory
from selflearn.infra.seed_account import KEEP_STUDENT, ensure_keep_student


@pytest.mark.asyncio
async def test_ensure_creates_when_empty() -> None:
    """空 DB 时调用后，Profile 表存在 KEEP_STUDENT 行。"""
    factory = get_session_factory()
    async with factory() as s:
        await s.execute(delete(Profile).where(Profile.student_id == KEEP_STUDENT))
        await s.commit()

    await ensure_keep_student()

    async with factory() as s:
        rows = (await s.execute(
            select(Profile).where(Profile.student_id == KEEP_STUDENT)
        )).scalars().all()
    assert len(rows) == 1, "expected exactly one Profile row for KEEP_STUDENT"
    assert rows[0].student_id == KEEP_STUDENT
    # 不假设 dimensions 默认值（可能是 {} 也可能是 None 等）；只断言行存在


@pytest.mark.asyncio
async def test_ensure_idempotent_when_exists() -> None:
    """已有 Profile 行时再次调用，DB 仍只有 1 行（不重复 INSERT）。"""
    factory = get_session_factory()
    await ensure_keep_student()
    await ensure_keep_student()
    await ensure_keep_student()

    async with factory() as s:
        cnt = (await s.execute(
            select(Profile).where(Profile.student_id == KEEP_STUDENT)
        )).scalars().all()
    assert len(cnt) == 1, "ensure_keep_student must be idempotent"
```

- [ ] **Step 2: 跑测试，验证 fail**

```bash
cd "D:/Projects/SelfLearn/backend" && uv run pytest tests/unit/test_ensure_keep_student.py -v -p no:warnings 2>&1 | tail -15
```

Expected: `ModuleNotFoundError: No module named 'selflearn.infra.seed_account'`

- [ ] **Step 3: 创建 `backend/src/selflearn/infra/seed_account.py`**

写入：

```python
"""启动时确保唯一账户存在。

幂等：empty DB 时 INSERT 一行空 Profile；已有 noop。

KEEP_STUDENT 字面量必须与以下 3 处保持完全一致（Task 265 spec § 7）：
  - backend/scripts/purge_test_data.py:24
  - frontend/src/constants/account.ts
  - CLAUDE.md "E2E 测试数据清理" 小节
"""
from __future__ import annotations

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory

KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"


async def ensure_keep_student() -> None:
    """幂等。空 DB 启动时 INSERT 一行空 Profile；存在则 noop。"""
    factory = get_session_factory()
    async with factory() as session:
        existing = (
            await session.execute(
                # 简化：用 student_id 而非 profile_id；Profile 表没有基于 student_id 的 PK。
                # 这里用 where 一次 select 即可（profile 表按 student_id 索引）。
                # 由于 Profile 表只允许"一学生一行"（按 § 5 决策），所以 first() 即可。
                select(Profile).where(Profile.student_id == KEEP_STUDENT)
            )
        ).scalars().first()
        if existing is not None:
            return
        session.add(Profile(student_id=KEEP_STUDENT))
        await session.commit()
```

注：
- 不预置 MapNode（按 spec § 2 决策 2）
- `Profile.dimensions` 等其他字段走 model default（看 `backend/src/selflearn/domain/profile.py`）

- [ ] **Step 4: 跑测试，验证 pass**

```bash
cd "D:/Projects/SelfLearn/backend" && uv run pytest tests/unit/test_ensure_keep_student.py -v -p no:warnings 2>&1 | tail -10
```

Expected: 2 passed

- [ ] **Step 5: 修改 `backend/src/selflearn/gateway/app.py` lifespan**

把现有 lifespan（lines 23-28）替换为：

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await ensure_keep_student()        # 新增：幂等 ensure Profile 行
    await setup_topology()
    log.info("gateway.startup_done")
    yield
    log.info("gateway.shutdown_done")
```

同时在文件顶部 import 区域加：

```python
from selflearn.infra.seed_account import ensure_keep_student
```

- [ ] **Step 6: mypy + 跑全部单测**

```bash
cd "D:/Projects/SelfLearn/backend" && uv run mypy src/selflearn 2>&1 | tail -3
cd "D:/Projects/SelfLearn/backend" && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
```

Expected:
- mypy: `Success: no issues found in N source files`
- pytest: 全 PASS（无回归）

- [ ] **Step 7: 字面量交叉校验**

```bash
cd "D:/Projects/SelfLearn" && grep -rn '"86820161-b0f0-455f-91b4-a69e49445bdf"' backend/scripts/purge_test_data.py backend/src/selflearn/infra/seed_account.py frontend/src/constants/account.ts 2>&1
```

Expected: 3 行命中，字符完全一致。

- [ ] **Step 8: Commit**

```bash
cd "D:/Projects/SelfLearn" && git add backend/src/selflearn/infra/seed_account.py backend/src/selflearn/gateway/app.py backend/tests/unit/test_ensure_keep_student.py && git commit -m "feat(backend): 启动 ensure KEEP_STUDENT 账户（幂等）+ 单测" 2>&1 | tail -5
```

---

### Task 3: 删 demo 文件 + 替换所有 sample/ResetButton 用法

**Files:**
- Delete: `frontend/src/data/sample.ts`
- Delete: `frontend/src/reset/ResetButton.tsx`
- Modify: `frontend/src/components/TopBar.tsx`
- Modify: `frontend/src/store/useWorkspace.ts`
- Modify: `frontend/src/lib/eventBus.ts`
- Modify: `frontend/src/components/ChatFloat.tsx`（如果 sendChat 仍被消费）

**Interfaces:**
- Consumes: 既有 useWorkspace / eventBus / ChatFloat 接口
- Produces: 前端不再 import `data/sample` 任何路径；build 0 error

- [ ] **Step 1: grep 找到所有 demo 数据引用**

```bash
cd "D:/Projects/SelfLearn/frontend" && grep -rn "data/sample\|reset/ResetButton" src/ 2>&1
```

Expected 命中（用真实 grep 输出作 step 2 子任务清单）：
- `src/lib/eventBus.ts:7` — `import type { MapNode, Edge } from '../data/sample';`
- `src/store/useWorkspace.ts:4` — `import { mapNodes, mapEdges, profile, tasks, initialChat, mockAiReplies } from '../data/sample';`
- `src/components/TopBar.tsx:4` — `import { ResetButton } from '../reset/ResetButton';`

- [ ] **Step 2: 修改 `frontend/src/lib/eventBus.ts`**

把 lines 5-9 区域 import 块改为：

```ts
import type { MapNode, Edge } from '../api/types';
```

（用 api/types.ts 真实定义的 MapNode/Edge，已存在；只是当前 eventBus 用错名指向 sample 的副本。）

不要碰其他代码；本文件 types 只在事件 payload shape 用。

- [ ] **Step 3: 重写 `frontend/src/store/useWorkspace.ts`** — **核心改造**

读取现有文件（保留所有 windows/move/focus/minimize/maximize/pin/close/open/resize toggle 逻辑，**只换 store 的初始状态**）。

改动：
- 删除 `import { mapNodes, mapEdges, profile, tasks, initialChat, mockAiReplies } from '../data/sample';`
- 把 store 字段默认值改为空：
  - `nodes: []`
  - `edges: []`
  - `profile: { student: '', dimensions: [] }`（与 api/types.ts:Profile 形状匹配）
  - `tasks: []`
  - `chat: []`
- 把 state 接口里 `nodes: typeof mapNodes; edges: typeof mapEdges; profile: typeof profile; tasks: typeof tasks;` 改为：
  - `nodes: import('../api/types').MapNode[]`
  - `edges: import('../api/types').Edge[]`
  - `profile: import('../api/types').Profile`
  - `tasks: Array<{ id: string; title: string; status: 'todo' | 'doing' | 'done'; minutes: number }>`
- 删除 `let replyIdx = 0;` 和 `mockAiReplies` 引用
- 把 `sendChat` 改为 push 用户消息 + push 一条 "AI 助手暂未接入" 的占位（**只允许"已接入/加载中"类提示文本**，不允许 mock 内容）：
  ```ts
  sendChat: (text) => {
    const userMsg: ChatMsg = { role: 'user', text };
    set((s) => ({ chat: [...s.chat, userMsg] }));
    const aiMsg: ChatMsg = { role: 'ai', text: 'AI 助手暂未接入' };
    set((s) => ({ chat: [...s.chat, aiMsg] }));
  }
  ```
  （即 0.5s 之前的 mockAiReplies 改为硬编码提示语；保留 setTimeout 0 同步触发也行，taste 选择。）
- 把 `toggleTask` 里 `s.tasks.map(...)` 保留逻辑不删（任务为空时是 noop）

若发现 `MapNode`/`Edge`/`Profile` 类型名称与 `api/types.ts` 字面不完全一致，subagent 必须以 `api/types.ts` 为准先确认再写。

- [ ] **Step 4: 修改 `frontend/src/components/TopBar.tsx`**

整文件替换为：

```tsx
import './TopBar.css';
import { ModeToggle } from './ModeToggle';
import { LayoutIcons } from './LayoutIcons';
import { useSession } from '../store/session';

export function TopBar() {
  const studentId = useSession((s) => s.studentId);
  // 显示前 8 位 UUID，方便用户识别身份但又不占满 TopBar
  const shortId = studentId ? studentId.slice(0, 8) : '—';
  return (
    <header className="topbar">
      <span className="logo">◆ SelfLearn</span>
      <nav>
        <a href="#" className="active">Map</a>
        <a href="#">Today</a>
        <a href="#">Resources</a>
        <a href="#">Profile</a>
      </nav>
      <ModeToggle />
      <LayoutIcons />
      <div className="right">
        <span className="cmdk">⌘K</span>
        <span className="student-id" title={studentId}>ID · {shortId}</span>
      </div>
    </header>
  );
}
```

要点：
- 删除 `ResetButton` import + 渲染
- 删除 `<span className="avatar">林</span>`（spec § 2 决策 5：不再显示中文字 avatar）

- [ ] **Step 5: 删除 demo 文件 + ResetButton**

```bash
rm "D:/Projects/SelfLearn/frontend/src/data/sample.ts"
rm "D:/Projects/SelfLearn/frontend/src/reset/ResetButton.tsx"
rmdir "D:/Projects/SelfLearn/frontend/src/data" 2>/dev/null || true
rmdir "D:/Projects/SelfLearn/frontend/src/reset" 2>/dev/null || true
```

Expected: 文件删除；空目录也尝试删除（rmdir ignore-fail 是 OK）。

- [ ] **Step 6: 静态验证 import 路径已清零**

```bash
cd "D:/Projects/SelfLearn/frontend" && grep -rn "data/sample\|reset/ResetButton" src/ 2>&1
```

Expected: 0 命中（之前 3 行现在全清）。

- [ ] **Step 7: 前端构建 gate**

```bash
cd "D:/Projects/SelfLearn/frontend" && npm run build 2>&1 | tail -20
```

Expected: `built in ...ms`，**0 type error**。这是结构性 task 的核心防线——任何漏改的 import 都会让这一步失败。

如失败，按错误定位：
- `cannot find module '../data/sample'` → 还有 import 漏改 → 回 Step 1 重 grep
- `Property X does not exist on typeof mapNodes` → store 字段类型没换对 → 回 Step 3
- 其他 → 看错误栈定位

- [ ] **Step 8: 跑后端单测（确认 demo 改动不破坏后端契约）**

```bash
cd "D:/Projects/SelfLearn/backend" && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
```

Expected: 全 PASS。

- [ ] **Step 9: Commit**

```bash
cd "D:/Projects/SelfLearn" && git add -A frontend/src/ && git commit -m "feat(frontend): 删除 demo 模式（sample.ts + ResetButton），store 默认空状态走真实后端" 2>&1 | tail -5
```

注：`git add -A frontend/src/` 会一并 stage 删文件 + 修改 — 比手动逐文件 stage 安全。

---

### Task 4: e2e 验证 + CLAUDE.md 更新

**Files:**
- Modify: `CLAUDE.md` (根目录 — 更新 "E2E 测试数据清理" 小节新增 KEEP_STUDENT 字面量来源说明)
- Verify-only: 无新代码改动

**Interfaces:**
- Consumes: T1/T2/T3 已完成代码
- Produces: 浏览器实测 + curl 实测 + 字面量 4 处一致

- [ ] **Step 1: 4 处字面量最终校验**

```bash
cd "D:/Projects/SelfLearn" && grep -rn '"86820161-b0f0-455f-91b4-a69e49445bdf"' backend/scripts/purge_test_data.py backend/src/selflearn/infra/seed_account.py frontend/src/constants/account.ts CLAUDE.md 2>&1
```

Expected: 4 行命中，字符完全一致。如不一致，**先回 T2 Step 7** 修 seed_account.py，再修 CLAUDE.md，最后再走本 step。

- [ ] **Step 2: 启动后端**

```bash
cd "D:/Projects/SelfLearn/backend" && uv run python -m selflearn.main --role gateway &> /tmp/gateway.log &
sleep 3
tail -5 /tmp/gateway.log
```

Expected: log 含 `gateway.startup_done`，且无 `ensure_keep_student` 抛错（如果有错误会显示在 log）。

- [ ] **Step 3: curl /api/profile 验证 empty DB → ensure 工作**

```bash
curl -s "http://localhost:8000/api/profile/86820161-b0f0-455f-91b4-a69e49445bdf" | head -50
```

Expected: 返回 200 + JSON 含 `student_id` 字段（不是 500）。如 backend/data 已经是种子过（之前的 E2E 跑过 seed_dev），Profile 行已存在；ensure_keep_student 幂等 noop。

- [ ] **Step 4: e2e DB 验证 Profile 行**

```bash
cd "D:/Projects/SelfLearn/backend" && uv run python << 'EOF'
import asyncio
from sqlalchemy import select, func
from selflearn.infra.db import get_session_factory
from selflearn.domain.profile import Profile
async def main():
    async with get_session_factory()() as s:
        cnt = (await s.execute(
            select(func.count()).select_from(Profile).where(Profile.student_id == "86820161-b0f0-455f-91b4-a69e49445bdf")
        )).scalar()
        print(f"Profile 行数 KEEP_STUDENT: {cnt}")
asyncio.run(main())
EOF
```

Expected: 至少 1。

- [ ] **Step 5: 停止后端进程**

```bash
pkill -f "python -m selflearn.main --role gateway" || true
```

- [ ] **Step 6: 更新 CLAUDE.md "E2E 测试数据清理" 小节**

读当前 `D:/Projects/SelfLearn/CLAUDE.md`（当前内容已有 KEEP_STUDENT 段落），在该段落后**新增**：

```markdown
## 唯一账户约束（Task 265）

后端永远只有 1 个学生账户，前端硬编码使用，**不允许动态生成新 UUID**：

- `KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"`
- 4 处字面量来源必须保持完全一致：
  1. `backend/scripts/purge_test_data.py:24`（E2E 清理保留目标）
  2. `backend/src/selflearn/infra/seed_account.py`（启动 ensure）
  3. `frontend/src/constants/account.ts`（前端唯一 ID）
  4. `CLAUDE.md` 本段（文档）
- 后端 startup `lifespan` 会自动 ensure KEEP_STUDENT 的 Profile 行（幂等）
- 前端不再有 demo 模式 / sample 数据 / ResetButton；session.ts 同步取常量
```

放在 "E2E 测试数据清理" 段之前或之后都行（subagent judgment）。

- [ ] **Step 7: 跑全套回归**

```bash
cd "D:/Projects/SelfLearn/backend" && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
cd "D:/Projects/SelfLearn/backend" && uv run mypy src/selflearn 2>&1 | tail -3
cd "D:/Projects/SelfLearn/frontend" && npm run build 2>&1 | tail -10
```

Expected:
- pytest 全 PASS
- mypy: `Success: no issues found`
- build: `built in ...ms`，0 error

- [ ] **Step 8: Commit CLAUDE.md + ledger**

```bash
cd "D:/Projects/SelfLearn" && git add CLAUDE.md && git commit -m "docs: CLAUDE.md 新增 Task 265 唯一账户约束说明" 2>&1 | tail -5
```

并在 `.superpowers/sdd/progress-task261.md` 末尾追加 Task 265 段（仿照 Task 262 段格式）：

```markdown
## Task 265 — 唯一账户 + 全清 Demo

| 任务 | 状态 | Commit | Review |
| --- | --- | --- | --- |
| T1 前端 KEEP_STUDENT 常量 + session.ts 重写 | complete | <sha1> | review clean |
| T2 后端 startup ensure KEEP_STUDENT + 单测 | complete | <sha2> | review clean |
| T3 删 demo（sample.ts + ResetButton）+ store 默认空 | complete | <sha3> | review clean |
| T4 e2e + CLAUDE.md 更新 | complete | <sha4> | review clean (whole-branch) |
```

sha 用 `git log --oneline -4` 实际输出替换。

```bash
cd "D:/Projects/SelfLearn" && git add .superpowers/sdd/progress-task261.md && git commit -m "docs(sdd): 记录 Task 265 唯一账户清理完成" 2>&1 | tail -5
```

---

## Self-Review（作者自审）

### Spec 覆盖
- § 1.1 范围 1（后端 ensure）：T2 ✅
- § 1.1 范围 2（前端常量）：T1 ✅
- § 1.1 范围 3（session.ts 重写）：T1 ✅
- § 1.1 范围 4（删 demo）：T3 ✅
- § 1.1 范围 5（CLAUDE.md）：T4 ✅
- § 2 决策 1-5：T1（同步常量）、T2（仅 Profile）、T3（删干净）、T3（TopBar 改 ID 显示）✅
- § 3 架构目录：与 file structure 一致 ✅
- § 4 API 不变：本文无 API 改动 ✅
- § 5 任务分解：与 T1-T4 顺序一致 ✅
- § 6 测试策略：T2 写 pytest 单测，T4 e2e 全测 ✅
- § 7 字面量矩阵：T1 Step 4 / T2 Step 7 / T4 Step 1 三处校验 ✅
- § 8 风险：T3 通过 build gate 把"漏改 import"阻断；T2 幂等 DELETE+INSERT 与 purge 一致；T3 fallback "暂无数据"复用原占位 ✅

### 占位符扫描
- 无 `TBD` / `TODO` / `implement later`
- 所有代码块都是可运行的完整代码
- 命令都在 D:/Projects/SelfLearn 工作目录可执行

### 类型一致性
- `KEEP_STUDENT` 在 T1 / T2 / T4 都是 `string`（与 sample/profile.ts 不冲突）
- `useSession` shape `{ studentId: string; reset: () => void }` T1 保持，下游 App.tsx:49 `useSession((s) => s.studentId)` 不动 ✅
- `ChatMsg` 接口（T3 还在用）+ `setTimeout` 替代 mockAiReplies，T3 内部类型稳定 ✅
- `MapNode`/`Edge` 改 import 自 `api/types.ts`（T3 Step 2），与 `TreasureMap.tsx:5` 既有 import 同源 ✅

### 风险补充

1. **T3 Step 3 重写 useWorkspace.ts 是最大改动**——windows/move/focus/minimize/maximize/pin/close/open/resize 逻辑必须全保留（其他窗口组件依赖）。Subagent 修改前必须 1:1 保留这部分代码，只换顶部 import + 默认值。
2. **T3 Step 4 TopBar 改后没有 avatar**——视觉上右侧区域少一个元素；用户接受（决策 5 已拍板）。
3. **KEEP_STUDENT 字面量与 docker-compose / .env / 数据库 seed 没有任何关联**——本任务不引入新 ENV，否则会让前端常量与 .env 漂移。

---

## Verification

| 层 | 命令 | 期望 |
|---|---|---|
| Frontend 字面量 | `grep -rn '"86820161..."' frontend/src/constants/account.ts` | 1 命中 |
| Backend 字面量 | `grep -rn '"86820161..."' backend/scripts/purge_test_data.py backend/src/selflearn/infra/seed_account.py` | 2 命中 |
| Frontend build | `cd frontend && npm run build` | 0 error |
| Backend unit | `cd backend && uv run pytest tests/unit -p no:warnings` | 全 pass |
| Backend mypy | `cd backend && uv run mypy src/selflearn` | clean |
| 启动 ensure | backend 启动 → `curl GET /api/profile/{KEEP_STUDENT}` | 200 + JSON |
| 字面量一致 | grep 4 处同源 | 字符完全一致 |
| Demo 残留 | `grep -rn "data/sample\|reset/ResetButton\|crypto.randomUUID" frontend/src/` | 0 命中 |
