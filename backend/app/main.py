"""FastAPI application entry point with lifespan, CORS, rate limiting, and compression."""

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend root and app directory are in sys.path
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
_app_dir = str(Path(__file__).resolve().parent)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import Response

from app.config import settings
from app.models.database import init_db
from app.routes import documents, export, rights
from app.services.extraction_service import ExtractionService
from app.services.redaction_service import RedactionService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize heavy resources once at startup."""
    logger.info("Starting Nyaya Sahayak backend...")

    try:
        # Initialize in-memory database
        await init_db()

        # Initialize vector store with statute corpus
        vector_store = VectorStoreService()
        vector_store.initialize()
        app.state.vector_store = vector_store

        # Services initialized with on-demand lazy loading
        app.state.extraction_service = ExtractionService()
        app.state.redaction_service = RedactionService()

        # Ensure writable upload directory
        try:
            settings.upload_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("Could not create upload directory: %s", e)
    except Exception as e:
        logger.error("Non-fatal startup initialization error: %s", e)

    logger.info("Nyaya Sahayak backend ready.")
    yield

    # Cleanup
    logger.info("Shutting down Nyaya Sahayak backend.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Nyaya Sahayak API",
        description=(
            "GenAI-powered legal assistance tool for understanding documents "
            "and situations in plain language. Provides information and direction "
            "to appropriate legal forums — never legal advice."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Exception handlers: do not swallow HTTPExceptions or RateLimitExceeded as 500
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please wait a moment and try again."},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server error on %s: %s", request.url.path, exc)
        # Mask internal details in production to prevent information leakage
        is_production = not os.getenv("DEV_MODE", "")
        detail = "An internal server error occurred. Please try again later." if is_production else f"Server error: {exc}"
        return JSONResponse(
            status_code=500,
            content={"detail": detail},
        )

    # GZip compression — reduces response payloads by ~70%
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # CORS for frontend dev server and Vercel deployments
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_origin_regex=r"^https://.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(documents.router, prefix="/api")
    app.include_router(rights.router, prefix="/api")
    app.include_router(export.router, prefix="/api")

    @app.get("/")
    @app.get("/health")
    @app.get("/api")
    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "nyaya-sahayak"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
