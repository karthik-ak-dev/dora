"""
SharedContent Entity Model

Universal content metadata shared across all users.
When content is saved, it's processed once and shared across all users who save it.

CLASSIFICATION ARCHITECTURE:
- `content_category`: The AUTHORITATIVE classification assigned during AI processing.
  This is a strong, tight classification into one of the defined categories.
  NOT dependent on user context or clustering.

- Content is classified ONCE during processing and this classification is immutable.
- Clusters are then created WITHIN each category for finer user-level groupings.

Example Flow:
1. User saves URL → SharedContent created (content_category=None, status=PENDING)
2. AI Processing → content_category="Food" assigned (strong classification)
3. Clustering Job → Groups user's Food saves into clusters like "Cafe Hopping"

SAMPLE SHARED_CONTENT RECORD:
┌──────────────────────────────────────────────────────────────────────────────┐
│ id               │ 550e8400-e29b-41d4-a716-446655440000                      │
│ source_platform  │ INSTAGRAM                                                  │
│ url              │ "https://instagram.com/p/ABC123"                          │
│ url_hash         │ "a1b2c3d4..."                                              │
│ status           │ READY                                                      │
│ content_category │ FOOD                                                       │
│ title            │ "Amazing Pasta Recipe"                                     │
│ save_count       │ 42                                                         │
└──────────────────────────────────────────────────────────────────────────────┘
"""

from typing import TYPE_CHECKING, Any, Optional
import uuid

from sqlalchemy import String, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import Base, TimestampMixin
from src.shared.models.enums import SourcePlatform, ItemStatus, ContentCategory, IntentType


if TYPE_CHECKING:
    from src.shared.models.user_content_save import UserContentSave
    from src.shared.models.processing_job import ProcessingJob


class SharedContent(Base, TimestampMixin):
    """
    SharedContent model - universal content metadata processed once, shared across users.

    Attributes:
        id: Unique identifier (UUID v4)
        source_platform: Platform the content came from (Instagram, YouTube, etc.)
        url: Original URL of the content
        url_hash: SHA256 hash for deduplication
        status: Processing status (PENDING, READY, FAILED)
        content_category: AI-classified category (Travel, Food, Tech, etc.)

    Relationships:
        user_saves: All user saves referencing this content
        processing_jobs: Processing job history
    """

    __tablename__ = "shared_content"

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY KEY
    # ═══════════════════════════════════════════════════════════════════════════

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # SOURCE INFORMATION
    # ═══════════════════════════════════════════════════════════════════════════

    source_platform: Mapped[SourcePlatform] = mapped_column(
        SQLEnum(SourcePlatform),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # SHA256 hash of normalized URL for deduplication
    url_hash: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
        index=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # PROCESSING STATUS
    # ═══════════════════════════════════════════════════════════════════════════

    status: Mapped[ItemStatus] = mapped_column(
        SQLEnum(ItemStatus),
        nullable=False,
        default=ItemStatus.PENDING,
        index=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY CLASSIFICATION
    # ═══════════════════════════════════════════════════════════════════════════

    # Authoritative category - assigned during AI processing, immutable after READY
    content_category: Mapped[Optional[ContentCategory]] = mapped_column(
        SQLEnum(ContentCategory),
        nullable=True,
        index=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # BASIC METADATA
    # ═══════════════════════════════════════════════════════════════════════════

    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # AI UNDERSTANDING - TEXT ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic_main: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Fine-grained tags within the content_category
    subcategories: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    locations: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    entities: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    intent: Mapped[Optional[IntentType]] = mapped_column(
        SQLEnum(IntentType),
        nullable=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # AI UNDERSTANDING - VISUAL ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    visual_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    visual_tags: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # VECTOR DATABASE REFERENCE
    # ═══════════════════════════════════════════════════════════════════════════

    embedding_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════

    # Number of users who saved this content
    save_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════════════════

    user_saves: Mapped[list["UserContentSave"]] = relationship(
        "UserContentSave",
        back_populates="shared_content",
        cascade="all, delete-orphan",
    )

    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        "ProcessingJob",
        back_populates="shared_content",
        cascade="all, delete-orphan",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<SharedContent(id={self.id}, status={self.status}, category={self.content_category})>"
        )
