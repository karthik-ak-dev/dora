"""
Clustering pipeline.
Orchestrates user clustering workflow.

CLUSTERING ARCHITECTURE:
Clustering happens WITHIN each content_category (not across categories):
1. Content is first classified (content_category assigned by ContentPipeline)
2. Clustering groups items WITHIN the same category
3. Each cluster has a content_category matching its items

Flow:
1. Get user's ready saves (status=READY, has embedding)
2. Group saves by content_category
3. For each category with enough items:
   a. Fetch embeddings from vector DB
   b. Run clustering algorithm
   c. Generate cluster labels via LLM
   d. Save clusters and memberships

Example:
- User has: 5 Food saves, 3 Travel saves, 1 Tech save
- Food (5 items) → 2 clusters: "Cafe Hopping in Indiranagar" (3), "Recipe Ideas" (2)
- Travel (3 items) → 1 cluster: "Goa Beach Vacation" (3)
- Tech (1 item) → No clustering (below minimum threshold)
"""

from typing import Dict, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ...shared.models.enums import ContentCategory
from ...shared.services.clustering_service import ClusteringService
from ...shared.repositories.user_content_save_repository import UserContentSaveRepository


@dataclass
class ClusteringPipelineResult:
    """Result of clustering pipeline for a user."""

    success: bool
    user_id: str
    clusters_created: Dict[ContentCategory, int]
    error_message: Optional[str] = None


class ClusteringPipeline:
    """
    Pipeline for clustering a user's saved content.

    Clustering is performed per-category:
    - All Food items are clustered together
    - All Travel items are clustered together
    - etc.

    This ensures items are properly categorized (via content_category)
    before being grouped into fine-grained clusters.
    """

    def __init__(self, db: Session):
        self.db = db
        self.clustering_service = ClusteringService(db)
        self.user_save_repo = UserContentSaveRepository(db)

    def process_user(self, user_id: str, embeddings_fetcher: callable) -> ClusteringPipelineResult:
        """
        Run clustering for a user across all categories.

        Args:
            user_id: User's ID
            embeddings_fetcher: Function that takes list of content IDs
                               and returns dict of content_id -> embedding

        Returns:
            ClusteringPipelineResult with counts per category
        """
        try:
            # 1. Get all user's ready saves
            saves = self.user_save_repo.get_user_saves_with_content(user_id)

            # Filter to only READY content with embeddings
            ready_saves = [
                s
                for s in saves
                if s.shared_content.status.value == "READY"
                and s.shared_content.embedding_id
                and s.shared_content.content_category
            ]

            if not ready_saves:
                return ClusteringPipelineResult(success=True, user_id=user_id, clusters_created={})

            # 2. Fetch all embeddings
            content_ids = [str(s.shared_content_id) for s in ready_saves]
            embeddings_map = embeddings_fetcher(content_ids)

            # 3. Run clustering for all categories
            results = self.clustering_service.cluster_all_user_categories(
                user_id=user_id, embeddings_map=embeddings_map
            )

            # 4. Build result
            clusters_created = {category: len(clusters) for category, clusters in results.items()}

            return ClusteringPipelineResult(
                success=True, user_id=user_id, clusters_created=clusters_created
            )

        except Exception as e:
            return ClusteringPipelineResult(
                success=False, user_id=user_id, clusters_created={}, error_message=str(e)
            )

    def process_user_category(
        self, user_id: str, content_category: ContentCategory, embeddings_fetcher: callable
    ) -> ClusteringPipelineResult:
        """
        Run clustering for a specific category only.

        Useful when:
        - User saves new items in a category
        - Re-clustering a specific category

        Args:
            user_id: User's ID
            content_category: Category to cluster
            embeddings_fetcher: Function to fetch embeddings

        Returns:
            ClusteringPipelineResult
        """
        try:
            # Get saves for this category
            saves = self.user_save_repo.get_user_saves_for_clustering(
                user_id=user_id, content_category=content_category
            )

            if not saves:
                return ClusteringPipelineResult(success=True, user_id=user_id, clusters_created={})

            # Fetch embeddings
            content_ids = [str(s.shared_content_id) for s in saves]
            embeddings_map = embeddings_fetcher(content_ids)

            # Run clustering
            clusters = self.clustering_service.cluster_user_category(
                user_id=user_id, content_category=content_category, embeddings_map=embeddings_map
            )

            return ClusteringPipelineResult(
                success=True,
                user_id=user_id,
                clusters_created={content_category: len(clusters)} if clusters else {},
            )

        except Exception as e:
            return ClusteringPipelineResult(
                success=False, user_id=user_id, clusters_created={}, error_message=str(e)
            )
