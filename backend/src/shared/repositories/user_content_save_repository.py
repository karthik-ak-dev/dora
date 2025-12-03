"""
UserContentSave repository for data access.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from ..models.user_content_save import UserContentSave
from .base import BaseRepository


class UserContentSaveRepository(BaseRepository[UserContentSave]):
    """Repository for UserContentSave entity."""
    
    def __init__(self, db: Session):
        super().__init__(UserContentSave, db)
    
    def get_user_save(
        self, 
        user_id: str, 
        shared_content_id: str
    ) -> Optional[UserContentSave]:
        """Check if user already saved this content."""
        stmt = select(UserContentSave).where(
            UserContentSave.user_id == user_id,
            UserContentSave.shared_content_id == shared_content_id
        )
        return self.db.scalar(stmt)
    
    def get_user_saves(
        self, 
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        include_archived: bool = False
    ) -> List[UserContentSave]:
        """Get all saves for a user with pagination."""
        stmt = select(UserContentSave).where(
            UserContentSave.user_id == user_id
        )
        
        if not include_archived:
            stmt = stmt.where(UserContentSave.is_archived == False)
        
        stmt = stmt.options(joinedload(UserContentSave.shared_content))
        stmt = stmt.offset(skip).limit(limit).order_by(UserContentSave.created_at.desc())
        
        return list(self.db.scalars(stmt).all())
