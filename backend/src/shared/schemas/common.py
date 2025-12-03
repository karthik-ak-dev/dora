"""
Common schemas used across the application.
"""
from pydantic import BaseModel, Field
from typing import Optional


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(20, ge=1, le=100, description="Number of items to return")


class PaginatedResponse(BaseModel):
    """Base paginated response."""
    total: int
    skip: int
    limit: int
    has_more: bool
