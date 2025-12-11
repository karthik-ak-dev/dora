"""
ProcessingJob Repository

Database operations for background processing jobs.

Common Operations:
==================
- get_pending_jobs()    → Get jobs waiting to be processed
- update_job_status()   → Update job status and error message
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.repositories.base import BaseRepository
from src.shared.models.processing_job import ProcessingJob, JobStatus


class ProcessingJobRepository(BaseRepository[ProcessingJob]):
    """
    Repository for ProcessingJob database operations.

    Handles job status tracking and queue management.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize ProcessingJobRepository.

        Args:
            session: Async database session
        """
        super().__init__(ProcessingJob, session)

    # ═══════════════════════════════════════════════════════════════════════════
    # READ OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_by_content_id(
        self,
        shared_content_id: UUID,
    ) -> List[ProcessingJob]:
        """
        Get all jobs for a specific content.

        Args:
            shared_content_id: Content UUID

        Returns:
            List of ProcessingJob for the content
        """
        result = await self.session.execute(
            select(ProcessingJob)
            .where(ProcessingJob.shared_content_id == shared_content_id)
            .order_by(ProcessingJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_jobs(
        self,
        job_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[ProcessingJob]:
        """
        Get pending jobs waiting to be processed.

        Args:
            job_type: Optional filter by job type
            limit: Max jobs to return

        Returns:
            List of pending ProcessingJob
        """
        query = select(ProcessingJob).where(ProcessingJob.status == JobStatus.PENDING.value)

        if job_type:
            query = query.where(ProcessingJob.job_type == job_type)

        query = query.order_by(ProcessingJob.created_at.asc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ═══════════════════════════════════════════════════════════════════════════
    # UPDATE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        error_message: Optional[str] = None,
    ) -> Optional[ProcessingJob]:
        """
        Update job status.

        Args:
            job_id: Job UUID
            status: New JobStatus
            error_message: Error message if status is FAILED

        Returns:
            Updated job or None if not found
        """
        job = await self.get(job_id)
        if not job:
            return None

        job.status = status.value
        if error_message and status == JobStatus.FAILED:
            job.error_message = error_message

        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def create_job(
        self,
        shared_content_id: UUID,
        job_type: str,
    ) -> ProcessingJob:
        """
        Create a new processing job.

        Args:
            shared_content_id: Content to process
            job_type: Type of job (ingest, analyze, etc.)

        Returns:
            Created ProcessingJob
        """
        return await self.create(
            shared_content_id=shared_content_id,
            job_type=job_type,
            status=JobStatus.PENDING.value,
        )
