"""
API Dependencies

FastAPI dependencies for injection into route handlers.

Dependencies:
=============
- Database: get_db(), DbSession
- Authentication: get_current_user(), CurrentUser
- Services: get_*_service() functions

Type Aliases:
=============
Type aliases provide cleaner route signatures:

    # Instead of this:
    async def handler(
        db: AsyncSession = Depends(get_db),
        user: dict = Depends(get_current_user)
    ):

    # Write this:
    async def handler(db: DbSession, user: CurrentUser):

Usage:
======
    from src.api.dependencies import DbSession, CurrentUser

    @router.get("/items")
    async def list_items(db: DbSession, user: CurrentUser):
        repo = ItemRepository(db)
        return await repo.list(user_id=user["user_id"])
"""

from src.api.dependencies.database import (
    get_db,
    DbSession,
)
from src.api.dependencies.auth import (
    get_current_user,
    get_current_user_token,
    CurrentUser,
)

__all__ = [
    # Database
    "get_db",
    "DbSession",
    # Authentication
    "get_current_user",
    "get_current_user_token",
    "CurrentUser",
]
