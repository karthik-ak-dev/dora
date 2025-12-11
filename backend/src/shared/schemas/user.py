"""
User Schemas

Request/response models for user and authentication endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from src.shared.schemas.common import BaseSchema


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(
        min_length=8,
        description="Password (minimum 8 characters)",
    )


class UserLogin(UserBase):
    """Schema for user login."""

    password: str = Field(
        min_length=8,
        description="Password (minimum 8 characters)",
    )


class UserResponse(BaseSchema):
    """Schema for user response."""

    id: str
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    """Schema for authentication response."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
