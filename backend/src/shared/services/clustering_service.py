"""
Clustering service - AI clustering algorithms.

CLUSTERING ARCHITECTURE:
- Clustering happens WITHIN each content_category (not across categories)
- Content must be classified first (content_category assigned during AI processing)
- Clusters group semantically similar items within the same category
- Each cluster gets an AI-generated label and description

Flow:
1. Get user's saves for a specific category (content_category)
2. Fetch embeddings for those saves from vector DB
3. Run clustering algorithm (HDBSCAN/Agglomerative)
4. For each cluster: generate label using LLM
5. Save clusters and memberships to DB

Example:
- User has 5 Food saves, 3 Travel saves
- Clustering for Food: Groups into "Cafe Hopping in Indiranagar" (3 items) + "Recipe Ideas" (2 items)
- Clustering for Travel: Groups into "Goa Beach Vacation" (3 items)
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import logging

import numpy as np
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..models.enums import ContentCategory
from ..models.cluster import Cluster
from ..models.cluster_membership import ClusterMembership
from ..models.user_content_save import UserContentSave
from ..repositories.cluster_repository import ClusterRepository
from ..repositories.user_content_save_repository import UserContentSaveRepository


@dataclass
class ClusteringResult:
    """Result of clustering algorithm for a single cluster."""

    label_id: int  # Internal cluster label from algorithm (0, 1, 2, ...)
    save_ids: List[str]  # UserContentSave IDs in this cluster
    centroid_idx: int  # Index of item closest to centroid (for sampling)


@dataclass
class ClusterLabelResult:
    """Result of LLM labeling for a cluster."""

    label: str  # Human-readable name
    short_description: str  # One-sentence description


class ClusteringService:
    """
    Service for clustering user's saved content.

    Clustering is performed WITHIN each content_category:
    - All Food items are clustered together
    - All Travel items are clustered together
    - etc.

    This ensures items are properly categorized before being grouped.
    """

    # Minimum items needed to form a cluster
    MIN_CLUSTER_SIZE = 2

    # Minimum items needed before running clustering at all
    MIN_ITEMS_FOR_CLUSTERING = 3

    def __init__(self, db: Session):
        self.db = db
        self.cluster_repo = ClusterRepository(db)
        self.user_save_repo = UserContentSaveRepository(db)

    def cluster_user_category(
        self,
        user_id: str,
        content_category: ContentCategory,
        embeddings_map: Dict[str, List[float]],
    ) -> List[Cluster]:
        """
        Cluster a user's saves within a specific category.

        Args:
            user_id: User's ID
            content_category: The category to cluster
            embeddings_map: Map of shared_content_id to embedding vector

        Returns:
            List of created/updated Cluster objects
        """
        # 1. Get user's saves for this category
        saves = self.user_save_repo.get_user_saves_for_clustering(
            user_id=user_id, content_category=content_category
        )

        if len(saves) < self.MIN_ITEMS_FOR_CLUSTERING:
            # Not enough items to cluster
            return []

        # 2. Build embedding matrix for clustering
        save_ids = []
        embeddings = []

        for save in saves:
            content_id = str(save.shared_content_id)
            if content_id in embeddings_map:
                save_ids.append(str(save.id))
                embeddings.append(embeddings_map[content_id])

        if len(embeddings) < self.MIN_ITEMS_FOR_CLUSTERING:
            return []

        embedding_matrix = np.array(embeddings)

        # 3. Run clustering algorithm
        clustering_results = self._run_clustering(embedding_matrix, save_ids)

        if not clustering_results:
            return []

        # 4. Delete existing clusters for this category (re-clustering)
        self.cluster_repo.delete_user_clusters_by_category(user_id, content_category)

        # 5. Create new clusters
        created_clusters = []
        saves_by_id = {str(s.id): s for s in saves}

        for result in clustering_results:
            # Get sample items for labeling
            sample_saves = [saves_by_id[sid] for sid in result.save_ids[:5]]

            # Generate label (placeholder - actual LLM call would go here)
            label_result = self._generate_cluster_label(
                content_category=content_category, sample_saves=sample_saves
            )

            # Create cluster
            cluster = self.cluster_repo.create_cluster(
                user_id=user_id,
                content_category=content_category,
                label=label_result.label,
                short_description=label_result.short_description,
            )

            # Create memberships
            for save_id in result.save_ids:
                membership = ClusterMembership(cluster_id=cluster.id, user_save_id=save_id)
                self.db.add(membership)

            self.db.commit()
            created_clusters.append(cluster)

        return created_clusters

    def cluster_all_user_categories(
        self, user_id: str, embeddings_map: Dict[str, List[float]]
    ) -> Dict[ContentCategory, List[Cluster]]:
        """
        Cluster all categories for a user.

        Args:
            user_id: User's ID
            embeddings_map: Map of shared_content_id to embedding vector

        Returns:
            Dict mapping category to list of clusters created
        """
        results: Dict[ContentCategory, List[Cluster]] = {}

        # Get all saves grouped by category
        saves = self.user_save_repo.get_user_saves_with_content(user_id)

        # Group by category
        saves_by_category: Dict[ContentCategory, List[UserContentSave]] = {}
        for save in saves:
            category = save.shared_content.content_category
            if category:
                if category not in saves_by_category:
                    saves_by_category[category] = []
                saves_by_category[category].append(save)

        # Cluster each category
        for category in saves_by_category.keys():
            clusters = self.cluster_user_category(
                user_id=user_id, content_category=category, embeddings_map=embeddings_map
            )
            if clusters:
                results[category] = clusters

        return results

    def _run_clustering(
        self, embedding_matrix: np.ndarray, save_ids: List[str]
    ) -> List[ClusteringResult]:
        """
        Run clustering algorithm on embeddings.

        Uses Agglomerative Clustering with cosine distance.

        Args:
            embedding_matrix: NxD matrix of embeddings
            save_ids: List of save IDs corresponding to rows

        Returns:
            List of ClusteringResult objects
        """
        try:
            from sklearn.cluster import AgglomerativeClustering
            from sklearn.metrics.pairwise import cosine_distances
        except ImportError:
            # Fallback: treat all items as one cluster
            return [ClusteringResult(label_id=0, save_ids=save_ids, centroid_idx=0)]

        n_samples = len(save_ids)

        if n_samples < self.MIN_ITEMS_FOR_CLUSTERING:
            return []

        # Compute distance matrix
        distance_matrix = cosine_distances(embedding_matrix)

        # Determine number of clusters dynamically
        # Heuristic: sqrt(n) clusters, but at least 1 and at most n/2
        n_clusters = max(1, min(int(np.sqrt(n_samples)), n_samples // 2))

        # Run clustering
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters, metric="precomputed", linkage="average"
        )
        labels = clustering.fit_predict(distance_matrix)

        # Group results
        clusters_dict: Dict[int, List[Tuple[int, str]]] = {}
        for idx, (label, save_id) in enumerate(zip(labels, save_ids)):
            if label not in clusters_dict:
                clusters_dict[label] = []
            clusters_dict[label].append((idx, save_id))

        # Build results, filtering out too-small clusters
        results = []
        for label_id, items in clusters_dict.items():
            if len(items) >= self.MIN_CLUSTER_SIZE:
                indices = [i for i, _ in items]
                sids = [sid for _, sid in items]

                # Find centroid (item with minimum average distance to others)
                if len(indices) > 1:
                    sub_distances = distance_matrix[np.ix_(indices, indices)]
                    avg_distances = sub_distances.mean(axis=1)
                    centroid_local_idx = int(np.argmin(avg_distances))
                    centroid_idx = indices[centroid_local_idx]
                else:
                    centroid_idx = indices[0]

                results.append(
                    ClusteringResult(label_id=label_id, save_ids=sids, centroid_idx=centroid_idx)
                )

        return results

    def _generate_cluster_label(
        self, content_category: ContentCategory, sample_saves: List[UserContentSave]
    ) -> ClusterLabelResult:
        """
        Generate human-readable label for a cluster using LLM.

        Args:
            content_category: The category of items
            sample_saves: Sample items from the cluster

        Returns:
            ClusterLabelResult with label and description
        """
        # Build context from sample items
        items_context = []
        topics = []
        locations = []

        for save in sample_saves:
            content = save.shared_content
            item_info = {}

            if content.topic_main:
                item_info["topic"] = content.topic_main
                topics.append(content.topic_main)
            if content.title:
                item_info["title"] = content.title
            if content.locations:
                item_info["locations"] = content.locations[:2]
                locations.extend(content.locations)
            if content.subcategories:
                item_info["tags"] = content.subcategories[:3]

            if item_info:
                items_context.append(item_info)

        # Try LLM-based labeling first
        try:
            return self._generate_label_with_llm(
                content_category=content_category,
                items_context=items_context,
            )
        except Exception:
            # Fallback to rule-based labeling
            return self._generate_label_fallback(
                content_category=content_category,
                topics=topics,
                locations=locations,
            )

    def _generate_label_with_llm(
        self,
        content_category: ContentCategory,
        items_context: List[Dict],
    ) -> ClusterLabelResult:
        """
        Generate cluster label using LLM.

        Args:
            content_category: Category of items
            items_context: List of item context dicts

        Returns:
            ClusterLabelResult from LLM
        """
        from ..adapters.openai_adapter import get_openai_adapter
        import json

        openai = get_openai_adapter()

        system_prompt = """You are naming a cluster of saved content for a user.
Generate a short, catchy label (3-5 words) and a one-sentence description.

Output JSON with exactly these fields:
{
  "label": "Short catchy name",
  "description": "One sentence describing what this cluster contains."
}

Guidelines:
- Label should be specific and memorable
- Use location names if items share a location
- Use activity/theme if items share a common theme
- Avoid generic names like "Food Collection" - be specific"""

        user_prompt = f"""Category: {content_category.value}

Items in this cluster:
{json.dumps(items_context, indent=2)}

Generate a label and description for this cluster."""

        result = openai.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )

        return ClusterLabelResult(
            label=result.get("label", f"{content_category.value} Collection"),
            short_description=result.get(
                "description",
                f"A collection of {content_category.value.lower()} content.",
            ),
        )

    def _generate_label_fallback(
        self,
        content_category: ContentCategory,
        topics: List[str],
        locations: List[str],
    ) -> ClusterLabelResult:
        """
        Fallback rule-based label generation.

        Used when LLM is unavailable.
        """
        unique_locations = list(set(locations))[:3]

        if unique_locations:
            location_str = unique_locations[0]
            label = f"{content_category.value} in {location_str}"
            description = (
                f"Saved {content_category.value.lower()} content related to {location_str}."
            )
        elif topics:
            label = f"{content_category.value} Collection"
            description = f"A collection of {content_category.value.lower()} content."
        else:
            label = f"{content_category.value} Saves"
            description = f"Saved {content_category.value.lower()} items."

        return ClusterLabelResult(label=label, short_description=description)
