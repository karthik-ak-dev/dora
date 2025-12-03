"""
User entity model.
"""
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid as uuid_pkg

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Registered application user."""
    
    __tablename__ = "users"
    
    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    
    # Authentication
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash = Column(
        Text,
        nullable=False
    )
    
    # Relationships
    saved_content = relationship(
        "UserContentSave",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    clusters = relationship(
        "Cluster",
        back_populates="user",
        cascade="all, delete-orphan"
    )
