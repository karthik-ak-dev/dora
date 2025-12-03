"""
Enums used across the application.
"""
from enum import Enum


class SourcePlatform(str, Enum):
    """Platform where content originated."""
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    UNKNOWN = "unknown"


class ItemStatus(str, Enum):
    """Processing lifecycle state."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class CategoryHighLevel(str, Enum):
    """High-level content categorization."""
    TRAVEL = "Travel"
    FOOD_DRINK = "Food & Drink"
    LEARNING = "Learning"
    CAREER = "Career"
    FITNESS = "Fitness"
    ENTERTAINMENT = "Entertainment"
    SHOPPING = "Shopping"
    TECH = "Tech"
    MISC = "Misc"


class IntentType(str, Enum):
    """Likely intent behind content."""
    LEARN = "learn"
    VISIT = "visit"
    BUY = "buy"
    TRY = "try"
    WATCH = "watch"
    MISC = "misc"


class ClusterType(str, Enum):
    """Cluster categorization."""
    TRAVEL = "Travel"
    FOOD = "Food"
    LEARNING = "Learning"
    FITNESS = "Fitness"
    ENTERTAINMENT = "Entertainment"
    SHOPPING = "Shopping"
    TECH = "Tech"
    MISC = "Misc"
