"""
Configuration Module

Application configuration loaded from environment variables.

Usage:
======
    from src.config.settings import settings

    db_url = settings.DATABASE_URL
    is_dev = settings.is_development
"""

from src.config.settings import settings, get_settings, Settings

__all__ = [
    "settings",
    "get_settings",
    "Settings",
]
