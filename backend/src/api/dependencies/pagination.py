"""
Pagination dependency.
"""
from fastapi import Query

from ...shared.schemas.common import PaginationParams


async def get_pagination(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return")
) -> PaginationParams:
    """Pagination parameters dependency."""
    return PaginationParams(skip=skip, limit=limit)
