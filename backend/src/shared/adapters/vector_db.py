"""
Vector database adapter - Qdrant client.

Provides:
- Vector storage and retrieval
- Similarity search
- Filtering by metadata (content_category, etc.)
"""

import functools
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from ...config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchResult:
    """Result of a vector similarity search."""

    id: str
    score: float
    payload: Dict[str, Any]


class VectorDBAdapter:
    """
    Adapter for Qdrant vector database operations.

    Handles:
    - Vector upsert (insert/update)
    - Similarity search with filtering
    - Vector deletion
    """

    COLLECTION_NAME = "shared_content"
    VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small dimensions

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Qdrant adapter.

        Args:
            url: Qdrant server URL. If not provided, uses settings.
            api_key: Qdrant API key for cloud. If not provided, uses settings.
        """
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or getattr(settings, "QDRANT_API_KEY", None)
        self._client: Optional[QdrantClient] = None

    @property
    def client(self) -> QdrantClient:
        """Lazy-loaded Qdrant client."""
        if self._client is None:
            if self.api_key:
                self._client = QdrantClient(url=self.url, api_key=self.api_key)
            else:
                self._client = QdrantClient(url=self.url)
        return self._client

    def ensure_collection(self) -> None:
        """
        Ensure the collection exists with proper configuration.
        Creates it if it doesn't exist.
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.COLLECTION_NAME not in collection_names:
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=qdrant_models.VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )
                logger.info("Created collection: %s", self.COLLECTION_NAME)

        except UnexpectedResponse as e:
            logger.error("Failed to ensure collection: %s", e)
            raise

    def upsert(
        self,
        point_id: str,
        vector: List[float],
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Insert or update a vector.

        Args:
            point_id: Unique identifier (typically shared_content.id)
            vector: Embedding vector
            payload: Metadata to store with vector
        """
        try:
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    qdrant_models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload or {},
                    )
                ],
            )
        except UnexpectedResponse as e:
            logger.error("Failed to upsert vector %s: %s", point_id, e)
            raise

    def upsert_batch(
        self,
        points: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> None:
        """
        Batch insert/update vectors.

        Args:
            points: List of dicts with 'id', 'vector', 'payload' keys
            batch_size: Number of points per batch
        """
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]

            try:
                self.client.upsert(
                    collection_name=self.COLLECTION_NAME,
                    points=[
                        qdrant_models.PointStruct(
                            id=p["id"],
                            vector=p["vector"],
                            payload=p.get("payload", {}),
                        )
                        for p in batch
                    ],
                )
            except UnexpectedResponse as e:
                logger.error("Batch upsert failed at index %d: %s", i, e)
                raise

    def search(
        self,
        vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors.

        Args:
            vector: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1 for cosine)
            filter_conditions: Qdrant filter conditions

        Returns:
            List of VectorSearchResult ordered by similarity
        """
        query_filter = None
        if filter_conditions:
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key=key,
                        match=qdrant_models.MatchValue(value=value),
                    )
                    for key, value in filter_conditions.items()
                ]
            )

        try:
            results = self.client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )

            return [
                VectorSearchResult(
                    id=str(r.id),
                    score=r.score,
                    payload=r.payload or {},
                )
                for r in results.points
            ]

        except UnexpectedResponse as e:
            logger.error("Vector search failed: %s", e)
            raise

    def search_by_category(
        self,
        vector: List[float],
        content_category: str,
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors within a specific category.

        Args:
            vector: Query vector
            content_category: Category to filter by
            limit: Maximum results
            score_threshold: Minimum similarity

        Returns:
            List of VectorSearchResult
        """
        return self.search(
            vector=vector,
            limit=limit,
            score_threshold=score_threshold,
            filter_conditions={"content_category": content_category},
        )

    def get_vectors(self, ids: List[str]) -> Dict[str, List[float]]:
        """
        Retrieve vectors by their IDs.

        Args:
            ids: List of vector IDs

        Returns:
            Dict mapping ID to vector
        """
        try:
            results = self.client.retrieve(
                collection_name=self.COLLECTION_NAME,
                ids=ids,
                with_vectors=True,
            )

            return {str(r.id): r.vector for r in results if r.vector}

        except UnexpectedResponse as e:
            logger.error("Failed to retrieve vectors: %s", e)
            raise

    def delete(self, ids: List[str]) -> None:
        """
        Delete vectors by IDs.

        Args:
            ids: List of vector IDs to delete
        """
        try:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=qdrant_models.PointIdsList(points=ids),
            )
        except UnexpectedResponse as e:
            logger.error("Failed to delete vectors: %s", e)
            raise

    def count(self, filter_conditions: Optional[Dict[str, Any]] = None) -> int:
        """
        Count vectors in collection.

        Args:
            filter_conditions: Optional filter

        Returns:
            Number of vectors
        """
        try:
            if filter_conditions:
                query_filter = qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key=key,
                            match=qdrant_models.MatchValue(value=value),
                        )
                        for key, value in filter_conditions.items()
                    ]
                )
                result = self.client.count(
                    collection_name=self.COLLECTION_NAME,
                    count_filter=query_filter,
                )
            else:
                result = self.client.count(collection_name=self.COLLECTION_NAME)

            return result.count

        except UnexpectedResponse as e:
            logger.error("Failed to count vectors: %s", e)
            raise


@functools.lru_cache(maxsize=1)
def get_vector_db_adapter() -> VectorDBAdapter:
    """Get or create VectorDB adapter singleton."""
    return VectorDBAdapter()
