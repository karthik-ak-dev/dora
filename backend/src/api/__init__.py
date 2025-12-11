"""
API Module

FastAPI application and route handlers.

Package Structure:
==================
    api/
    ├── main.py           ← Application entry point
    ├── routes.py         ← Route registration
    ├── dependencies/     ← FastAPI dependencies
    ├── handlers/         ← Route handlers
    └── middleware/       ← Custom middleware

Usage:
======
    # Run the API
    uvicorn src.api.main:app --reload

    # Import the app
    from src.api.main import app, create_application
"""
