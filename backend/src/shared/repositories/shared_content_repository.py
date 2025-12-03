"""
SharedContent repository for data access.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.shared_content import SharedContent
from ..models.enums import ItemStatus
from .base import BaseRepository


class SharedContentRepository(BaseRepository[SharedContent]):
    """Repository for SharedContent entity."""
    
    def __init__(self, db: Session):
        super().__init__(SharedContent, db)
    
    def get_by_url_hash(self, url_hash: str) -> Optional[SharedContent]:
        """Get content by URL hash (deduplication key)."""
        stmt = select(SharedContent).where(SharedContent.url_hash == url_hash)
        return self.db.scalar(stmt)
    
    def get_by_status(self, status: ItemStatus, limit: int = 100) -> List[SharedContent]:
        """Get content by processing status."""
        stmt = select(SharedContent).where(SharedContent.status == status).limit(limit)
        return list(self.db.scalars(stmt).all())
    
    def increment_save_count(self, content_id: str) -> None:
        """Increment save count for content."""
        content = self.get_by_id(content_id)
        if content:
            content.save_count += 1
            self.db.commit()
    
    def decrement_save_count(self, content_id: str) -> None:
        """Decrement save count for content."""
        content = self.get_by_id(content_id)
        if content and content.save_count > 0:
            content.save_count -= 1
            self.db.commit()
