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