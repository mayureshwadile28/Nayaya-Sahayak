"""FastAPI application entry point with lifespan, CORS, and rate limiting."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

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

    # Initialize database
    await init_db()

    # Load spaCy model once
    extraction_service = ExtractionService()
    extraction_service.load_models()
    app.state.extraction_service = extraction_service

    # Initialize Presidio once
    redaction_service = RedactionService()
    app.state.redaction_service = redaction_service

    # Initialize vector store with statute corpus
    vector_store = VectorStoreService()
    vector_store.initialize()
    app.state.vector_store = vector_store

    # Create upload directory
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

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

    # CORS for frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(documents.router, prefix="/api")
    app.include_router(rights.router, prefix="/api")
    app.include_router(export.router, prefix="/api")

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
