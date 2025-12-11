"""
User Entity Model

Represents a registered application user.

Model Hierarchy:
================
    User
       ├── saved_content (UserContentSave[]) - User's saved content
       └── clusters (Cluster[])              - User's content clusters

SAMPLE USER RECORD:
┌──────────────────────────────────────────────────────────────────────────────┐
│ id               │ 550e8400-e29b-41d4-a716-446655440000                      │
│ email            │ "user@example.com"                                        │
│ password_hash    │ "$2b$12$..."                                              │
│ created_at       │ 2024-01-01T00:00:00Z                                      │
│ updated_at       │ 2024-01-15T10:30:00Z                                      │
└──────────────────────────────────────────────────────────────────────────────┘
"""

from typing import TYPE_CHECKING
import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import Base, TimestampMixin


# TYPE_CHECKING block prevents circular imports while enabling type hints
if TYPE_CHECKING:
    from src.shared.models.user_content_save import UserContentSave
    from src.shared.models.cluster import Cluster


class User(Base, TimestampMixin):
    """
    User model representing a registered application user.

    Users can:
    - Save content from various platforms
    - Have their content auto-clustered into groups
    - Favorite and archive their saves

    Attributes:
        id: Unique identifier (UUID v4)
        email: User's email address (unique, indexed)
        password_hash: Bcrypt hashed password

    Relationships:
        saved_content: All content saves by this user
        clusters: All clusters belonging to this user
    """

    __tablename__ = "users"

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY KEY
    # ═══════════════════════════════════════════════════════════════════════════

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # AUTHENTICATION
    # ═══════════════════════════════════════════════════════════════════════════

    # Email address - used for login
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Bcrypt hashed password
    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════════════════

    # One-to-Many: User has many saved content items
    saved_content: Mapped[list["UserContentSave"]] = relationship(
        "UserContentSave",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # One-to-Many: User has many clusters
    clusters: Mapped[list["Cluster"]] = relationship(
        "Cluster",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<User(id={self.id}, email={self.email})>"
