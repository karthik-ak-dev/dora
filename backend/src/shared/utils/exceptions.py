"""
Custom exception classes.
"""


class DoraException(Exception):
    """Base exception for Dora application."""
    pass


class AuthenticationError(DoraException):
    """Authentication failed."""
    pass


class AuthorizationError(DoraException):
    """User not authorized."""
    pass


class ResourceNotFoundError(DoraException):
    """Resource not found."""
    pass


class DuplicateResourceError(DoraException):
    """Resource already exists."""
    pass


class ValidationError(DoraException):
    """Validation failed."""
    pass


class ExternalServiceError(DoraException):
    """External service error."""
    pass
