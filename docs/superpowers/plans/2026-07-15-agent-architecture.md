# Agent 架构重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal**: 把 5 个旧 Agent class 重构为 1 个 `LLMAgent` + 1 个 `ReviewStage`，所有行为由 7 个 `SKILL.md` 描述，DB 读写走 1 个 MCP Server（stdio 进程，15 个 tool）。

**Architecture**: 1 个 `LLMAgent` class（mcp 预拉 + LLM + lint + 重试）+ 1 个 `ReviewStage`（业务规则 + LLM 语义审查）+ 1 个 Director 链（lecture → lecture review → exercise 0-2 轮 → exercise review 双步骤 → 写库）+ 1 个 stdio MCP Server（15 个 tool）。改行为 = 改 Skill，不动 Python。

**Tech Stack**: Python 3.12 / FastAPI / SQLAlchemy async / asyncpg / Postgres 16 / mcp (Anthropic 官方) / nh3 / FastMCP / jsonschema / pytest / mypy

**Spec**: `docs/superpowers/specs/2026-07-15-agent-architecture-design.md`

## Global Constraints

（来自 spec 决策记录 § 8 + 全局约束）

- Agent class 数量：1（LLMAgent），ReviewStage 单独 1 个
- Skill 文件：Anthropic SKILL.md 规范，目录形式 `backend/skills/<kebab-name>/SKILL.md`
- MCP Server：1 个独立 stdio 进程，通过 `python -m selflearn.mcp_server` 启动
- MCP tool 总数：15（3 utility + 12 DB）
- DB 读写：不走 SQLAlchemy 直连，统一走 MCP
- LLM tool_use 实时调用：v1 不实现，`mcp_tool_use` 字段保留但默认空 list
- 迁移路径：一次性重构，**不保留 _legacy/**，不留 env var 回退开关
- 行为切换：靠不同 SKILL.md 文件，不在 Python 里写死
- Review：Python 强制 stage，业务规则（5 条 + lint_json）+ LLM 语义审查
- options_length 规则：改为 `options_min >= 2`
- exercise 重试：最多 2 轮（revision 0/1）；业务规则只在第 1 轮跑
- needs_fix 业务 issues：log warn，写库照常
- needs_revision LLM suggestions：喂给第 2 轮 exercise LLM；业务 issues 不喂
- 整链 retry：max_attempts=3（DB 写失败时重生成）
- Skill 数量：7（5 旧 + 2 新）
- 实施顺序：P1 → P2 → P3 → P4 → P5
- 兼容性：HTTP 路由 / SSE 协议 / envelope 协议 / smoke_mvp 8 步 / Playwright 3 测 / 旧 108 pytest 全部保持 PASS
- 范围外：LLM 实时 tool_use / 讲义实际生成 / 图片视频 iframe / 代码沙箱 / Alembic 迁移（讲义 backlog 另 PR）

---

## 实施总览

| Phase | 内容 | 任务数 |
|---|---|---|
| P1 | MCP Server（15 tool + stdio 启动 + 单测） | 7 |
| P2 | Skill 目录迁移（5 旧 + 2 新） | 4 |
| P3 | LLMAgent + ReviewStage | 3 |
| P4 | Director 链 + Retry | 2 |
| P5 | 删旧代码 + 收尾 | 2 |
| **总计** | | **18** |

每个 task 结束条件：1 个 commit + 单测 PASS + 范围内不破其他测试。

---

## Phase 1: MCP Server

### Task 1: MCP Server 骨架（stdio 启动）

**Files:**
- Create: `backend/src/selflearn/mcp_server/__init__.py`
- Create: `backend/src/selflearn/mcp_server/__main__.py`
- Create: `backend/src/selflearn/mcp_server/server.py`
- Modify: `backend/pyproject.toml`（加 mcp + nh3 依赖）
- Test: `backend/tests/unit/mcp/__init__.py` + `backend/tests/unit/mcp/test_server_starts.py`

**Interfaces:**
- Produces: `python -m selflearn.mcp_server` 启动一个 stdio FastMCP server，名称 `"SelfLearn"`

**Step 1**: 加依赖到 `pyproject.toml`：

```toml
[project]
dependencies = [
    # ... 现有依赖
    "mcp>=0.9.0",
    "nh3>=0.2.0",
]
```

运行 `cd backend && uv sync` 验证依赖装上。

**Step 2**: 写失败测试 `backend/tests/unit/mcp/test_server_starts.py`：

```python
"""验证 MCP server 进程能启动并响应 initialize 请求。"""
import asyncio
import json
import subprocess
import sys

import pytest


def test_mcp_server_starts_and_responds_to_initialize():
    """stdio MCP server 启动后能响应 initialize + list_tools。"""
    proc = subprocess.Popen(
        [sys.executable, "-m", "selflearn.mcp_server"],
        cwd="backend",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # 发送 initialize 请求
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1.0"},
            },
        }
        body = json.dumps(init_msg).encode()
        proc.stdin.write(body + b"\n")
        proc.stdin.flush()

        # 读一行响应
        line = proc.stdout.readline()
        response = json.loads(line)
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "SelfLearn"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
```

**Step 3**: 跑测试，**确认失败**：

```bash
cd backend && uv run pytest tests/unit/mcp/test_server_starts.py -v
```

预期：`ModuleNotFoundError: No module named 'selflearn.mcp_server'`

**Step 4**: 实现 MCP server 骨架

`backend/src/selflearn/mcp_server/__init__.py`：
```python
"""MCP server 入口（stdio 进程）。"""
```

`backend/src/selflearn/mcp_server/__main__.py`：
```python
"""python -m selflearn.mcp_server 启动入口。"""
from selflearn.mcp_server.server import main

if __name__ == "__main__":
    main()
```

`backend/src/selflearn/mcp_server/server.py`：
```python
"""SelfLearn MCP server（stdio 进程）。

15 个 tool 分两类：
- utility: fetch_skill / lint_json / lint_html (3 个)
- db: 12 个表操作（见各 task）

启动方式：python -m selflearn.mcp_server
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

# 暂不 import 任何 tool，本 task 只搭骨架
mcp = FastMCP("SelfLearn")


def main() -> None:
    """启动 stdio server。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

**Step 5**: 跑测试，**确认通过**：

```bash
cd backend && uv run pytest tests/unit/mcp/test_server_starts.py -v
```

预期：PASS

**Step 6**: Commit：

```bash
git add backend/src/selflearn/mcp_server/ backend/pyproject.toml backend/tests/unit/mcp/
git commit -m "feat(mcp): P1.1 server 骨架 + stdio 启动"
```

---

### Task 2: 3 个 utility tool（fetch_skill / lint_json / lint_html）

**Files:**
- Create: `backend/src/selflearn/mcp_server/tools/__init__.py`
- Create: `backend/src/selflearn/mcp_server/tools/fetch_skill.py`
- Create: `backend/src/selflearn/mcp_server/tools/lint_json.py`
- Create: `backend/src/selflearn/mcp_server/tools/lint_html.py`
- Modify: `backend/src/selflearn/mcp_server/server.py`（import + register 3 个 tool）
- Test: `backend/tests/unit/mcp/test_fetch_skill.py`
- Test: `backend/tests/unit/mcp/test_lint_json.py`
- Test: `backend/tests/unit/mcp/test_lint_html.py`

**Interfaces:**
- `fetch_skill(skill_id: str) -> dict` — 读 `backend/skills/<id>/SKILL.md`（Phase 2 才存在，本 task 先 hard-fail 友好）
- `lint_json(payload: Any, schema_name: str) -> dict` — jsonschema 校验，{ok, error}
- `lint_html(html: str, allowed_classes: list[str] | None = None) -> dict` — nh3 白名单清洗，{cleaned, is_empty}

**Step 1**: 实现 `lint_json.py`（从 `tools/builtin/lint_json.py` 搬过来改形态）：

```python
"""tool.lint_json: jsonschema 校验。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from mcp.server.fastmcp import Context

SCHEMA_DIR = Path(__file__).resolve().parents[5] / "schemas"
_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def _load_schema(name: str) -> dict[str, Any]:
    if name not in _SCHEMA_CACHE:
        path = SCHEMA_DIR / f"{name}.schema.json"
        _SCHEMA_CACHE[name] = json.loads(path.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE[name]


async def lint_json(payload: Any, schema_name: str) -> dict[str, Any]:
    """校验 LLM 输出的 JSON 是否符合 schema。

    Returns: {"ok": bool, "error": str | None}
    """
    try:
        data = json.loads(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"json_decode_error:{e}"}

    try:
        target = _load_schema(schema_name)
    except FileNotFoundError:
        return {"ok": False, "error": f"schema_not_found:{schema_name}"}

    try:
        jsonschema.validate(instance=data, schema=target)
    except jsonschema.ValidationError as e:
        return {"ok": False, "error": f"schema_violation:{e.message}"}

    return {"ok": True, "error": None}
```

**Step 2**: 写失败测试 `tests/unit/mcp/test_lint_json.py`：

```python
"""tool.lint_json 行为测试。"""
import pytest
from selflearn.mcp_server.tools.lint_json import lint_json


@pytest.mark.asyncio
async def test_lint_json_valid_array():
    """合法 exercise 数组应通过。"""
    payload = [
        {
            "exercise_type": "single_choice",
            "prompt": "题目至少 5 字符",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "解析至少 10 字符以上",
            "difficulty": 1,
            "score": 1.0,
        }
    ]
    result = await lint_json(payload, "exercise")
    assert result["ok"] is True
    assert result["error"] is None


@pytest.mark.asyncio
async def test_lint_json_missing_field():
    """缺 explanation 字段应被拒。"""
    payload = [
        {
            "exercise_type": "single_choice",
            "prompt": "题目至少 5 字符",
            "options": ["A", "B"],
            "correct_answer": "A",
            "difficulty": 1,
            "score": 1.0,
        }
    ]
    result = await lint_json(payload, "exercise")
    assert result["ok"] is False
    assert "explanation" in result["error"]


@pytest.mark.asyncio
async def test_lint_json_schema_not_found():
    """schema 不存在时友好报错。"""
    result = await lint_json([], "nonexistent_schema")
    assert result["ok"] is False
    assert "schema_not_found" in result["error"]
```

**Step 3**: 跑测试 → 期望 PASS（lint_json 已实现）。

**Step 4**: 实现 `lint_html.py`：

```python
"""tool.lint_html: nh3 白名单 + 预定义 class 清洗。"""
from __future__ import annotations

import nh3

ALLOWED_TAGS = {
    "h1", "h2", "h3", "p", "ul", "ol", "li",
    "strong", "em", "code", "pre", "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
    "br", "hr", "span", "div",
}
ALLOWED_CLASSES_DEFAULT = {"callout", "formula", "example", "katex", "katex-display"}


def _attr_filter(allowed_classes: set[str]):
    def _filter(element: str, attr: str, value: str) -> bool:
        if attr == "class":
            return value in allowed_classes
        # 其它属性：th/td 允许 colspan
        if element in ("th", "td") and attr == "colspan":
            return True
        return False
    return _filter


async def lint_html(
    html: str,
    allowed_classes: list[str] | None = None,
) -> dict[str, Any]:
    """白名单清洗 HTML，返回 {cleaned, is_empty}。

    is_empty: 清洗后无可见文本内容
    """
    classes = set(allowed_classes) if allowed_classes else ALLOWED_CLASSES_DEFAULT
    cleaned = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes={"code": ["class"], "pre": ["class"], "span": ["class"], "div": ["class"], "th": ["colspan"], "td": ["colspan"]},
        attribute_filter=_attr_filter(classes),
    )
    # not_empty: 去除标签后看是否有非空白文本
    import re
    text_only = re.sub(r"<[^>]+>", "", cleaned).strip()
    return {
        "cleaned": cleaned,
        "is_empty": len(text_only) == 0,
    }
```

**Step 5**: 写失败测试 `tests/unit/mcp/test_lint_html.py`：

```python
"""tool.lint_html 行为测试。"""
import pytest
from selflearn.mcp_server.tools.lint_html import lint_html


@pytest.mark.asyncio
async def test_lint_html_clean_allowed_tags():
    """白名单标签应保留。"""
    html = "<h1>标题</h1><p>段落 <strong>强调</strong></p>"
    result = await lint_html(html)
    assert "<h1>" in result["cleaned"]
    assert "<strong>" in result["cleaned"]
    assert result["is_empty"] is False


@pytest.mark.asyncio
async def test_lint_html_strip_script():
    """<script> 应被剥掉。"""
    html = "<h1>ok</h1><script>alert(1)</script>"
    result = await lint_html(html)
    assert "<script>" not in result["cleaned"]
    assert "alert" not in result["cleaned"]


@pytest.mark.asyncio
async def test_lint_html_strip_disallowed_class():
    """不在白名单的 class 应被剥掉。"""
    html = '<p class="evil">x</p><p class="callout">y</p>'
    result = await lint_html(html, allowed_classes=["callout"])
    assert "evil" not in result["cleaned"]
    assert "callout" in result["cleaned"]


@pytest.mark.asyncio
async def test_lint_html_katex_preserved():
    """KaTeX 输出的 span class 应保留。"""
    html = '<span class="katex"><span class="katex-html">x</span></span>'
    result = await lint_html(html)
    assert "katex" in result["cleaned"]


@pytest.mark.asyncio
async def test_lint_html_is_empty():
    """空字符串应 is_empty=True。"""
    result = await lint_html("")
    assert result["is_empty"] is True
```

**Step 6**: 跑测试 → 期望 PASS。

**Step 7**: 实现 `fetch_skill.py`（占位版本，Phase 2 才接真实 SKILL.md 路径）：

```python
"""tool.fetch_skill: 读 SKILL.md。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter


SKILLS_DIR = Path(__file__).resolve().parents[4] / "skills"  # backend/skills/


async def fetch_skill(skill_id: str) -> dict[str, Any]:
    """读 backend/skills/<skill_id>/SKILL.md。"""
    path = SKILLS_DIR / skill_id / "SKILL.md"
    if not path.exists():
        return {
            "ok": False,
            "error": f"skill_not_found:{skill_id}",
            "name": None,
            "description": None,
            "body": None,
            "output_schema": None,
            "mcp_prefetch": [],
            "mcp_tool_use": [],
            "max_retries": 0,
        }
    post = frontmatter.load(path)
    meta = post.metadata
    return {
        "ok": True,
        "error": None,
        "name": str(meta.get("name", skill_id)),
        "description": str(meta.get("description", "")),
        "body": post.content,
        "output_schema": meta.get("output_schema"),
        "mcp_prefetch": list(meta.get("mcp_prefetch", [])),
        "mcp_tool_use": list(meta.get("mcp_tool_use", [])),
        "max_retries": int(meta.get("max_retries", 0)),
    }
```

**Step 8**: 写失败测试 `tests/unit/mcp/test_fetch_skill.py`：

```python
"""tool.fetch_skill 行为测试。"""
import pytest
from selflearn.mcp_server.tools.fetch_skill import fetch_skill


@pytest.mark.asyncio
async def test_fetch_skill_not_found():
    """skill 不存在应友好报错。"""
    result = await fetch_skill("nonexistent.skill.id")
    assert result["ok"] is False
    assert "skill_not_found" in result["error"]


@pytest.mark.asyncio
async def test_fetch_skill_existing(tmp_path):
    """读存在的 skill（用 tmp_path 临时造一个）。"""
    from selflearn.mcp_server.tools import fetch_skill
    # 改 SKILLS_DIR 指向 tmp_path 临时
    original_dir = fetch_skill.SKILLS_DIR
    fetch_skill.SKILLS_DIR = tmp_path
    try:
        skill_dir = tmp_path / "skill.test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: skill.test\n"
            "description: Use when testing.\n"
            "output_schema: schemas/test.schema.json\n"
            "mcp_prefetch:\n  - tool.get_kp\n"
            "mcp_tool_use: []\n"
            "max_retries: 1\n"
            "---\n\n# Body\n"
        )
        result = await fetch_skill("skill.test")
        assert result["ok"] is True
        assert result["name"] == "skill.test"
        assert result["description"] == "Use when testing."
        assert result["output_schema"] == "schemas/test.schema.json"
        assert result["mcp_prefetch"] == ["tool.get_kp"]
        assert result["mcp_tool_use"] == []
        assert result["max_retries"] == 1
    finally:
        fetch_skill.SKILLS_DIR = original_dir
```

**Step 9**: 跑测试 → 期望 PASS。

**Step 10**: 在 `server.py` 注册 3 个 tool（用装饰器方式）：

```python
"""SelfLearn MCP server（stdio 进程）。"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from selflearn.mcp_server.tools.fetch_skill import fetch_skill
from selflearn.mcp_server.tools.lint_json import lint_json
from selflearn.mcp_server.tools.lint_html import lint_html

mcp = FastMCP("SelfLearn")

mcp.add_tool(fetch_skill, name="tool.fetch_skill")
mcp.add_tool(lint_json, name="tool.lint_json")
mcp.add_tool(lint_html, name="tool.lint_html")


def main() -> None:
    """启动 stdio server。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

`backend/src/selflearn/mcp_server/tools/__init__.py`：
```python
"""MCP tool 实现集合。"""
```

**Step 11**: 跑 `tests/unit/mcp/` 全部测试，期望全 PASS。

**Step 12**: Commit：

```bash
git add backend/src/selflearn/mcp_server/ backend/tests/unit/mcp/
git commit -m "feat(mcp): P1.2 utility tools (fetch_skill, lint_json, lint_html)"
```

---

### Task 3: DB tool — get_active_node / get_kp / get_recent_scores

**Files:**
- Create: `backend/src/selflearn/mcp_server/tools/get_active_node.py`
- Create: `backend/src/selflearn/mcp_server/tools/get_kp.py`
- Create: `backend/src/selflearn/mcp_server/tools/get_recent_scores.py`
- Modify: `backend/src/selflearn/mcp_server/server.py`（注册 3 个 tool）
- Test: `backend/tests/unit/mcp/test_get_active_node.py`
- Test: `backend/tests/unit/mcp/test_get_kp.py`
- Test: `backend/tests/unit/mcp/test_get_recent_scores.py`

**Interfaces:**
- `get_active_node(student_id: str) -> dict` — 查第一个 status=active 的 MapNode（含 kp_id, position）
- `get_kp(kp_id: str) -> dict` — 查 KnowledgePoint
- `get_recent_scores(student_id: str, limit: int = 3) -> list[float]` — 最近 N 次 level_completion.score

**Step 1**: 写失败测试 `tests/unit/mcp/test_get_active_node.py`（用真 DB，conftest 提供 fixture）：

```python
"""tool.get_active_node 行为测试。"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.mcp_server.tools.get_active_node import get_active_node


@pytest.mark.asyncio
async def test_get_active_node_returns_active(setup_kp_and_node):
    """有 active 节点时返回。"""
    student_id, kp_id, node_id = setup_kp_and_node
    factory = get_session_factory()
    async with factory() as session:
        # 插入 active node
        session.add(MapNode(
            student_id=student_id, kp_id=kp_id, status="active",
            branch_type="main", position={"x": 30.0, "y": 0.0},
        ))
        await session.commit()

    result = await get_active_node(student_id)
    assert result["kp_id"] == kp_id
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_get_active_node_none_when_no_active(setup_kp_and_node):
    """无 active 节点时返回空 dict + ok=False。"""
    student_id, _, _ = setup_kp_and_node
    result = await get_active_node(student_id)
    assert result["ok"] is False
    assert "no_active_node" in result.get("error", "")
```

`tests/conftest.py` 加 fixture（如果还没有）：

```python
@pytest_asyncio.fixture
async def setup_kp_and_node():
    """插入 1 个 KP + 返回 (student_id, kp_id, node_id)。"""
    from uuid import uuid4
    student_id = str(uuid4())
    kp_id = uuid4()
    factory = get_session_factory()
    async with factory() as session:
        kp = KnowledgePoint(
            kp_id=kp_id, subject="test", title="test_kp",
            description="desc", difficulty=1, prerequisites=[],
        )
        session.add(kp)
        await session.commit()
    yield student_id, kp_id, None
```

**Step 2**: 跑测试 → 期望 FAIL（`ModuleNotFoundError`）。

**Step 3**: 实现 `get_active_node.py`：

```python
"""tool.get_active_node: 查学生当前第一个 active 节点。"""
from __future__ import annotations

from uuid import UUID
from typing import Any

from sqlalchemy import select

from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory


async def get_active_node(student_id: str) -> dict[str, Any]:
    """查 student_id 下第一个 status=active 的 MapNode。

    Returns: {"ok": True, "node_id", "kp_id", "status", "position"} 或
             {"ok": False, "error": "no_active_node"}
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(MapNode)
            .where(MapNode.student_id == student_id, MapNode.status == "active")
            .limit(1)
        )
        node = (await session.execute(stmt)).scalars().first()
        if node is None:
            return {"ok": False, "error": "no_active_node"}
        return {
            "ok": True,
            "node_id": str(node.node_id),
            "kp_id": str(node.kp_id),
            "status": node.status,
            "position": node.position,
        }
```

**Step 4**: 实现 `get_kp.py`：

```python
"""tool.get_kp: 查 KnowledgePoint。"""
from __future__ import annotations

from uuid import UUID
from typing import Any

from sqlalchemy import select

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory


async def get_kp(kp_id: str) -> dict[str, Any]:
    """查 KnowledgePoint。

    Returns: {"ok": True, "kp_id", "subject", "title", "description",
              "difficulty", "prerequisites"} 或 {"ok": False, "error"}
    """
    try:
        kp_uuid = UUID(kp_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{kp_id}"}

    factory = get_session_factory()
    async with factory() as session:
        kp = await session.get(KnowledgePoint, kp_uuid)
        if kp is None:
            return {"ok": False, "error": f"kp_not_found:{kp_id}"}
        return {
            "ok": True,
            "kp_id": str(kp.kp_id),
            "subject": kp.subject,
            "title": kp.title,
            "description": kp.description,
            "difficulty": kp.difficulty,
            "prerequisites": list(kp.prerequisites or []),
        }
```

**Step 5**: 实现 `get_recent_scores.py`：

```python
"""tool.get_recent_scores: 查最近 N 次关卡完成分数。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from selflearn.domain.level_completion import LevelCompletion
from selflearn.infra.db import get_session_factory


async def get_recent_scores(student_id: str, limit: int = 3) -> list[float]:
    """返回 student_id 最近 limit 次 level_completion.score（按 submitted_at DESC）。"""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(LevelCompletion.score)
            .where(LevelCompletion.student_id == student_id)
            .order_by(LevelCompletion.submitted_at.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()
        return [float(s) for s in rows]
```

**Step 6**: 写 `test_get_kp.py` + `test_get_recent_scores.py`：

```python
# test_get_kp.py
@pytest.mark.asyncio
async def test_get_kp_existing(setup_kp_and_node):
    _, kp_id, _ = setup_kp_and_node
    from selflearn.mcp_server.tools.get_kp import get_kp
    result = await get_kp(str(kp_id))
    assert result["ok"] is True
    assert result["title"] == "test_kp"


@pytest.mark.asyncio
async def test_get_kp_invalid_uuid():
    from selflearn.mcp_server.tools.get_kp import get_kp
    result = await get_kp("not-a-uuid")
    assert result["ok"] is False
```

```python
# test_get_recent_scores.py
@pytest.mark.asyncio
async def test_get_recent_scores_empty(setup_kp_and_node):
    student_id, _, _ = setup_kp_and_node
    from selflearn.mcp_server.tools.get_recent_scores import get_recent_scores
    scores = await get_recent_scores(student_id, limit=3)
    assert scores == []
```

**Step 7**: 在 `server.py` 注册 3 个 tool（追加 import + add_tool）。

**Step 8**: 跑全部 mcp 单测 → 期望全 PASS。

**Step 9**: Commit：

```bash
git add backend/src/selflearn/mcp_server/tools/ backend/src/selflearn/mcp_server/server.py backend/tests/unit/mcp/
git commit -m "feat(mcp): P1.3 DB tools 1 (get_active_node, get_kp, get_recent_scores)"
```

---

### Task 4: DB tool — get_profile / create_profile

**Files:**
- Create: `backend/src/selflearn/mcp_server/tools/get_profile.py`
- Create: `backend/src/selflearn/mcp_server/tools/create_profile.py`
- Modify: `backend/src/selflearn/mcp_server/server.py`
- Test: `backend/tests/unit/mcp/test_get_profile.py`
- Test: `backend/tests/unit/mcp/test_create_profile.py`

**Interfaces:**
- `get_profile(student_id: str) -> dict` — 查 Profile 记录
- `create_profile(student_id: str, dimensions: dict, tags: list) -> dict`

**Step 1**: 写测试 `test_get_profile.py`：

```python
@pytest.mark.asyncio
async def test_get_profile_not_found(setup_kp_and_node):
    student_id, _, _ = setup_kp_and_node
    from selflearn.mcp_server.tools.get_profile import get_profile
    result = await get_profile(student_id)
    assert result["ok"] is False
    assert "profile_not_found" in result.get("error", "")


@pytest.mark.asyncio
async def test_get_profile_existing(setup_kp_and_node):
    from datetime import datetime, timezone
    student_id, _, _ = setup_kp_and_node
    factory = get_session_factory()
    async with factory() as session:
        from selflearn.domain.profile import Profile
        session.add(Profile(
            student_id=student_id,
            dimensions={"kb": 0.5, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
            tags=["smoke"],
            last_updated=datetime.now(timezone.utc),
        ))
        await session.commit()
    from selflearn.mcp_server.tools.get_profile import get_profile
    result = await get_profile(student_id)
    assert result["ok"] is True
    assert result["dimensions"]["kb"] == 0.5
    assert result["tags"] == ["smoke"]
```

**Step 2**: 跑测试 → FAIL（ModuleNotFoundError）。

**Step 3**: 实现 `get_profile.py`：

```python
"""tool.get_profile: 查 Profile。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory


async def get_profile(student_id: str) -> dict[str, Any]:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Profile).where(Profile.student_id == student_id).limit(1)
        profile = (await session.execute(stmt)).scalars().first()
        if profile is None:
            return {"ok": False, "error": "profile_not_found"}
        return {
            "ok": True,
            "profile_id": str(profile.profile_id),
            "dimensions": dict(profile.dimensions or {}),
            "tags": list(profile.tags or []),
            "last_updated": profile.last_updated.isoformat() if profile.last_updated else None,
        }
```

**Step 4**: 实现 `create_profile.py`：

```python
"""tool.create_profile: 写 Profile（upsert：存在则覆盖）。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory


async def create_profile(
    student_id: str,
    dimensions: dict,
    tags: list | None = None,
) -> dict[str, Any]:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Profile).where(Profile.student_id == student_id).limit(1)
        existing = (await session.execute(stmt)).scalars().first()
        if existing is not None:
            existing.dimensions = dimensions
            existing.tags = tags or []
            existing.last_updated = datetime.now(timezone.utc)
            await session.commit()
            return {"ok": True, "profile_id": str(existing.profile_id), "updated": True}

        profile = Profile(
            student_id=student_id,
            dimensions=dimensions,
            tags=tags or [],
            last_updated=datetime.now(timezone.utc),
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return {"ok": True, "profile_id": str(profile.profile_id), "updated": False}
```

**Step 5**: 写 `test_create_profile.py`（覆盖 create + update 两种路径）：

```python
@pytest.mark.asyncio
async def test_create_profile_new(setup_kp_and_node):
    student_id, _, _ = setup_kp_and_node
    from selflearn.mcp_server.tools.create_profile import create_profile
    result = await create_profile(
        student_id,
        dimensions={"kb": 0.7},
        tags=["new"],
    )
    assert result["ok"] is True
    assert result["updated"] is False


@pytest.mark.asyncio
async def test_create_profile_update_existing(setup_kp_and_node):
    student_id, _, _ = setup_kp_and_node
    from selflearn.mcp_server.tools.create_profile import create_profile
    await create_profile(student_id, dimensions={"kb": 0.5}, tags=[])
    result = await create_profile(student_id, dimensions={"kb": 0.8}, tags=["upd"])
    assert result["ok"] is True
    assert result["updated"] is True
```

**Step 6**: 注册到 `server.py`。

**Step 7**: 跑测试 → PASS。

**Step 8**: Commit：

```bash
git add backend/src/selflearn/mcp_server/tools/ backend/src/selflearn/mcp_server/server.py backend/tests/unit/mcp/
git commit -m "feat(mcp): P1.4 DB tools 2 (get_profile, create_profile)"
```

---

### Task 5: DB tool — get_existing_nodes / get_kps / create_map_nodes

**Files:**
- Create: `backend/src/selflearn/mcp_server/tools/get_existing_nodes.py`
- Create: `backend/src/selflearn/mcp_server/tools/get_kps.py`
- Create: `backend/src/selflearn/mcp_server/tools/create_map_nodes.py`
- Modify: `backend/src/selflearn/mcp_server/server.py`
- Test: 3 个 test 文件

**Interfaces:**
- `get_existing_nodes(student_id: str) -> list[dict]`
- `get_kps(limit: int = 5) -> list[dict]`
- `create_map_nodes(student_id, kp_id_list, positions) -> list[dict]` — 返回 node_id 列表

**Step 1**: 写 3 个测试文件 + 实现 3 个 tool（实现参考 `plan_agent.py:64-82` 原 SQL 逻辑）。

**Step 2**: `get_existing_nodes.py`：

```python
async def get_existing_nodes(student_id: str) -> list[dict[str, Any]]:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(MapNode).where(MapNode.student_id == student_id)
        nodes = (await session.execute(stmt)).scalars().all()
        return [
            {
                "node_id": str(n.node_id),
                "kp_id": str(n.kp_id),
                "status": n.status,
                "position": n.position,
            }
            for n in nodes
        ]
```

**Step 3**: `get_kps.py`：

```python
async def get_kps(limit: int = 5) -> list[dict[str, Any]]:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(KnowledgePoint).limit(limit)
        kps = (await session.execute(stmt)).scalars().all()
        return [
            {
                "kp_id": str(k.kp_id),
                "title": k.title,
                "description": k.description,
                "difficulty": k.difficulty,
            }
            for k in kps
        ]
```

**Step 4**: `create_map_nodes.py`：

```python
async def create_map_nodes(
    student_id: str,
    kp_id_list: list[str],
    positions: list[dict] | None = None,
) -> dict[str, Any]:
    """批量创建 MapNode。positions 可选（默认两行排列）。"""
    factory = get_session_factory()
    async with factory() as session:
        node_ids = []
        for idx, kp_id in enumerate(kp_id_list):
            if positions and idx < len(positions):
                pos = positions[idx]
            else:
                row = 0 if idx < 3 else 1
                col = idx if idx < 3 else idx - 3
                pos = {"x": float(col * 120 + 30), "y": float(row * 70)}
            try:
                kp_uuid = UUID(kp_id)
            except ValueError:
                return {"ok": False, "error": f"invalid_uuid:{kp_id}"}
            node = MapNode(
                student_id=student_id,
                kp_id=kp_uuid,
                status="active",
                branch_type="main",
                position=pos,
            )
            session.add(node)
            await session.flush()
            node_ids.append(str(node.node_id))
        await session.commit()
        return {"ok": True, "node_ids": node_ids}
```

**Step 5**: 测试 + 注册到 `server.py` + 跑测试 + Commit。

```bash
git commit -m "feat(mcp): P1.5 DB tools 3 (get_existing_nodes, get_kps, create_map_nodes)"
```

---

### Task 6: DB tool — create_level / bulk_create_exercises

**Files:**
- Create: `backend/src/selflearn/mcp_server/tools/create_level.py`
- Create: `backend/src/selflearn/mcp_server/tools/bulk_create_exercises.py`
- Modify: `backend/src/selflearn/mcp_server/server.py`
- Test: 2 个 test 文件

**Interfaces:**
- `create_level(node_id, lecture_html) -> dict` — 返回 {ok, level_id}（lecture_html 透传存到 level.lecture_html）
- `bulk_create_exercises(level_id, exercises) -> dict` — 返回 {ok, exercise_ids}

**Step 1**: 写测试 + 实现（参考 `director_agent.py:118-131` 原 SQL 逻辑）。注意：lecture_html 字段是 spec backlog 中加的（**本 plan 不实现讲义**），但 `create_level` 工具接受 `lecture_html` 参数——传 None 时不写该字段（兼容性）。

**Step 2**: `create_level.py`：

```python
async def create_level(node_id: str, lecture_html: str | None = None) -> dict[str, Any]:
    try:
        node_uuid = UUID(node_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{node_id}"}

    factory = get_session_factory()
    async with factory() as session:
        # SQLAlchemy 列定义在 Phase 5 后才有 lecture_html；本 task 用 getattr 防御性写
        level = Level(node_id=node_uuid, status="generated", form="exercise")
        if lecture_html is not None:
            # 若 levels 表有 lecture_html 列则写；否则忽略
            if hasattr(Level, "lecture_html"):
                setattr(level, "lecture_html", lecture_html)
        session.add(level)
        await session.commit()
        await session.refresh(level)
        return {"ok": True, "level_id": str(level.level_id)}
```

**Step 3**: `bulk_create_exercises.py`：

```python
async def bulk_create_exercises(level_id: str, exercises: list[dict]) -> dict[str, Any]:
    try:
        level_uuid = UUID(level_id)
    except ValueError:
        return {"ok": False, "error": f"invalid_uuid:{level_id}"}

    factory = get_session_factory()
    async with factory() as session:
        ex_ids = []
        for ex in exercises:
            ex_row = Exercise(
                level_id=level_uuid,
                exercise_type=ex["exercise_type"],
                prompt=ex["prompt"],
                options=ex.get("options", []),
                correct_answer=str(ex["correct_answer"]),
                explanation=ex.get("explanation", ""),
                difficulty=int(ex.get("difficulty", 1)),
                score=float(ex.get("score", 1.0)),
            )
            session.add(ex_row)
            await session.flush()
            ex_ids.append(str(ex_row.exercise_id))
        await session.commit()
        return {"ok": True, "exercise_ids": ex_ids}
```

**Step 4**: 测试 + 注册 + Commit：

```bash
git commit -m "feat(mcp): P1.6 DB tools 4 (create_level, bulk_create_exercises)"
```

---

### Task 7: DB tool — update_profile / apply_level_completion + 集成验收

**Files:**
- Create: `backend/src/selflearn/mcp_server/tools/update_profile.py`
- Create: `backend/src/selflearn/mcp_server/tools/apply_level_completion.py`
- Modify: `backend/src/selflearn/mcp_server/server.py`
- Test: 2 个 test 文件 + P1 集成验收

**Interfaces:**
- `update_profile(student_id, deltas: dict) -> dict` — 应用 kb/as delta + 写 profile_snapshot
- `apply_level_completion(level_id, student_id, score, answers) -> dict` — 写 level_completion + level.status=completed

**Step 1**: 实现 `update_profile.py`（参考 `ProfileRepository.apply_delta` + `apply_delta` 写 snapshot）：

```python
async def update_profile(student_id: str, deltas: dict[str, float]) -> dict[str, Any]:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Profile).where(Profile.student_id == student_id).limit(1)
        profile = (await session.execute(stmt)).scalars().first()
        if profile is None:
            return {"ok": False, "error": "profile_not_found"}

        # 应用 delta（clamp 到 [0, 1]）
        new_dims = dict(profile.dimensions or {})
        for k, v in deltas.items():
            cur = float(new_dims.get(k, 0.5))
            new_dims[k] = max(0.0, min(1.0, cur + v))
        profile.dimensions = new_dims
        profile.last_updated = datetime.now(timezone.utc)
        await session.commit()

        # 写 profile_snapshot（如存在表）
        # 注意：profile_snapshots 是手动 CREATE 的（Stage 4 报告遗留），
        # 本 tool 防御性写：表不存在时静默 skip
        if hasattr(selflearn.domain.profile_snapshot, "ProfileSnapshot"):
            from selflearn.domain.profile_snapshot import ProfileSnapshot
            snap = ProfileSnapshot(
                student_id=student_id,
                profile=new_dims,
                trigger="level_completed",
            )
            session.add(snap)
            try:
                await session.commit()
            except Exception:
                await session.rollback()  # 表不存在时静默

        return {"ok": True, "dimensions": new_dims, "snapshot_id": None}
```

**Step 2**: 实现 `apply_level_completion.py`（参考 `level.py:75-115` 逻辑）：

```python
async def apply_level_completion(
    level_id: str, student_id: str, score: float, answers: dict
) -> dict[str, Any]:
    factory = get_session_factory()
    async with factory() as session:
        # 查 level
        try:
            level_uuid = UUID(level_id)
        except ValueError:
            return {"ok": False, "error": f"invalid_uuid:{level_id}"}

        level = await session.get(Level, level_uuid)
        if level is None:
            return {"ok": False, "error": "level_not_found"}

        # 写 completion
        completion = LevelCompletion(
            level_id=level_uuid,
            student_id=student_id,
            score=score,
            duration_seconds=0,
            answers=answers,
            metrics={"items": len(answers)},
        )
        session.add(completion)
        level.status = "completed"
        await session.commit()
        await session.refresh(completion)
        return {"ok": True, "completion_id": str(completion.completion_id), "score": score}
```

**Step 3**: 测试 + 注册。

**Step 4**: P1 集成验收——启动真 stdio MCP server，用真 client 调通所有 15 个 tool：

```bash
# 测试 P1 端到端：stdio server + client
cd backend && uv run python -c "
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(command='uv', args=['run', 'python', '-m', 'selflearn.mcp_server'])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = sorted([t.name for t in tools.tools])
            print('tool count:', len(tool_names))
            for n in tool_names:
                print('  ', n)
            assert len(tool_names) == 15, f'expected 15 tools, got {len(tool_names)}'

asyncio.run(main())
"
```

预期：列出 15 个 tool 名。

**Step 5**: 跑旧测试看是否破坏：

```bash
cd backend && uv run pytest tests/ -x --ignore=tests/unit/mcp -q
```

预期：所有旧测试（除 5 个引用旧 Agent class 的）继续 PASS。被破坏的 5 个：test_exercise_agent.py / test_review_agent.py / test_director_tryexcept.py / test_difficulty_gradient.py / test_scheduler_target_id_routing.py——**这些会在 P5 删旧代码时一起改**。本 task 先记录到 .todo：

```bash
echo "P5: 修复旧测试 (5 个引用旧 Agent class 的)" > BACKLOG_P5.md
```

**Step 6**: Commit：

```bash
git add backend/src/selflearn/mcp_server/tools/ backend/src/selflearn/mcp_server/server.py backend/tests/unit/mcp/ BACKLOG_P5.md
git commit -m "feat(mcp): P1.7 DB tools 5 (update_profile, apply_level_completion) + P1 集成验收"
```

**Phase 1 收尾**：15 个 MCP tool 全部实现 + 单测全 PASS + stdio server 启动验证。

---

## Phase 2: Skill 目录迁移

### Task 8: Skill dataclass 升级 + load_all 改造

**Files:**
- Modify: `backend/src/selflearn/skills/library.py`
- Test: `backend/tests/unit/test_skill_loader.py`

**Interfaces:**
- `Skill` dataclass 新增字段：`mcp_prefetch: list[str]` / `mcp_tool_use: list[str]` / `max_retries: int`
- `load_all()` 从 `backend/docs/skills/*.md` 改为 `backend/skills/*/SKILL.md`

**Step 1**: 写失败测试 `test_skill_loader.py`：

```python
"""Skill loader 行为测试。"""
import pytest
from selflearn.skills.library import load_all, get, Skill


@pytest.fixture
def tmp_skills_dir(tmp_path, monkeypatch):
    from selflearn.skills import library
    monkeypatch.setattr(library, "SKILLS_DIR", tmp_path)
    return tmp_path


def test_load_skill_with_frontmatter(tmp_skills_dir):
    skill_dir = tmp_skills_dir / "skill.test"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: skill.test\n"
        "description: Use when testing.\n"
        "output_schema: schemas/test.json\n"
        "mcp_prefetch:\n  - tool.a\n  - tool.b\n"
        "mcp_tool_use:\n  - tool.c\n"
        "max_retries: 2\n"
        "---\n\n# Body content\n"
    )
    load_all()
    s = get("skill.test")
    assert isinstance(s, Skill)
    assert s.name == "skill.test"
    assert s.mcp_prefetch == ["tool.a", "tool.b"]
    assert s.mcp_tool_use == ["tool.c"]
    assert s.max_retries == 2
    assert "Body content" in s.body


def test_load_skill_missing_name_skipped(tmp_skills_dir, caplog):
    skill_dir = tmp_skills_dir / "skill.bad"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\ndescription: no name\n---\nbody\n")
    load_all()
    with pytest.raises(KeyError):
        get("skill.bad")
```

**Step 2**: 跑测试 → FAIL（`Skill` 没有 mcp_prefetch 字段）。

**Step 3**: 改造 `library.py`：

```python
"""Skill markdown 文档 loader。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter

from selflearn.core.logging import get_logger

log = get_logger("skills")
SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"  # backend/skills/


@dataclass
class Skill:
    name: str
    description: str
    body: str
    output_schema: str | None
    mcp_prefetch: list[str] = field(default_factory=list)
    mcp_tool_use: list[str] = field(default_factory=list)
    max_retries: int = 0


_skill_library: dict[str, Skill] = {}


def load_all(skills_dir: Path | None = None) -> None:
    """进程启动时调一次，从 backend/skills/<id>/SKILL.md 读 Skill。"""
    if skills_dir is None:
        skills_dir = SKILLS_DIR
    _skill_library.clear()
    if not skills_dir.exists():
        log.warning("skills.dir_not_found", path=str(skills_dir))
        return

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        md_path = skill_dir / "SKILL.md"
        if not md_path.exists():
            continue
        post = frontmatter.load(md_path)
        meta: dict[str, Any] = post.metadata
        if "name" not in meta:
            log.warning("skills.skip_missing_name", path=str(md_path))
            continue
        _skill_library[str(meta["name"])] = Skill(
            name=str(meta["name"]),
            description=str(meta.get("description", "")),
            body=post.content,
            output_schema=str(meta["output_schema"]) if "output_schema" in meta else None,
            mcp_prefetch=list(meta.get("mcp_prefetch", [])),
            mcp_tool_use=list(meta.get("mcp_tool_use", [])),
            max_retries=int(meta.get("max_retries", 0)),
        )
    log.info("skills.loaded", count=len(_skill_library))


def get(name: str) -> Skill:
    if name not in _skill_library:
        raise KeyError(f"skill_not_loaded:{name}")
    return _skill_library[name]
```

**Step 4**: 跑测试 → PASS。

**Step 5**: Commit：

```bash
git add backend/src/selflearn/skills/library.py backend/tests/unit/test_skill_loader.py
git commit -m "feat(skills): P2.1 Skill dataclass 升级 + 目录式 SKILL.md 加载"
```

---

### Task 9: 迁移 5 个旧 Skill + 加 frontmatter

**Files:**
- Create: `backend/skills/skill.profile.build/SKILL.md`
- Create: `backend/skills/skill.plan.generate/SKILL.md`
- Create: `backend/skills/skill.exercise.generate/SKILL.md`
- Create: `backend/skills/skill.review.exercise.business/SKILL.md`
- Create: `backend/skills/skill.director.start/SKILL.md`
- Delete: `backend/docs/skills/*.md`（5 个文件）
- Delete: `backend/prompts/exercise_generation_v1.yaml`
- Delete: `backend/prompts/review_exercise_v1.yaml`
- Test: `backend/tests/unit/test_skill_frontmatter.py`

**Interfaces:** 5 个 Skill 文件，每文件含 frontmatter（name/description/output_schema/mcp_prefetch/mcp_tool_use/max_retries）+ body。

**Step 1**: 写失败测试 `test_skill_frontmatter.py`：

```python
"""验证 5 个老 Skill 的 frontmatter 合法 + 路径正确。"""
import pytest
import yaml
from pathlib import Path
from selflearn.skills.library import load_all, get

SKILLS = [
    "skill.profile.build",
    "skill.plan.generate",
    "skill.exercise.generate",
    "skill.review.exercise.business",
    "skill.director.start",
]


def test_all_skills_loadable():
    load_all()
    for s in SKILLS:
        skill = get(s)
        assert skill.name == s
        assert skill.description.startswith("Use when")
        assert isinstance(skill.mcp_prefetch, list)
        assert isinstance(skill.mcp_tool_use, list)
        assert isinstance(skill.max_retries, int)


def test_skill_files_on_disk():
    from selflearn.skills.library import SKILLS_DIR
    for s in SKILLS:
        path = SKILLS_DIR / s / "SKILL.md"
        assert path.exists(), f"missing: {path}"
```

**Step 2**: 跑测试 → FAIL（5 个 SKILL.md 还不存在）。

**Step 3**: 创 5 个 SKILL.md（内容从 `backend/docs/skills/*.md` 搬，加 frontmatter）。

**`backend/skills/skill.profile.build/SKILL.md`**：

```markdown
---
name: skill.profile.build
description: Use when building a student's 6-dimension profile from input dimensions + tags. Outputs dimensions in kb/vp/as/ge/ept/fd short keys.
mcp_prefetch: []
mcp_tool_use: []
max_retries: 0
---

# Skill: 6 维画像构建

## Intent
读 payload.dimensions + tags，6 个维度键（knowledge_base / visual_preference / analytic_style / goal_employment / error_prone_type / focus_duration）映射成短名（kb / vp / as / ge / ept / fd），写 profiles 表。

## Validation Rules
- 6 维必须全填；任一缺失 → 默认 0.5
- dimensions 类型必须是 {string: number}
- tags 必须是 list[str]

## Output
- 短名 dimensions 字典（kb / vp / as / ge / ept / fd）
- profile_id (UUID)
```

**`backend/skills/skill.plan.generate/SKILL.md`**：

```markdown
---
name: skill.plan.generate
description: Use when generating a treasure map of 5-10 knowledge points for a new student. Idempotent: skips if nodes exist.
mcp_prefetch:
  - tool.get_existing_nodes
  - tool.get_kps
mcp_tool_use: []
max_retries: 0
---

# Skill: 藏宝图生成

## Intent
为新学生生成 5-10 个 MapNode；已有节点则跳过（幂等）。

## Validation Rules
- 已有任何 MapNode → 跳过
- KP 数 < 5 → 报错

## Output
- node_ids: list[UUID]
```

**`backend/skills/skill.exercise.generate/SKILL.md`**（内容来自原 `prompts/exercise_generation_v1.yaml`）：

```markdown
---
name: skill.exercise.generate
description: Use when generating a batch of 2-4 exercises for a knowledge point. Inputs are kp_title, difficulty, optional revision_suggestions.
output_schema: schemas/exercise.schema.json
mcp_prefetch:
  - tool.get_kp
  - tool.get_recent_scores
mcp_tool_use:
  - tool.lint_json
max_retries: 1
---

# 习题生成器

## 任务
为给定知识点出一组 2-4 道考察题。

## 严格输出格式
- **顶层必须是 JSON array（列表）**
- 每道题必填 6 字段：exercise_type / prompt / options / correct_answer / explanation / difficulty / score
- exercise_type 枚举: single_choice | fill_blank | short_answer | code
- prompt ≥ 5 字符
- single_choice: options 长度 ≥ 2，correct_answer ∈ options
- difficulty: 1 | 2 | 3
- score: 0.5 - 3.0

## 输出样例
```json
[
  {
    "exercise_type": "single_choice",
    "prompt": "Transformer 中 self-attention 缩放因子是？",
    "options": ["√d_k", "d_k", "d_model", "1"],
    "correct_answer": "√d_k",
    "explanation": "防止 QK^T 方差爆炸，缩放因子是 √d_k",
    "difficulty": 2,
    "score": 1.5
  }
]
```

## 难度梯度
- easy: 概念辨析
- medium: 应用
- hard: 综合

## 注意
- 不要输出 reasoning 过程
- 不要在 JSON 前后加解释文字
- 收到 revision_suggestions 时按意见改
```

**`backend/skills/skill.review.exercise.business/SKILL.md`**（内容来自原 `prompts/review_exercise_v1.yaml`）：

```markdown
---
name: skill.review.exercise.business
description: Use when running business-rule checks on a batch of exercises. Returns verdict ∈ {passed, rejected, needs_fix} and issues list.
mcp_prefetch: []
mcp_tool_use:
  - tool.lint_json
max_retries: 0
---

# Skill: 业务规则审查

## Intent
对一批习题做业务规则审查；规则失败列出 issues，verdict 由 issues 严重度聚合。

## Validation Rules
- lint_json 必过
- batch 内 prompt 不允许重复
- single_choice: options 长度 ≥ 2
- single_choice: correct_answer ∈ options
- code: correct_answer 必须包含 "def" 或 "class"
- difficulty 分布：batch size ≥ 3 时 1/2/3 各至少 1 道

## Output
- verdict: passed | rejected | needs_fix
- score: float 0..1
- issues: list[{rule, severity, message}]
```

**`backend/skills/skill.director.start/SKILL.md`**：

```markdown
---
name: skill.director.start
description: Use when starting a level generation chain. Chains lecture.generate → review.lecture → exercise.generate (≤2 revisions) → review.exercise (business + llm) → write DB.
mcp_prefetch:
  - tool.get_active_node
  - tool.get_kp
  - tool.get_recent_scores
mcp_tool_use: []
max_retries: 0
---

# Skill: Director 关卡编排

## Intent
编排端到端关卡生成链。失败重试 3 次（整链重生成）。

## Chain
1. node = mcp.get_active_node(student_id)
2. kp = mcp.get_kp(node.kp_id)
3. recent = mcp.get_recent_scores(student_id, limit=3)
4. difficulty = compute_difficulty(recent)
5. lecture_html = LLMAgent.run("skill.lecture.generate")
6. review_lec = ReviewStage.review_lecture(lecture_html)  # rejected → 整链失败
7. for revision in [0, 1]:
     exercises = LLMAgent.run("skill.exercise.generate", suggestions=...)
     if revision == 0:
       review_biz = ReviewStage.review_exercise_business(exercises)  # rejected → 整链失败
     review_llm = ReviewStage.review_exercise_llm(exercises, kp.title)
     if passed: break
     suggestions = review_llm.suggestions
8. level = mcp.create_level(node_id, lecture_html)
9. mcp.bulk_create_exercises(level_id, exercises)
10. deltas = compute_deltas(final_review.score)
11. mcp.update_profile(student_id, deltas)
12. SSE COMPLETED

## Failure Strategy
- MCP 预拉失败 → retry 整链
- LLM lint 失败 → retry 单步
- 业务规则 rejected → retry 整链
- 写库失败 → retry 整链（依赖 idempotency）
- max_attempts = 3
```

**Step 4**: 删 5 个旧文件 + 2 个 prompt yaml：

```bash
rm backend/docs/skills/*.md
rm backend/prompts/exercise_generation_v1.yaml
rm backend/prompts/review_exercise_v1.yaml
```

**Step 5**: 跑测试 → PASS。

**Step 6**: 跑旧测试看是否破坏（找引用 `docs/skills` 或 `prompts/` 路径的）：

```bash
cd backend && grep -rn "docs/skills\|prompts/" src/ tests/ 2>&1 | grep -v __pycache__
```

预期：基本无引用。**如果有**，手动修复路径。

**Step 7**: Commit：

```bash
git add backend/skills/ backend/docs/skills/ backend/prompts/ backend/tests/unit/test_skill_frontmatter.py
git commit -m "feat(skills): P2.2 迁移 5 个老 Skill 到 SKILL.md 格式 + 删旧文件"
```

---

### Task 10: 新增 2 个 Skill（lecture.generate + review.exercise.llm）

**Files:**
- Create: `backend/skills/skill.lecture.generate/SKILL.md`
- Create: `backend/skills/skill.review.exercise.llm/SKILL.md`
- Test: `backend/tests/unit/test_skill_frontmatter.py`（追加 2 个 case）

**Step 1**: 写测试追加：

```python
# test_skill_frontmatter.py 追加
NEW_SKILLS = ["skill.lecture.generate", "skill.review.exercise.llm"]

def test_new_skills_loadable():
    load_all()
    for s in NEW_SKILLS:
        skill = get(s)
        assert skill.name == s
```

**Step 2**: 跑测试 → FAIL。

**Step 3**: 创 2 个 SKILL.md。

**`backend/skills/skill.lecture.generate/SKILL.md`**（**占位**，本 plan 不实现讲义调用，关联 backlog）：

```markdown
---
name: skill.lecture.generate
description: Use when generating HTML lecture for a knowledge point. Outputs sanitized HTML in white-list tags + pre-defined classes (callout/formula/example). (Placeholder — implementation deferred to backlog 2026-07-15-html-lecture.)
output_schema: null
mcp_prefetch:
  - tool.get_kp
  - tool.get_recent_scores
mcp_tool_use:
  - tool.lint_html
max_retries: 1
---

# Skill: 讲义生成（占位）

## Intent
为知识点生成 HTML 讲义，800-1500 字，白名单标签 + 预定义 class + KaTeX 公式。

## Output
- lecture_html: string (sanitized HTML)

## Status
本 Skill 是预留占位，关联 backlog `docs/superpowers/backlog/2026-07-15-html-lecture.md`。当前 Phase 不调用。
```

**`backend/skills/skill.review.exercise.llm/SKILL.md`**：

```markdown
---
name: skill.review.exercise.llm
description: Use when running LLM semantic review on a batch of exercises. Inputs are exercises list, kp_title, optional prior issues. Returns verdict ∈ {passed, needs_revision} and suggestions for revision.
output_schema: null
mcp_prefetch: []
mcp_tool_use: []
max_retries: 0
---

# Skill: LLM 语义审查

## Intent
调 LLM 检查习题的语义质量：
- 题目是否真的考 kp_title
- explanation 是否与 correct_answer 自洽
- 题目措辞是否清晰无歧义

## Input
- exercises: list[dict]
- kp_title: string
- prior_issues: list[dict] (optional, 上轮 LLM 给的)

## Output
- verdict: "passed" | "needs_revision"
- suggestions: list[str]  (给 exercise LLM 的修改意见)
- issues: list[{rule, severity, message}]

## 审查要点
- 题目 vs KP 一致性：题目应明确问 kp 涉及的概念
- 答案 vs 解释：correct_answer 应在 explanation 里有推理依据
- 难度匹配：difficulty 与实际题目深度一致
- 措辞：避免歧义、避免引导性问题
```

**Step 4**: 跑测试 → PASS。

**Step 5**: Commit：

```bash
git add backend/skills/ backend/tests/unit/test_skill_frontmatter.py
git commit -m "feat(skills): P2.3 新增 2 个 Skill (lecture.generate, review.exercise.llm)"
```

---

### Task 11: Skill 加载启动 fail-fast + 7 个 Skill 验收

**Files:**
- Modify: `backend/src/selflearn/main.py`（启动时检查 7 个 Skill 全部加载）
- Test: `backend/tests/integration/test_skill_startup.py`

**Step 1**: 写测试 `test_skill_startup.py`：

```python
"""验证 7 个 Skill 全部加载。"""
from selflearn.skills.library import load_all, _skill_library

EXPECTED = {
    "skill.profile.build",
    "skill.plan.generate",
    "skill.exercise.generate",
    "skill.review.exercise.business",
    "skill.review.exercise.llm",
    "skill.lecture.generate",
    "skill.director.start",
}


def test_seven_skills_loaded():
    load_all()
    loaded = set(_skill_library.keys())
    missing = EXPECTED - loaded
    assert not missing, f"missing skills: {missing}"
    extra = loaded - EXPECTED
    assert not extra, f"unexpected skills: {extra}"
```

**Step 2**: 跑测试 → PASS（应该已经 7 个）。

**Step 3**: 在 `main.py` 启动后加 fail-fast 检查：

```python
# main.py worker 启动后
load_all()
expected_skills = {
    "skill.profile.build", "skill.plan.generate",
    "skill.exercise.generate", "skill.review.exercise.business",
    "skill.review.exercise.llm", "skill.lecture.generate",
    "skill.director.start",
}
loaded = set(_skill_library.keys())
missing = expected_skills - loaded
if missing:
    raise RuntimeError(f"skills_missing:{sorted(missing)}")
log.info("skills.preflight_ok", count=len(loaded))
```

**Step 4**: 启动 worker 验证（手动跑 main 一段）：

```bash
cd backend && timeout 10 uv run python -c "
from selflearn.main import main
import asyncio
asyncio.run(main())
" 2>&1 | grep -E "skills\."
```

预期：日志里有 `skills.preflight_ok`。

**Step 5**: Commit：

```bash
git add backend/src/selflearn/main.py backend/tests/integration/test_skill_startup.py
git commit -m "feat(skills): P2.4 启动 fail-fast 检查 7 个 Skill"
```

**Phase 2 收尾**：7 个 Skill md 全部就位 + frontmatter 校验通过 + 启动 fail-fast。

---

## Phase 3: LLMAgent + ReviewStage

### Task 12: LLMAgent 骨架 + prefetch + 调 LLM

**Files:**
- Create: `backend/src/selflearn/agents/core.py`
- Test: `backend/tests/unit/test_llm_agent.py`

**Interfaces:**
- `class LLMAgent(mcp: MCPClient, llm: LLMRegistry)`
- `async def run(skill_id: str, env: Envelope) -> Any`
  - 1. skill = mcp.fetch_skill(skill_id)
  - 2. prefetch = gather(mcp.call(t, **env.input_args) for t in skill.mcp_prefetch)
  - 3. prompt = skill.body.format(**prefetch, **env.input_args)
  - 4. response = llm.chat(ChatRequest(messages=[system, user], reasoning=True))
  - 5. (本期: tool_use 循环跳过，mcp_tool_use=[] v1 永不进入)
  - 6. (本期: lint 也跳过，Task 13 加)
  - 7. parse(response.content, skill.output_schema) → return

**Step 1**: 写失败测试 `test_llm_agent.py`：

```python
"""LLMAgent 行为测试。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from selflearn.agents.core import LLMAgent
from selflearn.core.envelope import Envelope, ActorRef


@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    mcp.call = AsyncMock()
    return mcp


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.default.return_value.chat = AsyncMock()
    return llm


@pytest.mark.asyncio
async def test_llm_agent_runs_skill_with_prefetch(mock_mcp, mock_llm):
    """验证：调 fetch_skill → prefetch → 拼 prompt → 调 LLM。"""
    mock_mcp.call.side_effect = lambda tool, **kwargs: {
        "tool.fetch_skill": {
            "ok": True,
            "name": "skill.test",
            "description": "test",
            "body": "Title: {title}",
            "output_schema": None,
            "mcp_prefetch": ["tool.get_kp"],
            "mcp_tool_use": [],
            "max_retries": 0,
        },
        "tool.get_kp": {
            "ok": True,
            "title": "Transformer",
            "description": "x",
        },
    }[tool]

    mock_llm.default.return_value.chat.return_value = MagicMock(
        content="ok", has_tool_call=False, raw="ok",
    )

    agent = LLMAgent(mcp=mock_mcp, llm=mock_llm)
    env = Envelope(
        action="skill.execute",
        target=ActorRef(type="skill", id="skill.test"),
        payload={"title": "自注意力"},
    )
    result = await agent.run("skill.test", env)
    # 验证 fetch_skill 被调
    assert any(c.args[0] == "tool.fetch_skill" for c in mock_mcp.call.call_args_list)
    # 验证 get_kp 被调
    assert any(c.args[0] == "tool.get_kp" for c in mock_mcp.call.call_args_list)
    # 验证 prompt 拼上了 KP title
    chat_call = mock_llm.default.return_value.chat.call_args
    messages = chat_call[0][0].messages
    assert "Transformer" in messages[0].content  # system 含 KP title 拼好的 prompt
```

**Step 2**: 跑测试 → FAIL（`ModuleNotFoundError: No module named 'selflearn.agents.core'`）。

**Step 3**: 实现 `agents/core.py`（v1 简化版，不含 lint 和 tool_use 循环）：

```python
"""LLMAgent: 1 个全能 Agent class。"""
from __future__ import annotations

import asyncio
from typing import Any

from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.llm.base import ChatMessage, ChatRequest
from selflearn.llm.registry import LLMRegistry


class LLMAgent:
    """通用 Agent：调 Skill → MCP 预拉 → LLM → 解析。"""

    def __init__(self, mcp_client: Any, llm_registry: LLMRegistry) -> None:
        self.mcp = mcp_client
        self.llm = llm_registry

    async def run(self, skill_id: str, env: Envelope) -> Any:
        """按 Skill 跑一次。

        Phase 3 简化版：prefetch + LLM + parse；lint 在 Task 13 加；tool_use 循环在后续 task 加。
        """
        # 1. 加载 Skill
        skill = await self.mcp.call("tool.fetch_skill", skill_id=skill_id)
        if not skill.get("ok"):
            raise AppError(ErrorCode.INTERNAL, f"fetch_skill failed: {skill.get('error')}")

        # 2. MCP 预拉（必填数据）
        prefetch: dict[str, Any] = {}
        for tool in skill.get("mcp_prefetch", []):
            prefetch[tool] = await self.mcp.call(tool)

        # 3. 拼 prompt
        try:
            prompt_body = skill["body"].format(**prefetch, **self._env_args(env))
        except KeyError as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"skill prompt missing key: {e}. Skill={skill_id}",
            )

        # 4. 调 LLM
        response = await self.llm.default().chat(
            ChatRequest(
                messages=[
                    ChatMessage("system", prompt_body),
                    ChatMessage("user", str(env.payload)),
                ],
                reasoning=True,
            )
        )

        # 5. v1: tool_use 循环跳过（mcp_tool_use=[] 默认）
        # 6. v1: lint 跳过（Task 13 加）

        # 7. 解析返回
        return response.content

    @staticmethod
    def _env_args(env: Envelope) -> dict[str, Any]:
        """把 envelope payload 暴露给 prompt 模板。"""
        return dict(env.payload or {})
```

**Step 4**: 跑测试 → PASS。

**Step 5**: 跑旧测试 + 新测试，看是否有破坏（mypy 也要跑）：

```bash
cd backend && uv run pytest tests/ -x -q
cd backend && uv run mypy src/selflearn/agents/core.py
```

**Step 6**: Commit：

```bash
git add backend/src/selflearn/agents/core.py backend/tests/unit/test_llm_agent.py
git commit -m "feat(agent): P3.1 LLMAgent 骨架 (prefetch + LLM + parse)"
```

---

### Task 13: LLMAgent 加 lint 重试 + tool_use 循环（v1 留空接口）

**Files:**
- Modify: `backend/src/selflearn/agents/core.py`
- Modify: `backend/tests/unit/test_llm_agent.py`（追加 lint + retry 测试）

**Step 1**: 追加测试到 `test_llm_agent.py`：

```python
@pytest.mark.asyncio
async def test_llm_agent_lint_retry(mock_mcp, mock_llm):
    """验证：lint 失败时重试 max_retries 次。"""
    mock_mcp.call.side_effect = lambda tool, **kwargs: {
        "tool.fetch_skill": {
            "ok": True, "name": "skill.test", "description": "t", "body": "x",
            "output_schema": "schemas/exercise.json",
            "mcp_prefetch": [], "mcp_tool_use": [], "max_retries": 1,
        },
        "tool.lint_json": {"ok": False, "error": "bad"} if kwargs.get("attempt", 0) == 0 else {"ok": True},
    }.get(tool, {})

    # 模拟 LLM 第一次坏、第二次好
    call_count = {"n": 0}
    def chat_side_effect(req):
        call_count["n"] += 1
        m = MagicMock(content="[]", has_tool_call=False, raw="[]")
        if call_count["n"] == 2:
            m.content = '[{"exercise_type":"single_choice","prompt":"12345","options":["a","b"],"correct_answer":"a","explanation":"1234567890","difficulty":1,"score":1.0}]'
        return m
    mock_llm.default.return_value.chat.side_effect = chat_side_effect

    agent = LLMAgent(mcp=mock_mcp, llm=mock_llm)
    env = Envelope(action="skill.execute", target=ActorRef(type="skill", id="skill.test"), payload={})
    result = await agent.run("skill.test", env)
    assert call_count["n"] == 2  # 重试 1 次
```

**Step 2**: 跑测试 → FAIL（当前实现不重试）。

**Step 3**: 改造 `core.py` 加 lint 重试：

```python
async def run(self, skill_id: str, env: Envelope) -> Any:
    skill = await self.mcp.call("tool.fetch_skill", skill_id=skill_id)
    if not skill.get("ok"):
        raise AppError(ErrorCode.INTERNAL, f"fetch_skill failed: {skill.get('error')}")

    prefetch: dict[str, Any] = {}
    for tool in skill.get("mcp_prefetch", []):
        prefetch[tool] = await self.mcp.call(tool)

    try:
        prompt_body = skill["body"].format(**prefetch, **self._env_args(env))
    except KeyError as e:
        raise AppError(ErrorCode.INTERNAL, f"skill prompt missing key: {e}. Skill={skill_id}")

    max_retries = skill.get("max_retries", 0)
    last_err: str | None = None

    for attempt in range(max_retries + 1):
        # 调 LLM（v1: tool_use 跳过，mcp_tool_use=[] 默认）
        response = await self.llm.default().chat(
            ChatRequest(
                messages=[
                    ChatMessage("system", prompt_body),
                    ChatMessage("user", str(env.payload)),
                ],
                reasoning=True,
            )
        )

        # v1: tool_use 循环留空（后续 task 加）
        # 现状 mcp_tool_use=[]，LLM 不会调 tool_use

        # lint（若 output_schema 存在）
        schema = skill.get("output_schema")
        if schema:
            lint = await self.mcp.call(
                "tool.lint_json", payload=response.content, schema_name=schema,
            )
            if lint.get("ok"):
                return response.content
            last_err = lint.get("error", "lint_failed")
        else:
            return response.content

    raise AppError(
        ErrorCode.INTERNAL,
        f"llm_max_retries_exceeded: skill={skill_id} last_err={last_err}",
    )
```

**Step 4**: 跑测试 → PASS。

**Step 5**: 跑旧测试 + mypy → 不破。

**Step 6**: Commit：

```bash
git add backend/src/selflearn/agents/core.py backend/tests/unit/test_llm_agent.py
git commit -m "feat(agent): P3.2 LLMAgent lint 重试 + tool_use 循环留空接口"
```

---

### Task 14: ReviewStage（业务规则 + LLM 审查双步骤）

**Files:**
- Create: `backend/src/selflearn/agents/review_stage.py`
- Test: `backend/tests/unit/test_review_stage.py`

**Interfaces:**
- `class ReviewStage(llm_agent: LLMAgent, mcp: Any)`
- `async def review_lecture(lecture_html: str) -> ReviewResult`（lint_html + not_empty）
- `async def review_exercise_business(exercises: list[dict]) -> ReviewResult`（5 条 + lint_json）
- `async def review_exercise_llm(exercises, kp_title, trace_id) -> LLMReviewResult`

**Step 1**: 写失败测试 `test_review_stage.py`：

```python
"""ReviewStage 行为测试。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from selflearn.agents.review_stage import ReviewStage, ReviewResult, LLMReviewResult


@pytest.fixture
def mock_deps():
    llm = MagicMock()
    mcp = MagicMock()
    mcp.call = AsyncMock()
    return ReviewStage(llm_agent=llm, mcp=mcp), llm, mcp


@pytest.mark.asyncio
async def test_review_lecture_clean_html(mock_deps):
    rs, _, mcp = mock_deps
    mcp.call.return_value = {
        "cleaned": "<h1>标题</h1><p>正文</p>",
        "is_empty": False,
    }
    result = await rs.review_lecture("<h1>标题</h1><p>正文</p>")
    assert result.verdict == "passed"


@pytest.mark.asyncio
async def test_review_lecture_empty_html(mock_deps):
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"cleaned": "", "is_empty": True}
    result = await rs.review_lecture("")
    assert result.verdict == "rejected"
    assert any(i["rule"] == "not_empty" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_business_passed(mock_deps):
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": True, "error": None}
    exercises = [
        {"exercise_type": "single_choice", "prompt": "Q1 题目", "options": ["A", "B"], "correct_answer": "A", "explanation": "解析", "difficulty": 1, "score": 1.0},
        {"exercise_type": "single_choice", "prompt": "Q2 题目", "options": ["A", "B"], "correct_answer": "B", "explanation": "解析", "difficulty": 2, "score": 1.0},
        {"exercise_type": "single_choice", "prompt": "Q3 题目", "options": ["A", "B"], "correct_answer": "C", "explanation": "解析", "difficulty": 3, "score": 1.0},
    ]
    result = await rs.review_exercise_business(exercises)
    assert result.verdict == "passed"


@pytest.mark.asyncio
async def test_review_exercise_business_duplicate_prompt(mock_deps):
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": True, "error": None}
    exercises = [
        {"exercise_type": "single_choice", "prompt": "相同", "options": ["A", "B"], "correct_answer": "A", "explanation": "x" * 20, "difficulty": 1, "score": 1.0},
        {"exercise_type": "single_choice", "prompt": "相同", "options": ["A", "B"], "correct_answer": "B", "explanation": "y" * 20, "difficulty": 2, "score": 1.0},
    ]
    result = await rs.review_exercise_business(exercises)
    assert result.verdict == "needs_fix"
    assert any(i["rule"] == "duplicate_prompt" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_business_options_min(mock_deps):
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": True, "error": None}
    exercises = [
        {"exercise_type": "single_choice", "prompt": "题目 12345", "options": ["A"], "correct_answer": "A", "explanation": "x" * 20, "difficulty": 1, "score": 1.0},
    ]
    result = await rs.review_exercise_business(exercises)
    assert result.verdict == "needs_fix"
    assert any(i["rule"] == "options_min" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_business_answer_not_in_options(mock_deps):
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": True, "error": None}
    exercises = [
        {"exercise_type": "single_choice", "prompt": "题目 12345", "options": ["A", "B"], "correct_answer": "X", "explanation": "x" * 20, "difficulty": 1, "score": 1.0},
    ]
    result = await rs.review_exercise_business(exercises)
    assert result.verdict == "rejected"
    assert any(i["rule"] == "answer_not_in_options" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_business_lint_failed(mock_deps):
    rs, _, mcp = mock_deps
    mcp.call.return_value = {"ok": False, "error": "schema_violation"}
    result = await rs.review_exercise_business([])
    assert result.verdict == "rejected"
    assert any(i["rule"] == "lint_json" for i in result.issues)


@pytest.mark.asyncio
async def test_review_exercise_llm_passed(mock_deps):
    rs, llm, mcp = mock_deps
    llm.run = AsyncMock(return_value='{"verdict": "passed", "suggestions": [], "issues": []}')
    result = await rs.review_exercise_llm([], "自注意力", "trace-1")
    assert result.verdict == "passed"


@pytest.mark.asyncio
async def test_review_exercise_llm_needs_revision(mock_deps):
    rs, llm, mcp = mock_deps
    llm.run = AsyncMock(return_value='{"verdict": "needs_revision", "suggestions": ["explanation 错"], "issues": []}')
    result = await rs.review_exercise_llm([], "自注意力", "trace-1")
    assert result.verdict == "needs_revision"
    assert "explanation 错" in result.suggestions
```

**Step 2**: 跑测试 → FAIL（ModuleNotFoundError）。

**Step 3**: 实现 `agents/review_stage.py`：

```python
"""ReviewStage: 业务规则 + LLM 语义审查。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from selflearn.core.errors import AppError, ErrorCode


@dataclass
class ReviewResult:
    verdict: str  # "passed" | "rejected" | "needs_fix"
    score: float = 0.0
    issues: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LLMReviewResult:
    verdict: str  # "passed" | "needs_revision"
    suggestions: list[str] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)


class ReviewStage:
    """Python 强制 stage：业务规则 (5 + lint) + LLM 语义审查。"""

    def __init__(self, llm_agent: Any, mcp: Any) -> None:
        self.llm = llm_agent
        self.mcp = mcp

    async def review_lecture(self, lecture_html: str) -> ReviewResult:
        """lecture 业务规则：lint_html + not_empty。"""
        issues: list[dict[str, Any]] = []
        if not lecture_html:
            return ReviewResult(verdict="rejected", score=0.0,
                                issues=[{"rule": "not_empty", "severity": "high",
                                         "message": "lecture_html 为空"}])

        lint = await self.mcp.call("tool.lint_html", html=lecture_html)
        if lint.get("is_empty"):
            issues.append({"rule": "not_empty", "severity": "high",
                           "message": "lecture_html 清洗后为空"})

        if any(i["severity"] == "high" for i in issues):
            return ReviewResult(verdict="rejected", score=0.0, issues=issues)
        return ReviewResult(verdict="passed", score=1.0, issues=[])

    async def review_exercise_business(self, exercises: list[dict]) -> ReviewResult:
        """exercise 业务规则：lint_json + 5 规则。"""
        issues: list[dict[str, Any]] = []

        # 1. lint_json
        lint = await self.mcp.call("tool.lint_json", payload=exercises, schema_name="exercise")
        if not lint.get("ok"):
            return ReviewResult(
                verdict="rejected", score=0.0,
                issues=[{"rule": "lint_json", "severity": "high", "message": lint.get("error", "lint_failed")}],
            )

        # 2. 业务规则
        seen_prompts: set[str] = set()
        for ex in exercises:
            prompt = str(ex.get("prompt", ""))
            if prompt in seen_prompts:
                issues.append({"rule": "duplicate_prompt", "severity": "medium",
                               "message": f"duplicate prompt: {prompt[:20]}"})
            seen_prompts.add(prompt)

            if ex.get("exercise_type") == "single_choice":
                opts = ex.get("options") or []
                if len(opts) < 2:
                    issues.append({"rule": "options_min", "severity": "medium",
                                   "message": f"options length {len(opts)} < 2"})
                if ex.get("correct_answer") not in opts:
                    issues.append({"rule": "answer_not_in_options", "severity": "high",
                                   "message": f"answer {ex.get('correct_answer')} not in {opts}"})

        if len(exercises) >= 3:
            diffs = {int(ex.get("difficulty", 1)) for ex in exercises}
            if not {1, 2, 3}.issubset(diffs):
                issues.append({"rule": "difficulty_gradient", "severity": "low",
                               "message": f"missing difficulty in {sorted(diffs)}"})

        if any(i["severity"] == "high" for i in issues):
            return ReviewResult(verdict="rejected", score=0.0, issues=issues)
        if issues:
            return ReviewResult(verdict="needs_fix", score=0.6, issues=issues)
        return ReviewResult(verdict="passed", score=1.0, issues=[])

    async def review_exercise_llm(
        self, exercises: list[dict], kp_title: str, trace_id: str
    ) -> LLMReviewResult:
        """LLM 语义审查：调 LLMAgent 跑 skill.review.exercise.llm。"""
        import json
        from selflearn.core.envelope import Envelope, ActorRef

        raw = await self.llm.run(
            skill_id="skill.review.exercise.llm",
            env=Envelope(
                action="skill.execute",
                sender=ActorRef(type="review", id="stage"),
                target=ActorRef(type="skill", id="skill.review.exercise.llm"),
                payload={"exercises": exercises, "kp_title": kp_title, "trace_id": trace_id},
            ),
        )
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError) as e:
            raise AppError(ErrorCode.INTERNAL, f"review_llm parse failed: {e}")

        return LLMReviewResult(
            verdict=data.get("verdict", "needs_revision"),
            suggestions=data.get("suggestions", []),
            issues=data.get("issues", []),
        )
```

**Step 4**: 跑测试 → PASS。

**Step 5**: mypy 跑：

```bash
cd backend && uv run mypy src/selflearn/agents/review_stage.py
```

**Step 6**: Commit：

```bash
git add backend/src/selflearn/agents/review_stage.py backend/tests/unit/test_review_stage.py
git commit -m "feat(agent): P3.3 ReviewStage (业务规则 + LLM 审查双步骤)"
```

**Phase 3 收尾**：LLMAgent + ReviewStage 都实现 + 单测全 PASS。

---

## Phase 4: Director 链 + Retry

### Task 15: Director 链主体（run_director_chain）

**Files:**
- Create: `backend/src/selflearn/agents/director.py`
- Test: `backend/tests/unit/test_director_chain.py`

**Interfaces:**
- `async def run_director_chain(env: Envelope, agent: LLMAgent, review: ReviewStage) -> dict`
- 内部：lecture → lecture review → exercise (≤2 轮) → exercise review (双步骤) → 写库

**Step 1**: 写失败测试 `test_director_chain.py`：

```python
"""Director 链单测。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from selflearn.agents.director import run_director_chain
from selflearn.core.envelope import Envelope, ActorRef


@pytest.fixture
def mock_agent_review():
    agent = MagicMock()
    agent.run = AsyncMock()
    agent.mcp = MagicMock()
    agent.mcp.call = AsyncMock()
    review = MagicMock()
    review.review_lecture = AsyncMock()
    review.review_exercise_business = AsyncMock()
    review.review_exercise_llm = AsyncMock()
    return agent, review


@pytest.mark.asyncio
async def test_director_chain_happy_path(mock_agent_review):
    agent, review = mock_agent_review
    # MCP 预拉返回
    agent.mcp.call.side_effect = lambda tool, **kwargs: {
        "tool.get_active_node": {"ok": True, "node_id": "n1", "kp_id": "k1", "status": "active", "position": {"x": 0, "y": 0}},
        "tool.get_kp": {"ok": True, "title": "Transformer", "description": "x", "difficulty": 1, "prerequisites": []},
        "tool.get_recent_scores": [],
        "tool.create_level": {"ok": True, "level_id": "L1"},
        "tool.bulk_create_exercises": {"ok": True, "exercise_ids": ["e1"]},
        "tool.update_profile": {"ok": True},
    }.get(tool, {})

    # LLM 调 lecture + exercise
    agent.run.side_effect = [
        "<h1>讲义</h1>",  # lecture_html
        '[{"exercise_type":"single_choice","prompt":"Q","options":["A","B"],"correct_answer":"A","explanation":"x"*20,"difficulty":1,"score":1.0}]',  # exercises
    ]

    review.review_lecture.return_value = MagicMock(verdict="passed")
    review.review_exercise_business.return_value = MagicMock(verdict="passed")
    review.review_exercise_llm.return_value = MagicMock(verdict="passed", score=1.0)

    env = Envelope(action="skill.execute", target=ActorRef(type="skill", id="skill.director.start"),
                    payload={"student_id": "s1"})
    result = await run_director_chain(env, agent, review)
    assert result["level_id"] == "L1"
    # verify lecture + exercise 各调 1 次
    assert agent.run.call_count == 2
    # verify create_level + bulk_create + update_profile
    called_tools = [c.args[0] for c in agent.mcp.call.call_args_list]
    assert "tool.create_level" in called_tools
    assert "tool.bulk_create_exercises" in called_tools
    assert "tool.update_profile" in called_tools


@pytest.mark.asyncio
async def test_director_chain_exercise_revision(mock_agent_review):
    """exercise needs_revision → 跑 2 轮。"""
    agent, review = mock_agent_review
    agent.mcp.call.side_effect = lambda tool, **kwargs: {
        "tool.get_active_node": {"ok": True, "node_id": "n1", "kp_id": "k1", "status": "active", "position": {"x": 0, "y": 0}},
        "tool.get_kp": {"ok": True, "title": "T", "description": "x", "difficulty": 1, "prerequisites": []},
        "tool.get_recent_scores": [],
        "tool.create_level": {"ok": True, "level_id": "L1"},
        "tool.bulk_create_exercises": {"ok": True, "exercise_ids": ["e1"]},
        "tool.update_profile": {"ok": True},
    }.get(tool, {})

    agent.run.side_effect = [
        "<h1>讲义</h1>",
        '[{"exercise_type":"single_choice","prompt":"Q1","options":["A","B"],"correct_answer":"A","explanation":"x"*20,"difficulty":1,"score":1.0}]',
        '[{"exercise_type":"single_choice","prompt":"Q2","options":["A","B"],"correct_answer":"B","explanation":"y"*20,"difficulty":1,"score":1.0}]',  # 修订版
    ]
    review.review_lecture.return_value = MagicMock(verdict="passed")
    review.review_exercise_business.return_value = MagicMock(verdict="passed")
    review.review_exercise_llm.side_effect = [
        MagicMock(verdict="needs_revision", suggestions=["改 explanation"], score=0.5),
        MagicMock(verdict="passed", score=1.0),
    ]
    env = Envelope(action="skill.execute", target=ActorRef(type="skill", id="skill.director.start"),
                    payload={"student_id": "s1"})
    result = await run_director_chain(env, agent, review)
    # exercise 调了 2 次（revision 0 + 1）
    assert agent.run.call_count == 3  # lecture + exercise×2
    # LLM 审查也跑 2 次
    assert review.review_exercise_llm.call_count == 2
```

**Step 2**: 跑测试 → FAIL（ModuleNotFoundError）。

**Step 3**: 实现 `agents/director.py`：

```python
"""Director 链：编排 lecture + exercise + review + 写库。"""
from __future__ import annotations

import asyncio
from typing import Any

from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.core.logging import get_logger
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.progress.stream import progress_publish

log = get_logger("director")


def _compute_difficulty(recent_scores: list[float]) -> str:
    if not recent_scores:
        return "medium"
    avg = sum(recent_scores) / len(recent_scores)
    if avg < 0.5:
        return "easy"
    if avg < 0.8:
        return "medium"
    return "hard"


def _compute_deltas(score: float) -> dict[str, float]:
    delta_kb = 0.05 if score >= 0.8 else (-0.03 if score < 0.5 else 0.0)
    delta_as = 0.02 if score >= 0.7 else -0.02
    return {"kb": delta_kb, "as": delta_as}


async def run_director_chain(
    env: Envelope, agent: Any, review: Any
) -> dict[str, Any]:
    """完整 Director 链。失败抛 AppError 由外层 retry 处理。"""
    trace_id = env.trace_id
    student_id = env.payload.get("student_id", "")

    # 1-3. 数据准备
    node = await agent.mcp.call("tool.get_active_node", student_id=student_id)
    if not node.get("ok"):
        raise AppError(ErrorCode.INTERNAL, f"get_active_node: {node.get('error')}")
    kp = await agent.mcp.call("tool.get_kp", kp_id=node["kp_id"])
    if not kp.get("ok"):
        raise AppError(ErrorCode.INTERNAL, f"get_kp: {kp.get('error')}")
    recent = await agent.mcp.call("tool.get_recent_scores", student_id=student_id, limit=3)
    difficulty = _compute_difficulty(list(recent))

    # 4. lecture
    await progress_publish(trace_id, ProgressEvent(stage=Stage.DIRECTOR, status="running",
        payload={"action": "lecture_generate", "node_id": node["node_id"]}))
    lecture_html = await agent.run("skill.lecture.generate", env)
    await progress_publish(trace_id, ProgressEvent(stage=Stage.LECTURE, status="completed",
        payload={"lecture_html_len": len(lecture_html)}))

    # 5. lecture 业务规则
    review_lec = await review.review_lecture(lecture_html)
    if review_lec.verdict == "rejected":
        raise AppError(ErrorCode.INTERNAL, f"lecture_rejected: {review_lec.issues}")

    # 6. exercise 0-2 轮
    suggestions: list[str] = []
    exercises = None
    final_review = None
    for revision in range(2):
        # 6a. 调 exercise skill
        env_ex = Envelope(
            action="skill.execute",
            sender=env.sender,
            target=env.target,
            payload={
                **env.payload,
                "node_id": node["node_id"],
                "kp_title": kp["title"],
                "difficulty": difficulty,
                "revision_suggestions": suggestions,
            },
            trace_id=trace_id,
            parent_id=env.span_id,
        )
        exercises_raw = await agent.run("skill.exercise.generate", env_ex)
        import json
        try:
            exercises = json.loads(exercises_raw) if isinstance(exercises_raw, str) else exercises_raw
        except json.JSONDecodeError as e:
            raise AppError(ErrorCode.INTERNAL, f"exercise parse failed: {e}")

        # 6b. 业务规则（仅 revision 0）
        if revision == 0:
            review_biz = await review.review_exercise_business(exercises)
            if review_biz.verdict == "rejected":
                raise AppError(ErrorCode.INTERNAL, f"exercise_rejected: {review_biz.issues}")
            # needs_fix: log warn，不重做

        # 6c. LLM 语义审查
        review_llm = await review.review_exercise_llm(exercises, kp["title"], trace_id)
        final_review = review_llm

        if review_llm.verdict == "passed":
            break
        if revision == 1:
            log.warning("director.exercise_max_revisions_reached", trace_id=trace_id)
            break
        suggestions = review_llm.suggestions

    # 7. 写库
    level = await agent.mcp.call(
        "tool.create_level", node_id=node["node_id"], lecture_html=lecture_html
    )
    if not level.get("ok"):
        raise AppError(ErrorCode.INTERNAL, f"create_level: {level.get('error')}")

    bulk = await agent.mcp.call(
        "tool.bulk_create_exercises", level_id=level["level_id"], exercises=exercises
    )
    if not bulk.get("ok"):
        raise AppError(ErrorCode.INTERNAL, f"bulk_create_exercises: {bulk.get('error')}")

    # 8. 更新 profile
    score_ratio = final_review.score if final_review else 0.6
    deltas = _compute_deltas(score_ratio)
    await agent.mcp.call("tool.update_profile", student_id=student_id, deltas=deltas)

    return {
        "level_id": level["level_id"],
        "exercise_ids": bulk.get("exercise_ids", []),
        "exercises_count": len(exercises),
        "score": score_ratio,
        "lecture_html_len": len(lecture_html),
    }
```

**Step 4**: 跑测试 → PASS。

**Step 5**: Commit：

```bash
git add backend/src/selflearn/agents/director.py backend/tests/unit/test_director_chain.py
git commit -m "feat(agent): P4.1 Director 链主体 (lecture + exercise×2 + review + 写库)"
```

---

### Task 16: Director retry 包装 + 接入 worker

**Files:**
- Create: `backend/src/selflearn/agents/director_retry.py`（或扩展 `director.py`）
- Modify: `backend/src/selflearn/agents/scheduler.py`（改用 Director 链）
- Modify: `backend/src/selflearn/main.py`（启动时构造 LLMAgent + ReviewStage + MCP client）
- Test: `backend/tests/unit/test_director_retry.py`
- Test: `backend/tests/integration/test_director_e2e.py`

**Interfaces:**
- `async def run_director_chain_with_retry(env, agent, review, max_attempts=3)`
- 失败时整链 retry（catch AppError / DBError）

**Step 1**: 写失败测试 `test_director_retry.py`：

```python
"""Director retry 包装测试。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from selflearn.agents.director import run_director_chain_with_retry
from selflearn.core.envelope import Envelope, ActorRef
from selflearn.core.errors import AppError, ErrorCode


@pytest.mark.asyncio
async def test_retry_on_db_write_failure_then_success():
    """第 1 次写库失败 → 第 2 次成功。"""
    agent = MagicMock()
    review = MagicMock()
    call_count = {"n": 0}

    async def fake_chain(env, a, r):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise AppError(ErrorCode.INTERNAL, "create_level: db_error")
        return {"level_id": "L1", "exercise_ids": [], "exercises_count": 0, "score": 1.0, "lecture_html_len": 100}

    env = Envelope(action="skill.execute", target=ActorRef(type="skill", id="skill.director.start"),
                    payload={"student_id": "s1"})
    result = await run_director_chain_with_retry(
        env, agent, review, run_chain_fn=fake_chain, max_attempts=3,
    )
    assert result["level_id"] == "L1"
    assert call_count["n"] == 2  # 第 1 次失败 + 第 2 次成功


@pytest.mark.asyncio
async def test_retry_exhausted_raises_last_error():
    """3 次都失败抛最后 1 次异常。"""
    agent = MagicMock()
    review = MagicMock()

    async def always_fail(env, a, r):
        raise AppError(ErrorCode.INTERNAL, "persistent_failure")

    env = Envelope(action="skill.execute", target=ActorRef(type="skill", id="skill.director.start"),
                    payload={"student_id": "s1"})
    with pytest.raises(AppError) as exc:
        await run_director_chain_with_retry(
            env, agent, review, run_chain_fn=always_fail, max_attempts=3,
        )
    assert "persistent_failure" in str(exc.value)
```

**Step 2**: 跑测试 → FAIL。

**Step 3**: 在 `director.py` 末尾加 retry 包装：

```python
async def run_director_chain_with_retry(
    env: Envelope, agent: Any, review: Any, max_attempts: int = 3
) -> dict[str, Any]:
    """整链 retry 包装。失败重生成（依赖 level/start 路由幂等性）。"""
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await run_director_chain(env, agent, review)
        except (AppError, Exception) as e:
            last_error = e
            log.warning("director.chain_retry",
                        attempt=attempt + 1, max_attempts=max_attempts,
                        error=repr(e))
    assert last_error is not None
    raise last_error
```

**Step 4**: 跑测试 → PASS。

**Step 5**: 改造 `scheduler.py`：删 `_AGENT_FOR_SKILL` map，改成"调 Director 链"：

```python
"""SkillBasedScheduler → Director dispatch。"""
from __future__ import annotations

from selflearn.agents.director import run_director_chain_with_retry
from selflearn.core.envelope import Envelope
from selflearn.core.logging import get_logger

log = get_logger("scheduler")

# 旧 _AGENT_FOR_SKILL map 删掉


async def dispatch(env: Envelope, agent: Any, review: Any) -> Envelope | None:
    """统一入口：所有 skill 都走 Director 链（Director 内部按 skill 路由）。"""
    if env.target.id != "skill.director.start":
        log.warning("scheduler.non_director_skill", skill_id=env.target.id)

    result = await run_director_chain_with_retry(env, agent, review)
    return None  # reply envelope 由 Director 内部处理（不返回）
```

**Step 6**: 改造 `main.py` 启动 worker 时构造 agent + review + MCP client：

```python
# main.py worker 启动后
from selflearn.agents.core import LLMAgent
from selflearn.agents.review_stage import ReviewStage
from selflearn.llm.registry import llm_registry
# MCP client 启动（stdio 进程）
from selflearn.mcp_client import MCPClient  # 写一个简单 client

mcp = MCPClient()
agent = LLMAgent(mcp_client=mcp, llm_registry=llm_registry)
review = ReviewStage(llm_agent=agent, mcp=mcp)

# 然后 RabbitMQ consumer 用 agent + review 调 dispatch
```

`backend/src/selflearn/mcp_client.py`（**新**，不在 spec 范围但必须存在——简化版 stdio client）：

```python
"""MCP stdio client：与 MCP server 进程通信。"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from typing import Any


class MCPClient:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "selflearn.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._id = 0

    async def call(self, tool: str, **kwargs: Any) -> Any:
        """单 tool call。简化版：同步读写。"""
        self._id += 1
        msg = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": kwargs},
        }
        loop = asyncio.get_event_loop()
        line = await loop.run_in_executor(None, self._send_and_read, msg)
        resp = json.loads(line)
        if "error" in resp:
            return {"ok": False, "error": resp["error"].get("message", "unknown")}
        return resp.get("result", {})

    def _send_and_read(self, msg: dict) -> bytes:
        body = json.dumps(msg).encode() + b"\n"
        self.proc.stdin.write(body)
        self.proc.stdin.flush()
        return self.proc.stdout.readline()

    def close(self) -> None:
        self.proc.terminate()
        self.proc.wait(timeout=5)
```

**Step 7**: 写集成测试 `test_director_e2e.py`（用真 DB + mock LLM via respx）：

```python
"""Director 链端到端：mock LLM + 真 DB + 真 MCP server。"""
import pytest
import respx
from httpx import Response
from selflearn.agents.core import LLMAgent
from selflearn.agents.review_stage import ReviewStage
from selflearn.agents.director import run_director_chain_with_retry
from selflearn.mcp_client import MCPClient
from selflearn.llm.registry import llm_registry


@pytest.mark.asyncio
async def test_director_e2e_with_mock_llm(setup_kp_and_node, cleanup_db):
    """端到端：mock LLM 返回固定值 + 真 DB + 真 MCP server。"""
    student_id, kp_id, _ = setup_kp_and_node
    mcp = MCPClient()
    try:
        # 准备 data
        # ... 插 student + node ...

        agent = LLMAgent(mcp_client=mcp, llm_registry=llm_registry)
        review = ReviewStage(llm_agent=agent, mcp=mcp)

        with respx.mock(base_url="https://llm-8fs3x2jvif1tomue.cn-beijing.maas.aliyuncs.com") as mock:
            mock.post("/compatible-mode/v1/chat/completions").mock(
                return_value=Response(200, json={
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                })
            )
            env = Envelope(...)
            result = await run_director_chain_with_retry(env, agent, review)
            assert result["level_id"]
    finally:
        mcp.close()
```

**Step 8**: 跑全部新测试 + 旧测试（除已记录的 5 个）：

```bash
cd backend && uv run pytest tests/ -x -q
```

预期：所有测试 PASS（5 个旧测试除外，本 task 还没修——P5 一起修）。

**Step 9**: Commit：

```bash
git add backend/src/selflearn/agents/director.py backend/src/selflearn/agents/scheduler.py backend/src/selflearn/main.py backend/src/selflearn/mcp_client.py backend/tests/
git commit -m "feat(agent): P4.2 Director retry 包装 + scheduler 接入 + MCP client"
```

**Phase 4 收尾**：Director 链 + retry + worker 接入 + 集成测试。

---

## Phase 5: 删旧代码 + 收尾

### Task 17: 删 5 个旧 Agent class + 删 tools/ 目录 + 删 backend/docs/skills/

**Files:**
- Delete: `backend/src/selflearn/agents/builtin/director_agent.py`
- Delete: `backend/src/selflearn/agents/builtin/exercise_agent.py`
- Delete: `backend/src/selflearn/agents/builtin/review_agent.py`
- Delete: `backend/src/selflearn/agents/builtin/plan_agent.py`
- Delete: `backend/src/selflearn/agents/builtin/profile_agent.py`
- Delete: `backend/src/selflearn/agents/builtin/_node_protocol.py`
- Delete: `backend/src/selflearn/agents/builtin/__init__.py`
- Delete: `backend/src/selflearn/tools/`（整个目录）
- Delete: `backend/docs/skills/`（整个目录）
- Modify: `backend/src/selflearn/agents/builtin/__init__.py`（如果保留目录则空）
- Modify: `backend/src/selflearn/agents/builtin/__init__.py`（空）

**Step 1**: 验证没有引用：

```bash
cd backend && grep -rn "from selflearn.agents.builtin.director_agent\|from selflearn.tools\b" src/ tests/ 2>&1 | grep -v __pycache__
```

预期：无引用。如果有，**改调用方**（不是保留旧文件）。

**Step 2**: 删 5 个 Agent class + tools/ 目录 + docs/skills/：

```bash
git rm backend/src/selflearn/agents/builtin/director_agent.py
git rm backend/src/selflearn/agents/builtin/exercise_agent.py
git rm backend/src/selflearn/agents/builtin/review_agent.py
git rm backend/src/selflearn/agents/builtin/plan_agent.py
git rm backend/src/selflearn/agents/builtin/profile_agent.py
git rm backend/src/selflearn/agents/builtin/_node_protocol.py
git rm -r backend/src/selflearn/tools/
git rm -r backend/docs/skills/
```

**Step 3**: 跑全部测试：

```bash
cd backend && uv run pytest tests/ -x -q
```

预期：除 5 个引用旧 Agent class 的测试外全 PASS。

**Step 4**: 改 5 个旧测试（用新架构）：

**`tests/unit/test_exercise_agent.py`** → **删除**（ExerciseAgent 概念已无；用 `tests/unit/test_llm_agent.py` 覆盖）

**`tests/unit/test_review_agent.py`** → **删除**（ReviewAgent 概念已无；用 `tests/unit/test_review_stage.py` 覆盖）

**`tests/unit/test_director_tryexcept.py`** → **改写**测试 Director 链的 try/except 行为（mock 一次失败，验证 retry 后成功）

**`tests/unit/test_difficulty_gradient.py`** → **保留**（测的是业务规则算法本身，可以独立测；从 `review_stage.py` 抽出来做成 `tests/unit/test_business_rules.py`）

**`tests/unit/test_scheduler_target_id_routing.py`** → **改写**测试新 `dispatch()`（只 1 个 skill_id 走 Director）

**Step 5**: 跑全部测试 → 全 PASS（~150 个）。

**Step 6**: mypy clean：

```bash
cd backend && uv run mypy src/selflearn/ 2>&1 | tail -20
```

**Step 7**: smoke_mvp + Playwright：

```bash
cd backend && bash scripts/smoke_mvp.sh 2>&1 | tail -15
cd frontend && npx playwright test 2>&1 | tail -10
```

**Step 8**: Commit：

```bash
git add -A
git commit -m "refactor(agent): P5.1 删 5 个旧 Agent class + tools/ 目录 + docs/skills/"
```

---

### Task 18: 全量验收 + tag

**Files:**
- 无（验收 + 打 tag）

**Step 1**: 跑全测试 + mypy + smoke + playwright：

```bash
cd backend && uv run pytest tests/ -q
cd backend && uv run mypy src/selflearn/
cd backend && bash scripts/smoke_mvp.sh
cd frontend && npx playwright test
```

预期：
- pytest：~150 PASS
- mypy：no issues
- smoke：8/8 PASS
- playwright：3/3 PASS

**Step 2**: 写验收报告 `docs/superpowers/reports/2026-07-15-agent-architecture.md`：

```markdown
# Agent 架构重构验收报告 — 2026-07-15

**Spec**: docs/superpowers/specs/2026-07-15-agent-architecture-design.md
**Plan**: docs/superpowers/plans/2026-07-15-agent-architecture.md

## TL;DR
1 个 LLMAgent + 1 个 ReviewStage + 1 个 stdio MCP Server（15 tool）+ 7 个 SKILL.md，5 个旧 Agent class 全删。

## 验收
- pytest: ~150 PASS
- mypy: clean
- smoke_mvp: 8/8 PASS
- playwright: 3/3 PASS

## 改动
- [commit list]
```

**Step 3**: Commit report + 打 tag：

```bash
git add docs/superpowers/reports/2026-07-15-agent-architecture.md
git commit -m "docs(report): Agent 架构重构验收 + tag agent-architecture-v1"
git tag agent-architecture-v1
```

**Phase 5 收尾 + 整个 plan 完成。**

---

## 风险与回退

| 风险 | 影响 | 缓解 |
|---|---|---|
| MCP stdio 通信慢 | 整链多 200-500ms | 单 tool 30ms 本地测量后估算；超过则改 HTTP |
| 旧测试 5 个破坏 | P5 一起改 | 已在 Task 17 计划 |
| `tool.fetch_skill` 读不到 md | 启动 fail-fast | Skill 启动检查（Task 11）已加 |
| nh3 API 变动 | lint_html 编译失败 | pyproject 锁版本 mcp>=0.9.0, nh3>=0.2.0 |
| LLM 调通但 MCP client 死锁 | 整链 hang | 用 run_in_executor + timeout |

## 不在范围内

- LLM 实时 tool_use 循环（v1 留空）
- 讲义 HTML 实际生成（关联 backlog `2026-07-15-html-lecture.md`）
- 图片 / 视频 / iframe
- Alembic 迁移（lecture_html 加在讲义 backlog PR 里）

## 验收

- [ ] pytest ~150 PASS
- [ ] mypy clean
- [ ] smoke_mvp 8/8 PASS
- [ ] playwright 3/3 PASS
- [ ] 5 个旧测试改写完成
- [ ] 报告 + tag
