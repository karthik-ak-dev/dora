"""
Repository Pattern Implementations

This module provides the Repository pattern for database operations.
Repositories encapsulate database queries and provide a clean API for data access.

Repository Hierarchy:
=====================
    BaseRepository[ModelType]           ← Generic CRUD operations
         │
         ├── UserRepository             ← User-specific queries
         ├── SharedContentRepository    ← Content deduplication & status
         ├── UserContentSaveRepository  ← User saves with filtering
         ├── ClusterRepository          ← AI cluster management
         └── ProcessingJobRepository    ← Background job tracking

Usage Example:
==============
    from src.shared.db import get_db
    from src.shared.repositories import UserRepository, SharedContentRepository

    async def save_content(db: AsyncSession, user_id: UUID, url: str):
        user_repo = UserRepository(db)
        content_repo = SharedContentRepository(db)

        # Check if content exists
        existing = await content_repo.get_by_url_hash(url_hash)
        if existing:
            return existing

        # Create new content
        return await content_repo.create(url=url, url_hash=url_hash, ...)
"""

from src.shared.repositories.base import BaseRepository
from src.shared.repositories.user_repository import UserRepository
from src.shared.repositories.shared_content_repository import SharedContentRepository
from src.shared.repositories.user_content_save_repository import UserContentSaveRepository
from src.shared.repositories.cluster_repository import ClusterRepository
from src.shared.repositories.processing_job_repository import ProcessingJobRepository

__all__ = [
    # Base class
    "BaseRepository",
    # Entity-specific repositories
    "UserRepository",
    "SharedContentRepository",
    "UserContentSaveRepository",
    "ClusterRepository",
    "ProcessingJobRepository",
]
