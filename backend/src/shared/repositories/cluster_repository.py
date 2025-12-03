"""
Cluster repository for data access.
"""
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.cluster import Cluster
from .base import BaseRepository


class ClusterRepository(BaseRepository[Cluster]):
    """Repository for Cluster entity."""
    
    def __init__(self, db: Session):
        super().__init__(Cluster, db)
    
    def get_user_clusters(self, user_id: str) -> List[Cluster]:
        """Get all clusters for a user."""
        stmt = select(Cluster).where(
            Cluster.user_id == user_id
        ).order_by(Cluster.updated_at.desc())
        return list(self.db.scalars(stmt).all())
