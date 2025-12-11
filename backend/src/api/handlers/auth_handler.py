"""
Authentication Handler

Handles user registration and login endpoints.

ARCHITECTURE:
=============
    Handler → Service → Repository → Model
          ↘ Utils  ↗

Handlers should ONLY:
- Parse HTTP requests
- Call service methods
- Format HTTP responses
- Handle HTTP-specific errors

Business logic belongs in the SERVICE layer, not here.

DEPENDENCY INJECTION:
=====================
Services are injected via FastAPI's Depends() mechanism.
This makes the code:
- More testable (easy to mock services)
- More explicit about dependencies
- Follows FastAPI best practices
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.shared.schemas.user import (
    UserCreate,
    UserLogin,
    AuthResponse,
    UserResponse,
)
from src.shared.services.auth_service import AuthService
from src.shared.core.exceptions import DuplicateResourceError, AuthenticationError
from src.api.dependencies.services import get_auth_service


router = APIRouter()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.

    Creates a new user account and returns authentication token.

    Args:
        user_data: User registration data (email, password)
        auth_service: Injected AuthService instance

    Returns:
        AuthResponse with user data and JWT token

    Raises:
        400: If email already registered
    """
    try:
        user, access_token, expires_in = await auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
        )
    except DuplicateResourceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return AuthResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            created_at=user.created_at,
        ),
        access_token=access_token,
        expires_in=expires_in,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate user and return JWT token.

    Args:
        credentials: Login credentials (email, password)
        auth_service: Injected AuthService instance

    Returns:
        AuthResponse with user data and JWT token

    Raises:
        401: If credentials are invalid
    """
    try:
        user, access_token, expires_in = await auth_service.login_user(
            email=credentials.email,
            password=credentials.password,
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return AuthResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            created_at=user.created_at,
        ),
        access_token=access_token,
        expires_in=expires_in,
    )
