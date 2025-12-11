"""
Cluster entity model.
AI-generated group of semantically similar content for a user.
"""

from sqlalchemy import Column, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid as uuid_pkg

from .base import Base, TimestampMixin
from .enums import ContentCategory


class Cluster(Base, TimestampMixin):
    """
    AI-generated cluster of semantically similar content saves.

    CLUSTERING ARCHITECTURE:
    - Clusters are created WITHIN a content_category (e.g., all Food items grouped together).
    - The `content_category` field indicates which category this cluster belongs to.
    - All items in a cluster MUST have the same SharedContent.content_category.

    Example:
    - User has 5 Food saves, 3 Travel saves
    - Clustering groups the 5 Food items into "Cafe Hopping in Indiranagar" cluster
    - Clustering groups the 3 Travel items into "Goa Beach Vacation" cluster
    - Each cluster has a content_category matching its items (Food, Travel)

    The `label` and `short_description` are AI-generated for the specific grouping.
    """

    __tablename__ = "clusters"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Cluster Metadata
    content_category = Column(
        SQLEnum(ContentCategory),
        nullable=False,
        index=True,
        comment="The category this cluster belongs to. All items in cluster share this category.",
    )
    label = Column(
        Text,
        nullable=False,
        comment="AI-generated human-readable cluster name (e.g., 'Cafe Hopping in Indiranagar')",
    )
    short_description = Column(Text, comment="AI-generated one-sentence description of the cluster")

    # Relationships
    user = relationship("User", back_populates="clusters")
    cluster_memberships = relationship(
        "ClusterMembership", back_populates="cluster", cascade="all, delete-orphan"
    )
