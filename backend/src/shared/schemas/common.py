"""
Common Schemas

Shared schemas used across the application for consistent API responses.

Schema Types:
=============
- BaseSchema: Base with common config (from_attributes, populate_by_name)
- Pagination: Parameters and response metadata
- Generic Responses: PaginatedResponse[T], MessageResponse, ErrorResponse

Usage:
======
    from src.shared.schemas.common import (
        BaseSchema,
        PaginationParams,
        PaginatedResponse,
        PaginationMeta,
    )

    class UserResponse(BaseSchema):
        id: str
        email: str
        created_at: datetime

    # In route handler
    return PaginatedResponse(
        data=users,
        pagination=PaginationMeta.create(page=1, per_page=20, total=100)
    )
"""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


# Generic type for paginated responses
DataT = TypeVar("DataT")


class BaseSchema(BaseModel):
    """
    Base schema with common configuration.

    All response schemas should inherit from this class.
    Provides:
    - from_attributes: Allow creating from ORM models
    - populate_by_name: Allow field population by name or alias
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGINATION
# ═══════════════════════════════════════════════════════════════════════════════


class PaginationParams(BaseModel):
    """
    Pagination query parameters.

    Used as a dependency in route handlers to parse pagination params.

    Example:
        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            items = await service.list(
                offset=pagination.offset,
                limit=pagination.limit
            )
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.per_page


class PaginationMeta(BaseModel):
    """
    Pagination metadata in response.

    Provides all pagination info for clients to navigate results.
    """

    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    total: int = Field(description="Total number of items")
    total_pages: int = Field(description="Total number of pages")

    @classmethod
    def create(cls, page: int, per_page: int, total: int) -> "PaginationMeta":
        """
        Create pagination meta from parameters.

        Automatically calculates total_pages.

        Args:
            page: Current page number
            per_page: Items per page
            total: Total number of items

        Returns:
            PaginationMeta instance
        """
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        )


class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    Generic paginated response.

    Type-safe generic wrapper for paginated data.

    Example:
        PaginatedResponse[UserResponse](
            data=[user1, user2],
            pagination=PaginationMeta.create(page=1, per_page=20, total=50)
        )
    """

    data: list[DataT]
    pagination: PaginationMeta


# ═══════════════════════════════════════════════════════════════════════════════
# STANDARD RESPONSES
# ═══════════════════════════════════════════════════════════════════════════════


class MessageResponse(BaseModel):
    """Simple message response for success confirmations."""

    message: str
    success: bool = True


class ErrorDetail(BaseModel):
    """Error detail structure in error responses."""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional error context",
    )


class ErrorResponse(BaseModel):
    """
    Standard error response schema.

    All API errors return this format for consistency.

    Example:
        {
            "error": {
                "code": "NOT_FOUND",
                "message": "User with id 'abc-123' not found",
                "details": {}
            }
        }
    """

    error: ErrorDetail


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = "healthy"
    service: str = "dora"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════════
# MIXINS
# ═══════════════════════════════════════════════════════════════════════════════


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields in responses."""

    created_at: datetime
    updated_at: datetime


class IDMixin(BaseModel):
    """Mixin for ID field in responses."""

    id: str


# ═══════════════════════════════════════════════════════════════════════════════
# SORTING
# ═══════════════════════════════════════════════════════════════════════════════


class SortParams(BaseModel):
    """Sorting query parameters."""

    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    )
