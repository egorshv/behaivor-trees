from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import Settings, get_settings
from app.database import create_session_factory, session_scope
from app.runtime.builder import RuntimeManager
from app.storage import ensure_demo_tree


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    session_factory = create_session_factory(resolved_settings)
    runtime_manager = RuntimeManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with session_factory() as session:
            ensure_demo_tree(session)
        yield

    app = FastAPI(title="Behavior Trees API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.session_factory = session_factory
    app.state.runtime_manager = runtime_manager

    @app.middleware("http")
    async def db_session_middleware(request: Request, call_next: Callable):
        session = session_factory()
        request.state.db = session
        try:
            response = await call_next(request)
            return response
        finally:
            session.close()

    app.include_router(router)
    return app


app = create_app()
