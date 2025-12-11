"""
Route Registration

Centralizes all route registration for the FastAPI application.

Route Hierarchy:
================
    /health         → Health check endpoints
    /auth           → Authentication (register, login)
    /items          → Content saves (CRUD)
    /clusters       → AI-generated clusters

Usage:
======
    from src.api.routes import register_routes

    app = FastAPI()
    register_routes(app)
"""

from fastapi import FastAPI

from src.api.handlers import (
    auth_handler,
    content_handler,
    cluster_handler,
    health_handler,
)


def register_routes(app: FastAPI) -> None:
    """
    Register all API routes.

    Args:
        app: FastAPI application instance
    """
    # Health check endpoints (no prefix, root level)
    app.include_router(
        health_handler.router,
        tags=["Health"],
    )

    # Authentication endpoints
    app.include_router(
        auth_handler.router,
        prefix="/auth",
        tags=["Authentication"],
    )

    # Content (Items) endpoints
    app.include_router(
        content_handler.router,
        prefix="/items",
        tags=["Content"],
    )

    # Cluster endpoints
    app.include_router(
        cluster_handler.router,
        prefix="/clusters",
        tags=["Clusters"],
    )
