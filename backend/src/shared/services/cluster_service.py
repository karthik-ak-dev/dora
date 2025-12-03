"""
Cluster service.
Business logic for cluster operations.
"""
from typing import List
from sqlalchemy.orm import Session

from ..repositories.cluster_repository import ClusterRepository
from ..models.cluster import Cluster


class ClusterService:
    """Service for cluster-related business logic."""
    
    def __init__(self, db: Session):
        self.db = db
        self.cluster_repo = ClusterRepository(db)
    
    def get_user_clusters(self, user_id: str) -> List[Cluster]:
        """
        Get all clusters for a user.
        
        Args:
            user_id: User's ID
            
        Returns:
            List of user's clusters
        """
        return self.cluster_repo.get_user_clusters(user_id)
    
    def get_cluster_by_id(self, cluster_id: str, user_id: str) -> Cluster:
        """
        Get cluster by ID, ensuring it belongs to the user.
        
        Args:
            cluster_id: Cluster ID
            user_id: User's ID
            
        Returns:
            Cluster object
            
        Raises:
            ValueError: If cluster not found or doesn't belong to user
        """
        cluster = self.cluster_repo.get_by_id(cluster_id)
        
        if not cluster:
            raise ValueError("Cluster not found")
        
        if str(cluster.user_id) != user_id:
            raise ValueError("Cluster does not belong to user")
        
        return cluster
