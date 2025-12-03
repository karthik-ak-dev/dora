"""
Cluster entity model.
AI-generated group of semantically similar content for a user.
"""
from sqlalchemy import Column, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid as uuid_pkg

from .base import Base, TimestampMixin
from .enums import ClusterType


class Cluster(Base, TimestampMixin):
    """AI-generated cluster of similar content saves."""
    
    __tablename__ = "clusters"
    
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
    
    # Cluster Metadata
    label = Column(
        Text,
        nullable=False,
        comment="Human-readable cluster name"
    )
    cluster_type = Column(SQLEnum(ClusterType))
    short_description = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="clusters")
    cluster_memberships = relationship(
        "ClusterMembership",
        back_populates="cluster",
        cascade="all, delete-orphan"
    )
