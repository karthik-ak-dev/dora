"""
Authentication handler.
Handles user registration and login.

ARCHITECTURE NOTE:
This handler follows the proper layered architecture:
  Handler → Service → Repository → Model
          ↘ Utils  ↗

Handlers should ONLY:
- Parse HTTP requests
- Call service methods
- Format HTTP responses
- Handle HTTP-specific errors

Business logic belongs in the SERVICE layer, not here.

DEPENDENCY INJECTION:
Services are injected via FastAPI's Depends() mechanism.
This makes the code:
- More testable (easy to mock services)
- More explicit about dependencies
- Follows FastAPI best practices
"""
from fastapi import APIRouter, Depends, HTTPException, status

from ...shared.schemas.user import UserCreate, UserLogin, AuthResponse, UserResponse
from ...shared.services.auth_service import AuthService
from ...shared.utils.exceptions import DuplicateResourceError, AuthenticationError
from ..dependencies.services import get_auth_service

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)  # ← Injected dependency
):
    """
    Register a new user.
    
    The AuthService is injected via dependency injection, making this
    handler easy to test and following FastAPI best practices.
    """
    try:
        user, access_token, expires_in = auth_service.register_user(
            email=user_data.email,
            password=user_data.password
        )
    except DuplicateResourceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return AuthResponse(
        user=UserResponse.from_orm(user),
        access_token=access_token,
        expires_in=expires_in
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)  # ← Injected dependency
):
    """
    Authenticate user and return JWT token.
    
    The AuthService is injected via dependency injection, making this
    handler easy to test and following FastAPI best practices.
    """
    try:
        user, access_token, expires_in = auth_service.login_user(
            email=credentials.email,
            password=credentials.password
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    
    return AuthResponse(
        user=UserResponse.from_orm(user),
        access_token=access_token,
        expires_in=expires_in
    )


