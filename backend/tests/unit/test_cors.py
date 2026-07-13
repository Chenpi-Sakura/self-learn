"""T1: CORS middleware 挂载验证。"""
from __future__ import annotations


def test_app_has_cors_middleware() -> None:
    from starlette.middleware.cors import CORSMiddleware

    from selflearn.gateway.app import create_app

    app = create_app()
    cors = next(
        (m for m in app.user_middleware if getattr(m.cls, "__name__", "") == CORSMiddleware.__name__),
        None,
    )
    assert cors is not None, "FastAPI app 未挂载 CORSMiddleware"


def test_cors_allows_vite_dev_origins() -> None:
    """spec § 10.1: dev 阶段必须放行 Vite 默认端口 5173 (localhost + 127.0.0.1)。"""
    from starlette.middleware.cors import CORSMiddleware

    from selflearn.gateway.app import create_app

    app = create_app()

    cors_mw = next(
        (m for m in app.user_middleware if getattr(m.cls, "__name__", "") == CORSMiddleware.__name__),
        None,
    )
    assert cors_mw is not None, "CORS middleware 缺失"
    allowed_raw: object = cors_mw.kwargs.get("allow_origins", [])
    assert isinstance(allowed_raw, list)
    assert "http://localhost:5173" in allowed_raw, f"localhost:5173 不在 allow_origins: {allowed_raw}"
    assert "http://127.0.0.1:5173" in allowed_raw, f"127.0.0.1:5173 不在 allow_origins: {allowed_raw}"