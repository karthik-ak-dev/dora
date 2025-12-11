"""
Cluster Service

Business logic for content cluster operations.

Clusters are AI-generated groups of semantically similar content
that belong to the same content category.

Usage:
======
    from src.shared.services.cluster_service import ClusterService

    service = ClusterService(db)
    clusters = await service.get_user_clusters(user_id)
"""

from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.cluster import Cluster
from src.shared.models.user_content_save import UserContentSave
from src.shared.models.enums import ContentCategory
from src.shared.repositories.cluster_repository import ClusterRepository
from src.shared.core.exceptions import NotFoundError


class ClusterService:
    """
    Service for cluster-related business logic.

    Handles:
    - Retrieving user's clusters
    - Getting cluster details with items
    - Category-based filtering
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize ClusterService.

        Args:
            session: Async database session
        """
        self.session = session
        self.repo = ClusterRepository(session)

    async def get_user_clusters(self, user_id: UUID) -> List[Cluster]:
        """
        Get all clusters for a user.

        Args:
            user_id: User's UUID

        Returns:
            List of Cluster ordered by most recently updated
        """
        return await self.repo.get_user_clusters(user_id)

    async def get_user_clusters_by_category(
        self,
        user_id: UUID,
        content_category: ContentCategory,
    ) -> List[Cluster]:
        """
        Get user's clusters filtered by content category.

        Args:
            user_id: User's UUID
            content_category: Category to filter by

        Returns:
            List of Cluster in that category
        """
        return await self.repo.get_user_clusters_by_category(user_id, content_category)

    async def get_user_clusters_with_counts(
        self,
        user_id: UUID,
    ) -> List[Dict]:
        """
        Get all clusters for a user with item counts.

        Args:
            user_id: User's UUID

        Returns:
            List of dicts with cluster and item_count keys
        """
        return await self.repo.get_user_clusters_with_counts(user_id)

    async def get_cluster_by_id(
        self,
        cluster_id: UUID,
        user_id: UUID,
    ) -> Optional[Cluster]:
        """
        Get a cluster by ID, ensuring it belongs to the user.

        Args:
            cluster_id: Cluster UUID
            user_id: User UUID (for access control)

        Returns:
            Cluster if found and belongs to user, None otherwise
        """
        cluster = await self.repo.get(cluster_id)
        if cluster and cluster.user_id == user_id:
            return cluster
        return None

    async def get_cluster_with_items(
        self,
        cluster_id: UUID,
        user_id: UUID,
    ) -> Optional[Dict]:
        """
        Get cluster with all its items.

        Args:
            cluster_id: Cluster UUID
            user_id: User UUID (for access control)

        Returns:
            Dict with cluster, items, and item_count, or None if not found

        Example:
            result = await service.get_cluster_with_items(cluster_id, user_id)
            if result:
                print(f"Cluster: {result['cluster'].label}")
                print(f"Items: {result['item_count']}")
        """
        return await self.repo.get_cluster_with_items(cluster_id, user_id)

    async def create_cluster(
        self,
        user_id: UUID,
        content_category: ContentCategory,
        label: str,
        short_description: Optional[str] = None,
    ) -> Cluster:
        """
        Create a new cluster.

        Args:
            user_id: Owner user UUID
            content_category: Category this cluster belongs to
            label: Human-readable cluster name
            short_description: Optional description

        Returns:
            Created Cluster
        """
        return await self.repo.create_cluster(
            user_id=user_id,
            content_category=content_category,
            label=label,
            short_description=short_description,
        )

    async def delete_cluster(
        self,
        cluster_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete a cluster.

        Args:
            cluster_id: Cluster UUID
            user_id: User UUID (for access control)

        Returns:
            True if deleted, False if not found or not owned by user
        """
        cluster = await self.get_cluster_by_id(cluster_id, user_id)
        if not cluster:
            return False

        await self.repo.delete(cluster_id)
        return True

    async def delete_user_clusters_by_category(
        self,
        user_id: UUID,
        content_category: ContentCategory,
    ) -> int:
        """
        Delete all clusters for a user in a specific category.

        Used before re-clustering to remove old clusters.

        Args:
            user_id: User UUID
            content_category: Category to delete clusters for

        Returns:
            Number of clusters deleted
        """
        return await self.repo.delete_user_clusters_by_category(user_id, content_category)
