"""
Content Service

Business logic for content operations.

CLASSIFICATION ARCHITECTURE:
- When content is saved, SharedContent is created with status=PENDING
- Background worker processes the content and assigns content_category
- content_category is assigned ONCE and is immutable after status=READY
- Clustering then groups items WITHIN each content_category

Usage:
======
    from src.shared.services.content_service import ContentService

    service = ContentService(db)
    save, content, is_new = await service.save_content(user_id, url, ...)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.shared_content import SharedContent
from src.shared.models.user_content_save import UserContentSave
from src.shared.models.enums import ItemStatus, ContentCategory, SourcePlatform
from src.shared.repositories.shared_content_repository import SharedContentRepository
from src.shared.repositories.user_content_save_repository import UserContentSaveRepository
from src.shared.core.exceptions import ConflictError, NotFoundError


@dataclass
class PaginatedSaves:
    """Paginated list of user saves."""

    items: List[UserContentSave]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class ContentService:
    """
    Service for content-related business logic.

    Handles:
    - Saving new content (with deduplication)
    - Retrieving user's saves with filtering
    - Updating save properties (favorites, archive)
    - Category-based filtering and grouping
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize ContentService.

        Args:
            session: Async database session
        """
        self.session = session
        self.shared_content_repo = SharedContentRepository(session)
        self.user_save_repo = UserContentSaveRepository(session)

    async def save_content(
        self,
        user_id: UUID,
        url: str,
        url_hash: str,
        platform: SourcePlatform,
        raw_share_text: Optional[str] = None,
    ) -> Tuple[UserContentSave, SharedContent, bool]:
        """
        Save content for a user.

        Flow:
        1. Check if SharedContent exists (by url_hash)
        2. If exists: Create UserContentSave linking to existing content
        3. If new: Create SharedContent (status=PENDING, content_category=None)
                   → Background worker will classify and set content_category

        Args:
            user_id: User's UUID
            url: Content URL
            url_hash: SHA256 hash of normalized URL
            platform: Source platform (Instagram, YouTube, etc.)
            raw_share_text: User's personal note

        Returns:
            Tuple of (save, content, is_new_content)

        Raises:
            ConflictError: If user already saved this content
        """
        # Check if content already exists
        existing_content = await self.shared_content_repo.get_by_url_hash(url_hash)

        if existing_content:
            # Content exists, check if user already saved it
            existing_save = await self.user_save_repo.get_user_save(
                user_id=user_id,
                shared_content_id=existing_content.id,
            )
            if existing_save:
                raise ConflictError("Content already saved by user")

            # Create new save for existing content
            save = await self.user_save_repo.create(
                user_id=user_id,
                shared_content_id=existing_content.id,
                raw_share_text=raw_share_text,
            )
            await self.shared_content_repo.increment_save_count(existing_content.id)

            return save, existing_content, False
        else:
            # Create new shared content
            # content_category will be assigned by AI processing worker
            new_content = await self.shared_content_repo.create(
                url=url,
                url_hash=url_hash,
                source_platform=platform,
                status=ItemStatus.PENDING,
                content_category=None,  # Will be assigned during AI processing
                save_count=1,
            )

            # Create save
            save = await self.user_save_repo.create(
                user_id=user_id,
                shared_content_id=new_content.id,
                raw_share_text=raw_share_text,
            )

            return save, new_content, True

    async def get_user_saves(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        category: Optional[ContentCategory] = None,
        status: Optional[ItemStatus] = None,
        include_archived: bool = False,
    ) -> PaginatedSaves:
        """
        Get paginated list of user's saved content.

        Args:
            user_id: User's UUID
            page: Page number (1-indexed)
            page_size: Items per page
            category: Optional category filter
            status: Optional status filter
            include_archived: Whether to include archived saves

        Returns:
            PaginatedSaves with items and pagination info
        """
        skip = (page - 1) * page_size

        if category:
            # Filter by category
            all_saves = await self.user_save_repo.get_user_saves_by_category(
                user_id=user_id,
                content_category=category,
                include_pending=(status != ItemStatus.READY),
                include_archived=include_archived,
            )
            # Apply status filter if specified
            if status:
                all_saves = [s for s in all_saves if s.shared_content.status == status]

            total = len(all_saves)
            items = all_saves[skip : skip + page_size]
        else:
            # Get all saves with pagination
            items = await self.user_save_repo.get_user_saves(
                user_id=user_id,
                skip=skip,
                limit=page_size,
                include_archived=include_archived,
            )
            # Get total count
            all_saves = await self.user_save_repo.get_user_saves_with_content(
                user_id=user_id,
                include_archived=include_archived,
            )
            if status:
                all_saves = [s for s in all_saves if s.shared_content.status == status]
            total = len(all_saves)

        return PaginatedSaves(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(skip + page_size) < total,
            has_prev=page > 1,
        )

    async def get_user_save_by_id(
        self,
        user_id: UUID,
        save_id: UUID,
    ) -> Optional[UserContentSave]:
        """
        Get a specific save by ID, ensuring it belongs to the user.

        Args:
            user_id: User's UUID
            save_id: Save UUID

        Returns:
            UserContentSave if found and belongs to user, None otherwise
        """
        save = await self.user_save_repo.get(save_id)
        if save and save.user_id == user_id:
            return save
        return None

    async def delete_user_save(
        self,
        user_id: UUID,
        save_id: UUID,
    ) -> bool:
        """
        Delete a user's save.

        This removes the UserContentSave but keeps SharedContent
        (other users may have saved it).

        Args:
            user_id: User's UUID
            save_id: Save UUID to delete

        Returns:
            True if deleted, False if not found
        """
        save = await self.get_user_save_by_id(user_id, save_id)
        if not save:
            return False

        # Decrement save count on SharedContent
        await self.shared_content_repo.decrement_save_count(save.shared_content_id)

        # Delete the save
        await self.user_save_repo.delete(save_id)
        return True

    async def update_user_save(
        self,
        user_id: UUID,
        save_id: UUID,
        raw_share_text: Optional[str] = None,
        is_favorited: Optional[bool] = None,
        is_archived: Optional[bool] = None,
    ) -> Optional[UserContentSave]:
        """
        Update a user's save.

        Args:
            user_id: User's UUID
            save_id: Save UUID to update
            raw_share_text: New note (if provided)
            is_favorited: New favorite status (if provided)
            is_archived: New archived status (if provided)

        Returns:
            Updated UserContentSave or None if not found
        """
        save = await self.get_user_save_by_id(user_id, save_id)
        if not save:
            return None

        # Update fields if provided
        if raw_share_text is not None:
            save.raw_share_text = raw_share_text
        if is_favorited is not None:
            save.is_favorited = is_favorited
        if is_archived is not None:
            save.is_archived = is_archived

        await self.session.flush()
        await self.session.refresh(save)
        return save

    async def get_user_saves_by_category(
        self,
        user_id: UUID,
        content_category: ContentCategory,
        include_pending: bool = False,
    ) -> List[UserContentSave]:
        """
        Get user's saves filtered by content category.

        Args:
            user_id: User's UUID
            content_category: Category to filter by
            include_pending: Include content still being processed

        Returns:
            List of UserContentSave objects with matching category
        """
        return await self.user_save_repo.get_user_saves_by_category(
            user_id=user_id,
            content_category=content_category,
            include_pending=include_pending,
        )

    async def get_user_saves_grouped_by_category(
        self,
        user_id: UUID,
    ) -> Dict[ContentCategory, List[UserContentSave]]:
        """
        Get user's saves grouped by content category.

        Returns:
            Dictionary mapping ContentCategory to list of saves
        """
        saves = await self.user_save_repo.get_user_saves_with_content(user_id)

        grouped: Dict[ContentCategory, List[UserContentSave]] = {}
        for save in saves:
            category = save.shared_content.content_category
            if category:
                if category not in grouped:
                    grouped[category] = []
                grouped[category].append(save)

        return grouped

    async def get_category_counts(self, user_id: UUID) -> Dict[str, int]:
        """
        Get count of saves per category for a user.

        Returns:
            Dict mapping category value to count
        """
        grouped = await self.get_user_saves_grouped_by_category(user_id)
        return {cat.value: len(saves) for cat, saves in grouped.items()}

    async def update_content_category(
        self,
        shared_content_id: UUID,
        content_category: ContentCategory,
    ) -> SharedContent:
        """
        Update the content category for a SharedContent item.

        This is called by the AI processing worker after classification.
        content_category should only be set once (when status transitions to READY).

        Args:
            shared_content_id: SharedContent UUID
            content_category: The classified category

        Returns:
            Updated SharedContent

        Raises:
            NotFoundError: If content not found
            ConflictError: If category already assigned and content is READY
        """
        content = await self.shared_content_repo.get(shared_content_id)
        if not content:
            raise NotFoundError("Content", str(shared_content_id))

        # Only allow setting category if it's not already set
        if content.content_category is not None and content.status == ItemStatus.READY:
            raise ConflictError("Content category already assigned and content is READY")

        return await self.shared_content_repo.update(
            shared_content_id,
            content_category=content_category,
        )

    async def get_shared_content(self, content_id: UUID) -> Optional[SharedContent]:
        """
        Get SharedContent by ID.

        Args:
            content_id: SharedContent UUID

        Returns:
            SharedContent or None
        """
        return await self.shared_content_repo.get(content_id)
