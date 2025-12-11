"""
OpenAI adapter - OpenAI API client.

Provides:
- Text embeddings generation (text-embedding-3-small)
- LLM completions for content analysis and cluster labeling
"""

import json
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from openai import OpenAI, APIError, RateLimitError, APIConnectionError

from ...config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embedding: List[float]
    model: str
    usage_tokens: int


@dataclass
class CompletionResult:
    """Result of LLM completion."""

    content: str
    model: str
    usage_prompt_tokens: int
    usage_completion_tokens: int


class OpenAIAdapter:
    """
    Adapter for OpenAI API operations.

    Handles:
    - Embedding generation for content vectorization
    - LLM completions for content analysis and cluster labeling
    - Rate limiting and error handling
    """

    # Models
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    COMPLETION_MODEL = "gpt-4o-mini"
    COMPLETION_MAX_TOKENS = 1024

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key. If not provided, uses settings.
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        """Lazy-loaded OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenAI API key not configured")
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector

        Raises:
            OpenAIError: If API call fails
        """
        try:
            response = self.client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text,
            )

            return EmbeddingResult(
                embedding=response.data[0].embedding,
                model=response.model,
                usage_tokens=response.usage.total_tokens,
            )

        except RateLimitError as e:
            logger.warning("OpenAI rate limit hit: %s", e)
            raise
        except APIConnectionError as e:
            logger.error("OpenAI connection error: %s", e)
            raise
        except APIError as e:
            logger.error("OpenAI API error: %s", e)
            raise

    def generate_embeddings_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of EmbeddingResult objects
        """
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            try:
                response = self.client.embeddings.create(
                    model=self.EMBEDDING_MODEL,
                    input=batch,
                )

                for data in response.data:
                    results.append(
                        EmbeddingResult(
                            embedding=data.embedding,
                            model=response.model,
                            usage_tokens=response.usage.total_tokens // len(batch),
                        )
                    )

            except (RateLimitError, APIConnectionError, APIError) as e:
                logger.error("Batch embedding failed at index %d: %s", i, e)
                raise

        return results

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> CompletionResult:
        """
        Generate LLM completion.

        Args:
            system_prompt: System instruction
            user_prompt: User message
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            CompletionResult with generated text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.COMPLETION_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens or self.COMPLETION_MAX_TOKENS,
            )

            choice = response.choices[0]

            return CompletionResult(
                content=choice.message.content or "",
                model=response.model,
                usage_prompt_tokens=response.usage.prompt_tokens,
                usage_completion_tokens=response.usage.completion_tokens,
            )

        except (RateLimitError, APIConnectionError, APIError) as e:
            logger.error("OpenAI completion error: %s", e)
            raise

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate LLM completion and parse as JSON.

        Args:
            system_prompt: System instruction (should request JSON output)
            user_prompt: User message
            temperature: Sampling temperature

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If response is not valid JSON
        """
        result = self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )

        content = result.content.strip()

        # Handle markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response: %s", content[:200])
            raise ValueError(f"Invalid JSON response from LLM: {e}") from e


# Singleton instance for convenience
_openai_adapter: Optional[OpenAIAdapter] = None


def get_openai_adapter() -> OpenAIAdapter:
    """Get or create OpenAI adapter singleton."""
    global _openai_adapter
    if _openai_adapter is None:
        _openai_adapter = OpenAIAdapter()
    return _openai_adapter
