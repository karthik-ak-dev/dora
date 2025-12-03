"""
User repository for data access.
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.user import User
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity."""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)
    
    def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        return self.get_by_email(email) is not None
