"""
Custom Exceptions

Application-specific exceptions with HTTP status codes and error codes.

Exception Hierarchy:
====================
    DoraException (base)
       │
       ├── AuthenticationError (401)    ← Invalid credentials, token expired
       ├── AuthorizationError (403)     ← Access denied, insufficient permissions
       ├── NotFoundError (404)          ← Resource not found
       │      ├── UserNotFoundError
       │      ├── ContentNotFoundError
       │      └── ClusterNotFoundError
       ├── ValidationError (400)        ← Invalid input data
       ├── ConflictError (409)          ← Resource already exists
       ├── RateLimitError (429)         ← Too many requests
       └── ServiceUnavailableError (503) ← External service down

Usage:
======
    from src.shared.core.exceptions import NotFoundError, ValidationError

    # Raise with automatic status code
    raise NotFoundError("User", user_id)
    # Results in: {"error": {"code": "NOT_FOUND", "message": "User with id 'abc' not found"}}

    # Raise with additional details
    raise ValidationError("Invalid email format", details={"field": "email"})

Exception Handling:
===================
    Exceptions are caught by the error handler middleware and converted to JSON:
    {
        "error": {
            "code": "NOT_FOUND",
            "message": "User with id 'abc-123' not found",
            "details": {}
        }
    }
"""

from typing import Any, Optional


class DoraException(Exception):
    """
    Base exception for all Dora application errors.

    All custom exceptions inherit from this class, providing:
    - HTTP status code mapping
    - Error code for programmatic handling
    - Optional details dictionary
    - Consistent JSON serialization

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default 500)
        error_code: Machine-readable error code
        details: Additional error context

    Example:
        raise DoraException(
            message="Something went wrong",
            status_code=400,
            error_code="BAD_REQUEST",
            details={"field": "email"}
        )
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary for API response.

        Returns:
            Dictionary with error details for JSON response
        """
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION & AUTHORIZATION ERRORS (401, 403)
# ═══════════════════════════════════════════════════════════════════════════════


class AuthenticationError(DoraException):
    """
    Authentication failed error (401 Unauthorized).

    Raised when:
    - Missing or invalid credentials
    - Token expired or malformed
    - Invalid API key
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(DoraException):
    """
    Authorization failed error (403 Forbidden).

    Raised when user is authenticated but lacks permission.
    """

    def __init__(
        self,
        message: str = "Access denied",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# NOT FOUND ERRORS (404)
# ═══════════════════════════════════════════════════════════════════════════════


class NotFoundError(DoraException):
    """
    Resource not found error (404 Not Found).

    Base class for all "not found" errors with automatic message formatting.

    Example:
        raise NotFoundError("User", user_id)
        # Message: "User with id 'abc-123' not found"
    """

    def __init__(
        self,
        resource: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details,
        )


class UserNotFoundError(NotFoundError):
    """User not found error."""

    def __init__(self, user_id: str) -> None:
        super().__init__(resource="User", resource_id=user_id)


class ContentNotFoundError(NotFoundError):
    """Content not found error."""

    def __init__(self, content_id: str) -> None:
        super().__init__(resource="Content", resource_id=content_id)


class SaveNotFoundError(NotFoundError):
    """User content save not found error."""

    def __init__(self, save_id: str) -> None:
        super().__init__(resource="Save", resource_id=save_id)


class ClusterNotFoundError(NotFoundError):
    """Cluster not found error."""

    def __init__(self, cluster_id: str) -> None:
        super().__init__(resource="Cluster", resource_id=cluster_id)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION & CONFLICT ERRORS (400, 409)
# ═══════════════════════════════════════════════════════════════════════════════


class ValidationError(DoraException):
    """
    Validation error (400 Bad Request).

    Raised when input data fails validation.
    """

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class ConflictError(DoraException):
    """
    Resource conflict error (409 Conflict).

    Raised when operation conflicts with existing resource.

    Example:
        raise ConflictError("Email already registered")
    """

    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details,
        )


class DuplicateResourceError(ConflictError):
    """
    Duplicate resource error.

    Specific case of conflict when trying to create duplicate resource.
    """

    def __init__(
        self,
        message: str = "Resource already exists",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, details=details)


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING & SERVICE ERRORS (429, 503)
# ═══════════════════════════════════════════════════════════════════════════════


class RateLimitError(DoraException):
    """
    Rate limit exceeded error (429 Too Many Requests).

    Includes retry_after hint for clients.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        extra_details = details or {}
        if retry_after:
            extra_details["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=extra_details,
        )


class ServiceUnavailableError(DoraException):
    """
    Service temporarily unavailable error (503).

    Raised when external services (OpenAI, Qdrant, etc.) are down.
    """

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details=details,
        )


class ExternalServiceError(ServiceUnavailableError):
    """
    External service error.

    More specific error for external API failures.
    """

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        msg = message or f"{service_name} service error"
        extra_details = details or {}
        extra_details["service"] = service_name
        super().__init__(message=msg, details=extra_details)
