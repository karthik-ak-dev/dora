"""
Cluster repository for data access.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func

from ..models.cluster import Cluster
from ..models.cluster_membership import ClusterMembership
from ..models.user_content_save import UserContentSave
from ..models.enums import ContentCategory
from .base import BaseRepository


class ClusterRepository(BaseRepository[Cluster]):
    """Repository for Cluster entity."""

    def __init__(self, db: Session):
        super().__init__(Cluster, db)

    def get_user_clusters(self, user_id: str) -> List[Cluster]:
        """Get all clusters for a user."""
        stmt = select(Cluster).where(Cluster.user_id == user_id).order_by(Cluster.updated_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_user_clusters_by_category(
        self, user_id: str, content_category: ContentCategory
    ) -> List[Cluster]:
        """
        Get user's clusters filtered by content category.

        Args:
            user_id: User's ID
            content_category: The category to filter by

        Returns:
            List of clusters in that category
        """
        stmt = (
            select(Cluster)
            .where(Cluster.user_id == user_id, Cluster.content_category == content_category)
            .order_by(Cluster.updated_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_user_clusters_with_counts(self, user_id: str) -> List[dict]:
        """
        Get all clusters for a user with item counts.

        Returns:
            List of dicts with cluster info and item_count
        """
        stmt = (
            select(Cluster, func.count(ClusterMembership.user_save_id).label("item_count"))
            .outerjoin(ClusterMembership, Cluster.id == ClusterMembership.cluster_id)
            .where(Cluster.user_id == user_id)
            .group_by(Cluster.id)
            .order_by(Cluster.updated_at.desc())
        )

        results = self.db.execute(stmt).all()
        return [{"cluster": row.Cluster, "item_count": row.item_count} for row in results]

    def get_cluster_with_items(self, cluster_id: str, user_id: str) -> Optional[dict]:
        """
        Get cluster with all its items.

        Args:
            cluster_id: Cluster ID
            user_id: User ID (for access control)

        Returns:
            Dict with cluster and items, or None if not found
        """
        cluster = self.get_by_id(cluster_id)
        if not cluster or str(cluster.user_id) != user_id:
            return None

        # Get items via ClusterMembership
        stmt = (
            select(UserContentSave)
            .join(ClusterMembership, UserContentSave.id == ClusterMembership.user_save_id)
            .where(ClusterMembership.cluster_id == cluster_id)
            .options(joinedload(UserContentSave.shared_content))
            .order_by(UserContentSave.created_at.desc())
        )
        items = list(self.db.scalars(stmt).unique().all())

        return {"cluster": cluster, "items": items, "item_count": len(items)}

    def create_cluster(
        self,
        user_id: str,
        content_category: ContentCategory,
        label: str,
        short_description: Optional[str] = None,
    ) -> Cluster:
        """
        Create a new cluster.

        Args:
            user_id: Owner user ID
            content_category: The category this cluster belongs to
            label: Human-readable cluster name
            short_description: Optional description

        Returns:
            Created Cluster
        """
        cluster = Cluster(
            user_id=user_id,
            content_category=content_category,
            label=label,
            short_description=short_description,
        )
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)
        return cluster

    def delete_user_clusters_by_category(
        self, user_id: str, content_category: ContentCategory
    ) -> int:
        """
        Delete all clusters for a user in a specific category.
        Used before re-clustering.

        Args:
            user_id: User ID
            content_category: Category to delete clusters for

        Returns:
            Number of clusters deleted
        """
        stmt = select(Cluster).where(
            Cluster.user_id == user_id, Cluster.content_category == content_category
        )
        clusters = list(self.db.scalars(stmt).all())
        count = len(clusters)

        for cluster in clusters:
            self.db.delete(cluster)

        self.db.commit()
        return count
