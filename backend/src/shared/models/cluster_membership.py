"""
ClusterMembership Entity Model

Junction table linking UserContentSaves to Clusters.

This is a many-to-many relationship table that tracks which
user saves belong to which clusters.

SAMPLE CLUSTER_MEMBERSHIP RECORD:
┌──────────────────────────────────────────────────────────────────────────────┐
│ cluster_id       │ 550e8400-e29b-41d4-a716-446655440000                      │
│ user_save_id     │ 660e8400-e29b-41d4-a716-446655440000                      │
└──────────────────────────────────────────────────────────────────────────────┘
"""

from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import Base


if TYPE_CHECKING:
    from src.shared.models.cluster import Cluster
    from src.shared.models.user_content_save import UserContentSave


class ClusterMembership(Base):
    """
    ClusterMembership model - links user content saves to clusters.

    This is a junction table for the many-to-many relationship between
    UserContentSave and Cluster entities.

    A single save can belong to multiple clusters (if clusters overlap),
    and a cluster contains many saves.

    Attributes:
        cluster_id: The cluster this membership belongs to (part of composite PK)
        user_save_id: The save that belongs to the cluster (part of composite PK)

    Relationships:
        cluster: The parent cluster
        user_save: The save that belongs to this cluster
    """

    __tablename__ = "cluster_memberships"

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPOSITE PRIMARY KEY
    # ═══════════════════════════════════════════════════════════════════════════

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clusters.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_save_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_content_saves.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════════════════

    cluster: Mapped["Cluster"] = relationship(
        "Cluster",
        back_populates="cluster_memberships",
    )

    user_save: Mapped["UserContentSave"] = relationship(
        "UserContentSave",
        back_populates="cluster_memberships",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<ClusterMembership(cluster_id={self.cluster_id}, save_id={self.user_save_id})>"
