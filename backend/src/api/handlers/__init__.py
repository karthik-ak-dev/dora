"""
API Handlers

Route handlers for the Dora API.

Handlers follow the pattern:
- Parse HTTP requests
- Call service methods
- Format HTTP responses
- Handle HTTP-specific errors

All business logic is delegated to the service layer.
"""

from src.api.handlers import (
    auth_handler,
    content_handler,
    cluster_handler,
    health_handler,
)

__all__ = [
    "auth_handler",
    "content_handler",
    "cluster_handler",
    "health_handler",
]
