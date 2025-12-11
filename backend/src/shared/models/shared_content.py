"""
SharedContent entity model.
Universal content metadata shared across all users.
"""

from sqlalchemy import Column, String, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid as uuid_pkg

from .base import Base, TimestampMixin
from .enums import SourcePlatform, ItemStatus, ContentCategory, IntentType


class SharedContent(Base, TimestampMixin):
    """
    Universal content metadata (processed once, shared across users).

    CLASSIFICATION ARCHITECTURE:
    - `content_category`: The AUTHORITATIVE classification assigned during AI processing.
      This is a strong, tight classification into one of the defined categories.
      NOT dependent on user context or clustering.

    - Content is classified ONCE during processing and this classification is immutable.
    - Clusters are then created WITHIN each category for finer user-level groupings.

    Example Flow:
    1. User saves URL → SharedContent created (content_category=None, status=PENDING)
    2. AI Processing → content_category="Food" assigned (strong classification)
    3. Clustering Job → Groups user's Food saves into clusters like "Cafe Hopping in Indiranagar"
    """

    __tablename__ = "shared_content"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)

    # Source Information
    source_platform = Column(SQLEnum(SourcePlatform), nullable=False)
    url = Column(Text, nullable=False)
    url_hash = Column(
        Text,
        unique=True,
        nullable=False,
        index=True,
        comment="SHA256 hash of normalized URL for deduplication",
    )

    # Processing Status
    status = Column(SQLEnum(ItemStatus), nullable=False, default=ItemStatus.PENDING, index=True)

    # === PRIMARY CLASSIFICATION ===
    # This is the authoritative category - assigned during AI processing
    content_category = Column(
        SQLEnum(ContentCategory),
        nullable=True,
        index=True,
        comment="Primary content category (Travel, Food, Tech, etc.). Assigned during AI processing. Immutable after READY status.",
    )

    # Basic Metadata
    title = Column(Text)
    caption = Column(Text)
    description = Column(Text)
    thumbnail_url = Column(Text)
    duration_seconds = Column(Integer)

    # AI Understanding - Text Analysis
    content_text = Column(Text)
    topic_main = Column(Text)
    subcategories = Column(JSONB, comment="Fine-grained tags within the content_category")
    locations = Column(JSONB)
    entities = Column(JSONB)
    intent = Column(SQLEnum(IntentType))

    # AI Understanding - Visual Analysis
    visual_description = Column(Text)
    visual_tags = Column(JSONB)

    # Vector Database Reference
    embedding_id = Column(Text)

    # Statistics
    save_count = Column(Integer, default=0, comment="Number of users who saved this content")

    # Relationships
    user_saves = relationship(
        "UserContentSave", back_populates="shared_content", cascade="all, delete-orphan"
    )
    processing_jobs = relationship(
        "ProcessingJob", back_populates="shared_content", cascade="all, delete-orphan"
    )
