"""
Shared Module

Contains code shared between API and Worker components:
- Models: SQLAlchemy ORM models
- Repositories: Data access layer
- Services: Business logic layer
- Schemas: Pydantic request/response models
- Core: Logging, exceptions, utilities
- Adapters: External service integrations

Package Structure:
==================
    shared/
    ├── core/           ← Logging, exceptions
    ├── db/             ← Database session management
    ├── models/         ← SQLAlchemy models
    ├── repositories/   ← Data access layer
    ├── services/       ← Business logic
    ├── schemas/        ← Pydantic schemas
    ├── adapters/       ← External services
    └── utils/          ← Utilities

Usage:
======
    from src.shared.models import User, SharedContent
    from src.shared.repositories import UserRepository
    from src.shared.services import AuthService
    from src.shared.schemas import UserCreate, AuthResponse
    from src.shared.core import logger, DoraException
"""
