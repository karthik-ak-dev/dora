"""
Base scraper interface.
"""


class BaseScraper:
    """Base interface for content scrapers."""

    def scrape(self, url: str) -> dict:
        """
        Scrape content from URL.
        Returns dict with metadata.
        """
        raise NotImplementedError
