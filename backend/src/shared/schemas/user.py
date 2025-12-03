"""
User-related Pydantic schemas.
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(min_length=8, description="Password (min 8 characters)")


class UserLogin(UserBase):
    """Schema for user login."""
    password: str = Field(min_length=8, description="Password (min 8 characters)")


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Schema for authentication response."""
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
