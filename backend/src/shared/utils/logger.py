"""
Structured logging configuration.
"""
import logging
import sys
from typing import Any


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup structured JSON logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '{"level": "%(levelname)s", "timestamp": "%(asctime)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
