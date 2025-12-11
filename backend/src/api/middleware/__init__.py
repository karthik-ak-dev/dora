"""
API Middleware

Custom middleware for the FastAPI application.

Components:
===========
- error_handler: Global exception handling
- logging_middleware: Request/response logging
- rate_limiter: Rate limiting (optional)

Usage:
======
    from src.api.middleware import setup_exception_handlers, LoggingMiddleware

    app = FastAPI()
    setup_exception_handlers(app)
    app.add_middleware(LoggingMiddleware)
"""

from src.api.middleware.error_handler import setup_exception_handlers

__all__ = [
    "setup_exception_handlers",
]
