"""Hot memory LRU cache for frequently accessed memories.

Caches individual memory retrievals in Redis DB 3 with 24-hour TTL.
Reduces PostgreSQL + Weaviate roundtrips for popular memories.
Target: 20-30% reduction in database queries.
"""

import os
import hashlib
import json
import logging
from typing import Optional, Dict, Any
import redis

logger = logging.getLogger(__name__)


class MemoryCache:
    """Redis-backed LRU cache for individual memory items.

    Uses Redis DB 3 on acms_redis container (port 40379).
    Cache key format: memory_cache:<memory_id>
    TTL: 24 hours (time-based expiration)

    Example:
        cache = MemoryCache()
        memory = await cache.get("abc-123")
        if not memory:
            memory = await fetch_from_db("abc-123")
            await cache.set("abc-123", memory)
    """

    def __init__(
        self,
        redis_host: str = None,
        redis_port: int = None,
        db: int = 3,
        default_ttl: int = 86400  # 24 hours
    ):
        """Initialize memory cache.

        Args:
            redis_host: Redis server host (default: from REDIS_HOST env or localhost)
            redis_port: Redis server port (default: from REDIS_PORT env or 6379 for Docker, 40379 for local)
            db: Redis database number (3 for memory cache)
            default_ttl: Default TTL in seconds (86400 = 24 hours)
        """
        # Use environment variables for Docker networking
        # Docker: redis:6379, Local: localhost:40379
        if redis_host is None:
            redis_host = os.getenv("REDIS_HOST", "localhost")
        if redis_port is None:
            redis_port = int(os.getenv("REDIS_PORT", "6379"))

        # Create connection pool with proper settings
        pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=db,
            max_connections=50,  # Handle high concurrent load
            socket_connect_timeout=5,
            socket_timeout=5,
            socket_keepalive=True,
            socket_keepalive_options={},
            decode_responses=True
        )

        self.redis = redis.Redis(connection_pool=pool)
        self.default_ttl = default_ttl

        # Test connection
        try:
            self.redis.ping()
            logger.info(f"MemoryCache connected to Redis at {redis_host}:{redis_port} DB{db} (pool: max_connections=50)")
        except redis.ConnectionError as e:
            logger.error(f"MemoryCache failed to connect to Redis: {e}")
            raise

    def _generate_cache_key(self, memory_id: str) -> str:
        """Generate cache key for memory ID.

        Args:
            memory_id: Memory UUID

        Returns:
            str: Cache key in format "memory_cache:<memory_id>"
        """
        return f"memory_cache:{memory_id}"

    async def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get cached memory if exists.

        Args:
            memory_id: Memory UUID

        Returns:
            dict: Cached memory or None if cache miss
        """
        key = self._generate_cache_key(memory_id)

        try:
            cached = self.redis.get(key)

            if cached:
                logger.debug(f"Memory cache HIT for {memory_id}")
                return json.loads(cached)
            else:
                logger.debug(f"Memory cache MISS for {memory_id}")
                return None

        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting from memory cache: {e}")
            return None

    async def set(
        self,
        memory_id: str,
        memory_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Store memory in cache.

        Args:
            memory_id: Memory UUID
            memory_data: Memory dict to cache
            ttl: Optional custom TTL in seconds (uses default if None)

        Returns:
            bool: True if stored successfully, False otherwise
        """
        key = self._generate_cache_key(memory_id)
        ttl = ttl or self.default_ttl

        try:
            # Store with TTL
            self.redis.setex(
                key,
                ttl,
                json.dumps(memory_data)
            )
            logger.debug(f"Cached memory {memory_id} (TTL: {ttl}s)")
            return True

        except (redis.RedisError, TypeError) as e:
            logger.error(f"Error setting memory cache: {e}")
            return False

    async def delete(self, memory_id: str) -> bool:
        """Delete memory from cache (e.g., after update/delete).

        Args:
            memory_id: Memory UUID

        Returns:
            bool: True if deleted, False otherwise
        """
        key = self._generate_cache_key(memory_id)

        try:
            deleted = self.redis.delete(key)
            if deleted:
                logger.debug(f"Deleted memory {memory_id} from cache")
            return bool(deleted)
        except redis.RedisError as e:
            logger.error(f"Error deleting from memory cache: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            dict: Cache statistics including:
                - total_cached_memories: Number of cached memories
                - redis_memory_usage: Memory used by Redis
        """
        try:
            # Count cached memories
            keys = self.redis.keys("memory_cache:*")
            total_cached = len(keys)

            # Get Redis memory info
            memory_info = self.redis.info("memory")
            memory_usage = memory_info.get("used_memory_human", "unknown")

            stats = {
                "total_cached_memories": total_cached,
                "redis_memory_usage": memory_usage,
                "redis_db": 3,
                "default_ttl_seconds": self.default_ttl
            }

            logger.debug(f"Memory cache stats: {stats}")
            return stats

        except redis.RedisError as e:
            logger.error(f"Error getting memory cache stats: {e}")
            return {
                "error": str(e),
                "total_cached_memories": 0
            }

    def clear_all(self) -> int:
        """Clear all cached memories (use with caution).

        Returns:
            int: Number of keys deleted
        """
        try:
            keys = self.redis.keys("memory_cache:*")
            if keys:
                deleted = self.redis.delete(*keys)
                logger.warning(f"Cleared {deleted} cached memories")
                return deleted
            return 0

        except redis.RedisError as e:
            logger.error(f"Error clearing memory cache: {e}")
            return 0


# Global cache instance (initialized in api_server.py)
_memory_cache_instance = None


def get_memory_cache() -> MemoryCache:
    """Get global memory cache instance.

    Returns:
        MemoryCache: Global cache instance

    Raises:
        RuntimeError: If cache not initialized
    """
    global _memory_cache_instance
    if _memory_cache_instance is None:
        _memory_cache_instance = MemoryCache()
    return _memory_cache_instance
