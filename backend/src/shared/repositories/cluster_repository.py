"""
Cluster Repository

Database operations for AI-generated content clusters.

Common Operations:
==================
- get_user_clusters()           → Get all clusters for a user
- get_user_clusters_by_category() → Filter by content category
- get_user_clusters_with_counts() → Include item counts
- get_cluster_with_items()       → Get cluster with all its items
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.shared.repositories.base import BaseRepository
from src.shared.models.cluster import Cluster
from src.shared.models.cluster_membership import ClusterMembership
from src.shared.models.user_content_save import UserContentSave
from src.shared.models.enums import ContentCategory


class ClusterRepository(BaseRepository[Cluster]):
    """
    Repository for Cluster database operations.

    Handles cluster queries with item counts and membership lookups.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize ClusterRepository.

        Args:
            session: Async database session
        """
        super().__init__(Cluster, session)

    # ═══════════════════════════════════════════════════════════════════════════
    # READ OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_user_clusters(self, user_id: UUID) -> List[Cluster]:
        """
        Get all clusters for a user.

        Args:
            user_id: User's UUID

        Returns:
            List of Cluster ordered by most recently updated
        """
        result = await self.session.execute(
            select(Cluster).where(Cluster.user_id == user_id).order_by(Cluster.updated_at.desc())
        )
        return list(result.scalars().all())

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
        result = await self.session.execute(
            select(Cluster)
            .where(
                Cluster.user_id == user_id,
                Cluster.content_category == content_category,
            )
            .order_by(Cluster.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_user_clusters_with_counts(
        self,
        user_id: UUID,
    ) -> List[dict]:
        """
        Get all clusters for a user with item counts.

        Returns clusters with the count of items in each.

        Args:
            user_id: User's UUID

        Returns:
            List of dicts with cluster and item_count
        """
        result = await self.session.execute(
            select(
                Cluster,
                func.count(ClusterMembership.user_save_id).label("item_count"),
            )
            .outerjoin(ClusterMembership, Cluster.id == ClusterMembership.cluster_id)
            .where(Cluster.user_id == user_id)
            .group_by(Cluster.id)
            .order_by(Cluster.updated_at.desc())
        )

        rows = result.all()
        return [{"cluster": row.Cluster, "item_count": row.item_count} for row in rows]

    async def get_cluster_with_items(
        self,
        cluster_id: UUID,
        user_id: UUID,
    ) -> Optional[dict]:
        """
        Get cluster with all its items.

        Verifies user ownership before returning.

        Args:
            cluster_id: Cluster UUID
            user_id: User UUID (for access control)

        Returns:
            Dict with cluster, items, and item_count, or None if not found
        """
        cluster = await self.get(cluster_id)
        if not cluster or cluster.user_id != user_id:
            return None

        # Get items via ClusterMembership
        result = await self.session.execute(
            select(UserContentSave)
            .join(ClusterMembership, UserContentSave.id == ClusterMembership.user_save_id)
            .where(ClusterMembership.cluster_id == cluster_id)
            .options(selectinload(UserContentSave.shared_content))
            .order_by(UserContentSave.created_at.desc())
        )
        items = list(result.scalars().unique().all())

        return {
            "cluster": cluster,
            "items": items,
            "item_count": len(items),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # CREATE/DELETE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

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
        return await self.create(
            user_id=user_id,
            content_category=content_category,
            label=label,
            short_description=short_description,
        )

    async def delete_user_clusters_by_category(
        self,
        user_id: UUID,
        content_category: ContentCategory,
    ) -> int:
        """
        Delete all clusters for a user in a specific category.

        Used before re-clustering.

        Args:
            user_id: User UUID
            content_category: Category to delete clusters for

        Returns:
            Number of clusters deleted
        """
        result = await self.session.execute(
            select(Cluster).where(
                Cluster.user_id == user_id,
                Cluster.content_category == content_category,
            )
        )
        clusters = list(result.scalars().all())
        count = len(clusters)

        for cluster in clusters:
            await self.session.delete(cluster)

        await self.session.flush()
        return count
