"""
Error Handler Middleware

Global exception handling for the API.

Provides consistent error responses across all endpoints by catching
exceptions and converting them to standardized JSON responses.

Error Response Format:
======================
    {
        "error": {
            "code": "NOT_FOUND",
            "message": "User with id 'abc-123' not found",
            "details": {}
        }
    }

Exception Handling:
===================
1. DoraException subclasses → Use their status_code and to_dict()
2. Pydantic ValidationError → 400 with validation details
3. Other exceptions → 500 with generic message (details hidden)

Usage:
======
    from src.api.middleware.error_handler import setup_exception_handlers

    app = FastAPI()
    setup_exception_handlers(app)
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.shared.core.exceptions import DoraException
from src.shared.core.logging import logger


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Set up global exception handlers.

    Should be called during application initialization to register
    exception handlers for all routes.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(DoraException)
    async def dora_exception_handler(
        request: Request,
        exc: DoraException,
    ) -> JSONResponse:
        """
        Handle Dora-specific exceptions.

        All custom exceptions inherit from DoraException and include:
        - status_code: HTTP status code
        - error_code: Machine-readable error code
        - message: Human-readable message
        - details: Additional context
        """
        logger.warning(
            "Application error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors.

        These occur when request body doesn't match the expected schema.
        """
        logger.warning(
            "Validation error",
            errors=exc.errors(),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Handle unexpected exceptions.

        Catches any unhandled exception and returns a generic error.
        Full error details are logged but not exposed to clients.
        """
        logger.error(
            "Unexpected error",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                }
            },
        )
