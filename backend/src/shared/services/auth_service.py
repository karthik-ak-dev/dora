"""
Authentication Service

Business logic for user authentication and registration.

Service Pattern:
================
Services encapsulate business logic and coordinate between:
- Repositories (data access)
- External services (if any)
- Domain logic

Usage:
======
    from src.shared.services.auth_service import AuthService

    service = AuthService(db)
    user, token, expires = await service.register_user(email, password)
"""

from datetime import timedelta
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.shared.repositories.user_repository import UserRepository
from src.shared.utils.security import SecurityUtils
from src.shared.core.exceptions import DuplicateResourceError, AuthenticationError
from src.shared.models.user import User


class AuthService:
    """
    Service for authentication-related business logic.

    Handles:
    - User registration with email/password
    - User authentication (login)
    - JWT token generation

    Attributes:
        session: Database session
        repo: UserRepository instance
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize AuthService.

        Args:
            session: Async database session
        """
        self.session = session
        self.repo = UserRepository(session)

    async def register_user(
        self,
        email: str,
        password: str,
    ) -> Tuple[User, str, int]:
        """
        Register a new user.

        Creates a new user account and generates a JWT token.

        Args:
            email: User's email address
            password: Plain text password (will be hashed)

        Returns:
            Tuple of (user, access_token, expires_in_seconds)

        Raises:
            DuplicateResourceError: If email already registered

        Example:
            user, token, expires = await service.register_user(
                email="user@example.com",
                password="secure_password123"
            )
        """
        # Check if email already exists
        if await self.repo.email_exists(email):
            raise DuplicateResourceError("Email already registered")

        # Hash password using bcrypt
        password_hash = SecurityUtils.hash_password(password)

        # Create user
        user = await self.repo.create(
            email=email,
            password_hash=password_hash,
        )

        # Generate JWT token
        access_token = SecurityUtils.create_access_token(
            data={"user_id": str(user.id), "email": user.email},
            secret_key=settings.SECRET_KEY,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds

        return user, access_token, expires_in

    async def login_user(
        self,
        email: str,
        password: str,
    ) -> Tuple[User, str, int]:
        """
        Authenticate user and generate token.

        Verifies credentials and returns a JWT token on success.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            Tuple of (user, access_token, expires_in_seconds)

        Raises:
            AuthenticationError: If credentials are invalid

        Example:
            user, token, expires = await service.login_user(
                email="user@example.com",
                password="their_password"
            )
        """
        # Get user by email
        user = await self.repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not SecurityUtils.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        # Generate JWT token
        access_token = SecurityUtils.create_access_token(
            data={"user_id": str(user.id), "email": user.email},
            secret_key=settings.SECRET_KEY,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds

        return user, access_token, expires_in
