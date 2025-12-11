"""
UserContentSave repository for data access.
"""

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from ..models.user_content_save import UserContentSave
from ..models.shared_content import SharedContent
from ..models.enums import ContentCategory, ItemStatus
from .base import BaseRepository


class UserContentSaveRepository(BaseRepository[UserContentSave]):
    """Repository for UserContentSave entity."""

    def __init__(self, db: Session):
        super().__init__(UserContentSave, db)

    def get_user_save(self, user_id: str, shared_content_id: str) -> Optional[UserContentSave]:
        """Check if user already saved this content."""
        stmt = select(UserContentSave).where(
            UserContentSave.user_id == user_id,
            UserContentSave.shared_content_id == shared_content_id,
        )
        return self.db.scalar(stmt)

    def get_user_saves(
        self, user_id: str, skip: int = 0, limit: int = 100, include_archived: bool = False
    ) -> List[UserContentSave]:
        """Get all saves for a user with pagination."""
        stmt = select(UserContentSave).where(UserContentSave.user_id == user_id)

        if not include_archived:
            stmt = stmt.where(UserContentSave.is_archived == False)

        stmt = stmt.options(joinedload(UserContentSave.shared_content))
        stmt = stmt.offset(skip).limit(limit).order_by(UserContentSave.created_at.desc())

        return list(self.db.scalars(stmt).all())

    def get_user_saves_with_content(
        self, user_id: str, include_archived: bool = False
    ) -> List[UserContentSave]:
        """Get all saves for a user with SharedContent eagerly loaded."""
        stmt = select(UserContentSave).where(UserContentSave.user_id == user_id)

        if not include_archived:
            stmt = stmt.where(UserContentSave.is_archived == False)

        stmt = stmt.options(joinedload(UserContentSave.shared_content))
        stmt = stmt.order_by(UserContentSave.created_at.desc())

        return list(self.db.scalars(stmt).unique().all())

    def get_user_saves_by_category(
        self,
        user_id: str,
        content_category: ContentCategory,
        include_pending: bool = False,
        include_archived: bool = False,
    ) -> List[UserContentSave]:
        """
        Get user's saves filtered by content category.

        Args:
            user_id: User's ID
            content_category: The category to filter by
            include_pending: Whether to include content still being processed
            include_archived: Whether to include archived saves

        Returns:
            List of UserContentSave objects with matching category
        """
        stmt = (
            select(UserContentSave)
            .join(SharedContent)
            .where(
                UserContentSave.user_id == user_id,
                SharedContent.content_category == content_category,
            )
        )

        if not include_pending:
            stmt = stmt.where(SharedContent.status == ItemStatus.READY)

        if not include_archived:
            stmt = stmt.where(UserContentSave.is_archived == False)

        stmt = stmt.options(joinedload(UserContentSave.shared_content))
        stmt = stmt.order_by(UserContentSave.created_at.desc())

        return list(self.db.scalars(stmt).unique().all())

    def get_user_saves_for_clustering(
        self, user_id: str, content_category: ContentCategory
    ) -> List[UserContentSave]:
        """
        Get user's saves ready for clustering within a category.

        Only returns saves where:
        - SharedContent status is READY
        - SharedContent has the specified content_category
        - SharedContent has an embedding_id (vectorized)
        - Not archived by user

        Args:
            user_id: User's ID
            content_category: The category to get saves for

        Returns:
            List of UserContentSave ready for clustering
        """
        stmt = (
            select(UserContentSave)
            .join(SharedContent)
            .where(
                UserContentSave.user_id == user_id,
                UserContentSave.is_archived == False,
                SharedContent.content_category == content_category,
                SharedContent.status == ItemStatus.READY,
                SharedContent.embedding_id.isnot(None),
            )
        )

        stmt = stmt.options(joinedload(UserContentSave.shared_content))
        stmt = stmt.order_by(UserContentSave.created_at.desc())

        return list(self.db.scalars(stmt).unique().all())
