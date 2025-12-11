"""
Dora SQLAlchemy Models

This package contains all database models for the Dora application.

Model Hierarchy:
================
    User
       ├── saved_content (UserContentSave[])
       │      └── cluster_memberships (ClusterMembership[])
       └── clusters (Cluster[])
              └── cluster_memberships (ClusterMembership[])

    SharedContent
       ├── user_saves (UserContentSave[])
       └── processing_jobs (ProcessingJob[])

Models Overview:
================
- Base: Base class and mixins (timestamps, soft delete)
- User: Registered application user
- SharedContent: Universal content metadata (processed once, shared)
- UserContentSave: User's personal save of content
- Cluster: AI-generated group of similar content
- ClusterMembership: Junction table for clusters and saves
- ProcessingJob: Background job tracking

Usage:
======
    from src.shared.models import User, SharedContent, UserContentSave, Cluster

    # Query examples
    user = await repo.get(user_id)
    user.saved_content  # All saves by this user
    user.clusters       # All clusters for this user
"""

from src.shared.models.base import Base, TimestampMixin, SoftDeleteMixin
from src.shared.models.enums import (
    SourcePlatform,
    ItemStatus,
    ContentCategory,
    IntentType,
)
from src.shared.models.user import User
from src.shared.models.shared_content import SharedContent
from src.shared.models.user_content_save import UserContentSave
from src.shared.models.cluster import Cluster
from src.shared.models.cluster_membership import ClusterMembership
from src.shared.models.processing_job import ProcessingJob, JobStatus

__all__ = [
    # Base classes and mixins
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    # Enums
    "SourcePlatform",
    "ItemStatus",
    "ContentCategory",
    "IntentType",
    "JobStatus",
    # Core models
    "User",
    "SharedContent",
    "UserContentSave",
    "Cluster",
    "ClusterMembership",
    "ProcessingJob",
]
