"""
UserContentSave Repository

Database operations for user content saves.

Common Operations:
==================
- get_user_saves()           → Get paginated saves for a user
- get_user_save()            → Get specific save for a user
- get_user_saves_by_category() → Filter by content category
- get_user_saves_with_content() → Include SharedContent in results
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.shared.repositories.base import BaseRepository
from src.shared.models.user_content_save import UserContentSave
from src.shared.models.shared_content import SharedContent
from src.shared.models.enums import ContentCategory, ItemStatus


class UserContentSaveRepository(BaseRepository[UserContentSave]):
    """
    Repository for UserContentSave database operations.

    Handles user-specific content saves with filtering and eager loading.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize UserContentSaveRepository.

        Args:
            session: Async database session
        """
        super().__init__(UserContentSave, session)

    # ═══════════════════════════════════════════════════════════════════════════
    # READ OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_user_save(
        self,
        user_id: UUID,
        shared_content_id: UUID,
    ) -> Optional[UserContentSave]:
        """
        Get a specific save for a user and content.

        Used to check if user already saved specific content.

        Args:
            user_id: User's UUID
            shared_content_id: Content UUID

        Returns:
            UserContentSave if exists, None otherwise
        """
        result = await self.session.execute(
            select(UserContentSave).where(
                UserContentSave.user_id == user_id,
                UserContentSave.shared_content_id == shared_content_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_saves(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_archived: bool = False,
    ) -> List[UserContentSave]:
        """
        Get paginated saves for a user.

        Args:
            user_id: User's UUID
            skip: Number of records to skip
            limit: Max records to return
            include_archived: Include archived saves

        Returns:
            List of UserContentSave
        """
        query = (
            select(UserContentSave)
            .options(selectinload(UserContentSave.shared_content))
            .where(UserContentSave.user_id == user_id)
        )

        if not include_archived:
            query = query.where(UserContentSave.is_archived == False)

        query = query.order_by(UserContentSave.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_saves_with_content(
        self,
        user_id: UUID,
        include_archived: bool = False,
    ) -> List[UserContentSave]:
        """
        Get all saves for a user with SharedContent eagerly loaded.

        Args:
            user_id: User's UUID
            include_archived: Include archived saves

        Returns:
            List of UserContentSave with shared_content populated
        """
        query = (
            select(UserContentSave)
            .options(selectinload(UserContentSave.shared_content))
            .where(UserContentSave.user_id == user_id)
        )

        if not include_archived:
            query = query.where(UserContentSave.is_archived == False)

        query = query.order_by(UserContentSave.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_saves_by_category(
        self,
        user_id: UUID,
        content_category: ContentCategory,
        include_pending: bool = False,
        include_archived: bool = False,
    ) -> List[UserContentSave]:
        """
        Get user's saves filtered by content category.

        Args:
            user_id: User's UUID
            content_category: Category to filter by
            include_pending: Include content still being processed
            include_archived: Include archived saves

        Returns:
            List of UserContentSave in the category
        """
        query = (
            select(UserContentSave)
            .join(SharedContent)
            .options(selectinload(UserContentSave.shared_content))
            .where(
                UserContentSave.user_id == user_id,
                SharedContent.content_category == content_category,
            )
        )

        if not include_pending:
            query = query.where(SharedContent.status == ItemStatus.READY)

        if not include_archived:
            query = query.where(UserContentSave.is_archived == False)

        query = query.order_by(UserContentSave.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_user_saves(
        self,
        user_id: UUID,
        include_archived: bool = False,
    ) -> int:
        """
        Count total saves for a user.

        Args:
            user_id: User's UUID
            include_archived: Include archived saves

        Returns:
            Number of saves
        """
        filters = {"user_id": user_id}
        if not include_archived:
            filters["is_archived"] = False
        return await self.count(filters=filters)
