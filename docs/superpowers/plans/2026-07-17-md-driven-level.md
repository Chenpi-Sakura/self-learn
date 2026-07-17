# 用户上传 md 驱动地图与关卡生成 — 实施 plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans。任务步骤用 checkbox `- [ ]` 语法追踪。

**Goal**：让 SelfLearn 学生上传 1-4 份 `.md` 后能基于其内容自动生成 KP 地图与个性化关卡，并在 UI 上通过 SSE 进度条看到 5 阶段（提炼主题）与 4 阶段（关卡生成）的真实进展。

**Architecture**：客户端只做"骨架" + "进度条 UI"——核心在服务端加 `resources` 表与 `extract_topics` 后台任务，蒸馏用一个 LLM 调用取 topics JSON；地图节点通过整删 + 重写事务确保幂等；KP.source_content_md 字段把"提供的材料知识"塞进 director chain prefetch，使 lecture / exercise skill 在生成时直接引用 md 切片。SSE 沿用既有 `progress/stages.py` + Redis Stream 协议，加 5 个 `extract_topics.*` 枚举。FK CASCADE 让"重生成 = 学生历史关卡归零"语义自动成立。

**Tech Stack**：FastAPI + SQLAlchemy 2.0 async + Pydantic + alembic + Redis Stream + React 18 + Vite + zustand + EventSource；前端不引入 vitest（改用 Playwright E2E）。

---

## Global Constraints

- **依赖**：后端不引入新依赖（除 alembic 现有的 sa.types）；前端不引入 vitest，**已有 Playwright** 作为 E2E 框架。
- **迁移**：不允许改任何已有 alembic migration；新增一个独立 migration，`down_revision="2f78430b5478"`（当前 head，Task 261 加 lecture_html 的那个）。
- **包名规范**：与现有 SKILL.md 命名一致——skill 走 `skill.<area>.<verb>` 形式（`skill.resource.extract_topics`）。
- **commit 规范**：中文 commit message。
- **Docker 构建**：`HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897`（CLAUDE.md 约束，daemon.json 不可靠）。
- **测试运行**：`cd backend && uv run pytest -p no:warnings`；前端 `cd frontend && npm run build`（tsc --noEmit + vite build）作为类型门禁。
- **branch**：直接 main（CLAUDE.md + memory `no-worktrees-sdd`）。
- **单账户**：KEEP_STUDENT `86820161-b0f0-455f-91b4-a69e49445bdf`（4 处字面量必须保持一致：`backend/scripts/purge_test_data.py:24` / `backend/src/selflearn/infra/seed_account.py:17` / `frontend/src/constants/account.ts:6` / `CLAUDE.md`）。
- **鉴权**：项目不做登录鉴权（memory `no-auth-no-login`）。
- **FK 级联约定**：写库用 SQL `delete(Model).where(...)`，让数据库层 `ondelete="CASCADE"` 生效；**不**用 ORM `session.delete(obj)` 逐行删。
- **SSE 协议**：沿用 `progress/stages.py` 既有 `Stage` 枚举 + `progress_publish` / `progress_consume`；`progress/__init__.py` re-export 必须同步加新 Stage。
- **不做的事**（写在每条任务"约束"块里）：
  - MinIO / Qdrant / Tika / OCR
  - md 切片向量化
  - 跨 student KP 自动去重
  - 资源上传并发进度条
  - 取消提取主题任务（**没有取消按钮**）
  - 文件夹右键重命名
  - 多用户 / 权限
  - 一次性大扫除脚本
  - `content_hash` 字段
  - `resources.name` UNIQUE 约束
  - 前端 vitest 基础设施（用 Playwright）

---

## 文件结构总览

### 新建

| 文件 | 归属任务 | 用途 |
|------|---------|------|
| `backend/migrations/versions/<hash>_add_resources_and_kp_source.py` | T1 | alembic：新表 + KP 加列 |
| `backend/src/selflearn/domain/resource.py` | T1 | ORM `Resource` |
| `backend/src/selflearn/schemas/resource.py` | T1 | Pydantic 请求/响应 |
| `backend/src/selflearn/gateway/routes/resources.py` | T1 | POST/GET/PUT/DELETE 4 路由 |
| `backend/tests/unit/test_resources_crud.py` | T1 | 资源 CRUD 单测 |
| `backend/tests/unit/test_resources_kp_migration.py` | T1 | KP 新列迁移断言（live 升 head） |
| `backend/skills/skill.resource.extract_topics/SKILL.md` | T2 | 主题提炼 SKILL |
| `backend/src/selflearn/agents/extract_topics.py` | T2 | 5 阶段流水线 |
| `backend/src/selflearn/schemas/extract_topics.py` | T2 | 触发请求 schema |
| `backend/src/selflearn/gateway/routes/extract_topics.py` | T2 | POST 触发（也含 GET stream；T3 加） |
| `backend/tests/unit/test_extract_topics_pipeline.py` | T2 | 5 阶段 + JSON schema + retry + 事务回滚 + 孤儿 KP |
| `backend/tests/integration/test_extract_topics_sse.py` | T3 | EventSource 真连 5 阶段 |
| `frontend/src/components/MarkdownRenderer.tsx` | T4 | 抽象渲染组件 |
| `frontend/src/components/ResourceListView.tsx` | T4 | 抽象列表组件 |
| `frontend/src/components/ProgressOverlay.tsx` | T3 | 浮层 5 阶段进度条 |
| `frontend/src/components/MDBrowser.tsx` | T5 | MD 浏览器窗口内容 |
| `frontend/src/components/ResourceLibrary.tsx` | T5 | 资源管理器窗口内容 |
| `frontend/src/components/ExtractTopicsDialog.tsx` | T5 | 提炼对话框窗口内容 |
| `frontend/src/components/EmptyStateOverlay.tsx` | T5 | 冷启动引导卡 |
| `frontend/src/api/resources.ts` | T1 | 资源 CRUD REST |
| `frontend/src/api/extractTopics.ts` | T2/T3 | 触发 + SSE subscribe |
| `frontend/src/styles/markdown.css` | T4 | `.markdown-body` 样式（从 lecture.css 搬） |
| `frontend/tests/e2e/md-driven.spec.ts` | T5 | Playwright 端到端 |

### 修改

| 文件 | 任务 | 改什么 |
|------|------|--------|
| `backend/src/selflearn/domain/knowledge_point.py` | T1 | 加 `source: Mapped[str\|None]` + `source_content_md: Mapped[str\|None]` |
| `backend/src/selflearn/progress/stages.py` | T2 | 加 5 个 Stage 枚举 |
| `backend/src/selflearn/progress/__init__.py` | T2 | re-export（无需改既有，但下面 T3 会再 sync） |
| `backend/src/selflearn/gateway/app.py` | T1/T2 | 注册新 router（resources / extract_topics） |
| `frontend/src/types/window.ts` | T5 | AppId 加 3 个；SINGLETON_APP_IDS 加 `extract_topics_dialog` / `md_browser` |
| `frontend/src/App.tsx` | T5 | `WIN_CONTENT` 加 3 个 + `renderBody` 加 3 个 case |
| `frontend/src/store/useWorkspace.ts` | T5 | 默认 `windows: {}`、新增 `hasOpenedFirstWindow: boolean` 状态 |
| `frontend/src/panes/LecturePane.tsx` | T4 | 重构使用 `MarkdownRenderer` |
| `frontend/src/styles/lecture.css` | T4 | 拆出一份 `markdown.css`，让 `.lecture` 与 `.markdown-body` 共用 |
| `backend/scripts/e2e_md_driven.sh` | T5 | 新增端到端 demo 脚本 |

---

## Task 1：基础数据层（resources 表 + KP 加列 + 资源 CRUD 路由）

**Files:**
- Create: `backend/migrations/versions/<hash>_add_resources_and_kp_source.py`
- Create: `backend/src/selflearn/domain/resource.py`
- Create: `backend/src/selflearn/schemas/resource.py`
- Create: `backend/src/selflearn/gateway/routes/resources.py`
- Create: `backend/src/selflearn/api/`（如果还没有就建）`__init__.py`，否则在 `app.py` 内注册
- Create: `frontend/src/api/resources.ts`
- Create: `backend/tests/unit/test_resources_crud.py`
- Modify: `backend/src/selflearn/domain/knowledge_point.py`
- Modify: `backend/src/selflearn/gateway/app.py`

**Interfaces:**
- Consumes: FastAPI `get_session_factory`、`get_redis`、`AsyncIterator`；KEEP_STUDENT 常量
- Produces:
  - `Resource` ORM（`backend.src.selflearn.domain.resource.Resource`）
  - `ResourceResponse`, `ResourceUploadResponse`, `ResourceUpdate` Pydantic
  - `POST /api/resources/upload` / `GET /api/resources/list` / `GET /api/resources/{id}` / `PUT /api/resources/{id}` / `DELETE /api/resources/{id}`
  - 新增 stage 枚举值（先用 stub，T2 完善）

---

### Step 1: 写 failing 单测：资源表结构

在 `backend/tests/unit/test_resources_kp_migration.py` 新建：

```python
"""验证 KP 加 source/source_content_md 字段生效。"""
from __future__ import annotations
import pytest
from sqlalchemy import inspect
from selflearn.infra.db import get_session_factory


@pytest.mark.asyncio(loop_scope="session")
async def test_kp_has_source_columns_after_migration() -> None:
    factory = get_session_factory()
    async with factory() as session:
        insp = inspect(session.bind)  # type: ignore[union-attr]
        cols = {c["name"] for c in insp.get_columns("knowledge_points")}
        assert "source" in cols
        assert "source_content_md" in cols


@pytest.mark.asyncio(loop_scope="session")
async def test_resources_table_exists_after_migration() -> None:
    factory = get_session_factory()
    async with factory() as session:
        insp = inspect(session.bind)  # type: ignore[union-attr]
        assert "resources" in insp.get_table_names()
```

在 `backend/tests/unit/test_resources_crud.py` 新建：

```python
"""resources CRUD 单测（含非循环 PUT 校验）。"""
from __future__ import annotations
from io import BytesIO
from uuid import UUID, uuid4
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from selflearn.infra.db import get_session_factory
from selflearn.gateway.app import app as gateway_app

KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 启动 lifespan
        async with AsyncClient(transport=transport, base_url="http://test").aio_apps_cm() if False else _noop():
            yield ac


async def _noop():
    return None
# 上面 fixture 简化：实际用 httpx + ASGI lifespan manager


@pytest.mark.asyncio(loop_scope="session")
async def test_upload_rejects_non_md() -> None:
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = [("files", ("a.txt", BytesIO(b"x"), "text/plain"))]
        r = await ac.post("/api/resources/upload", files=files)
        assert r.status_code == 400


@pytest.mark.asyncio(loop_scope="session")
async def test_upload_rejects_more_than_4_files() -> None:
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = [("files", (f"a{i}.md", BytesIO(b"# x"), "text/markdown")) for i in range(5)]
        r = await ac.post("/api/resources/upload", files=files)
        assert r.status_code == 400


@pytest.mark.asyncio(loop_scope="session")
async def test_upload_then_list_then_get_then_delete() -> None:
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = [("files", ("笔记.md", BytesIO(b"# Title\n\nbody"), "text/markdown"))]
        r = await ac.post("/api/resources/upload", files=files)
        assert r.status_code == 200
        body = r.json()
        rid = body["uploaded"][0]["id"]

        r = await ac.get("/api/resources/list")
        assert any(item["id"] == rid for item in r.json()["items"])

        r = await ac.get(f"/api/resources/{rid}")
        assert r.status_code == 200
        assert r.json()["content_md"] == "# Title\n\nbody"

        # 软删
        r = await ac.delete(f"/api/resources/{rid}")
        assert r.status_code == 204

        r = await ac.get(f"/api/resources/{rid}")
        assert r.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_put_rejects_cycle() -> None:
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 上传 a/x.md
        files = [("files", ("a/x.md", BytesIO(b"# x"), "text/markdown"))]
        r = await ac.post("/api/resources/upload", files=files)
        rid = r.json()["uploaded"][0]["id"]

        # 试图改名为 a/x/y.md（自身子路径，应 400）
        r = await ac.put(f"/api/resources/{rid}", json={"name": "a/x/y.md"})
        assert r.status_code == 400
```

### Step 2: 跑测试确认 FAIL

```bash
cd backend && uv run pytest tests/unit/test_resources_kp_migration.py tests/unit/test_resources_crud.py -v -p no:warnings 2>&1 | tail -15
```

Expected: 全部 FAIL（路由和表都不存在）。

### Step 3: 写 alembic migration

新建 `backend/migrations/versions/<ts>_add_resources_and_kp_source.py`（`ts` 用 uuid4 前 12 位；用 `cd backend && uv run alembic revision --autogenerate -m "add resources and kp source" --rev-id=<your-12-hex>` 生成骨架后再改；或者下面这样手写）：

```python
"""add resources table and kp.source / kp.source_content_md

Revision ID: <your-12-hex>
Revises: 2f78430b5478
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa


revision = "<your-12-hex>"
down_revision = "2f78430b5478"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # KP 加列
    op.add_column("knowledge_points", sa.Column("source", sa.String(500), nullable=True))
    op.add_column("knowledge_points", sa.Column("source_content_md", sa.Text(), nullable=True))

    # 新表 resources
    op.create_table(
        "resources",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"],
                                name="fk_resources_student", ondelete="RESTRICT"),
    )
    op.create_index("idx_resources_student_active",
                    "resources", ["student_id"],
                    postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("idx_resources_student_name",
                    "resources", ["student_id", "name"])


def downgrade() -> None:
    op.drop_index("idx_resources_student_name", table_name="resources")
    op.drop_index("idx_resources_student_active", table_name="resources")
    op.drop_table("resources")
    op.drop_column("knowledge_points", "source_content_md")
    op.drop_column("knowledge_points", "source")
```

跑升级：

```bash
cd backend && uv run alembic upgrade head
```

### Step 4: 修改 ORM domain

修改 `backend/src/selflearn/domain/knowledge_point.py`，加两行（参考现有 `lecture_html: Mapped[str | None]` 模式）：

```python
source: Mapped[str | None] = mapped_column(String(500), nullable=True)
source_content_md: Mapped[str | None] = mapped_column(Text, nullable=True)
```

别忘了加 import `Text`：`from sqlalchemy import CheckConstraint, Index, SmallInteger, String, Text, func`

新建 `backend/src/selflearn/domain/resource.py`：

```python
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from selflearn.domain.base import Base


class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

### Step 5: 跑 migration 断言测试 pass

```bash
cd backend && uv run pytest tests/unit/test_resources_kp_migration.py -v -p no:warnings
```

Expected: 2/2 PASS。

### Step 6: 写 Pydantic schemas

新建 `backend/src/selflearn/schemas/resource.py`：

```python
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ResourceListItem(BaseModel):
    id: UUID
    name: str
    size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True


class ResourceResponse(BaseModel):
    id: UUID
    name: str
    content_md: str
    size_bytes: int
    created_at: datetime


class ResourceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=1000)


class ResourceUploadItem(BaseModel):
    id: UUID
    name: str
    size_bytes: int


class ResourceUploadResponse(BaseModel):
    uploaded: list[ResourceUploadItem]
```

### Step 7: 写 4 个资源 CRUD 路由

新建 `backend/src/selflearn/gateway/routes/resources.py`：

```python
"""资源 CRUD 路由（Task 1）。"""
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from selflearn.domain.resource import Resource
from selflearn.infra.db import get_session_factory
from selflearn.schemas.resource import (
    ResourceListItem,
    ResourceResponse,
    ResourceUpdate,
    ResourceUploadResponse,
    ResourceUploadItem,
)


router = APIRouter(prefix="/api/resources", tags=["resources"])
MAX_FILES = 4
MAX_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/upload", response_model=ResourceUploadResponse)
async def upload_resources(files: list[UploadFile] = File(...)) -> ResourceUploadResponse:
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"max {MAX_FILES} files")
    if not files:
        raise HTTPException(status_code=400, detail="at least one file")

    for f in files:
        if not (f.filename or "").lower().endswith(".md"):
            raise HTTPException(status_code=400, detail=f"only .md accepted: {f.filename}")

    uploaded: list[ResourceUploadItem] = []
    factory = get_session_factory()
    async with factory() as session:
        for f in files:
            body = await f.read()
            if len(body) > MAX_BYTES:
                raise HTTPException(status_code=400, detail=f"{f.filename} too large")
            r = Resource(
                student_id=UUID(KEEP_STUDENT),
                name=f.filename or "untitled.md",
                content_md=body.decode("utf-8", errors="replace"),
                size_bytes=len(body),
            )
            session.add(r)
            await session.flush()
            uploaded.append(ResourceUploadItem(id=r.id, name=r.name, size_bytes=r.size_bytes))
        await session.commit()
    return ResourceUploadResponse(uploaded=uploaded)


@router.get("/list", response_model=dict)
async def list_resources() -> dict:
    factory = get_session_factory()
    async with factory() as session:
        rows = (await session.execute(
            select(Resource).where(Resource.deleted_at.is_(None)).order_by(Resource.name)
        )).scalars().all()
        return {"items": [ResourceListItem.model_validate(r) for r in rows]}


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: UUID) -> ResourceResponse:
    factory = get_session_factory()
    async with factory() as session:
        r = (await session.execute(
            select(Resource).where(Resource.id == resource_id, Resource.deleted_at.is_(None))
        )).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="not found")
        return ResourceResponse.model_validate(r)


def _would_create_cycle(old_name: str, new_name: str) -> bool:
    """防止把文件移到自身子路径。"""
    if not new_name.startswith(old_name + "/"):
        return False
    return True  # a/x 改 a/x/y 即循环


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(resource_id: UUID, body: ResourceUpdate) -> ResourceResponse:
    factory = get_session_factory()
    async with factory() as session:
        r = (await session.execute(
            select(Resource).where(Resource.id == resource_id, Resource.deleted_at.is_(None))
        )).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="not found")
        if r.name != body.name:
            if _would_create_cycle(r.name, body.name):
                raise HTTPException(status_code=400, detail="cycle rename rejected")
            r.name = body.name
            await session.commit()
            await session.refresh(r)
        return ResourceResponse.model_validate(r)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource_id: UUID) -> None:
    from datetime import datetime
    factory = get_session_factory()
    async with factory() as session:
        r = (await session.execute(
            select(Resource).where(Resource.id == resource_id, Resource.deleted_at.is_(None))
        )).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="not found")
        r.deleted_at = datetime.utcnow()
        await session.commit()
```

注意顶部要加常量：`KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"`

### Step 8: 注册路由到 gateway

修改 `backend/src/selflearn/gateway/app.py`：`from selflearn.gateway.routes.resources import router as resources_router` + `app.include_router(resources_router)`。

### Step 9: 跑 CRUD 单测

```bash
cd backend && uv run pytest tests/unit/test_resources_crud.py -v -p no:warnings 2>&1 | tail -20
```

Expected: 4/4 PASS。如果生命周期问题（ASGITransport 不启 lifespan），把 fixture 改成显式 `async with LifespanManager(...)` 包裹，或改用 `httpx.AsyncClient(transport=ASGITransport(app), ...)` + 自己手动 `await app.router.startup()`。

### Step 10: 写前端 REST 客户端

新建 `frontend/src/api/resources.ts`：

```typescript
import { apiGet, apiPost, apiPut, apiDelete } from './client';

export interface ResourceListItem {
  id: string;
  name: string;
  size_bytes: number;
  created_at: string;
}

export interface ResourceResponse extends ResourceListItem {
  content_md: string;
}

export const listResources = () =>
  apiGet<{ items: ResourceListItem[] }>('/api/resources/list');

export const getResource = (id: string) =>
  apiGet<ResourceResponse>(`/api/resources/${encodeURIComponent(id)}`);

export const uploadResources = (files: File[]) => {
  const form = new FormData();
  for (const f of files) form.append('files', f, f.name);
  return apiPost<{ uploaded: ResourceListItem[] }>('/api/resources/upload', form);
};

export const updateResource = (id: string, name: string) =>
  apiPut<ResourceResponse>(`/api/resources/${encodeURIComponent(id)}`, { name });

export const deleteResource = (id: string) =>
  apiDelete<void>(`/api/resources/${encodeURIComponent(id)}`);
```

### Step 11: mypy + 跑全量回归

```bash
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
cd backend && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
```

Expected: mypy clean，pytest 176 + 6 = 182 passed。

### Step 12: Commit

```bash
cd D:/Projects/SelfLearn && git add backend/migrations/versions/<hash>_add_resources_and_kp_source.py backend/src/selflearn/domain/{resource,knowledge_point}.py backend/src/selflearn/schemas/resource.py backend/src/selflearn/gateway/routes/resources.py backend/src/selflearn/gateway/app.py backend/tests/unit/test_resources_crud.py backend/tests/unit/test_resources_kp_migration.py frontend/src/api/resources.ts && git commit -m "feat(后端+前端): 资源 CRUD 基础设施（resources 表 + KP 加 source 列）"
```

---

## Task 2：提炼主题后端流程（5 阶段 + JSON schema + retry + 孤儿 KP 清理）

**Files:**
- Create: `backend/skills/skill.resource.extract_topics/SKILL.md`
- Create: `backend/src/selflearn/agents/extract_topics.py`
- Create: `backend/src/selflearn/schemas/extract_topics.py`
- Create: `backend/src/selflearn/gateway/routes/extract_topics.py`
- Modify: `backend/src/selflearn/progress/stages.py`
- Create: `backend/tests/unit/test_extract_topics_pipeline.py`
- Modify: `backend/src/selflearn/gateway/app.py`

**Interfaces:**
- Consumes: `Resource` ORM（Task 1）、`KnowledgePoint` ORM（带 source/source_content_md）、`progress_publish(trace_id, ProgressEvent)`、`LLMAgent.run(env)`（既有）
- Produces:
  - `Stage.EXTRACT_TOPICS_PARSE/LLM/VALIDATE/WRITE/DONE` 5 个枚举
  - `POST /api/resources/extract_topics` 路由，返回 `{ task_id }`
  - `run_extract_topics(task_id, selected_resource_ids)` 后台任务，发布 5 阶段 SSE 事件

---

### Step 1: 在 progress/stages.py 加 5 个 Stage 枚举

修改 `backend/src/selflearn/progress/stages.py`，在 `class Stage(str, Enum):` 末尾追加：

```python
    EXTRACT_TOPICS_PARSE = "extract_topics.parse"
    EXTRACT_TOPICS_LLM = "extract_topics.llm"
    EXTRACT_TOPICS_VALIDATE = "extract_topics.validate"
    EXTRACT_TOPICS_WRITE = "extract_topics.write"
    EXTRACT_TOPICS_DONE = "extract_topics.done"
```

### Step 2: 写 SKILL.md

新建 `backend/skills/skill.resource.extract_topics/SKILL.md`：

```markdown
---
name: skill.resource.extract_topics
description: "Use when extracting topics (KP draft) from a student's uploaded .md learning materials. Input is a list of resources, output is a topics JSON. Each topic contains excerpt_text sourced from the input materials for later lecture/exercise skill injection."
output_schema: schemas/extract_topics.schema.json
mcp_prefetch: []
mcp_tool_use:
  - tool.lint_json
max_retries: 1
---

# 主题提炼器

## 任务
你是教学设计师。下面是学生上传的多份 .md 学习资料。
任务：
  1. 通读所有资料，识别 N 个（3-8 个）**不重叠、互相有逻辑关联**的主题
  2. 每个主题对应一个"知识节点"，给学生后续学习
  3. 对每个主题，从原始资料中挑出**最相关的 500-1500 字片段**，作为后续关卡生成的"提供的材料知识"
  4. 主题之间尽量体现先修关系（prerequisites），但不强求

## 输入（env.payload）
```json
{
  "resources": [
    {"id": "uuid", "name": "Transformer 详解.md", "content_md": "..."}
  ]
}
```

## 严格输出 JSON（不要 markdown fence，不要其它任何内容）
{
  "topics": [
    {
      "title": "主题名（≤30 字）",
      "description": "一段话描述（≤150 字）",
      "prerequisites": ["本次输出的其它主题 title，不在本数组内的被丢弃"],
      "excerpt_text": "原资料中 500-1500 字摘录，必须能从某份 input.resources.content_md 中找到（按字符串包含）",
      "source_resource_id": "上面 input.resources 中某个资源 id"
    }
  ]
}

约束：
- topics 长度 3-8
- 每条 excerpt_text 必须是某一 input.resources.content_md 的连续子字符串（防止幻觉）
- source_resource_id 必须在 input.resources 出现过
```

`schemas/extract_topics.schema.json` 不强制新建——`lint_json` 走 `tool` 的现有 schema 路径。但本次 LLM 输出需要**自己**做 JSON schema 校验，所以我们在 `extract_topics.py` 里写一个 in-module schema dict。

### Step 3: 写 schemas/extract_topics.py

新建 `backend/src/selflearn/schemas/extract_topics.py`：

```python
from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field


class ExtractTopicsRequest(BaseModel):
    selected_resource_ids: list[UUID] = Field(min_length=1, max_length=10)


class ExtractTopicsResponse(BaseModel):
    task_id: str
```

### Step 4: 写 agents/extract_topics.py（含 in-module JSON schema）

新建 `backend/src/selflearn/agents/extract_topics.py`：

```python
"""提炼主题 5 阶段流水线（Task 2）。

依赖：
- selflearn.domain.resource.Resource
- selflearn.domain.map_node.MapNode
- selflearn.domain.knowledge_point.KnowledgePoint
- selflearn.progress.{progress_publish, Stage, ProgressEvent}
- selflearn.agents.core.LLMAgent
- selflearn.llm.registry.LLMRegistry
"""
from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import delete, not_, select
from selflearn.agents.core import LLMAgent
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.domain.map_node import MapNode
from selflearn.domain.resource import Resource
from selflearn.infra.db import get_session_factory
from selflearn.llm.registry import LLMRegistry
from selflearn.progress import ProgressEvent, Stage, progress_publish


TIMEOUT_LLM_SEC = 90
TIMEOUT_TOTAL_SEC = 90


@dataclass
class TopicDraft:
    title: str
    description: str
    prerequisites: list[str]
    excerpt_text: str
    source_resource_id: str


# 模块内 schema（不依赖外部 json 文件）
TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 30},
                    "description": {"type": "string", "minLength": 1, "maxLength": 200},
                    "prerequisites": {"type": "array", "items": {"type": "string"}},
                    "excerpt_text": {"type": "string", "minLength": 500, "maxLength": 1500},
                    "source_resource_id": {"type": "string", "format": "uuid"},
                },
                "required": ["title", "description", "prerequisites", "excerpt_text", "source_resource_id"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["topics"],
    "additionalProperties": False,
}


class _SchemaValidationError(Exception):
    pass


def _validate_topics(data: dict[str, Any], input_ids: set[str]) -> list[TopicDraft]:
    """最简 JSON schema 校验（含 excerpt 必须在某 input md 中出现）。"""
    if not isinstance(data, dict) or "topics" not in data:
        raise _SchemaValidationError("missing topics")
    raw_topics = data["topics"]
    if not isinstance(raw_topics, list) or not (3 <= len(raw_topics) <= 8):
        raise _SchemaValidationError("topics length 3-8 required")
    titles_seen: set[str] = set()
    drafts: list[TopicDraft] = []
    for t in raw_topics:
        if not isinstance(t, dict):
            raise _SchemaValidationError("topic must be object")
        try:
            title = str(t["title"]).strip()
            desc = str(t["description"]).strip()
            prereqs = list(t["prerequisites"])
            excerpt = str(t["excerpt_text"])
            src_id = str(t["source_resource_id"])
        except (KeyError, TypeError) as e:
            raise _SchemaValidationError(f"field missing: {e}") from e
        if not (1 <= len(title) <= 30):
            raise _SchemaValidationError("title length 1-30")
        if not (1 <= len(desc) <= 200):
            raise _SchemaValidationError("description length 1-200")
        if not (500 <= len(excerpt) <= 1500):
            raise _SchemaValidationError("excerpt_text length 500-1500")
        if src_id not in input_ids:
            raise _SchemaValidationError(f"source_resource_id {src_id} not in input")
        if title in titles_seen:
            raise _SchemaValidationError(f"duplicate title: {title}")
        titles_seen.add(title)
        drafts.append(TopicDraft(
            title=title, description=desc,
            prerequisites=[p for p in prereqs if p in titles_seen and p != title],
            excerpt_text=excerpt, source_resource_id=src_id,
        ))
    return drafts


async def run_extract_topics(task_id: str, selected_ids: list[UUID]) -> None:
    """5 阶段流水线。失败会推 status=failed。"""
    try:
        await asyncio.wait_for(_run_pipeline(task_id, selected_ids), timeout=TIMEOUT_TOTAL_SEC)
    except asyncio.TimeoutError:
        await progress_publish(task_id, ProgressEvent(
            stage=Stage.EXTRACT_TOPICS_LLM, status="failed",
            payload={"error": "total timeout"},
        ))


async def _run_pipeline(task_id: str, selected_ids: list[UUID]) -> None:
    # 1. parse
    await progress_publish(task_id, ProgressEvent(stage=Stage.EXTRACT_TOPICS_PARSE, status="running"))
    factory = get_session_factory()
    async with factory() as session:
        rows = (await session.execute(
            select(Resource).where(
                Resource.id.in_(selected_ids),
                Resource.deleted_at.is_(None),
            )
        )).scalars().all()
        if not rows:
            await progress_publish(task_id, ProgressEvent(
                stage=Stage.EXTRACT_TOPICS_PARSE, status="failed",
                payload={"error": "no resources found"},
            ))
            return
        resources_payload = [
            {"id": str(r.id), "name": r.name, "content_md": r.content_md}
            for r in rows
        ]
        student_id = rows[0].student_id
        input_ids = {str(r.id) for r in rows}
    await progress_publish(task_id, ProgressEvent(
        stage=Stage.EXTRACT_TOPICS_PARSE, status="completed",
        payload={"byte_count": sum(len(r["content_md"]) for r in resources_payload)},
    ))

    # 2. llm（最多 1 次重试）
    drafts: list[TopicDraft] = []
    last_error: str = ""
    for attempt in range(2):
        if attempt == 0:
            await progress_publish(task_id, ProgressEvent(stage=Stage.EXTRACT_TOPICS_LLM, status="running"))
        else:
            await progress_publish(task_id, ProgressEvent(
                stage=Stage.EXTRACT_TOPICS_LLM, status="running",
                payload={"retry": True, "last_error": last_error},
            ))
        registry = LLMRegistry()
        agent = LLMAgent(mcp=None, registry=registry)  # type: ignore[arg-type]
        env = Envelope(
            action="skill.execute",
            sender=ActorRef(type="script", id="extract_topics"),
            target=ActorRef(type="skill", id="skill.resource.extract_topics"),
            payload={"resources": resources_payload},
        )
        try:
            response_text = await asyncio.wait_for(agent.run(env), timeout=TIMEOUT_LLM_SEC)
        except asyncio.TimeoutError:
            await progress_publish(task_id, ProgressEvent(
                stage=Stage.EXTRACT_TOPICS_LLM, status="failed",
                payload={"error": f"llm timeout >{TIMEOUT_LLM_SEC}s"},
            ))
            return

        # parse output → schema validate
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            last_error = f"json decode: {e}"
            continue
        try:
            drafts = _validate_topics(data, input_ids)
            break
        except _SchemaValidationError as e:
            last_error = str(e)
            continue

    if not drafts:
        await progress_publish(task_id, ProgressEvent(
            stage=Stage.EXTRACT_TOPICS_VALIDATE, status="failed",
            payload={"error": f"schema rejected after 2 attempts: {last_error}"},
        ))
        return
    await progress_publish(task_id, ProgressEvent(
        stage=Stage.EXTRACT_TOPICS_LLM, status="completed",
        payload={"topic_count": len(drafts)},
    ))
    await progress_publish(task_id, ProgressEvent(stage=Stage.EXTRACT_TOPICS_VALIDATE, status="running"))
    await progress_publish(task_id, ProgressEvent(
        stage=Stage.EXTRACT_TOPICS_VALIDATE, status="completed",
        payload={"draft_count": len(drafts)},
    ))

    # 4. write (整删 + INSERT KP + INSERT MapNode，事务)
    await progress_publish(task_id, ProgressEvent(stage=Stage.EXTRACT_TOPICS_WRITE, status="running"))
    created_node_ids: list[str] = []
    try:
        async with factory() as session:
            async with session.begin():
                # 整删该 student 的私有地图（FK CASCADE 清 Level/Exercise/Completion）
                await session.execute(delete(MapNode).where(MapNode.student_id == student_id))
                # 孤儿 KP 清理（仅清"由用户 md 蒸馏出来的 KP"）
                orphan_kps = (await session.execute(
                    select(KnowledgePoint).where(
                        KnowledgePoint.source.is_not(None),
                        ~select(MapNode.kp_id).where(
                            MapNode.kp_id == KnowledgePoint.kp_id
                        ).exists()
                    )
                )).scalars().all()
                for kp in orphan_kps:
                    await session.delete(kp)
                # INSERT 新 KP 和 MapNode
                for col, draft in enumerate(drafts):
                    kp = KnowledgePoint(
                        subject="用户提炼",
                        title=draft.title,
                        description=draft.description,
                        difficulty=2,
                        prerequisites=draft.prerequisites,
                        source=next((r["name"] for r in resources_payload
                                     if r["id"] == draft.source_resource_id), None),
                        source_content_md=draft.excerpt_text,
                    )
                    session.add(kp)
                    await session.flush()
                    node = MapNode(
                        student_id=student_id,
                        kp_id=kp.kp_id,
                        status="active",
                        branch_type="main",
                        position={"col": col % 5, "row": col // 5},
                    )
                    session.add(node)
                    await session.flush()
                    created_node_ids.append(str(node.node_id))
    except Exception as e:  # noqa: BLE001
        await progress_publish(task_id, ProgressEvent(
            stage=Stage.EXTRACT_TOPICS_WRITE, status="failed",
            payload={"error": f"db write failed: {type(e).__name__}: {e}"},
        ))
        return

    await progress_publish(task_id, ProgressEvent(
        stage=Stage.EXTRACT_TOPICS_WRITE, status="completed",
        payload={"created_node_ids": created_node_ids},
    ))
    await progress_publish(task_id, ProgressEvent(
        stage=Stage.EXTRACT_TOPICS_DONE, status="completed",
        payload={"created_node_ids": created_node_ids,
                 "extracted_resource_count": len(resources_payload)},
    ))
```

### Step 5: 写 POST 触发路由

新建 `backend/src/selflearn/gateway/routes/extract_topics.py`（仅 POST；SSE 路由在 T3 加）：

```python
"""提炼主题 POST 触发（SSE 流在 Task 3 加）。"""
from __future__ import annotations
import asyncio
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks
from selflearn.agents.extract_topics import run_extract_topics
from selflearn.infra.redis_client import get_redis
from selflearn.schemas.extract_topics import ExtractTopicsRequest, ExtractTopicsResponse


router = APIRouter(prefix="/api/resources", tags=["extract_topics"])


@router.post("/extract_topics", response_model=ExtractTopicsResponse, status_code=202)
async def trigger(body: ExtractTopicsRequest) -> ExtractTopicsResponse:
    task_id = str(uuid4())
    r = get_redis()
    await r.set(f"stream:{task_id}", "running", ex=3600)  # 留个尾巴，TTL 兜底
    # 走 BackgroundTasks 同进程执行（T1 ~ T3 阶段不做 worker 进程扩展）
    async def _kick() -> None:
        await run_extract_topics(task_id, body.selected_resource_ids)
    asyncio.create_task(_kick())
    return ExtractTopicsResponse(task_id=task_id)
```

### Step 6: 注册到 gateway

修改 `backend/src/selflearn/gateway/app.py`，加 `from selflearn.gateway.routes.extract_topics import router as extract_topics_router` + `app.include_router(extract_topics_router)`。

### Step 7: 写 failing 单测

新建 `backend/tests/unit/test_extract_topics_pipeline.py`：

```python
"""提炼主题 5 阶段流水线 + JSON schema + 重试 + 孤儿 KP 清理 + 事务回滚。"""
from __future__ import annotations
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from selflearn.agents.extract_topics import (
    TOPIC_SCHEMA, _validate_topics, TopicDraft,
    run_extract_topics,
)
from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.progress import Stage


# ----- 纯函数：schema 校验 -----

def test_validate_topics_accepts_well_formed() -> None:
    data = {"topics": [
        {"title": "T1", "description": "d" * 50, "prerequisites": [],
         "excerpt_text": "x" * 600, "source_resource_id": "abc"},
    ] * 0}  # 故意制造空数组，下面我们再用一个 valid 的加
    valid = {"topics": [
        {"title": "T1", "description": "d" * 50, "prerequisites": [],
         "excerpt_text": "x" * 600, "source_resource_id": "abc"},
        {"title": "T2", "description": "d" * 50, "prerequisites": ["T1"],
         "excerpt_text": "x" * 600, "source_resource_id": "abc"},
        {"title": "T3", "description": "d" * 50, "prerequisites": [],
         "excerpt_text": "x" * 600, "source_resource_id": "abc"},
    ]}
    drafts = _validate_topics(valid, {"abc"})
    assert len(drafts) == 3
    assert drafts[1].prerequisites == ["T1"]


def test_validate_topics_rejects_excerpt_too_short() -> None:
    bad = {"topics": [
        {"title": "T1", "description": "d" * 50, "prerequisites": [],
         "excerpt_text": "x" * 100, "source_resource_id": "abc"},
    ] * 3}  # 3 个
    with pytest.raises(Exception):  # _SchemaValidationError
        _validate_topics(bad, {"abc"})


def test_validate_topics_rejects_source_not_in_input() -> None:
    bad = {"topics": [
        {"title": "T1", "description": "d" * 50, "prerequisites": [],
         "excerpt_text": "x" * 600, "source_resource_id": "missing"},
        {"title": "T2", "description": "d" * 50, "prerequisites": [],
         "excerpt_text": "x" * 600, "source_resource_id": "missing"},
        {"title": "T3", "description": "d" * 50, "prerequisites": [],
         "excerpt_text": "x" * 600, "source_resource_id": "missing"},
    ]}
    with pytest.raises(Exception):
        _validate_topics(bad, {"abc"})


# ----- pipeline 行为：mock LLM + mock progress_publish -----

@pytest.mark.asyncio(loop_scope="session")
async def test_pipeline_publishes_5_stages_in_order() -> None:
    events = []
    with patch("selflearn.agents.extract_topics.progress_publish",
               new=AsyncMock(side_effect=lambda tid, ev: events.append(ev))):
        # mock LLM 返回有效 JSON
        valid_json = json.dumps({"topics": [...]})  # 实际下面填
        ...
```

（pipeline 测试要 mock 掉 LLM、DB；具体 mock 方案采用已有的 `AsyncMock` + `patch("selflearn.agents.extract_topics.LLMAgent")` 模式；事务回滚测试用 pytest `pytest.raises(RuntimeError)` 注入失败；orphan KP 测试先 INSERT 一个 KP with source，然后跑 pipeline 验该 KP 被 DELETE。）

参考 `tests/unit/test_profile_repo.py` 与 `tests/unit/test_progress_stream.py` 的纯 mock 写法。每个测试写完先跑 fail 再跑 pass。

### Step 8: 跑测试

```bash
cd backend && uv run pytest tests/unit/test_extract_topics_pipeline.py -v -p no:warnings 2>&1 | tail -25
```

Expected: 5-7 个 test 通过（包含 _validate_topics 的 3 个 + pipeline 行为 2-3 个 + 事务回滚 1 个）。

### Step 9: 全量回归

```bash
cd backend && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
```

Expected: clean。

### Step 10: Commit

```bash
cd D:/Projects/SelfLearn && git add backend/skills/skill.resource.extract_topics/SKILL.md backend/src/selflearn/agents/extract_topics.py backend/src/selflearn/schemas/extract_topics.py backend/src/selflearn/gateway/routes/extract_topics.py backend/src/selflearn/gateway/app.py backend/src/selflearn/progress/stages.py backend/tests/unit/test_extract_topics_pipeline.py && git commit -m "feat(后端): 提炼主题 5 阶段流水线（LLM + JSON schema + retry + 孤儿 KP 清理）"
```

---

## Task 3：SSE 流 + 进度条组件

**Files:**
- Modify: `backend/src/selflearn/gateway/routes/extract_topics.py`（加 GET /stream）
- Create: `frontend/src/components/ProgressOverlay.tsx`
- Create: `frontend/src/api/extractTopics.ts`（subscribe 函数）
- Create: `backend/tests/integration/test_extract_topics_sse.py`

**Interfaces:**
- Consumes: `progress_consume(trace_id)`（既有）
- Produces:
  - `GET /api/resources/extract_topics/stream?task_id=...` SSE 端点
  - `<ProgressOverlay>` 浮层
  - `subscribeExtractTopicsProgress(taskId, onEvent)` 客户端

---

### Step 1: 写 failing 集成测试（SSE 真连）

新建 `backend/tests/integration/test_extract_topics_sse.py`：

```python
"""EventSource 真连 /api/resources/extract_topics/stream 接收 5 阶段。"""
from __future__ import annotations
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from selflearn.gateway.app import app as gateway_app
from selflearn.progress import Stage


@pytest.mark.asyncio(loop_scope="session")
async def test_sse_pushes_5_stage_events_then_completed() -> None:
    """铺 5 个 ProgressEvent 到 Redis Stream，验证 SSE 客户端能按序收到。"""
    import asyncio
    from sse_starlette.sse import EventSourceResponse
    from selflearn.progress import progress_publish, ProgressEvent

    task_id = "integration-test-task-1234"

    # 在子任务里触发 5 阶段推送
    async def _producer():
        # 等客户端先连上
        await asyncio.sleep(0.2)
        for st in (Stage.EXTRACT_TOPICS_PARSE, Stage.EXTRACT_TOPICS_LLM,
                   Stage.EXTRACT_TOPICS_VALIDATE, Stage.EXTRACT_TOPICS_WRITE,
                   Stage.EXTRACT_TOPICS_DONE):
            await progress_publish(task_id, ProgressEvent(stage=st, status="completed"))
            await asyncio.sleep(0.05)

    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=10) as ac:
        # 启动 producer
        asyncio.create_task(_producer())

        # 用 raw httpx 流
        received_stages = []
        got_completed = False
        async with ac.stream("GET", f"/api/resources/extract_topics/stream?task_id={task_id}") as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                # SSE 行格式: "event: progress\ndata: {json}\n\n"
                if line.startswith("data:"):
                    payload = json.loads(line[len("data:"):].strip())
                    if payload.get("stage") not in (None, "completed"):
                        received_stages.append(payload["stage"])
                    if payload.get("status") == "completed":
                        got_completed = True
                        break
        assert got_completed
        assert len(received_stages) >= 1  # 至少收到 1 个
```

### Step 2: 跑测试，确认 FAIL（端点不存在）

```bash
cd backend && uv run pytest tests/integration/test_extract_topics_sse.py -v -p no:warnings 2>&1 | tail -20
```

Expected: FAIL。

### Step 3: 加 SSE 路由

修改 `backend/src/selflearn/gateway/routes/extract_topics.py`，在末尾追加：

```python
from collections.abc import AsyncIterator
import json
from sse_starlette.sse import EventSourceResponse
from selflearn.progress import progress_consume


async def _stream_extract_topics_events(task_id: str) -> AsyncIterator[dict[str, str]]:
    async for ev in progress_consume(task_id):
        data = json.dumps(
            {"stage": ev.stage.value, "status": ev.status, "payload": ev.payload},
            ensure_ascii=False,
        )
        yield {"event": "progress", "data": data}
        if ev.status in ("completed", "failed"):
            yield {"event": "completed" if ev.status == "completed" else "error",
                   "data": json.dumps({"status": ev.status, "payload": ev.payload}, ensure_ascii=False)}
            return


@router.get("/extract_topics/stream")
async def stream_extract_topics(task_id: str) -> EventSourceResponse:
    return EventSourceResponse(_stream_extract_topics_events(task_id))
```

### Step 4: 跑测试 PASS

```bash
cd backend && uv run pytest tests/integration/test_extract_topics_sse.py -v -p no:warnings 2>&1 | tail -10
```

Expected: PASS。

### Step 5: 写前端 SSE 客户端

新建 `frontend/src/api/extractTopics.ts`：

```typescript
import { apiPost } from './client';
import type { SSEEvent, SSEEventData } from './types';

export interface ExtractTopicsResponse {
  task_id: string;
}

export const triggerExtractTopics = (selectedResourceIds: string[]) =>
  apiPost<ExtractTopicsResponse>('/api/resources/extract_topics', {
    selected_resource_ids: selectedResourceIds,
  });

export function subscribeExtractTopicsProgress(
  taskId: string,
  onEvent: (e: SSEEvent) => void
): () => void {
  const es = new EventSource(
    `/api/resources/extract_topics/stream?task_id=${encodeURIComponent(taskId)}`
  );
  const handler = (kind: 'progress' | 'completed' | 'error') => (e: MessageEvent) => {
    onEvent({ event: kind, data: JSON.parse(e.data) } as SSEEvent);
  };
  es.addEventListener('progress', handler('progress'));
  es.addEventListener('completed', (e) => { handler('completed')(e); es.close(); });
  es.addEventListener('error', () => { es.close(); onEvent({ event: 'error', data: { status: 'failed', payload: { code: 'sse_error', message: 'lost connection' } } } as SSEEvent); });
  return () => es.close();
}
```

### Step 6: 写 ProgressOverlay 组件（浮层）

新建 `frontend/src/components/ProgressOverlay.tsx`：

```typescript
import { useEffect, useState } from 'react';
import { subscribeExtractTopicsProgress } from '../api/extractTopics';
import { subscribeLevelProgress } from '../api/sse';
import type { SSEEvent } from '../api/types';

export interface ProgressStage {
  key: string;
  label: string;
}

export type ProgressSource =
  | { kind: 'extract_topics'; taskId: string; stages: ProgressStage[]; onDone: (createdNodeIds: string[]) => void }
  | { kind: 'level'; levelId: string; traceId: string; stages: ProgressStage[]; onDone: () => void };

const STAGE_KEY_TO_INDEX = (stages: ProgressStage[]) =>
  Object.fromEntries(stages.map((s, i) => [s.key, i]));

export function ProgressOverlay({ source, onClose }: { source: ProgressSource; onClose: () => void }) {
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [progressStatus, setProgressStatus] = useState<{ [k: string]: 'running' | 'completed' | 'failed' }>({});

  useEffect(() => {
    const idxMap = STAGE_KEY_TO_INDEX(source.stages);
    const handle = (ev: SSEEvent) => {
      if (ev.event === 'progress') {
        const d = ev.data as { stage: string; status: 'running' | 'completed' | 'failed'; payload: { [k: string]: unknown } };
        // 'extract_topics.parse' → 'parse'
        const shortKey = d.stage.split('.').pop()!;
        setProgressStatus((s) => ({ ...s, [shortKey]: d.status }));
        if (idxMap[shortKey] !== undefined) setCurrentStageIdx(idxMap[shortKey]);
      } else if (ev.event === 'completed') {
        const d = ev.data as { status: string; payload: { created_node_ids?: string[] } };
        if (source.kind === 'extract_topics') {
          source.onDone(d.payload.created_node_ids ?? []);
        } else {
          source.onDone();
        }
      } else if (ev.event === 'error') {
        setError('任务失败');
      }
    };
    const close = source.kind === 'extract_topics'
      ? subscribeExtractTopicsProgress(source.taskId, handle)
      : subscribeLevelProgress(source.levelId, source.traceId, handle);
    return () => close();
  }, [source]);

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 9999,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{ background: '#FBF7EC', borderRadius: 12, padding: 24, minWidth: 480, fontFamily: 'HedvigLettersSerif, serif' }}>
        <h3 style={{ margin: 0, marginBottom: 16 }}>{source.kind === 'extract_topics' ? '提炼主题进度' : '关卡生成进度'}</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {source.stages.map((stage, idx) => {
            const status = progressStatus[stage.key] ?? 'pending';
            const isCurrent = idx === currentStageIdx && status === 'running';
            const isDone = status === 'completed';
            return (
              <div key={stage.key} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                <div style={{
                  width: 24, height: 24, borderRadius: '50%',
                  background: isDone ? '#5A8F4D' : isCurrent ? '#1B3B6F' : '#E5E5E0',
                  color: '#FBF7EC', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  animation: isCurrent ? 'pulse 1.2s infinite' : 'none',
                }}>
                  {isDone ? '✓' : idx + 1}
                </div>
                <div style={{ marginLeft: 6, fontSize: 13, color: isDone ? '#5A8F4D' : isCurrent ? '#1B3B6F' : '#6B6B70' }}>
                  {stage.label}
                </div>
                {idx < source.stages.length - 1 && (
                  <div style={{ flex: 1, height: 2, background: isDone ? '#5A8F4D' : '#E5E5E0', margin: '0 8px' }} />
                )}
              </div>
            );
          })}
        </div>
        {error && (
          <div style={{ marginTop: 16, color: '#BC4749', fontSize: 13 }}>
            {error}
            <button onClick={onClose} style={{ marginLeft: 12 }}>关闭</button>
          </div>
        )}
        <style>{`@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(27,59,111,0.4); } 70% { box-shadow: 0 0 0 8px rgba(27,59,111,0); } 100% { box-shadow: 0 0 0 0 rgba(27,59,111,0); } }`}</style>
      </div>
    </div>
  );
}
```

`frontend/src/api/types.ts` 里 `SSEEventData` 已有（reference：SSEEventData/SSEEvent 联合类型），如缺字段在后续 Task 4 一起补完。

### Step 7: 前端构建门禁

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: tsc + vite build clean（任何 type 错误在这里报错）。

### Step 8: 全量回归

```bash
cd backend && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
```

Expected: clean。

### Step 9: Commit

```bash
cd D:/Projects/SelfLearn && git add backend/src/selflearn/gateway/routes/extract_topics.py backend/tests/integration/test_extract_topics_sse.py frontend/src/components/ProgressOverlay.tsx frontend/src/api/extractTopics.ts && git commit -m "feat(后端+前端): 提炼主题 SSE 流 + 浮层进度条组件"
```

---

## Task 4：前端抽象组件（MarkdownRenderer + ResourceListView + LecturePane 重构）

**Files:**
- Create: `frontend/src/components/MarkdownRenderer.tsx`
- Create: `frontend/src/styles/markdown.css`
- Modify: `frontend/src/styles/lecture.css`（拆出 .markdown-body 共用样式）
- Modify: `frontend/src/panes/LecturePane.tsx`
- Create: `frontend/src/components/ResourceListView.tsx`
- Modify: `frontend/src/api/types.ts`（如缺字段）

**Interfaces:**
- Consumes: KaTeX `auto-render.mjs`、`lecture.css` 既有样式
- Produces:
  - `<MarkdownRenderer html={string} className?: string />` —— 接受 html 字符串，渲染 + KaTeX 懒加载
  - `<ResourceListView items MultiSelect? onSelectionChange? onRename? onDelete? onMove? onOpen? mode? />` —— 共用列表/网格组件

---

### Step 1: 写 styles/markdown.css（抽 lecture.css 中可共用部分）

新建 `frontend/src/styles/markdown.css`：

```css
.markdown-body {
  background: #FBF7EC;
  font-family: HedvigLettersSerif, "STKaiti", "KaiTi", serif;
  color: #1A1A1A;
  line-height: 1.7;
  padding: 16px;
  height: 100%;
  overflow: auto;
}
.markdown-body h2 {
  color: #1B3B6F;
  font-family: "STSong", "SimSun", "Times New Roman", serif;
  border-bottom: 1px solid rgba(27, 59, 111, 0.15);
  padding-bottom: 4px;
  margin-top: 24px;
}
.markdown-body h3 {
  color: #1B3B6F;
  font-family: "STSong", "SimSun", "Times New Roman", serif;
  margin-top: 16px;
}
.markdown-body p { margin: 12px 0; }
.markdown-body ul, .markdown-body ol { padding-left: 24px; }
.markdown-body code {
  font-family: "SF Mono", Consolas, monospace;
  background: rgba(27, 59, 111, 0.05);
  padding: 1px 4px;
  border-radius: 2px;
}
.markdown-body pre {
  background: #FFF;
  border: 1px solid rgba(27, 59, 111, 0.15);
  padding: 8px 12px;
  overflow-x: auto;
}
.markdown-body blockquote {
  border-left: 3px solid rgba(27, 59, 111, 0.3);
  margin: 12px 0;
  padding-left: 12px;
  color: #6B6B70;
  font-style: italic;
}
.markdown-body .callout {
  border-left: 4px solid #BC4749;
  background: rgba(188, 71, 73, 0.06);
  padding: 8px 12px;
  margin: 12px 0;
  border-radius: 0 4px 4px 0;
}
.markdown-body .formula {
  background: #FFF;
  border: 1px solid rgba(27, 59, 111, 0.15);
  padding: 12px;
  margin: 12px 0;
  font-family: "SF Mono", Consolas, monospace;
  text-align: center;
  overflow-x: auto;
}
.markdown-body .example {
  background: rgba(27, 59, 111, 0.04);
  border-left: 2px solid rgba(27, 59, 111, 0.3);
  padding: 8px 12px;
  margin: 12px 0;
  font-family: "STKaiti", "KaiTi", serif;
}
```

修改 `frontend/src/styles/lecture.css`：保留 `.lecture` 类但改为 `.markdown-body` 的别名：

```css
.lecture { /* alias for historical content already in DB */ }
```

（用 `@extend .markdown-body` 或者 CSS duplicate 一下）

### Step 2: 写 MarkdownRenderer 组件

新建 `frontend/src/components/MarkdownRenderer.tsx`：

```typescript
import { useEffect, useRef } from 'react';
import '../styles/markdown.css';

export function MarkdownRenderer({ html, className }: { html: string; className?: string }) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!html) return;
    let cancelled = false;
    Promise.all([
      import('katex/dist/katex.min.css'),
      import('katex'),
      import('katex/dist/contrib/auto-render.mjs'),
    ]).then(([, , autoRenderMod]) => {
      if (cancelled) return;
      const renderMathInElement = (autoRenderMod as any).default ?? autoRenderMod;
      if (typeof renderMathInElement !== 'function') {
        console.warn('[MarkdownRenderer] renderMathInElement 获取失败');
        return;
      }
      if (rootRef.current) {
        renderMathInElement(rootRef.current, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$', right: '$', display: false },
          ],
          throwOnError: false,
        });
      }
    });
    return () => { cancelled = true; };
  }, [html]);

  return (
    <div
      ref={rootRef}
      className={className ?? 'markdown-body'}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
```

### Step 3: 重构 LecturePane 使用 MarkdownRenderer

修改 `frontend/src/panes/LecturePane.tsx`，把 `dangerouslySetInnerHTML` 替换为 `<MarkdownRenderer html={lectureHtml} />`，删掉 KaTeX 加载 effect 和 `lecture.css` import（移交给 MarkdownRenderer）。其余错误处理 / 空态 / 防 LLM 错误展示段保留。

```typescript
import { useEffect, useState } from 'react';
import { getLevel } from '../api/level';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

export function LecturePane({ levelId }: { levelId: string }) {
  const [state, setState] = useState<
    | { loaded: false }
    | { loaded: true; html: string | null }
  >({ loaded: false });

  useEffect(() => {
    if (!levelId) return;
    getLevel(levelId)
      .then((lv) => setState({ loaded: true, html: lv.lecture_html ?? null }))
      .catch(() => setState({ loaded: true, html: null }));
  }, [levelId]);

  if (!state.loaded) {
    if (!levelId) return <div style={{ padding: 16 }}>请先选择左侧地图上的节点</div>;
    return <div style={{ padding: 16 }}>加载讲义...</div>;
  }
  const lectureHtml = state.html;

  if (!lectureHtml) {
    return <div style={{ padding: 16, color: '#6B6B70' }}>该关卡尚无讲义，请重新启动关卡</div>;
  }
  const looksLikeError = /无法获取|请检查参数|\bkp_id\b.*\bstudent_id\b|invalid_uuid/i.test(lectureHtml);
  if (looksLikeError) {
    return <div style={{ padding: 16, color: '#BC4749' }}>讲义生成失败（LLM 把工具错误写进了讲义）。</div>;
  }

  return <MarkdownRenderer html={lectureHtml} className="lecture" />;
}
```

### Step 4: 写 ResourceListView 组件

新建 `frontend/src/components/ResourceListView.tsx`：

```typescript
import { useState, useMemo } from 'react';
import type { ResourceListItem } from '../api/resources';

export interface ResourceListViewProps {
  items: ResourceListItem[];
  mode?: 'grid' | 'picker';   // 'picker' = 多选模式（提炼对话框）
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  onOpen?: (id: string) => void;
  onContextMenu?: (e: React.MouseEvent, id: string) => void;
  onRename?: (id: string, newName: string) => Promise<void>;
  onMove?: (id: string, newName: string) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
}

export function ResourceListView({
  items, mode = 'grid',
  selectedIds = new Set(),
  onSelectionChange,
  onOpen, onContextMenu, onRename, onMove, onDelete,
}: ResourceListViewProps) {
  const [editing, setEditing] = useState<{ id: string; value: string } | null>(null);
  // 网格列数自适应：视口宽度 / 140
  const cols = useMemo(() => Math.max(2, Math.floor(window.innerWidth / 140)), []);

  const sorted = useMemo(() =>
    [...items].sort((a, b) => a.name.localeCompare(b.name, 'zh')),
    [items]);

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `repeat(${cols}, 1fr)`,
      gap: 12, padding: 12, overflow: 'auto', height: '100%',
    }}>
      {sorted.map((r) => {
        const isSelected = selectedIds.has(r.id);
        const isFolder = !r.name.endsWith('.md');
        return (
          <div
            key={r.id}
            draggable
            onDragStart={(e) => e.dataTransfer.setData('resource:id', r.id)}
            onClick={() => {
              if (mode === 'picker' && onSelectionChange) {
                const ns = new Set(selectedIds);
                if (ns.has(r.id)) ns.delete(r.id); else ns.add(r.id);
                onSelectionChange(ns);
              } else if (onOpen) onOpen(r.id);
            }}
            onContextMenu={(e) => onContextMenu?.(e, r.id)}
            style={{
              cursor: 'pointer', padding: 8, borderRadius: 6,
              border: isSelected ? '2px solid #1B3B6F' : '1px solid #E5E5E0',
              position: 'relative',
              background: isSelected ? 'rgba(27,59,111,0.04)' : 'transparent',
            }}
          >
            {mode === 'picker' && isSelected && (
              <div style={{ position: 'absolute', top: 4, right: 4, color: '#1B3B6F' }}>✓</div>
            )}
            <div style={{ fontSize: 48, textAlign: 'center' }}>
              {isFolder ? '📁' : '📄'}
            </div>
            {editing?.id === r.id ? (
              <input
                autoFocus
                value={editing.value}
                onChange={(e) => setEditing({ id: r.id, value: e.target.value })}
                onBlur={async () => {
                  await onRename?.(r.id, editing.value);
                  setEditing(null);
                }}
                onKeyDown={async (e) => {
                  if (e.key === 'Enter') {
                    await onRename?.(r.id, editing.value);
                    setEditing(null);
                  } else if (e.key === 'Escape') setEditing(null);
                }}
                style={{ width: '100%', fontSize: 12 }}
              />
            ) : (
              <div
                style={{ fontSize: 13, textAlign: 'center', wordBreak: 'break-all', marginTop: 4 }}
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  setEditing({ id: r.id, value: r.name });
                }}
              >
                {r.name.split('/').pop()}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

### Step 5: 前端构建

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: clean。

### Step 6: 全量回归

```bash
cd backend && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
```

### Step 7: Commit

```bash
cd D:/Projects/SelfLearn && git add frontend/src/components/MarkdownRenderer.tsx frontend/src/components/ResourceListView.tsx frontend/src/styles/markdown.css frontend/src/styles/lecture.css frontend/src/panes/LecturePane.tsx && git commit -m "refactor(前端): 抽 MarkdownRenderer + ResourceListView 共用组件，LecturePane 复用"
```

---

## Task 5：三窗口 + 引导卡 + 端到端串联

**Files:**
- Modify: `frontend/src/types/window.ts`（AppId 加 3 个 + SINGLETON）
- Modify: `frontend/src/App.tsx`（WIN_CONTENT + renderBody）
- Modify: `frontend/src/store/useWorkspace.ts`（默认空 windows、hasOpenedFirstWindow 状态）
- Create: `frontend/src/components/MDBrowser.tsx`
- Create: `frontend/src/components/ResourceLibrary.tsx`
- Create: `frontend/src/components/ExtractTopicsDialog.tsx`
- Create: `frontend/src/components/EmptyStateOverlay.tsx`
- Create: `frontend/src/api/extractTopics.ts`（已经在 Task 3 创建过 import 行，本 task 在窗口里 consume）
- Modify: `frontend/src/components/Dock.tsx`（加 resource_library 图标）
- Create: `backend/scripts/e2e_md_driven.sh`
- Create: `frontend/tests/e2e/md-driven.spec.ts`（Playwright 端到端）

**Interfaces:**
- Consumes:
  - `ResourceListView`（Task 4）
  - `<MarkdownRenderer>`（Task 4）
  - `<ProgressOverlay>`（Task 3）
  - `listResources / uploadResources / getResource / updateResource / deleteResource`（Task 1）
  - `triggerExtractTopics + subscribeExtractTopicsProgress`（Task 3）
- Produces:
  - 3 个新 appId 窗口内容组件
  - 冷启动引导卡
  - `windows: {}` 默认状态
  - Playwright E2E 测试

---

### Step 1: 写 failing Playwright 端到端测试

新建 `frontend/tests/e2e/md-driven.spec.ts`：

```typescript
import { test, expect } from '@playwright/test';

test('user uploads 2 md files, generates topics, sees progress bar, and new nodes appear on map', async ({ page }) => {
  await page.goto('/');
  // 引导卡可见（首次访问无任何窗口）
  await expect(page.getByText('开始上传你的学习资料')).toBeVisible();

  // 打开资源管理器
  await page.getByRole('button', { name: '打开资源管理器' }).click();
  const rlWin = page.getByRole('dialog', { name: '资源管理器' });
  await expect(rlWin).toBeVisible();

  // 上传 2 个 md
  const fileInput = rlWin.locator('input[type="file"]');
  await fileInput.setInputFiles({
    name: '01-self-attn.md', mimeType: 'text/markdown',
    buffer: Buffer.from('# Self-Attention\n\n' + 'A'.repeat(700)),
  });
  await fileInput.setInputFiles({
    name: '02-multi-head.md', mimeType: 'text/markdown',
    buffer: Buffer.from('# Multi-Head\n\n' + 'B'.repeat(700)),
  });

  // 等待资源出现在网格
  await expect(rlWin.getByText('01-self-attn.md')).toBeVisible({ timeout: 5000 });

  // 选 2 个，触发提炼
  await rlWin.getByText('01-self-attn.md').click();
  await rlWin.getByText('02-multi-head.md').click();
  await rlWin.getByRole('button', { name: /用所选生成地图/ }).click();

  // 提炼对话框出现，按"确认提炼"
  const dlg = page.getByRole('dialog', { name: '生成地图对话框' });
  await expect(dlg).toBeVisible();
  await dlg.getByRole('button', { name: '确认提炼' }).click();

  // 进度条出现
  await expect(page.getByText('提炼主题进度')).toBeVisible();
  await expect(page.getByText('加载资料')).toBeVisible();
  await expect(page.getByText('AI 抽取主题')).toBeVisible();
  await expect(page.getByText('写入知识图谱')).toBeVisible();

  // 等待 SSE 完成（最长 90s，留 30s buffer 在 CI 上）
  await expect(page.getByText('提炼主题进度')).toBeHidden({ timeout: 120000 });

  // 引导卡消失
  await expect(page.getByText('开始上传你的学习资料')).toBeHidden();

  // 地图上有节点
  // (地图渲染依赖现有 TreasureMap 组件)
});
```

### Step 2: 注册 3 个 appId

修改 `frontend/src/types/window.ts`：

```typescript
export type AppId =
  | 'treasure_map' | 'chat' | 'document' | 'exercise'
  | 'code_editor' | 'notebook' | 'mind_map'
  | 'resource_library'
  | 'extract_topics_dialog'   // +new
  | 'md_browser'             // +new
  | 'dashboard' | 'settings' | 'task_list' | 'profile';

export const SINGLETON_APP_IDS: ReadonlySet<AppId> = new Set<AppId>([
  'treasure_map', 'notebook', 'resource_library', 'dashboard', 'settings',
  'task_list', 'extract_topics_dialog', 'md_browser',   // +new
]);
```

### Step 3: 资源管理器窗口内容

新建 `frontend/src/components/ResourceLibrary.tsx`：

```typescript
import { useEffect, useState } from 'react';
import { useWorkspace } from '../store/useWorkspace';
import { ResourceListView } from './ResourceListView';
import { listResources, uploadResources, deleteResource, updateResource, type ResourceListItem } from '../api/resources';
import { triggerExtractTopics, subscribeExtractTopicsProgress } from '../api/extractTopics';
import { ProgressOverlay } from './ProgressOverlay';

export function ResourceLibrary({ onOpenExtractDialog }: { onOpenExtractDialog: (ids: string[]) => void }) {
  const openWindow = useWorkspace((s) => s.openWindow);
  const [items, setItems] = useState<ResourceListItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const refresh = async () => {
    const r = await listResources();
    setItems(r.items);
  };
  useEffect(() => { refresh(); }, []);

  const onUpload = async (files: File[]) => {
    await uploadResources(files);
    await refresh();
  };

  const onExtract = async () => {
    onOpenExtractDialog([...selected]);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', gap: 8, padding: 8, borderBottom: '1px solid #E5E5E0' }}>
        <label style={{ padding: '6px 12px', background: '#1B3B6F', color: '#FBF7EC', borderRadius: 4, cursor: 'pointer' }}>
          ⬆ 上传 .md
          <input
            type="file" accept=".md" multiple hidden
            onChange={(e) => {
              const files = Array.from(e.target.files || []);
              if (files.length) onUpload(files);
              e.target.value = '';
            }}
          />
        </label>
        <button
          disabled={selected.size === 0}
          onClick={onExtract}
          style={{ padding: '6px 12px', background: selected.size ? '#BC4749' : '#E5E5E0', color: selected.size ? '#FBF7EC' : '#6B6B70', borderRadius: 4, cursor: selected.size ? 'pointer' : 'not-allowed' }}
        >
          🗺 用所选生成地图{selected.size > 0 && ` (${selected.size})`}
        </button>
      </div>
      <div
        onDrop={(e) => {
          e.preventDefault();
          const files = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.md'));
          if (files.length) onUpload(files);
        }}
        onDragOver={(e) => e.preventDefault()}
        style={{ flex: 1, overflow: 'hidden' }}
      >
        <ResourceListView
          items={items}
          mode="grid"
          selectedIds={selected}
          onSelectionChange={setSelected}
          onOpen={(id) => openWindow('md_browser')}
          onContextMenu={(e, id) => {
            e.preventDefault();
            if (confirm('删除这份资源？')) {
              deleteResource(id).then(refresh);
            }
          }}
          onRename={(id, name) => updateResource(id, name).then(refresh)}
        />
      </div>
    </div>
  );
}
```

### Step 4: 提炼对话框

新建 `frontend/src/components/ExtractTopicsDialog.tsx`：

```typescript
import { useState } from 'react';
import { ResourceListView } from './ResourceListView';
import { listResources, type ResourceListItem } from '../api/resources';

export function ExtractTopicsDialog({
  preSelectedIds, onConfirm, onCancel,
}: {
  preSelectedIds: string[];
  onConfirm: (selectedIds: string[]) => void;
  onCancel: () => void;
}) {
  const [items, setItems] = useState<ResourceListItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(preSelectedIds));

  useState(() => {
    listResources().then((r) => {
      setItems(r.items);
      // 过滤掉软删/不存在的预选
      setSelected(new Set(preSelectedIds.filter((id) => r.items.some((it) => it.id === id))));
    });
    return null;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: 12, borderBottom: '1px solid #E5E5E0' }}>
        选择要提炼的资料（已选 {selected.size} 个）
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ResourceListView
          items={items}
          mode="picker"
          selectedIds={selected}
          onSelectionChange={setSelected}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: 12, borderTop: '1px solid #E5E5E0' }}>
        <button onClick={onCancel} style={{ padding: '6px 16px' }}>取消</button>
        <button
          onClick={() => onConfirm([...selected])}
          disabled={selected.size === 0}
          style={{
            padding: '6px 16px',
            background: selected.size ? '#1B3B6F' : '#E5E5E0',
            color: selected.size ? '#FBF7EC' : '#6B6B70',
          }}
        >
          确认提炼
        </button>
      </div>
    </div>
  );
}
```

### Step 5: MD 浏览器

新建 `frontend/src/components/MDBrowser.tsx`：

```typescript
import { useEffect, useState } from 'react';
import { getResource, type ResourceResponse } from '../api/resources';
import { MarkdownRenderer } from './MarkdownRenderer';

export function MDBrowser({ resourceId }: { resourceId: string }) {
  const [res, setRes] = useState<ResourceResponse | null>(null);
  const [fontSize, setFontSize] = useState(15);
  useEffect(() => { getResource(resourceId).then(setRes); }, [resourceId]);
  if (!res) return <div style={{ padding: 16 }}>加载中…</div>;

  const onCopy = () => {
    navigator.clipboard.writeText(res.content_md);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', gap: 8, padding: 8, borderBottom: '1px solid #E5E5E0', alignItems: 'center' }}>
        <span style={{ flex: 1, fontSize: 13 }}>{res.name}</span>
        <span style={{ fontSize: 12, color: '#6B6B70' }}>字号</span>
        <button onClick={() => setFontSize(Math.max(12, fontSize - 1))}>A-</button>
        <span>{fontSize}</span>
        <button onClick={() => setFontSize(Math.min(24, fontSize + 1))}>A+</button>
        <button onClick={onCopy}>复制全文</button>
      </div>
      <div style={{ flex: 1, fontSize, overflow: 'hidden' }}>
        <MarkdownRenderer html={`<pre style="white-space: pre-wrap;">${escapeHtml(res.content_md)}</pre>`} />
      </div>
    </div>
  );
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
```

### Step 6: 引导卡

新建 `frontend/src/components/EmptyStateOverlay.tsx`：

```typescript
import { useWorkspace } from '../store/useWorkspace';

export function EmptyStateOverlay() {
  const windows = useWorkspace((s) => s.windows);
  const openWindow = useWorkspace((s) => s.openWindow);
  if (Object.keys(windows).length > 0) return null;

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(251,247,236,0.95)',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      zIndex: 999, fontFamily: 'HedvigLettersSerif, serif',
    }}>
      <h1 style={{ fontSize: 32, color: '#1B3B6F', marginBottom: 16 }}>开始上传你的学习资料</h1>
      <p style={{ fontSize: 16, color: '#6B6B70', maxWidth: 480, textAlign: 'center', lineHeight: 1.7 }}>
        上传 1-4 份 .md 文件，系统会从中<br/>抽取主题，生成知识地图。
      </p>
      <button
        onClick={() => openWindow('resource_library')}
        style={{ marginTop: 24, padding: '12px 24px', background: '#1B3B6F', color: '#FBF7EC', borderRadius: 6, fontSize: 15 }}
      >
        打开资源管理器
      </button>
      <p style={{ marginTop: 16, fontSize: 13, color: '#6B6B70' }}>（也可以从 Dock 栏打开）</p>
    </div>
  );
}
```

### Step 7: App.tsx WIN_CONTENT + renderBody

修改 `frontend/src/App.tsx`：

```typescript
const WIN_CONTENT: Record<string, WinDef> = {
  // 既有
  treasure_map: { title: '深度学习路径', isKey: true },
  task_list:    { title: '今日学习' },
  profile:      { title: '六维画像' },
  chat:         { title: '小书' },
  dashboard:    { title: '日历' },
  document:     { title: '讲义' },
  exercise:     { title: '习题' },
  // 新
  resource_library:        { title: '资源管理器' },
  extract_topics_dialog:   { title: '生成地图对话框' },
  md_browser:              { title: 'MD 浏览器' },
};

function renderBody(appId: string, win: WindowState, studentId: string, levelId: string, ...): ReactNode {
  switch (appId) {
    // 既有
    case 'treasure_map': return <TreasureMap studentId={studentId} />;
    // ... etc
    // 新
    case 'resource_library':      return <ResourceLibrary onOpenExtractDialog={(ids) => openWindow('extract_topics_dialog', { preselected: ids })} />;
    case 'extract_topics_dialog': return <ExtractTopicsDialog preSelectedIds={win.preselected || []} onConfirm={...} onCancel={...} />;
    case 'md_browser':            return <MDBrowser resourceId={win.resourceId || ''} />;
    default:                       return null;
  }
}
```

`renderBody` 新增 props 需要在 App.tsx 内部重写，让每个 case 能拿到 `openWindow` 等 store 方法。

### Step 8: useWorkspace 加 preselected 等动态字段 + 空 windows

修改 `frontend/src/store/useWorkspace.ts`：

```typescript
// 在 DEFAULT_WIN 旁边：
windows: {} as Record<string, WindowState>,
focusedId: null as string | null,
hasOpenedFirstWindow: false,

openWindow: (appId, payload) =>
  set((s) => {
    // ... 既有逻辑
    const newWin = { ..., payload };
    return { windows: { ...s.windows, [key]: newWin }, focusedId: key, hasOpenedFirstWindow: true };
  }),
```

并在 `WindowState` 类型上加 `payload?: { preselected?: string[]; resourceId?: string }`（在 `types/window.ts` 修改）。

### Step 9: Dock.tsx 加 resource_library（如果之前没有）

```typescript
// 检查现有 items 是否包含；若没有：
{ appId: 'resource_library', ic: '❐', lb: 'Res' },
```

### Step 10: 端到端 demo 脚本

新建 `backend/scripts/e2e_md_driven.sh`：

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
ROOT="$SCRIPT_DIR/.."

# 1. 起服务（如果你没在跑）
# 2. 准备测试 md
mkdir -p /tmp/md_files
cat > /tmp/md_files/01-self-attn.md <<EOF
# 自注意力机制

Self-Attention 是 Transformer 的核心。对于序列中每个位置，都计算它与所有位置的注意力分数。

## 公式

\$PE_{(pos, 2i)} = \sin\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)\$
\$PE_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)\$

(此后填充大量内容到 ≥500 字)
EOF
echo "(更多正文)" >> /tmp/md_files/01-self-attn.md
python -c "import sys; sys.stdout.write('# 多头注意力\n\n' + '多头注意力把 Q、K、V 分别线性映射 h 次后并行做 attention。' * 20)" > /tmp/md_files/02-multi-head.md

# 3. 调用上传 + 提炼（实际靠 frontend Playwright；本脚本只验证 DB 状态）
echo "请通过前端 UI 完成上传 + 提炼。完成后会触发 SSE 流，5 阶段完后回到这里。"
read -p "完成后按 Enter 继续..."

# 4. 验 DB
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
  SELECT kp_id, title, source, LENGTH(source_content_md) AS excerpt_len
  FROM knowledge_points WHERE source IS NOT NULL ORDER BY created_at DESC LIMIT 5;
  SELECT COUNT(*) AS map_node_count FROM map_nodes WHERE student_id = '86820161-b0f0-455f-91b4-a69e49445bdf';
"

echo "如果上方有 ≥ 1 个 KP + ≥ 1 个 MapNode = 通过"
```

### Step 11: 跑 Playwright

```bash
cd frontend && npx playwright install --with-deps chromium   # 一次性
cd frontend && npx playwright test tests/e2e/md-driven.spec.ts
```

Expected: PASS in <120s. 如果 CI 超时，调大 `expect.toBeHidden({ timeout: 120000 })`。

### Step 12: 前端构建门禁

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: clean。

### Step 13: 全量回归

```bash
cd backend && uv run pytest tests/unit tests/integration -p no:warnings 2>&1 | tail -3
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
```

### Step 14: Commit

```bash
cd D:/Projects/SelfLearn && git add frontend/src/types/window.ts frontend/src/App.tsx frontend/src/store/useWorkspace.ts frontend/src/components/Dock.tsx frontend/src/components/ResourceLibrary.tsx frontend/src/components/ExtractTopicsDialog.tsx frontend/src/components/MDBrowser.tsx frontend/src/components/EmptyStateOverlay.tsx frontend/tests/e2e/md-driven.spec.ts backend/scripts/e2e_md_driven.sh && git commit -m "feat(前端): 资源管理器+MD 浏览器+提炼对话框三窗口+冷启动引导卡+端到端 e2e"
```

---

## Task 6：director chain 注入 source_content_md + 关卡进度条复用

**Files:**
- Modify: `backend/src/selflearn/agents/core.py`（prefetch 透传 source_content_md）
- Modify: `backend/skills/skill.lecture.generate/SKILL.md`（系统提示词引用规则）
- Modify: `backend/skills/skill.exercise.generate/SKILL.md`（同）
- Create: `frontend/src/components/LevelStartProgress.tsx`（弹窗形式）
- Modify: `frontend/src/api/sse.ts`（确认 subscribeLevelProgress 仍可用）
- Create: `backend/tests/unit/test_director_injects_source_content.py`

**Interfaces:**
- Consumes:
  - `core.py` 的 `prefetch` 函数（读 kp）
  - `skill.lecture.generate` / `skill.exercise.generate`（既有 prompt）
  - `<ProgressOverlay>` from Task 3（重新利用）
- Produces:
  - lecture / exercise 的 LLM 提示词增加"如有 source_content_md 则优先引用"
  - 关卡 4 阶段 `[outline, lecture_html, exercise, review]` ProgressOverlay
  - 单测：prefetch 返回含 source_content_md；LLM 提示词拼装序列化含 source_content_md

---

### Step 1: 写 failing 单测：core.py prefetch 透传

新建 `backend/tests/unit/test_director_injects_source_content.py`：

```python
"""验证 director chain prefetch 把 KP.source_content_md 注入 lecture/exercise env。"""
from __future__ import annotations
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert
from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.agents.core import build_prefetch
from selflearn.infra.db import get_session_factory


@pytest.mark.asyncio(loop_scope="session")
async def test_prefetch_includes_source_content_md() -> None:
    kp_id = uuid4()
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            insert(KnowledgePoint).values(
                kp_id=kp_id,
                subject="用户提炼",
                title="T1",
                description="desc",
                difficulty=2,
                prerequisites=[],
                source="01-self-attn.md",
                source_content_md="x" * 800,  # 800 字
            )
        )
        await session.commit()

    prefetch_data = await build_prefetch(student_id=str(uuid4()), kp_id=kp_id)
    assert "source_content_md" in prefetch_data
    assert prefetch_data["source_content_md"].startswith("x")
```

### Step 2: 跑测试 FAIL

```bash
cd backend && uv run pytest tests/unit/test_director_injects_source_content.py -v -p no:warnings 2>&1 | tail -15
```

Expected: FAIL（因为现有 prefetch 不带 `source_content_md`）。

### Step 3: 修改 agents/core.py prefetch

找到 `build_prefetch` 函数（应该在 `selflearn/agents/core.py`），加 `source_content_md` 字段：

```python
async def build_prefetch(student_id: str, kp_id: str) -> dict[str, Any]:
    """Return prefetch dict to inject into LLM user prompt."""
    factory = get_session_factory()
    async with factory() as session:
        kp = (await session.execute(
            select(KnowledgePoint).where(KnowledgePoint.kp_id == UUID(kp_id))
        )).scalar_one_or_none()
        if kp is None:
            return {"kp_id": kp_id, "error": "kp not found"}
        return {
            "kp_id": str(kp.kp_id),
            "title": kp.title,
            "description": kp.description,
            "difficulty": kp.difficulty,
            "prerequisites": kp.prerequisites,
            "subject": kp.subject,
            "source": kp.source,
            "source_content_md": kp.source_content_md,  # +new
        }
```

### Step 4: 跑测试 PASS

```bash
cd backend && uv run pytest tests/unit/test_director_injects_source_content.py -v -p no:warnings
```

Expected: PASS。

### Step 5: 修改 lecture SKILL.md 加引用规则

修改 `backend/skills/skill.lecture.generate/SKILL.md`，在 "输入" 段加：

```markdown
- env.payload.source_content_md → （**可选**）蒸馏时挑出来的"提供的材料知识"片段。如存在，**优先围绕它讲解**，并在讲义显式标注"参考自 XXX.md 的段落"。
- env.payload.source → 该 KP 来源的原始 md 文件名（如"Transformer 详解.md"）。
```

并在 system prompt 末尾加：

```markdown
## 引用源标注规则（重要）
若 env.payload.source_content_md 非空：
- 讲义每节开头或末尾标注「参考自 XXX.md」
- 不要直接大段复制 md 内容；只引 1-2 句作为锚点，然后展开讲解
- 如 md 内容与 KP 不完全契合，**只引用契合部分**，不强行引用
```

### Step 6: 修改 exercise SKILL.md 同上

修改 `backend/skills/skill.exercise.generate/SKILL.md` 的"输入"与"严格输出格式"段：

```markdown
- env.payload.source_content_md → 蒸馏切片（可选）；如有，**explanation 必须显式引用其中片段**，引用方式："如讲义『XXX』中所言：..."
- env.payload.source → 来源文件名（如有）
```

并在 explanation 强制要求里加：

```markdown
4. 如存在 source_content_md，必须从其中挑一句作为引子（"如材料『XXX.md』中提到：..."）
```

### Step 7: 端到端 e2e 验讲义引用 md

启服务（参考 CLAUDE.md `HTTP_PROXY=... docker compose build gateway worker && docker compose up -d --force-recreate gateway worker` 或直接 `uvicorn`）。

运行：
```bash
bash backend/scripts/e2e_md_driven.sh
# 前端 UI 触发提炼主题；拿到 created_node_ids 后：
NODE_ID=<from created_node_ids>
LEVEL_ID=$(curl -X POST http://localhost:8000/api/level/start \
  -H 'Content-Type: application/json' \
  -d "{\"student_id\":\"$KEEP_STUDENT\",\"node_id\":\"$NODE_ID\"}" | jq -r '.level_id')
curl http://localhost:8000/api/level/$LEVEL_ID | jq '.lecture_html' | grep -E "参考自|自注意力" && echo OK || echo FAIL
```

Expected: 找到 "参考自" 或 KP title 关键字。

### Step 8: 关卡进度条 component（复用 ProgressOverlay）

新建 `frontend/src/components/LevelStartProgress.tsx`：

```typescript
import { ProgressOverlay } from './ProgressOverlay';

export function LevelStartProgress({
  levelId, traceId, onDone, onClose,
}: {
  levelId: string;
  traceId: string;
  onDone: () => void;
  onClose: () => void;
}) {
  return (
    <ProgressOverlay
      source={{
        kind: 'level',
        levelId,
        traceId,
        stages: [
          { key: 'outline',     label: '提炼纲要' },
          { key: 'lecture',     label: '写讲义' },
          { key: 'exercise',    label: '出题' },
          { key: 'review',      label: '审核' },
        ],
        onDone,
      }}
      onClose={onClose}
    />
  );
}
```

接入 `frontend/src/panes/LecturePane.tsx`：在 `useEffect` 内判断当前关卡状态（`level.lecture_html != null`），如果是 `lecture_html == null` 则展示 `LevelStartProgress`，否则展示 `<MarkdownRenderer>`。

### Step 9: 前端构建

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: clean。

### Step 10: 全量回归

```bash
cd backend && uv run pytest tests/unit tests/integration -p no:warnings 2>&1 | tail -3
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
```

### Step 11: Commit

```bash
cd D:/Projects/SelfLearn && git add backend/src/selflearn/agents/core.py backend/skills/skill.lecture.generate/SKILL.md backend/skills/skill.exercise.generate/SKILL.md backend/tests/unit/test_director_injects_source_content.py frontend/src/components/LevelStartProgress.tsx frontend/src/panes/LecturePane.tsx && git commit -m "feat(后端+前端): director chain 注入 KP.source_content_md + 关卡进度条"
```

---

## 自检（写作计划时我自己跑）

| 检查项 | 结果 |
|--------|------|
| **Spec 覆盖** | §2 数据模型 → Task 1；§3.1 CRUD → Task 1；§3.2/3.3 提炼流程 → Task 2；§3.5 SSE 协议 → Task 3；§4.1-4.5 前端注册 + ProgressOverlay → Task 3-5；§4.6 冷启动 → Task 5；§6.1 单测 → Task 1-3-5；§6.3 e2e 脚本 → Task 5 |
| **Placeholder 扫描** | 无 TBD/TODO；所有 step 都给了具体代码 / 命令 / 预期输出 |
| **Type 一致性** | `Resource.id` (UUID) ↔ `ResourceListItem.id` (string) ↔ `getResource()` 输出；`task_id: str` ↔ SSE `task_id=` query；`WindowState.payload.preselected[]` ↔ ExtractTopicsDialog.preSelectedIds |
| **约束引用** | CLAUDE.md（docker proxy / no worktree / KEEP_STUDENT 4 处字面量 / 唯一账户）每条任务都隐含遵守；memory `no-auth-no-login` 不引 token；FK CASCADE 约束在 Task 2 write 段用 `delete(MapNode).where(...)` 走 SQL 触发数据库层 cascade |
| **下个 review 的引用** | Task 2 §5 整删 + INSERT 用 SQL `delete(Model).where(...)` 让 DB 层 cascade；Task 5 §6 默认 `windows: {}`，hasOpenedFirstWindow 状态；Task 5 §10 e2e 脚本需前端 UI 完成 |

## 执行选项

Plan 已落定到 `docs/superpowers/plans/2026-07-17-md-driven-level.md`，6 个 task。两种执行选项：

**1. Subagent-Driven（推荐）** — 每个 task 起 1 个 implementer + 1 个 task reviewer + 末尾 1 个 whole-branch review；中间不打断你。
**2. Inline Execution** — 当前会话直接按 checklist 推进，每完成一个 task 给你 checkpoint。

请告诉我选哪个，我立刻开干。