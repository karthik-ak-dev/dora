"""
Embedding service - Vector embedding operations.

Provides:
- Embedding generation for content
- Vector storage in Qdrant
- Similarity search operations
"""

import functools
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..adapters.openai_adapter import OpenAIAdapter, get_openai_adapter
from ..adapters.vector_db import VectorDBAdapter, get_vector_db_adapter
from ..models.shared_content import SharedContent
from ..models.enums import ContentCategory

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingInput:
    """Input for embedding generation."""

    content_id: str
    text: str
    content_category: Optional[str] = None


@dataclass
class SimilarContentResult:
    """Result of similarity search."""

    content_id: str
    score: float
    content_category: Optional[str] = None


class EmbeddingService:
    """
    Service for embedding operations.

    Handles:
    - Building embedding input text from SharedContent
    - Generating embeddings via OpenAI
    - Storing/retrieving vectors from Qdrant
    - Similarity search
    """

    def __init__(
        self,
        openai_adapter: Optional[OpenAIAdapter] = None,
        vector_db: Optional[VectorDBAdapter] = None,
    ):
        """
        Initialize embedding service.

        Args:
            openai_adapter: OpenAI adapter instance
            vector_db: Vector DB adapter instance
        """
        self._openai = openai_adapter
        self._vector_db = vector_db

    @property
    def openai(self) -> OpenAIAdapter:
        """Lazy-loaded OpenAI adapter."""
        if self._openai is None:
            self._openai = get_openai_adapter()
        return self._openai

    @property
    def vector_db(self) -> VectorDBAdapter:
        """Lazy-loaded Vector DB adapter."""
        if self._vector_db is None:
            self._vector_db = get_vector_db_adapter()
        return self._vector_db

    def build_embedding_text(self, content: SharedContent) -> str:
        """
        Build text input for embedding from SharedContent.

        Creates a concise, structured text that captures the key semantic aspects.

        Args:
            content: SharedContent to build text from

        Returns:
            Embedding input text
        """
        parts = []

        # Add main topic
        if content.topic_main:
            parts.append(content.topic_main)

        # Add title
        if content.title and content.title != content.topic_main:
            parts.append(content.title)

        # Add category context
        if content.content_category:
            parts.append(f"Category: {content.content_category.value}")

        # Add subcategories
        if content.subcategories:
            tags = ", ".join(content.subcategories[:5])
            parts.append(f"Tags: {tags}")

        # Add locations
        if content.locations:
            locs = ", ".join(content.locations[:3])
            parts.append(f"Location: {locs}")

        # Fallback to caption/description if no topic
        if not parts:
            if content.caption:
                parts.append(content.caption[:200])
            elif content.description:
                parts.append(content.description[:200])

        return ". ".join(parts) if parts else content.url

    def generate_and_store_embedding(
        self,
        content: SharedContent,
    ) -> str:
        """
        Generate embedding for content and store in vector DB.

        Args:
            content: SharedContent to embed

        Returns:
            Embedding ID (same as content.id)
        """
        # Build embedding text
        text = self.build_embedding_text(content)

        # Generate embedding
        result = self.openai.generate_embedding(text)

        # Build payload with metadata for filtering
        payload = {
            "content_id": str(content.id),
        }
        if content.content_category:
            payload["content_category"] = content.content_category.value
        if content.source_platform:
            payload["source_platform"] = content.source_platform.value

        # Store in vector DB
        embedding_id = str(content.id)
        self.vector_db.upsert(
            id=embedding_id,
            vector=result.embedding,
            payload=payload,
        )

        logger.info(
            "Generated embedding for content %s, tokens used: %d",
            content.id,
            result.usage_tokens,
        )

        return embedding_id

    def generate_embeddings_batch(
        self,
        contents: List[SharedContent],
    ) -> Dict[str, str]:
        """
        Generate embeddings for multiple contents.

        Args:
            contents: List of SharedContent to embed

        Returns:
            Dict mapping content_id to embedding_id
        """
        if not contents:
            return {}

        # Build texts
        texts = [self.build_embedding_text(c) for c in contents]

        # Generate embeddings
        results = self.openai.generate_embeddings_batch(texts)

        # Prepare points for batch upsert
        points = []
        result_map = {}

        for content, emb_result in zip(contents, results):
            embedding_id = str(content.id)
            payload = {"content_id": embedding_id}

            if content.content_category:
                payload["content_category"] = content.content_category.value
            if content.source_platform:
                payload["source_platform"] = content.source_platform.value

            points.append(
                {
                    "id": embedding_id,
                    "vector": emb_result.embedding,
                    "payload": payload,
                }
            )
            result_map[str(content.id)] = embedding_id

        # Batch upsert
        self.vector_db.upsert_batch(points)

        logger.info("Generated embeddings for %d contents", len(contents))

        return result_map

    def get_embeddings(self, content_ids: List[str]) -> Dict[str, List[float]]:
        """
        Retrieve embeddings by content IDs.

        Args:
            content_ids: List of content IDs

        Returns:
            Dict mapping content_id to embedding vector
        """
        return self.vector_db.get_vectors(content_ids)

    def find_similar(
        self,
        content_id: str,
        limit: int = 10,
        score_threshold: float = 0.5,
        content_category: Optional[ContentCategory] = None,
    ) -> List[SimilarContentResult]:
        """
        Find content similar to a given content.

        Args:
            content_id: Content ID to find similar items for
            limit: Maximum results
            score_threshold: Minimum similarity score
            content_category: Optional category filter

        Returns:
            List of similar content results
        """
        # Get the embedding for the query content
        vectors = self.vector_db.get_vectors([content_id])
        if content_id not in vectors:
            logger.warning("No embedding found for content %s", content_id)
            return []

        query_vector = vectors[content_id]

        # Search
        filter_conditions = None
        if content_category:
            filter_conditions = {"content_category": content_category.value}

        results = self.vector_db.search(
            vector=query_vector,
            limit=limit + 1,  # +1 to exclude self
            score_threshold=score_threshold,
            filter_conditions=filter_conditions,
        )

        # Convert and exclude self
        similar = []
        for r in results:
            if r.id != content_id:
                similar.append(
                    SimilarContentResult(
                        content_id=r.id,
                        score=r.score,
                        content_category=r.payload.get("content_category"),
                    )
                )

        return similar[:limit]

    def find_similar_by_text(
        self,
        text: str,
        limit: int = 10,
        score_threshold: float = 0.5,
        content_category: Optional[ContentCategory] = None,
    ) -> List[SimilarContentResult]:
        """
        Find content similar to arbitrary text.

        Useful for search functionality.

        Args:
            text: Query text
            limit: Maximum results
            score_threshold: Minimum similarity
            content_category: Optional category filter

        Returns:
            List of similar content results
        """
        # Generate embedding for query text
        result = self.openai.generate_embedding(text)

        # Search
        filter_conditions = None
        if content_category:
            filter_conditions = {"content_category": content_category.value}

        results = self.vector_db.search(
            vector=result.embedding,
            limit=limit,
            score_threshold=score_threshold,
            filter_conditions=filter_conditions,
        )

        return [
            SimilarContentResult(
                content_id=r.id,
                score=r.score,
                content_category=r.payload.get("content_category"),
            )
            for r in results
        ]

    def delete_embedding(self, content_id: str) -> None:
        """
        Delete embedding for a content.

        Args:
            content_id: Content ID to delete embedding for
        """
        self.vector_db.delete([content_id])
        logger.info("Deleted embedding for content %s", content_id)


@functools.lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Get or create EmbeddingService singleton."""
    return EmbeddingService()
