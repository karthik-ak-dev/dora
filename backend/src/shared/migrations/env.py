# pylint: skip-file
# ruff: noqa
"""
Alembic Environment Configuration

This module configures Alembic for async SQLAlchemy with PostgreSQL.
It supports both online (connected to database) and offline (generating SQL) modes.

Note: This file uses Alembic's runtime proxy pattern (alembic.context, alembic.op)
which are populated at migration runtime and cannot be statically analyzed.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from src.config.settings import settings
from src.shared.models.base import Base

# Import all models to register them with SQLAlchemy's metadata.
# This is REQUIRED for autogenerate to detect model changes.
# Models must be imported before accessing Base.metadata.
from src.shared.models import (
    User,
    SharedContent,
    UserContentSave,
    Cluster,
    ClusterMembership,
    ProcessingJob,
)

# Store model references to ensure they're registered with metadata
REGISTERED_MODELS = (
    User,
    SharedContent,
    UserContentSave,
    Cluster,
    ClusterMembership,
    ProcessingJob,
)

# Alembic Config object - provides access to .ini file values
config = context.config

# Set database URL from settings (not hardcoded in alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This generates SQL statements without connecting to the database.
    Useful for generating migration scripts to review or apply manually.

    Usage:
        alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations using the provided connection.

    This is called by both online sync and async modes.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Compare types to detect column type changes
        compare_type=True,
        # Compare server defaults
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in async mode.

    Creates an async engine and runs migrations within an async context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates a connection to the database and runs migrations.
    Uses asyncio for async SQLAlchemy support.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
