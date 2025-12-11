"""
URL service - URL normalization and validation.
"""

import hashlib
from urllib.parse import urlparse, parse_qs, urlunparse
from typing import Tuple

from ..models.enums import SourcePlatform


class URLService:
    """Service for URL operations."""

    TRACKING_PARAMS = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
    }

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL for deduplication.
        - Convert to lowercase
        - Remove tracking parameters
        - Standardize to HTTPS
        - Remove trailing slashes and fragments
        """
        parsed = urlparse(url.lower())

        # Remove tracking parameters
        query_params = parse_qs(parsed.query)
        clean_params = {
            k: v for k, v in query_params.items() if k not in URLService.TRACKING_PARAMS
        }
        clean_query = "&".join(f"{k}={v[0]}" for k, v in clean_params.items())

        # Rebuild URL
        normalized = urlunparse(
            (
                "https",  # Force HTTPS
                parsed.netloc.replace("www.", ""),  # Remove www
                parsed.path.rstrip("/"),  # Remove trailing slash
                "",  # params
                clean_query,
                "",  # fragment
            )
        )

        return normalized

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """Generate SHA256 hash of normalized URL."""
        normalized = URLService.normalize_url(url)
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def detect_platform(url: str) -> SourcePlatform:
        """Detect platform from URL."""
        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace("www.", "")

        if "instagram.com" in domain:
            return SourcePlatform.INSTAGRAM
        if "youtube.com" in domain or "youtu.be" in domain:
            return SourcePlatform.YOUTUBE
        return SourcePlatform.UNKNOWN

    @staticmethod
    def validate_and_process(url: str) -> Tuple[str, str, SourcePlatform]:
        """
        Validate and process URL.
        Returns: (normalized_url, url_hash, platform)
        """
        normalized = URLService.normalize_url(url)
        url_hash = URLService.generate_url_hash(url)
        platform = URLService.detect_platform(url)

        return normalized, url_hash, platform
