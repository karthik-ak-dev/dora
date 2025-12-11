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


class ContentCategory(str, Enum):
    """
    Unified content categorization.

    This is the AUTHORITATIVE classification for all content.
    Applied at content processing time (not user-dependent).
    Used by both SharedContent and Cluster entities.

    Content is classified into exactly ONE category during AI analysis.
    Clusters are then created WITHIN each category for finer groupings.
    """

    TRAVEL = "Travel"
    FOOD = "Food"
    LEARNING = "Learning"
    CAREER = "Career"
    FITNESS = "Fitness"
    ENTERTAINMENT = "Entertainment"
    SHOPPING = "Shopping"
    TECH = "Tech"
    LIFESTYLE = "Lifestyle"
    MISC = "Misc"


# Backwards compatibility aliases
CategoryHighLevel = ContentCategory
ClusterType = ContentCategory


class IntentType(str, Enum):
    """Likely intent behind content."""

    LEARN = "learn"
    VISIT = "visit"
    BUY = "buy"
    TRY = "try"
    WATCH = "watch"
    MISC = "misc"
