"""
ProcessingJob repository for data access.
"""
from sqlalchemy.orm import Session

from ..models.processing_job import ProcessingJob
from .base import BaseRepository


class ProcessingJobRepository(BaseRepository[ProcessingJob]):
    """Repository for ProcessingJob entity."""
    
    def __init__(self, db: Session):
        super().__init__(ProcessingJob, db)
