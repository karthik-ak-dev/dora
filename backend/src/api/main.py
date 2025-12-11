"""
Dora API Application Entry Point

FastAPI application setup with all routers, middleware, and lifecycle management.

Application Architecture:
=========================
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DORA API                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │                    Middleware Stack                          │          │
│   │  ┌─────────────────────────────────────────────────────┐    │          │
│   │  │ CORS Middleware                                      │    │          │
│   │  │ Error Handler                                        │    │          │
│   │  └─────────────────────────────────────────────────────┘    │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │                       Routers                                │          │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │          │
│   │  │  Health  │ │   Auth   │ │  Items   │ │ Clusters │       │          │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │                Dependencies (Injected)                       │          │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │          │
│   │  │ Database │ │   Auth   │ │ Services │                    │          │
│   │  └──────────┘ └──────────┘ └──────────┘                    │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Lifecycle:
==========
1. Application starts → lifespan startup
2. Database connection initialized
3. Application serves requests
4. Application stops → lifespan shutdown
5. Database connection closed

Usage:
======
    # Run with uvicorn
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

    # Or programmatically
    from src.api.main import create_application
    app = create_application()
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.shared.db import init_db, close_db
from src.shared.core.logging import logger
from src.api.middleware import setup_exception_handlers
from src.api.routes import register_routes


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the application.

    Startup:
    - Initialize database connection pool
    - Any other startup tasks (Redis, etc.)

    Shutdown:
    - Close database connections
    - Cleanup resources
    """
    # ═══════════════════════════════════════════════════════════════════════════
    # STARTUP
    # ═══════════════════════════════════════════════════════════════════════════
    logger.info(
        "Starting Dora API",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )

    # Initialize database
    await init_db()

    # Add other startup tasks here (Redis, etc.)
    logger.info("Dora API started successfully")

    yield

    # ═══════════════════════════════════════════════════════════════════════════
    # SHUTDOWN
    # ═══════════════════════════════════════════════════════════════════════════
    logger.info("Shutting down Dora API")

    # Close database connections
    await close_db()

    # Add other cleanup tasks here
    logger.info("Dora API shutdown complete")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance

    This factory function:
    1. Creates the FastAPI app with settings
    2. Adds middleware (CORS, etc.)
    3. Sets up exception handlers
    4. Registers all routes
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-Powered Second Brain for Content",
        version=settings.APP_VERSION,
        # Only show docs in development
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        # Use lifespan for startup/shutdown
        lifespan=lifespan,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # MIDDLEWARE
    # ═══════════════════════════════════════════════════════════════════════════

    # CORS Middleware - Must be added first
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # EXCEPTION HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    setup_exception_handlers(app)

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTES
    # ═══════════════════════════════════════════════════════════════════════════

    register_routes(app)

    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════════════════

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": settings.APP_NAME.lower(),
            "version": settings.APP_VERSION,
        }

    return app


# Create the application instance
app = create_application()
