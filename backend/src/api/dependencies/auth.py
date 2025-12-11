"""
Authentication Dependencies

FastAPI dependencies for user authentication and authorization.

Dependency Hierarchy:
=====================
    get_current_user_token()  ← Extract and validate JWT from header
           │
           ▼
    get_current_user()        ← Verify user exists and is active
           │
           ▼
    require_authenticated()   ← Return current user (for most routes)

Type Aliases:
=============
    CurrentUser     - Authenticated user from JWT
    CurrentUserDict - User data as dict

Usage:
======
    from src.api.dependencies.auth import CurrentUser, get_current_user

    # Using type alias (recommended)
    @router.get("/me")
    async def get_me(current_user: CurrentUser):
        return current_user

    # Using explicit Depends
    @router.get("/profile")
    async def get_profile(user: dict = Depends(get_current_user)):
        return {"email": user["email"]}
"""

from typing import Annotated, Optional

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...config.settings import settings
from ...shared.core.exceptions import AuthenticationError
from ...shared.utils.security import SecurityUtils


# Security scheme for Bearer tokens
security = HTTPBearer()


async def get_current_user_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
) -> dict:
    """
    Extract and validate JWT token from Authorization header.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is missing or invalid
    """
    if not credentials:
        raise AuthenticationError("Authorization header required")

    try:
        token = credentials.credentials
        payload = SecurityUtils.decode_access_token(token, settings.SECRET_KEY)
        return payload
    except ValueError as e:
        raise AuthenticationError(str(e)) from e


async def get_current_user(
    token: Annotated[dict, Depends(get_current_user_token)],
) -> dict:
    """
    Get current authenticated user from token.

    Args:
        token: Decoded JWT token

    Returns:
        User data dict with id, email, etc.

    Raises:
        AuthenticationError: If user_id not in token
    """
    user_id = token.get("user_id")
    email = token.get("email")

    if not user_id:
        raise AuthenticationError("Invalid token payload")

    return {
        "user_id": user_id,
        "email": email,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TYPE ALIASES
# ═══════════════════════════════════════════════════════════════════════════════

# Authenticated user (most common dependency)
CurrentUser = Annotated[dict, Depends(get_current_user)]
