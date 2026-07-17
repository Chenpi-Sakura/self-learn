# 六维画像冷启动生成（Onboarding）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让首次进站的学生通过 8 道情境题（7 单选/多选 + 1 开放文本）触发 LLM 单 chat 评分，得到六维画像初始值（kb/vp/as/ge/ept/fd），写入 `Profile.dimensions` 并创建 trigger=`onboarding` 的 snapshot。

**Architecture:** 预制 JSON 题库 → 用户答完 → 路由 `/api/onboarding/submit` 同步调 `tool.onboard_profile` → LLM 单 chat 输出 6 维分 → clamp 兜底 → `create_profile` upsert + `ProfileSnapshot(trigger="onboarding")` 写入 → 前端 `App.tsx` 守卫检测 `dimensions` 全 0.5 时强制渲染 `<Onboarding />`。

**Tech Stack:** FastAPI + Pydantic + sse_starlette（不用，onboarding 同步）+ SQLAlchemy 2.0 + LLMAgent（`selflearn.agents.core`）+ Markdown skill prompt + React + vitest + pytest + mypy。

---

## Global Constraints

| # | 约束 | 来源 |
|---|------|------|
| 1 | 单账户 `KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"` 4 处硬编码保持一致 | `CLAUDE.md` |
| 2 | branch 直 main，不开 worktree | memory `no-worktrees-sdd` |
| 3 | 中文 commit message | `CLAUDE.md` |
| 4 | Docker 代理 `HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897` | `CLAUDE.md` |
| 5 | 无登录鉴权 | memory `no-auth-no-login` |
| 6 | 6 维短名 `kb/vp/as/ge/ept/fd`、长名 `knowledge_base/visual_preference/analytic_style/goal_employment/error_prone_type/focus_duration` 全部沿用 | `backend/src/selflearn/gateway/routes/profile.py:150-157` + `backend/skills/skill.profile.build/SKILL.md:12` + `frontend/src/components/ProfileRadar.tsx:17-24` |
| 7 | `ProfileSnapshot.profile` JSON（不是 JSONB，字段名是 `profile` 不是 `dimensions`） | `backend/src/selflearn/domain/profile_snapshot.py` |
| 8 | 前端 Notion Serif 风格 + HedvigLettersSerif 字体 + `ProgressOverlay` 同款遮罩 | `frontend/src/components/ProgressOverlay.tsx` |
| 9 | Profile 已是默认 0.5 不能再 onboarding（防覆盖学习成果） | spec 路由层 409 |
| 10 | onboarding 不动 envelope 异步总线 | bus 仅供异步 skill.execute |
| 11 | TDD：先写 failing 测试，再实现，再 verify，再 commit | `CLAUDE.md` |
| 12 | LLM 调用统一走 `selflearn.agents.core.LLMAgent.run(skill_id, env)` | `backend/src/selflearn/agents/core.py` |
| 13 | JSON lint 走 `selflearn.mcp_server.tools.lint_json` + `extract_json_from_fence` 容错 | `backend/src/selflearn/core/thinking.py` |
| 14 | 前端测 vitest 单文件用 `vitest run` + `--reporter=verbose`，参考 `frontend/src/components/__tests__/` 现有写法（如有） | `frontend/package.json` |
| 15 | 后端测 `cd backend && uv run pytest tests/unit/<file>.py -v -p no:warnings` | `backend/pyproject.toml` |
| 16 | E2E 走 `scripts/smoke_mvp.sh` + `uv run python -m scripts.purge_test_data` | `backend/scripts/` |

---

## 文件结构（实施前心智模型）

**6 新 + 3 改**：

| 文件 | 职责 |
|------|------|
| **新增** `backend/src/selflearn/data/onboarding_questions.json` | 题库：8 道题 JSON |
| **新增** `backend/skills/skill.profile.onboard/SKILL.md` | LLM prompt body（system） |
| **新增** `backend/src/selflearn/mcp_server/tools/onboard_profile.py` | `tool.onboard_profile(student_id, answers, agent)` |
| **新增** `backend/src/selflearn/gateway/routes/onboarding.py` | HTTP 路由 `GET /api/onboarding/questions` + `POST /api/onboarding/submit` |
| **新增** `frontend/src/api/onboarding.ts` | `fetchOnboardingQuestions` + `submitOnboarding` |
| **新增** `frontend/src/components/Onboarding.tsx` | 全屏问卷组件 |
| **新增** `frontend/src/utils/profile.ts` | `isProfileInitialized(dims)` |
| **改** `backend/src/selflearn/mcp_server/server.py` | 注册 `onboard_profile` tool |
| **改** `backend/src/selflearn/main.py` | 挂载 onboarding router |
| **改** `frontend/src/App.tsx` | 路由守卫：`isProfileInitialized=false` → 渲染 `<Onboarding />` |

**测试文件**（每个 task 配套 1 个）：

| 测试文件 | 覆盖 |
|---------|------|
| `backend/tests/unit/test_onboarding_questions_json.py` | JSON 契约（8 题 / 6 维覆盖 / 最后 1 题 open） |
| `backend/tests/unit/test_onboard_profile_tool.py` | tool 主路径 + clamp + 缺维度 + lint 失败 |
| `backend/tests/unit/test_onboarding_route.py` | GET / POST + 409 + 400 + 500 |
| `frontend/src/utils/__tests__/profile.test.ts` | `isProfileInitialized` 三种 case |
| `frontend/src/components/__tests__/Onboarding.test.tsx` | 渲染 / 状态机 / submit / error |

---

## Task 1: 题库 JSON + Skill markdown + JSON 契约测试

**Files:**
- Create: `backend/src/selflearn/data/onboarding_questions.json`
- Create: `backend/skills/skill.profile.onboard/SKILL.md`
- Create: `backend/tests/unit/test_onboarding_questions_json.py`

**Interfaces:**
- Consumes: 无（数据契约测试）
- Produces:
  - `onboarding_questions.json` 加载后是 `list[dict]`，每题有 `id/dimension_hint/type/prompt/options?/placeholder?`
  - `SKILL.md` 含 frontmatter `name: skill.profile.onboard` + Markdown body
  - 测试 `test_questions_meet_contract()` 验证：8 道 / 6 维覆盖 / 最后 1 题 open

---

- [ ] **Step 1: 创建题库 JSON 文件**

写 `backend/src/selflearn/data/onboarding_questions.json`：

```json
[
  {
    "id": "q1_kb",
    "dimension_hint": "kb",
    "type": "single",
    "prompt": "遇到一个全新概念，你的第一反应是？",
    "options": [
      { "id": "a", "label": "先找它的定义和理论来源" },
      { "id": "b", "label": "看几个例子理解它的用法" },
      { "id": "c", "label": "直接动手试一试" },
      { "id": "d", "label": "找同学或老师讨论一下" }
    ]
  },
  {
    "id": "q2_vp",
    "dimension_hint": "vp",
    "type": "single",
    "prompt": "下面哪种资料对你最有吸引力？",
    "options": [
      { "id": "a", "label": "详细的图表与流程图" },
      { "id": "b", "label": "完整的文字说明" },
      { "id": "c", "label": "音频或视频讲解" },
      { "id": "d", "label": "可以亲手操作的小实验" }
    ]
  },
  {
    "id": "q3_as",
    "dimension_hint": "as",
    "type": "single",
    "prompt": "解一道难题时，你倾向：",
    "options": [
      { "id": "a", "label": "一步步严格推导" },
      { "id": "b", "label": "先想一个直觉，再补细节" },
      { "id": "c", "label": "类比熟悉的场景找答案" },
      { "id": "d", "label": "直接尝试不同解法看哪种能跑通" }
    ]
  },
  {
    "id": "q4_ge",
    "dimension_hint": "ge",
    "type": "single",
    "prompt": "你学习这门课的主要目标更接近：",
    "options": [
      { "id": "a", "label": "拿到一份工程师 / 实习 offer" },
      { "id": "b", "label": "通过学校课程考试" },
      { "id": "c", "label": "纯粹兴趣 / 提升视野" },
      { "id": "d", "label": "为转方向或读研打基础" }
    ]
  },
  {
    "id": "q5_ept",
    "dimension_hint": "ept",
    "type": "single",
    "prompt": "过去学习时，你最常在哪类问题上卡住？",
    "options": [
      { "id": "a", "label": "概念辨析（似是而非的术语）" },
      { "id": "b", "label": "计算与公式推导" },
      { "id": "c", "label": "把知识用到具体场景" },
      { "id": "d", "label": "记忆细节与例外" }
    ]
  },
  {
    "id": "q6_fd",
    "dimension_hint": "fd",
    "type": "single",
    "prompt": "你能保持高效专注学习的连续时长一般是：",
    "options": [
      { "id": "a", "label": "15 分钟以内" },
      { "id": "b", "label": "15-30 分钟" },
      { "id": "c", "label": "30-60 分钟" },
      { "id": "d", "label": "60 分钟以上" }
    ]
  },
  {
    "id": "q7_mixed",
    "dimension_hint": "as",
    "type": "multi",
    "prompt": "下面哪些描述符合你？（可多选）",
    "options": [
      { "id": "a", "label": "我喜欢把问题拆解成一步步的小任务" },
      { "id": "b", "label": "我经常从结果反推原因" },
      { "id": "c", "label": "我倾向于记口诀或顺口溜" },
      { "id": "d", "label": "我倾向于画图或列表" }
    ]
  },
  {
    "id": "q8_open",
    "type": "open",
    "prompt": "请用一两句话描述：你理想的学习方式是什么？",
    "placeholder": "比如：我喜欢先看图，再看例子，最后总结…"
  }
]
```

- [ ] **Step 2: 创建 Skill markdown**

写 `backend/skills/skill.profile.onboard/SKILL.md`：

```markdown
---
name: skill.profile.onboard
description: "Use when a first-time student answers 8 onboarding scenario questions. Evaluates the student on 6 dimensions (kb/vp/as/ge/ept/fd) and outputs scores in [0,1] + reasoning."
mcp_prefetch: []
mcp_tool_use: []
max_retries: 2
---

# Profile Onboard — 六维画像冷启动评分

你是 SelfLearn 的画像评估助手。下面有 8 道情境题和学生的回答。
请根据**全部回答**给出学生在 6 个维度上的评分（0.0 ~ 1.0），并写一段中文 reasoning。

## 6 维度定义（短名 — 长名 — 含义）

- **kb** — `knowledge_base`（知识基础）：对新概念的接受速度；是否已有扎实基础
- **vp** — `visual_preference`（视觉偏好）：对图像、图表、视频等视觉材料的偏好程度
- **as** — `analytic_style`（分析风格）：偏向演绎（一步步推导）还是归纳（先看案例）
- **ge** — `goal_employment`（求职目标）：学习目标与就业/职业发展的关联程度
- **ept** — `error_prone_type`（易错类型）：哪类问题最容易卡住（概念 / 计算 / 应用 / 记忆）
- **fd** — `focus_duration`（专注时长）：能保持高效学习的连续时长（短→低，长→高）

## 输入

user message 是 JSON，包含：
- `questions`: 题列表（元素含 `id` / `prompt` / `type` / `options?` / `dimension_hint?`）
- `answers`: 学生回答（元素含 `question_id` / `choice` / `free_text?`）

请通读所有回答，对每个维度给出一个 [0,1] 的分数。

## 评分原则

- **不要被单题选项的字面值带偏**：dimension_hint 是软提示，主要看选项语义
- **多选/开放题**通常信号更强，要重点参考
- 缺维度（signal 不足）→ 给 0.5
- 分数可以是 0.0 ~ 1.0 的任意小数，保留 2 位
- reasoning 用中文 100~200 字，简述 AI 怎么从回答中得出这些分数

## 输出 JSON schema

```json
{
  "type": "object",
  "properties": {
    "kb":  { "type": "number", "minimum": 0, "maximum": 1 },
    "vp":  { "type": "number", "minimum": 0, "maximum": 1 },
    "as":  { "type": "number", "minimum": 0, "maximum": 1 },
    "ge":  { "type": "number", "minimum": 0, "maximum": 1 },
    "ept": { "type": "number", "minimum": 0, "maximum": 1 },
    "fd":  { "type": "number", "minimum": 0, "maximum": 1 },
    "reasoning": { "type": "string" }
  },
  "required": ["kb","vp","as","ge","ept","fd","reasoning"]
}
```

只输出 JSON，不要任何解释文字。
```

- [ ] **Step 3: 写 JSON 契约测试**

写 `backend/tests/unit/test_onboarding_questions_json.py`：

```python
"""Onboarding 题库 JSON 契约测试 — 防止后续改题库破坏 LLM skill prompt 输入。"""
from __future__ import annotations

import json
from pathlib import Path

QUESTION_FILE = Path(
    "backend/src/selflearn/data/onboarding_questions.json"  # 从 backend/ 跑
)
SHORT_KEYS = {"kb", "vp", "as", "ge", "ept", "fd"}


def _load() -> list[dict]:
    return json.loads(QUESTION_FILE.read_text(encoding="utf-8"))


def test_total_count_between_7_and_8() -> None:
    qs = _load()
    assert 7 <= len(qs) <= 8, f"题数应在 7-8，实际 {len(qs)}"


def test_all_six_dimensions_covered_as_hint() -> None:
    qs = _load()
    hinted = {q.get("dimension_hint") for q in qs if "dimension_hint" in q}
    missing = SHORT_KEYS - hinted
    assert not missing, f"6 维未被 dimension_hint 覆盖: {missing}"


def test_last_question_is_open_type() -> None:
    qs = _load()
    last = qs[-1]
    assert last["type"] == "open", f"最后一题应 open，实际 {last['type']}"
    assert "placeholder" in last and last["placeholder"], "开放题需 placeholder"


def test_single_questions_have_options() -> None:
    qs = _load()
    for q in qs:
        if q["type"] in ("single", "multi"):
            assert "options" in q, f"题 {q['id']} 缺 options"
            assert len(q["options"]) >= 3, f"题 {q['id']} 选项数应 >= 3"
            ids = [o["id"] for o in q["options"]]
            assert len(ids) == len(set(ids)), f"题 {q['id']} 选项 id 重复"


def test_all_ids_unique() -> None:
    qs = _load()
    ids = [q["id"] for q in qs]
    assert len(ids) == len(set(ids)), f"题 id 重复: {ids}"
```

- [ ] **Step 4: 跑测试验证 pass（数据已合规）**

```bash
cd backend && uv run pytest tests/unit/test_onboarding_questions_json.py -v -p no:warnings 2>&1 | tail -10
```

Expected: `5 passed`（题库 JSON 已合规；测试是"正向"测试，必须 PASS 才说明数据 OK）。

- [ ] **Step 5: 跑 mypy 检查**

```bash
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
```

Expected: `Success: no issues found in N source files`（无新增 src 代码但确认 baseline）。

- [ ] **Step 6: Commit**

```bash
cd D:/Projects/SelfLearn && git add backend/src/selflearn/data/onboarding_questions.json backend/skills/skill.profile.onboard/SKILL.md backend/tests/unit/test_onboarding_questions_json.py && git commit -m "feat(onboarding): 题库 JSON + LLM skill prompt + 数据契约测试"
```

---

## Task 2: `tool.onboard_profile` + MCP server 注册 + 单测

**Files:**
- Create: `backend/src/selflearn/mcp_server/tools/onboard_profile.py`
- Create: `backend/tests/unit/test_onboard_profile_tool.py`
- Modify: `backend/src/selflearn/mcp_server/server.py`（注册 tool）

**Interfaces:**
- Consumes:
  - `LLMAgent.run(skill_id="skill.profile.onboard", env)` 返回 `str`（lint 过的 JSON）
  - `extract_json_from_fence` 容错（`backend/src/selflearn/core/thinking.py`）
  - `tool.create_profile(student_id, dimensions, tags)` 已有
  - `tool.get_profile(student_id)` 已有
- Produces:
  - `async def onboard_profile(student_id, answers, agent) -> dict`：
    - 成功：`{"ok": True, "dimensions": {...6 短 key...}, "reasoning": str, "snapshot_id": int}`
    - 已 onboarding：`{"ok": False, "error": "already_onboarded"}`
    - lint 失败：`{"ok": False, "error": "onboard_lint_failed"}`
  - 注册后 `tool.onboard_profile` 可被 `agent.mcp.call("tool.onboard_profile", ...)` 调用

---

- [ ] **Step 1: 写 failing test**

写 `backend/tests/unit/test_onboard_profile_tool.py`：

```python
"""tool.onboard_profile 单测：mock LLM 路径 + clamp + 缺维度 + 重复 onboarding。"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from selflearn.mcp_server.tools.onboard_profile import onboard_profile


def _fake_env() -> dict[str, Any]:
    return {
        "trace_id": "test-trace",
        "sender": {"type": "test", "id": "test"},
        "target": {"type": "skill", "id": "skill.profile.onboard"},
        "payload": {"student_id": "sid"},
    }


def _fake_agent(llm_output: str) -> MagicMock:
    """Mock LLMAgent.run 返回固定字符串。"""
    agent = MagicMock()
    agent.run = AsyncMock(return_value=llm_output)
    return agent


def _good_dims_payload() -> str:
    return json.dumps(
        {
            "kb": 0.72,
            "vp": 0.55,
            "as": 0.80,
            "ge": 0.30,
            "ept": 0.65,
            "fd": 0.45,
            "reasoning": "从你的回答来看...",
        },
        ensure_ascii=False,
    )


@pytest.mark.asyncio
async def test_onboard_profile_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """正常：LLM 返回合规 JSON → tool 写 profile + snapshot，返回 ok=True。"""
    created: list[dict] = []
    snapshots: list[dict] = []

    async def fake_get_profile(student_id: str) -> dict:
        return {"ok": False, "error": "profile_not_found"}

    async def fake_create_profile(student_id: str, dimensions: dict, tags: list | None = None) -> dict:
        created.append({"student_id": student_id, "dimensions": dimensions, "tags": tags})
        return {"ok": True, "profile_id": "pid-123", "updated": False}

    async def fake_write_snapshot(student_id: str, profile: dict, trigger: str) -> int:
        snapshots.append({"student_id": student_id, "profile": profile, "trigger": trigger})
        return 42

    monkeypatch.setattr(
        "selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile
    )
    monkeypatch.setattr(
        "selflearn.mcp_server.tools.onboard_profile.create_profile", fake_create_profile
    )
    monkeypatch.setattr(
        "selflearn.mcp_server.tools.onboard_profile._write_snapshot", fake_write_snapshot
    )

    agent = _fake_agent(_good_dims_payload())
    answers = [{"question_id": "q1_kb", "choice": "a"}]

    result = await onboard_profile("sid", answers, agent)

    assert result["ok"] is True
    assert result["dimensions"]["kb"] == 0.72
    assert result["dimensions"]["as"] == 0.80
    assert result["snapshot_id"] == 42
    assert created[0]["tags"] == ["onboarded"]
    assert snapshots[0]["trigger"] == "onboarding"


@pytest.mark.asyncio
async def test_onboard_profile_clamp_out_of_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 返回 1.5 / -0.3 → tool clamp 到 [0,1]。"""
    async def fake_get_profile(student_id: str) -> dict:
        return {"ok": False, "error": "profile_not_found"}

    async def fake_create_profile(student_id: str, dimensions: dict, tags: list | None = None) -> dict:
        return {"ok": True, "profile_id": "p", "updated": False}

    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile)
    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.create_profile", fake_create_profile)
    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile._write_snapshot",
                        AsyncMock(return_value=1))

    payload = json.dumps({
        "kb": 1.5, "vp": -0.3, "as": 0.5,
        "ge": 0.5, "ept": 0.5, "fd": 0.5,
        "reasoning": "test",
    })
    agent = _fake_agent(payload)

    result = await onboard_profile("sid", [], agent)

    assert result["ok"] is True
    assert result["dimensions"]["kb"] == 1.0
    assert result["dimensions"]["vp"] == 0.0


@pytest.mark.asyncio
async def test_onboard_profile_missing_dim_defaults_to_half(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 只返回 4 维 → 缺维度补 0.5。"""
    async def fake_get_profile(student_id: str) -> dict:
        return {"ok": False, "error": "profile_not_found"}

    async def fake_create_profile(student_id: str, dimensions: dict, tags: list | None = None) -> dict:
        return {"ok": True, "profile_id": "p", "updated": False}

    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile)
    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.create_profile", fake_create_profile)
    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile._write_snapshot",
                        AsyncMock(return_value=1))

    payload = json.dumps({
        "kb": 0.7, "vp": 0.3, "as": 0.5, "ge": 0.5,
        "reasoning": "缺 ept 和 fd",
    })
    agent = _fake_agent(payload)

    result = await onboard_profile("sid", [], agent)

    assert result["dimensions"]["kb"] == 0.7
    assert result["dimensions"]["ept"] == 0.5  # 补默认
    assert result["dimensions"]["fd"] == 0.5


@pytest.mark.asyncio
async def test_onboard_profile_already_initialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Profile 已有非默认 dimensions → 返回 already_onboarded，不调 LLM。"""
    async def fake_get_profile(student_id: str) -> dict:
        return {
            "ok": True,
            "profile_id": "p",
            "dimensions": {"kb": 0.8, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
            "tags": [],
        }

    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile)

    agent = _fake_agent(_good_dims_payload())
    result = await onboard_profile("sid", [], agent)

    assert result == {"ok": False, "error": "already_onboarded"}
    agent.run.assert_not_called()  # LLM 不能被调


@pytest.mark.asyncio
async def test_onboard_profile_lint_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 返回完全非 JSON → 返回 onboard_lint_failed。"""
    async def fake_get_profile(student_id: str) -> dict:
        return {"ok": False, "error": "profile_not_found"}

    monkeypatch.setattr("selflearn.mcp_server.tools.onboard_profile.get_profile", fake_get_profile)

    agent = _fake_agent("not json at all")
    result = await onboard_profile("sid", [], agent)

    assert result["ok"] is False
    assert result["error"] == "onboard_lint_failed"
```

- [ ] **Step 2: 跑测试验证 fail（tool 不存在）**

```bash
cd backend && uv run pytest tests/unit/test_onboard_profile_tool.py -v -p no:warnings 2>&1 | tail -15
```

Expected: 5 个测试全 FAIL（ImportError: cannot import name 'onboard_profile'）。

- [ ] **Step 3: 实现 `tool.onboard_profile`**

写 `backend/src/selflearn/mcp_server/tools/onboard_profile.py`：

```python
"""tool.onboard_profile — 6 维画像冷启动生成。

LLM 单 chat 评分（基于 8 道情境题回答）→ clamp + 缺维度兜底 → create_profile + snapshot。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from selflearn.core.envelope import ActorRef, Envelope
from selflearn.core.errors import AppError, ErrorCode
from selflearn.core.thinking import extract_json_from_fence
from selflearn.domain.profile_snapshot import ProfileSnapshot
from selflearn.infra.db import get_session_factory

from selflearn.mcp_server.tools.create_profile import create_profile
from selflearn.mcp_server.tools.get_profile import get_profile

log = logging.getLogger("onboard_profile")

DIM_SHORT_KEYS = ("kb", "vp", "as", "ge", "ept", "fd")
DEFAULT_DIM_VALUE = 0.5


def _is_initialized(dims: dict[str, Any] | None) -> bool:
    """Profile 已有非默认 dimensions 视为已 onboarding。"""
    if not dims:
        return False
    return any(
        abs(float(dims.get(k, DEFAULT_DIM_VALUE)) - DEFAULT_DIM_VALUE) > 1e-6
        for k in DIM_SHORT_KEYS
    )


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _normalize_dims(raw: dict[str, Any]) -> dict[str, float]:
    """6 维齐全 + clamp [0,1] + 缺失补 0.5。"""
    out: dict[str, float] = {}
    for k in DIM_SHORT_KEYS:
        v = raw.get(k)
        if isinstance(v, (int, float)):
            out[k] = round(_clamp(float(v)), 2)
        else:
            out[k] = DEFAULT_DIM_VALUE
    return out


async def _write_snapshot(student_id: str, profile: dict[str, float], trigger: str) -> int:
    """写 ProfileSnapshot（trigger="onboarding"）。返回 snapshot.id。"""
    factory = get_session_factory()
    async with factory() as session:
        snap = ProfileSnapshot(
            student_id=student_id,
            profile=profile,
            trigger=trigger,
            created_at=datetime.now(timezone.utc),
        )
        session.add(snap)
        await session.commit()
        await session.refresh(snap)
        return int(snap.id)


async def onboard_profile(
    student_id: str,
    answers: list[dict[str, Any]],
    agent: Any,
) -> dict[str, Any]:
    """LLM 单 chat 评分 → clamp → create_profile + snapshot。

    Returns:
      成功：{"ok": True, "dimensions", "reasoning", "snapshot_id"}
      已 onboarding：{"ok": False, "error": "already_onboarded"}
      lint 失败：{"ok": False, "error": "onboard_lint_failed"}
    """
    # 1. 防御：已 onboarding 直接拒绝
    existing = await get_profile(student_id)
    if existing.get("ok") and _is_initialized(existing.get("dimensions")):
        return {"ok": False, "error": "already_onboarded"}

    # 2. 构造 envelope + 调 LLM skill（走 agent.run 走 lint 链）
    env = Envelope(
        action="skill.execute",
        sender=ActorRef(type="tool", id="onboard_profile"),
        target=ActorRef(type="skill", id="skill.profile.onboard"),
        payload={
            "student_id": student_id,
            "answers": answers,
        },
    )
    try:
        llm_output = await agent.run("skill.profile.onboard", env)
    except AppError as e:
        log.warning("onboard_profile.agent_run_failed", error=str(e))
        return {"ok": False, "error": "onboard_lint_failed"}

    # 3. 解析 LLM JSON（容错：fence/裸 JSON 都行）
    try:
        parsed = extract_json_from_fence(llm_output) if isinstance(llm_output, str) else llm_output
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if not isinstance(parsed, dict):
            raise ValueError("LLM output is not a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        log.warning("onboard_profile.parse_failed", error=str(e), raw=llm_output[:200])
        return {"ok": False, "error": "onboard_lint_failed"}

    # 4. 归一化（clamp + 缺维度补 0.5）
    dimensions = _normalize_dims(parsed)
    reasoning = str(parsed.get("reasoning", ""))

    # 5. 写 profile + snapshot
    create_result = await create_profile(student_id, dimensions, tags=["onboarded"])
    if not create_result.get("ok"):
        return {"ok": False, "error": "profile_write_failed"}

    snapshot_id = await _write_snapshot(student_id, dimensions, trigger="onboarding")

    return {
        "ok": True,
        "dimensions": dimensions,
        "reasoning": reasoning,
        "snapshot_id": snapshot_id,
    }
```

- [ ] **Step 4: 跑测试验证 pass**

```bash
cd backend && uv run pytest tests/unit/test_onboard_profile_tool.py -v -p no:warnings 2>&1 | tail -15
```

Expected: `5 passed`。

- [ ] **Step 5: 注册 tool 到 MCP server**

读 `backend/src/selflearn/mcp_server/server.py`，找到现有 tool 注册的位置（看是否已有 registry / @tool 装饰器），追加：

```python
from selflearn.mcp_server.tools.onboard_profile import onboard_profile

# 在现有 tool 注册块中加：
# 命名约定：tool.onboard_profile（参考 tool.create_profile / tool.update_profile）
tool_registry.register(name="tool.onboard_profile", fn=onboard_profile)
```

如果现有 server.py 用的是函数式 dispatch（查 `mcp_server/server.py` 全文确认），就改成对应的注册形式。**Step 5 前必须先读 server.py 当前结构再写 patch**。

- [ ] **Step 6: 跑回归**

```bash
cd backend && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
```

Expected: pytest 全 PASS（183+）；mypy clean。

- [ ] **Step 7: Commit**

```bash
cd D:/Projects/SelfLearn && git add backend/src/selflearn/mcp_server/tools/onboard_profile.py backend/src/selflearn/mcp_server/server.py backend/tests/unit/test_onboard_profile_tool.py && git commit -m "feat(mcp): onboard_profile tool + 5 个单测（happy/clamp/missing/already/lint）"
```

---

## Task 3: HTTP 路由 + 单测

**Files:**
- Create: `backend/src/selflearn/gateway/routes/onboarding.py`
- Create: `backend/src/selflearn/gateway/schemas/onboarding.py`
- Create: `backend/tests/unit/test_onboarding_route.py`
- Modify: `backend/src/selflearn/main.py`（挂路由）

**Interfaces:**
- Consumes:
  - `tool.onboard_profile(student_id, answers, agent)`（Task 2）
  - 题库 JSON（Task 1）
- Produces:
  - `GET /api/onboarding/questions` → `{"questions": list[dict]}`
  - `POST /api/onboarding/submit` → 200 `{dimensions, reasoning, snapshot_id}` / 409 `{error: "already_onboarded"}` / 400 `{error: "answers_mismatch"}` / 500 `{error: "onboard_failed"}`

---

- [ ] **Step 1: 写 Pydantic schema**

写 `backend/src/selflearn/gateway/schemas/onboarding.py`：

```python
"""Onboarding 路由请求/响应 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class OnboardingAnswer(BaseModel):
    question_id: str
    choice: str | list[str] | None = None
    free_text: str | None = None


class OnboardingSubmitRequest(BaseModel):
    student_id: str
    answers: list[OnboardingAnswer] = Field(..., min_length=1)


class OnboardingSubmitResponse(BaseModel):
    dimensions: dict[str, float]
    reasoning: str
    snapshot_id: int


class OnboardingQuestionsResponse(BaseModel):
    questions: list[dict]
```

- [ ] **Step 2: 写 failing 路由测试**

写 `backend/tests/unit/test_onboarding_route.py`：

```python
"""Onboarding HTTP 路由测试。"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from selflearn.gateway.routes.onboarding import router

QUESTION_FILE = Path(__file__).parent.parent.parent / "src/selflearn/data/onboarding_questions.json"


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_get_questions_returns_8(client: TestClient) -> None:
    res = client.get("/api/onboarding/questions")
    assert res.status_code == 200
    data = res.json()
    assert "questions" in data
    assert 7 <= len(data["questions"]) <= 8


def test_post_submit_success(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    fake_agent = MagicMock()
    fake_agent.run = AsyncMock(return_value=json.dumps({
        "kb": 0.7, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5,
        "reasoning": "ok",
    }, ensure_ascii=False))

    async def fake_onboard(student_id, answers, agent):
        return {
            "ok": True,
            "dimensions": {"kb": 0.7, "vp": 0.5, "as": 0.5, "ge": 0.5, "ept": 0.5, "fd": 0.5},
            "reasoning": "ok",
            "snapshot_id": 99,
        }

    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._run_onboard",
        fake_onboard,
    )
    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._build_agent",
        lambda: fake_agent,
    )

    payload = {
        "student_id": "sid",
        "answers": [
            {"question_id": "q1_kb", "choice": "a"},
        ],
    }
    res = client.post("/api/onboarding/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["dimensions"]["kb"] == 0.7
    assert data["snapshot_id"] == 99


def test_post_submit_already_onboarded(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    async def fake_onboard(student_id, answers, agent):
        return {"ok": False, "error": "already_onboarded"}

    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._run_onboard", fake_onboard
    )
    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._build_agent",
        lambda: MagicMock(),
    )

    res = client.post(
        "/api/onboarding/submit",
        json={"student_id": "sid", "answers": [{"question_id": "q1_kb", "choice": "a"}]},
    )
    assert res.status_code == 409
    assert res.json()["error"] == "already_onboarded"


def test_post_submit_answers_mismatch(client: TestClient) -> None:
    """answers 为空 → Pydantic min_length=1 → 422。"""
    res = client.post(
        "/api/onboarding/submit",
        json={"student_id": "sid", "answers": []},
    )
    assert res.status_code == 422


def test_post_submit_llm_failure(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    async def fake_onboard(student_id, answers, agent):
        return {"ok": False, "error": "onboard_lint_failed"}

    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._run_onboard", fake_onboard
    )
    monkeypatch.setattr(
        "selflearn.gateway.routes.onboarding._build_agent",
        lambda: MagicMock(),
    )

    res = client.post(
        "/api/onboarding/submit",
        json={"student_id": "sid", "answers": [{"question_id": "q1_kb", "choice": "a"}]},
    )
    assert res.status_code == 500
    assert res.json()["error"] == "onboard_failed"
```

- [ ] **Step 3: 跑测试验证 fail**

```bash
cd backend && uv run pytest tests/unit/test_onboarding_route.py -v -p no:warnings 2>&1 | tail -10
```

Expected: 全 FAIL（路由不存在 / ImportError）。

- [ ] **Step 4: 实现路由**

写 `backend/src/selflearn/gateway/routes/onboarding.py`：

```python
"""Onboarding 路由：GET 题库 / POST 提交（同步调 tool.onboard_profile）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from selflearn.gateway.schemas.onboarding import (
    OnboardingQuestionsResponse,
    OnboardingSubmitRequest,
    OnboardingSubmitResponse,
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

QUESTION_FILE = (
    Path(__file__).parent.parent.parent / "src/selflearn/data/onboarding_questions.json"
)


def _load_questions() -> list[dict]:
    return json.loads(QUESTION_FILE.read_text(encoding="utf-8"))


def _build_agent() -> Any:
    """构造 LLMAgent 实例（路由层懒加载，避免 import 期副作用）。"""
    from selflearn.agents.core import LLMAgent
    from selflearn.llm.registry import LLMRegistry
    from selflearn.mcp_client import MCPClient

    registry = LLMRegistry()
    registry._register_default_adapters()  # noqa: SLF001
    mcp = MCPClient()
    return LLMAgent(mcp, registry)


async def _run_onboard(
    student_id: str, answers: list[dict[str, Any]], agent: Any
) -> dict[str, Any]:
    """调 tool.onboard_profile（tool 注册由 MCP server 维护）。"""
    from selflearn.mcp_server.tools.onboard_profile import onboard_profile
    return await onboard_profile(student_id, answers, agent)


@router.get("/questions", response_model=OnboardingQuestionsResponse)
async def get_questions() -> OnboardingQuestionsResponse:
    """读题库 JSON 返回（HTTP 缓存由前端控制）。"""
    return OnboardingQuestionsResponse(questions=_load_questions())


@router.post("/submit", response_model=OnboardingSubmitResponse)
async def submit(body: OnboardingSubmitRequest) -> OnboardingSubmitResponse:
    """同步调 LLM 评分 → 返回 6 维分 + reasoning + snapshot_id。"""
    agent = _build_agent()
    answers_payload = [a.model_dump() for a in body.answers]
    result = await _run_onboard(body.student_id, answers_payload, agent)

    if result.get("ok"):
        return OnboardingSubmitResponse(
            dimensions=result["dimensions"],
            reasoning=result.get("reasoning", ""),
            snapshot_id=int(result["snapshot_id"]),
        )

    err = result.get("error", "unknown")
    if err == "already_onboarded":
        raise HTTPException(status_code=409, detail="already_onboarded")
    if err == "answers_mismatch":
        raise HTTPException(status_code=400, detail="answers_mismatch")
    # onboard_lint_failed / profile_write_failed 等
    raise HTTPException(status_code=500, detail="onboard_failed")
```

**注意**：`_build_agent` 用的是单测时的 `MCPClient` mock — 单测里 `monkeypatch.setattr("selflearn.gateway.routes.onboarding._build_agent", lambda: MagicMock())` 替换。

- [ ] **Step 5: 挂载路由**

读 `backend/src/selflearn/main.py`，找到现有 `app.include_router(...)` 块，追加：

```python
from selflearn.gateway.routes.onboarding import router as onboarding_router

# 在其他 include_router 旁边加：
app.include_router(onboarding_router)
```

- [ ] **Step 6: 跑测试验证 pass**

```bash
cd backend && uv run pytest tests/unit/test_onboarding_route.py -v -p no:warnings 2>&1 | tail -10
```

Expected: `5 passed`。

- [ ] **Step 7: 跑回归 + mypy**

```bash
cd backend && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
```

Expected: 全 PASS；mypy clean。

- [ ] **Step 8: Commit**

```bash
cd D:/Projects/SelfLearn && git add backend/src/selflearn/gateway/routes/onboarding.py backend/src/selflearn/gateway/schemas/onboarding.py backend/src/selflearn/main.py backend/tests/unit/test_onboarding_route.py && git commit -m "feat(gateway): onboarding 路由 (GET questions / POST submit) + 5 个单测"
```

---

## Task 4: 前端 api + utils + 组件 + 单测

**Files:**
- Create: `frontend/src/api/onboarding.ts`
- Create: `frontend/src/utils/profile.ts`
- Create: `frontend/src/components/Onboarding.tsx`
- Create: `frontend/src/utils/__tests__/profile.test.ts`
- Create: `frontend/src/components/__tests__/Onboarding.test.tsx`

**Interfaces:**
- Consumes: `apiGet` / `apiPost`（`frontend/src/api/client.ts`），`useSession`（`frontend/src/store/session.ts` 取 studentId）
- Produces:
  - `fetchOnboardingQuestions(): Promise<Question[]>`
  - `submitOnboarding(sid, answers): Promise<OnboardingSubmitResponse>`
  - `isProfileInitialized(dims): boolean`
  - `<Onboarding studentId onDone />` 全屏组件

---

- [ ] **Step 1: 写前端 utils + 测试**

写 `frontend/src/utils/profile.ts`：

```typescript
export const SHORT_KEYS = ['kb', 'vp', 'as', 'ge', 'ept', 'fd'] as const;
export type ShortKey = (typeof SHORT_KEYS)[number];

/**
 * Profile 是否已初始化（非 null 且 6 维不全 0.5）。
 * - null/undefined → 未初始化（首次）
 * - 全 0.5 → 未初始化（默认初值）
 * - 任一维 ≠ 0.5 → 已初始化（onboarding 完成 或 director 驱动过）
 */
export function isProfileInitialized(
  dims?: Record<string, number> | null
): boolean {
  if (!dims) return false;
  return SHORT_KEYS.some(
    (k) => Math.abs((dims[k] ?? 0.5) - 0.5) > 1e-6
  );
}
```

写 `frontend/src/utils/__tests__/profile.test.ts`：

```typescript
import { describe, it, expect } from 'vitest';
import { isProfileInitialized, SHORT_KEYS } from '../profile';

describe('isProfileInitialized', () => {
  it('null → false', () => {
    expect(isProfileInitialized(null)).toBe(false);
    expect(isProfileInitialized(undefined)).toBe(false);
  });

  it('全 0.5 → false (默认初值)', () => {
    const dims = Object.fromEntries(SHORT_KEYS.map((k) => [k, 0.5]));
    expect(isProfileInitialized(dims)).toBe(false);
  });

  it('任一维 ≠ 0.5 → true', () => {
    const dims = Object.fromEntries(SHORT_KEYS.map((k) => [k, 0.5]));
    dims.kb = 0.72;
    expect(isProfileInitialized(dims)).toBe(true);
  });

  it('空对象 → false (视为未初始化)', () => {
    expect(isProfileInitialized({})).toBe(false);
  });
});
```

- [ ] **Step 2: 跑测试验证 pass**

```bash
cd frontend && npx vitest run src/utils/__tests__/profile.test.ts --reporter=verbose 2>&1 | tail -10
```

Expected: `4 passed`。

- [ ] **Step 3: 写前端 api**

写 `frontend/src/api/onboarding.ts`：

```typescript
import { apiGet, apiPost } from './client';

export interface QuestionOption {
  id: string;
  label: string;
}

export interface Question {
  id: string;
  dimension_hint?: string;
  type: 'single' | 'multi' | 'open';
  prompt: string;
  options?: QuestionOption[];
  placeholder?: string;
}

export interface OnboardingAnswer {
  question_id: string;
  choice?: string | string[];
  free_text?: string;
}

export interface OnboardingSubmitResponse {
  dimensions: Record<string, number>;
  reasoning: string;
  snapshot_id: number;
}

export async function fetchOnboardingQuestions(): Promise<Question[]> {
  const res = await apiGet<{ questions: Question[] }>('/api/onboarding/questions');
  return res.questions;
}

export async function submitOnboarding(
  studentId: string,
  answers: OnboardingAnswer[]
): Promise<OnboardingSubmitResponse> {
  return apiPost<OnboardingSubmitResponse>('/api/onboarding/submit', {
    student_id: studentId,
    answers,
  });
}
```

- [ ] **Step 4: 写 Onboarding 组件**

写 `frontend/src/components/Onboarding.tsx`：

```tsx
import { useEffect, useState } from 'react';
import {
  fetchOnboardingQuestions,
  submitOnboarding,
  type Question,
  type OnboardingAnswer,
} from '../api/onboarding';

type Status = 'loading' | 'answering' | 'submitting' | 'error';

interface Props {
  studentId: string;
  onDone: () => void;
}

export function Onboarding({ studentId, onDone }: Props) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [qIdx, setQIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, OnboardingAnswer>>({});
  const [status, setStatus] = useState<Status>('loading');
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    fetchOnboardingQuestions()
      .then((qs) => {
        setQuestions(qs);
        setStatus('answering');
      })
      .catch(() => {
        setErrorMsg('问卷加载失败，请刷新重试');
        setStatus('error');
      });
  }, []);

  if (status === 'loading') {
    return <FullScreenShell><Center>加载中...</Center></FullScreenShell>;
  }

  if (status === 'error' && questions.length === 0) {
    return (
      <FullScreenShell>
        <Center>
          <ErrorText>{errorMsg}</ErrorText>
          <button onClick={() => location.reload()}>刷新</button>
        </Center>
      </FullScreenShell>
    );
  }

  const q = questions[qIdx];
  const ans = answers[q.id] ?? { question_id: q.id };
  const isLast = qIdx === questions.length - 1;
  const canNext = isAnswered(q, ans);

  function handleSingle(optId: string) {
    setAnswers((a) => ({
      ...a,
      [q.id]: { question_id: q.id, choice: optId },
    }));
  }

  function handleMulti(optId: string) {
    setAnswers((a) => {
      const cur = (a[q.id]?.choice as string[] | undefined) ?? [];
      const next = cur.includes(optId)
        ? cur.filter((x) => x !== optId)
        : [...cur, optId];
      return { ...a, [q.id]: { question_id: q.id, choice: next } };
    });
  }

  function handleOpen(text: string) {
    setAnswers((a) => ({
      ...a,
      [q.id]: { question_id: q.id, free_text: text },
    }));
  }

  async function handleSubmit() {
    setStatus('submitting');
    setErrorMsg('');
    try {
      const payload: OnboardingAnswer[] = questions.map((qq) => ({
        question_id: qq.id,
        choice: answers[qq.id]?.choice,
        free_text: answers[qq.id]?.free_text,
      }));
      await submitOnboarding(studentId, payload);
      onDone();
    } catch (e) {
      setErrorMsg(`提交失败：${String(e)}，请重试`);
      setStatus('answering');
    }
  }

  return (
    <FullScreenShell>
      <Header>
        <Progress>
          问题 {qIdx + 1} / {questions.length}
        </Progress>
        <ProgressBar value={(qIdx + 1) / questions.length} />
      </Header>

      <QuestionCard>
        <Prompt>{q.prompt}</Prompt>

        {q.type === 'single' &&
          q.options?.map((opt) => (
            <Option
              key={opt.id}
              selected={ans.choice === opt.id}
              onClick={() => handleSingle(opt.id)}
            >
              <Radio checked={ans.choice === opt.id} />
              <span>{opt.label}</span>
            </Option>
          ))}

        {q.type === 'multi' &&
          q.options?.map((opt) => {
            const cur = (ans.choice as string[] | undefined) ?? [];
            const checked = cur.includes(opt.id);
            return (
              <Option
                key={opt.id}
                selected={checked}
                onClick={() => handleMulti(opt.id)}
              >
                <CheckBox checked={checked} />
                <span>{opt.label}</span>
              </Option>
            );
          })}

        {q.type === 'open' && (
          <OpenTextarea
            value={ans.free_text ?? ''}
            placeholder={q.placeholder ?? ''}
            onChange={(v) => handleOpen(v)}
          />
        )}
      </QuestionCard>

      {status === 'error' && (
        <ErrorText style={{ marginTop: 16 }}>{errorMsg}</ErrorText>
      )}

      <Footer>
        <Btn onClick={() => setQIdx((i) => Math.max(0, i - 1))} disabled={qIdx === 0}>
          上一题
        </Btn>
        {isLast ? (
          <Btn primary disabled={!canNext || status === 'submitting'} onClick={handleSubmit}>
            {status === 'submitting' ? 'AI 评估中...' : '提交'}
          </Btn>
        ) : (
          <Btn primary disabled={!canNext} onClick={() => setQIdx((i) => i + 1)}>
            下一题
          </Btn>
        )}
      </Footer>
    </FullScreenShell>
  );
}

// ---------- helpers ----------

function isAnswered(q: Question, a: OnboardingAnswer): boolean {
  if (q.type === 'single') return typeof a.choice === 'string' && a.choice.length > 0;
  if (q.type === 'multi') return Array.isArray(a.choice); // 允许多选 0 个（视为跳过）
  if (q.type === 'open') return typeof a.free_text === 'string' && a.free_text.trim().length >= 10;
  return false;
}

// ---------- inline style atoms ----------

const FullScreenShell: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      position: 'fixed',
      inset: 0,
      background: '#FBF7EC',
      fontFamily: 'HedvigLettersSerif, serif',
      zIndex: 10000,
      display: 'flex',
      flexDirection: 'column',
      padding: '40px 80px',
      overflowY: 'auto',
    }}
  >
    {children}
  </div>
);

const Center: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    {children}
  </div>
);

const Header: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ marginBottom: 24 }}>{children}</div>
);

const Progress: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ fontSize: 14, color: '#6B6B70', marginBottom: 8 }}>{children}</div>
);

const ProgressBar: React.FC<{ value: number }> = ({ value }) => (
  <div style={{ height: 4, background: '#E5E5E0', borderRadius: 2 }}>
    <div style={{ width: `${value * 100}%`, height: 4, background: '#1B3B6F', borderRadius: 2 }} />
  </div>
);

const QuestionCard: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ flex: 1, maxWidth: 720, margin: '0 auto', width: '100%' }}>{children}</div>
);

const Prompt: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h2 style={{ fontSize: 24, color: '#1B3B6F', marginBottom: 24 }}>{children}</h2>
);

const Option: React.FC<{ selected: boolean; onClick: () => void; children: React.ReactNode }> = ({
  selected,
  onClick,
  children,
}) => (
  <div
    onClick={onClick}
    style={{
      padding: '16px 20px',
      border: `2px solid ${selected ? '#1B3B6F' : '#E5E5E0'}`,
      borderRadius: 8,
      marginBottom: 12,
      cursor: 'pointer',
      background: selected ? '#F0EBDF' : '#FFFFFF',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      fontSize: 15,
    }}
  >
    {children}
  </div>
);

const Radio: React.FC<{ checked: boolean }> = ({ checked }) => (
  <div
    style={{
      width: 18,
      height: 18,
      borderRadius: '50%',
      border: `2px solid ${checked ? '#1B3B6F' : '#9B9B9F'}`,
      flexShrink: 0,
    }}
  >
    {checked && (
      <div
        style={{
          width: 8,
          height: 8,
          background: '#1B3B6F',
          borderRadius: '50%',
          margin: '3px auto',
        }}
      />
    )}
  </div>
);

const CheckBox: React.FC<{ checked: boolean }> = ({ checked }) => (
  <div
    style={{
      width: 18,
      height: 18,
      border: `2px solid ${checked ? '#1B3B6F' : '#9B9B9F'}`,
      borderRadius: 4,
      background: checked ? '#1B3B6F' : 'transparent',
      flexShrink: 0,
    }}
  />
);

const OpenTextarea: React.FC<{ value: string; placeholder: string; onChange: (v: string) => void }> = ({
  value,
  placeholder,
  onChange,
}) => (
  <textarea
    value={value}
    placeholder={placeholder}
    onChange={(e) => onChange(e.target.value)}
    style={{
      width: '100%',
      minHeight: 120,
      padding: 16,
      fontSize: 15,
      fontFamily: 'HedvigLettersSerif, serif',
      border: '2px solid #E5E5E0',
      borderRadius: 8,
      resize: 'vertical',
      background: '#FFFFFF',
    }}
  />
);

const Footer: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32 }}>
    {children}
  </div>
);

const Btn: React.FC<{
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  primary?: boolean;
}> = ({ children, onClick, disabled, primary }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    style={{
      padding: '12px 24px',
      fontSize: 14,
      fontFamily: 'HedvigLettersSerif, serif',
      background: primary ? '#1B3B6F' : '#FFFFFF',
      color: primary ? '#FBF7EC' : '#1B3B6F',
      border: `1px solid ${primary ? '#1B3B6F' : '#E5E5E0'}`,
      borderRadius: 6,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
    }}
  >
    {children}
  </button>
);

const ErrorText: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children,
  style,
}) => <div style={{ color: '#BC4749', fontSize: 14, ...style }}>{children}</div>;
```

- [ ] **Step 5: 写 Onboarding vitest**

写 `frontend/src/components/__tests__/Onboarding.test.tsx`：

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Onboarding } from '../Onboarding';
import * as api from '../../api/onboarding';

vi.mock('../../api/onboarding');

const MOCK_QUESTIONS = [
  {
    id: 'q1_kb',
    dimension_hint: 'kb',
    type: 'single' as const,
    prompt: '遇到新概念？',
    options: [
      { id: 'a', label: '查定义' },
      { id: 'b', label: '看例子' },
      { id: 'c', label: '试一下' },
    ],
  },
  {
    id: 'q8_open',
    type: 'open' as const,
    prompt: '你的学习方式？',
    placeholder: '...',
  },
];

describe('Onboarding', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('渲染第 1 题', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);

    render(<Onboarding studentId="sid" onDone={vi.fn()} />);
    await waitFor(() => expect(screen.getByText('遇到新概念？')).toBeInTheDocument());
    expect(screen.getByText('问题 1 / 2')).toBeInTheDocument();
  });

  it('选 single 选项 → 下一题可点', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);
    render(<Onboarding studentId="sid" onDone={vi.fn()} />);
    await waitFor(() => screen.getByText('查定义'));

    fireEvent.click(screen.getByText('查定义'));
    const nextBtn = screen.getByText('下一题') as HTMLButtonElement;
    expect(nextBtn.disabled).toBe(false);
  });

  it('open 题提交按钮 disabled 当文本 < 10 字', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);
    render(<Onboarding studentId="sid" onDone={vi.fn()} />);
    await waitFor(() => screen.getByText('查定义'));

    fireEvent.click(screen.getByText('查定义'));
    fireEvent.click(screen.getByText('下一题'));

    const textarea = screen.getByPlaceholderText('...') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '短文本' } });

    const submitBtn = screen.getByText('提交') as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it('提交成功 → onDone 被调', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);
    vi.mocked(api.submitOnboarding).mockResolvedValue({
      dimensions: { kb: 0.7, vp: 0.5, as: 0.5, ge: 0.5, ept: 0.5, fd: 0.5 },
      reasoning: 'ok',
      snapshot_id: 1,
    });
    const onDone = vi.fn();

    render(<Onboarding studentId="sid" onDone={onDone} />);
    await waitFor(() => screen.getByText('查定义'));

    fireEvent.click(screen.getByText('查定义'));
    fireEvent.click(screen.getByText('下一题'));

    const textarea = screen.getByPlaceholderText('...') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '我喜欢先看图再看例子' } });

    fireEvent.click(screen.getByText('提交'));

    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
    expect(api.submitOnboarding).toHaveBeenCalledWith(
      'sid',
      expect.arrayContaining([
        { question_id: 'q1_kb', choice: 'a', free_text: undefined },
        { question_id: 'q8_open', choice: undefined, free_text: '我喜欢先看图再看例子' },
      ]),
    );
  });

  it('提交失败 → 显示错误', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);
    vi.mocked(api.submitOnboarding).mockRejectedValue(new Error('网络错误'));

    render(<Onboarding studentId="sid" onDone={vi.fn()} />);
    await waitFor(() => screen.getByText('查定义'));

    fireEvent.click(screen.getByText('查定义'));
    fireEvent.click(screen.getByText('下一题'));

    const textarea = screen.getByPlaceholderText('...') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '我喜欢先看图再看例子' } });
    fireEvent.click(screen.getByText('提交'));

    await waitFor(() => expect(screen.getByText(/提交失败/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 6: 跑测试验证 pass**

```bash
cd frontend && npx vitest run src/components/__tests__/Onboarding.test.tsx --reporter=verbose 2>&1 | tail -15
```

Expected: `5 passed`。

如有 vitest config 问题，先看 `frontend/vitest.config.ts` 是否需要加 `@testing-library/react` 的 jsdom env。

- [ ] **Step 7: 跑 frontend build 验证无类型错**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: build 成功，无 TS 错误。

- [ ] **Step 8: Commit**

```bash
cd D:/Projects/SelfLearn && git add frontend/src/api/onboarding.ts frontend/src/utils/profile.ts frontend/src/components/Onboarding.tsx frontend/src/utils/__tests__/profile.test.ts frontend/src/components/__tests__/Onboarding.test.tsx && git commit -m "feat(frontend): Onboarding 组件 + utils + api + vitest (5 个测试)"
```

---

## Task 5: App.tsx 路由守卫 + smoke 更新 + e2e

**Files:**
- Modify: `frontend/src/App.tsx`（加守卫）
- Modify: `backend/scripts/smoke_mvp.sh`（加 onboarding 步骤）

**Interfaces:**
- Consumes: `useProfile` 已有（`frontend/src/api/profile.ts`）、`useSession` 已有
- Produces: 守卫逻辑：`!isProfileInitialized(profile?.dimensions)` → 渲染 `<Onboarding />`

---

- [ ] **Step 1: 读 App.tsx 现状**

读 `frontend/src/App.tsx`，找到现有的 `useProfile` / 路由分发位置。

**预期结构**（基于已有约定）：

```typescript
function App() {
  const { studentId } = useSession();
  const { data: profile, isLoading } = useProfile(studentId);
  // ... 主渲染
}
```

- [ ] **Step 2: 加守卫**

修改 `frontend/src/App.tsx`，在主渲染前插入：

```typescript
import { isProfileInitialized } from './utils/profile';
import { Onboarding } from './components/Onboarding';

// 在 App 函数内、return 前加：
if (isLoading) {
  return <div style={{ padding: 40, fontFamily: 'HedvigLettersSerif, serif' }}>加载中...</div>;
}

if (!isProfileInitialized(profile?.dimensions)) {
  return (
    <Onboarding
      studentId={studentId}
      onDone={() => window.location.reload()}
    />
  );
}
```

`onDone={() => window.location.reload()}` — 简单粗暴触发 useProfile 重拉；如想精细可用 React Query 的 `refetch()`，根据 App 现有写法选一种。

- [ ] **Step 3: 跑 frontend build 验证**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: build 成功。

- [ ] **Step 4: 更新 smoke_mvp.sh**

读 `backend/scripts/smoke_mvp.sh`，找到合适位置（一般在 "Test 5 profile build" 之前或之后）加 onboarding 步骤。**这是 verification 脚本**，不需要重写，只追加：

```bash
# 追加在脚本末尾或 profile build 后：
echo "[smoke] Test 9: onboarding flow"
# 1. 删 KEEP_STUDENT 的 Profile（强制首启）
cd backend && uv run python -c "
import asyncio
from sqlalchemy import delete
from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory
async def main():
    async with get_session_factory()() as s:
        await s.execute(delete(Profile).where(Profile.student_id == '86820161-b0f0-455f-91b4-a69e49445bdf'))
        await s.commit()
asyncio.run(main())
"
# 2. 拉题库
curl -s http://localhost:8000/api/onboarding/questions | jq '.questions | length'  # → 8
# 3. 提交模拟答案（mock LLM 跳过；如要真跑需 LLM provider）
curl -s -X POST http://localhost:8000/api/onboarding/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "student_id": "86820161-b0f0-455f-91b4-a69e49445bdf",
    "answers": [
      {"question_id": "q1_kb", "choice": "a"},
      {"question_id": "q2_vp", "choice": "a"},
      {"question_id": "q3_as", "choice": "b"},
      {"question_id": "q4_ge", "choice": "b"},
      {"question_id": "q5_ept", "choice": "c"},
      {"question_id": "q6_fd", "choice": "c"},
      {"question_id": "q7_mixed", "choice": ["a", "b"]},
      {"question_id": "q8_open", "free_text": "我喜欢先看图再看例子最后总结。"}
    ]
  }' | jq '.dimensions | length'  # → 6
```

> **注意**：smoke 步骤 3 需要真实 LLM 跑；如 `.env` 配的是 `LLM_DEFAULT_PROVIDER=mock`，会得到 mock 的固定 0.5 输出。两条路径都 OK（mock 验接口契约，真 LLM 验端到端）。

- [ ] **Step 5: 跑 smoke**

```bash
cd backend && uv run python -m scripts.purge_test_data  # 清场
cd backend && bash scripts/smoke_mvp.sh 2>&1 | tail -20
```

Expected: smoke 末尾看到 `[smoke] Test 9: onboarding flow` + 8（题数）+ 6（维度数），整段 9/9 PASS。

- [ ] **Step 6: 跑全量回归**

```bash
cd backend && uv run pytest tests/unit -p no:warnings 2>&1 | tail -3
cd backend && uv run mypy src/selflearn 2>&1 | tail -3
cd frontend && npx vitest run --reporter=verbose 2>&1 | tail -5
cd frontend && npm run build 2>&1 | tail -5
```

Expected: pytest 188+ passed / mypy clean / vitest 9+ passed / build OK。

- [ ] **Step 7: 浏览器手动验证**

（可选但强烈建议）

1. 起 docker：`cd backend && HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 docker compose up -d --force-recreate gateway worker`
2. 清 Profile：`cd backend && uv run python -m scripts.purge_test_data`
3. 浏览器开 `http://localhost:5173`
4. 验证：进入全屏 onboarding → 答完 8 题 → 提交 → 看到雷达图（6 维非全 0.5）
5. 刷新页面 → 不再进入 onboarding（已 init）

- [ ] **Step 8: Commit**

```bash
cd D:/Projects/SelfLearn && git add frontend/src/App.tsx backend/scripts/smoke_mvp.sh && git commit -m "feat(integration): App.tsx 路由守卫 + smoke onboarding 步骤"
```

---

## 自审 Checklist（spec coverage）

- [x] **数据模型 § 1.1 不动 schema**：Task 2 写 `ProfileSnapshot(trigger="onboarding")` 而非新表；Task 2 tool `_write_snapshot` 用现有 ORM
- [x] **数据模型 § 1.2 题库 JSON**：Task 1 Step 1
- [x] **数据模型 § 1.3 LLM 输出 schema**：Task 1 Step 2 SKILL.md + Task 2 `_normalize_dims` 校验
- [x] **后端 § 2.1 SKILL.md**：Task 1 Step 2
- [x] **后端 § 2.2 tool.onboard_profile**：Task 2 Step 3
- [x] **后端 § 2.3 路由**：Task 3 Step 4
- [x] **后端 § 2.4 注册 tool**：Task 2 Step 5
- [x] **后端 § 2.5 挂路由**：Task 3 Step 5
- [x] **前端 § 3.1 api/onboarding.ts**：Task 4 Step 3
- [x] **前端 § 3.2 Onboarding.tsx**：Task 4 Step 4
- [x] **前端 § 3.3 App.tsx 守卫**：Task 5 Step 2
- [x] **前端 § 3.3 utils/profile.ts**：Task 4 Step 1
- [x] **数据流 § 4.1 首次进站**：Task 4 + Task 5 串起来
- [x] **数据流 § 4.2 重复触发防护**：Task 2 `already_onboarded` + Task 3 409 + Task 5 守卫
- [x] **错误处理 § 5**：Task 2 (clamp/missing/lint) + Task 3 (409/400/500) + Task 4 (submit 错误)
- [x] **测试 § 6**：5 个测试文件，每个 task 配套
- [x] **Task 划分 § 7**：5 个 task，对应 spec 5 段
- [x] **风险 § 8**：LLM 不稳定 → Task 2 max_retries=2 + clamp；幂等性 → Task 2 already_onboarded + Task 5 守卫
- [x] **不做 § 9**：所有 YAGNI 项均未实现

## 自审 Checklist（placeholder scan）

无 TBD/TODO/"implement later"/"similar to Task N"/无类型签名漂移。

## 自审 Checklist（type consistency）

| 字段 | Task 定义处 | 后续使用处 | 一致 |
|------|-------------|-----------|------|
| `onboard_profile(student_id, answers, agent) -> dict` | Task 2 Step 3 | Task 3 Step 4 `_run_onboard` | ✓ |
| `{ok: True, dimensions, reasoning, snapshot_id}` | Task 2 Step 3 | Task 3 Step 4 路由返回 | ✓ |
| `OnboardingAnswer {question_id, choice?, free_text?}` | Task 4 Step 3 | Task 4 Step 5 测试 mock | ✓ |
| `isProfileInitialized(dims?) -> boolean` | Task 4 Step 1 | Task 5 Step 2 App.tsx | ✓ |
| `fetchOnboardingQuestions() -> Question[]` | Task 4 Step 3 | Task 4 Step 5 测试 mock | ✓ |
| `submitOnboarding(sid, answers) -> OnboardingSubmitResponse` | Task 4 Step 3 | Task 4 Step 5 测试 mock | ✓ |

---

## Global Constraints（执行时同步）

- branch 直接 main（CLAUDE.md + memory `no-worktrees-sdd`）
- 中文 commit message
- Docker proxy `HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897`
- 单账户 `KEEP_STUDENT = "86820161-b0f0-455f-91b4-a69e49445bdf"`（Task 5 Step 4 smoke 用到，与 `backend/scripts/purge_test_data.py:24` 一致）
- 无登录鉴权
- 无 worktree（SDD subagent 直跑 main）

## Verification（执行完后整体验证）

| 层级 | 命令 | 期望 |
|------|------|------|
| 后端单测 | `cd backend && uv run pytest tests/unit -p no:warnings` | 188+ passed |
| 后端类型 | `cd backend && uv run mypy src/selflearn` | clean |
| 前端单测 | `cd frontend && npx vitest run` | 9+ passed (4 utils + 5 Onboarding) |
| 前端构建 | `cd frontend && npm run build` | OK |
| E2E smoke | `cd backend && bash scripts/smoke_mvp.sh` | 9/9 PASS（含 onboarding） |
| 手动验证 | 浏览器：清 Profile → 走完 onboarding → 看到雷达图 | OK |
