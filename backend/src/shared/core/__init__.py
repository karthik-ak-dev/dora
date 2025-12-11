"""
Core Module

Provides core functionality shared across the application:
- Structured logging
- Custom exceptions
- Security utilities

Usage:
======
    from src.shared.core.logging import logger, get_logger
    from src.shared.core.exceptions import DoraException, NotFoundError

    logger.info("Starting operation", user_id=user_id)
"""

from src.shared.core.logging import (
    logger,
    get_logger,
    log_context,
    clear_log_context,
)
from src.shared.core.exceptions import (
    DoraException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    UserNotFoundError,
    ContentNotFoundError,
    SaveNotFoundError,
    ClusterNotFoundError,
    ValidationError,
    ConflictError,
    DuplicateResourceError,
    RateLimitError,
    ServiceUnavailableError,
    ExternalServiceError,
)

__all__ = [
    # Logging
    "logger",
    "get_logger",
    "log_context",
    "clear_log_context",
    # Exceptions
    "DoraException",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "UserNotFoundError",
    "ContentNotFoundError",
    "SaveNotFoundError",
    "ClusterNotFoundError",
    "ValidationError",
    "ConflictError",
    "DuplicateResourceError",
    "RateLimitError",
    "ServiceUnavailableError",
    "ExternalServiceError",
]
