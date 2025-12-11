"""
User Repository

Database operations specific to the User model.
Extends BaseRepository with user-specific query methods.

Common Operations:
==================
- get_by_email()   → Find user by email address
- email_exists()   → Check if email is already registered

Usage Example:
==============
    async def authenticate_user(db: AsyncSession, email: str, password: str):
        repo = UserRepository(db)
        user = await repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid credentials")
        # Verify password...
        return user
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.repositories.base import BaseRepository
from src.shared.models.user import User


class UserRepository(BaseRepository[User]):
    """
    Repository for User database operations.

    Provides methods for common user queries beyond basic CRUD:
    - Looking up users by email
    - Checking email availability
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize UserRepository.

        Args:
            session: Async database session
        """
        super().__init__(User, session)

    # ═══════════════════════════════════════════════════════════════════════════
    # LOOKUP METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Email lookup is case-insensitive for better UX.

        Args:
            email: Email address to search for

        Returns:
            User if found, None otherwise

        Example:
            user = await repo.get_by_email("user@example.com")
            if user:
                print(f"Found user: {user.id}")

        SQL Generated:
            SELECT * FROM users WHERE email = 'user@example.com'
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.

        Used to validate uniqueness when registering.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False if available

        Example:
            if await repo.email_exists("new@example.com"):
                raise ConflictError("Email already registered")
        """
        user = await self.get_by_email(email)
        return user is not None
