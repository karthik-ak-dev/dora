"""
Health Check Handler

Provides health check endpoints for monitoring and load balancers.
"""

from fastapi import APIRouter

from src.config.settings import settings
from src.shared.schemas.common import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        HealthResponse with service status
    """
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME.lower(),
        version=settings.APP_VERSION,
    )


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/load balancers.

    This could be extended to check database connectivity, etc.

    Returns:
        Simple ready status
    """
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """
    Liveness check for Kubernetes.

    Returns:
        Simple alive status
    """
    return {"status": "alive"}
