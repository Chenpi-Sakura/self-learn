# 讲义 HTML（Lecture）— Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `levels` 表加 `lecture_html` 字段，Director 关卡生成链路多一次 LLM 调用产出白名单约束的 HTML 讲义（含 KaTeX 公式），前端 `LecturePane` 渲染该 HTML 替代当前的"显示第一道题 prompt"占位；讲义与答案解释通过 `_extract_lecture_outline` 解耦 —— 讲义只讲知识点，exercise 的 `explanation` 字段显式引用讲义纲要。

**Architecture:**
1. **数据层**：Alembic migration 加 `lecture_html String(50000)` 列，ORM/Pydantic 同步；`tool.create_level` 去掉 hasattr 防御 + 硬截断到 50000
2. **Director chain 注入 outline**：lecture 跑完后调 `_extract_lecture_outline(html)` 提取 `{sections, callouts, examples}` 三类结构化纲要，注入到 exercise 的 `env.payload.lecture_outline`
3. **SKILL prompt 改写**：`skill.lecture.generate` 重写为"纯知识点讲解"；`skill.exercise.generate` 改为"explanation 首句引用 lecture_outline + ≥30 字"
4. **前端渲染**：`LecturePane` 改用 `dangerouslySetInnerHTML` + KaTeX 懒加载（code-splitting）；新增 `lecture.css` 主题样式

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic + P5 MCP（nh3） + DeepSeek（openai_compat） + React 18 + Vite + KaTeX 0.16

## Global Constraints

- **依赖约束**：后端不引入新依赖（mcp / nh3 已存在）；前端新增 `katex@^0.16.11` 唯一新依赖
- **迁移约束**：不修改任何已有 alembic migration；新增一个独立 migration（down_revision 指向 `f1963078e4e4` 当前 head）
- **字段类型**：`lecture_html String(50000) nullable=True`（不是 Text，不是 String(20000)，理由见 spec § 4.4）
- **重试策略**：整链 retry（max_attempts=3），lecture lint rejected → 整链 retry，不软失败
- **不做的事**：
  - 不做前端 XSS 二次清洗（依赖后端 nh3）
  - 不调 LLM 做讲义 review（仅 lint_html + not_empty）
  - 不实现图片/视频/iframe（图片模态用户后续做）
  - 不主动迁移历史关卡讲义（NULL 占位即可）
  - 不重做 ReviewAgent / Director chain
- **commit 规范**：中文 commit message；branch 直接 main（CLAUDE.md + memory `no-worktrees-sdd`）
- **Docker 构建**：`HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 docker compose build gateway worker`
- **测试运行**：`cd backend && uv run pytest -p no:warnings`

---

## 文件结构（实施前心智模型）

**新建 5 文件**：
- `backend/migrations/versions/<hash>_add_lecture_html.py` — Alembic migration
- `backend/src/selflearn/agents/lecture_outline.py` — `_extract_lecture_outline` 工具函数
- `backend/tests/unit/test_create_level.py` — `tool.create_level` 截断 + 字段写入单测
- `backend/tests/unit/test_lecture_outline.py` — `_extract_lecture_outline` 各场景单测
- `backend/tests/unit/test_exercise_skill_outline.py` — exercise LLM 收到 lecture_outline 的注入单测
- `frontend/src/styles/lecture.css` — 讲义主题样式

**修改 6 文件**：
- `backend/src/selflearn/domain/level.py` — ORM 加 `lecture_html`
- `backend/src/selflearn/schemas/level.py` — `LevelDetailResponse` 加 `lecture_html`
- `backend/src/selflearn/gateway/routes/level.py` — `get_level` 返回 lecture_html
- `backend/src/selflearn/mcp_server/tools/create_level.py` — 截断 + 去掉 hasattr 防御
- `backend/src/selflearn/agents/director.py` — lecture 后跑 outline 提取 + 注入 exercise env
- `backend/skills/skill.lecture.generate/SKILL.md` — 占位 → 真实讲解 prompt
- `backend/skills/skill.exercise.generate/SKILL.md` — 去掉 prefetch `tool.get_kp` + 加 lecture_outline 说明 + explanation 强制要求
- `frontend/src/api/types.ts` — `LevelDetail` 加 `lecture_html`
- `frontend/src/panes/LecturePane.tsx` — 渲染 lecture_html + KaTeX 懒加载
- `frontend/package.json` — 加 `katex` 依赖

**修改 1 测试文件**：
- `backend/tests/integration/test_director_e2e.py` — 加 lecture_outline 注入 + 端到端断言

---

## Phase 1 — 数据层

### Task 1: Alembic migration 加 lecture_html 列

**Files:**
- Create: `backend/migrations/versions/<hash>_add_lecture_html.py`（hash 用 alembic 命令生成；先占位 `placeholder`，Task 2 跑完命令后回填）

**Interfaces:**
- Consumes: `down_revision = "f1963078e4e4"`（当前 head = stage4_profile_snapshots）
- Produces: 一个可被 `alembic upgrade head` 运行的 migration，给 `levels` 表加 `lecture_html` 列

- [ ] **Step 1: 写 migration 文件**

在 `backend/migrations/versions/` 下创建 `<hash>_add_lecture_html.py`：

```python
"""add lecture_html to levels

Revision ID: <hash>
Revises: f1963078e4e4
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa


revision = "<hash>"
down_revision = "f1963078e4e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "levels",
        sa.Column("lecture_html", sa.String(50000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("levels", "lecture_html")
```

把 `<hash>` 临时替换为 `placeholder`（下一步会被真 hash 替换）。

- [ ] **Step 2: 用 alembic 工具生成 revision hash**

```bash
cd backend && python -c "import secrets; print(secrets.token_hex(6))"
```

Expected: 输出一个 12 字符的 hex 字符串（例：`a1b2c3d4e5f6`）。

- [ ] **Step 3: 用真 hash 替换占位**

用上一步的 hash 重命名文件并替换文件内的 `<hash>` 占位：

```bash
mv migrations/versions/placeholder_add_lecture_html.py migrations/versions/<hash>_add_lecture_html.py
```

然后用 Edit 工具把文件内 4 个 `<hash>` 占位全替换为真 hash。

- [ ] **Step 4: 验证 migration 文件头正确**

```bash
cd backend && head -15 migrations/versions/<hash>_add_lecture_html.py
```

Expected: 输出看到 `revision = "<hash>"` 和 `down_revision = "f1963078e4e4"` 是真实值，不再有 `<hash>` 字面。

- [ ] **Step 5: 验证 alembic 识别新 migration**

```bash
cd backend && alembic heads
```

Expected: 输出当前 head 是 `<hash>_add_lecture_html`（head 切换为新 migration）。

- [ ] **Step 6: 验证 alembic upgrade 可逆**

```bash
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

Expected: 三步都 EXIT=0，最后状态是 head 升级到新 migration。

- [ ] **Step 7: Commit**

```bash
git add backend/migrations/versions/<hash>_add_lecture_html.py
git commit -m "feat(db): migration 加 levels.lecture_html 列（String(50000) nullable）"
```

---

### Task 2: ORM 字段 Level.lecture_html

**Files:**
- Modify: `backend/src/selflearn/domain/level.py:18` 后插入新字段（在 `form` 之后、`created_at` 之前）

**Interfaces:**
- Consumes: Task 1 的 migration 已 apply，DB 有 `lecture_html` 列
- Produces: `Level` model 加 `lecture_html: Mapped[str | None]` 字段（与 `node_id` 同样的 nullable 风格）

- [ ] **Step 1: 读现有 Level model**

```bash
cat backend/src/selflearn/domain/level.py
```

Expected: 看到 27 行 ORM 定义，包含 `level_id / node_id / status / form / created_at / updated_at` 6 个字段。

- [ ] **Step 2: 加 lecture_html 字段**

用 Edit 工具在 `form: Mapped[str] = mapped_column(String(32), nullable=False, default="exercise")` 之后插入：

```python
    lecture_html: Mapped[str | None] = mapped_column(String(50000), nullable=True)
```

注意：缩进 4 空格；末尾无逗号（Python 不要求）。

- [ ] **Step 3: 验证 Python 语法**

```bash
cd backend && python -c "from selflearn.domain.level import Level; print(Level.lecture_html)"
```

Expected: 输出 `< sqlalchemy.orm.attributes.InstrumentedAttribute ... >`，说明字段被 SQLAlchemy 识别。

- [ ] **Step 4: 验证 alembic 模型与 migration 一致**

```bash
cd backend && alembic check
```

Expected: 输出 `No new upgrade operations detected.`（说明 ORM 字段与 DB schema 一致）。

- [ ] **Step 5: Commit**

```bash
git add backend/src/selflearn/domain/level.py
git commit -m "feat(domain): Level.lecture_html 字段（Mapped[str|None], String(50000)）"
```

---

### Task 3: Pydantic schema + Gateway 返回 lecture_html

**Files:**
- Modify: `backend/src/selflearn/schemas/level.py` 加 `lecture_html` 字段
- Modify: `backend/src/selflearn/gateway/routes/level.py` `get_level` 返回 `lecture_html`

**Interfaces:**
- Consumes: Task 2 的 ORM 字段
- Produces: `LevelDetailResponse` 含 `lecture_html: str | None = None`；GET `/api/level/{id}` 响应 JSON 含 `lecture_html` 键

- [ ] **Step 1: 读现有 schema**

```bash
cat backend/src/selflearn/schemas/level.py
```

Expected: 看到 `LevelDetailResponse` 4 个字段：`level_id / node_id / status / exercises`。

- [ ] **Step 2: 加 lecture_html 字段**

用 Edit 在 `LevelDetailResponse` 类的 `exercises: list[ExerciseResponse] = []` 行后插入：

```python
    lecture_html: str | None = None  # NULL 时前端显示"该关卡尚无讲义"
```

注意：4 空格缩进。

- [ ] **Step 3: 验证 schema**

```bash
cd backend && python -c "from selflearn.schemas.level import LevelDetailResponse; import uuid; r = LevelDetailResponse(level_id=uuid.uuid4(), node_id=uuid.uuid4(), status='generated'); print(r.lecture_html, r.model_dump())"
```

Expected: 输出 `None` 和包含 `'lecture_html': None` 的字典。

- [ ] **Step 4: 改 Gateway `get_level`**

读 `backend/src/selflearn/gateway/routes/level.py` 第 179-205 行的 `get_level` 函数。在最后 `return LevelDetailResponse(...)` 块中加一行 `lecture_html=level.lecture_html,`（放在 `status=level.status,` 之后）。

- [ ] **Step 5: 跑现有 level 测试**

```bash
cd backend && uv run pytest tests/unit/test_level_start_routing.py -v -p no:warnings 2>&1 | tail -20
```

Expected: 全 PASS（无回归；改的是 return 字段不影响既有逻辑）。

- [ ] **Step 6: Commit**

```bash
git add backend/src/selflearn/schemas/level.py backend/src/selflearn/gateway/routes/level.py
git commit -m "feat(api): LevelDetailResponse + GET /api/level/{id} 返回 lecture_html 字段"
```

---

### Task 4: tool.create_level 截断 + 单测

**Files:**
- Modify: `backend/src/selflearn/mcp_server/tools/create_level.py`（截断 + 去掉 hasattr 防御）
- Create: `backend/tests/unit/test_create_level.py`

**Interfaces:**
- Consumes: Task 2 的 `Level.lecture_html` 字段
- Produces: `create_level(node_id, lecture_html=None)` 入参 `lecture_html` 超 50000 字符时硬截断 + log warn；None 时不写 lecture_html

- [ ] **Step 1: 写 failing test（lecture_html 正常入参）**

创建 `backend/tests/unit/test_create_level.py`：

```python
"""tool.create_level 单测：lecture_html 入参 + 截断 + None 跳过。

为避免 pytest-asyncio + module-level engine 的 'attached to a different loop'
问题，单测用 AsyncMock + patch session_factory 避免真 DB。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from selflearn.mcp_server.tools.create_level import (
    MAX_LECTURE_HTML_LEN,
    create_level,
)


@pytest.mark.asyncio
async def test_create_level_accepts_lecture_html() -> None:
    """lecture_html 入参正常时，Level 行带该字段。"""
    node_id = str(uuid4())
    lecture = "<h2>概念</h2><p>讲解</p>"

    fake_level = MagicMock()
    fake_level.level_id = uuid4()
    fake_session = AsyncMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock(side_effect=lambda lvl: setattr(lvl, "level_id", fake_level.level_id))

    with patch("selflearn.mcp_server.tools.create_level.get_session_factory") as gsf:
        gsf.return_value = lambda: fake_session

        result = await create_level(node_id=node_id, lecture_html=lecture)

    assert result["ok"] is True
    assert "level_id" in result
    # 关键断言：Level(...) 调用传入了 lecture_html
    fake_session.add.assert_called_once()
    added_level = fake_session.add.call_args[0][0]
    assert added_level.lecture_html == lecture


@pytest.mark.asyncio
async def test_create_level_truncates_long_lecture_html() -> None:
    """lecture_html 超 MAX_LECTURE_HTML_LEN 时硬截断。"""
    node_id = str(uuid4())
    long_html = "<p>" + ("x" * (MAX_LECTURE_HTML_LEN + 1000)) + "</p>"

    fake_session = AsyncMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock()

    with patch("selflearn.mcp_server.tools.create_level.get_session_factory") as gsf:
        gsf.return_value = lambda: fake_session

        result = await create_level(node_id=node_id, lecture_html=long_html)

    assert result["ok"] is True
    fake_session.add.assert_called_once()
    added_level = fake_session.add.call_args[0][0]
    assert added_level.lecture_html is not None
    assert len(added_level.lecture_html) == MAX_LECTURE_HTML_LEN
    assert added_level.lecture_html == long_html[:MAX_LECTURE_HTML_LEN]


@pytest.mark.asyncio
async def test_create_level_lecture_html_none_skips_field() -> None:
    """lecture_html=None 时，Level 行的 lecture_html 字段为 None（不写列）。"""
    node_id = str(uuid4())

    fake_session = AsyncMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock()

    with patch("selflearn.mcp_server.tools.create_level.get_session_factory") as gsf:
        gsf.return_value = lambda: fake_session

        result = await create_level(node_id=node_id, lecture_html=None)

    assert result["ok"] is True
    fake_session.add.assert_called_once()
    added_level = fake_session.add.call_args[0][0]
    assert added_level.lecture_html is None
```

- [ ] **Step 2: 跑测试验证 fail**

```bash
cd backend && uv run pytest tests/unit/test_create_level.py -v -p no:warnings 2>&1 | tail -20
```

Expected: 3 个测试都 FAIL（`NameError: cannot import name MAX_LECTURE_HTML_LEN`，因为还没实现）。

- [ ] **Step 3: 实现 create_level 截断**

重写 `backend/src/selflearn/mcp_server/tools/create_level.py`：

```python
"""tool.create_level: 写一个 Level 行（绑定 MapNode）。"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from selflearn.core.logging import get_logger
from selflearn.domain.level import Level
from selflearn.infra.db import get_session_factory

log = get_logger("create_level")

MAX_LECTURE_HTML_LEN = 50000


async def create_level(
    node_id: str,
    lecture_html: str | None = None,
) -> dict[str, Any]:
    """给一个 MapNode 创建 Level 行。

    lecture_html 是讲义 HTML（nh3 白名单清洗后）。
    若超过 MAX_LECTURE_HTML_LEN，截断并 log warn（prompt 已有 800-1500 字约束，截断是兜底）。

    Returns: {"ok": True, "level_id": "..."} 或
             {"ok": False, "error": "invalid_uuid:<node_id>"}
    """
    try:
        node_uuid = UUID(node_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{node_id}"}

    factory = get_session_factory()
    async with factory() as session:
        truncated_html: str | None = None
        if lecture_html is not None:
            if len(lecture_html) > MAX_LECTURE_HTML_LEN:
                log.warning(
                    "create_level.lecture_html_truncated",
                    orig_len=len(lecture_html),
                    max_len=MAX_LECTURE_HTML_LEN,
                )
                truncated_html = lecture_html[:MAX_LECTURE_HTML_LEN]
            else:
                truncated_html = lecture_html

        level = Level(
            node_id=node_uuid,
            status="generated",
            form="exercise",
            lecture_html=truncated_html,
        )
        session.add(level)
        await session.commit()
        await session.refresh(level)
        return {"ok": True, "level_id": str(level.level_id)}
```

- [ ] **Step 4: 跑测试验证 pass**

```bash
cd backend && uv run pytest tests/unit/test_create_level.py -v -p no:warnings 2>&1 | tail -20
```

Expected: 3 个测试全 PASS。

- [ ] **Step 5: 跑现有相关测试确认无回归**

```bash
cd backend && uv run pytest tests/unit/test_level_start_routing.py tests/unit/test_director_chain.py -v -p no:warnings 2>&1 | tail -30
```

Expected: 全 PASS（无回归）。

- [ ] **Step 6: Commit**

```bash
git add backend/src/selflearn/mcp_server/tools/create_level.py backend/tests/unit/test_create_level.py
git commit -m "feat(mcp): tool.create_level 截断 lecture_html 到 50000 + 去掉 hasattr 防御 + 单测"
```

---

## Phase 2 — Director chain 联调

### Task 5: `_extract_lecture_outline` 工具函数 + 单测

**Files:**
- Create: `backend/src/selflearn/agents/lecture_outline.py`
- Create: `backend/tests/unit/test_lecture_outline.py`

**Interfaces:**
- Consumes: `lecture_html: str`（已通过 `tool.lint_html` 清洗的 HTML）
- Produces: `extract_lecture_outline(html) -> dict[str, list[str]]` 返回 `{"sections": [...], "callouts": [...], "examples": [...]}`

- [ ] **Step 1: 写 failing test**

创建 `backend/tests/unit/test_lecture_outline.py`：

```python
"""extract_lecture_outline 单测：从 lecture_html 抽 sections/callouts/examples。"""
from __future__ import annotations

from selflearn.agents.lecture_outline import extract_lecture_outline


def test_extract_sections_from_h2_h3() -> None:
    """h2 / h3 标题都被抽到 sections。"""
    html = """
    <h2>核心概念</h2>
    <p>正文</p>
    <h3>子概念</h3>
    <p>子正文</p>
    """
    outline = extract_lecture_outline(html)
    assert outline["sections"] == ["核心概念", "子概念"]
    assert outline["callouts"] == []
    assert outline["examples"] == []


def test_extract_callouts() -> None:
    """callout 块抽到 callouts。"""
    html = """
    <p>上文</p>
    <div class="callout">缩放因子是 √d_k</div>
    <p>下文</p>
    """
    outline = extract_lecture_outline(html)
    assert outline["callouts"] == ["缩放因子是 √d_k"]


def test_extract_examples() -> None:
    """example 块抽到 examples。"""
    html = """
    <div class="example">d_model=512, d_k=64 时</div>
    """
    outline = extract_lecture_outline(html)
    assert outline["examples"] == ["d_model=512, d_k=64 时"]


def test_strip_nested_tags() -> None:
    """嵌套 HTML 标签被剥除（保留纯文本）。"""
    html = '<div class="callout"><strong>关键</strong> 缩放是 <code>√d_k</code></div>'
    outline = extract_lecture_outline(html)
    assert outline["callouts"] == ["关键 缩放是 √d_k"]


def test_empty_html_returns_empty_dict() -> None:
    """空 lecture_html 返回空字典。"""
    outline = extract_lecture_outline("")
    assert outline == {"sections": [], "callouts": [], "examples": []}


def test_full_real_world_html() -> None:
    """完整讲义样例覆盖三类抽取。"""
    html = """
<h2>核心概念</h2>
<p>Self-attention 通过 query 和 key 内积...</p>
<div class="callout">缩放因子是 √d_k</div>
<p>公式：$softmax(QK^T/√d_k)$</p>
<h3>例子</h3>
<div class="example">d_model=512, d_k=64</div>
"""
    outline = extract_lecture_outline(html)
    assert outline["sections"] == ["核心概念", "例子"]
    assert outline["callouts"] == ["缩放因子是 √d_k"]
    assert outline["examples"] == ["d_model=512, d_k=64"]
```

- [ ] **Step 2: 跑测试验证 fail**

```bash
cd backend && uv run pytest tests/unit/test_lecture_outline.py -v -p no:warnings 2>&1 | tail -15
```

Expected: 6 个测试都 FAIL（`ModuleNotFoundError: No module named 'selflearn.agents.lecture_outline'`）。

- [ ] **Step 3: 实现 extract_lecture_outline**

创建 `backend/src/selflearn/agents/lecture_outline.py`：

```python
"""lecture_outline: 从 lecture_html 提取结构化纲要供 exercise LLM 引用。"""
from __future__ import annotations

import re

_OUTLINE_RE_SECTION = re.compile(r"<h[23][^>]*>(.*?)</h[23]>", re.DOTALL)
_OUTLINE_RE_CALLOUT = re.compile(r'<div class="callout"[^>]*>(.*?)</div>', re.DOTALL)
_OUTLINE_RE_EXAMPLE = re.compile(r'<div class="example"[^>]*>(.*?)</div>', re.DOTALL)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


def _strip_tags(html_fragment: str) -> str:
    """去掉 HTML 标签 + 收尾空白。"""
    return _TAG_STRIP_RE.sub("", html_fragment).strip()


def extract_lecture_outline(lecture_html: str) -> dict[str, list[str]]:
    """从 lecture_html 提取结构化纲要，供 exercise LLM 在 explanation 里引用。

    Returns:
        {
            "sections": ["核心概念：self-attention", ...],  # h2/h3 标题
            "callouts": ["缩放因子是 √d_k...", ...],       # callout 块文本
            "examples": ["d_model=512 时...", ...],         # example 块文本
        }
    """
    return {
        "sections": [_strip_tags(m) for m in _OUTLINE_RE_SECTION.findall(lecture_html)],
        "callouts": [_strip_tags(m) for m in _OUTLINE_RE_CALLOUT.findall(lecture_html)],
        "examples": [_strip_tags(m) for m in _OUTLINE_RE_EXAMPLE.findall(lecture_html)],
    }
```

- [ ] **Step 4: 跑测试验证 pass**

```bash
cd backend && uv run pytest tests/unit/test_lecture_outline.py -v -p no:warnings 2>&1 | tail -15
```

Expected: 6 个测试全 PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/src/selflearn/agents/lecture_outline.py backend/tests/unit/test_lecture_outline.py
git commit -m "feat(agent): extract_lecture_outline 工具函数（抽 sections/callouts/examples）+ 单测"
```

---

### Task 6: 重写 skill.lecture.generate SKILL.md

**Files:**
- Modify: `backend/skills/skill.lecture.generate/SKILL.md`（从占位改为真实 prompt）

**Interfaces:**
- Consumes: 现有的 P5 skill loader（已能解析 frontmatter）
- Produces: 7 字段 SKILL.md frontmatter（含 `mcp_prefetch: [tool.get_kp, tool.get_recent_scores]`）；body 改为"只生成知识点讲解"，明确禁止输出题目答案

- [ ] **Step 1: 读现有 SKILL.md**

```bash
cat backend/skills/skill.lecture.generate/SKILL.md
```

Expected: 看到 23 行占位 frontmatter + body（output_schema: null，body 写"本 Skill 是预留占位"）。

- [ ] **Step 2: 整文件重写**

用 Write 工具**完整覆盖** `backend/skills/skill.lecture.generate/SKILL.md`：

```markdown
---
name: skill.lecture.generate
description: "Use when generating HTML lecture content for a knowledge point. Outputs sanitized HTML using white-list tags + pre-defined classes + KaTeX math. Length 800-1500 chars of text (HTML may be longer due to formula)."
output_schema: null
mcp_prefetch:
  - tool.get_kp
  - tool.get_recent_scores
mcp_tool_use:
  - tool.lint_html
max_retries: 1
---

# Skill: 讲义生成

## 任务
为给定知识点生成 HTML **知识点讲解**（800-1500 字），不含题目答案解释。答案解释由 skill.exercise.generate 在生成题目时一并产出（在 explanation 字段里引用讲义内容）。

## 输出范围
**只讲知识点本身**：
- 核心概念定义
- 关键细节、原理、推导
- 类比、例子
- 总结

**不要输出**：
- 任何"题目 N 答案" / "针对本题" / "本题考察"等针对题目的内容
- 习题相关提示（这些在 exercise skill 里管）

## 输出格式
**直接输出 HTML 字符串**（不要包 JSON，不要 markdown fence）。

## 允许的 HTML 标签
h2, h3, p, ul, ol, li, strong, em, code, pre, blockquote, div, span

## 允许的 class（限以下 4 种）
- callout（关键提示）
- formula（公式块）
- example（举例）
- katex（KaTeX 渲染节点，前端自动包裹）

## 公式
行内：`$...$`
块级：用 `<p class="formula">$$...$$</p>` 包裹

## 结构建议
1. `<h2>` 一级概念（1-2 段）
2. 关键细节用 `<div class="callout">...</div>` 强调
3. 1-2 个 `<div class="example">...</div>` 给具体例子
4. 收尾用一段总结
5. **不要**追加题目答案区块

## 输入（来自 prefetch）
- tool.get_kp → {title, description, difficulty, prerequisites}
- tool.get_recent_scores → 最近 3 次得分（用于调整讲解深度）
  - 全 ≥0.8：可深入讲公式推导
  - 全 <0.5：用大量 example
  - 混合：基础概念 + 1-2 个 example

## 严禁
- 任何 `<script>` / `<style>` / `<iframe>` / `<img>` / `<video>` / `<svg>`
- 任何 `onclick` / `onerror` / `onload` 等事件属性
- 任何 `href` / `src` 外部 URL
- 任何 `<h1>`（讲义嵌入已有页面，h1 属于宿主）
- 任何 `style="..."` 内联样式
- 不要在 HTML 前后加 ```json fence 或解释文字
- 不要包 JSON（直接输出 HTML 字符串）
- 不要追加题目答案解释（那是 exercise skill 的职责）

## 示例（仅作格式参考）
<h2>核心概念</h2>
<p>Self-attention 通过计算 query 与 key 的相似度...</p>
<div class="callout">缩放因子是 √d_k，防止方差爆炸</div>
<p>公式：$softmax(\frac{QK^T}{\sqrt{d_k}})$</p>
<div class="example">例：d_model=512, d_k=64 时...</div>
```

- [ ] **Step 3: 验证 Skill loader 能解析**

```bash
cd backend && python -c "
from selflearn.skills.library import _skill_library, load_all
load_all()
sk = _skill_library['skill.lecture.generate']
print('frontmatter:', sk.get('description'))
print('prefetch:', sk.get('mcp_prefetch'))
print('body head:', sk.get('body', '')[:80])
"
```

Expected: 3 行输出：
- `frontmatter: Use when generating HTML lecture content for a knowledge point...`
- `prefetch: ['tool.get_kp', 'tool.get_recent_scores']`
- `body head: # Skill: 讲义生成...`

- [ ] **Step 4: 验证 worker 启动能识别新 SKILL**

读 `backend/src/selflearn/main.py` 的 `expected_skills` 列表，确认 `"skill.lecture.generate"` 已存在（已存在，无需改 main.py）。

- [ ] **Step 5: Commit**

```bash
git add backend/skills/skill.lecture.generate/SKILL.md
git commit -m "feat(skill): skill.lecture.generate 重写为纯讲解 prompt（禁输出题目答案）"
```

---

### Task 7: 改 skill.exercise.generate SKILL.md + Director chain 注入 outline

**Files:**
- Modify: `backend/skills/skill.exercise.generate/SKILL.md`（prefetch 去 `tool.get_kp`；explanation 强制引用 lecture_outline）
- Modify: `backend/src/selflearn/agents/director.py`（lecture 后跑 `_extract_lecture_outline`，注入 exercise env）
- Create: `backend/tests/unit/test_exercise_skill_outline.py`

**Interfaces:**
- Consumes: Task 5 的 `extract_lecture_outline` 函数；Task 6 的 lecture SKILL.md
- Produces:
  - `director.run_director_chain(env, agent, review)` 在 lecture 后跑 outline 提取；exercise 的 `env_ex.payload` 含 `lecture_outline` 字段
  - exercise SKILL.md 描述明确要求 explanation 首句引用 lecture_outline

- [ ] **Step 1: 写 failing test（Director chain 注入 outline）**

创建 `backend/tests/unit/test_exercise_skill_outline.py`：

```python
"""Director chain 注入 lecture_outline 到 exercise env + exercise SKILL.md 引用要求。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.agents.director import run_director_chain


@pytest.mark.asyncio
async def test_director_chain_injects_lecture_outline_into_exercise_env() -> None:
    """lecture 跑完后，exercise 收到的 env.payload 应含 lecture_outline。"""
    # mock lecture LLM 输出（已 lint 后的 HTML，含 h2 + callout + example）
    lecture_html = (
        "<h2>核心概念</h2>"
        "<p>Self-attention 通过 query-key 内积...</p>"
        '<div class="callout">缩放因子是 √d_k</div>'
        '<div class="example">d_model=512, d_k=64 时</div>'
    )
    exercises = [
        {
            "exercise_type": "single_choice",
            "prompt": "缩放因子是？",
            "options": ["√d_k", "d_k", "d_model", "1"],
            "correct_answer": "√d_k",
            "explanation": "如讲义中所言...",
            "difficulty": 2,
            "score": 1.5,
        }
    ]

    # mock agent：lecture + exercise 两次调用
    agent = MagicMock()
    agent.mcp = MagicMock()
    agent.mcp.call = AsyncMock(side_effect=[
        # get_active_node
        {"ok": True, "node_id": "n1", "kp_id": "k1"},
        # get_kp
        {"ok": True, "kp_id": "k1", "title": "self-attention"},
        # get_recent_scores
        [],
        # tool.lint_html (review_lecture)
        {"cleaned": lecture_html, "is_empty": False},
        # create_level
        {"ok": True, "level_id": "l1"},
        # bulk_create_exercises
        {"ok": True, "exercise_ids": ["e1"]},
    ])
    agent.run = AsyncMock(side_effect=[lecture_html, exercises])

    review = MagicMock()
    review.review_lecture = AsyncMock(return_value=MagicMock(verdict="passed", issues=[]))
    review.review_exercise_business = AsyncMock(return_value=MagicMock(verdict="passed", issues=[]))
    review.review_exercise_llm = AsyncMock(return_value=MagicMock(
        verdict="passed", score=1.0, suggestions=[], issues=[],
    ))

    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="test", id="t"),
        target=ActorRef(type="skill", id="skill.director.start"),
        payload={"student_id": "s1", "node_id": "n1"},
    )

    await run_director_chain(env, agent, review)

    # 关键断言：agent.run 第二次调用（exercise）的 env 含 lecture_outline
    assert agent.run.call_count == 2
    exercise_env: Envelope = agent.run.call_args_list[1].args[1]
    assert "lecture_outline" in exercise_env.payload
    outline = exercise_env.payload["lecture_outline"]
    assert "核心概念" in outline["sections"]
    assert "缩放因子是 √d_k" in outline["callouts"]
    assert any("d_model=512" in e for e in outline["examples"])


def test_exercise_skill_md_requires_explanation_reference_lecture_outline() -> None:
    """exercise SKILL.md 必须明确要求 explanation 引用 lecture_outline。"""
    skill_path = Path("backend/skills/skill.exercise.generate/SKILL.md")
    text = skill_path.read_text(encoding="utf-8")
    # 必须显式提到 lecture_outline
    assert "lecture_outline" in text
    # 必须明确要求 explanation 引用
    assert re.search(r"explanation.*引用.*lecture_outline", text, re.DOTALL) is not None
    # 必须说明 prefetch 不含 tool.get_kp
    assert "tool.get_kp" not in text
```

- [ ] **Step 2: 跑测试验证 fail**

```bash
cd backend && uv run pytest tests/unit/test_exercise_skill_outline.py -v -p no:warnings 2>&1 | tail -20
```

Expected: 两个测试都 FAIL（director.py 还没注入；exercise SKILL.md 还没改）。

- [ ] **Step 3: 改 director.py 注入 outline**

读 `backend/src/selflearn/agents/director.py`，定位：
- import 段加入 `from selflearn.agents.lecture_outline import extract_lecture_outline`
- 在 `# 4. lecture` 块（line 64-69 附近）后插入：

```python
    # 4.5 提取讲义纲要，注入到 exercise env（让 exercise 的 explanation 引用讲义内容）
    lecture_outline = extract_lecture_outline(lecture_html)
```

- 在 `# 6. exercise 0-2 轮` 块的 `payload={...}` 字典中加 `"lecture_outline": lecture_outline,`（在 `"revision_suggestions": suggestions,` 之后）

- [ ] **Step 4: 改 exercise SKILL.md**

读 `backend/skills/skill.exercise.generate/SKILL.md` 现有内容。整文件覆盖：

```markdown
---
name: skill.exercise.generate
description: "Use when generating a batch of 2-4 exercises for a knowledge point. Inputs are kp_title, difficulty, lecture_outline (讲义纲要，用于 explanation 引用), optional revision_suggestions."
output_schema: schemas/exercise.schema.json
mcp_prefetch:
  - tool.get_recent_scores
  # lecture_outline 不通过 prefetch 走 —— 它在 env.payload 里（director.py 注入）
mcp_tool_use:
  - tool.lint_json
max_retries: 1
---

# 习题生成器

## 任务
为给定知识点出一组 2-4 道考察题。**每道题的 explanation 字段必须显式引用 lecture_outline 中的内容**（让讲义与答案解释互为补充，学生做完题看 explanation 时能直接串回讲义）。

## 输入（来自 prefetch + env.payload）
- tool.get_recent_scores → 最近 3 次得分
- env.payload.lecture_outline → 讲义结构化纲要：
  ```json
  {
    "sections": ["核心概念：self-attention", "..."],
    "callouts": ["缩放因子是 √d_k，防止方差爆炸"],
    "examples": ["d_model=512, d_k=64 时..."]
  }
  ```
- env.payload.kp_title → 知识点标题
- env.payload.difficulty → easy / medium / hard
- env.payload.revision_suggestions → 第二轮 review LLM 给的修改意见（仅 revision 1 时存在）

## explanation 字段强制要求
每道题的 explanation 必须：
1. **首句引用 lecture_outline 中的某个 section / callout / example**（用"如讲义『XXX』所言：..." 或 "讲义中提到：..." 等显式引用形式）
2. 解释为什么正确答案是这个（不是机械重复题干）
3. 简要指出其他选项错在哪（如果是 single_choice）

## 示例
```json
[
  {
    "exercise_type": "single_choice",
    "prompt": "Transformer 中 self-attention 缩放因子是？",
    "options": ["√d_k", "d_k", "d_model", "1"],
    "correct_answer": "√d_k",
    "explanation": "如讲义『关键细节』中所言：缩放因子是 √d_k，目的是防止 QK^T 方差爆炸。其他选项错在：d_k 是未缩放的，会导致 softmax 进入饱和区；d_model 是模型维度，跟缩放无关；1 是无缩放，效果等同于 d_k。",
    "difficulty": 2,
    "score": 1.5
  }
]
```

## 严格输出格式
- **顶层必须是 JSON array（列表）**
- 每道题必填 7 字段：exercise_type / prompt / options / correct_answer / explanation / difficulty / score
- exercise_type 枚举: single_choice | fill_blank | short_answer | code
- prompt ≥ 5 字符
- single_choice: options 长度 ≥ 2，correct_answer ∈ options
- difficulty: 1 | 2 | 3
- score: 0.5 - 3.0
- **explanation ≥ 30 字符**（避免 LLM 输出 "对，就是这个" 这种空洞答案）

## 难度梯度
- easy: 概念辨析
- medium: 应用
- hard: 综合

## 注意
- 不要输出 reasoning 过程
- 不要在 JSON 前后加解释文字
- 收到 revision_suggestions 时按意见改
```

- [ ] **Step 5: 跑测试验证 pass**

```bash
cd backend && uv run pytest tests/unit/test_exercise_skill_outline.py -v -p no:warnings 2>&1 | tail -20
```

Expected: 2 个测试全 PASS。

- [ ] **Step 6: 跑现有 director 测试确认无回归**

```bash
cd backend && uv run pytest tests/unit/test_director_chain.py tests/unit/test_director_retry.py -v -p no:warnings 2>&1 | tail -30
```

Expected: 全 PASS（无回归；改的是新增字段不影响既有断言）。

- [ ] **Step 7: Commit**

```bash
git add backend/skills/skill.exercise.generate/SKILL.md backend/src/selflearn/agents/director.py backend/tests/unit/test_exercise_skill_outline.py
git commit -m "feat(agent): Director chain 提取 lecture_outline 注入 exercise env + exercise SKILL.md 加 lecture_outline 引用要求"
```

---

## Phase 3 — 前端渲染

### Task 8: LecturePane 重写 + lecture.css + KaTeX 懒加载 + types.ts

**Files:**
- Modify: `frontend/src/api/types.ts`（`LevelDetail` 加 `lecture_html`）
- Modify: `frontend/src/panes/LecturePane.tsx`（重写渲染逻辑 + KaTeX 懒加载）
- Create: `frontend/src/styles/lecture.css`（讲义主题样式）
- Modify: `frontend/package.json`（加 `katex` 依赖）

**Interfaces:**
- Consumes: Task 3 的 `LevelDetailResponse.lecture_html` API 输出
- Produces:
  - `LevelDetail.lecture_html: string | null` 类型
  - `LecturePane` 接受 `lecture_html`，NULL 显示占位；非空用 `dangerouslySetInnerHTML` + KaTeX auto-render
  - `lecture.css` 主题样式

- [ ] **Step 1: 改 types.ts**

读 `frontend/src/api/types.ts` 现有 `LevelDetail` 接口。在 `exercises: ExerciseResponse[];` 后加：

```typescript
  lecture_html: string | null;  // NULL 时显示"该关卡尚无讲义"
```

- [ ] **Step 2: 装 katex 依赖**

```bash
cd frontend && npm install katex@^0.16.11
```

Expected: 看到 `katex@0.16.x` 加入 dependencies。

- [ ] **Step 3: 改写 LecturePane.tsx**

读 `frontend/src/panes/LecturePane.tsx` 现有 21 行占位实现。整文件覆盖：

```tsx
import { useEffect, useState } from 'react';
import { getLevel } from '../api/level';
import '../styles/lecture.css';

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

  // KaTeX 懒加载：只在 lecture_html 非空时动态 import
  useEffect(() => {
    if (!state.loaded || !state.html) return;
    Promise.all([
      import('katex/dist/katex.min.css'),
      import('katex'),
      import('katex/dist/contrib/auto-render.min.js'),
    ]).then(([, , autoRenderMod]) => {
      const autoRender = (autoRenderMod as any).default;
      const root = document.querySelector('.lecture') as HTMLElement | null;
      if (root) {
        autoRender.render(root, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$', right: '$', display: false },
          ],
          throwOnError: false,
        });
      }
    });
  }, [state.loaded, state.html]);

  // 加载中
  if (!state.loaded) {
    return <div style={{ padding: 16, height: '100%', overflow: 'auto' }}>加载讲义...</div>;
  }

  // 没讲义（旧关卡 / 生成失败）
  if (!state.html) {
    return (
      <div
        style={{
          padding: 16,
          color: '#6B6B70',
          fontFamily: 'HedvigLettersSerif, serif',
        }}
      >
        该关卡尚无讲义，请重新启动关卡
      </div>
    );
  }

  // 渲染讲义（依赖后端 nh3 白名单清洗，不在前端二次清洗）
  return (
    <div
      className="lecture"
      style={{
        padding: 16,
        height: '100%',
        overflow: 'auto',
        fontFamily: 'HedvigLettersSerif, serif',
      }}
      dangerouslySetInnerHTML={{ __html: state.html }}
    />
  );
}
```

- [ ] **Step 4: 新建 lecture.css**

创建 `frontend/src/styles/lecture.css`：

```css
/* 讲义样式（UKIYO × Notion 主题） */
.lecture {
  background: #FBF7EC;        /* 米黄底（比 --paper 略深） */
  font-family: HedvigLettersSerif, "STKaiti", "KaiTi", serif;
  color: #1A1A1A;
  line-height: 1.7;
}
.lecture h2 {
  color: #1B3B6F;             /* 靛蓝（= --indigo） */
  font-family: "STSong", "SimSun", "Times New Roman", serif;
  border-bottom: 1px solid rgba(27, 59, 111, 0.15);
  padding-bottom: 4px;
  margin-top: 24px;
}
.lecture h3 {
  color: #1B3B6F;
  font-family: "STSong", "SimSun", "Times New Roman", serif;
  margin-top: 16px;
}
.lecture p {
  margin: 12px 0;
}
.lecture ul, .lecture ol {
  padding-left: 24px;
}
.lecture code {
  font-family: "SF Mono", Consolas, monospace;
  background: rgba(27, 59, 111, 0.05);
  padding: 1px 4px;
  border-radius: 2px;
}
.lecture pre {
  background: #FFF;
  border: 1px solid rgba(27, 59, 111, 0.15);
  padding: 8px 12px;
  overflow-x: auto;
}
.lecture .callout {
  border-left: 4px solid #BC4749;  /* 朱红（= --vermilion） */
  background: rgba(188, 71, 73, 0.06);
  padding: 8px 12px;
  margin: 12px 0;
  border-radius: 0 4px 4px 0;
}
.lecture .formula {
  background: #FFF;
  border: 1px solid rgba(27, 59, 111, 0.15);
  padding: 12px;
  margin: 12px 0;
  font-family: "SF Mono", Consolas, monospace;
  text-align: center;
  overflow-x: auto;
}
.lecture .example {
  background: rgba(27, 59, 111, 0.04);
  border-left: 2px solid rgba(27, 59, 111, 0.3);
  padding: 8px 12px;
  margin: 12px 0;
  font-family: "STKaiti", "KaiTi", serif;
}
.lecture blockquote {
  border-left: 3px solid rgba(27, 59, 111, 0.3);
  margin: 12px 0;
  padding-left: 12px;
  color: #6B6B70;
  font-style: italic;
}
```

- [ ] **Step 5: 验证 TypeScript 编译**

```bash
cd frontend && npm run typecheck
```

Expected: 输出 `tsc --noEmit` 成功（exit code 0），无错误。

- [ ] **Step 6: 验证前端构建**

```bash
cd frontend && npm run build
```

Expected: `vite build` 成功生成 `dist/`，KaTeX 包应在独立 chunk 中（可用 `ls dist/assets | grep katex` 验证）。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/panes/LecturePane.tsx frontend/src/styles/lecture.css frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): LecturePane 渲染 lecture_html + KaTeX 懒加载 + lecture.css"
```

---

## Phase 4 — 回归

### Task 9: 端到端 + smoke + 3 节点实测

**Files:**
- Modify: `backend/tests/integration/test_director_e2e.py`（加 lecture_outline 断言）
- Modify: 容器内 DB（无文件改动；只验数据）

**Interfaces:**
- Consumes: Task 1-8 全部产出
- Produces: 完整回归通过 + 3 个不同节点实测验证 lecture_html 写入 + explanation 引用 outline

- [ ] **Step 1: 加端到端测试断言**

读 `backend/tests/integration/test_director_e2e.py`，找到验证 lecture_html 写入 DB 的位置（如已有相关断言；如没有就加）。

加一个新测试：

```python
@pytest.mark.asyncio
async def test_director_e2e_lecture_outline_explanation_aligned() -> None:
    """端到端：lecture_html 写入 + lecture_outline 注入 + exercise explanation 引用 outline。"""
    # 此测试需要真 DB（testcontainers 或 dev DB），跑前确保 alembic upgrade head
    # 详细步骤见原 test_director_e2e.py 的 fixture 设置
    ...
```

（具体实现参考 `test_director_e2e.py` 现有 fixture 风格，复用 session / node setup）

- [ ] **Step 2: 跑全套单元测试**

```bash
cd backend && uv run pytest -p no:warnings 2>&1 | tail -10
```

Expected: `XXX passed in Y.YYs`（XXX ≥ 161，新增 11 个 test，无回归）。

- [ ] **Step 3: 跑 mypy 严格模式**

```bash
cd backend && mypy src/selflearn 2>&1 | tail -20
```

Expected: `Success: no issues found in N source files` 或只显示原有 `misc / no-any-return` 已 disabled 的提示。

- [ ] **Step 4: 跑后端 smoke**

```bash
cd backend && bash scripts/smoke_mvp.sh 2>&1 | tail -15
```

Expected: `8/8 PASS` 或 `OK`（smoke 不涉及 lecture_html 字段，应该全过）。

- [ ] **Step 5: 重建 + 重启后端容器**

```bash
cd backend && HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 docker compose build gateway worker
cd backend && docker compose up -d --force-recreate gateway worker
```

Expected: BUILD_EXIT=0，UP_EXIT=0，`selflearn-worker Started`。

- [ ] **Step 6: 容器内端到端触发 3 个不同节点**

```bash
# 用真实 student_id（CLAUDE.md 默认）：86820161-b0f0-455f-91b4-a69e49445bdf
# 节点 id 从 DB 取（前面 task 260 用过 92c1868b / 6eebd2d9 / 9989ce0f 三个）
for NODE in 92c1868b-d007-4379-9d18-18305f00ad60 6eebd2d9-7037-47e8-8948-db6b6b12f9a5 9989ce0f-...; do
  curl -s -X POST -H "Content-Type: application/json" \
    -d "{\"student_id\":\"86820161-b0f0-455f-91b4-a69e49445bdf\",\"node_id\":\"$NODE\"}" \
    http://localhost:8000/api/level/start
  echo
done
```

Expected: 3 次返回都含 `trace_id`，worker 处理完成后 SSE COMPLETED。

- [ ] **Step 7: DB 验证 lecture_html + outline 引用**

```bash
docker exec selflearn-postgres psql -U selflearn -d selflearn -c "
SELECT
  l.level_id,
  l.node_id,
  length(l.lecture_html) AS html_len,
  e.explanation
FROM levels l
JOIN exercises e ON e.level_id = l.level_id
WHERE l.created_at > NOW() - INTERVAL '10 minutes'
ORDER BY l.created_at DESC
LIMIT 9;
"
```

Expected: 3 个 level × 3 个 exercise = 9 行；`html_len > 100`（讲义非空）；`explanation` 长度 ≥ 30 字；至少 1 行的 explanation 首句包含 lecture 的某个 callout / section 文本片段（如 "缩放因子" 或 "self-attention"）。

- [ ] **Step 8: 前端手工验证**

打开浏览器 `http://localhost:5174`，在 TreasureMap 上点 3 个节点：
- 每个节点的 LecturePane 应显示讲义（米黄底 + 靛蓝标题 + 朱红 callout）
- 公式应被 KaTeX 渲染（行内 + 块级）
- 切换节点 → 讲义内容应改变

- [ ] **Step 9: Commit（如有 e2e 测试改动）**

```bash
git add backend/tests/integration/test_director_e2e.py
git commit -m "test(e2e): director chain lecture_outline 注入 + explanation 引用 outline"
```

（如该测试在 Step 1 已 commit，本步可跳过）

- [ ] **Step 10: 更新 SDD ledger**

读 `backend/.superpowers/sdd/progress.md`，在末尾追加：

```markdown
## Task 261: 讲义 HTML（lecture_html）落地
- Status: DONE
- 9 个子任务（T1-T9）：data layer → director chain → 前端 → 回归
- Commits: <填入实际 commit hashes>
- 验证:
  - 3 个不同节点触发 /start → DB 里 level.lecture_html 非空 + exercise.explanation ≥ 30 字 + 首句引用 lecture_outline
  - pytest 161+ passed
  - mypy clean
  - 前端 LecturePane 渲染讲义 + KaTeX 公式
```

然后：

```bash
git add backend/.superpowers/sdd/progress.md
git commit -m "docs(sdd): 记录 Task 261 讲义 HTML 落地完成"
```

---

## 自审 Checklist

执行完成后逐项核对：

- [ ] `git log --oneline | head -15` 看到 9+ 个新 commit（每个 task 至少 1 个）
- [ ] `cd backend && uv run pytest -p no:warnings` 全 PASS（161+ 个）
- [ ] `cd backend && mypy src/selflearn` clean
- [ ] `cd backend && bash scripts/smoke_mvp.sh` 8/8 PASS
- [ ] `cd frontend && npm run typecheck && npm run build` 全成功
- [ ] `docker exec selflearn-postgres psql ...` 看到 3 个节点的 lecture_html 非空 + explanation 引用 outline
- [ ] 浏览器手工验证 3 个节点切换讲义内容变化
- [ ] `.superpowers/sdd/progress.md` 已记录 Task 261 DONE

如有任何一项失败，**不要报告"完成"** —— 回到对应 task 修复。