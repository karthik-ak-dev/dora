"""
Route registration.
"""
from fastapi import FastAPI

from .handlers import auth_handler, content_handler, cluster_handler, health_handler


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""
    app.include_router(health_handler.router, tags=["Health"])
    app.include_router(auth_handler.router, prefix="/auth", tags=["Authentication"])
    app.include_router(content_handler.router, prefix="/items", tags=["Content"])
    app.include_router(cluster_handler.router, prefix="/clusters", tags=["Clusters"])
