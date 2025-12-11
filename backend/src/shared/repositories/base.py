"""
Base Repository

This module provides a generic base repository with common CRUD operations.
All entity-specific repositories inherit from this class.

What This Provides:
===================
- get(id)        → Fetch single record by UUID
- get_by_ids()   → Fetch multiple records by UUIDs
- list()         → List records with pagination and filtering
- count()        → Count records with filtering
- create()       → Create new record
- update()       → Update existing record
- delete()       → Hard delete record
- soft_delete()  → Soft delete (set deleted_at)
- exists()       → Check if record exists

Generic Type Pattern:
=====================
The BaseRepository uses Python generics to be type-safe:

    class UserRepository(BaseRepository[User]):
        pass

    repo = UserRepository(db)
    user = await repo.get(id)  # Returns User, not Any!

This gives you:
- IDE autocomplete for returned objects
- Type checking catches errors at development time
- Clear documentation of what types are used

CRUD Operations Flow:
=====================
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CRUD OPERATIONS                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   CREATE:                                                                   │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │ instance = Model(**kwargs)   # Create Python object         │          │
│   │ session.add(instance)        # Add to session (not in DB yet)│         │
│   │ await session.flush()        # Send INSERT to database      │          │
│   │ await session.refresh()      # Reload from DB (get id, etc.)│          │
│   │ return instance              # Return with all DB values    │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
│   READ:                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │ query = select(Model).where(...)  # Build query             │          │
│   │ result = await session.execute()   # Execute SQL            │          │
│   │ return result.scalar_one_or_none() # Extract result         │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
│   UPDATE:                                                                   │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │ instance = await self.get(id)  # Load from DB               │          │
│   │ setattr(instance, field, value) # Modify Python object      │          │
│   │ await session.flush()           # Send UPDATE to database   │          │
│   │ await session.refresh()         # Reload with new values    │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
│   DELETE:                                                                   │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │ instance = await self.get(id)   # Load from DB              │          │
│   │ await session.delete(instance)   # Mark for deletion        │          │
│   │ await session.flush()            # Send DELETE to database  │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

flush() vs commit():
====================
- flush(): Sends SQL to database but doesn't commit transaction
  - Changes are visible within the same session
  - Can be rolled back if error occurs later

- commit(): Permanently saves all changes
  - Called by get_db() after request handler completes
  - Repository methods use flush() to allow request-level transactions
"""

from datetime import datetime, timezone
from typing import Any, Generic, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from src.shared.models.base import Base


# TypeVar bound to Base ensures we only work with SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository providing common CRUD operations.

    All entity-specific repositories inherit from this class and add
    their own specialized query methods.

    Type Parameter:
        ModelType: The SQLAlchemy model class this repository manages

    Attributes:
        model: The SQLAlchemy model class
        session: The async database session

    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)

            # Add user-specific methods here
            async def get_by_email(self, email: str) -> Optional[User]:
                ...
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            model: SQLAlchemy model class (e.g., User, Cluster, SharedContent)
            session: Async database session from get_db()

        Example:
            repo = UserRepository(db)  # Creates with User model internally
        """
        self.model = model
        self.session = session

    # ═══════════════════════════════════════════════════════════════════════════
    # READ OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get(self, record_id: UUID) -> Optional[ModelType]:
        """
        Get a single record by its UUID.

        This is the most basic read operation. It fetches exactly one
        record or returns None if not found.

        Args:
            record_id: The UUID of the record to fetch

        Returns:
            The model instance if found, None otherwise

        Example:
            user = await repo.get(UUID("550e8400-e29b-41d4-a716-446655440000"))
            if user:
                print(user.email)

        SQL Generated:
            SELECT * FROM users WHERE id = '550e8400-...'
        """
        result = await self.session.execute(select(self.model).where(self.model.id == record_id))
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[UUID]) -> list[ModelType]:
        """
        Get multiple records by their UUIDs.

        Efficiently fetches multiple records in a single query using IN clause.
        Useful when you have a list of IDs and need all the corresponding records.

        Args:
            ids: List of UUIDs to fetch

        Returns:
            List of model instances (may be fewer than requested if some not found)

        Example:
            ids = [uuid1, uuid2, uuid3]
            users = await repo.get_by_ids(ids)
            # Returns list of 0-3 users

        SQL Generated:
            SELECT * FROM users WHERE id IN ('uuid1', 'uuid2', 'uuid3')
        """
        if not ids:
            return []

        result = await self.session.execute(select(self.model).where(self.model.id.in_(ids)))
        return list(result.scalars().all())

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = True,
    ) -> list[ModelType]:
        """
        List records with pagination and optional filtering.

        This is a flexible list method that supports:
        - Pagination (offset/limit)
        - Simple equality filters
        - Ordering by any field

        Args:
            offset: Number of records to skip (for pagination)
            limit: Maximum records to return (default 100)
            filters: Dict of field=value for WHERE clauses
            order_by: Field name to order results by
            order_desc: If True, order descending; if False, ascending

        Returns:
            List of model instances

        Example:
            # Get page 2 of users (20 per page)
            users = await repo.list(
                offset=20,
                limit=20,
                order_by="created_at",
                order_desc=True
            )

        SQL Generated:
            SELECT * FROM users
            ORDER BY created_at DESC
            OFFSET 20 LIMIT 20
        """
        query = select(self.model)

        # Apply filters: WHERE field = value
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        # Apply ordering: ORDER BY field [DESC|ASC]
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            query = query.order_by(order_field.desc() if order_desc else order_field)

        # Apply pagination: OFFSET x LIMIT y
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """
        Count records with optional filtering.

        Efficiently counts records without loading them into memory.

        Args:
            filters: Dict of field=value for WHERE clauses

        Returns:
            Number of matching records

        Example:
            total_users = await repo.count()
            print(f"Total users: {total_users}")

        SQL Generated:
            SELECT COUNT(*) FROM users
        """
        query = select(sql_count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def exists(self, record_id: UUID) -> bool:
        """
        Check if a record exists without loading it.

        More efficient than get() when you only need to know if it exists.

        Args:
            record_id: The UUID to check

        Returns:
            True if record exists, False otherwise

        Example:
            if await repo.exists(user_id):
                print("User exists!")

        SQL Generated:
            SELECT COUNT(*) FROM users WHERE id = '...'
        """
        result = await self.session.execute(
            select(sql_count()).select_from(self.model).where(self.model.id == record_id)
        )
        return (result.scalar() or 0) > 0

    # ═══════════════════════════════════════════════════════════════════════════
    # CREATE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new record.

        Creates a new instance of the model, adds it to the session,
        and flushes to get the generated ID and defaults.

        Args:
            **kwargs: Field values for the new record

        Returns:
            The created model instance with all DB-generated values

        Example:
            user = await repo.create(
                email="user@example.com",
                password_hash=hashed_password
            )
            print(user.id)  # UUID generated by DB
            print(user.created_at)  # Timestamp set by DB

        SQL Generated:
            INSERT INTO users (email, password_hash, ...)
            VALUES ('user@example.com', '...', ...)
            RETURNING id, created_at, ...
        """
        # Create model instance with provided field values
        instance = self.model(**kwargs)

        # Add to session (marks as pending insert)
        self.session.add(instance)

        # Flush: send INSERT to database (but don't commit yet)
        # This gets us the DB-generated values (id, created_at, etc.)
        await self.session.flush()

        # Refresh: reload the instance from database
        # Ensures we have all default values and triggers
        await self.session.refresh(instance)

        return instance

    # ═══════════════════════════════════════════════════════════════════════════
    # UPDATE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def update(
        self,
        record_id: UUID,
        **kwargs: Any,
    ) -> Optional[ModelType]:
        """
        Update a record by ID.

        Loads the record, applies changes, and flushes to database.
        Only updates fields that are provided and not None.

        Args:
            record_id: UUID of the record to update
            **kwargs: Fields to update (None values are ignored)

        Returns:
            Updated model instance, or None if not found

        Example:
            user = await repo.update(
                user_id,
                email="new@example.com"
            )
            if user:
                print(f"Updated: {user.email}")

        SQL Generated:
            UPDATE users
            SET email = 'new@example.com', updated_at = NOW()
            WHERE id = '...'
        """
        # First, load the existing record
        instance = await self.get(record_id)
        if not instance:
            return None

        # Apply updates (skip None values to allow partial updates)
        for field, value in kwargs.items():
            if hasattr(instance, field) and value is not None:
                setattr(instance, field, value)

        # Flush changes to database
        await self.session.flush()

        # Refresh to get any DB-side changes (e.g., updated_at)
        await self.session.refresh(instance)

        return instance

    # ═══════════════════════════════════════════════════════════════════════════
    # DELETE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def delete(self, record_id: UUID) -> bool:
        """
        Hard delete a record by ID.

        Permanently removes the record from the database.
        Use soft_delete() instead if you want to preserve data.

        Args:
            record_id: UUID of the record to delete

        Returns:
            True if deleted, False if not found

        Example:
            if await repo.delete(user_id):
                print("User deleted permanently")

        SQL Generated:
            DELETE FROM users WHERE id = '...'

        Warning:
            This is irreversible! Consider using soft_delete() instead.
        """
        instance = await self.get(record_id)
        if not instance:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def soft_delete(self, record_id: UUID) -> Optional[ModelType]:
        """
        Soft delete a record by setting deleted_at timestamp.

        The record remains in the database but is marked as deleted.
        This allows for data recovery and preserves audit trails.

        Note: Only works on models that have a deleted_at field
        (i.e., models using SoftDeleteMixin).

        Args:
            record_id: UUID of the record to soft delete

        Returns:
            Updated model instance, or None if not found or doesn't support soft delete

        Example:
            content = await repo.soft_delete(content_id)
            if content:
                print(f"Soft deleted at: {content.deleted_at}")

        SQL Generated:
            UPDATE shared_content SET deleted_at = NOW() WHERE id = '...'

        Querying soft-deleted records:
            Most queries should filter: WHERE deleted_at IS NULL
            This is typically done in repository methods.
        """
        instance = await self.get(record_id)

        # Check if record exists and supports soft delete
        if not instance or not hasattr(instance, "deleted_at"):
            return None

        # Set the deleted_at timestamp
        instance.deleted_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(instance)

        return instance
