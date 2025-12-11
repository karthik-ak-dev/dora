"""
Pydantic Schemas

Request and response models for the API.

Schema Categories:
==================
- common: Base schemas, pagination, error responses
- user: User and authentication schemas
- content: Content save schemas
- cluster: Cluster schemas

Usage:
======
    from src.shared.schemas.user import UserCreate, UserResponse, AuthResponse
    from src.shared.schemas.common import PaginatedResponse, ErrorResponse
"""

from src.shared.schemas.common import (
    BaseSchema,
    PaginationParams,
    PaginationMeta,
    PaginatedResponse,
    MessageResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    TimestampMixin,
    IDMixin,
    SortParams,
)
from src.shared.schemas.user import (
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    AuthResponse,
)
from src.shared.schemas.cluster import (
    ClusterResponse,
    ClusterItemResponse,
    ClusterWithItemsResponse,
    ClusterListResponse,
    ClustersByCategoryResponse,
    CreateClusterRequest,
)

__all__ = [
    # Common
    "BaseSchema",
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "TimestampMixin",
    "IDMixin",
    "SortParams",
    # User
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "AuthResponse",
    # Cluster
    "ClusterResponse",
    "ClusterItemResponse",
    "ClusterWithItemsResponse",
    "ClusterListResponse",
    "ClustersByCategoryResponse",
    "CreateClusterRequest",
]
