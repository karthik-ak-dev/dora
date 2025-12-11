"""
Cluster service.
Business logic for cluster operations.

CLUSTERING ARCHITECTURE:
- Clusters are created WITHIN a content_category (not across categories)
- Each cluster has a content_category field matching its items
- All items in a cluster have the same SharedContent.content_category

Use ClusteringService for the actual clustering algorithm.
Use this service for CRUD operations on clusters.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from ..repositories.cluster_repository import ClusterRepository
from ..models.cluster import Cluster
from ..models.enums import ContentCategory
from ..schemas.cluster import ClusterResponse, ClusterWithItemsResponse, ClusterItemResponse


class ClusterService:
    """Service for cluster-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.cluster_repo = ClusterRepository(db)

    def get_user_clusters(self, user_id: str) -> List[dict]:
        """
        Get all clusters for a user with item counts.

        Args:
            user_id: User's ID

        Returns:
            List of dicts with cluster and item_count
        """
        return self.cluster_repo.get_user_clusters_with_counts(user_id)

    def get_user_clusters_by_category(
        self, user_id: str, content_category: ContentCategory
    ) -> List[Cluster]:
        """
        Get user's clusters filtered by content category.

        Args:
            user_id: User's ID
            content_category: Category to filter by

        Returns:
            List of clusters in that category
        """
        return self.cluster_repo.get_user_clusters_by_category(
            user_id=user_id, content_category=content_category
        )

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

    def get_cluster_with_items(self, cluster_id: str, user_id: str) -> Optional[dict]:
        """
        Get cluster with all its items.

        Args:
            cluster_id: Cluster ID
            user_id: User ID (for access control)

        Returns:
            Dict with cluster, items, and item_count

        Raises:
            ValueError: If cluster not found or doesn't belong to user
        """
        result = self.cluster_repo.get_cluster_with_items(cluster_id, user_id)

        if not result:
            raise ValueError("Cluster not found or access denied")

        return result

    def get_clusters_grouped_by_category(self, user_id: str) -> Dict[ContentCategory, List[dict]]:
        """
        Get all user's clusters grouped by content category.

        Args:
            user_id: User's ID

        Returns:
            Dict mapping category to list of cluster dicts
        """
        clusters_with_counts = self.cluster_repo.get_user_clusters_with_counts(user_id)

        grouped: Dict[ContentCategory, List[dict]] = {}
        for item in clusters_with_counts:
            cluster = item["cluster"]
            category = cluster.content_category

            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)

        return grouped

    def get_category_summary(self, user_id: str) -> List[dict]:
        """
        Get summary of clusters per category for a user.

        Returns:
            List of dicts with category, cluster_count, total_items
        """
        grouped = self.get_clusters_grouped_by_category(user_id)

        summary = []
        for category, clusters in grouped.items():
            total_items = sum(c["item_count"] for c in clusters)
            summary.append(
                {"category": category, "cluster_count": len(clusters), "total_items": total_items}
            )

        # Sort by total_items descending
        summary.sort(key=lambda x: x["total_items"], reverse=True)
        return summary
