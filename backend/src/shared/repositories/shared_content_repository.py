"""
SharedContent Repository

Database operations specific to the SharedContent model.

Common Operations:
==================
- get_by_url_hash()    → Find content by URL hash (for deduplication)
- update_status()      → Update processing status
- increment/decrement_save_count() → Update save statistics
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.repositories.base import BaseRepository
from src.shared.models.shared_content import SharedContent
from src.shared.models.enums import ItemStatus


class SharedContentRepository(BaseRepository[SharedContent]):
    """
    Repository for SharedContent database operations.

    Handles content deduplication via URL hash lookups
    and processing status management.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize SharedContentRepository.

        Args:
            session: Async database session
        """
        super().__init__(SharedContent, session)

    # ═══════════════════════════════════════════════════════════════════════════
    # LOOKUP METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_by_url_hash(self, url_hash: str) -> Optional[SharedContent]:
        """
        Get content by URL hash.

        URL hash is used for deduplication - same URL always has same hash.

        Args:
            url_hash: SHA256 hash of normalized URL

        Returns:
            SharedContent if found, None otherwise

        Example:
            existing = await repo.get_by_url_hash(url_hash)
            if existing:
                print("Content already exists!")
        """
        result = await self.session.execute(
            select(SharedContent).where(SharedContent.url_hash == url_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_status(
        self,
        status: ItemStatus,
        offset: int = 0,
        limit: int = 100,
    ) -> list[SharedContent]:
        """
        Get content by processing status.

        Useful for finding content that needs processing.

        Args:
            status: Status to filter by (PENDING, READY, FAILED)
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            List of SharedContent with matching status
        """
        result = await self.session.execute(
            select(SharedContent)
            .where(SharedContent.status == status)
            .order_by(SharedContent.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ═══════════════════════════════════════════════════════════════════════════
    # UPDATE METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    async def update_status(
        self,
        content_id: UUID,
        status: ItemStatus,
        error_message: Optional[str] = None,
    ) -> Optional[SharedContent]:
        """
        Update processing status.

        Args:
            content_id: Content UUID
            status: New status
            error_message: Error message if status is FAILED

        Returns:
            Updated content or None if not found
        """
        content = await self.get(content_id)
        if not content:
            return None

        content.status = status
        if error_message and status == ItemStatus.FAILED:
            # Store error in metadata or dedicated field if needed
            pass

        await self.session.flush()
        await self.session.refresh(content)
        return content

    async def increment_save_count(self, content_id: UUID) -> Optional[SharedContent]:
        """
        Increment the save count when a user saves content.

        Args:
            content_id: Content UUID

        Returns:
            Updated content or None if not found
        """
        content = await self.get(content_id)
        if not content:
            return None

        content.save_count = (content.save_count or 0) + 1
        await self.session.flush()
        await self.session.refresh(content)
        return content

    async def decrement_save_count(self, content_id: UUID) -> Optional[SharedContent]:
        """
        Decrement the save count when a user removes their save.

        Args:
            content_id: Content UUID

        Returns:
            Updated content or None if not found
        """
        content = await self.get(content_id)
        if not content:
            return None

        content.save_count = max(0, (content.save_count or 0) - 1)
        await self.session.flush()
        await self.session.refresh(content)
        return content
