"""
Health check handler.

This is a simple health check endpoint that doesn't require authentication.
Used by load balancers and monitoring systems to verify the API is running.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns basic service information to confirm the API is operational.
    This endpoint does not require authentication.
    """
    return {
        "status": "healthy",
        "service": "dora-api",
        "version": "1.0.0"
    }

