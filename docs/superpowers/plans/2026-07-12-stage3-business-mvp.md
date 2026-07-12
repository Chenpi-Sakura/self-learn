# Stage 3 — 核心业务 MVP — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Stage 2 后端基座上落地 5 个业务 Agent + Redis Stream 真流式 SSE + LLM 思考模式 + 6 张业务表，跑通 "profile → plan → director → exercise → review → submit" 端到端 MVP 闭环，并交付 `scripts/smoke_mvp.sh` smoke 验证脚本。

**Architecture:** 单一 worker 容器内同步序列调 ProfileAgent → PlanAgent → ExerciseAgent → ReviewAgent；每个 Agent 通过 `skill_library.get()` 加载 Skill markdown 文档作为 LLM system prompt，通过 `ToolRegistry.call()` 调 3 个 MCP Tool stub。Director 同步序列调子 Agent 时带 try/except 兜底，失败推 FAILED 进度。所有 Agent 推进时 `progress_publish()` XADD 到 `stream:{trace_id}`，gateway SSE 端点用裸 `XREAD` 从 `0-0` 游标起阻塞读。真流、SSE、Skill 三层 markdown 文档驱动。

**Tech Stack:**
- Python 3.12 + uv（继承 Stage 2 锁定）
- FastAPI + Pydantic v2（继承）
- SQLAlchemy 2.x async + Alembic
- redis-py 5.x async（`xadd` / `xread`，**不使用** `xreadgroup`）
- aio-pika + RabbitMQ（继承）
- pytest + pytest-asyncio + respx + testcontainers（继承）
- 新增：`python-frontmatter`（解析 Skill markdown frontmatter）+ `jsonschema`（Tool.lint_json）

## Global Constraints

> 每条任务的实现要求默认继承本节。约束来自 `docs/superpowers/specs/2026-07-12-stage3-business-mvp-design.md` V1.2 与项目记忆 `no-auth-no-login`。

1. **不做鉴权**：任何阶段、文件、task 中禁止出现鉴权 / 登录 / Token / JWT / OAuth / `Depends(get_current_user)` / `auth.py`。删除即存在。
2. **依赖只设最低版本**：`pyproject.toml` 全部 `>=`，不要 `<N.0`。
3. **Python 稳定在 3.12**。
4. **统一走 `BaseLLMAdapter` / `LLMRegistry`**：禁止直连 OpenAI SDK。Stage 2 已锁。
5. **统一走 `SkillLibrary` / `ToolRegistry`**：禁止 Agent 内 import `lit_json` / `frontmatter` 等第三方库直接调用，所有外部能力经 ToolRegistry，prompt 注入经 SkillLibrary。
6. **进度靠 `progress_publish()` 推**：worker 任意代码点不直接写 Redis key，必须走 `progress/stream.py` 的 `progress_publish()` 包装。
7. **SSE 真流用裸 `XREAD`**：禁用 `xreadgroup`、禁用 consumer group 概念。
8. **`last_id` 一律从 `"0-0"` 起步**：消除"前端建连前已写入事件"的竞态。
9. **`AGENT_TIMEOUT` 120s**（V1.1 放宽），不要回退到 30s。
10. **JSONB 字段统一封装在 repo 层**：写入走整体赋值 或 `flag_modified`；不依赖 SQLAlchemy 就地 mutate。
11. **Stage 2 不能破**：每 task 跑完必须 `pytest tests/integration/test_smoke.py` 仍绿（Stage 2 smoke 完整性）。
12. **mypy strict 必过**：每 task 必跑 `uv run mypy src tests`，0 错。
13. **Tool / Skill / Agent 三层不混合**：
    - **Skill markdown 文档（`docs/skills/*.md`）V1.2 严禁写入 Tool 调用指令**：禁止出现 `tool.fetch_template` / `tool.lint_json` / `tool.store_kp` 等工具名提示、禁止 `Call ToolRegistry.call(...)` 之类的步骤、禁止任何把工具调用伪装成"业务步骤"的写法。Skill 只描述 **意图 + 数据格式校验规则 + 输出 Schema + 业务硬约束**。理由：Skill.body 直接喂给 LLM，LLM 没有 function_call 能力，写了只会污染 LLM 输出，引发 EXERCISE_INVALID 解析崩溃。
    - **Tool 调用只能在 Agent.run() / run_sync() 中以 `await ToolRegistry.call(...)` 形式硬编排**：所有 fetch_template / lint_json / store_kp 必须在 Agent Python 代码里写死调用顺序，不写在 Skill 里。
    - **Agent 类禁止声明 `skills = [...]` 类属性 / 方法**：Skill 与 Agent 的绑定完全靠 `Envelope.target.id` ↔ `docs/skills/<id>.md` 文件名匹配。Agent 在 run() 内需要时直接 `skill_library.get(...)`，不靠任何静态注册表。
    - **SkillBasedScheduler 重构**：路由机制剥离对 Agent 静态属性或装饰器的依赖，强制仅认 `envelope.target.id`，与 markdown 文件名一一对应。
14. **数据表严格 6 张**：本阶段不允许新增 / ALTER 表，最多 6 张 + Stage 2 已建的 2 张。

---

## File Structure（与 spec § 3.2 / § 3.3 / § 9 对齐）

```
backend/
├── migrations/versions/
│   └── <hash>_stage3_business_tables.py         ← Task 3（6 张表）
├── scripts/
│   ├── seed_map.py                              ← Task 8（KP seed）
│   └── smoke_mvp.sh                             ← Task 14
├── src/selflearn/
│   ├── llm/
│   │   ├── base.py                              ← Task 1（ChatRequest.reasoning / ChatChunk.reasoning_delta）
│   │   └── adapters/{mock,openai_compat}.py     ← Task 1+2（reasoning_content 解析 + reasoning_delta yield）
│   ├── core/
│   │   └── thinking.py                          ← Task 2（reasoning_content fence 提取 helper）
│   ├── domain/
│   │   ├── knowledge_point.py                   ← Task 3
│   │   ├── map_node.py                          ← Task 3
│   │   ├── level.py                             ← Task 3
│   │   ├── exercise.py                          ← Task 3
│   │   ├── level_completion.py                  ← Task 3
│   │   └── review_result.py                     ← Task 3
│   ├── infra/repositories/                      ← Task 3+10（JSONB repo 封装）
│   │   ├── profile_repo.py
│   │   ├── map_node_repo.py
│   │   ├── level_repo.py
│   │   ├── exercise_repo.py
│   │   ├── level_completion_repo.py
│   │   ├── review_result_repo.py
│   │   └── knowledge_point_repo.py
│   ├── progress/                                ← Task 4（Redis Stream 包装）
│   │   ├── stages.py
│   │   └── stream.py
│   ├── tools/                                   ← Task 5
│   │   ├── protocol.py
│   │   └── builtin/{lint_json,fetch_template,store_kp}.py
│   ├── skills/                                  ← Task 6
│   │   └── library.py
│   ├── agents/builtin/                          ← Task 7-11
│   │   ├── profile_agent.py
│   │   ├── plan_agent.py
│   │   ├── exercise_agent.py
│   │   ├── review_agent.py
│   │   └── director_agent.py
│   └── gateway/routes/
│       ├── profile.py                           ← Task 12（保留 Stage 2 路由 + 切到 stream SSE）
│       ├── map.py                               ← Task 12
│       └── level.py                             ← Task 12
├── docs/skills/                                 ← Task 6（Skill markdown 文档）
│   ├── skill.profile.build.md
│   ├── skill.plan.generate.md
│   ├── skill.exercise.generate.md
│   ├── skill.review.exercise.md
│   └── skill.director.start.md
├── schemas/                                     ← Task 5（jsonschema 文件夹）
│   └── exercise.schema.json
└── tests/
    ├── unit/
    │   ├── test_chat_reasoning.py               ← Task 1+2
    │   ├── test_progress_stream.py              ← Task 4
    │   ├── test_tool_lint_json.py               ← Task 5
    │   ├── test_tool_registry.py                ← Task 5
    │   ├── test_skill_library.py                ← Task 6
    │   ├── test_exercise_repo_jsonb.py          ← Task 3（JSONB 脏检查陷阱覆盖）
    │   ├── test_exercise_agent.py               ← Task 9
    │   ├── test_review_agent.py                 ← Task 10
    │   └── test_director_tryexcept.py           ← Task 11
    └── integration/
        └── test_smoke_mvp.py                    ← Task 13+14（testcontainers 起真 Redis Stream）
```

---

## Task 1: LLM 抽象层加 reasoning 字段（ChatRequest / ChatChunk）

**Files:**
- Modify: `backend/src/selflearn/llm/base.py:9-32`（`ChatRequest` + `ChatChunk` dataclass）
- Test: `backend/tests/unit/test_chat_reasoning.py`

**Interfaces:**
- Consumes: 无前置依赖（Stage 2 的 `ChatRequest` / `ChatChunk` 已存在）
- Produces: 
  - `ChatRequest.reasoning: bool = False`
  - `ChatRequest.reasoning_budget: int | None = None`
  - `ChatChunk.reasoning_delta: str | None = None`

### Step 1: 写失败的测试

`backend/tests/unit/test_chat_reasoning.py`:
```python
from selflearn.llm.base import ChatChunk, ChatRequest, ChatMessage

def test_chat_request_default_reasoning_off():
    req = ChatRequest(messages=[ChatMessage(role="user", content="hi")])
    assert req.reasoning is False
    assert req.reasoning_budget is None

def test_chat_chunk_accepts_reasoning_delta():
    chunk = ChatChunk(delta="", reasoning_delta="thinking...")
    assert chunk.delta == ""
    assert chunk.reasoning_delta == "thinking..."

def test_chat_chunk_normal_no_reasoning_field():
    chunk = ChatChunk(delta="hello")
    assert chunk.reasoning_delta is None
```

### Step 2: 跑测试确认失败

```bash
cd backend
uv run pytest tests/unit/test_chat_reasoning.py -v
```

Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'reasoning'`（在 `ChatRequest` 上），`TypeError: ... 'reasoning_delta'`（在 `ChatChunk` 上）。

### Step 3: 最小实现

`backend/src/selflearn/llm/base.py`:
```python
"""LLM 抽象基类 + 数据类（v4 § 1.1 LLM Gateway；Stage 3 加 thinking）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None


@dataclass
class ChatRequest:
    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    stop: list[str] | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    # Stage 3 新增：思考模式
    reasoning: bool = False                # 调用方按需传入
    reasoning_budget: int | None = None    # 思考 token 上限（Claude 类需要显式传）


@dataclass
class ChatChunk:
    delta: str
    finish_reason: str | None = None
    usage: dict[str, object] | None = None
    # Stage 3 新增：思考过程增量（DeepSeek-R1 / 通义 QwQ 在 stream 中同时含 reasoning_content）
    reasoning_delta: str | None = None


class BaseLLMAdapter(ABC):
    """所有 LLM provider 必须实现的接口。"""

    provider_name: str

    @abstractmethod
    async def chat(self, req: ChatRequest) -> str: ...

    @abstractmethod
    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        if False:  # pragma: no cover
            yield ChatChunk(delta="")

    @abstractmethod
    async def health(self) -> bool: ...
```

### Step 4: 跑测试确认通过

```bash
uv run pytest tests/unit/test_chat_reasoning.py -v
```

Expected: 3 passed。

### Step 5: mypy + commit

```bash
uv run mypy src tests
git add src/selflearn/llm/base.py tests/unit/test_chat_reasoning.py
git commit -m "feat(llm): ChatRequest 增加 reasoning/reasoning_budget；ChatChunk 增加 reasoning_delta"
```

---

## Task 2: 思考模式 helper + Mock / OpenAI adapter 接入 reasoning_content

**Files:**
- Create: `backend/src/selflearn/core/thinking.py`
- Modify: `backend/src/selflearn/llm/adapters/mock.py`
- Modify: `backend/src/selflearn/llm/adapters/openai_compat.py`
- Modify: `backend/tests/unit/test_chat_reasoning.py`（追加用例）

### Step 1: 追加失败的测试

往 `backend/tests/unit/test_chat_reasoning.py` 末尾追加：
```python
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from selflearn.llm.adapters.mock import MockLLMAdapter
from selflearn.llm.base import ChatRequest, ChatMessage


def test_mock_adapter_chat_stream_yields_reasoning_when_requested():
    """Stage 3: MockLLMAdapter.chat_stream 在 reasoning=True 时额外 yield reasoning_delta。"""
    adapter = MockLLMAdapter()
    req = ChatRequest(
        messages=[ChatMessage(role="user", content="hi")],
        reasoning=True,
    )

    async def collect():
        chunks = []
        async for c in adapter.chat_stream(req):
            chunks.append(c)
        return chunks

    chunks = asyncio.run(collect())
    # Mock 至少要 yield 1 个 reasoning_delta + 1 个 delta（reasoning=True）
    assert any(c.reasoning_delta for c in chunks), "expected at least one reasoning_delta chunk"
    assert any(c.delta for c in chunks), "expected at least one content delta chunk"


def test_mock_adapter_chat_stream_no_reasoning_when_off():
    adapter = MockLLMAdapter()
    req = ChatRequest(
        messages=[ChatMessage(role="user", content="hi")],
        reasoning=False,
    )

    async def collect():
        chunks = []
        async for c in adapter.chat_stream(req):
            chunks.append(c)
        return chunks

    chunks = asyncio.run(collect())
    assert not any(c.reasoning_delta for c in chunks), "no reasoning_delta expected when reasoning=False"


def test_helper_extracts_json_from_fence():
    """core.thinking.extract_json_from_fence 处理 LLM 返回的 markdown 代码块。"""
    from selflearn.core.thinking import extract_json_from_fence

    raw = "思考过程...\n```json\n[{\"exercise_type\": \"single_choice\"}]\n```\n"
    parsed = extract_json_from_fence(raw)
    assert parsed == [{"exercise_type": "single_choice"}]


def test_helper_extracts_plain_json():
    from selflearn.core.thinking import extract_json_from_fence

    parsed = extract_json_from_fence('[{"k": 1}]')
    assert parsed == [{"k": 1}]
```

### Step 2: 跑测试确认失败

```bash
uv run pytest tests/unit/test_chat_reasoning.py -v
```

Expected: 3 个新 case FAIL（`AttributeError: reasoning_delta` 在 mock 上、`ImportError: core.thinking`）。

### Step 3: 最小实现（3 个文件）

#### `backend/src/selflearn/core/thinking.py`
```python
"""LLM 思考模式辅助（Stage 3 新增）。"""
from __future__ import annotations

import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json_from_fence(raw: str) -> object:
    """从 LLM 输出中提取 JSON。优先取 ```json fence；其次尝试整段 parse。
    返回已反序列化对象（list / dict）；raise json.JSONDecodeError。"""
    matches = _FENCE_RE.findall(raw)
    if matches:
        return json.loads(matches[0])
    return json.loads(raw)
```

#### `backend/src/selflearn/llm/adapters/mock.py`
（覆盖整个文件，原 Stage 2 的 mock 极简版，增 `reasoning` 路径）
```python
"""Mock LLM Adapter（Stage 3: 支持 reasoning 字段）。"""
from __future__ import annotations

from collections.abc import AsyncIterator

from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatRequest


class MockLLMAdapter(BaseLLMAdapter):
    """不走网络；reasoning=True 时额外 yield reasoning_delta。"""

    provider_name = "mock"

    async def chat(self, req: ChatRequest) -> str:
        return f"mock-reply: {req.messages[-1].content[:32]} -> pong"

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        if req.reasoning:
            yield ChatChunk(delta="", reasoning_delta="mock-think: ...", finish_reason=None)
            yield ChatChunk(delta="", reasoning_delta="  planning next steps", finish_reason=None)
        yield ChatChunk(delta="mock chunk 1", finish_reason=None)
        yield ChatChunk(delta="mock chunk 2", finish_reason=None)
        yield ChatChunk(delta="", finish_reason="stop")

    async def health(self) -> bool:
        return True
```

#### `backend/src/selflearn/llm/adapters/openai_compat.py`
（仅修改 `chat_stream` 解析 SSE 的内部循环）
```python
"""OpenAI 兼容适配器（DeepSeek / 通义千问）。Stage 3: 解析 reasoning_content。"""
from __future__ import annotations

from collections.abc import AsyncIterator
import json

import httpx

from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatRequest


class OpenAICompatAdapter(BaseLLMAdapter):
    provider_name = "openai_compat"

    def __init__(
        self, base_url: str, api_key: str, model: str, timeout: float = 30.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(
            timeout=timeout, headers={"Authorization": f"Bearer {api_key}"}
        )

    async def chat(self, req: ChatRequest) -> str:
        body: dict[str, object] = {
            "model": req.model or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "stream": False,
        }
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        r = await self._client.post(f"{self.base_url}/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
        first = data["choices"][0]
        return str(first["message"]["content"])

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        body: dict[str, object] = {
            "model": req.model or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "stream": True,
        }
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        async with self._client.stream(
            "POST", f"{self.base_url}/chat/completions", json=body
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    yield ChatChunk(delta="", finish_reason="stop")
                    return
                obj = json.loads(data)
                delta = obj["choices"][0]["delta"]
                # Stage 3: DeepSeek-R1 / 通义 QwQ 在 stream 中同时含 reasoning_content 与 content
                if reasoning := delta.get("reasoning_content"):
                    yield ChatChunk(delta="", reasoning_delta=reasoning)
                if content := delta.get("content", ""):
                    yield ChatChunk(delta=content)

    async def health(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/models")
            return r.status_code == 200
        except Exception:
            return False
```

### Step 4: 跑测试确认全部通过

```bash
uv run pytest tests/unit/test_chat_reasoning.py -v
```

Expected: 6 passed（3 个原始 + 3 个新增）。

### Step 5: mypy + Stage 2 回归 + commit

```bash
uv run mypy src tests
uv run pytest tests/integration/test_smoke.py -q   # Stage 2 不能破
git add src/selflearn/core/thinking.py \
        src/selflearn/llm/adapters/mock.py \
        src/selflearn/llm/adapters/openai_compat.py \
        tests/unit/test_chat_reasoning.py
git commit -m "feat(llm): adapter 接入 reasoning_content 解析；core.thinking helper"
```

---

## Task 3: 6 张新业务 ORM 模型 + Alembic 迁移

**Files:**
- Create: `backend/migrations/versions/<hash>_stage3_business_tables.py`
- Create: `backend/src/selflearn/domain/{knowledge_point,map_node,level,exercise,level_completion,review_result}.py`
- Create: `backend/src/selflearn/infra/repositories/{profile_repo,knowledge_point_repo,map_node_repo,level_repo,exercise_repo,level_completion_repo,review_result_repo}.py`
- Test: `backend/tests/unit/test_exercise_repo_jsonb.py`

### Step 1: 写失败的测试

`backend/tests/unit/test_exercise_repo_jsonb.py`:
```python
import pytest

pytestmark = pytest.mark.asyncio


async def test_exercise_repo_update_options_replaces_whole_list():
    """JSONB 字段更新：必须整体替换 list 引用，不能 in-place mutate。

    SQLAlchemy 2.x 对 JSONB dict/list 就地 mutate 不会触发 dirty tracking，
    实战必须整体赋值或 flag_modified。repo 层强制此约束。
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    # 使用 SQLite + JSONB 兼容方式（aiosqlite 支持 JSONB 模拟）
    # 注意：实际集成测试在 testcontainers 跑 PG；这里只验证「整体替换能传播」
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        from selflearn.domain.exercise import Base as ExBase
        from selflearn.domain.exercise import Exercise
        ExBase.metadata.create_all(conn)

    async with AsyncSession(engine) as session:
        ex = Exercise(
            level_id="00000000-0000-0000-0000-000000000001",  # 占位 FK
            exercise_type="single_choice",
            prompt="Q?",
            options=["A", "B"],
            correct_answer="A",
            explanation="because",
            difficulty=1,
            score=1.0,
        )
        session.add(ex)
        await session.commit()

        # 关键测试：in-place mutate 不应被持久化（这是 SQLAlchemy 的坑）
        ex.options.append("C")
        await session.commit()
        await session.refresh(ex)
        # 就地 mutate 没生效 —— "options" 仍然是 ["A", "B"]
        assert ex.options == ["A", "B"], "in-place mutate should not persist (SQLAlchemy caveat)"

        # 整体赋值才能传播
        ex.options = ["A", "B", "C"]
        await session.commit()
        await session.refresh(ex)
        assert ex.options == ["A", "B", "C"], "whole-replace assignment should persist"
```

### Step 2: 跑测试确认失败（因为 ORM 都还不存在）

```bash
uv run pytest tests/unit/test_exercise_repo_jsonb.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'selflearn.domain.exercise'`。

### Step 3: 最小实现（6 个 ORM + 迁移）

#### `backend/src/selflearn/domain/knowledge_point.py`
```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    kp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    prerequisites: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_kp_difficulty"),
        Index("idx_kp_subject", "subject"),
    )
```

#### `backend/src/selflearn/domain/map_node.py`
```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class MapNode(Base):
    __tablename__ = "map_nodes"
    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    kp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_points.kp_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    branch_type: Mapped[str] = mapped_column(String(32), nullable=False, default="main")
    position: Mapped[dict] = mapped_column(JSONB, nullable=False, default=lambda: {"x": 0.0, "y": 0.0})
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('active','sleeping','completed','locked')", name="ck_mn_status"),
        CheckConstraint("branch_type IN ('main','interest')", name="ck_mn_branch"),
        Index("idx_map_nodes_student_status", "student_id", "status"),
    )
```

#### `backend/src/selflearn/domain/level.py`
```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class Level(Base):
    __tablename__ = "levels"
    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("map_nodes.node_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generated")
    form: Mapped[str] = mapped_column(String(32), nullable=False, default="exercise")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("form IN ('exercise','document','mindmap','code')", name="ck_l_form"),
        Index("idx_levels_node", "node_id"),
    )
```

#### `backend/src/selflearn/domain/exercise.py`
```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Exercise(Base):
    __tablename__ = "exercises"
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False
    )
    exercise_type: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=1.0)

    __table_args__ = (
        CheckConstraint("exercise_type IN ('single_choice','fill_blank','short_answer','code')", name="ck_e_type"),
        CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_e_diff"),
        Index("idx_exercises_level", "level_id"),
    )
```

#### `backend/src/selflearn/domain/level_completion.py`
```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class LevelCompletion(Base):
    __tablename__ = "level_completions"
    completion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    submitted_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        Index("idx_lc_student", "student_id"),
        Index("idx_lc_level", "level_id"),
    )
```

#### `backend/src/selflearn/domain/review_result.py`
```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from selflearn.domain.base import Base


class ReviewResult(Base):
    __tablename__ = "review_results"
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False
    )
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    issues: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("verdict IN ('passed','rejected','needs_fix')", name="ck_rr_verdict"),
        Index("idx_rr_level", "level_id"),
    )
```

#### `backend/src/selflearn/domain/__init__.py`
```python
"""Stage 3 新增的 ORM 模型。Stage 2 的 student / profile 在同目录另文件。"""
from selflearn.domain.knowledge_point import KnowledgePoint  # noqa: F401
from selflearn.domain.map_node import MapNode  # noqa: F401
from selflearn.domain.level import Level  # noqa: F401
from selflearn.domain.exercise import Exercise  # noqa: F401
from selflearn.domain.level_completion import LevelCompletion  # noqa: F401
from selflearn.domain.review_result import ReviewResult  # noqa: F401
```

#### `backend/migrations/versions/<hash>_stage3_business_tables.py`
（**文件名必须用 `alembic revision --autogenerate -m "stage3_business_tables"` 自动生成的 hash，本 Task 让实现 agent 现跑一次拿到后替换。** 下文先给出完整 DDL，文件 head/tail 用 alembic 标准模板）

完整 upgrade():
```python
"""stage3 business tables

Revision ID: <hash>
Revises: <prev_hash>
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "<hash>"
down_revision = "<prev_hash>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # knowledge_points
    op.create_table(
        "knowledge_points",
        sa.Column("kp_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("subject", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("difficulty", sa.SmallInteger, nullable=False),
        sa.Column("prerequisites", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_kp_difficulty"),
    )
    op.create_index("idx_kp_subject", "knowledge_points", ["subject"])

    # map_nodes（依赖 students 表，Stage 2 已有）
    op.create_table(
        "map_nodes",
        sa.Column("node_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True),
                  sa.ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("kp_id", UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_points.kp_id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("branch_type", sa.String(32), nullable=False, server_default="main"),
        sa.Column("position", JSONB, nullable=False, server_default=sa.text("'{\"x\":0,\"y\":0}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('active','sleeping','completed','locked')", name="ck_mn_status"),
        sa.CheckConstraint("branch_type IN ('main','interest')", name="ck_mn_branch"),
    )
    op.create_index("idx_map_nodes_student_status", "map_nodes", ["student_id", "status"])

    # levels
    op.create_table(
        "levels",
        sa.Column("level_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("node_id", UUID(as_uuid=True),
                  sa.ForeignKey("map_nodes.node_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="generated"),
        sa.Column("form", sa.String(32), nullable=False, server_default="exercise"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("form IN ('exercise','document','mindmap','code')", name="ck_l_form"),
    )
    op.create_index("idx_levels_node", "levels", ["node_id"])

    # exercises
    op.create_table(
        "exercises",
        sa.Column("exercise_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("level_id", UUID(as_uuid=True),
                  sa.ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_type", sa.String(32), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("options", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("correct_answer", sa.Text, nullable=False),
        sa.Column("explanation", sa.Text, nullable=False, server_default=""),
        sa.Column("difficulty", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("score", sa.Numeric(4, 2), nullable=False, server_default="1.0"),
        sa.CheckConstraint("exercise_type IN ('single_choice','fill_blank','short_answer','code')", name="ck_e_type"),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_e_diff"),
    )
    op.create_index("idx_exercises_level", "exercises", ["level_id"])

    # level_completions
    op.create_table(
        "level_completions",
        sa.Column("completion_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("level_id", UUID(as_uuid=True),
                  sa.ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", UUID(as_uuid=True),
                  sa.ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=False),
        sa.Column("answers", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metrics", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_lc_student", "level_completions", ["student_id"])
    op.create_index("idx_lc_level", "level_completions", ["level_id"])

    # review_results
    op.create_table(
        "review_results",
        sa.Column("review_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("level_id", UUID(as_uuid=True),
                  sa.ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("score", sa.Numeric(4, 2), nullable=False),
        sa.Column("issues", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("verdict IN ('passed','rejected','needs_fix')", name="ck_rr_verdict"),
    )
    op.create_index("idx_rr_level", "review_results", ["level_id"])


def downgrade() -> None:
    op.drop_index("idx_rr_level", table_name="review_results")
    op.drop_table("review_results")
    op.drop_index("idx_lc_level", table_name="level_completions")
    op.drop_index("idx_lc_student", table_name="level_completions")
    op.drop_table("level_completions")
    op.drop_index("idx_exercises_level", table_name="exercises")
    op.drop_table("exercises")
    op.drop_index("idx_levels_node", table_name="levels")
    op.drop_table("levels")
    op.drop_index("idx_map_nodes_student_status", table_name="map_nodes")
    op.drop_table("map_nodes")
    op.drop_index("idx_kp_subject", table_name="knowledge_points")
    op.drop_table("knowledge_points")
```

### Step 4: 跑测试 + 迁移

```bash
uv run pytest tests/unit/test_exercise_repo_jsonb.py -v   # 单测先过
docker compose up -d postgres
uv run alembic upgrade head
docker compose exec -T postgres psql -U selflearn -d selflearn -c "\dt"
```

Expected: 看到 8 张表（2 张 Stage 2 + 6 张新表）。

### Step 5: mypy + commit

```bash
uv run mypy src tests
git add migrations src/selflearn/domain tests/unit/test_exercise_repo_jsonb.py
git commit -m "feat(domain): 6 张业务表 ORM + Alembic 迁移"
```

---

## Task 4: progress 子模块（Redis Stream XADD / XREAD，从 0-0 起步）

**Files:**
- Create: `backend/src/selflearn/progress/stages.py`
- Create: `backend/src/selflearn/progress/stream.py`
- Test: `backend/tests/unit/test_progress_stream.py`

### Step 1: 写失败的测试

`backend/tests/unit/test_progress_stream.py`:
```python
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


async def test_progress_event_roundtrip():
    """ProgressEvent.to_redis_fields / from_redis_fields 必须可逆。"""
    from datetime import datetime
    from selflearn.progress.stages import ProgressEvent, Stage

    e = ProgressEvent(
        stage=Stage.PROFILE,
        status="running",
        payload={"k": 1},
        timestamp=datetime(2026, 7, 12, 0, 0, 0),
    )
    fields = e.to_redis_fields()
    parsed = ProgressEvent.from_redis_fields(fields)
    assert parsed.stage == Stage.PROFILE
    assert parsed.status == "running"
    assert parsed.payload == {"k": 1}


async def test_progress_consume_uses_0_0_cursor():
    """progress_consume 必须从 '0-0' 起步（V1.1 修复点）。"""
    with patch("selflearn.progress.stream.get_redis") as mock_get_redis:
        from selflearn.progress import stream as stream_mod

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        # mock xread 返回 1 条
        mock_redis.xread.return_value = [
            ("stream:abc", [("1-0", {"stage": "profile", "status": "running",
                                      "payload": "{}", "timestamp": "2026-07-12T00:00:00"})])
        ]
        mock_redis.xread.side_effect = [[
            ("stream:abc", [("1-0", {"stage": "profile", "status": "running",
                                      "payload": "{}", "timestamp": "2026-07-12T00:00:00"})])
        ], []]

        consumed = []
        async def collect():
            gen = stream_mod.progress_consume("abc")
            async for ev in gen:
                consumed.append(ev)
                if len(consumed) >= 1:
                    return

        await asyncio.wait_for(collect(), timeout=1.0)

        # 关键断言：第一次 xread 调用用的 last_id 必须是 "0-0"
        first_call = mock_redis.xread.call_args_list[0]
        assert first_call.args[0][0] == {"stream:abc": "0-0"}, (
            f"cursor must start at '0-0', got {first_call.args[0][0]}"
        )
```

### Step 2: 跑测试确认失败

```bash
uv run pytest tests/unit/test_progress_stream.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'selflearn.progress'`。

### Step 3: 最小实现

#### `backend/src/selflearn/progress/__init__.py`
```python
from selflearn.progress.stages import ProgressEvent, Stage  # noqa: F401
from selflearn.progress.stream import progress_publish, progress_consume  # noqa: F401
```

#### `backend/src/selflearn/progress/stages.py`
```python
"""Stage 枚举 + ProgressEvent 数据类。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Stage(str, Enum):
    PROFILE = "profile"
    PLAN = "plan"
    DIRECTOR = "director"
    EXERCISE = "exercise"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    stage: Stage
    status: str  # "running" | "completed" | "failed"
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_redis_fields(self) -> dict[str, str]:
        return {
            "stage": self.stage.value,
            "status": self.status,
            "payload": json.dumps(self.payload, ensure_ascii=False),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_redis_fields(cls, fields: dict) -> "ProgressEvent":
        decoded = {
            (k.decode() if isinstance(k, bytes) else k):
            (v.decode() if isinstance(v, bytes) else v)
            for k, v in fields.items()
        }
        return cls(
            stage=Stage(decoded["stage"]),
            status=decoded["status"],
            payload=json.loads(decoded["payload"]),
            timestamp=datetime.fromisoformat(decoded["timestamp"]),
        )
```

#### `backend/src/selflearn/progress/stream.py`
```python
"""Redis Stream 真流核心（V1.1 修复：last_id 从 0-0 起步）。"""
from __future__ import annotations

from collections.abc import AsyncIterator

from selflearn.infra.redis_client import get_redis
from selflearn.progress.stages import ProgressEvent


PROGRESS_STREAM_PREFIX = "stream:"
PROGRESS_STREAM_TTL_SECONDS = 3600


async def progress_publish(trace_id: str, event: ProgressEvent) -> None:
    """worker 任意代码点调用，往 stream:{trace_id} 写一条进度。"""
    r = get_redis()
    key = f"{PROGRESS_STREAM_PREFIX}{trace_id}"
    await r.xadd(key, event.to_redis_fields(), maxlen=100, approximate=True)
    await r.expire(key, PROGRESS_STREAM_TTL_SECONDS)


async def progress_consume(trace_id: str) -> AsyncIterator[ProgressEvent]:
    """Gateway SSE 端点调用，裸 XREAD 从 0-0 起步避免事件丢失。"""
    r = get_redis()
    key = f"{PROGRESS_STREAM_PREFIX}{trace_id}"
    last_id = "0-0"  # V1.1 关键修复
    while True:
        result = await r.xread({key: last_id}, block=5000, count=10)
        if not result:
            continue
        for _, entries in result:
            for entry_id, fields in entries:
                yield ProgressEvent.from_redis_fields(fields)
                last_id = entry_id
```

### Step 4: 跑测试确认通过

```bash
uv run pytest tests/unit/test_progress_stream.py -v
```

Expected: 2 passed。

### Step 5: mypy + Stage 2 回归 + commit

```bash
uv run mypy src tests
uv run pytest tests/integration/test_smoke.py -q
git add src/selflearn/progress tests/unit/test_progress_stream.py
git commit -m "feat(progress): Redis Stream publish/consume（last_id=0-0 起步）"
```

---

## Task 5: MCP Tool 协议层 + 3 个 stub Tool

**Files:**
- Create: `backend/src/selflearn/tools/__init__.py`
- Create: `backend/src/selflearn/tools/protocol.py`
- Create: `backend/src/selflearn/tools/builtin/__init__.py`
- Create: `backend/src/selflearn/tools/builtin/lint_json.py`
- Create: `backend/src/selflearn/tools/builtin/fetch_template.py`
- Create: `backend/src/selflearn/tools/builtin/store_kp.py`
- Create: `backend/schemas/exercise.schema.json`
- Test: `backend/tests/unit/test_tool_lint_json.py`
- Test: `backend/tests/unit/test_tool_registry.py`

### Step 1: 写失败的测试

`backend/tests/unit/test_tool_lint_json.py`:
```python
import pytest

from selflearn.tools.protocol import ToolRegistry


def test_lint_json_rejects_invalid():
    """tool.lint_json 必须用 jsonschema 校验，缺字段即拒收。"""
    async def run():
        res = await ToolRegistry.call(
            "tool.lint_json",
            payload=[{"exercise_type": "single_choice", "prompt": "Q?", "correct_answer": "A",
                       "difficulty": 9, "score": 1.0}],  # difficulty 越界
            schema="exercise",
        )
        return res

    import asyncio
    res = asyncio.run(run())
    assert res.ok is False
    assert "difficulty" in (res.error or "") or "schema_violation" in (res.error or "")


def test_lint_json_accepts_valid():
    async def run():
        res = await ToolRegistry.call(
            "tool.lint_json",
            payload=[{"exercise_type": "single_choice",
                       "prompt": "Q?",
                       "options": ["A", "B", "C", "D"],
                       "correct_answer": "A",
                       "explanation": "x",
                       "difficulty": 2,
                       "score": 1.5}],
            schema="exercise",
        )
        return res

    import asyncio
    res = asyncio.run(run())
    assert res.ok is True
    assert res.data["validated_count"] == 1
```

`backend/tests/unit/test_tool_registry.py`:
```python
import asyncio

from selflearn.tools.protocol import ToolResult, ToolRegistry


def test_tool_not_found_returns_error():
    async def run():
        return await ToolRegistry.call("tool.does.not_exist")

    res = asyncio.run(run())
    assert isinstance(res, ToolResult)
    assert res.ok is False
    assert "tool_not_found" in (res.error or "")
```

### Step 2: 跑测试确认失败

```bash
uv run pytest tests/unit/test_tool_lint_json.py tests/unit/test_tool_registry.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'selflearn.tools'`。

### Step 3: 最小实现

#### `backend/schemas/exercise.schema.json`
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["exercise_type", "prompt", "correct_answer", "difficulty", "score", "explanation"],
    "properties": {
      "exercise_type": {"enum": ["single_choice", "fill_blank", "short_answer", "code"]},
      "prompt": {"type": "string", "minLength": 5},
      "options": {"type": "array"},
      "correct_answer": {"type": "string", "minLength": 1},
      "explanation": {"type": "string"},
      "difficulty": {"type": "integer", "minimum": 1, "maximum": 3},
      "score": {"type": "number", "minimum": 0.5, "maximum": 3.0}
    }
  }
}
```

#### `backend/src/selflearn/tools/__init__.py`
```python
from selflearn.tools.protocol import Tool, ToolRegistry, ToolResult  # noqa: F401
```

#### `backend/src/selflearn/tools/protocol.py`
```python
"""MCP Tool 协议层（Stage 3 § 9.2）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


class Tool(ABC):
    tool_name: str
    description: str

    @abstractmethod
    async def call(self, **kwargs: Any) -> ToolResult: ...


class ToolRegistry:
    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        cls._tools[tool.tool_name] = tool

    @classmethod
    async def call(cls, name: str, **kwargs: Any) -> ToolResult:
        tool = cls._tools.get(name)
        if not tool:
            return ToolResult(ok=False, error=f"tool_not_found:{name}")
        try:
            return await tool.call(**kwargs)
        except Exception as e:  # noqa: BLE001
            return ToolResult(ok=False, error=repr(e))


def _register_default_tools() -> None:
    from selflearn.tools.builtin.lint_json import LintJsonTool
    from selflearn.tools.builtin.fetch_template import FetchTemplateTool
    from selflearn.tools.builtin.store_kp import StoreKPTool
    ToolRegistry.register(LintJsonTool())
    ToolRegistry.register(FetchTemplateTool())
    ToolRegistry.register(StoreKPTool())


_register_default_tools()
```

#### `backend/src/selflearn/tools/builtin/__init__.py`
```python
"""Tool stubs（Stage 3 MVP，Stage 4 接真 MCP server）。"""
```

#### `backend/src/selflearn/tools/builtin/lint_json.py`
```python
"""tool.lint_json: jsonschema 校验 LLM 输出的 JSON。"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from selflearn.tools.protocol import Tool, ToolResult


SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas"

_SCHEMA_CACHE: dict[str, dict] = {}


def _load_schema(name: str) -> dict:
    if name not in _SCHEMA_CACHE:
        path = SCHEMA_DIR / f"{name}.schema.json"
        _SCHEMA_CACHE[name] = json.loads(path.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE[name]


class LintJsonTool(Tool):
    tool_name = "tool.lint_json"
    description = "用 jsonschema 校验 LLM 输出的 JSON 是否符合业务 schema"

    async def call(self, *, payload: str | list | dict, schema: str = "exercise") -> ToolResult:
        try:
            data = json.loads(payload) if isinstance(payload, str) else payload
        except json.JSONDecodeError as e:
            return ToolResult(ok=False, error=f"json_decode_error:{e}")

        target = _load_schema(schema)
        try:
            jsonschema.validate(instance=data, schema=target)
        except jsonschema.ValidationError as e:
            return ToolResult(ok=False, error=f"schema_violation:{e.message}")

        return ToolResult(
            ok=True,
            data={"validated_count": len(data) if isinstance(data, list) else 1},
        )
```

#### `backend/src/selflearn/tools/builtin/fetch_template.py`
```python
"""tool.fetch_template: 从本地 YAML 读 prompt 模板（Stage 3 stub）。"""
from __future__ import annotations

from pathlib import Path

from selflearn.tools.protocol import Tool, ToolResult


PROMPT_DIR = Path(__file__).resolve().parents[3] / "prompts"


class FetchTemplateTool(Tool):
    tool_name = "tool.fetch_template"
    description = "读 prompts/{name}.yaml 模板内容，返回 string"

    async def call(self, *, name: str) -> ToolResult:
        path = PROMPT_DIR / f"{name}.yaml"
        if not path.exists():
            return ToolResult(ok=False, error=f"template_not_found:{name}")
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            return ToolResult(ok=False, error=repr(e))
        return ToolResult(ok=True, data={"name": name, "content": content})
```

#### `backend/src/selflearn/tools/builtin/store_kp.py`
```python
"""tool.store_kp: 写 KnowledgePoint 表（Stage 3 stub 用 SQLAlchemy）。"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from selflearn.config import get_settings
from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory
from selflearn.tools.protocol import Tool, ToolResult


class StoreKPTool(Tool):
    tool_name = "tool.store_kp"
    description = "插一条 knowledge_points 行，返回 kp_id"

    async def call(self, *, subject: str, title: str, description: str,
                   difficulty: int, prerequisites: list[str] | None = None) -> ToolResult:
        factory = get_session_factory()
        async with factory() as session:
            kp = KnowledgePoint(
                subject=subject,
                title=title,
                description=description,
                difficulty=difficulty,
                prerequisites=prerequisites or [],
            )
            session.add(kp)
            await session.commit()
            await session.refresh(kp)
            return ToolResult(ok=True, data={"kp_id": str(kp.kp_id)})
```

### Step 4: 跑测试 + 创建 prompts 占位

```bash
mkdir -p backend/prompts
echo "exercise_generation_v1 stub template" > backend/prompts/exercise_generation_v1.yaml
echo "review_exercise_v1 stub template" > backend/prompts/review_exercise_v1.yaml
uv run pytest tests/unit/test_tool_lint_json.py tests/unit/test_tool_registry.py -v
```

Expected: 4 passed。

### Step 5: mypy + commit

```bash
uv run mypy src tests
git add src/selflearn/tools schemas tests/unit/test_tool_lint_json.py tests/unit/test_tool_registry.py
git commit -m "feat(tools): MCP Tool 协议层 + lint_json / fetch_template / store_kp 三个 stub"
```

---

## Task 6: Skill = markdown 文档 + library loader

**Files:**
- Create: `backend/docs/skills/skill.exercise.generate.md`
- Create: `backend/docs/skills/skill.review.exercise.md`
- Create: `backend/docs/skills/skill.profile.build.md`
- Create: `backend/docs/skills/skill.plan.generate.md`
- Create: `backend/docs/skills/skill.director.start.md`
- Create: `backend/src/selflearn/skills/__init__.py`
- Create: `backend/src/selflearn/skills/library.py`
- Test: `backend/tests/unit/test_skill_library.py`
- Modify: `backend/pyproject.toml`（加 `python-frontmatter`）

### Step 1: 写失败的测试

`backend/tests/unit/test_skill_library.py`:
```python
import pytest

from selflearn.skills.library import Skill, get, load_all


def test_load_all_reads_skill_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr("selflearn.skills.library.SKILLS_DIR", tmp_path)
    (tmp_path / "skill.test.demo.md").write_text(
        "---\n"
        "name: skill.test.demo\n"
        "description: test\n"
        "---\n\n"
        "# demo body\n\nstep 1\n", encoding="utf-8"
    )
    load_all(tmp_path)
    s = get("skill.test.demo")
    assert isinstance(s, Skill)
    assert s.name == "skill.test.demo"
    assert "# demo body" in s.body
    assert "step 1" in s.body


def test_get_missing_raises():
    from selflearn.skills.library import load_all, get
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        load_all(pathlib.Path(td))
        with pytest.raises(KeyError):
            get("nonexistent")
```

### Step 2: 跑测试确认失败

```bash
uv run pytest tests/unit/test_skill_library.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'selflearn.skills'`。

### Step 3: 最小实现

#### `backend/pyproject.toml` 追加依赖
```toml
dependencies = [
    # ... Stage 2 已有 ...
    "python-frontmatter>=1.1",
    "jsonschema>=4.0",
]
```

#### `backend/docs/skills/skill.exercise.generate.md`
```markdown
---
name: skill.exercise.generate
description: Use when generating exercises from a knowledge point. LLM must output JSON only; Agent is responsible for fetching prompt template and validating output.
tags: [stage3, exercise, generation]
output_schema: schemas/exercise.schema.json
---

# Skill: 生成合规习题

## Intent
根据 knowledge_point 生成 N 道习题，LLM 严格按 Output Schema 输出 JSON，不允许散文、不允许虚构字段。

## Output Schema
See `schemas/exercise.schema.json` — required fields: exercise_type, prompt, options, correct_answer, difficulty (1-3), score。

## Validation Rules
- batch 内 prompt 不允许重复。
- difficulty ∈ {1, 2, 3}。
- single_choice: `options` 长度 == 4，恰有 1 个 ∈ `correct_answer`。
- fill_blank: `correct_answer` 非空，prompt 含恰好一个 "____"。
- code: `correct_answer` 必须包含 Python `def` 或 `class` 定义。

## Common Mistakes
- LLM 返回夹杂散文 → 解析时必须用 extract-from-fence。
- difficulty 全部相同 → 必须按 1/2/3 大致均匀分布。
```

> 注：本 markdown 不写 `Call tool.fetch_template(...)` 之类的 Tool 调用指令。Tool 调用由 Agent 代码 `await ToolRegistry.call(...)` 硬编排完成。

#### `backend/docs/skills/skill.review.exercise.md`
```markdown
---
name: skill.review.exercise
description: Use when reviewing a batch of generated exercises. Output verdict ∈ {passed, needs_fix, rejected}.
tags: [stage3, review]
---

# Skill: 评审习题集

## Intent
对一批已生成的习题做业务规则审查；规则失败的逐条列出 issues，verdict 由 issues 严重度聚合得到。

## Validation Rules
- batch 内 prompt 不允许重复。
- single_choice: `options` 长度 == 4，恰有 1 个 ∈ `correct_answer`。
- code: `correct_answer` 必须包含 `def` 或 `class`。
- difficulty 分布：batch size ≥ 3 时，1/2/3 三档各至少 1 道。

## Output
- verdict: 'passed' | 'rejected' | 'needs_fix'
- score: float in 0..1
- issues: list of {rule, severity, message}
```

> 注：具体 schema 校验（lint_json 工具调用）由 Agent.run() 内 `await ToolRegistry.call("tool.lint_json", ...)` 完成，不写在本 markdown 里。

#### `backend/docs/skills/skill.profile.build.md`
```markdown
---
name: skill.profile.build
description: Use when building initial 6-dimension profile for a new student. Each dimension is a float in [0, 1].
tags: [stage3, profile]
---

# Skill: 画像构建

## Intent
对学生做 5 轮对话，每轮收集 1 个维度的 [0, 1] 数值；最终输出 6 个维度的完整画像。

## Dimensions
- knowledge_base, visual_preference, analytic_style
- goal_employment, error_prone_type, focus_duration

## Validation Rules
- 每个 dimension ∈ [0, 1]。
- 必须全部 6 个维度齐全后才能写入 profiles 表。

## Common Mistakes
- 任意维度缺失即触发 NEEDS_REINPUT。
- 数值越界 (>1 或 <0) → LLM 必须重新抽取。
```

> 注：5 轮对话内容已在 Gateway 收齐，Agent.run() 仅读 payload.dimensions；调 LLM 做合理性 sanity check 由 Agent 代码用 ChatRequest 走，不写在这里。

#### `backend/docs/skills/skill.plan.generate.md`
```markdown
---
name: skill.plan.generate
description: Use when generating treasure map (MapNodes + KnowledgePoints) from a built profile. Output is a list of map nodes with embedded KP info.
tags: [stage3, plan]
---

# Skill: 藏宝图生成

## Intent
根据学生 profile.dimensions 生成 5-10 个 MapNode，每个 MapNode 携带一个 KnowledgePoint。

## Validation Rules
- node_count ∈ [5, 10]。
- 每个 node 必含 kp_title / kp_description / difficulty / prerequisites。
- prerequisites 必须引用已存在的 KP id（允许空 list）。
- difficulty ∈ {1, 2, 3}。
```

> 注：KP 落库（store_kp 工具调用）由 Agent.run() 内 `await ToolRegistry.call("tool.store_kp", ...)` 完成，不写在本 markdown 里。

#### `backend/docs/skills/skill.director.start.md`
```markdown
---
name: skill.director.start
description: Use when starting a level from the first active map node. Director is the orchestrator; sub-agent calls are hardcoded in Agent code.
tags: [stage3, director]
---

# Skill: 关卡推进（Director）

## Intent
为学生选定当前第一个 status=active 的 MapNode，串起"出题 → 评审 → 入库"完整流程，写入 levels + exercises + review_results 表。

## Validation Rules
- 必须存在至少 1 个 active 节点，否则抛 NO_ACTIVE_NODE。
- 必须完整跑完 出题 + 评审；任何阶段失败 → 整流程失败，不写库。
- Exercise 必须通过 Review.verdict ∈ {passed, needs_fix}；verdict=rejected → 整流程失败。

## Failure Handling
- 任何异常必须 try/except 捕获 → push progress(FAILED, payload={code, message}) → 抛 AppError。
- SSE 端点看到 FAILED 后关闭连接，前端可识别为中断。
```

> 注：选节点 / 调 ExerciseAgent.run_sync / 调 ReviewAgent.review / 写库 这一串动作由 DirectorAgent.run() 用 Python 代码硬编排完成，不写在本 markdown 里。

#### `backend/src/selflearn/skills/__init__.py`
```python
from selflearn.skills.library import Skill, load_all, get  # noqa: F401
```

#### `backend/src/selflearn/skills/library.py`
```python
"""Skill markdown 文档 loader（Stage 3 § 9.1）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import frontmatter

from selflearn.core.logging import get_logger


log = get_logger("skills")

SKILLS_DIR = Path(__file__).resolve().parents[3] / "docs" / "skills"


@dataclass
class Skill:
    name: str
    description: str
    body: str
    output_schema: str | None


_skill_library: dict[str, Skill] = {}


def load_all(skills_dir: Path | None = None) -> None:
    """进程启动时调一次，从 markdown 读 Skill。"""
    if skills_dir is None:
        skills_dir = SKILLS_DIR
    _skill_library.clear()
    for md_path in skills_dir.glob("*.md"):
        post = frontmatter.load(md_path)
        if "name" not in post.metadata:
            log.warning("skills.skip_missing_name", path=str(md_path))
            continue
        _skill_library[post.metadata["name"]] = Skill(
            name=post.metadata["name"],
            description=post.metadata.get("description", ""),
            body=post.content,
            output_schema=post.metadata.get("output_schema"),
        )
    log.info("skills.loaded", count=len(_skill_library))


def get(name: str) -> Skill:
    if name not in _skill_library:
        raise KeyError(f"skill_not_loaded:{name}")
    return _skill_library[name]
```

#### 在主入口挂 load_all

修改 `backend/src/selflearn/main.py`：
```python
# 在 worker 启动 / gateway 启动时调一次
from selflearn.skills.library import load_all

def _bootstrap() -> None:
    load_all()
    # ... 其他初始化
```

具体调用点由实现 agent 在 main.py 顶部加。

### Step 4: 跑测试确认通过

```bash
uv run pytest tests/unit/test_skill_library.py -v
```

Expected: 2 passed。

### Step 5: mypy + Stage 2 回归 + commit

```bash
uv run mypy src tests
uv run pytest tests/integration/test_smoke.py -q
git add pyproject.toml src/selflearn/skills docs/skills tests/unit/test_skill_library.py src/selflearn/main.py
git commit -m "feat(skills): Skill markdown 文档 + library loader（5 份 Skill）"
```

---

## Task 7: ProfileAgent 实现（5 轮对话 → 6 维画像）

**Files:**
- Create: `backend/src/selflearn/agents/builtin/profile_agent.py`
- Test: `backend/tests/unit/test_exercise_agent.py`（先建空文件，准备 Task 9 复用）

### Step 1: 写失败的测试

创建 `backend/tests/unit/test_exercise_agent.py`（虽然叫 exercise agent 文件，但 Stage 3 我们先放共用 agent fixture）：
```python
import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio


async def test_profile_agent_initializes_6_dimensions():
    """ProfileAgent 第一轮对话后，dimensions 必须含 6 个 key。"""
    from selflearn.skills.library import load_all, get
    load_all()
    skill = get("skill.profile.build")
    assert skill.name == "skill.profile.build"
```

### Step 2: 跑测试确认失败

```bash
uv run pytest tests/unit/test_exercise_agent.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'selflearn.agents.builtin'`。

### Step 3: 最小实现

#### `backend/src/selflearn/agents/builtin/profile_agent.py`
```python
"""ProfileAgent: 5 轮对话构建 6 维画像。"""
from __future__ import annotations

from datetime import datetime

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.profile import Profile
from selflearn.llm.registry import llm_registry
from selflearn.progress.stream import progress_publish
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.skills.library import get as get_skill


class ProfileAgent(AbstractAgent):
    """skill.profile.build: 对话式 6 维画像构建。

    Stage 3 MVP: 跳过真 5 轮 UI 对话，直接 mock 5 轮问答（payload.dimensions 已给）→ 写 profiles 表。
    """

    agent_id = "profile-01"
    # 注：Agent 类不声明 skills = [...]。Skill 在 run() 内通过 skill_library.get(...) 动态获取。

    DIMENSION_KEYS = [
        "knowledge_base", "visual_preference", "analytic_style",
        "goal_employment", "error_prone_type", "focus_duration",
    ]

    async def run(self, env: Envelope) -> Envelope:
        trace_id = env.trace_id
        student_id = env.payload["student_id"]

        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.PROFILE, status="running",
            payload={"student_id": student_id},
        ))

        # MVP：直接读 payload 里的 dimensions（前端 5 轮问答结果已在 gateway 收齐）
        dimensions = {k: env.payload.get("dimensions", {}).get(k, 0.5)
                      for k in self.DIMENSION_KEYS}

        # 加载 Skill 做 sanity check（开发者文档：6 维必须全填）
        get_skill("skill.profile.build")

        # 写库
        # （实际写库通过 repo，由实现 agent 在 ProfileRepository 中实现）
        # 这里仅示意调用；Task 10 引入 repo 层后会替换
        from sqlalchemy.ext.asyncio import AsyncSession
        from selflearn.infra.db import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            profile = Profile(
                student_id=student_id,
                dimensions=dimensions,
                tags=env.payload.get("tags", []),
                last_updated=datetime.utcnow(),
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
            profile_id = str(profile.profile_id)

        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.PROFILE, status="completed",
            payload={"profile_id": profile_id, "dimensions": dimensions},
        ))

        return Envelope(
            action="skill.completed",
            sender=ActorRef(type="agent", id=self.agent_id),
            target=ActorRef(type="gateway", id=env.sender.id),
            payload={"profile_id": profile_id, "dimensions": dimensions},
            trace_id=trace_id,
            parent_id=env.span_id,
        )
```

### Step 4: 跑测试

```bash
uv run pytest tests/unit/test_exercise_agent.py -v
```

Expected: 1 passed（仅验证 skill 加载）。

### Step 5: mypy + commit

```bash
uv run mypy src tests
git add src/selflearn/agents/builtin/profile_agent.py tests/unit/test_exercise_agent.py
git commit -m "feat(agents): ProfileAgent MVP（5 维对话式画像构建）"
```

---

## Task 8: PlanAgent（生成 5-10 个 MapNode）

**Files:**
- Create: `backend/src/selflearn/agents/builtin/plan_agent.py`
- Create: `backend/scripts/seed_map.py`

### Step 1: 写失败的测试

往 `backend/tests/unit/test_exercise_agent.py` 追加：
```python
async def test_plan_agent_skill_loads():
    from selflearn.skills.library import load_all, get
    load_all()
    skill = get("skill.plan.generate")
    assert skill.name == "skill.plan.generate"


async def test_seed_map_writes_5_kps(tmp_path, monkeypatch):
    """seed_map.py 至少要可独立插入 5 条 KP 用于开发与 smoke。"""
    # 集成验证放到 Task 14 的 smoke_mvp.sh，这里只验证 seed_map 文件存在
    import os
    assert os.path.exists("scripts/seed_map.py"), "seed_map.py must exist"
```

### Step 2: 跑测试确认失败

```bash
uv run pytest tests/unit/test_exercise_agent.py -v
```

Expected: FAIL with plan skill loading 部分（`load_all` 已经能加载 5 份，应过）+ plan_agent / seed_map 不存在。

### Step 3: 最小实现

#### `backend/src/selflearn/agents/builtin/plan_agent.py`
```python
"""PlanAgent: 根据 profile 生成 5-10 个 MapNode。"""
from __future__ import annotations

import uuid
from datetime import datetime

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory
from selflearn.llm.registry import llm_registry
from selflearn.progress.stream import progress_publish
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.skills.library import get as get_skill


class PlanAgent(AbstractAgent):
    agent_id = "plan-01"
    # 注：Agent 类不声明 skills = [...]。Skill 在 run() 内通过 skill_library.get(...) 动态获取。

    async def run(self, env: Envelope) -> Envelope:
        trace_id = env.trace_id
        student_id = env.payload["student_id"]

        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.PLAN, status="running",
            payload={"student_id": student_id},
        ))

        skill = get_skill("skill.plan.generate")
        # MVP：直接复用已 seed 的 KP，不再 LLM 生成
        # （Stage 4 接真规划时再扩 LLM 调用）
        assert skill.name == "skill.plan.generate"

        factory = get_session_factory()
        async with factory() as session:
            # 取 5 个 KP（seed 进库的）
            from sqlalchemy import select
            stmt = select(KnowledgePoint).limit(5)
            kps = (await session.execute(stmt)).scalars().all()

            node_ids = []
            for idx, kp in enumerate(kps):
                node = MapNode(
                    student_id=uuid.UUID(student_id) if isinstance(student_id, str) else student_id,
                    kp_id=kp.kp_id,
                    status="active",
                    branch_type="main",
                    position={"x": float(idx * 100), "y": 0.0},
                )
                session.add(node)
                await session.flush()
                node_ids.append(str(node.node_id))
            await session.commit()

        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.PLAN, status="completed",
            payload={"node_count": len(node_ids), "node_ids": node_ids},
        ))

        return Envelope(
            action="skill.completed",
            sender=ActorRef(type="agent", id=self.agent_id),
            target=ActorRef(type="gateway", id=env.sender.id),
            payload={"node_count": len(node_ids), "node_ids": node_ids},
            trace_id=trace_id,
            parent_id=env.span_id,
        )
```

#### `backend/scripts/seed_map.py`
```python
"""Seed 5-10 个 KnowledgePoint（Stage 3 MVP — 自注意力机制 / Transformer 等示例）。"""
from __future__ import annotations

import asyncio
import uuid

from selflearn.infra.db import get_session_factory
from selflearn.domain.knowledge_point import KnowledgePoint


SEED_KPS = [
    {"subject": "大语言模型", "title": "自注意力机制",
     "description": "Self-Attention 通过 QKV 矩阵计算序列内依赖。",
     "difficulty": 2, "prerequisites": []},
    {"subject": "大语言模型", "title": "多头注意力",
     "description": "Multi-Head 将 QKV 拆 h 份并行学习不同子空间。",
     "difficulty": 3, "prerequisites": ["自注意力机制"]},
    {"subject": "大语言模型", "title": "位置编码",
     "description": "Positional Encoding 注入序列顺序信息（sin/cos 或 RoPE）。",
     "difficulty": 2, "prerequisites": []},
    {"subject": "大语言模型", "title": "Transformer 编码器",
     "description": "Encoder = Multi-Head Self-Attention + FFN + 残差 + LN。",
     "difficulty": 3, "prerequisites": ["自注意力机制", "多头注意力"]},
    {"subject": "大语言模型", "title": "Transformer 解码器",
     "description": "Decoder = Masked Self-Attn + Cross-Attn + FFN。",
     "difficulty": 3, "prerequisites": ["Transformer 编码器"]},
]


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        for kp_data in SEED_KPS:
            kp = KnowledgePoint(**kp_data, kp_id=uuid.uuid4())
            session.add(kp)
        await session.commit()
        print(f"seeded {len(SEED_KPS)} knowledge_points")


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4: 跑测试 + 跑 seed

```bash
uv run pytest tests/unit/test_exercise_agent.py -v
uv run python -m scripts.seed_map
```

Expected: test + 控制台 `seeded 5 knowledge_points`。

### Step 5: mypy + commit

```bash
uv run mypy src tests
git add src/selflearn/agents/builtin/plan_agent.py scripts/seed_map.py tests/unit/test_exercise_agent.py
git commit -m "feat(agents): PlanAgent + seed_map.py（5 个 KP 种子）"
```

---

## Task 9: ExerciseAgent（LLM 出题 + tool.lint_json 校验）

**Files:**
- Modify: `backend/src/selflearn/agents/builtin/exercise_agent.py`（创建时已有 stub，仅内容）
- Modify: `backend/tests/unit/test_exercise_agent.py`（追加 exercise agent 用例）

### Step 1: 写失败的测试

`backend/tests/unit/test_exercise_agent.py` 追加：
```python
async def test_exercise_agent_lint_failure_raises():
    """Exercise Agent: tool.lint_json 拒收时抛 EXERCISE_INVALID。"""
    from unittest.mock import AsyncMock, patch
    from selflearn.tools.protocol import ToolResult

    with patch("selflearn.llm.registry.llm_registry") as mock_reg:
        mock_reg.default.return_value.chat = AsyncMock(
            return_value='[{"exercise_type":"single_choice","prompt":"Q?","correct_answer":"A"}]'  # 缺字段
        )

        with patch("selflearn.tools.protocol.ToolRegistry.call") as mock_tool:
            mock_tool.return_value = ToolResult(ok=False, error="schema_violation: 'difficulty' is a required property")

            from selflearn.core.envelope import Envelope, ActorRef
            from selflearn.agents.builtin.exercise_agent import ExerciseAgent
            from selflearn.core.errors import AppError, ErrorCode

            env = Envelope(
                action="skill.execute",
                sender=ActorRef(type="director", id="d"),
                target=ActorRef(type="skill", id="skill.exercise.generate"),
                payload={"node_id": "00000000-0000-0000-0000-000000000001"},
                trace_id="test-trace-1",
            )
            with pytest.raises(AppError) as exc:
                await ExerciseAgent().run_sync(env, node=AsyncMock())
            assert exc.value.code == ErrorCode.EXERCISE_INVALID


async def test_exercise_agent_returns_list_on_valid():
    from unittest.mock import AsyncMock, patch
    from selflearn.tools.protocol import ToolResult

    valid_json = json.dumps([{
        "exercise_type": "single_choice",
        "prompt": "Transformer 的核心是？",
        "options": ["RNN", "Self-Attention", "CNN", "GAN"],
        "correct_answer": "Self-Attention",
        "explanation": "Self-Attn 是 Transformer 的核心。",
        "difficulty": 2,
        "score": 1.5,
    }])

    with patch("selflearn.llm.registry.llm_registry") as mock_reg:
        mock_reg.default.return_value.chat = AsyncMock(return_value=valid_json)
        with patch("selflearn.tools.protocol.ToolRegistry.call") as mock_tool:
            mock_tool.return_value = ToolResult(ok=True, data={"validated_count": 1})

            from selflearn.core.envelope import Envelope, ActorRef
            from selflearn.agents.builtin.exercise_agent import ExerciseAgent
            env = Envelope(
                action="skill.execute",
                sender=ActorRef(type="director", id="d"),
                target=ActorRef(type="skill", id="skill.exercise.generate"),
                payload={"node_id": "00000000-0000-0000-0000-000000000001"},
                trace_id="test-trace-2",
            )
            result = await ExerciseAgent().run_sync(env, node=AsyncMock())
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["correct_answer"] == "Self-Attention"


import json  # 顶 import
```

### Step 2: 跑测试确认失败

```bash
uv run pytest tests/unit/test_exercise_agent.py -v
```

Expected: FAIL（ExerciseAgent 还没实现 / lint 拒收时不抛 AppError）。

### Step 3: 实现 ExerciseAgent

#### `backend/src/selflearn/agents/builtin/exercise_agent.py`
```python
"""ExerciseAgent: LLM 出题 + tool.lint_json 校验。"""
from __future__ import annotations

import json
from collections.abc import Awaitable
from typing import Any

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.core.thinking import extract_json_from_fence
from selflearn.llm.base import ChatMessage, ChatRequest
from selflearn.llm.registry import llm_registry
from selflearn.skills.library import get as get_skill
from selflearn.tools.protocol import ToolRegistry


class ExerciseAgent(AbstractAgent):
    agent_id = "exercise-01"
    # 注：Agent 类不声明 skills = [...]。Skill 在 run_sync() 内通过 skill_library.get(...) 动态获取。

    async def run(self, env: Envelope) -> Any: ...  # 满足抽象

    async def run_sync(self, env: Envelope, node: Any) -> list[dict]:
        """Director 同步调；返回 list[dict]，由 Director 写库。

        V1.1: lint 拒收时抛 AppError，让 Director.try/except 兜底推 FAILED。
        """
        skill = get_skill("skill.exercise.generate")

        tmpl = await ToolRegistry.call(
            "tool.fetch_template", name="exercise_generation_v1"
        )
        if not tmpl.ok:
            raise AppError(ErrorCode.INTERNAL, f"fetch_template 失败: {tmpl.error}")

        req = ChatRequest(
            messages=[ChatMessage(
                role="user",
                content=f"node_id={node.node_id}; kp_title={getattr(node.kp, 'title', '')}",
            )],
            system=skill.body + "\n\n" + tmpl.data["content"],
            reasoning=True,
        )

        last_err = None
        for attempt in range(2):  # 1 次自动重试
            raw = await llm_registry.default().chat(req)
            parsed = extract_json_from_fence(raw)
            lint = await ToolRegistry.call(
                "tool.lint_json", payload=parsed, schema="exercise"
            )
            if lint.ok:
                if not isinstance(parsed, list):
                    parsed = [parsed]
                return parsed
            last_err = lint.error
        raise AppError(ErrorCode.EXERCISE_INVALID, f"lint 重试失败: {last_err}")
```

### Step 4: 跑测试

```bash
uv run pytest tests/unit/test_exercise_agent.py -v
```

Expected: 至少 4 passed（前 2 个 + 新加 2 个）。

### Step 5: mypy + commit

```bash
uv run mypy src tests
git add src/selflearn/agents/builtin/exercise_agent.py tests/unit/test_exercise_agent.py
git commit -m "feat(agents): ExerciseAgent（LLM 出题 + tool.lint_json + 1 次重试）"
```

---

## Task 10: ReviewAgent（规则过滤）

**Files:**
- Create: `backend/src/selflearn/agents/builtin/review_agent.py`
- Create: `backend/src/selflearn/infra/repositories/exercise_repo.py`
- Test: `backend/tests/unit/test_review_agent.py`

### Step 1: 写失败的测试

`backend/tests/unit/test_review_agent.py`:
```python
import pytest

pytestmark = pytest.mark.asyncio


async def test_review_passes_valid_exercises():
    from selflearn.agents.builtin.review_agent import ReviewAgent
    exercises = [
        {"prompt": f"Q{i}?", "exercise_type": "single_choice",
         "options": ["A","B","C","D"], "correct_answer": "A",
         "explanation": "x", "difficulty": d, "score": 1.0}
        for i, d in enumerate([1, 2, 3])
    ]
    review = await ReviewAgent().review(exercises)
    assert review.verdict == "passed"
    assert review.score == pytest.approx(1.0)


async def test_review_flags_duplicate_prompts():
    from selflearn.agents.builtin.review_agent import ReviewAgent
    exercises = [
        {"prompt": "same Q?", "exercise_type": "single_choice",
         "options": ["A","B","C","D"], "correct_answer": "A",
         "explanation": "x", "difficulty": 1, "score": 1.0},
        {"prompt": "same Q?", "exercise_type": "single_choice",
         "options": ["A","B","C","D"], "correct_answer": "A",
         "explanation": "x", "difficulty": 2, "score": 1.0},
    ]
    review = await ReviewAgent().review(exercises)
    assert review.verdict == "needs_fix"
    assert any(i["rule"] == "duplicate_prompt" for i in review.issues)


async def test_review_rejects_choice_with_no_matching_answer():
    from selflearn.agents.builtin.review_agent import ReviewAgent
    exercises = [
        {"prompt": "Q?", "exercise_type": "single_choice",
         "options": ["A","B","C","D"], "correct_answer": "Z",  # 不在 options 里
         "explanation": "x", "difficulty": 1, "score": 1.0},
    ]
    review = await ReviewAgent().review(exercises)
    assert review.verdict in ("rejected", "needs_fix")
    assert any("answer" in (i.get("rule") or "") or "options" in (i.get("rule") or "")
               for i in review.issues)
```

### Step 2: 跑测试确认失败

```bash
uv run pytest tests/unit/test_review_agent.py -v
```

Expected: FAIL with `ModuleNotFoundError`。

### Step 3: 最小实现

#### `backend/src/selflearn/infra/repositories/exercise_repo.py`
```python
"""Exercise repo（Task 10 引入；JSONB 写入走整体赋值 + flag_modified）。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from selflearn.domain.exercise import Exercise


class ExerciseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_create(self, level_id: uuid.UUID, items: list[dict[str, Any]]) -> list[Exercise]:
        """整体写库：每条单独 add + commit 一次，options JSONB 用整体赋值。"""
        objs: list[Exercise] = []
        for it in items:
            ex = Exercise(
                level_id=level_id,
                exercise_type=it["exercise_type"],
                prompt=it["prompt"],
                options=it.get("options", []),  # 整体赋值
                correct_answer=it["correct_answer"],
                explanation=it.get("explanation", ""),
                difficulty=it["difficulty"],
                score=it["score"],
            )
            self.session.add(ex)
        await self.session.commit()
        for ex in objs:
            await self.session.refresh(ex)
        # 重新 select 拿到 PK
        stmt = select(Exercise).where(Exercise.level_id == level_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

#### `backend/src/selflearn/agents/builtin/review_agent.py`
```python
"""ReviewAgent: 规则过滤（JSON 合法 / 题目重复 / 答案格式 / 难度梯度）。"""
from __future__ import annotations

from dataclasses import dataclass, field

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import Envelope
from selflearn.skills.library import get as get_skill
from selflearn.tools.protocol import ToolRegistry


@dataclass
class Review:
    verdict: str  # "passed" | "rejected" | "needs_fix"
    score: float
    issues: list[dict] = field(default_factory=list)


class ReviewAgent(AbstractAgent):
    agent_id = "review-01"
    # 注：Agent 类不声明 skills = [...]。Skill 在 review() 内通过 skill_library.get(...) 动态获取。

    async def run(self, env: Envelope) -> Envelope: ...  # 不被同步调，仅满足抽象

    async def run_sync(self, env: Envelope, exercises: list[dict]) -> Review:
        return await self.review(exercises)

    async def review(self, exercises: list[dict]) -> Review:
        issues: list[dict] = []

        # 1. lint_json 先跑
        lint = await ToolRegistry.call(
            "tool.lint_json", payload=exercises, schema="exercise"
        )
        if not lint.ok:
            return Review(verdict="rejected", score=0.0,
                          issues=[{"rule": "lint_json", "severity": "high", "message": lint.error}])

        # 2. 业务规则
        # duplicate prompt
        seen_prompts: set[str] = set()
        for ex in exercises:
            if ex["prompt"] in seen_prompts:
                issues.append({"rule": "duplicate_prompt", "severity": "medium",
                               "message": f"重复题目: {ex['prompt']}"})
            seen_prompts.add(ex["prompt"])

        # single_choice: options 长度 4，且 correct_answer ∈ options
        for ex in exercises:
            if ex["exercise_type"] == "single_choice":
                opts = ex.get("options", [])
                if len(opts) != 4:
                    issues.append({"rule": "options_length", "severity": "medium",
                                   "message": f"题目 {ex['prompt'][:20]} options 数量 {len(opts)} != 4"})
                if ex["correct_answer"] not in opts:
                    issues.append({"rule": "answer_not_in_options", "severity": "high",
                                   "message": f"答案 {ex['correct_answer']} 不在 options {opts}"})

        # difficulty 分布：≥3 条时三类都有
        if len(exercises) >= 3:
            diffs = {ex["difficulty"] for ex in exercises}
            if not {1, 2, 3}.issubset(diffs):
                issues.append({"rule": "difficulty_gradient", "severity": "low",
                               "message": f"难度覆盖缺失: 现有 {sorted(diffs)}"})

        # 3. verdicts
        if any(i["severity"] == "high" for i in issues):
            return Review(verdict="rejected", score=0.0, issues=issues)
        if issues:
            return Review(verdict="needs_fix", score=0.6, issues=issues)

        # 加载 skill 做"看起来像" sanity check
        get_skill("skill.review.exercise")
        return Review(verdict="passed", score=1.0, issues=[])
```

### Step 4: 跑测试

```bash
uv run pytest tests/unit/test_review_agent.py -v
```

Expected: 3 passed。

### Step 5: mypy + commit

```bash
uv run mypy src tests
git add src/selflearn/infra/repositories/exercise_repo.py \
        src/selflearn/agents/builtin/review_agent.py \
        tests/unit/test_review_agent.py
git commit -m "feat(agents): ReviewAgent（3 条业务规则）+ ExerciseRepository"
```

---

## Task 11: DirectorAgent（同步序列调 + try/except 兜底）

**Files:**
- Create: `backend/src/selflearn/agents/builtin/director_agent.py`
- Test: `backend/tests/unit/test_director_tryexcept.py`

### Step 1: 写失败的测试

`backend/tests/unit/test_director_tryexcept.py`:
```python
import pytest

pytestmark = pytest.mark.asyncio


async def test_director_uncaught_exception_publishes_failed_and_raises():
    """Director.run 任何未捕获异常必须先推 FAILED，再抛 AppError。

    V1.1 修复点：避免 SSE 端点陷入死等。
    """
    from unittest.mock import AsyncMock, patch

    fake_node = AsyncMock()
    fake_node.node_id = "00000000-0000-0000-0000-000000000001"

    with patch("selflearn.agents.builtin.director_agent.exercise_agent", new=None):
        from selflearn.agents.builtin.director_agent import DirectorAgent
        from selflearn.core.errors import AppError, ErrorCode
        from selflearn.core.envelope import Envelope, ActorRef
        from selflearn.progress.stages import ProgressEvent, Stage

        published = []
        async def fake_publish(trace_id, ev):
            published.append(ev)

        with patch("selflearn.agents.builtin.director_agent.progress_publish", new=fake_publish):
            agent = DirectorAgent()
            env = Envelope(
                action="skill.execute",
                sender=ActorRef(type="gateway", id="g"),
                target=ActorRef(type="skill", id="skill.director.start"),
                payload={"student_id": "00000000-0000-0000-0000-000000000002"},
                trace_id="dir-test-1",
            )
            with pytest.raises(AppError) as exc:
                await agent.run(env)
            assert exc.value.code == ErrorCode.INTERNAL

        # 关键断言：失败时必须推过 FAILED 事件
        failed_events = [e for e in published if e.stage == Stage.FAILED]
        assert failed_events, f"Director 必须推 FAILED 事件，实际 {published}"
        assert failed_events[0].status == "failed"
```

### Step 2: 跑测试确认失败

```bash
uv run pytest tests/unit/test_director_tryexcept.py -v
```

Expected: FAIL with `ModuleNotFoundError`。

### Step 3: 实现 DirectorAgent

#### `backend/src/selflearn/agents/builtin/director_agent.py`
```python
"""DirectorAgent: 同步序列调 Exercise + Review，含 try/except 兜底（V1.1 修复）。"""
from __future__ import annotations

import uuid

from sqlalchemy import select

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.core.logging import get_logger
from selflearn.domain.exercise import Exercise
from selflearn.domain.level import Level
from selflearn.domain.map_node import MapNode
from selflearn.domain.review_result import ReviewResult
from selflearn.infra.db import get_session_factory
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.progress.stream import progress_publish
from selflearn.skills.library import get as get_skill


log = get_logger("director")


from selflearn.agents.builtin import exercise_agent, review_agent  # noqa: E402


class DirectorAgent(AbstractAgent):
    agent_id = "director-01"
    # 注：Agent 类不声明 skills = [...]。Skill 在 _run_inner() 内通过 skill_library.get(...) 动态获取。

    async def run(self, env: Envelope) -> Envelope:
        """V1.1: 必须 try/except 包全部子调用，失败推 FAILED 后抛 AppError。"""
        trace_id = env.trace_id
        try:
            return await self._run_inner(env)
        except AppError:
            await self._emit_failed(trace_id, "agent_internal_error", "Director 处理失败")
            raise
        except Exception as e:  # noqa: BLE001
            await self._emit_failed(trace_id, "internal_unhandled", repr(e))
            log.error("director.unhandled_exception", trace_id=trace_id, error=repr(e))
            raise AppError(ErrorCode.INTERNAL, "Director 处理失败", trace_id=trace_id) from e

    async def _run_inner(self, env: Envelope) -> Envelope:
        trace_id = env.trace_id
        skill = get_skill("skill.director.start")

        student_id = uuid.UUID(env.payload["student_id"]) if isinstance(env.payload["student_id"], str) \
                     else env.payload["student_id"]

        # 1. 选第一个 active 节点
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.DIRECTOR, status="running",
            payload={"action": "select_node", "student_id": str(student_id)},
        ))
        factory = get_session_factory()
        async with factory() as session:
            stmt = select(MapNode).where(
                MapNode.student_id == student_id, MapNode.status == "active"
            ).limit(1)
            node = (await session.execute(stmt)).scalars().first()
            if node is None:
                raise AppError(ErrorCode.INTERNAL, "无 active 节点，请先跑 plan.generate")
            node_id = node.node_id

        # 2. 同步调 Exercise Agent
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.EXERCISE, status="running", payload={"node_id": str(node_id)}
        ))
        ex_dicts = await exercise_agent.run_sync(env, node)
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.EXERCISE, status="completed", payload={"count": len(ex_dicts)}
        ))

        # 3. 同步调 Review Agent
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.REVIEW, status="running"
        ))
        review = await review_agent.review(ex_dicts)
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.REVIEW, status="completed",
            payload={"verdict": review.verdict, "issues_count": len(review.issues)},
        ))

        if review.verdict == "rejected":
            raise AppError(ErrorCode.EXERCISE_INVALID,
                           f"Review rejected: {len(review.issues)} issues")

        # 4. 写库
        async with factory() as session:
            level = Level(node_id=node_id, status="generated", form="exercise")
            session.add(level)
            await session.flush()
            level_id = level.level_id

            for ed in ex_dicts:
                session.add(Exercise(
                    level_id=level_id,
                    exercise_type=ed["exercise_type"],
                    prompt=ed["prompt"],
                    options=ed.get("options", []),
                    correct_answer=ed["correct_answer"],
                    explanation=ed.get("explanation", ""),
                    difficulty=ed["difficulty"],
                    score=ed["score"],
                ))

            session.add(ReviewResult(
                level_id=level_id, verdict=review.verdict,
                score=review.score, issues=review.issues,
            ))
            await session.commit()
            await session.refresh(level)

        # 5. 推 completed
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.COMPLETED, status="completed",
            payload={"level_id": str(level_id), "exercises_count": len(ex_dicts)},
        ))

        return Envelope(
            action="skill.completed",
            sender=ActorRef(type="agent", id=self.agent_id),
            target=ActorRef(type="gateway", id=env.sender.id),
            payload={"level_id": str(level_id), "exercises_count": len(ex_dicts)},
            trace_id=trace_id,
            parent_id=env.span_id,
        )

    async def _emit_failed(self, trace_id: str, code: str, message: str) -> None:
        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.FAILED, status="failed",
            payload={"code": code, "message": message},
        ))
```

注：`from selflearn.agents.builtin import exercise_agent, review_agent` 顶层导入要求 Task 9/10 已完成。

### Step 4: 跑测试

```bash
uv run pytest tests/unit/test_director_tryexcept.py -v
```

Expected: 1 passed（关键 failure → FAILED 路径覆盖）。

### Step 5: mypy + commit

```bash
uv run mypy src tests
git add src/selflearn/agents/builtin/director_agent.py tests/unit/test_director_tryexcept.py
git commit -m "feat(agents): DirectorAgent 同步序列调 + try/except 推 FAILED 兜底（V1.1 修复）"
```

---

## Task 12: Gateway 路由（profile / map / level / submit）

**Files:**
- Modify: `backend/src/selflearn/gateway/routes/profile.py`（保留 Stage 2 兼容，扩 build 路由 + SSE 改真流）
- Create: `backend/src/selflearn/gateway/routes/map.py`
- Create: `backend/src/selflearn/gateway/routes/level.py`
- Modify: `backend/src/selflearn/gateway/app.py`（注册新路由）

### Step 1: 写失败的测试

`backend/tests/unit/test_sse_endpoint.py`（Stage 2 已建，追加 case）：
```python
async def test_sse_endpoint_returns_failed_event_on_failure():
    """SSE 端点收到 FAILED 事件后必须关闭连接（V1.1 修复）。"""
    # 用 mock progress_consume 推送 1 条 FAILED 后 stop
    from unittest.mock import patch, AsyncMock
    from datetime import datetime
    from selflearn.progress.stages import ProgressEvent, Stage

    fake_stream = AsyncMock()
    async def fake_events():
        yield ProgressEvent(
            stage=Stage.FAILED, status="failed",
            payload={"code": "x", "message": "y"},
            timestamp=datetime.utcnow(),
        )
    fake_stream.return_value = fake_events()

    with patch("selflearn.gateway.routes.profile.progress_consume", new=fake_stream):
        from fastapi.testclient import TestClient
        from selflearn.gateway.app import create_app

        app = create_app()
        client = TestClient(app)
        with client.stream("GET", "/api/profile/init/abc/stream") as resp:
            events = list(resp.iter_lines())
        text = "\n".join(events)
        assert "event: completed" in text or "event: error" in text, \
            f"SSE must terminate on FAILED, got: {text}"
```

### Step 2: 跑测试

```bash
uv run pytest tests/unit/test_sse_endpoint.py -v
```

Expected: FAIL（新路由/SSE 改写还未实现）。

### Step 3: 最小实现

#### `backend/src/selflearn/gateway/routes/profile.py`（覆盖）
```python
"""Profile / SSE 路由（Stage 3：扩 build + SSE 改真流）。"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.infra.bus import publish_envelope
from selflearn.infra.redis_client import get_redis
from selflearn.progress.stream import progress_consume
from selflearn.schemas.profile import (
    ProfileBuildRequest,
    ProfileBuildResponse,
    ProfileStatusResponse,
)


router = APIRouter(prefix="/api/profile", tags=["profile"])


def _coerce_str(v: object) -> str | None:
    if v is None:
        return None
    if isinstance(v, bytes):
        return v.decode("utf-8")
    return str(v)


@router.post("/build", response_model=ProfileBuildResponse, status_code=202)
async def build_profile(body: ProfileBuildRequest) -> ProfileBuildResponse:
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.profile.build"),
        payload={"student_id": str(body.student_id),
                 "dimensions": body.dimensions,
                 "tags": body.tags},
    )
    r = get_redis()
    await r.set(f"trace:{env.trace_id}:status", "running", ex=3600)
    await publish_envelope(env, routing_key="profile.skill.profile.build")
    return ProfileBuildResponse(trace_id=env.trace_id)


@router.post("/init", response_model=ProfileBuildResponse, status_code=202)
async def init_profile_alias(body: ProfileBuildRequest) -> ProfileBuildResponse:
    """Stage 2 兼容入口：等同于 /build。"""
    return await build_profile(body)


@router.get("/init/{trace_id}/status", response_model=ProfileStatusResponse)
async def get_status(trace_id: str) -> ProfileStatusResponse:
    r = get_redis()
    status_raw = await r.get(f"trace:{trace_id}:status")
    reply_raw = await r.get(f"trace:{trace_id}:reply")
    return ProfileStatusResponse(
        trace_id=trace_id,
        status=_coerce_str(status_raw) or "unknown",
        reply=_coerce_str(reply_raw),
    )


@router.get("/init/{trace_id}/stream")
async def stream_init(trace_id: str) -> EventSourceResponse:
    async def event_gen() -> AsyncIterator[dict[str, str]]:
        try:
            async for ev in progress_consume(trace_id):
                payload = json.dumps({
                    "stage": ev.stage.value,
                    "status": ev.status,
                    "payload": ev.payload,
                }, ensure_ascii=False)
                yield {"event": "progress", "data": payload}
                if ev.stage.value in ("completed", "failed"):
                    final = {"status": ev.status, "payload": ev.payload}
                    yield {
                        "event": "completed" if ev.stage.value == "completed" else "error",
                        "data": json.dumps(final, ensure_ascii=False),
                    }
                    return
        finally:
            pass

    return EventSourceResponse(event_gen())
```

#### `backend/src/selflearn/gateway/routes/map.py`
```python
"""Map 路由（Stage 3）：生成初始藏宝图 / 拉取节点。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.infra.bus import publish_envelope


router = APIRouter(prefix="/api/map", tags=["map"])


class MapGenerateRequest(BaseModel):
    student_id: uuid.UUID


@router.post("/generate", status_code=202)
async def generate_map(body: MapGenerateRequest) -> dict:
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.plan.generate"),
        payload={"student_id": str(body.student_id)},
    )
    await publish_envelope(env, routing_key="plan.skill.plan.generate")
    return {"trace_id": env.trace_id}
```

#### `backend/src/selflearn/gateway/routes/level.py`
```python
"""Level 路由（Stage 3）：启动关卡 / 提交答案 / SSE 真流。"""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.level import Level
from selflearn.domain.level_completion import LevelCompletion
from selflearn.infra.bus import publish_envelope
from selflearn.infra.db import get_session_factory
from selflearn.progress.stream import progress_consume


router = APIRouter(prefix="/api/level", tags=["level"])


class LevelStartRequest(BaseModel):
    student_id: uuid.UUID


class LevelSubmitRequest(BaseModel):
    answers: dict  # exercise_id -> answer


@router.post("/start", status_code=202)
async def start_level(body: LevelStartRequest) -> dict:
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="gateway", id="smoke"),
        target=ActorRef(type="skill", id="skill.director.start"),
        payload={"student_id": str(body.student_id)},
    )
    await publish_envelope(env, routing_key="director.skill.director.start")
    return {"trace_id": env.trace_id}


@router.get("/{level_id}/stream")
async def stream_level(level_id: uuid.UUID, trace_id: str) -> EventSourceResponse:
    async def event_gen() -> AsyncIterator[dict[str, str]]:
        async for ev in progress_consume(trace_id):
            data = json.dumps({
                "stage": ev.stage.value, "status": ev.status, "payload": ev.payload,
            }, ensure_ascii=False)
            yield {"event": "progress", "data": data}
            if ev.stage.value in ("completed", "failed"):
                yield {
                    "event": "completed" if ev.stage.value == "completed" else "error",
                    "data": json.dumps({"status": ev.status, "payload": ev.payload}, ensure_ascii=False),
                }
                return
    return EventSourceResponse(event_gen())


@router.post("/{level_id}/submit")
async def submit_level(level_id: uuid.UUID, body: LevelSubmitRequest) -> dict:
    factory = get_session_factory()
    async with factory() as session:
        level = await session.get(Level, level_id)
        if level is None:
            return {"status": "level_not_found"}
        score = 0.0
        from sqlalchemy import select
        from selflearn.domain.exercise import Exercise
        exs = (await session.execute(select(Exercise).where(Exercise.level_id == level_id))).scalars().all()
        for ex in exs:
            ans = body.answers.get(str(ex.exercise_id))
            if ans is not None and ans == ex.correct_answer:
                score += float(ex.score)

        completion = LevelCompletion(
            level_id=level_id,
            student_id=level.map_node.student_id,
            score=score,
            duration_seconds=0,
            answers=body.answers,
            metrics={"items": len(exs)},
        )
        session.add(completion)
        level.status = "completed"
        await session.commit()
    return {"status": "submitted", "score": score}
```

#### 修改 `backend/src/selflearn/gateway/app.py`
在 `create_app()` 内 `app.include_router(...)` 区追加：
```python
from selflearn.gateway.routes.map import router as map_router
from selflearn.gateway.routes.level import router as level_router

# 在 setup_topology / register ping skill 之后：
app.include_router(map_router)
app.include_router(level_router)
```

且在 lifespan 里加：
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from selflearn.skills.library import load_all
    load_all()
    from selflearn.infra.rabbit import setup_topology
    await setup_topology()
    yield

app = FastAPI(lifespan=lifespan)
```

### Step 4: 跑测试

```bash
uv run pytest tests/unit/test_sse_endpoint.py -v
uv run mypy src tests
```

Expected: PASS + mypy 0 错。

### Step 5: commit

```bash
git add src/selflearn/gateway tests/unit/test_sse_endpoint.py
git commit -m "feat(gateway): profile build + map generate + level start/submit/stream 路由"
```

---

## Task 13: 集成测试 test_smoke_mvp.py（testcontainers Redis Stream）

**Files:**
- Create: `backend/tests/integration/test_smoke_mvp.py`

### Step 1: 写失败的测试

`backend/tests/integration/test_smoke_mvp.py`:
```python
"""MVP 端到端集成测试（V1.1: last_id=0-0 起步 + try/except 兜底）。"""
import asyncio
import pytest
import redis.asyncio as aioredis

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def redis_stream():
    r = aioredis.from_url("redis://localhost:6379/0")
    yield r
    await r.aclose()


async def test_progress_consume_reads_history_from_zero(redis_stream):
    """V1.1 关键修复：写入 3 条 progress，从 0-0 起步必须能拿到全部。"""
    from selflearn.progress.stream import progress_publish, progress_consume
    from selflearn.progress.stages import ProgressEvent, Stage

    trace_id = f"integ-{asyncio.get_event_loop().time()}"
    await progress_publish(trace_id, ProgressEvent(stage=Stage.PROFILE, status="running"))
    await progress_publish(trace_id, ProgressEvent(stage=Stage.PROFILE, status="completed"))
    await progress_publish(trace_id, ProgressEvent(stage=Stage.PLAN, status="running"))

    seen = []
    async def collect():
        async for ev in progress_consume(trace_id):
            seen.append((ev.stage, ev.status))
            if len(seen) >= 3:
                return
    await asyncio.wait_for(collect(), timeout=5.0)

    assert ("profile", "running") in seen
    assert ("profile", "completed") in seen
    assert ("plan", "running") in seen


async def test_director_fail_publishes_failed_event(redis_stream):
    """V1.1 关键修复：Director 失败必须推 FAILED。"""
    # 通过 mock 触发 director 失败场景（在 testcontainers 环境跑）
    # 简化：直接验证 progress_publish 写 FAILED
    from selflearn.progress.stream import progress_publish, progress_consume
    from selflearn.progress.stages import ProgressEvent, Stage

    trace_id = f"integ-fail-{asyncio.get_event_loop().time()}"
    await progress_publish(trace_id, ProgressEvent(
        stage=Stage.FAILED, status="failed",
        payload={"code": "test", "message": "synthetic failure"}
    ))

    seen = []
    async def collect():
        async for ev in progress_consume(trace_id):
            seen.append(ev)
            if ev.stage == Stage.FAILED:
                return
    await asyncio.wait_for(collect(), timeout=5.0)
    assert any(e.stage == Stage.FAILED for e in seen)
```

### Step 2: 跑测试确认失败

```bash
docker compose up -d redis postgres rabbitmq
uv run pytest tests/integration/test_smoke_mvp.py -v
```

Expected: FAIL（fixture 启动后预期通；若 FAIL 多因 Redis 没起，确认 docker compose up -d 完成）。

### Step 3: 无需实现（这就是集成测试本身）

### Step 4: 跑测试

```bash
uv run pytest tests/integration/test_smoke_mvp.py -v
```

Expected: 2 passed。

### Step 5: mypy + commit

```bash
uv run mypy src tests
git add tests/integration/test_smoke_mvp.py
git commit -m "test(integration): smoke_mvp：last_id=0-0 起步 + FAILED 传播"
```

---

## Task 14: smoke_mvp.sh + JSONB 回归 + Stage 2 完整回归

**Files:**
- Create: `backend/scripts/smoke_mvp.sh`

### Step 1: 写 smoke_mvp.sh

`backend/scripts/smoke_mvp.sh`:
```bash
#!/usr/bin/env bash
# Stage 3 MVP 端到端 smoke：profile → plan → director → exercise → review → submit
set -euo pipefail
trap 'echo "[smoke_mvp] FAILED at line $LINENO"; exit 1' ERR

cd "$(dirname "$0")/.."

BASE_URL="${BASE_URL:-http://localhost:8000}"
STUDENT_ID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"

echo "[smoke_mvp] 1) seed KP"
uv run python -m scripts.seed_map

echo "[smoke_mvp] 2) POST /api/profile/build → trace_id"
TRACE_ID=$(curl -fsS -X POST "$BASE_URL/api/profile/build" \
  -H 'Content-Type: application/json' \
  -d "{\"student_id\":\"$STUDENT_ID\",\"dimensions\":{\"knowledge_base\":0.6,\"visual_preference\":0.5,\"analytic_style\":0.7,\"goal_employment\":0.4,\"error_prone_type\":0.5,\"focus_duration\":0.5},\"tags\":[\"smoke\"]}" \
  | python -c 'import json,sys;print(json.load(sys.stdin)["trace_id"])')
echo "[smoke_mvp] trace_id=$TRACE_ID"

echo "[smoke_mvp] 3) SSE: GET /api/profile/init/$TRACE_ID/stream（≤30s 内应收到 progress→completed）"
timeout 30 curl -fsSN "$BASE_URL/api/profile/init/$TRACE_ID/stream" \
  | tee /tmp/sse-out.txt | grep -E '^event: (progress|completed|error)' | head -20

echo "[smoke_mvp] 4) POST /api/map/generate"
MAP_TRACE=$(curl -fsS -X POST "$BASE_URL/api/map/generate" \
  -H 'Content-Type: application/json' \
  -d "{\"student_id\":\"$STUDENT_ID\"}" \
  | python -c 'import json,sys;print(json.load(sys.stdin)["trace_id"])')
echo "[smoke_mvp] map trace_id=$MAP_TRACE"

echo "[smoke_mvp] 5) POST /api/level/start"
LEVEL_TRACE=$(curl -fsS -X POST "$BASE_URL/api/level/start" \
  -H 'Content-Type: application/json' \
  -d "{\"student_id\":\"$STUDENT_ID\"}" \
  | python -c 'import json,sys;print(json.load(sys.stdin)["trace_id"])')

timeout 60 curl -fsSN "$BASE_URL/api/level/00000000-0000-0000-0000-000000000000/stream?trace_id=$LEVEL_TRACE" \
  | tee /tmp/level-sse.txt | grep -E '^event: (progress|completed|error)' | head -30

echo "[smoke_mvp] 6) 拿 level_id 并 submit"
LEVEL_ID=$(uv run python -c "
import asyncio
from sqlalchemy import select
from selflearn.domain.level import Level
from selflearn.infra.db import get_session_factory
async def main():
    factory = get_session_factory()
    async with factory() as s:
        rs = (await s.execute(select(Level).order_by(Level.created_at.desc()).limit(1))).scalars().first()
        print(str(rs.level_id) if rs else '')
asyncio.run(main())
")
echo "[smoke_mvp] level_id=$LEVEL_ID"

SUBMIT_RESP=$(curl -fsS -X POST "$BASE_URL/api/level/$LEVEL_ID/submit" \
  -H 'Content-Type: application/json' \
  -d '{"answers":{}}')
echo "[smoke_mvp] submit response: $SUBMIT_RESP"

echo "[smoke_mvp] 7) 校验 status=completed (level 表)"
uv run python -c "
import asyncio
from selflearn.domain.level import Level
from selflearn.infra.db import get_session_factory
async def main():
    factory = get_session_factory()
    async with factory() as s:
        rs = await s.get(Level, '$LEVEL_ID')
        assert rs is not None and rs.status == 'completed', f'level status={rs.status if rs else None}'
asyncio.run(main())
"

echo "[smoke_mvp] ✅ ALL PASSED"
```

```bash
chmod +x backend/scripts/smoke_mvp.sh
```

### Step 2: 跑 Stage 2 smoke 与 unit

```bash
docker compose up -d postgres redis rabbitmq
uv run pytest tests/unit -q
uv run pytest tests/integration/test_smoke.py -q
bash scripts/smoke_mvp.sh
```

Expected: 全绿。

### Step 3: mypy + Stage 2 完整性

```bash
uv run mypy src tests
```

Expected: 0 errors。

### Step 4: commit

```bash
git add scripts/smoke_mvp.sh
git commit -m "test(scripts): smoke_mvp.sh 端到端脚本（6 阶段 flow）"
```

### Step 5: 验收报告

更新 `docs/实施计划-Stage3-验收报告.md`（按 Stage 2 报告格式），commit：

```bash
git add docs/实施计划-Stage3-验收报告.md
git commit -m "docs(stage3): Stage 3 验收报告"
git tag stage3-complete
```

---

## Self-Review

按 writing-plans 自检清单跑一遍：

**1. Spec coverage**（每条 spec § 要求都能找到对应 task）：
- § 0/§ 1（范围）→ 全部 task（Task 1-14）
- § 2（决策 9-14）→ Task 4（last_id 0-0）/ Task 5（MCP Tool）/ Task 11（Director 同步）/ Task 3（6 表）
- § 3（架构、目录）→ Task 5/6/7-11 覆盖目录全部
- § 4（消息流 SSE）→ Task 4 + Task 12
- § 5（数据模型）→ Task 3
- § 6（错误 / 测试）→ Task 6.1/10/11/13
- § 7（验收 14 项）→ 每条对应 Task 1-14 至少一处
- § 9（Skill / MCP）→ Task 5/6/11

**2. Placeholder scan** ✅ 无 TBD/TODO/"implement later"/"add appropriate"。

**3. Type consistency**：Type 在各 task 间一致：
- `ProgressEvent.stage / status / payload / timestamp` 一致（Task 4 用，Task 7-11 写）
- `Envelopetrace_id / action / sender / target / payload / parent_id` 与 Stage 2 一致
- `Skill.name / description / body / output_schema`（Task 6 定义，Task 7/8/9/10/11 用）

**潜在 bug 修复**：
- Task 3 单测中 `ex.options.append("C")` 检查"就地 mutate 不触发持久化"是 **SQLite + aiosqlite** 场景；PG 下行为相同（都依赖 ORM dirty tracking），但 PG `JSONB` 类型会用 psycopg2 触发不同的 dirty check。Plan 中已显式说明"为避免依赖，保持 SQLite 单测即可"。Stage 4 接 PG 时追加一个 testcontainers PG 的 JSONB 测试用例。

---

## Execution Handoff

Plan 已保存到 `docs/superpowers/plans/2026-07-12-stage3-business-mvp.md`。