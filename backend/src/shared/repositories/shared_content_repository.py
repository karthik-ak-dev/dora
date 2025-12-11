"""
SharedContent repository for data access.
"""

from typing import Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.shared_content import SharedContent
from ..models.enums import ItemStatus, ContentCategory
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

    def get_by_category(
        self,
        content_category: ContentCategory,
        status: Optional[ItemStatus] = None,
        limit: int = 100,
    ) -> List[SharedContent]:
        """Get content by category with optional status filter."""
        stmt = select(SharedContent).where(SharedContent.content_category == content_category)

        if status:
            stmt = stmt.where(SharedContent.status == status)

        stmt = stmt.limit(limit).order_by(SharedContent.created_at.desc())
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

    def update(self, content_id: str, **kwargs: Any) -> Optional[SharedContent]:
        """
        Update SharedContent fields.

        Args:
            content_id: The SharedContent ID
            **kwargs: Fields to update

        Returns:
            Updated SharedContent or None if not found
        """
        content = self.get_by_id(content_id)
        if not content:
            return None

        for key, value in kwargs.items():
            if hasattr(content, key):
                setattr(content, key, value)

        self.db.commit()
        self.db.refresh(content)
        return content

    def update_after_processing(
        self,
        content_id: str,
        content_category: ContentCategory,
        topic_main: Optional[str] = None,
        subcategories: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        embedding_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[SharedContent]:
        """
        Update SharedContent after AI processing completes.

        This sets the authoritative content_category and transitions to READY status.

        Args:
            content_id: The SharedContent ID
            content_category: The classified category (required, strong classification)
            topic_main: Main topic extracted by AI
            subcategories: Fine-grained tags
            locations: Locations mentioned
            entities: Entities (people, brands, products)
            embedding_id: Vector DB reference
            **kwargs: Additional fields to update

        Returns:
            Updated SharedContent
        """
        content = self.get_by_id(content_id)
        if not content:
            return None

        # Set authoritative classification
        content.content_category = content_category
        content.status = ItemStatus.READY

        # Set optional fields
        if topic_main is not None:
            content.topic_main = topic_main
        if subcategories is not None:
            content.subcategories = subcategories
        if locations is not None:
            content.locations = locations
        if entities is not None:
            content.entities = entities
        if embedding_id is not None:
            content.embedding_id = embedding_id

        # Set any additional fields
        for key, value in kwargs.items():
            if hasattr(content, key):
                setattr(content, key, value)

        self.db.commit()
        self.db.refresh(content)
        return content
