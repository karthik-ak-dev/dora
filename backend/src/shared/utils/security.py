"""
Security Utilities

Password hashing and JWT token management.

Password Hashing:
=================
Uses bcrypt for secure password hashing with automatic salt generation.

JWT Tokens:
===========
Uses PyJWT for JSON Web Token creation and validation.

Usage:
======
    from src.shared.utils.security import SecurityUtils

    # Hash password
    hashed = SecurityUtils.hash_password("password123")

    # Verify password
    if SecurityUtils.verify_password("password123", hashed):
        print("Password matches!")

    # Create JWT
    token = SecurityUtils.create_access_token(
        data={"user_id": "123"},
        secret_key="secret",
        expires_delta=timedelta(hours=1)
    )

    # Decode JWT
    payload = SecurityUtils.decode_access_token(token, "secret")
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext


# Password hashing configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


class SecurityUtils:
    """
    Security utilities for authentication.

    Provides:
    - Password hashing with bcrypt
    - JWT token creation and validation
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # PASSWORD HASHING
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.

        Bcrypt automatically:
        - Generates a random salt
        - Uses a secure work factor
        - Produces a hash that includes the salt

        Args:
            password: Plain text password

        Returns:
            Bcrypt hash string (includes salt)
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against bcrypt hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Bcrypt hash to verify against

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    # ═══════════════════════════════════════════════════════════════════════════
    # JWT TOKENS
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def create_access_token(
        data: dict,
        secret_key: str,
        expires_delta: Optional[timedelta] = None,
        algorithm: str = "HS256",
    ) -> str:
        """
        Create JWT access token.

        Args:
            data: Payload data to encode (e.g., user_id, email)
            secret_key: Secret key for signing
            expires_delta: Token expiration time (default: 7 days)
            algorithm: JWT algorithm (default: HS256)

        Returns:
            Encoded JWT token string

        Example:
            token = SecurityUtils.create_access_token(
                data={"user_id": "123", "email": "user@example.com"},
                secret_key=settings.SECRET_KEY,
                expires_delta=timedelta(hours=24)
            )
        """
        to_encode = data.copy()

        # Set expiration
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=7)

        # Add standard JWT claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        })

        # Encode the token
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)

        return encoded_jwt

    @staticmethod
    def decode_access_token(
        token: str,
        secret_key: str,
        algorithm: str = "HS256",
    ) -> dict:
        """
        Decode and verify JWT token.

        Args:
            token: JWT token string
            secret_key: Secret key used for signing
            algorithm: JWT algorithm (default: HS256)

        Returns:
            Decoded token payload

        Raises:
            ValueError: If token is expired or invalid

        Example:
            try:
                payload = SecurityUtils.decode_access_token(token, settings.SECRET_KEY)
                user_id = payload["user_id"]
            except ValueError as e:
                raise AuthenticationError(str(e))
        """
        try:
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
