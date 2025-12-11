"""
Database Dependency

FastAPI dependency for database sessions.

This module provides the get_db dependency that yields async database sessions
to route handlers. The session is automatically committed on success and
rolled back on error.

Usage:
======
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.dependencies.database import get_db, DbSession

    # Using type alias (recommended)
    @router.get("/users")
    async def list_users(db: DbSession):
        repo = UserRepository(db)
        return await repo.list()

    # Using explicit Depends
    @router.get("/users/{id}")
    async def get_user(id: str, db: AsyncSession = Depends(get_db)):
        repo = UserRepository(db)
        return await repo.get(id)
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.db import get_db as _get_db


async def get_db() -> AsyncSession:
    """
    FastAPI dependency for database sessions.

    Yields an async database session for the duration of the request.
    The session is automatically:
    - Committed on success
    - Rolled back on exception
    - Closed after the request

    Yields:
        AsyncSession: Database session for the current request
    """
    async for session in _get_db():
        yield session


# Type alias for cleaner route signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
