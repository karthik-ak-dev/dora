"""
Database dependency for FastAPI.
"""

from typing import Generator
from sqlalchemy.orm import Session

from ...shared.adapters.database import DatabaseAdapter
from ...config.settings import settings

# Initialize database adapter
db_adapter = DatabaseAdapter(settings.DATABASE_URL)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    yield from db_adapter.get_db()
