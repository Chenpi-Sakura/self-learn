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
