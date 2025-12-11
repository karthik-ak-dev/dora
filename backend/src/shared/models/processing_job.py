"""
ProcessingJob Entity Model

Tracks background job processing for SharedContent.

Each SharedContent item goes through various processing stages,
and ProcessingJob tracks the status and any errors.

SAMPLE PROCESSING_JOB RECORD:
┌──────────────────────────────────────────────────────────────────────────────┐
│ id               │ 550e8400-e29b-41d4-a716-446655440000                      │
│ shared_content_id│ 660e8400-e29b-41d4-a716-446655440000                      │
│ job_type         │ "ingest"                                                   │
│ status           │ "COMPLETED"                                                │
│ error_message    │ null                                                       │
└──────────────────────────────────────────────────────────────────────────────┘
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import Base, TimestampMixin


if TYPE_CHECKING:
    from src.shared.models.shared_content import SharedContent


class JobStatus(str, Enum):
    """Job processing status enumeration."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingJob(Base, TimestampMixin):
    """
    ProcessingJob model - tracks background job processing for content.

    Attributes:
        id: Unique identifier (UUID v4)
        shared_content_id: The content being processed
        job_type: Type of job (ingest, analyze, embed, etc.)
        status: Current job status
        error_message: Error details if job failed
        metadata: Additional job metadata (JSON)

    Relationships:
        shared_content: The content this job is processing
    """

    __tablename__ = "processing_jobs"

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY KEY
    # ═══════════════════════════════════════════════════════════════════════════

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # FOREIGN KEYS
    # ═══════════════════════════════════════════════════════════════════════════

    shared_content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shared_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # JOB DETAILS
    # ═══════════════════════════════════════════════════════════════════════════

    # Type of job (ingest, analyze, embed, cluster, etc.)
    job_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Current status
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=JobStatus.PENDING.value,
    )

    # Error message if job failed
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Additional job metadata
    metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════════════════

    shared_content: Mapped["SharedContent"] = relationship(
        "SharedContent",
        back_populates="processing_jobs",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<ProcessingJob(id={self.id}, type={self.job_type}, status={self.status})>"
