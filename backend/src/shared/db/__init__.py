"""
Database Module

This module provides database connectivity and session management for Dora.

Architecture Overview:
======================
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   FastAPI Route                                                             │
│       │                                                                     │
│       │  Dependency Injection: get_db()                                     │
│       ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │              AsyncSession (from session.py)                 │          │
│   │                                                             │          │
│   │  - One session per request                                  │          │
│   │  - Auto-commit on success                                   │          │
│   │  - Auto-rollback on exception                               │          │
│   │  - Auto-close when request ends                             │          │
│   └─────────────────────────────────────────────────────────────┘          │
│       │                                                                     │
│       │  Passed to Repository                                               │
│       ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │              Repository (from repositories/)                │          │
│   │                                                             │          │
│   │  - UserRepository                                           │          │
│   │  - SharedContentRepository                                  │          │
│   │  - UserContentSaveRepository                                │          │
│   │  - ClusterRepository                                        │          │
│   │  - ProcessingJobRepository                                  │          │
│   └─────────────────────────────────────────────────────────────┘          │
│       │                                                                     │
│       │  SQL Queries                                                        │
│       ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │              PostgreSQL Database                            │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Components:
===========
- session.py: Database engine, session factory, and lifecycle functions

Usage in FastAPI:
=================
    from fastapi import Depends
    from src.shared.db import get_db
    from src.shared.repositories import UserRepository

    @app.get("/users/{user_id}")
    async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
        repo = UserRepository(db)
        user = await repo.get(user_id)
        return user
"""

from src.shared.db.session import (
    get_db,
    init_db,
    close_db,
    AsyncSessionLocal,
    engine,
)

__all__ = [
    # Session management
    "get_db",  # FastAPI dependency for getting a database session
    "init_db",  # Initialize database on app startup
    "close_db",  # Close database on app shutdown
    "AsyncSessionLocal",  # Session factory for manual session creation
    "engine",  # Database engine (for migrations, etc.)
]
