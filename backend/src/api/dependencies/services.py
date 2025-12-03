"""
Service dependencies for FastAPI.
Provides service instances via dependency injection.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from ...shared.services.auth_service import AuthService
from ...shared.services.content_service import ContentService
from ...shared.services.cluster_service import ClusterService
from .database import get_db


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """
    Dependency to get AuthService instance.
    
    This creates a new service instance per request, which is fine because:
    - Services are stateless (only hold db session reference)
    - Each request gets its own db session
    - No shared state between requests
    """
    return AuthService(db)


def get_content_service(db: Session = Depends(get_db)) -> ContentService:
    """Dependency to get ContentService instance."""
    return ContentService(db)


def get_cluster_service(db: Session = Depends(get_db)) -> ClusterService:
    """Dependency to get ClusterService instance."""
    return ClusterService(db)
