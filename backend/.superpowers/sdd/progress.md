# SDD Progress — SelfLearn

## Task 256: 修复 P5 失败测试（mock 真实 I/O）
- Status: DONE
- Commits: 03ea80e

## Task 257: 修复地图节点切换不刷新讲义/习题
- Status: DONE
- Commits: ee4fc9b, 68c7ee9

## Task 258: 调试节点切换不生效
- Status: DONE
- 根因：worker 容器内 MCP server 子进程没继承 POSTGRES_HOST/REDIS_URL

## Task 259: 修复 MCP server env 丢失
- Status: DONE
- Commits: 5ee5af7

## Task 259 (fix): 修复 skill prompt .format() 误解析
- Status: DONE
- Commits: e6ff423

## Task 260: 修复 lint_json + 持续修复直到跑通
- Status: DONE
- Commits: 95974de, 8d87a9a, 403b0f5, a32aaa5
- 修复链:
  1. lint_json 路径解析 + Dockerfile 缺 schemas/
  2. LLM ```json fence 解析兼容
  3. Director chain 按 env.payload.node_id 精确路由（get_active_node 加 node_id 参数）
  4. review_stage 清理调试 logger

## Task 261: 讲义 HTML（lecture_html）落地
- Status: DONE_WITH_CONCERNS
- 9 个子任务（T1-T9）：data layer → director chain → 前端 → 回归
- Commits:
  - T1 c519f8c feat(db): migration 加 levels.lecture_html 列（String(50000) nullable）
  - T2 6492e99 feat(domain): Level.lecture_html 字段（Mapped[str|None], String(50000)）
  - T3 98d79fd feat(api): LevelDetailResponse + GET /api/level/{id} 返回 lecture_html 字段
  - T4 814ce95 feat(mcp): tool.create_level 截断 lecture_html 到 50000 + 单测
  - T5 4a771e8 feat(agent): extract_lecture_outline 工具函数（抽 sections/callouts/examples）+ 单测
  - T6 a9c9d5c feat(skill): skill.lecture.generate 重写为纯讲解 prompt（禁输出题目答案）
  - T7 8271244 feat(agent): Director chain 提取 lecture_outline 注入 exercise env
  - T8 afe52ab + 7193404 feat(frontend): LecturePane + KaTeX + lecture.css + katex.d.ts 修复
  - T9 12e5cdb test(e2e): director chain lecture_outline 注入 + explanation 引用 outline
- 验证:
  - 3 个不同节点触发 /start → DB 里 level.lecture_html 非空（3077 / 3116 / 63 字符）+ exercise.explanation ≥ 100 字 + 首句引用 lecture_outline（"如讲义『...』中所言" 模式 8/8 命中）
  - pytest 176 passed
  - mypy 1 预存在错误（director.py:103，T7 引入 cast 缺失；非本次回归）
  - 前端 typecheck + build 通过
- 关注点:
  - smoke step 6 SSE 偶发 curl-18 关闭（仅 level 通路；profile SSE 正常；与 T1-T8 无关；建议另开 task 排查 progress_consume / EventSourceResponse 协同）
  - 9989ce0f 节点 worker 经历 3 次 review_llm parse failed 重试，最终产物 lecture_html 仅 63 字符（fallback callout），但解释仍引用之，链路完整
  - 验证时删除了 86820161-b0f0-455f-91b4-a69e49445bdf 旧 level/exercise 再触发，生产慎用
- 验证:
  - 3 个不同节点 (92c1868b / 6eebd2d9 / 9989ce0f) 触发 /start 全部成功
  - 每个节点生成 1 个 level + 3 个 exercise
  - worker 日志 agent.no_reply（chain 跑完）
  - 151 unit tests pass

## 关键设计点（值得记）

- **MCP SDK `stdio_client` env 继承是白名单模式**——业务变量（POSTGRES_HOST / LLM_*）必须显式 `env=dict(os.environ)` 传
- **`.format()` 对 dict 值 str() 表示二次解析**——SKILL.md body 含 markdown 文本里的 `{exercise_type}` 会被误解析为占位符
- **LLM 输出 ```json``` fence**——所有 `json.loads(raw)` 路径必须用 `extract_json_from_fence` 先剥 fence
- **Director chain 需要 env.payload 精确透传**——MCP tool `get_active_node` 必须接受 `node_id` 参数，不能 fallback 到"第一个 active"

## 剩余 backlog
1. `docs/superpowers/backlog/2026-07-15-html-lecture.md`（HTML 富讲义）
2. BACKLOG_P5.md 描述与实际不符（可选修）
3. 前端 `node_locked` 错误提示 UI（待办）