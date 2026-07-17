# SelfLearn — 项目级约定

## Docker 构建代理

由于国内网络限制，构建 Docker 镜像时须传入代理环境变量以拉取基础镜像：

```bash
HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 docker compose build <service>
```

注意：`daemon.json` 的 `proxies` 配置会被 Docker Desktop 重启后自动还原，**不能依赖** daemon.json 写死代理。标准做法是构建时在命令前加环境变量。

- 代理端口 `7897` 对应 Clash HTTP 代理
- WSL 网络模式为 **Mirrored**，因此 `127.0.0.1` 能直通 Windows 本机

## 常用的完整构建 + 启动命令

```bash
cd backend
HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 docker compose build gateway worker
docker compose up -d --force-recreate gateway worker
```

## 开发环境

- LLM Provider：`.env` 中 `LLM_DEFAULT_PROVIDER=openai_compat`（真实 DeepSeek）或 `mock`（测试）
- 容器内通过 `env_file: .env` 读取配置，改 `.env` 后需 `--force-recreate` 容器才能生效
- WSL Mirrored 模式下 `localhost` 在容器内可能解析为 IPv6，部分组件（RabbitMQ）需要用 `127.0.0.1` 替代

## E2E 测试数据清理

每个 task E2E 跑完**必须**调清场脚本，避免 stub level 污染 DB：

```bash
cd backend && uv run python -m scripts.purge_test_data
```

`KEEP_STUDENT = 86820161-b0f0-455f-91b4-a69e49445bdf` 是唯一的真实账户。该脚本会：
- 删其他所有 student_id 的 MapNode / Level / Exercise / LevelCompletion / Profile / ProfileSnapshot
- 删 KEEP_STUDENT 的 NULL-lecture level（让 `/start` 重新生成讲义）
- 保留 KEEP_STUDENT 的有讲义 level（= 最近一次真实使用的关卡）

如要修改 KEEP_STUDENT，改 `backend/scripts/purge_test_data.py` 第 22 行。
