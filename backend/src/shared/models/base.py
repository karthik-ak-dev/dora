"""
Base Model Classes

This module provides the foundational classes for all SQLAlchemy models in Dora.
It includes the declarative base and common mixins for timestamps and soft deletion.

These base classes ensure consistency across all models and reduce code duplication.

Model Hierarchy:
================
    Base                    ← SQLAlchemy declarative base
       │
       ├── TimestampMixin   ← Automatic created_at/updated_at
       │
       └── SoftDeleteMixin  ← Soft delete with deleted_at

Usage:
======
    from src.shared.models.base import Base, TimestampMixin, SoftDeleteMixin

    class User(Base, TimestampMixin):
        __tablename__ = "users"
        id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
        email: Mapped[str] = mapped_column(String(255), unique=True)

    class Content(Base, TimestampMixin, SoftDeleteMixin):
        __tablename__ = "content"
        id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
        # Can be soft-deleted with content.deleted_at = datetime.now()
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    This is the declarative base that all models inherit from. It provides:
    - Automatic table name generation
    - Type annotation support for columns
    - JSON type mapping for PostgreSQL JSONB columns

    All models in the application should inherit from this class either
    directly or through one of the mixin classes.

    Example:
        class User(Base, TimestampMixin):
            __tablename__ = "users"

            id: Mapped[uuid.UUID] = mapped_column(
                UUID(as_uuid=True),
                primary_key=True,
                default=uuid.uuid4
            )
    """

    # Map Python dict type to PostgreSQL JSONB for flexible JSON storage
    type_annotation_map = {
        dict[str, Any]: "JSONB",
    }


class TimestampMixin:
    """
    Mixin that adds automatic timestamp tracking to models.

    Provides two timestamp columns that are automatically managed:
    - created_at: Set when the record is first inserted
    - updated_at: Updated whenever the record is modified

    Usage:
        class MyModel(Base, TimestampMixin):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)

    Example values:
        created_at: 2024-01-15T10:30:00Z (when record was created)
        updated_at: 2024-01-16T14:45:30Z (last modification time)

    Database Behavior:
    ==================
    - created_at: Set by PostgreSQL on INSERT via server_default
    - updated_at: Set on INSERT, updated by SQLAlchemy on UPDATE via onupdate
    """

    # Timestamp when the record was created
    # Automatically set by the database on INSERT using server_default
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # Store with timezone info for global apps
        server_default=text("CURRENT_TIMESTAMP"),  # Database sets this on INSERT
        nullable=False,
    )

    # Timestamp when the record was last updated
    # Automatically updated by SQLAlchemy on UPDATE using onupdate
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # Store with timezone info
        server_default=text("CURRENT_TIMESTAMP"),  # Initial value on INSERT
        onupdate=lambda: datetime.now(timezone.utc),  # SQLAlchemy updates this on UPDATE
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Mixin that adds soft delete capability to models.

    Instead of permanently deleting records, soft delete marks them
    as deleted by setting a timestamp. This allows:
    - Data recovery if needed
    - Audit trail preservation
    - Referential integrity maintenance

    Usage:
        class MyModel(Base, TimestampMixin, SoftDeleteMixin):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)

    Example values:
        deleted_at: None              (record is active)
        deleted_at: 2024-01-20T09:00:00Z  (record was soft-deleted)

    Querying:
    =========
    Queries should filter out soft-deleted records:
        query.where(MyModel.deleted_at.is_(None))

    Soft Delete Pattern:
    ====================
        # Soft delete a record
        record.deleted_at = datetime.now(timezone.utc)
        await session.commit()

        # Check if deleted
        if record.is_deleted:
            print("This record has been deleted")

        # Restore a record
        record.deleted_at = None
        await session.commit()
    """

    # Timestamp when the record was soft-deleted
    # NULL means the record is active; a timestamp means it's deleted
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,  # NULL = not deleted
        default=None,  # Records start as not deleted
    )

    @property
    def is_deleted(self) -> bool:
        """
        Check if the record has been soft deleted.

        Returns:
            True if deleted_at is set (record is deleted)
            False if deleted_at is None (record is active)
        """
        return self.deleted_at is not None
