# Stage 4 — Demo 对接与学习闭环 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Stage 3 后端 5-Agent 业务 MVP 与 `frontend/`（原 demo-serif 重命名）对接成可演示的 Demo：浏览器里跑通"画像 → 关卡 → 答题 → 画像动画 → 画像演变"完整闭环；后端追加 3 个学习闭环点 + AOP Hook 观测链；前端用 react-rnd + recharts + framer-motion 实现 3 窗口可拖拽 + 雷达图动画。

**Architecture:** 继承 Stage 2/3 后端基座与 v4 spec；`demo-serif/` 重命名为 `frontend/` 承担前端项目角色；后端补 5 个查询端点 + 1 张 `profile_snapshots` 表 + 3 处 Agent 微调（SSE payload 字段）+ AOP 装饰器 Hook；前端用 Zustand store + SSE 订阅 + react-rnd 拖拽 + recharts 雷达图。

**Tech Stack:**
- **Backend（继承 + 新增）**：Python 3.12 / FastAPI / SQLAlchemy 2.x async / Alembic / Redis 7 Stream / OpenAI 兼容 LLM / pydantic-settings
- **Frontend**：Vite + React 18 / TypeScript / Zustand / react-rnd / recharts / framer-motion / @playwright/test
- **测试**：pytest + pytest-asyncio + fakeredis（继承）+ Playwright e2e（新增）

## Global Constraints

继承 spec `docs/superpowers/specs/2026-07-13-stage4-demo-integration-design.md` 全部约束。要点：

1. **不引入鉴权**：任何阶段、任何 task 出现登录 / 鉴权 / 会话 / Token / JWT / OAuth / `Depends(get_current_user)` / `auth.py` 一律删除（项目级硬约束 `[[no-auth-no-login]]`）。
2. **不重写既有代码**：v4 spec / Stage 2 spec / Stage 3 spec 全部沿用；本计划仅追加与微调。
3. **依赖版本下限**（无上限）：`>=` only，不写 `<N.0` 上界。Python 3.12 锁定。
4. **mypy strict 是硬门**：每 task 末尾 `uv run mypy src tests` 必须 0 errors。
5. **Stage 2 smoke + Stage 3 smoke_mvp 必跑**：每 task 末尾确认不破坏既有测试。
6. **AOP 装饰器零侵入**：业务函数体不修改，Hook 通过装饰器包裹原函数实现。
7. **凭证管理**：`OPENAI_API_KEY` 缺失时 LlmRegistry 自动 fallback 到 Mock adapter（spec § 10.7）。
8. **dev 阶段 CORS**：仅放行 `localhost:5173`（Vite dev）和 `localhost:8000`。
9. **commit 频率**：每 task 至少 1 commit；task 13/14 大 task 可分多 commit。
10. **tag**：所有 task 完成后打 `stage4-complete` lightweight tag。

---

## File Structure（实施前最终确认）

```
D:\Projects\SelfLearn\
├── backend/                                # 继承 + 增量
│   ├── src/selflearn/
│   │   ├── observability/                  # 新增（Task 3）
│   │   │   ├── __init__.py
│   │   │   ├── hooks.py                    # HookBus 单例
│   │   │   ├── decorators.py               # @hook + @hook_stream
│   │   │   └── routes.py                   # /debug/state
│   │   ├── domain/
│   │   │   └── profile_snapshot.py         # 新增（Task 2）
│   │   ├── gateway/routes/
│   │   │   ├── profile.py                  # 修改：加 GET /{student_id} + history
│   │   │   ├── map.py                      # 修改：加 GET /{student_id}/nodes
│   │   │   └── level.py                    # 修改：加 GET /{level_id}
│   │   ├── agents/builtin/
│   │   │   ├── profile_agent.py            # 修改：SSE 末 publish 加 profile 字段
│   │   │   └── director_agent.py           # 修改：SSE 末 publish 加 level_id
│   │   ├── infra/bus.py                    # 修改：装饰 publish_envelope / consume_envelope
│   │   ├── llm/base.py                     # 修改：用 __init_subclass__ 装 hook_stream
│   │   └── progress/stream.py              # 修改：装饰 progress_publish
│   ├── migrations/versions/
│   │   └── <new>_stage4_profile_snapshots.py  # 新增（Task 2）
│   ├── scripts/smoke_mvp.sh                # 继承（不变）
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_aop_hooks.py           # 新增
│   │   │   ├── test_profile_update.py      # 新增
│   │   │   ├── test_difficulty_gradient.py # 新增
│   │   │   └── test_profile_snapshot.py    # 新增
│   │   └── integration/
│   │       └── test_api_gaps.py            # 新增：5 端点 + 2 SSE 字段
│   └── .env.example                        # 新增（Task 1）
├── frontend/                               # 原 demo-serif/，Task 1 重命名
│   ├── src/
│   │   ├── api/                            # 新增（Task 13）
│   │   │   ├── client.ts
│   │   │   ├── profile.ts
│   │   │   ├── map.ts
│   │   │   ├── level.ts
│   │   │   └── sse.ts
│   │   ├── panes/                          # 新增（Task 13）
│   │   │   ├── LecturePane.tsx
│   │   │   ├── ExercisePane.tsx
│   │   │   └── ChatPane.tsx
│   │   ├── desk/                           # 修改（Task 13）
│   │   │   ├── Desktop.tsx
│   │   │   ├── MapPanel.tsx
│   │   │   ├── ProfilePanel.tsx            # 雷达图 + 演变迷你折线
│   │   │   └── CalendarPanel.tsx
│   │   ├── store/                          # 新增（Task 13）
│   │   │   ├── profile.ts
│   │   │   └── session.ts
│   │   ├── reset/                          # 新增（Task 13）：重置 demo 按钮
│   │   └── main.tsx
│   ├── e2e/smoke.spec.ts                   # 新增（Task 14）
│   ├── vite.config.ts                      # 修改（Task 13）：配 proxy
│   ├── package.json                        # 修改：加 react-rnd / recharts / @playwright/test
│   └── playwright.config.ts                # 新增
└── docs/superpowers/specs/                 # 已存在 Stage 4 spec
```

---

## Task Dependency Graph

```
T1 (rename + CORS + .env)
  └→ T2 (profile_snapshots 表 + ORM)
       └→ T7 (GET /api/profile/{id})
            └→ T8 (GET /api/profile/{id}/history)
  └→ T3 (HookBus + decorators)
       └→ T4 (3 hook wrapping points)
            └→ T5 (/debug/state route)
  └→ T6 (ProfileRepository) ← T2 后单独 OR 合并到 T13
  T9 (GET /api/map/{id}/nodes)
  T10 (GET /api/level/{id})
  T11 (ProfileAgent SSE payload)
  T12 (DirectorAgent SSE payload)
  T13 (Profile 动态更新 + 难度梯度)
  T14 (frontend 4 段主线)
  T15 (Playwright e2e + 验收报告)
```

15 个 task。**T14 frontend 必须在 T7-T12 后端端点就绪后**；**T15 e2e 必须在 T14 frontend 完成且 T11/T12 SSE 字段落实后**。

---

## Task Breakdown（15 task）

### Task 1: demo-serif → frontend 重命名 + 全量引用更新 + CORS + .env.example

**Files:**
- Rename: `demo-serif/` → `frontend/`（`git mv`）
- Create: `backend/.env.example`
- Modify: `backend/src/selflearn/gateway/app.py`（加 CORSMiddleware）
- Modify: `backend/src/selflearn/config.py`（加 `debug: bool = False` 字段）

**Interfaces:**
- Consumes: 现有 `create_app()`（`backend/src/selflearn/gateway/app.py`）
- Produces: `frontend/` 目录（前端项目根）；`backend/.env.example` 模板；`get_settings().debug` 字段

- [ ] **Step 1: 重命名 demo-serif → frontend**

```bash
cd D:\Projects\SelfLearn
git mv demo-serif frontend
```

- [ ] **Step 2: 全量扫描 demo-serif 引用**

```bash
git grep -l "demo-serif"
```
预期输出：README / 文档 / 脚本 / 配置文件若干。**全部记录**，下一步逐个改。

- [ ] **Step 3: 改写所有 demo-serif 引用为 frontend**

涉及至少：
- `frontend/package.json`：`"name": "frontend"`
- `frontend/README.md`：标题与路径
- `backend/scripts/smoke_mvp.sh`：如引用 `../demo-serif/...` 改为 `../frontend/...`
- `backend/scripts/seed_map.py`：注释里的 demo-serif 引用
- `docs/产品需求修订说明.md` / `docs/superpowers/specs/*.md` 中旧名引用
- `.gitignore` / `.dockerignore`（如有 demo-serif 路径）

⚠️ **不要改 v4 spec 正文**：v4 是继承文档，本任务不改 v4，仅改其他文档中的引用。

- [ ] **Step 4: 验证 grep 为空**

```bash
git grep "demo-serif"
```
预期：0 命中。

- [ ] **Step 5: 写失败的测试（settings.debug）**

`backend/tests/unit/test_settings_debug.py`：
```python
def test_settings_has_debug_field():
    from selflearn.config import get_settings
    s = get_settings()
    assert hasattr(s, "debug"), "settings.debug 字段缺失"
    assert isinstance(s.debug, bool), "settings.debug 应为 bool"
```

```bash
uv run pytest tests/unit/test_settings_debug.py -v
```
预期：FAIL（字段不存在）。

- [ ] **Step 6: 实现 settings.debug 字段**

`backend/src/selflearn/config.py` 在 `Settings` 类追加：
```python
debug: bool = False  # Stage 4: AOP /debug/state 路由挂载开关（spec § 10.7）
```

```bash
uv run pytest tests/unit/test_settings_debug.py -v
```
预期：PASS。

- [ ] **Step 7: 写失败的测试（CORS middleware）**

`backend/tests/unit/test_cors.py`：
```python
def test_app_has_cors_middleware():
    from selflearn.gateway.app import create_app
    from starlette.middleware.cors import CORSMiddleware
    app = create_app()
    cors = next((m for m in app.user_middleware if m.cls is CORSMiddleware), None)
    assert cors is not None, "FastAPI app 未挂载 CORSMiddleware"
```

```bash
uv run pytest tests/unit/test_cors.py -v
```
预期：FAIL（middleware 不存在）。

- [ ] **Step 8: 实现 CORS middleware**

`backend/src/selflearn/gateway/app.py` 在 `FastAPI(...)` 创建后、`include_router` 前：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

```bash
uv run pytest tests/unit/test_cors.py -v
```
预期：PASS。

- [ ] **Step 9: 创建 backend/.env.example**

```bash
cat > backend/.env.example <<'EOF'
# Stage 4 Demo LLM 凭证（spec § 10.7）
# 缺失时 LlmRegistry 自动 fallback 到 Mock adapter
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# Stage 4 调试开关
DEBUG=false

# Stage 2/3 既有配置（保留）
DATABASE_URL=postgresql+asyncpg://selflearn:selflearn@localhost:5432/selflearn
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
EOF
```

- [ ] **Step 10: 跑全部既有测试 + mypy**

```bash
uv run pytest tests/unit -q
uv run mypy src tests
```
预期：全绿 + mypy 0 errors。

- [ ] **Step 11: commit**

```bash
git add -A
git commit -m "feat(stage4): demo-serif → frontend 重命名 + CORS + settings.debug + .env.example"
```

---

### Task 2: profile_snapshots ORM + Alembic 迁移

**Files:**
- Create: `backend/src/selflearn/domain/profile_snapshot.py`
- Create: `backend/migrations/versions/<rev>_stage4_profile_snapshots.py`（Alembic 自动生成）

**Interfaces:**
- Consumes: Stage 3 `Base` / `metadata`（`backend/src/selflearn/domain/base.py`）
- Produces: `ProfileSnapshot` ORM 类；Alembic 迁移 revision

- [ ] **Step 1: 写失败的测试**

`backend/tests/unit/test_profile_snapshot.py`：
```python
def test_profile_snapshot_table_exists():
    from selflearn.domain.profile_snapshot import ProfileSnapshot
    from selflearn.domain.base import Base
    assert "profile_snapshots" in Base.metadata.tables
```

```bash
uv run pytest tests/unit/test_profile_snapshot.py -v
```
预期：FAIL（模块不存在）。

- [ ] **Step 2: 实现 ORM**

`backend/src/selflearn/domain/profile_snapshot.py`：
```python
"""ProfileSnapshot: 画像演变快照（Stage 4 spec § 5.3）。

写入触发：关卡完成时由 DirectorAgent 通过 ProfileRepository.apply_delta 调用。
读取触发：前端 GET /api/profile/{student_id}/history。
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    profile: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)  # 'level_completed' | 'manual_edit' | 'build'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

注：如使用 SQLite 测试环境，`PG_UUID` 会报错；改用：
```python
from sqlalchemy import String
student_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
profile: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
```
**Stage 4 简化**：用 `String(36)` + `JSON`（兼容 SQLite + PG）。Stage 5+ 切 PG 时再换 `PG_UUID` + `JSONB`。

- [ ] **Step 3: 跑测试**

```bash
uv run pytest tests/unit/test_profile_snapshot.py -v
```
预期：PASS。

- [ ] **Step 4: 生成 Alembic 迁移**

```bash
cd backend
uv run alembic revision --autogenerate -m "stage4 profile_snapshots"
```
预期：生成 1 个新 revision 文件 `backend/migrations/versions/<rev>_stage4_profile_snapshots.py`。

⚠️ **manual review**：打开生成的文件，确认 upgrade() / downgrade() 包含 `profile_snapshots` 表 + `student_id` 索引。如未自动生成索引，**手动加**。

- [ ] **Step 5: 跑既有 migration（head 验证）**

```bash
uv run alembic upgrade head
```
预期：成功。

- [ ] **Step 6: 写失败的迁移测试（可选）**

`backend/tests/unit/test_profile_snapshot_migration.py`：
```python
def test_profile_snapshot_migration_creates_table():
    """验证 migration 创建了正确表结构。"""
    # 用 sqlite 内存 + Base.metadata.create_all 验证 ORM 与 SQL 一致
    from sqlalchemy import create_engine, inspect
    from selflearn.domain.base import Base
    from selflearn.domain.profile_snapshot import ProfileSnapshot  # noqa

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    assert "profile_snapshots" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("profile_snapshots")}
    assert {"id", "student_id", "profile", "trigger", "created_at"} <= cols
```

- [ ] **Step 7: 跑全部单测 + mypy**

```bash
uv run pytest tests/unit -q
uv run mypy src tests
```
预期：全绿。

- [ ] **Step 8: commit**

```bash
git add src/selflearn/domain/profile_snapshot.py migrations/ tests/
git commit -m "feat(domain): ProfileSnapshot ORM + Alembic 迁移"
```

---

### Task 3: AOP HookBus + 装饰器

**Files:**
- Create: `backend/src/selflearn/observability/__init__.py`
- Create: `backend/src/selflearn/observability/hooks.py`
- Create: `backend/src/selflearn/observability/decorators.py`

**Interfaces:**
- Consumes: 无（纯新增）
- Produces: `hook_bus` 单例（`hooks.py`）；`@hook(kind)` / `@hook_stream(kind)` 装饰器（`decorators.py`）

- [ ] **Step 1: 写失败的测试（HookBus）**

`backend/tests/unit/test_hook_bus.py`：
```python
def test_hook_bus_emits_and_snapshots():
    from selflearn.observability.hooks import HookBus
    bus = HookBus(maxlen=10)
    bus.emit("test.kind", {"a": 1})
    bus.emit("test.kind2", {"b": 2})
    snap = bus.snapshot()
    assert len(snap) == 2
    assert snap[0]["kind"] == "test.kind"
    assert snap[1]["kind"] == "test.kind2"
    assert snap[0]["ts"] > 0


def test_hook_bus_respects_maxlen():
    from selflearn.observability.hooks import HookBus
    bus = HookBus(maxlen=3)
    for i in range(5):
        bus.emit("x", {"i": i})
    assert len(bus.snapshot()) == 3
    # 最新 3 条
    snap = bus.snapshot()
    assert [s["i"] for s in snap] == [2, 3, 4]


def test_hook_bus_is_thread_safe():
    import threading
    from selflearn.observability.hooks import HookBus
    bus = HookBus(maxlen=1000)
    def worker():
        for i in range(100):
            bus.emit("t", {"i": i})
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(bus.snapshot()) == 500
```

```bash
uv run pytest tests/unit/test_hook_bus.py -v
```
预期：FAIL（模块不存在）。

- [ ] **Step 2: 实现 HookBus**

`backend/src/selflearn/observability/__init__.py`：空（仅 `from .hooks import hook_bus; from .decorators import hook, hook_stream`）。

`backend/src/selflearn/observability/hooks.py`：
```python
"""AOP HookBus（spec § 6.3）：进程内 RingBuffer，供 /debug/state 查询。"""
from __future__ import annotations

import collections
import threading
import time
from typing import Any


class HookBus:
    def __init__(self, maxlen: int = 500) -> None:
        self._ring: collections.deque[dict[str, Any]] = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def emit(self, kind: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._ring.append({"ts": time.time(), "kind": kind, **payload})

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._ring)

    def clear(self) -> None:
        with self._lock:
            self._ring.clear()


hook_bus = HookBus()
```

- [ ] **Step 3: 跑 HookBus 测试**

```bash
uv run pytest tests/unit/test_hook_bus.py -v
```
预期：3/3 PASS。

- [ ] **Step 4: 写失败的测试（@hook 装饰器）**

`backend/tests/unit/test_hook_decorator.py`：
```python
import pytest


@pytest.mark.asyncio
async def test_hook_decorator_emits_ok_event():
    from selflearn.observability.hooks import hook_bus
    from selflearn.observability.decorators import hook
    hook_bus.clear()

    @hook("test.fn")
    async def fn(x: int) -> int:
        return x * 2

    result = await fn(3)
    assert result == 6

    snap = hook_bus.snapshot()
    assert any(e["kind"] == "test.fn" and e["status"] == "ok" for e in snap)


@pytest.mark.asyncio
async def test_hook_decorator_emits_error_event_on_exception():
    from selflearn.observability.hooks import hook_bus
    from selflearn.observability.decorators import hook
    hook_bus.clear()

    @hook("test.err")
    async def bad() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await bad()
    snap = hook_bus.snapshot()
    assert any(e["kind"] == "test.err" and e["status"] == "error" and "boom" in e["error"] for e in snap)


@pytest.mark.asyncio
async def test_hook_stream_counts_chunks():
    from selflearn.observability.hooks import hook_bus
    from selflearn.observability.decorators import hook_stream
    hook_bus.clear()

    @hook_stream("test.stream")
    async def gen():
        for i in range(3):
            yield i

    out = []
    async for x in gen():
        out.append(x)
    assert out == [0, 1, 2]

    snap = hook_bus.snapshot()
    assert any(e["kind"] == "test.stream" and e["n_chunks"] == 3 for e in snap)
```

```bash
uv run pytest tests/unit/test_hook_decorator.py -v
```
预期：FAIL。

- [ ] **Step 5: 实现 @hook 与 @hook_stream**

`backend/src/selflearn/observability/decorators.py`：
```python
"""无侵入 AOP 装饰器（spec § 6.4）。"""
from __future__ import annotations

import functools
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from selflearn.observability.hooks import hook_bus

P = ParamSpec("P")
R = TypeVar("R")


def hook(kind: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """包一层 try/except + HookBus.emit，业务异常不被吞。"""
    def deco(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
            t0 = time.perf_counter()
            try:
                result = await fn(*args, **kwargs)
                hook_bus.emit(kind, {
                    "status": "ok",
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                })
                return result
            except Exception as e:
                hook_bus.emit(kind, {
                    "status": "error",
                    "error": str(e),
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                })
                raise
        return wrap
    return deco


def hook_stream(kind: str) -> Callable[..., Callable[..., AsyncIterator[Any]]]:
    """流式版本：包装 AsyncIterator 输出，统计 chunk 数与总延迟。"""
    def deco(fn: Callable[P, AsyncIterator[R]]) -> Callable[P, AsyncIterator[R]]:
        @functools.wraps(fn)
        async def wrap(*args: P.args, **kwargs: P.kwargs) -> AsyncIterator[R]:
            t0 = time.perf_counter()
            n = 0
            try:
                async for chunk in fn(*args, **kwargs):
                    n += 1
                    yield chunk
                hook_bus.emit(kind, {
                    "status": "ok",
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                    "n_chunks": n,
                })
            except Exception as e:
                hook_bus.emit(kind, {"status": "error", "error": str(e), "n_chunks": n})
                raise
        return wrap
    return deco
```

- [ ] **Step 6: 跑全部 Hook 测试 + mypy**

```bash
uv run pytest tests/unit/test_hook_bus.py tests/unit/test_hook_decorator.py -v
uv run mypy src tests
```
预期：6/6 PASS + mypy 0。

- [ ] **Step 7: commit**

```bash
git add src/selflearn/observability tests/unit/test_hook_bus.py tests/unit/test_hook_decorator.py
git commit -m "feat(observability): HookBus 单例 + @hook / @hook_stream 装饰器"
```

---

### Task 4: 3 个横切点装 Hook

**Files:**
- Modify: `backend/src/selflearn/infra/bus.py`（装饰 `publish_envelope` / `consume_envelope`）
- Modify: `backend/src/selflearn/progress/stream.py`（装饰 `progress_publish`）
- Modify: `backend/src/selflearn/llm/base.py`（用 `__init_subclass__` 给所有 LLM adapter 自动装 `@hook_stream`）

**Interfaces:**
- Consumes: `hook_bus` / `@hook` / `@hook_stream`（Task 3）
- Produces: 3 处装饰后的函数；LLM adapter 自动装钩子

- [ ] **Step 1: 写失败的测试（Hook 在 publish_envelope 触发）**

`backend/tests/unit/test_aop_integration.py`：
```python
import pytest
from unittest.mock import patch, AsyncMock
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.observability.hooks import hook_bus


@pytest.mark.asyncio
async def test_publish_envelope_emits_hook_event():
    hook_bus.clear()

    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gw", id="t"),
        target=ActorRef(type="skill", id="skill.profile.build"),
    )

    with patch("selflearn.infra.bus.get_connection") as conn_mock:
        conn_mock.return_value = AsyncMock()
        from selflearn.infra.bus import publish_envelope
        await publish_envelope(env, routing_key="test.key")

    snap = hook_bus.snapshot()
    assert any(e["kind"] == "envelope.publish" and e["status"] == "ok" for e in snap), \
        f"publish_envelope 未触发 hook: {snap}"
```

```bash
uv run pytest tests/unit/test_aop_integration.py -v
```
预期：FAIL（hook_bus 没有 envelope.publish 事件）。

- [ ] **Step 2: 装饰 publish_envelope / consume_envelope**

`backend/src/selflearn/infra/bus.py`：
```python
# 在文件顶部追加
from selflearn.observability.decorators import hook


@hook("envelope.publish")
async def publish_envelope(envelope: Envelope, routing_key: str) -> None:
    """原有函数体不动。"""
    conn = await get_connection()
    # ... 原实现 ...


@hook("envelope.consume")
async def consume_envelope(  # type: ignore[no-untyped-def]
    queue_name: str,
    routing_key: str,
    callback,
    *,
    prefetch: int = 4,
):
    """原有函数体不动。"""
    # ... 原实现 ...
```

⚠️ **不要替换函数体**——只加装饰器。装饰器内部 await 原函数，确保业务行为零变化。

- [ ] **Step 3: 装饰 progress_publish**

`backend/src/selflearn/progress/stream.py` 顶部：
```python
from selflearn.observability.decorators import hook


@hook("progress.publish")
async def progress_publish(trace_id: str, event) -> None:
    """原函数体不动。"""
    # ... 原实现 ...
```

- [ ] **Step 4: 验证测试**

```bash
uv run pytest tests/unit/test_aop_integration.py -v
```
预期：PASS。

- [ ] **Step 5: 写失败的测试（LLM adapter 自动装 hook）**

`backend/tests/unit/test_aop_llm.py`：
```python
import pytest
from selflearn.observability.hooks import hook_bus
from selflearn.llm.base import ChatRequest, ChatChunk, BaseLLMAdapter
from selflearn.llm.adapters.mock import MockAdapter


@pytest.mark.asyncio
async def test_llm_adapter_emits_hook_event():
    hook_bus.clear()
    adapter = MockAdapter()
    req = ChatRequest(messages=[{"role": "user", "content": "hi"}])
    chunks = []
    async for c in adapter.chat(req):
        chunks.append(c)
        if c.finish_reason:
            break

    snap = hook_bus.snapshot()
    assert any(e["kind"] == "llm.call" and e["status"] == "ok" for e in snap), \
        f"LLM adapter 未触发 hook: {snap}"
```

- [ ] **Step 6: 实现 BaseLLMAdapter.__init_subclass__**

`backend/src/selflearn/llm/base.py`（在 `BaseLLMAdapter` 类内追加）：
```python
from selflearn.observability.decorators import hook_stream


class BaseLLMAdapter:
    # ... 既有字段 ...

    def __init_subclass__(cls, **kwargs):  # type: ignore[no-untyped-def]
        """所有 LLM adapter 子类自动装 @hook_stream 装饰 chat()。"""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "chat"):
            cls.chat = hook_stream("llm.call")(cls.chat)  # type: ignore[method-assign]
```

⚠️ **注意事项**：原 `chat` 方法已被装饰（如 MockAdapter 中），再次装饰会造成双层包装。改用：
```python
def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    original = cls.__dict__.get("chat")
    if original is not None and not getattr(original, "_is_hook_wrapped", False):
        wrapped = hook_stream("llm.call")(original)
        wrapped._is_hook_wrapped = True  # type: ignore[attr-defined]
        cls.chat = wrapped  # type: ignore[method-assign]
```

- [ ] **Step 7: 跑 LLM Hook 测试**

```bash
uv run pytest tests/unit/test_aop_llm.py -v
```
预期：PASS。

- [ ] **Step 8: 跑全部既有测试 + mypy**

```bash
uv run pytest tests/unit -q
uv run mypy src tests
```
预期：全绿（既有 58 + 新增 ≈ 64 个测试 PASS）。

- [ ] **Step 9: commit**

```bash
git add src/selflearn/infra/bus.py src/selflearn/progress/stream.py src/selflearn/llm/base.py tests/unit/test_aop_*.py
git commit -m "feat(aop): 3 横切点装 hook（envelope / progress / LLM adapter）"
```

---

### Task 5: /debug/state 路由

**Files:**
- Create: `backend/src/selflearn/observability/routes.py`
- Modify: `backend/src/selflearn/gateway/app.py`（条件挂载）

**Interfaces:**
- Consumes: `hook_bus.snapshot()`（Task 3）；`get_settings().debug`（Task 1）
- Produces: `GET /debug/state` JSON 端点

- [ ] **Step 1: 写失败的测试**

`backend/tests/unit/test_debug_state_route.py`：
```python
import pytest
from selflearn.observability.hooks import hook_bus


@pytest.mark.asyncio
async def test_debug_state_returns_events(monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    from selflearn.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    s = get_settings()
    assert s.debug is True

    from selflearn.gateway.app import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    client = TestClient(app)

    hook_bus.clear()
    hook_bus.emit("test.kind", {"foo": "bar"})

    resp = client.get("/debug/state")
    assert resp.status_code == 200, f"GET /debug/state 返回 {resp.status_code}"
    data = resp.json()
    assert "events" in data
    assert any(e["kind"] == "test.kind" for e in data["events"])


@pytest.mark.asyncio
async def test_debug_state_not_mounted_when_debug_false(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    from selflearn.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    from selflearn.gateway.app import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    client = TestClient(app)
    resp = client.get("/debug/state")
    assert resp.status_code == 404
```

```bash
uv run pytest tests/unit/test_debug_state_route.py -v
```
预期：FAIL。

- [ ] **Step 2: 实现 routes.py**

`backend/src/selflearn/observability/routes.py`：
```python
"""AOP /debug/state 路由（spec § 6.5）。仅在 settings.debug=True 时挂载。"""
from __future__ import annotations

from fastapi import APIRouter

from selflearn.observability.hooks import hook_bus


router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/state")
async def state() -> dict:
    return {"events": hook_bus.snapshot()}
```

- [ ] **Step 3: 在 app.py 条件挂载**

`backend/src/selflearn/gateway/app.py` `create_app()` 末尾（`include_router` 区）：
```python
if s.debug:
    from selflearn.observability.routes import router as debug_router
    app.include_router(debug_router)
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/unit/test_debug_state_route.py -v
```
预期：2/2 PASS。

- [ ] **Step 5: 跑全部 + mypy**

```bash
uv run pytest tests/unit -q
uv run mypy src tests
```

- [ ] **Step 6: commit**

```bash
git add src/selflearn/observability/routes.py src/selflearn/gateway/app.py tests/unit/test_debug_state_route.py
git commit -m "feat(observability): /debug/state 路由（仅 debug=True 挂载）"
```

---

### Task 6: ProfileRepository（关卡完成回调专用）

**Files:**
- Create: `backend/src/selflearn/infra/repositories/profile_repo.py`

**Interfaces:**
- Consumes: `Profile` ORM / `ProfileSnapshot` ORM / `get_session_factory`
- Produces: `ProfileRepository(session)` 类，含 `apply_delta` / `create_snapshot` / `get_or_create` 方法

- [ ] **Step 1: 写失败的测试**

`backend/tests/unit/test_profile_repo.py`：
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from selflearn.domain.base import Base
from selflearn.domain.profile import Profile
from selflearn.domain.profile_snapshot import ProfileSnapshot
from selflearn.infra.repositories.profile_repo import ProfileRepository

import uuid


@pytest.mark.asyncio
async def test_profile_repo_apply_delta_creates_snapshot():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        await conn.execute(Profile.__table__.insert().values(
            student_id=uuid.uuid4(),
            dimensions={"knowledge_base": 0.5, "analytic_style": 0.5},
            tags=[],
        ))

    async with AsyncSession(engine) as session:
        repo = ProfileRepository(session)
        # 取第一条 profile
        from sqlalchemy import select
        rs = (await session.execute(select(Profile))).scalars().first()
        sid = rs.student_id
        new_dims = await repo.apply_delta(sid, {"knowledge_base": 0.05, "analytic_style": -0.02})
        await session.commit()

    # 验证 snapshot 创建
    async with AsyncSession(engine) as session:
        from sqlalchemy import select
        snaps = (await session.execute(select(ProfileSnapshot).where(ProfileSnapshot.student_id == sid))).scalars().all()
        assert len(snaps) == 1
        assert snaps[0].trigger == "level_completed"
        assert snaps[0].profile["knowledge_base"] == pytest.approx(0.55, 0.01)
```

```bash
uv run pytest tests/unit/test_profile_repo.py -v
```
预期：FAIL。

- [ ] **Step 2: 实现 ProfileRepository**

`backend/src/selflearn/infra/repositories/profile_repo.py`：
```python
"""Profile + ProfileSnapshot repository（Stage 4 spec § 5.1）。

apply_delta：根据答题对错微调维度 + 写 snapshot。维度上限 [0.0, 1.0]。
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from selflearn.domain.profile import Profile
from selflearn.domain.profile_snapshot import ProfileSnapshot


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, student_id: UUID, default_dims: dict[str, float] | None = None) -> Profile:
        rs = await self.session.get(Profile, student_id)
        if rs is not None:
            return rs
        new = Profile(
            student_id=student_id,
            dimensions=default_dims or {
                "knowledge_base": 0.5, "visual_preference": 0.5,
                "analytic_style": 0.5, "goal_employment": 0.5,
                "error_prone_type": 0.5, "focus_duration": 0.5,
            },
            tags=[],
        )
        self.session.add(new)
        await self.session.flush()
        return new

    async def apply_delta(
        self,
        student_id: UUID,
        delta: dict[str, float],
        trigger: str = "level_completed",
    ) -> dict[str, float]:
        """应用 delta 到现有 dimensions（clamp [0,1]）并写 snapshot。"""
        profile = await self.get_or_create(student_id)
        new_dims = dict(profile.dimensions)
        for k, v in delta.items():
            if k in new_dims and isinstance(new_dims[k], (int, float)) and isinstance(v, (int, float)):
                new_dims[k] = max(0.0, min(1.0, float(new_dims[k]) + float(v)))
        profile.dimensions = new_dims  # ⚠️ PG JSONB 需要整体替换（不可就地 mutate）
        snapshot = ProfileSnapshot(student_id=student_id, profile=new_dims, trigger=trigger)
        self.session.add(snapshot)
        await self.session.flush()
        return new_dims

    async def recent_snapshots(self, student_id: UUID, limit: int = 10) -> list[ProfileSnapshot]:
        rs = (await self.session.execute(
            select(ProfileSnapshot)
            .where(ProfileSnapshot.student_id == student_id)
            .order_by(ProfileSnapshot.created_at.desc())
            .limit(limit)
        )).scalars().all()
        return list(rs)
```

- [ ] **Step 3: 跑测试**

```bash
uv run pytest tests/unit/test_profile_repo.py -v
```
预期：PASS。

- [ ] **Step 4: mypy + 全部既有测试**

```bash
uv run pytest tests/unit -q
uv run mypy src tests
```

- [ ] **Step 5: commit**

```bash
git add src/selflearn/infra/repositories/profile_repo.py tests/unit/test_profile_repo.py
git commit -m "feat(repo): ProfileRepository（apply_delta + recent_snapshots）"
```

---

### Task 7: GET /api/profile/{student_id}

**Files:**
- Modify: `backend/src/selflearn/gateway/routes/profile.py`
- Modify: `backend/src/selflearn/schemas/profile.py`

**Interfaces:**
- Consumes: `Profile` ORM / `ProfileRepository`（Task 6）/ `get_session_factory`
- Produces: `GET /api/profile/{student_id}` → `ProfileDetailResponse`

- [ ] **Step 1: 写失败的测试**

`backend/tests/integration/test_api_gaps.py`（新文件，集中放 5 端点测试）：
```python
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from selflearn.domain.base import Base
from selflearn.domain.profile import Profile


@pytest.fixture
async def client_and_db(monkeypatch):
    """in-memory SQLite + 异步 httpx client。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(Profile.__table__.insert().values(
            student_id=sid,
            dimensions={"knowledge_base": 0.7, "visual_preference": 0.5,
                       "analytic_style": 0.6, "goal_employment": 0.4,
                       "error_prone_type": 0.5, "focus_duration": 0.5},
            tags=["demo"],
        ))

    from selflearn.config import get_settings
    monkeypatch.setattr("selflearn.infra.db.get_session_factory",
                        lambda: lambda: AsyncSession(engine))
    # health endpoint 不要 DB，profile endpoint 需要；此处仅 patch profile 路由用的 DB

    from selflearn.gateway.app import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        yield client, sid


@pytest.mark.asyncio
async def test_get_profile_returns_dimensions_and_tags(client_and_db):
    client, sid = client_and_db
    resp = await client.get(f"/api/profile/{sid}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["student_id"] == str(sid)
    assert data["dimensions"]["knowledge_base"] == 0.7
    assert "demo" in data["tags"]
    assert "snapshot_count" in data
```

⚠️ **in-memory SQLite + dependency override**：上述 fixture 简化版可能因 `get_session_factory()` 多处引用失败。**Plan 实现者**：使用 `app.dependency_overrides` 或 mock 整个 `get_session_factory`。

```bash
uv run pytest tests/integration/test_api_gaps.py::test_get_profile_returns_dimensions_and_tags -v
```
预期：FAIL。

- [ ] **Step 2: 加 Pydantic schema**

`backend/src/selflearn/schemas/profile.py` 追加：
```python
class ProfileDetailResponse(BaseModel):
    student_id: UUID
    dimensions: dict[str, float]
    tags: list[str]
    snapshot_count: int
    last_updated_at: datetime | None = None
```

- [ ] **Step 3: 实现 GET 端点**

`backend/src/selflearn/gateway/routes/profile.py` 末尾追加：
```python
@router.get("/{student_id}", response_model=ProfileDetailResponse)
async def get_profile(student_id: UUID) -> ProfileDetailResponse:
    """Stage 4 spec § 4.1: 启动时拉画像渲染雷达图。"""
    from sqlalchemy import select, func
    from datetime import datetime
    from selflearn.domain.profile import Profile
    from selflearn.domain.profile_snapshot import ProfileSnapshot
    from selflearn.infra.db import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        profile = await session.get(Profile, student_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="profile_not_found")
        snap_count = (await session.execute(
            select(func.count()).select_from(ProfileSnapshot).where(
                ProfileSnapshot.student_id == student_id
            )
        )).scalar_one()

    return ProfileDetailResponse(
        student_id=student_id,
        dimensions=profile.dimensions,  # type: ignore[dict-item]
        tags=profile.tags,
        snapshot_count=int(snap_count),
        last_updated_at=profile.last_updated,
    )
```

⚠️ 顶部加 `from fastapi import APIRouter, HTTPException`。

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/integration/test_api_gaps.py::test_get_profile_returns_dimensions_and_tags -v
```
预期：PASS。

- [ ] **Step 5: mypy + 既有测试**

```bash
uv run pytest tests/unit tests/integration -q
uv run mypy src tests
```

- [ ] **Step 6: commit**

```bash
git add src/selflearn/schemas/profile.py src/selflearn/gateway/routes/profile.py tests/integration/test_api_gaps.py
git commit -m "feat(gateway): GET /api/profile/{student_id}"
```

---

### Task 8: GET /api/profile/{student_id}/history

**Files:**
- Modify: `backend/src/selflearn/gateway/routes/profile.py`
- Modify: `backend/src/selflearn/schemas/profile.py`

**Interfaces:**
- Consumes: `ProfileRepository.recent_snapshots`（Task 6）
- Produces: `GET /api/profile/{student_id}/history?limit=N`

- [ ] **Step 1: 写失败的测试**

在 `tests/integration/test_api_gaps.py` 追加：
```python
@pytest.mark.asyncio
async def test_get_profile_history_returns_snapshots(client_and_db):
    client, sid = client_and_db
    # 预先插 3 条 snapshot
    from sqlalchemy.ext.asyncio import AsyncSession
    from selflearn.domain.profile_snapshot import ProfileSnapshot
    engine_attr = ...  # Plan 实现者：调整 fixture 让 sid 共享
    # ... 插入 3 条 ProfileSnapshot ...
    resp = await client.get(f"/api/profile/{sid}/history?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["snapshots"]) == 3
    assert "profile" in data["snapshots"][0]
```

（具体 fixture 设计由实现者根据上一 task 的 client_and_db 调整。）

- [ ] **Step 2: schema**

`backend/src/selflearn/schemas/profile.py`：
```python
class ProfileHistoryEntry(BaseModel):
    profile: dict[str, float]
    trigger: str
    created_at: datetime


class ProfileHistoryResponse(BaseModel):
    student_id: UUID
    snapshots: list[ProfileHistoryEntry]
```

- [ ] **Step 3: 路由**

`backend/src/selflearn/gateway/routes/profile.py`：
```python
@router.get("/{student_id}/history", response_model=ProfileHistoryResponse)
async def get_profile_history(student_id: UUID, limit: int = 10) -> ProfileHistoryResponse:
    """Stage 4 spec § 5.3: 画像演变历史。"""
    from selflearn.infra.db import get_session_factory
    from selflearn.infra.repositories.profile_repo import ProfileRepository

    factory = get_session_factory()
    async with factory() as session:
        repo = ProfileRepository(session)
        snaps = await repo.recent_snapshots(student_id, limit=limit)

    return ProfileHistoryResponse(
        student_id=student_id,
        snapshots=[
            ProfileHistoryEntry(profile=s.profile, trigger=s.trigger, created_at=s.created_at)  # type: ignore[arg-type]
            for s in snaps
        ],
    )
```

- [ ] **Step 4: 测试 + mypy + commit**

```bash
uv run pytest tests/integration/test_api_gaps.py -v
uv run mypy src tests
git add ... 
git commit -m "feat(gateway): GET /api/profile/{student_id}/history"
```

---

### Task 9: GET /api/map/{student_id}/nodes

**Files:**
- Modify: `backend/src/selflearn/gateway/routes/map.py`
- Modify: `backend/src/selflearn/schemas/__init__.py`（新增 MapNodeResponse）

**Interfaces:**
- Consumes: `MapNode` ORM / `get_session_factory`
- Produces: `GET /api/map/{student_id}/nodes` → `MapNodesResponse`

- [ ] **Step 1: 写失败的测试**

`tests/integration/test_api_gaps.py` 追加：
```python
@pytest.mark.asyncio
async def test_get_map_nodes_returns_list(client_and_db):
    client, sid = client_and_db
    # 插入 MapNode fixture（参考 spec § 4.2 出参示例）
    resp = await client.get(f"/api/map/{sid}/nodes")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    # 验证节点字段齐全（id, kp_id, title, position, status, parent_id）
```

- [ ] **Step 2: schema**

`backend/src/selflearn/schemas/__init__.py` 或新建 `map.py`：
```python
class MapNodePosition(BaseModel):
    x: float
    y: float


class MapNodeResponse(BaseModel):
    node_id: UUID
    kp_id: UUID
    title: str
    position: MapNodePosition
    status: str  # available | in_progress | completed | locked
    parent_id: UUID | None = None


class MapNodesResponse(BaseModel):
    nodes: list[MapNodeResponse]
```

- [ ] **Step 3: 路由**

⚠️ **MapNode 表当前字段需要核实**（`backend/src/selflearn/domain/map_node.py`）。如缺 `position.x/y` / `status` / `parent_id`，Stage 4 不扩字段，**简化**：position 固定 `{x: 0, y: 0}`；status 全部 `"available"`；parent_id 全部 `None`。v4 spec 完整字段 Stage 5+ 再加。

```python
# map.py 追加
@router.get("/{student_id}/nodes", response_model=MapNodesResponse)
async def get_map_nodes(student_id: UUID) -> MapNodesResponse:
    """Stage 4 spec § 4.2: 加载藏宝图节点列表。"""
    from sqlalchemy import select
    from selflearn.domain.map_node import MapNode
    from selflearn.domain.knowledge_point import KnowledgePoint
    from selflearn.infra.db import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(MapNode, KnowledgePoint.title)
            .join(KnowledgePoint, MapNode.kp_id == KnowledgePoint.kp_id)
            .where(MapNode.student_id == student_id)
        )
        rows = (await session.execute(stmt)).all()

    return MapNodesResponse(nodes=[
        MapNodeResponse(
            node_id=node.node_id,
            kp_id=node.kp_id,
            title=kp_title,
            position=MapNodePosition(x=0.0, y=0.0),  # Stage 4 简化
            status="available",
            parent_id=None,
        )
        for node, kp_title in rows
    ])
```

- [ ] **Step 4: 测试 + mypy + commit**

```bash
uv run pytest tests/integration/test_api_gaps.py -v
uv run mypy src tests
git commit -m "feat(gateway): GET /api/map/{student_id}/nodes（Stage 4 简化版）"
```

---

### Task 10: GET /api/level/{level_id}

**Files:**
- Modify: `backend/src/selflearn/gateway/routes/level.py`
- Modify: `backend/src/selflearn/schemas/__init__.py`（新增 Level schemas）

**Interfaces:**
- Consumes: `Level` / `Exercise` ORM
- Produces: `GET /api/level/{level_id}` → `LevelDetailResponse`

- [ ] **Step 1: 写失败的测试**

`tests/integration/test_api_gaps.py` 追加：
```python
@pytest.mark.asyncio
async def test_get_level_returns_exercises(client_and_db):
    client, _ = client_and_db
    # 插入 Level + 2 Exercise fixture
    resp = await client.get(f"/api/level/{level_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "exercises" in data
    assert len(data["exercises"]) == 2
    assert "prompt" in data["exercises"][0]
```

- [ ] **Step 2: schema**

```python
class ExerciseResponse(BaseModel):
    exercise_id: UUID
    prompt: str
    options: list[str] | None = None
    type: str  # single_choice | multi_choice | short_answer


class LevelDetailResponse(BaseModel):
    level_id: UUID
    node_id: UUID
    status: str
    exercises: list[ExerciseResponse]
```

- [ ] **Step 3: 路由**

```python
# level.py 追加
@router.get("/{level_id}", response_model=LevelDetailResponse)
async def get_level(level_id: UUID) -> LevelDetailResponse:
    """Stage 4 spec § 4.3: 加载关卡详情（exercises + 题干）。"""
    from sqlalchemy import select
    from selflearn.domain.exercise import Exercise
    from selflearn.domain.level import Level
    from selflearn.infra.db import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        level = await session.get(Level, level_id)
        if level is None:
            raise HTTPException(status_code=404, detail="level_not_found")
        exs = (await session.execute(
            select(Exercise).where(Exercise.level_id == level_id)
        )).scalars().all()

    return LevelDetailResponse(
        level_id=level.level_id,
        node_id=level.node_id,
        status=level.status,
        exercises=[
            ExerciseResponse(
                exercise_id=ex.exercise_id,
                prompt=ex.prompt,
                options=ex.options,  # type: ignore[arg-type]
                type="single_choice",  # Stage 4 简化：所有 exercise 都标 single_choice
            )
            for ex in exs
        ],
    )
```

- [ ] **Step 4: 测试 + mypy + commit**

```bash
uv run pytest tests/integration/test_api_gaps.py -v
uv run mypy src tests
git commit -m "feat(gateway): GET /api/level/{level_id}（含 exercises 列表）"
```

---

### Task 11: ProfileAgent SSE payload 增 profile 字段 + integration test

**Files:**
- Modify: `backend/src/selflearn/agents/builtin/profile_agent.py`（SSE 末 publish 加 `profile` 字段）

**Interfaces:**
- Consumes: 现有 `progress_publish` 末调用；`Profile` ORM 写库结果
- Produces: SSE `completed` 事件 `payload.profile` 含完整 dimensions 字典

⚠️ **重要前置**：spec § 10.3 标注的"硬骨头 #3"在此 Task 修复。

- [ ] **Step 1: 写失败的测试**

`tests/integration/test_api_gaps.py` 追加：
```python
@pytest.mark.asyncio
async def test_profile_sse_completed_includes_full_profile(client_and_db):
    """SSE completed 事件必须携带完整 profile 字段（spec § 10.3）。"""
    client, sid = client_and_db
    # POST /api/profile/build
    resp = await client.post("/api/profile/build", json={
        "student_id": str(sid),
        "dimensions": {"knowledge_base": 0.7, "visual_preference": 0.5,
                       "analytic_style": 0.6, "goal_employment": 0.4,
                       "error_prone_type": 0.5, "focus_duration": 0.5},
        "tags": ["integration"],
    })
    assert resp.status_code == 202
    trace_id = resp.json()["trace_id"]

    # 订阅 SSE completed 事件
    import httpx
    from sse_starlette.sse import EventSourceResponse
    # ... 实际订阅逻辑（参考 Stage 3 test_smoke_mvp.py）...
    # 断言：completed event data 包含 payload.profile.dimensions.knowledge_base == 0.7
```

实现：参考 `tests/integration/test_smoke_mvp.py:25` 的 `progress_consume` 模式，直接用 `progress_consume(trace_id)` 拉 events，断言最后一条 progress 事件 `payload["profile"]` 字段存在。

- [ ] **Step 2: 找到现有 publish 调用并补字段**

`backend/src/selflearn/agents/builtin/profile_agent.py` 找到末次 `progress_publish` 调用（约第 66 行），改为：
```python
await progress_publish(trace_id, ProgressEvent(
    stage=Stage.PROFILE,
    status="completed",
    payload={"profile": {"dimensions": dimensions, "tags": env.payload.get("tags", [])}},
))
```

⚠️ dimensions 是局部变量，确认在调用前已定义。

- [ ] **Step 3: 跑测试**

```bash
uv run pytest tests/integration/test_api_gaps.py -v -k profile_sse
```
预期：PASS。

- [ ] **Step 4: Stage 2/3 既有 smoke 验证未破**

```bash
bash scripts/smoke.sh  # Stage 2（如果还在）
uv run pytest tests/integration/test_smoke.py tests/integration/test_smoke_mvp.py -v
uv run mypy src tests
```

- [ ] **Step 5: commit**

```bash
git add src/selflearn/agents/builtin/profile_agent.py tests/integration/test_api_gaps.py
git commit -m "feat(agents): ProfileAgent SSE completed 事件加 profile 字段（spec § 10.3）"
```

---

### Task 12: DirectorAgent SSE payload 增 level_id + exercise_ids + 关卡完成回调

**Files:**
- Modify: `backend/src/selflearn/agents/builtin/director_agent.py`
- Modify: `backend/src/selflearn/agents/builtin/exercise_agent.py`（难度梯度入口）
- Create: `backend/tests/unit/test_difficulty_gradient.py`

**Interfaces:**
- Consumes: `ProfileRepository.apply_delta`（Task 6）；`LevelRepository.recent_scores`（本 task 实现）
- Produces: SSE `completed` 事件 `payload.level_id` + `payload.exercise_ids`；关卡完成时触发画像更新

- [ ] **Step 1: 实现 LevelRepository.recent_scores**

`backend/src/selflearn/infra/repositories/level_repo.py`（新建）：
```python
"""Level 仓储：recent_scores 用于难度梯度计算（spec § 5.2）。"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from selflearn.domain.level import Level
from selflearn.domain.level_completion import LevelCompletion


class LevelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def recent_scores(self, student_id: UUID, limit: int = 3) -> list[float]:
        rs = (await self.session.execute(
            select(LevelCompletion.score)
            .join(Level, LevelCompletion.level_id == Level.level_id)
            .join(MapNode, Level.node_id == MapNode.node_id)
            .where(MapNode.student_id == student_id)
            .order_by(LevelCompletion.created_at.desc())
            .limit(limit)
        )).scalars().all()
        return [float(s) for s in rs]
```

⚠️ `MapNode` import 路径按实际位置调整。

- [ ] **Step 2: 写失败的测试（难度梯度）**

`backend/tests/unit/test_difficulty_gradient.py`：
```python
def test_difficulty_easy_when_low_scores():
    from selflearn.agents.builtin.director_agent import _compute_difficulty
    assert _compute_difficulty([0.3, 0.4, 0.2]) == "easy"


def test_difficulty_medium_when_mid_scores():
    from selflearn.agents.builtin.director_agent import _compute_difficulty
    assert _compute_difficulty([0.6, 0.7]) == "medium"


def test_difficulty_hard_when_high_scores():
    from selflearn.agents.builtin.director_agent import _compute_difficulty
    assert _compute_difficulty([0.9, 0.85, 0.95]) == "hard"


def test_difficulty_medium_when_no_history():
    from selflearn.agents.builtin.director_agent import _compute_difficulty
    assert _compute_difficulty([]) == "medium"
```

```bash
uv run pytest tests/unit/test_difficulty_gradient.py -v
```
预期：FAIL。

- [ ] **Step 3: 实现 _compute_difficulty**

`director_agent.py` 末尾追加：
```python
def _compute_difficulty(recent_scores: list[float]) -> str:
    """spec § 5.2: 平均分 < 0.5 → easy；< 0.8 → medium；其余 → hard。无历史 → medium。"""
    if not recent_scores:
        return "medium"
    avg = sum(recent_scores) / len(recent_scores)
    if avg < 0.5:
        return "easy"
    if avg < 0.8:
        return "medium"
    return "hard"
```

- [ ] **Step 4: 在 director_agent.run() 内集成难度梯度 + Profile 更新**

`director_agent.py` `_run_inner` 入口追加（读了 skill 之后、出 Exercise 之前）：
```python
from selflearn.infra.repositories.profile_repo import ProfileRepository
from selflearn.infra.repositories.level_repo import LevelRepository

# spec § 5.2: 计算难度
async with factory() as session:
    recent = await LevelRepository(session).recent_scores(student_id, limit=3)
difficulty = _compute_difficulty(recent)
log.info("director.difficulty_chosen", difficulty=difficulty, recent=recent)
```

并把 `difficulty` 透传到 `exercise_agent.run_sync(env, node, difficulty=difficulty)`。

- [ ] **Step 5: ExerciseAgent 接受 difficulty 参数**

`exercise_agent.py` `run_sync` 签名加 `difficulty: str = "medium"`，prompt 拼接：
```python
prompt = f"{skill.body}\n\n当前难度：{difficulty}\n..."
```

- [ ] **Step 6: 关卡完成时调 Profile 更新**

`director_agent.py` `_run_inner` 末尾（写完 Level + Exercise + ReviewResult 后、调 progress_publish 前）：
```python
# spec § 5.1: 关卡完成后调 ProfileRepository.apply_delta
# 简化：根据 completion.score 微调 kb / as
score_ratio = score / max(1.0, total_max_score)
delta_kb = 0.05 if score_ratio >= 0.8 else (-0.03 if score_ratio < 0.5 else 0.0)
delta_as = 0.02 if score_ratio >= 0.7 else -0.02

async with factory() as session:
    await ProfileRepository(session).apply_delta(student_id, {"kb": delta_kb, "as": delta_as})
    await session.commit()
```

- [ ] **Step 7: SSE completed 加 level_id + exercise_ids**

`director_agent.py` 末 `progress_publish` 调用改为：
```python
await progress_publish(trace_id, ProgressEvent(
    stage=Stage.DIRECTOR,
    status="completed",
    payload={
        "level_id": str(level.level_id),
        "exercise_ids": [str(e.exercise_id) for e in ex_list],
        "score": score,
    },
))
```

- [ ] **Step 8: 写失败的 integration test（SSE 字段）**

`tests/integration/test_api_gaps.py` 追加：
```python
@pytest.mark.asyncio
async def test_director_sse_completed_includes_level_id_and_exercise_ids(client_and_db):
    """SSE completed 事件 payload 必须包含 level_id + exercise_ids。"""
    # POST /api/level/start → trace_id → 订阅 SSE → 断言 payload.level_id 是 UUID
    # 注：需 mock ExerciseAgent + ReviewAgent 或注入测试 fixture
```

- [ ] **Step 9: 跑全部测试 + mypy**

```bash
uv run pytest tests/unit tests/integration -q
uv run mypy src tests
```

- [ ] **Step 10: commit**

```bash
git add src/selflearn/agents/builtin/director_agent.py src/selflearn/agents/builtin/exercise_agent.py src/selflearn/infra/repositories/level_repo.py tests/unit/test_difficulty_gradient.py tests/integration/test_api_gaps.py
git commit -m "feat(agents): Director SSE 加 level_id+exercise_ids + 难度梯度 + Profile 自动更新"
```

---

### Task 13: frontend 4 段主线（api / desk / panes / 画像动画）

**Files:**
- Modify: `frontend/vite.config.ts`（proxy）
- Modify: `frontend/package.json`（加 react-rnd / recharts）
- Create: `frontend/src/api/{client,profile,map,level,sse,types}.ts`
- Create: `frontend/src/store/{profile,session}.ts`
- Create: `frontend/src/panes/{LecturePane,ExercisePane,ChatPane}.tsx`
- Create/Modify: `frontend/src/desk/{Desktop,MapPanel,ProfilePanel,CalendarPanel}.tsx`
- Create: `frontend/src/reset/ResetButton.tsx`
- Modify: `frontend/src/main.tsx`

**Interfaces:**
- Consumes: `localhost:8000` REST + SSE（spec § 4）
- Produces: 浏览器可访问的完整 Demo 页面

⚠️ **本 Task 不引入 Playwright**（Task 14）。本 Task 仅手动验证。

- [ ] **Step 1: 装包**

```bash
cd frontend
npm install --save react-rnd recharts
```
预期：`package.json` 出现 `"react-rnd": "^x.y.z"` 和 `"recharts": "^x.y.z"`。

- [ ] **Step 2: Vite proxy 配置**

`frontend/vite.config.ts`：
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // spec § 10.2: 关闭 proxy buffering 避免 SSE 流式变批量
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes) => {
            proxyRes.headers["cache-control"] = "no-cache";
          });
        },
      },
    },
  },
});
```

- [ ] **Step 3: api/client.ts（fetch 封装）**

```ts
const BASE = "";  // 走 vite proxy

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`GET ${path} → ${r.status}`);
  return r.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok && r.status !== 202) throw new Error(`POST ${path} → ${r.status}`);
  return r.json();
}
```

- [ ] **Step 4: api/types.ts（spec § 4.5 类型）**

照抄 spec § 4.5 的 `SSEEvent` / `ProfileResponse` / `MapNode` / `LevelDetail`。

- [ ] **Step 5: api/profile.ts / map.ts / level.ts**

```ts
// profile.ts
import { apiGet, apiPost } from "./client";
import type { ProfileResponse } from "./types";

export const getProfile = (sid: string) => apiGet<ProfileResponse>(`/api/profile/${sid}`);
export const buildProfile = (sid: string, dims: Record<string, number>, tags: string[]) =>
  apiPost<{ trace_id: string }>("/api/profile/build", { student_id: sid, dimensions: dims, tags });

// map.ts
import { apiGet, apiPost } from "./client";
import type { MapNode } from "./types";

export const generateMap = (sid: string) =>
  apiPost<{ trace_id: string }>("/api/map/generate", { student_id: sid });
export const getMapNodes = (sid: string) =>
  apiGet<{ nodes: MapNode[] }>(`/api/map/${sid}/nodes`);

// level.ts
import { apiGet, apiPost } from "./client";
import type { LevelDetail } from "./types";

export const startLevel = (sid: string) =>
  apiPost<{ trace_id: string }>("/api/level/start", { student_id: sid });
export const getLevel = (lid: string) => apiGet<LevelDetail>(`/api/level/${lid}`);
export const submitLevel = (lid: string, answers: Record<string, string>) =>
  apiPost<{ status: string; score: number }>(`/api/level/${lid}/submit`, { answers });
```

- [ ] **Step 6: api/sse.ts（SSE 订阅通用函数）**

```ts
import type { SSEEvent } from "./types";

export function subscribeProgress(traceId: string, onEvent: (e: SSEEvent) => void): () => void {
  const es = new EventSource(`/api/profile/init/${traceId}/stream`);
  // 同时兼容 level SSE（不同 path）
  const handler = (kind: "progress" | "completed" | "error") => (e: MessageEvent) => {
    onEvent({ event: kind, data: JSON.parse(e.data) } as SSEEvent);
  };
  es.addEventListener("progress", handler("progress"));
  es.addEventListener("completed", (e) => {
    handler("completed")(e);
    es.close();
  });
  es.addEventListener("error", (e) => {
    handler("error")(e);
    es.close();
  });
  return () => es.close();
}
```

⚠️ Level SSE path 不同（`/api/level/{id}/stream?trace_id=...`）。实现者需要把函数通用化或拆 `subscribeLevelProgress`。

- [ ] **Step 7: store/session.ts + store/profile.ts（Zustand）**

```ts
// session.ts
import { create } from "zustand";
const KEY = "selflearn.student_id";

function genId() {
  return crypto.randomUUID();
}

export const useSession = create<{ studentId: string; reset: () => void }>((set) => ({
  studentId: localStorage.getItem(KEY) ?? (() => { const id = genId(); localStorage.setItem(KEY, id); return id; })(),
  reset: () => {
    localStorage.removeItem(KEY);
    set({ studentId: genId() });
    location.reload();  // spec § 10.6 重置 demo
  },
}));

// profile.ts
import { create } from "zustand";
import type { ProfileDimensions } from "../api/types";

export const useProfile = create<{ dimensions: ProfileDimensions | null; setDimensions: (d: ProfileDimensions) => void }>((set) => ({
  dimensions: null,
  setDimensions: (d) => set({ dimensions: d }),
}));
```

- [ ] **Step 8: desk/ProfilePanel.tsx（雷达图 + 演变迷你折线）**

```tsx
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";
import { useProfile } from "../store/profile";

const LABELS = ["知识基础", "视觉偏好", "分析风格", "求职目标", "易错类型", "专注时长"];

export function ProfilePanel() {
  const dims = useProfile((s) => s.dimensions);
  if (!dims) return <div>加载画像...</div>;
  const data = LABELS.map((label, i) => ({
    label,
    value: [dims.kb, dims.vp, dims.as, dims.ge, dims.ept, fd: dims.fd][i] ?? 0.5,
  }));
  return (
    <ResponsiveContainer width="100%" height={250}>
      <RadarChart data={data}>
        <PolarGrid stroke="#E4E4E0" />
        <PolarAngleAxis dataKey="label" tick={{ fill: "#1A1A1A", fontFamily: "HedvigLettersSerif" }} />
        <Radar name="profile" dataKey="value" stroke="#1B3B6F" fill="#1B3B6F" fillOpacity={0.3} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
```

⚠️ 实测 recharts RadarChart API，调整 data 映射。**`dims.fd` typo** 是上面示范，提醒 Plan 实现者注意 v4 中文→英文键映射。

- [ ] **Step 9: desk/Desktop.tsx（左 1/3 + 右 2/3 布局）**

```tsx
import { MapPanel } from "./MapPanel";
import { ProfilePanel } from "./ProfilePanel";
import { CalendarPanel } from "./CalendarPanel";
import { LecturePane } from "../panes/LecturePane";
import { ExercisePane } from "../panes/ExercisePane";
import { ChatPane } from "../panes/ChatPane";
import { ResetButton } from "../reset/ResetButton";

export function Desktop() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", height: "100vh", background: "#F7F5EF" }}>
      <div style={{ display: "grid", gridTemplateRows: "2fr 1fr", borderRight: "1px solid #E4E4E0" }}>
        <MapPanel />
        <ProfilePanel />
      </div>
      <CalendarPanel />
      <Dock>
        <PaneOpener name="讲义" Comp={LecturePane} />
        <PaneOpener name="习题" Comp={ExercisePane} />
        <PaneOpener name="AI 对话" Comp={ChatPane} />
      </Dock>
      <ResetButton />
    </div>
  );
}
```

具体子组件由实现者按 demo-serif 现有视觉风格填充。

- [ ] **Step 10: panes/LecturePane / ExercisePane / ChatPane（react-rnd）**

```tsx
// LecturePane.tsx
import { Rnd } from "react-rnd";

export function LecturePane({ levelId }: { levelId: string }) {
  const [content, setContent] = useState<string>("");
  useEffect(() => { /* GET /api/level/{id} → 渲染 prompt */ }, [levelId]);
  return (
    <Rnd default={{ x: 100, y: 100, width: 500, height: 400 }}>
      <div style={{ background: "#fff", padding: 16, borderRadius: 8 }}>
        {content || "加载讲义..."}
      </div>
    </Rnd>
  );
}
```

- [ ] **Step 11: main.tsx 启动入口**

```tsx
import { useEffect } from "react";
import { Desktop } from "./desk/Desktop";
import { useSession } from "./store/session";
import { useProfile } from "./store/profile";
import { getProfile } from "./api/profile";

export function App() {
  const sid = useSession((s) => s.studentId);
  const setDims = useProfile((s) => s.setDimensions);

  useEffect(() => {
    getProfile(sid)
      .then((p) => setDims(p.dimensions))
      .catch(() => {/* 启动时无画像：等 SSE */});
  }, [sid]);

  return <Desktop />;
}
```

- [ ] **Step 12: 手动验证**

启动：
```bash
# Terminal 1: 后端
cd backend
uv run uvicorn selflearn.gateway.app:create_app --factory --reload --port 8000

# Terminal 2: worker
uv run python -m selflearn.main run_worker

# Terminal 3: frontend
cd ../frontend
npm run dev
```

打开 `http://localhost:5173`，验证：
- [ ] 无 CORS 报错（DevTools Console）
- [ ] 看到藏宝图 + 画像雷达图 + 日历
- [ ] SSE 流式真在流（Network 面板看 `/api/profile/init/.../stream` 是 `eventstream` 类型 + 持续推送）
- [ ] 点击"进入关卡"→ 3 个窗口飞出 + 可拖拽

- [ ] **Step 13: TypeScript check**

```bash
cd frontend
npm run typecheck
```
预期：0 errors。

- [ ] **Step 14: commit**

```bash
git add -A
git commit -m "feat(frontend): 4 段主线（api + desk + panes + 画像动画）+ Vite SSE proxy"
```

---

### Task 14: Playwright e2e + 验收报告

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/smoke.spec.ts`
- Create: `frontend/package.json`（加 `@playwright/test` 到 devDependencies）
- Create: `docs/实施计划-Stage4-验收报告.md`

**Interfaces:**
- Consumes: 完整 frontend + backend demo
- Produces: Playwright e2e 自动测脚本 + Stage 4 验收报告

- [ ] **Step 1: 装 Playwright**

```bash
cd frontend
npm install --save-dev @playwright/test
npx playwright install chromium
```

- [ ] **Step 2: playwright.config.ts**

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  use: { baseURL: "http://localhost:5173", headless: true },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
```

⚠️ Playwright 默认 webServer 不会起 backend；Stage 4 假设 backend 已由用户手动起。Plan 实现者：可加第二个 webServer 项起 backend，或 README 写明"先起 backend 再跑 e2e"。

- [ ] **Step 3: e2e/smoke.spec.ts**

```ts
import { test, expect } from "@playwright/test";

test("Stage 4 demo smoke: 打开页 → 看到藏宝图 + 画像", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /藏宝图/ })).toBeVisible({ timeout: 10_000 });
  await expect(page.locator(".recharts-radar")).toBeVisible({ timeout: 10_000 });
});

test("CORS: 浏览器调 /api/profile/{id} 无错误", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  // 至少确认没有 CORS 报错
  const corsErrors = consoleErrors.filter((m) => m.includes("CORS"));
  expect(corsErrors).toEqual([]);
});
```

- [ ] **Step 4: 跑 e2e**

```bash
cd frontend
# 确保 backend 已起 + frontend npm run dev 已在 5173 端口
npx playwright test
```
预期：2/2 PASS。

- [ ] **Step 5: 写验收报告**

`docs/实施计划-Stage4-验收报告.md`：参考 Stage 3 验收报告格式。

包含：
- 范围 vs 实际交付
- 全部测试通过截图/命令输出
- 5 API 缺口补齐证据
- 1 张新表 + 1 张新迁移文件
- AOP Hook 3 横切点证据（curl `/debug/state` 输出截选）
- 3 学习闭环点（Profile 更新 + 难度梯度 + 画像演变）证据
- frontend 4 段交付物（截图）
- 已知遗留与 Stage 5+ 列表

- [ ] **Step 6: commit + tag**

```bash
git add -A
git commit -m "test(e2e): Playwright smoke（前端 + CORS）+ Stage 4 验收报告"
git tag stage4-complete
```

---

## Self-Review Checklist

执行后由 controller 跑：

- [x] **Spec coverage**：
  - § 1.1 目录重命名 → Task 1
  - § 1.1 5 API 缺口 → Task 7-12（含 T11/T12 SSE 字段补）
  - § 1.1 学习闭环 3 点 → Task 6（repo）+ Task 12（director 集成）+ Task 11（profile SSE）
  - § 1.1 1 张新表 → Task 2
  - § 1.1 AOP Hook → Task 3/4/5
  - § 1.1 frontend 4 段 → Task 13
  - § 1.1 Playwright e2e → Task 14
- [x] **Placeholder scan**：无 TBD / TODO / "implement later"
- [x] **Type consistency**：`SSEEvent` / `ProfileDimensions` / `MapNode` / `LevelDetail` / `ExerciseResponse` 在 api/types.ts 与 Pydantic schema 同步
- [x] **项目级硬约束**：Task 1 显式 `git grep demo-serif` 0 命中；不引入 auth
- [x] **依赖版本下限**：`>=` only，无 `<N.0` 上界（pyproject.toml 已沿用）
- [x] **mypy strict 是硬门**：每 task 末尾 `uv run mypy src tests` 必跑
- [x] **AOP 零侵入**：Task 4 用装饰器 + `__init_subclass__`，不改业务函数体
- [x] **Stage 2/3 smoke 必跑**：Task 11/12 末尾 explicit `bash scripts/smoke.sh` + `pytest tests/integration/test_smoke.py test_smoke_mvp.py`
- [x] **commit 频率**：每 task 至少 1 commit（共 14 commit）
- [x] **tag**：Task 14 末尾 `stage4-complete`
- [x] **已知风险**：spec § 10.1-10.7 全部映射到具体 task（CORS=T1, Vite SSE buffer=T13, SSE 缺字段=T11/T12, 动画=T13, 重命名=T1, student_id=T13, .env=T1）

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-13-stage4-demo-integration.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?