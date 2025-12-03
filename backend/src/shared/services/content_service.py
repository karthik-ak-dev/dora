"""
Content service - Business logic for content operations.
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from ..models.shared_content import SharedContent
from ..models.user_content_save import UserContentSave
from ..models.enums import ItemStatus
from ..repositories.shared_content_repository import SharedContentRepository
from ..repositories.user_content_save_repository import UserContentSaveRepository


class ContentService:
    """Service for content-related business logic."""
    
    def __init__(self, db: Session):
        self.db = db
        self.shared_content_repo = SharedContentRepository(db)
        self.user_save_repo = UserContentSaveRepository(db)
    
    def save_content(
        self,
        user_id: str,
        url: str,
        url_hash: str,
        raw_share_text: Optional[str] = None
    ) -> Tuple[UserContentSave, SharedContent, bool]:
        """
        Save content for a user.
        Returns: (save, content, is_new_content)
        """
        # Check if content already exists
        existing_content = self.shared_content_repo.get_by_url_hash(url_hash)
        
        if existing_content:
            # Content exists, check if user already saved it
            existing_save = self.user_save_repo.get_user_save(
                user_id, 
                str(existing_content.id)
            )
            if existing_save:
                raise ValueError("Content already saved by user")
            
            # Create new save for existing content
            save = self.user_save_repo.create(
                user_id=user_id,
                shared_content_id=existing_content.id,
                raw_share_text=raw_share_text
            )
            self.shared_content_repo.increment_save_count(str(existing_content.id))
            
            return save, existing_content, False
        
        else:
            # Create new shared content
            # TODO: Detect platform from URL
            from ..models.enums import SourcePlatform
            
            new_content = self.shared_content_repo.create(
                url=url,
                url_hash=url_hash,
                source_platform=SourcePlatform.UNKNOWN,
                status=ItemStatus.PENDING,
                save_count=1
            )
            
            # Create save
            save = self.user_save_repo.create(
                user_id=user_id,
                shared_content_id=new_content.id,
                raw_share_text=raw_share_text
            )
            
            return save, new_content, True
