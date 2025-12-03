"""
UserContentSave entity model.
User's personal save of a SharedContent item.
"""
from sqlalchemy import Column, ForeignKey, Text, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid as uuid_pkg

from .base import Base, TimestampMixin


class UserContentSave(Base, TimestampMixin):
    """User's personal save of shared content."""
    
    __tablename__ = "user_content_saves"
    
    # Identity
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    shared_content_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shared_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # User-Specific Data
    raw_share_text = Column(
        Text,
        comment="User's personal note when saving"
    )
    
    # User Actions (Optional MVP+)
    is_favorited = Column(
        Boolean,
        default=False,
        comment="User marked as favorite"
    )
    is_archived = Column(
        Boolean,
        default=False,
        comment="User archived this save"
    )
    last_viewed_at = Column(
        TIMESTAMP(timezone=True),
        comment="When user last viewed this"
    )
    
    # Relationships
    user = relationship("User", back_populates="saved_content")
    shared_content = relationship("SharedContent", back_populates="user_saves")
    cluster_memberships = relationship(
        "ClusterMembership",
        back_populates="user_save",
        cascade="all, delete-orphan"
    )
