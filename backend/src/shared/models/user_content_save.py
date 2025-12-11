"""
UserContentSave Entity Model

User's personal save of a SharedContent item.

This represents the many-to-many relationship between Users and SharedContent,
with additional user-specific metadata like notes, favorites, and archive status.

SAMPLE USER_CONTENT_SAVE RECORD:
┌──────────────────────────────────────────────────────────────────────────────┐
│ id               │ 550e8400-e29b-41d4-a716-446655440000                      │
│ user_id          │ 660e8400-e29b-41d4-a716-446655440000                      │
│ shared_content_id│ 770e8400-e29b-41d4-a716-446655440000                      │
│ raw_share_text   │ "Great recipe to try this weekend!"                       │
│ is_favorited     │ true                                                       │
│ is_archived      │ false                                                      │
└──────────────────────────────────────────────────────────────────────────────┘
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import ForeignKey, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import Base, TimestampMixin


if TYPE_CHECKING:
    from src.shared.models.user import User
    from src.shared.models.shared_content import SharedContent
    from src.shared.models.cluster_membership import ClusterMembership


class UserContentSave(Base, TimestampMixin):
    """
    UserContentSave model - user's personal save of shared content.

    Represents the user's relationship to a piece of content, including
    their personal notes and organization preferences.

    Attributes:
        id: Unique identifier (UUID v4)
        user_id: The user who saved this content
        shared_content_id: The content that was saved
        raw_share_text: User's personal note when saving
        is_favorited: Whether user marked as favorite
        is_archived: Whether user archived this save
        last_viewed_at: When user last viewed this content

    Relationships:
        user: The user who made this save
        shared_content: The content that was saved
        cluster_memberships: Clusters this save belongs to
    """

    __tablename__ = "user_content_saves"

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY KEY
    # ═══════════════════════════════════════════════════════════════════════════

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # FOREIGN KEYS
    # ═══════════════════════════════════════════════════════════════════════════

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    shared_content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shared_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # USER-SPECIFIC DATA
    # ═══════════════════════════════════════════════════════════════════════════

    # User's personal note when saving
    raw_share_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # USER ACTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    # User marked as favorite
    is_favorited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # User archived this save
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # When user last viewed this
    last_viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════════════════

    user: Mapped["User"] = relationship(
        "User",
        back_populates="saved_content",
    )

    shared_content: Mapped["SharedContent"] = relationship(
        "SharedContent",
        back_populates="user_saves",
    )

    cluster_memberships: Mapped[list["ClusterMembership"]] = relationship(
        "ClusterMembership",
        back_populates="user_save",
        cascade="all, delete-orphan",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<UserContentSave(id={self.id}, user_id={self.user_id})>"
