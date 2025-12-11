"""
Logging Configuration

Structured logging setup using structlog for consistent, parseable logs.

Log Output:
===========
Development:
    2024-01-15 10:30:00 [info     ] User created                   user_id=550e8400-e29b-...

Production (JSON):
    {"timestamp": "2024-01-15T10:30:00", "level": "info", "event": "User created", "user_id": "550e8400-..."}

Features:
=========
- Structured key-value logging
- Context variables (add info to all subsequent logs)
- Colored console output in development
- JSON output in production
- Automatic timestamp and log level

Usage:
======
    from src.shared.core.logging import logger, get_logger, log_context

    # Basic logging
    logger.info("User created", user_id=user_id, email=email)
    logger.error("Database error", error=str(e), query=query)

    # Get named logger
    db_logger = get_logger("database")
    db_logger.debug("Query executed", sql=sql)

    # Add context to all subsequent logs
    log_context(request_id=request_id, user_id=user_id)
    logger.info("Processing request")  # Includes request_id and user_id
"""

import logging
import sys
from typing import Any

import structlog
from structlog.typing import Processor

from src.config.settings import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up structlog with:
    - Development: Colored console output for readability
    - Production: JSON output for log aggregation systems

    Called automatically when this module is imported.
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Shared processors for all environments
    shared_processors: list[Processor] = [
        # Merge context variables from contextvars
        structlog.contextvars.merge_contextvars,
        # Add log level (info, warning, error, etc.)
        structlog.stdlib.add_log_level,
        # Add logger name for filtering
        structlog.stdlib.add_logger_name,
        # Format positional arguments
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Add ISO timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Decode bytes to strings
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_development:
        # Development: colored console output for readability
        processors: list[Processor] = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output for log aggregation
        processors = shared_processors + [
            # Format exception info
            structlog.processors.format_exc_info,
            # Output as JSON
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name, defaults to module name if not specified

    Returns:
        Configured structlog logger

    Example:
        db_logger = get_logger("database")
        db_logger.info("Connected to database", host=host, port=port)
    """
    return structlog.get_logger(name)


def log_context(**kwargs: Any) -> None:
    """
    Add context variables to all subsequent log calls.

    Context is stored in context variables and automatically included
    in all log messages until cleared or the request ends.

    Args:
        **kwargs: Key-value pairs to add to log context

    Example:
        # Add request context at the start of request handling
        log_context(request_id="abc-123", user_id="user-456")

        # All subsequent logs include these values
        logger.info("Processing started")  # Includes request_id, user_id
        logger.info("Step complete")       # Includes request_id, user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_log_context() -> None:
    """
    Clear all context variables.

    Call this at the end of request processing to prevent
    context from leaking to other requests.

    Example:
        try:
            log_context(request_id=request_id)
            # ... process request ...
        finally:
            clear_log_context()
    """
    structlog.contextvars.clear_contextvars()


# Initialize logging on module import
setup_logging()

# Default logger instance for convenient import
logger = get_logger("dora")

