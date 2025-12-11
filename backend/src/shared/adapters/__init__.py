"""
Adapters Package

External service integrations.

Contents:
=========
- openai_adapter: OpenAI API client
- redis_adapter: Redis cache client
- sqs_adapter: AWS SQS queue client
- storage: File storage (S3, etc.)
- vector_db: Qdrant vector database client

Note: Database access is handled by shared/db/session.py using async SQLAlchemy.

Usage:
======
    from src.shared.adapters.openai_adapter import OpenAIAdapter
    from src.shared.adapters.redis_adapter import RedisAdapter
"""
