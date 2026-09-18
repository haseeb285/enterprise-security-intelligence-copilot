"""FastAPI application boundary and dependency lifecycle."""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from qdrant_client import QdrantClient
from sqlalchemy import text

from app.api.routes.data import router as data_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.schemas import HealthOut
from app.core.settings import Settings, get_settings
from app.db.session import create_db_engine, make_session_factory
from app.llm.ollama import OllamaProvider

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: Any = None,
    qdrant_client: Any = None,
    llm_provider: Any = None,
    rag_service: Any = None,
) -> FastAPI:
    settings = settings or get_settings()
    if settings.demo_api_token is None or settings.demo_read_token is None:
        raise RuntimeError("Set DEMO_API_TOKEN and DEMO_READ_TOKEN before starting the API")
    admin = settings.demo_api_token.get_secret_value()
    reader = settings.demo_read_token.get_secret_value()
    if len(admin) < 24 or len(reader) < 24 or admin == reader:
        raise RuntimeError("Demo tokens must be distinct and at least 24 characters")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = None
        app.state.settings = settings
        if session_factory is not None:
            app.state.session_factory = session_factory
        elif settings.database_url is not None:
            engine = create_db_engine(settings)
            app.state.session_factory = make_session_factory(engine)
        else:
            app.state.session_factory = None
        app.state.qdrant = qdrant_client or QdrantClient(url=str(settings.qdrant_url), timeout=5)
        app.state.llm = llm_provider or OllamaProvider(settings)
        app.state.rag_service = rag_service
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()
            if qdrant_client is None:
                app.state.qdrant.close()
            if llm_provider is None:
                app.state.llm.client.close()

    app = FastAPI(
        title="Enterprise Security Intelligence Copilot API",
        description="Local synthetic-data API. Bearer tokens are demo-only authentication.",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(_request: Request, _exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": "Invalid request input"})

    @app.exception_handler(ValidationError)
    async def model_validation_error(_request: Request, _exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": "Invalid request input"})

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, exc: Exception):
        logger.error("Unhandled API error: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.middleware("http")
    async def request_size_limit(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                length = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid content length"})
            if length > 8192 or len(await request.body()) > 8192:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        return await call_next(request)

    @app.get(
        "/api/v1/health",
        response_model=HealthOut,
        responses={503: {"model": HealthOut}},
        tags=["Health"],
        summary="Check app and local dependency readiness",
    )
    def health(request: Request):
        dependencies = {
            "application": "ok",
            "postgresql": "unavailable",
            "qdrant": "unavailable",
            "ollama": "unavailable",
        }
        factory = request.app.state.session_factory
        if factory is not None:
            try:
                with factory() as session:
                    session.execute(text("SELECT 1"))
                dependencies["postgresql"] = "ok"
            except Exception:
                pass
        try:
            collections = request.app.state.qdrant.get_collections().collections
            names = {item.name for item in collections}
            dependencies["qdrant"] = (
                "ok" if settings.rag_collection in names else "collection_missing"
            )
        except Exception:
            pass
        try:
            llm_health = request.app.state.llm.health()
            if llm_health.reachable:
                dependencies["ollama"] = "ok" if llm_health.model_available else "model_missing"
        except Exception:
            pass
        overall = "ready" if all(value == "ok" for value in dependencies.values()) else "degraded"
        return JSONResponse(
            status_code=200 if overall == "ready" else 503,
            content=HealthOut(status=overall, dependencies=dependencies).model_dump(),
        )

    app.include_router(data_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1")
    return app


# Run with: uvicorn app.api.main:create_app --factory --host 127.0.0.1
