"""
Cluster Entity Model

AI-generated group of semantically similar content for a user.

CLUSTERING ARCHITECTURE:
- Clusters are created WITHIN a content_category (e.g., all Food items grouped together).
- The `content_category` field indicates which category this cluster belongs to.
- All items in a cluster MUST have the same SharedContent.content_category.

Example:
- User has 5 Food saves, 3 Travel saves
- Clustering groups the 5 Food items into "Cafe Hopping in Indiranagar" cluster
- Clustering groups the 3 Travel items into "Goa Beach Vacation" cluster
- Each cluster has a content_category matching its items (Food, Travel)

SAMPLE CLUSTER RECORD:
┌──────────────────────────────────────────────────────────────────────────────┐
│ id               │ 550e8400-e29b-41d4-a716-446655440000                      │
│ user_id          │ 660e8400-e29b-41d4-a716-446655440000                      │
│ content_category │ FOOD                                                       │
│ label            │ "Cafe Hopping in Indiranagar"                             │
│ short_description│ "Cozy cafes and brunch spots in Indiranagar"              │
└──────────────────────────────────────────────────────────────────────────────┘
"""

from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import Base, TimestampMixin
from src.shared.models.enums import ContentCategory


if TYPE_CHECKING:
    from src.shared.models.user import User
    from src.shared.models.cluster_membership import ClusterMembership


class Cluster(Base, TimestampMixin):
    """
    Cluster model - AI-generated group of semantically similar content saves.

    The `label` and `short_description` are AI-generated for the specific grouping.

    Attributes:
        id: Unique identifier (UUID v4)
        user_id: Owner user ID
        content_category: The category this cluster belongs to
        label: AI-generated human-readable name
        short_description: AI-generated one-sentence description

    Relationships:
        user: The user who owns this cluster
        cluster_memberships: Items belonging to this cluster
    """

    __tablename__ = "clusters"

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

    # ═══════════════════════════════════════════════════════════════════════════
    # CLUSTER METADATA
    # ═══════════════════════════════════════════════════════════════════════════

    # The category this cluster belongs to - all items in cluster share this
    content_category: Mapped[ContentCategory] = mapped_column(
        SQLEnum(ContentCategory),
        nullable=False,
        index=True,
    )

    # AI-generated human-readable cluster name
    label: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # AI-generated one-sentence description
    short_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════════════════

    user: Mapped["User"] = relationship(
        "User",
        back_populates="clusters",
    )

    cluster_memberships: Mapped[list["ClusterMembership"]] = relationship(
        "ClusterMembership",
        back_populates="cluster",
        cascade="all, delete-orphan",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<Cluster(id={self.id}, label={self.label}, category={self.content_category})>"
