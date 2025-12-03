"""
Content-related Pydantic schemas.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from ..models.enums import SourcePlatform, ItemStatus, CategoryHighLevel, IntentType


class SaveContentRequest(BaseModel):
    """Request to save new content."""
    url: str = Field(description="URL to save")
    raw_share_text: Optional[str] = Field(None, description="User's personal note")


class SharedContentResponse(BaseModel):
    """Response for shared content."""
    id: str
    url: str
    source_platform: SourcePlatform
    status: ItemStatus
    title: Optional[str] = None
    caption: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    category_high: Optional[CategoryHighLevel] = None
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


class SaveContentResponse(BaseModel):
    """Response after saving content."""
    save: UserContentSaveResponse
    content: SharedContentResponse
    message: str
