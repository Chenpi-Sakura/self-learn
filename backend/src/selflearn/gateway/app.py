"""FastAPI app 装配。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from selflearn.config import get_settings
from selflearn.core.errors import AppError
from selflearn.core.logging import get_logger
from selflearn.core.tracing import setup_tracing
from selflearn.gateway.routes import health, profile
from selflearn.gateway.routes.extract_topics import router as extract_topics_router
from selflearn.gateway.routes.level import router as level_router
from selflearn.gateway.routes.map import router as map_router
from selflearn.gateway.routes.resources import router as resources_router
from selflearn.infra.rabbit import setup_topology
from selflearn.infra.seed_account import ensure_keep_student

log = get_logger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await ensure_keep_student()        # 新增：幂等 ensure Profile 行
    await setup_topology()
    log.info("gateway.startup_done")
    yield
    log.info("gateway.shutdown_done")


def create_app() -> FastAPI:
    s = get_settings()
    setup_tracing(s.otel_service_name + "-gateway", s.otel_exporter_otlp_endpoint)
    app = FastAPI(title="selflearn-gateway", version="0.1.0", lifespan=lifespan)
    # Stage 4: dev CORS（spec § 10.1 + plan T1）
    # STAGE5_PROD_HARDEN: 上生产时收紧 allow_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173", "http://127.0.0.1:5173",
            "http://localhost:5174", "http://127.0.0.1:5174",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(profile.router)
    app.include_router(map_router)
    app.include_router(level_router)
    app.include_router(resources_router)
    app.include_router(extract_topics_router)

    # Stage 4: AOP /debug/state 路由（spec § 6.5 + § 10.7，plan T5）
    # 仅在 settings.debug=True 时挂载；生产场景（DEBUG 不设）返回 404，零暴露面。
    if s.debug:
        from selflearn.observability.routes import router as debug_router

        app.include_router(debug_router)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        trace_id = request.headers.get("x-trace-id")
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict(trace_id))

    return app