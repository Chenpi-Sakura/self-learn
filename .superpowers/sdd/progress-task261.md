# Task 261 — 讲义 HTML（Lecture）落地

**Plan**: docs/superpowers/plans/2026-07-16-html-lecture.md
**Spec**: docs/superpowers/specs/2026-07-16-html-lecture-design.md
**Base**: 4e57bc8（plan commit）
**Branch**: main（CLAUDE.md + memory `no-worktrees-sdd`）
**Started**: 2026-07-16

## Global Constraints（verbatim from plan § Global Constraints）

- 依赖约束：后端不引入新依赖（mcp / nh3 已存在）；前端新增 `katex@^0.16.11` 唯一新依赖
- 迁移约束：不修改任何已有 alembic migration；新增一个独立 migration（down_revision 指向 `f1963078e4e4` 当前 head）
- 字段类型：`lecture_html String(50000) nullable=True`
- 重试策略：整链 retry（max_attempts=3），lecture lint rejected → 整链 retry，不软失败
- 不做的事：
  - 不做前端 XSS 二次清洗（依赖后端 nh3）
  - 不调 LLM 做讲义 review（仅 lint_html + not_empty）
  - 不实现图片/视频/iframe
  - 不主动迁移历史关卡讲义（NULL 占位即可）
  - 不重做 ReviewAgent / Director chain
- commit 规范：中文 commit message
- Docker 构建：`HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897`
- 测试运行：`cd backend && uv run pytest -p no:warnings`

## Progress

| Task 1 — Alembic migration 加 lecture_html 列 | **complete** | c519f8c | review clean (haiku) |
| Task 2 — ORM Level.lecture_html 字段 | **complete** | 6492e99 | review clean (haiku) |
| Task 3 — Pydantic schema + Gateway 返回 lecture_html | **complete** | 98d79fd | review clean (haiku) |
| Task 4 — tool.create_level 截断 + 单测 | **complete** | 814ce95 | review clean (sonnet) |
| Task 5 — extract_lecture_outline 工具函数 + 单测 | **complete** | 4a771e8 | review clean (haiku) |
| Task 6 — 重写 skill.lecture.generate SKILL.md | **complete** | a9c9d5c | review clean (sonnet) — Important contract gap with T7 noted as expected T7 work |
| Task 7 — Director 注入 outline + exercise SKILL.md | **complete** | 8271244 | review clean (sonnet) — contract wired |
| Task 8 — 前端 LecturePane + KaTeX + lecture.css | **complete** | afe52ab + 7193404 | review clean after fix (sonnet review → haiku fix re-review) — Critical .gitignore issue resolved |
| Task 9 — 端到端 + smoke + 3 节点实测 | **complete** | 12e5cdb + 5ae3cf3 + 361c58f | pytest 176 passed; mypy 1 error 修复后 clean; smoke step 6 SSE curl-18 (与 T1-T8 无关，建议另开 task); 3-node DB 验证 lecture_html + explanation 引用 outline 8/8 命中 |

## Task 265 — 唯一账户 + 全清 Demo

| 任务 | 状态 | Commit | Review |
| --- | --- | --- | --- |
| T1 前端 KEEP_STUDENT 常量 + session.ts 重写 | complete | 1e613bf | review clean (haiku) — Minor: 文件末尾无 newline, brief 未要求, 不阻塞 |
| T2 后端 startup ensure KEEP_STUDENT + 单测 | complete | f4a6465 | review clean (sonnet) — 两个 brief 偏差 (`from sqlalchemy import select` 缺 import; `loop_scope="session"` 适配项目 pytest-asyncio) 由 TDD 暴露, 均为 brief 修正, 不算 overstep |
| T3 删 demo（sample.ts + ResetButton）+ store 默认空 | complete | a189986 | review clean (sonnet) — Important: useWorkspace.ts 有无用 import ProfileDimensions; Minor: 注释仍提及 data/sample（不影响运行）。无用 import 已当场修 |
| T4 e2e + CLAUDE.md 更新 | complete | 3315d2e | whole-branch review clean after fix (b9ebd88) — Important: useWorkspace 无用 import 已提交修; Minor: CLAUDE.md 行号 `:22`→`:24` 已一并修 |

## Task 262 — 讲义反孤儿化（A + B）

| 阶段 | 状态 | Commit | Review |
| --- | --- | --- | --- |
| T1 — reuse 谓词排除 NULL lecture | **complete** | 895e1e4 | review clean (sonnet) — Python guard deviation accepted as defense-in-depth |
| T2 — backfill 脚本 | **complete** | 503148c | review clean (sonnet) — but regeneration hit PEP 479 StopIteration, fix in T2.5 |
| T2.5 — LLMRegistry.default() PEP 479 修复 | **complete** | a1af102 | review clean (sonnet) — script + registry 双重防御 |
| T3 — e2e + 回归 | **complete** | n/a (验证) | backfill --limit 3: success=3/3; /start e2e: 复用 lecture_html 非 NULL（reused=true）+ 跳过 NULL（reused=false）; pytest 164 passed; mypy clean; smoke step 6 SSE curl-18 仍存在（pre-existing，与本任务无关）|

### 端到端验证
- 真实 backfill 4 个 node（dev DB），lecture_html 525-3184 字符，explanation 63-177 字符（全部 ≥30）
- `POST /api/level/start` 在强制 `lecture_html=NULL` 后返回 `reused: false`；恢复后返回 `reused: true` + 复用新 level
- pytest 164 passed, mypy clean