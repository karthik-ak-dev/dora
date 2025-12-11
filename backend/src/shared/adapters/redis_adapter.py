"""
Redis adapter - Caching and rate limiting.

Provides:
- Key-value caching with TTL
- Rate limiting support
- Distributed locking
"""

import functools
import json
import logging
from typing import Optional, Any, Dict

import redis
from redis.exceptions import RedisError

from ...config.settings import settings

logger = logging.getLogger(__name__)


class RedisAdapter:
    """
    Adapter for Redis operations.

    Handles:
    - Caching with TTL
    - Rate limiting
    - Distributed locks
    """

    def __init__(self, url: Optional[str] = None):
        """
        Initialize Redis adapter.

        Args:
            url: Redis URL (redis://host:port/db)
        """
        self.url = url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        """Lazy-loaded Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.url,
                decode_responses=True,
            )
        return self._client

    def get(self, key: str) -> Optional[str]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            return self.client.get(key)
        except RedisError as e:
            logger.warning("Redis get failed for %s: %s", key, e)
            return None

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a JSON value from cache.

        Args:
            key: Cache key

        Returns:
            Parsed JSON or None
        """
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        try:
            if ttl:
                self.client.setex(key, ttl, value)
            else:
                self.client.set(key, value)
            return True
        except RedisError as e:
            logger.warning("Redis set failed for %s: %s", key, e)
            return False

    def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set a JSON value in cache.

        Args:
            key: Cache key
            value: Dict to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        return self.set(key, json.dumps(value), ttl)

    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted
        """
        try:
            return bool(self.client.delete(key))
        except RedisError as e:
            logger.warning("Redis delete failed for %s: %s", key, e)
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        try:
            return bool(self.client.exists(key))
        except RedisError as e:
            logger.warning("Redis exists failed for %s: %s", key, e)
            return False

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a counter.

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New counter value or None
        """
        try:
            return self.client.incrby(key, amount)
        except RedisError as e:
            logger.warning("Redis incr failed for %s: %s", key, e)
            return None

    def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiry on a key.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        try:
            return bool(self.client.expire(key, ttl))
        except RedisError as e:
            logger.warning("Redis expire failed for %s: %s", key, e)
            return False

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window.

        Args:
            key: Rate limit key (e.g., "rate:user:123")
            limit: Maximum allowed requests
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, current_count)
        """
        try:
            current = self.incr(key)
            if current is None:
                return True, 0

            if current == 1:
                self.expire(key, window_seconds)

            return current <= limit, current

        except RedisError as e:
            logger.warning("Rate limit check failed for %s: %s", key, e)
            return True, 0  # Allow on error

    def acquire_lock(
        self,
        key: str,
        ttl: int = 30,
    ) -> bool:
        """
        Acquire a distributed lock.

        Args:
            key: Lock key
            ttl: Lock timeout in seconds

        Returns:
            True if lock acquired
        """
        try:
            return bool(self.client.set(f"lock:{key}", "1", nx=True, ex=ttl))
        except RedisError as e:
            logger.warning("Lock acquisition failed for %s: %s", key, e)
            return False

    def release_lock(self, key: str) -> bool:
        """
        Release a distributed lock.

        Args:
            key: Lock key

        Returns:
            True if released
        """
        return self.delete(f"lock:{key}")

    def cache_content_embedding(
        self,
        content_id: str,
        embedding: list,
        ttl: int = 3600,
    ) -> bool:
        """
        Cache a content embedding.

        Args:
            content_id: SharedContent ID
            embedding: Embedding vector
            ttl: Cache TTL

        Returns:
            True if cached
        """
        key = f"embedding:{content_id}"
        return self.set_json(key, {"embedding": embedding}, ttl)

    def get_cached_embedding(self, content_id: str) -> Optional[list]:
        """
        Get a cached content embedding.

        Args:
            content_id: SharedContent ID

        Returns:
            Embedding vector or None
        """
        key = f"embedding:{content_id}"
        data = self.get_json(key)
        if data:
            return data.get("embedding")
        return None

    def ping(self) -> bool:
        """
        Check Redis connectivity.

        Returns:
            True if connected
        """
        try:
            return self.client.ping()
        except RedisError:
            return False


@functools.lru_cache(maxsize=1)
def get_redis_adapter() -> RedisAdapter:
    """Get or create Redis adapter singleton."""
    return RedisAdapter()
