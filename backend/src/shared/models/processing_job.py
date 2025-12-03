"""
ProcessingJob entity model.
Tracks background job processing for SharedContent.
"""
from sqlalchemy import Column, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid as uuid_pkg

from .base import Base, TimestampMixin


class JobStatus(str):
    """Job processing status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingJob(Base, TimestampMixin):
    """Background job tracking for content processing."""
    
    __tablename__ = "processing_jobs"
    
    # Identity
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    shared_content_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shared_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Job Details
    job_type = Column(
        Text,
        nullable=False,
        comment="Type of job (ingest, analyze, etc.)"
    )
    status = Column(
        Text,
        nullable=False,
        default=JobStatus.PENDING
    )
    error_message = Column(Text)
    metadata = Column(JSONB)
    
    # Relationships
    shared_content = relationship("SharedContent", back_populates="processing_jobs")
