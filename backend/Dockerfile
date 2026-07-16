# 多阶段构建：builder + runtime
FROM python:3.12-slim AS builder
RUN pip install --no-cache-dir "uv>=0.4"
WORKDIR /app
COPY pyproject.toml uv.lock ./
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-install-project --no-dev
COPY src ./src
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "uv>=0.4" -i https://mirrors.aliyun.com/pypi/simple/
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY src ./src
COPY skills ./skills
COPY schemas ./schemas
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "selflearn.gateway.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
