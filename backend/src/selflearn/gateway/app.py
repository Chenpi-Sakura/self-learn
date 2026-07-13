"""FastAPI app 装配。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from selflearn.config import get_settings
from selflearn.core.errors import AppError
from selflearn.core.logging import get_logger
from selflearn.core.tracing import setup_tracing
from selflearn.gateway.routes import health, profile
from selflearn.gateway.routes.level import router as level_router
from selflearn.gateway.routes.map import router as map_router
from selflearn.infra.rabbit import setup_topology
from selflearn.skills.builtin.ping import register as register_ping_skill

log = get_logger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await setup_topology()
    log.info("gateway.startup_done")
    yield
    log.info("gateway.shutdown_done")


def create_app() -> FastAPI:
    s = get_settings()
    setup_tracing(s.otel_service_name + "-gateway", s.otel_exporter_otlp_endpoint)
    register_ping_skill()
    app = FastAPI(title="selflearn-gateway", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(profile.router)
    app.include_router(map_router)
    app.include_router(level_router)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        trace_id = request.headers.get("x-trace-id")
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict(trace_id))

    return app