"""
ClusterMembership entity model.
Junction table linking UserContentSaves to Clusters.
"""
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class ClusterMembership(Base):
    """Links user content saves to clusters."""
    
    __tablename__ = "cluster_memberships"
    
    # Composite Primary Key
    cluster_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clusters.id", ondelete="CASCADE"),
        primary_key=True
    )
    user_save_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_content_saves.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # Relationships
    cluster = relationship("Cluster", back_populates="cluster_memberships")
    user_save = relationship("UserContentSave", back_populates="cluster_memberships")
