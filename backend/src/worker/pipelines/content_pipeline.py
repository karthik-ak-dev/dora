"""
Content processing pipeline.
Orchestrates ingestion -> enrichment -> analysis -> vectorization.

CLASSIFICATION ARCHITECTURE:
This pipeline is responsible for assigning the AUTHORITATIVE content_category
to each piece of content. The classification is:
- Strong and tight (one of the defined ContentCategory values)
- NOT dependent on user context or existing clusters
- Immutable after assignment (when status transitions to READY)

Pipeline Stages:
1. INGESTION: Fetch metadata from platform (title, thumbnail, etc.)
2. ENRICHMENT: Extract text (transcription, OCR, etc.)
3. ANALYSIS: AI classification → content_category assigned here
4. VECTORIZATION: Generate embedding for similarity search

After this pipeline completes:
- SharedContent.content_category is set
- SharedContent.status = READY
- Clustering can then group items WITHIN each category
"""

from typing import Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ...shared.models.shared_content import SharedContent
from ...shared.models.enums import ContentCategory, ItemStatus, IntentType
from ...shared.repositories.shared_content_repository import SharedContentRepository


@dataclass
class ContentAnalysisResult:
    """Result from AI content analysis."""

    content_category: ContentCategory  # REQUIRED - the authoritative classification
    topic_main: Optional[str] = None
    subcategories: Optional[list] = None
    locations: Optional[list] = None
    entities: Optional[list] = None
    intent: Optional[IntentType] = None
    summary: Optional[str] = None


@dataclass
class PipelineResult:
    """Result of content processing pipeline."""

    success: bool
    shared_content_id: str
    content_category: Optional[ContentCategory] = None
    error_message: Optional[str] = None


class ContentPipeline:
    """
    Content processing pipeline.

    Processes SharedContent through:
    1. Ingestion (metadata fetching)
    2. Enrichment (text extraction)
    3. Analysis (AI classification)
    4. Vectorization (embedding generation)

    The key output is content_category - the authoritative classification.
    """

    def __init__(self, db: Session):
        self.db = db
        self.content_repo = SharedContentRepository(db)

    def process(self, shared_content_id: str) -> PipelineResult:
        """
        Process a SharedContent item through the full pipeline.

        Args:
            shared_content_id: ID of SharedContent to process

        Returns:
            PipelineResult with success status and assigned category
        """
        content = self.content_repo.get_by_id(shared_content_id)
        if not content:
            return PipelineResult(
                success=False,
                shared_content_id=shared_content_id,
                error_message="SharedContent not found",
            )

        # Skip if already processed
        if content.status == ItemStatus.READY:
            return PipelineResult(
                success=True,
                shared_content_id=shared_content_id,
                content_category=content.content_category,
            )

        try:
            # Update status to PROCESSING
            content.status = ItemStatus.PROCESSING
            self.db.commit()

            # Stage 1: Ingestion
            self._run_ingestion(content)

            # Stage 2: Enrichment
            self._run_enrichment(content)

            # Stage 3: Analysis (assigns content_category)
            analysis_result = self._run_analysis(content)

            # Stage 4: Vectorization
            embedding_id = self._run_vectorization(content, analysis_result)

            # Update SharedContent with results
            self.content_repo.update_after_processing(
                content_id=shared_content_id,
                content_category=analysis_result.content_category,
                topic_main=analysis_result.topic_main,
                subcategories=analysis_result.subcategories,
                locations=analysis_result.locations,
                entities=analysis_result.entities,
                intent=analysis_result.intent,
                embedding_id=embedding_id,
            )

            return PipelineResult(
                success=True,
                shared_content_id=shared_content_id,
                content_category=analysis_result.content_category,
            )

        except Exception as e:
            # Mark as failed
            content.status = ItemStatus.FAILED
            self.db.commit()

            return PipelineResult(
                success=False, shared_content_id=shared_content_id, error_message=str(e)
            )

    def _run_ingestion(self, content: SharedContent) -> None:
        """
        Stage 1: Fetch metadata from platform.

        TODO: Implement actual scraping using:
        - instagram_scraper for Instagram
        - youtube_scraper for YouTube
        - generic_scraper for other URLs
        """
        # Placeholder - actual implementation would use scrapers

    def _run_enrichment(self, content: SharedContent) -> None:
        """
        Stage 2: Extract and unify text content.

        TODO: Implement:
        - Audio transcription (Whisper)
        - Visual analysis (GPT-4V)
        - Text unification
        """
        # Placeholder - actual implementation would extract text
        # Build content_text from title, caption, description, transcript
        parts = []
        if content.title:
            parts.append(f"Title: {content.title}")
        if content.caption:
            parts.append(f"Caption: {content.caption}")
        if content.description:
            parts.append(f"Description: {content.description}")

        content.content_text = "\n".join(parts) if parts else None
        self.db.commit()

    def _run_analysis(self, content: SharedContent) -> ContentAnalysisResult:
        """
        Stage 3: AI analysis and classification.

        This is where content_category is assigned.
        The classification is STRONG and TIGHT - must be one of ContentCategory values.

        TODO: Implement actual LLM call using OpenAI/Claude.
        """
        # Placeholder - actual implementation would call LLM
        # For now, return default category
        # In production, this would parse the LLM response and validate

        return ContentAnalysisResult(
            content_category=ContentCategory.MISC,  # Default until LLM implemented
            topic_main=content.title,
            subcategories=[],
            locations=[],
            entities=[],
            intent=IntentType.MISC,
        )

    def _run_vectorization(
        self, content: SharedContent, _analysis: ContentAnalysisResult
    ) -> Optional[str]:
        """
        Stage 4: Generate embedding and store in vector DB.

        TODO: Implement actual embedding generation using:
        - OpenAI text-embedding-3-small
        - Qdrant for storage
        """
        # Placeholder - actual implementation would:
        # 1. Build embedding input text
        # 2. Call OpenAI embeddings API
        # 3. Store in Qdrant
        # 4. Return embedding_id

        return f"shared:{content.id}"
