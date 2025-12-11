"""
Service Dependencies

FastAPI dependencies for service injection.

These dependencies create service instances with proper database session injection.
Services are created per-request, which is fine because:
- Services are stateless (only hold db session reference)
- Each request gets its own db session
- No shared state between requests

Usage:
======
    from src.api.dependencies.services import get_auth_service, get_content_service

    @router.post("/register")
    async def register(
        data: UserCreate,
        auth_service: AuthService = Depends(get_auth_service)
    ):
        return await auth_service.register_user(data.email, data.password)
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db
from src.shared.services.auth_service import AuthService
from src.shared.services.content_service import ContentService
from src.shared.services.cluster_service import ClusterService


async def get_auth_service(
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    """
    Dependency to get AuthService instance.

    Creates a new service instance per request with the request's db session.
    """
    return AuthService(db)


async def get_content_service(
    db: AsyncSession = Depends(get_db),
) -> ContentService:
    """
    Dependency to get ContentService instance.
    """
    return ContentService(db)


async def get_cluster_service(
    db: AsyncSession = Depends(get_db),
) -> ClusterService:
    """
    Dependency to get ClusterService instance.
    """
    return ClusterService(db)
