"""
Dora Backend

AI-Powered Second Brain for Content.

Package Structure:
==================
    src/
    ├── api/        ← FastAPI application
    ├── worker/     ← Background job processor
    ├── shared/     ← Shared code (models, services, etc.)
    └── config/     ← Configuration

Running the Application:
========================
    # API Server
    uvicorn src.api.main:app --reload

    # Worker
    python -m src.worker.main
"""
