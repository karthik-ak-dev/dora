"""
Content-related Pydantic schemas.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict
from ..models.enums import SourcePlatform, ItemStatus, ContentCategory, IntentType


class SaveContentRequest(BaseModel):
    """Request to save new content."""

    url: str = Field(description="URL to save")
    raw_share_text: Optional[str] = Field(None, description="User's personal note")


class UpdateSaveRequest(BaseModel):
    """Request to update a save."""

    raw_share_text: Optional[str] = Field(None, description="User's personal note")
    is_favorited: Optional[bool] = Field(None, description="Favorite status")
    is_archived: Optional[bool] = Field(None, description="Archived status")


class SharedContentResponse(BaseModel):
    """
    Response for shared content.

    content_category: The authoritative classification assigned during AI processing.
    This is NOT user-dependent - it's a strong, tight classification.
    """

    id: str
    url: str
    source_platform: SourcePlatform
    status: ItemStatus
    title: Optional[str] = None
    caption: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    content_category: Optional[ContentCategory] = None
    topic_main: Optional[str] = None
    subcategories: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    intent: Optional[IntentType] = None
    save_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserContentSaveResponse(BaseModel):
    """Response for user content save."""

    id: str
    user_id: str
    shared_content_id: str
    raw_share_text: Optional[str] = None
    is_favorited: bool
    is_archived: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SaveWithContentResponse(BaseModel):
    """Response for a save with its content details."""

    save: UserContentSaveResponse
    content: SharedContentResponse


class SaveContentResponse(BaseModel):
    """Response after saving content."""

    save: UserContentSaveResponse
    content: SharedContentResponse
    message: str


class PaginatedSavesResponse(BaseModel):
    """Paginated response for user saves."""

    items: List[SaveWithContentResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class ContentByCategoryResponse(BaseModel):
    """Response for content grouped by category."""

    category: ContentCategory
    items: List[SaveWithContentResponse]
    total_count: int


class CategoryCountsResponse(BaseModel):
    """Response for category counts."""

    counts: Dict[str, int]
    total: int
