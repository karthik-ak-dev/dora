"""
Content service - Business logic for content operations.

CLASSIFICATION ARCHITECTURE:
- When content is saved, SharedContent is created with status=PENDING and content_category=None
- Background worker processes the content and assigns content_category (strong classification)
- content_category is assigned ONCE and is immutable after status=READY
- Clustering then groups items WITHIN each content_category
"""

from typing import Optional, Tuple, List
from sqlalchemy.orm import Session

from ..models.shared_content import SharedContent
from ..models.user_content_save import UserContentSave
from ..models.enums import ItemStatus, ContentCategory, SourcePlatform
from ..repositories.shared_content_repository import SharedContentRepository
from ..repositories.user_content_save_repository import UserContentSaveRepository


class ContentService:
    """Service for content-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.shared_content_repo = SharedContentRepository(db)
        self.user_save_repo = UserContentSaveRepository(db)

    def save_content(
        self, user_id: str, url: str, url_hash: str, raw_share_text: Optional[str] = None
    ) -> Tuple[UserContentSave, SharedContent, bool]:
        """
        Save content for a user.

        Flow:
        1. Check if SharedContent exists (by url_hash)
        2. If exists: Create UserContentSave linking to existing content
        3. If new: Create SharedContent (status=PENDING, content_category=None)
                   → Background worker will classify and set content_category

        Returns: (save, content, is_new_content)
        """
        # Check if content already exists
        existing_content = self.shared_content_repo.get_by_url_hash(url_hash)

        if existing_content:
            # Content exists, check if user already saved it
            existing_save = self.user_save_repo.get_user_save(user_id, str(existing_content.id))
            if existing_save:
                raise ValueError("Content already saved by user")

            # Create new save for existing content
            save = self.user_save_repo.create(
                user_id=user_id,
                shared_content_id=existing_content.id,
                raw_share_text=raw_share_text,
            )
            self.shared_content_repo.increment_save_count(str(existing_content.id))

            return save, existing_content, False

        else:
            # Create new shared content
            # content_category will be assigned by AI processing worker
            new_content = self.shared_content_repo.create(
                url=url,
                url_hash=url_hash,
                source_platform=SourcePlatform.UNKNOWN,
                status=ItemStatus.PENDING,
                content_category=None,  # Will be assigned during AI processing
                save_count=1,
            )

            # Create save
            save = self.user_save_repo.create(
                user_id=user_id, shared_content_id=new_content.id, raw_share_text=raw_share_text
            )

            return save, new_content, True

    def get_user_saves_by_category(
        self, user_id: str, content_category: ContentCategory, include_pending: bool = False
    ) -> List[UserContentSave]:
        """
        Get user's saves filtered by content category.

        Args:
            user_id: User's ID
            content_category: The category to filter by
            include_pending: Whether to include content that's still being processed

        Returns:
            List of UserContentSave objects with matching category
        """
        return self.user_save_repo.get_user_saves_by_category(
            user_id=user_id, content_category=content_category, include_pending=include_pending
        )

    def get_user_saves_grouped_by_category(
        self, user_id: str
    ) -> dict[ContentCategory, List[UserContentSave]]:
        """
        Get user's saves grouped by content category.

        Returns:
            Dictionary mapping ContentCategory to list of saves
        """
        saves = self.user_save_repo.get_user_saves_with_content(user_id)

        grouped: dict[ContentCategory, List[UserContentSave]] = {}
        for save in saves:
            category = save.shared_content.content_category
            if category:
                if category not in grouped:
                    grouped[category] = []
                grouped[category].append(save)

        return grouped

    def update_content_category(
        self, shared_content_id: str, content_category: ContentCategory
    ) -> SharedContent:
        """
        Update the content category for a SharedContent item.

        This is called by the AI processing worker after classification.
        content_category should only be set once (when status transitions to READY).

        Args:
            shared_content_id: SharedContent ID
            content_category: The classified category

        Returns:
            Updated SharedContent
        """
        content = self.shared_content_repo.get_by_id(shared_content_id)
        if not content:
            raise ValueError("SharedContent not found")

        # Only allow setting category if it's not already set
        if content.content_category is not None and content.status == ItemStatus.READY:
            raise ValueError("Content category already assigned and content is READY")

        return self.shared_content_repo.update(shared_content_id, content_category=content_category)
