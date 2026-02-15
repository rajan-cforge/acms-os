"""Query result caching for /ask endpoint.

Caches query → answer mappings in Redis with 1-hour TTL.
Target: 40-60% cache hit rate, 30-50% cost reduction.
"""

import os
import hashlib
import json
import logging
from typing import Optional, Dict, Any, List
import redis

logger = logging.getLogger(__name__)


class QueryCache:
    """Redis-backed cache for /ask endpoint query results.

    Uses Redis DB 2 on acms_redis container (port 40379).
    Cache key format: query_cache:<sha256_hash>
    TTL: 1 hour (time-based invalidation only)

    Example:
        cache = QueryCache()
        result = await cache.get("What is ACMS?", 5, ["PUBLIC"])
        if not result:
            result = await generate_answer(...)
            await cache.set("What is ACMS?", 5, ["PUBLIC"], result)
    """

    def __init__(
        self,
        redis_host: str = None,
        redis_port: int = None,
        db: int = 2,
        default_ttl: int = 3600  # 1 hour
    ):
        """Initialize query cache.

        Args:
            redis_host: Redis server host (default: from REDIS_HOST env or localhost)
            redis_port: Redis server port (default: from REDIS_PORT env or 6379 for Docker, 40379 for local)
            db: Redis database number (2 for query cache)
            default_ttl: Default TTL in seconds (3600 = 1 hour)
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
            logger.info(f"QueryCache connected to Redis at {redis_host}:{redis_port} DB{db} (pool: max_connections=50)")
        except redis.ConnectionError as e:
            logger.error(f"QueryCache failed to connect to Redis: {e}")
            raise

    def _generate_cache_key(
        self,
        query: str,
        context_limit: int,
        privacy_filter: List[str]
    ) -> str:
        """Generate unique cache key from query parameters.

        Args:
            query: User question
            context_limit: Number of memories to retrieve
            privacy_filter: List of privacy levels (e.g., ["PUBLIC", "INTERNAL"])

        Returns:
            str: Cache key in format "query_cache:<hash>"
        """
        # Normalize privacy filter (sort for consistent hashing)
        normalized_privacy = ','.join(sorted(privacy_filter))

        # Create cache input string
        cache_input = f"{query.lower().strip()}|{context_limit}|{normalized_privacy}"

        # Hash with SHA256
        cache_hash = hashlib.sha256(cache_input.encode('utf-8')).hexdigest()

        return f"query_cache:{cache_hash}"

    async def get(
        self,
        query: str,
        context_limit: int,
        privacy_filter: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get cached query result if exists.

        Args:
            query: User question
            context_limit: Number of memories to retrieve
            privacy_filter: List of privacy levels

        Returns:
            dict: Cached result or None if cache miss
        """
        key = self._generate_cache_key(query, context_limit, privacy_filter)

        try:
            cached = self.redis.get(key)

            if cached:
                logger.info(f"Cache HIT for query: {query[:50]}...")
                return json.loads(cached)
            else:
                logger.info(f"Cache MISS for query: {query[:50]}...")
                return None

        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting from cache: {e}")
            return None

    async def set(
        self,
        query: str,
        context_limit: int,
        privacy_filter: List[str],
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Store query result in cache.

        Args:
            query: User question
            context_limit: Number of memories to retrieve
            privacy_filter: List of privacy levels
            result: Query result to cache (answer, sources, confidence)
            ttl: Optional custom TTL in seconds (uses default if None)

        Returns:
            bool: True if stored successfully, False otherwise
        """
        key = self._generate_cache_key(query, context_limit, privacy_filter)
        ttl = ttl or self.default_ttl

        try:
            # Store with TTL
            self.redis.setex(
                key,
                ttl,
                json.dumps(result)
            )
            logger.info(f"Cached query result for: {query[:50]}... (TTL: {ttl}s)")
            return True

        except (redis.RedisError, TypeError) as e:
            logger.error(f"Error setting cache: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            dict: Cache statistics including:
                - total_cached_queries: Number of cached query results
                - redis_memory_usage: Memory used by Redis
                - cache_hit_rate: Estimated cache hit rate (if tracked)
        """
        try:
            # Count cached queries
            keys = self.redis.keys("query_cache:*")
            total_cached = len(keys)

            # Get Redis memory info
            memory_info = self.redis.info("memory")
            memory_usage = memory_info.get("used_memory_human", "unknown")

            stats = {
                "total_cached_queries": total_cached,
                "redis_memory_usage": memory_usage,
                "redis_db": 2,
                "default_ttl_seconds": self.default_ttl
            }

            logger.debug(f"Cache stats: {stats}")
            return stats

        except redis.RedisError as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "error": str(e),
                "total_cached_queries": 0
            }

    def clear_all(self) -> int:
        """Clear all cached queries (use with caution).

        Returns:
            int: Number of keys deleted
        """
        try:
            keys = self.redis.keys("query_cache:*")
            if keys:
                deleted = self.redis.delete(*keys)
                logger.warning(f"Cleared {deleted} cached queries")
                return deleted
            return 0

        except redis.RedisError as e:
            logger.error(f"Error clearing cache: {e}")
            return 0


# Global cache instance (initialized in api_server.py)
_query_cache_instance = None


def get_query_cache() -> QueryCache:
    """Get global query cache instance.

    Returns:
        QueryCache: Global cache instance

    Raises:
        RuntimeError: If cache not initialized
    """
    global _query_cache_instance
    if _query_cache_instance is None:
        _query_cache_instance = QueryCache()
    return _query_cache_instance
