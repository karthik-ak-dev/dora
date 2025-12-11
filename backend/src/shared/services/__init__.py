"""
Business Logic Services

Services encapsulate business logic and coordinate between repositories,
external services, and domain rules.

Service Pattern:
================
    Handler → Service → Repository → Database
                ↘ External APIs

Services should:
- Contain business logic and validation
- Coordinate multiple repositories if needed
- Handle transactions (via session)
- NOT handle HTTP concerns (that's for handlers)

Available Services:
===================
- AuthService: User registration and authentication
- ContentService: Content saving, retrieval, and organization
- ClusterService: AI-generated content cluster management

Usage:
======
    from src.shared.services import AuthService, ContentService

    service = AuthService(db)
    user, token, expires = await service.register_user(email, password)
"""

from src.shared.services.auth_service import AuthService
from src.shared.services.content_service import ContentService
from src.shared.services.cluster_service import ClusterService

__all__ = [
    "AuthService",
    "ContentService",
    "ClusterService",
]
