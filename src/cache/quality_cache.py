"""
Quality-Gated Cache - Only stores verified, high-quality responses.

Key differences from old SemanticCache (disabled Nov 2025):
1. Tracks agent_used - prevents wrong-agent serving
2. Tracks contains_web_search - prevents stale web data
3. Tiered TTL based on query type
4. Only caches after positive feedback + user verification
5. Only caches PUBLIC/INTERNAL (never CONFIDENTIAL/LOCAL_ONLY)

Part of Active Second Brain implementation (Jan 2026).
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Dict, Any, List

from src.storage.weaviate_client import WeaviateClient
from src.embeddings import get_embeddings

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Query types with different cache TTLs."""
    DEFINITION = "definition"   # "What is X?" - 7 day TTL
    FACTUAL = "factual"         # "How does X work?" - 24hr TTL
    TEMPORAL = "temporal"       # "What happened today?" - NO CACHE
    CREATIVE = "creative"       # "Write a poem" - NO CACHE
    CODE = "code"               # "Write function" - 24hr TTL


def detect_query_type(query: str) -> QueryType:
    """
    Detect query type for TTL calculation.

    Args:
        query: User's query text

    Returns:
        QueryType enum value
    """
    query_lower = query.lower().strip()

    # Definition patterns
    definition_patterns = [
        r'^what is\b',
        r'^what are\b',
        r'^define\b',
        r'\bstand for\b',
        r'^explain what\b',
        r'^tell me about\b',
    ]
    for pattern in definition_patterns:
        if re.search(pattern, query_lower):
            return QueryType.DEFINITION

    # Temporal patterns (never cache)
    temporal_patterns = [
        r'\btoday\b',
        r'\byesterday\b',
        r'\bcurrent\b',
        r'\blatest\b',
        r'\brecent\b',
        r'\bnow\b',
        r'\bthis week\b',
        r'\bthis month\b',
        r'\bright now\b',
        r'\bprice of\b',
    ]
    for pattern in temporal_patterns:
        if re.search(pattern, query_lower):
            return QueryType.TEMPORAL

    # Creative patterns (never cache)
    creative_patterns = [
        r'^write a (poem|story|song|essay)',
        r'^create a (story|poem|narrative)',
        r'^compose\b',
        r'^generate a creative\b',
    ]
    for pattern in creative_patterns:
        if re.search(pattern, query_lower):
            return QueryType.CREATIVE

    # Code patterns
    code_patterns = [
        r'\bwrite a? ?(python |javascript |)?(function|method|class|code|script)\b',
        r'\bimplement\b',
        r'\bcode (for|to|that)\b',
        r'\b(python|javascript|java|go|rust|typescript) (function|class|method)\b',
        r'\bhow (do i|to) (write|create|implement|code)\b',
    ]
    for pattern in code_patterns:
        if re.search(pattern, query_lower):
            return QueryType.CODE

    # Default to factual
    return QueryType.FACTUAL


@dataclass
class CacheEntry:
    """
    Enhanced cache entry with quality signals.

    Tracks agent, web search, feedback counts for intelligent caching.
    """
    query_text: str
    response: str
    agent_used: str              # claude/chatgpt/gemini/ollama
    contains_web_search: bool    # Did this use web search?
    query_type: QueryType        # For TTL calculation
    confidence: float            # AI extraction confidence
    user_verified: bool          # Did user click "verify"?
    positive_feedback_count: int # How many 👍
    negative_feedback_count: int # How many 👎
    user_id: str                 # Privacy isolation
    created_at: datetime
    last_served: datetime
    serve_count: int
    privacy_level: str           # PUBLIC/INTERNAL/CONFIDENTIAL/LOCAL_ONLY

    @property
    def quality_score(self) -> float:
        """
        Calculate quality score for cache ranking.

        Score based on:
        - Base confidence
        - User verification bonus (+0.1)
        - Positive feedback bonus (+0.02 per 👍, max +0.1)
        - Negative feedback penalty (>2 👎 = 0 score)

        Returns:
            float: Quality score 0.0 to 1.0
        """
        # Too many downvotes = zero quality
        if self.negative_feedback_count > 2:
            return 0.0

        base = self.confidence

        # Verification bonus
        if self.user_verified:
            base += 0.1

        # Positive feedback bonus (capped at +0.1)
        if self.positive_feedback_count > 0:
            base += min(self.positive_feedback_count * 0.02, 0.1)

        return min(base, 1.0)

    @property
    def ttl_hours(self) -> int:
        """
        Get TTL based on query type and web search flag.

        Web search results have short TTL (1 hour) to avoid stale data.

        Returns:
            int: TTL in hours (0 = never cache)
        """
        # Web search = always short TTL
        if self.contains_web_search:
            return 1

        # Query type based TTL
        ttl_map = {
            QueryType.DEFINITION: 168,  # 7 days
            QueryType.FACTUAL: 24,
            QueryType.CODE: 24,
            QueryType.TEMPORAL: 0,      # Never cache
            QueryType.CREATIVE: 0,      # Never cache
        }
        return ttl_map.get(self.query_type, 24)

    def is_valid_for_request(self, requested_agent: Optional[str]) -> bool:
        """
        Check if this cache entry is valid for the current request.

        Validates:
        - Quality score >= 0.5
        - Agent matches (or request is "auto")
        - Entry not expired

        Args:
            requested_agent: Agent user requested (None/"auto" = any)

        Returns:
            bool: True if valid for serving
        """
        # Quality check
        if self.quality_score < 0.5:
            return False

        # Agent check (only if specific agent requested)
        if requested_agent and requested_agent not in (None, "auto"):
            if self.agent_used != requested_agent:
                return False

        # Expiry check
        age_hours = (datetime.now(timezone.utc) - self.created_at).total_seconds() / 3600
        if age_hours > self.ttl_hours:
            return False

        return True


class QualityCache:
    """
    Quality-gated semantic cache.

    Only stores verified, high-quality responses.
    Prevents serving wrong agent responses or stale web data.
    """

    SIMILARITY_THRESHOLD = 0.95  # Stricter than old 0.90
    COLLECTION_NAME = "ACMS_QualityCache_v1"
    MAX_ENTRIES = 10000

    def __init__(self):
        """Initialize quality cache."""
        self.weaviate = WeaviateClient()
        self.embeddings = get_embeddings()
        self.collection_name = self.COLLECTION_NAME

        # Stats tracking
        self._hits = 0
        self._misses = 0

        # Ensure collection exists
        self._ensure_collection()

        logger.info(
            f"QualityCache initialized: {self.collection_name} "
            f"(threshold={self.SIMILARITY_THRESHOLD})"
        )

    def _ensure_collection(self):
        """Create Weaviate collection if it doesn't exist."""
        if self.weaviate.collection_exists(self.collection_name):
            logger.debug(f"Collection {self.collection_name} already exists")
            return

        from weaviate.classes.config import Configure, Property, DataType, VectorDistances

        try:
            self.weaviate._client.collections.create(
                name=self.collection_name,
                description="Quality-gated semantic cache for verified responses",
                vectorizer_config=None,  # Manual vectors from OpenAI
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE
                ),
                properties=[
                    Property(name="query_text", data_type=DataType.TEXT),
                    Property(name="response", data_type=DataType.TEXT),
                    Property(name="agent_used", data_type=DataType.TEXT),
                    Property(name="contains_web_search", data_type=DataType.BOOL),
                    Property(name="query_type", data_type=DataType.TEXT),
                    Property(name="confidence", data_type=DataType.NUMBER),
                    Property(name="user_verified", data_type=DataType.BOOL),
                    Property(name="positive_feedback_count", data_type=DataType.INT),
                    Property(name="negative_feedback_count", data_type=DataType.INT),
                    Property(name="user_id", data_type=DataType.TEXT),
                    Property(name="created_at", data_type=DataType.DATE),
                    Property(name="last_served", data_type=DataType.DATE),
                    Property(name="serve_count", data_type=DataType.INT),
                    Property(name="privacy_level", data_type=DataType.TEXT),
                    Property(name="original_query_id", data_type=DataType.TEXT),
                ],
            )
            logger.info(f"Created collection {self.collection_name}")
        except Exception as e:
            logger.warning(f"Could not create collection: {e}")

    async def get(
        self,
        query: str,
        user_id: str,
        requested_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and valid.

        Cache HIT conditions:
        1. Similarity >= 0.95 (strict)
        2. Same user_id (privacy)
        3. Agent matches request (or request is "auto")
        4. Quality score >= 0.5
        5. Not expired (TTL based on query type)

        Args:
            query: User's query
            user_id: User ID for privacy isolation
            requested_agent: Specific agent requested (None/"auto" = any)

        Returns:
            Dict with cached response or None for cache miss
        """
        try:
            # Generate embedding for query
            embedding = self.embeddings.generate_embedding(query)

            # Search for similar queries
            results = self.weaviate.semantic_search(
                collection=self.collection_name,
                query_vector=embedding,
                limit=1,
            )

            if not results:
                self._misses += 1
                logger.debug("QualityCache MISS: No similar queries")
                return None

            match = results[0]
            similarity = 1 - match["distance"]  # Distance to similarity
            props = match["properties"]

            # Check similarity threshold
            if similarity < self.SIMILARITY_THRESHOLD:
                self._misses += 1
                logger.debug(f"QualityCache MISS: Similarity {similarity:.3f} < {self.SIMILARITY_THRESHOLD}")
                return None

            # Check user match (privacy)
            if props.get("user_id") != user_id:
                self._misses += 1
                logger.debug("QualityCache MISS: Different user")
                return None

            # Build cache entry to check validity
            entry = self._props_to_entry(props)

            # Check agent match
            if not entry.is_valid_for_request(requested_agent):
                self._misses += 1
                reason = "agent mismatch" if requested_agent else "invalid entry"
                logger.debug(f"QualityCache MISS: {reason}")
                return None

            # Cache HIT!
            self._hits += 1
            logger.info(
                f"QualityCache HIT: similarity={similarity:.3f}, "
                f"agent={entry.agent_used}, verified={entry.user_verified}"
            )

            return {
                "response": entry.response,
                "from_cache": True,
                "cache_type": "quality",
                "cache_similarity": similarity,
                "original_query": entry.query_text,
                "agent_used": entry.agent_used,
                "user_verified": entry.user_verified,
                "confidence": entry.confidence,
            }

        except Exception as e:
            logger.error(f"QualityCache error: {e}", exc_info=True)
            self._misses += 1
            return None

    async def promote_to_cache(
        self,
        query_history_id: str,
        user_id: str
    ) -> bool:
        """
        Promote a query to cache after positive feedback.

        Called when user gives 👍 AND clicks "Save as verified".

        Args:
            query_history_id: ID of the query_history record
            user_id: User ID

        Returns:
            bool: True if promoted successfully
        """
        try:
            # Get query history record
            query_record = await get_query_history_by_id(query_history_id)
            if not query_record:
                logger.warning(f"Query history not found: {query_history_id}")
                return False

            # Check privacy level - never cache CONFIDENTIAL/LOCAL_ONLY
            privacy = query_record.get("privacy_level", "PUBLIC")
            if privacy in ("CONFIDENTIAL", "LOCAL_ONLY"):
                logger.info(f"Not caching {privacy} response")
                return False

            # Generate embedding
            query_text = query_record["query"]
            embedding = self.embeddings.generate_embedding(query_text)

            # Detect query type
            query_type = detect_query_type(query_text)

            # Build cache entry data
            data = {
                "query_text": query_text,
                "response": query_record["response"],
                "agent_used": query_record.get("response_source", "unknown"),
                "contains_web_search": query_record.get("contains_web_search", False),
                "query_type": query_type.value,
                "confidence": query_record.get("confidence", 0.9),
                "user_verified": True,  # User explicitly verified
                "positive_feedback_count": 1,
                "negative_feedback_count": 0,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                "last_served": datetime.now(timezone.utc),
                "serve_count": 0,
                "privacy_level": privacy,
                "original_query_id": query_history_id,
            }

            # Insert into Weaviate
            vector_id = self.weaviate.insert_vector(
                collection=self.collection_name,
                vector=embedding,
                data=data,
            )

            logger.info(f"Promoted to QualityCache: {vector_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to promote to cache: {e}", exc_info=True)
            return False

    async def demote_from_cache(
        self,
        cache_entry_id: str,
        reason: str,
        enable_propagation: bool = True
    ) -> bool:
        """
        Demote/remove entry after negative feedback.

        Increments negative_feedback_count. If count > 2, deletes entry
        and triggers propagated forgetting to flag related knowledge.

        Cognitive Principle: Active Forgetting.
        When a memory is corrected, related memories may also be inconsistent.
        The hippocampus uses this principle to maintain memory integrity.

        Args:
            cache_entry_id: Weaviate object ID
            reason: Reason for demotion (incorrect/outdated/etc)
            enable_propagation: Whether to flag related knowledge (default True)

        Returns:
            bool: True if demoted successfully
        """
        try:
            # Get current entry
            entry_data = self.weaviate.get_by_id(self.collection_name, cache_entry_id)
            if not entry_data:
                logger.warning(f"Cache entry not found: {cache_entry_id}")
                return False

            current_negative = entry_data.get("negative_feedback_count", 0)
            new_negative = current_negative + 1

            # If too many downvotes, delete the entry and propagate
            if new_negative > 2:
                self.weaviate.delete_by_id(self.collection_name, cache_entry_id)
                logger.info(f"Deleted cache entry {cache_entry_id} (too many downvotes)")

                # Propagate forgetting to related knowledge entries
                if enable_propagation:
                    await self.propagated_forget(
                        source_entry_id=cache_entry_id,
                        source_collection="ACMS_QualityCache_v1",
                        reason=reason,
                        entry_data=entry_data
                    )

                return True

            # Otherwise, increment the count
            self.weaviate.update_properties(
                self.collection_name,
                cache_entry_id,
                {"negative_feedback_count": new_negative}
            )
            logger.info(f"Demoted cache entry {cache_entry_id}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Failed to demote cache entry: {e}", exc_info=True)
            return False

    async def propagated_forget(
        self,
        source_entry_id: str,
        source_collection: str,
        reason: str,
        entry_data: Dict[str, Any]
    ) -> int:
        """
        Propagate forgetting to related knowledge entries.

        Cognitive Principle: Active Forgetting.
        When the hippocampus determines a memory is unreliable, it triggers
        a cascade of re-evaluation for semantically related memories.

        This method:
        1. Finds knowledge entries with similar embeddings to the deleted cache entry
        2. Flags them in the knowledge_review_queue for human review
        3. Does NOT delete them - humans must approve corrections

        Args:
            source_entry_id: ID of the deleted cache entry
            source_collection: Collection the deletion came from
            reason: Reason for the original deletion
            entry_data: Properties of the deleted entry (for embedding lookup)

        Returns:
            int: Number of knowledge entries flagged for review
        """
        from src.storage.knowledge_review_crud import flag_related_knowledge_for_review

        flagged_count = 0

        try:
            # Extract query text for semantic matching
            query_text = entry_data.get("query_text", "")
            user_id = entry_data.get("user_id", "")

            if not query_text:
                logger.warning(f"[PropagatedForget] No query text in deleted entry")
                return 0

            # Generate embedding for similarity search
            embedding = self.embeddings.generate_embedding(query_text)

            # Search ACMS_Knowledge_v2 for related entries
            knowledge_results = self.weaviate.semantic_search(
                collection="ACMS_Knowledge_v2",
                query_vector=embedding,
                limit=10,  # Check top 10 related entries
            )

            # Flag entries that are semantically related (similarity > 0.70)
            PROPAGATION_THRESHOLD = 0.70

            for result in knowledge_results:
                distance = result.get("distance", 1.0)
                similarity = 1 - distance

                if similarity >= PROPAGATION_THRESHOLD:
                    knowledge_id = result.get("uuid", "")
                    knowledge_props = result.get("properties", {})

                    # Only flag if same user (privacy)
                    if knowledge_props.get("user_id") != user_id:
                        continue

                    # Flag for review
                    review_id = await flag_related_knowledge_for_review(
                        entry_id=knowledge_id,
                        entry_collection="ACMS_Knowledge_v2",
                        reason=f"Related cache entry deleted: {reason}",
                        source_deletion_id=source_entry_id,
                        priority="medium" if similarity >= 0.85 else "low",
                        user_id=user_id,
                        similarity_to_deleted=similarity,
                        deleted_query=query_text,
                    )

                    if review_id:
                        flagged_count += 1
                        logger.info(
                            f"[PropagatedForget] Flagged {knowledge_id[:8]}... "
                            f"(similarity={similarity:.2f})"
                        )

            # Also check ACMS_Raw_v1 for related raw Q&A pairs
            raw_results = self.weaviate.semantic_search(
                collection="ACMS_Raw_v1",
                query_vector=embedding,
                limit=5,
            )

            for result in raw_results:
                distance = result.get("distance", 1.0)
                similarity = 1 - distance

                if similarity >= PROPAGATION_THRESHOLD:
                    raw_id = result.get("uuid", "")

                    # Flag for review
                    review_id = await flag_related_knowledge_for_review(
                        entry_id=raw_id,
                        entry_collection="ACMS_Raw_v1",
                        reason=f"Related cache entry deleted: {reason}",
                        source_deletion_id=source_entry_id,
                        priority="low",  # Raw entries lower priority
                        user_id=user_id,
                        similarity_to_deleted=similarity,
                        deleted_query=query_text,
                    )

                    if review_id:
                        flagged_count += 1

            logger.info(
                f"[PropagatedForget] Flagged {flagged_count} entries for review "
                f"(source: {source_entry_id[:8]}...)"
            )

            return flagged_count

        except Exception as e:
            logger.error(f"[PropagatedForget] Error: {e}", exc_info=True)
            return flagged_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with total entries, hit rate, etc.
        """
        try:
            total_entries = self.weaviate.count_vectors(self.collection_name)
        except Exception:
            total_entries = 0

        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "total_entries": total_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "similarity_threshold": self.SIMILARITY_THRESHOLD,
            "collection": self.collection_name,
        }

    def _props_to_entry(self, props: Dict[str, Any]) -> CacheEntry:
        """Convert Weaviate properties to CacheEntry."""
        # Parse created_at
        created_at_raw = props.get("created_at")
        if isinstance(created_at_raw, str):
            created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        elif isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        else:
            created_at = datetime.now(timezone.utc)

        # Parse query_type
        query_type_str = props.get("query_type", "factual")
        try:
            query_type = QueryType(query_type_str)
        except ValueError:
            query_type = QueryType.FACTUAL

        return CacheEntry(
            query_text=props.get("query_text", ""),
            response=props.get("response", ""),
            agent_used=props.get("agent_used", "unknown"),
            contains_web_search=props.get("contains_web_search", False),
            query_type=query_type,
            confidence=props.get("confidence", 0.8),
            user_verified=props.get("user_verified", False),
            positive_feedback_count=props.get("positive_feedback_count", 0),
            negative_feedback_count=props.get("negative_feedback_count", 0),
            user_id=props.get("user_id", ""),
            created_at=created_at,
            last_served=datetime.now(timezone.utc),
            serve_count=props.get("serve_count", 0),
            privacy_level=props.get("privacy_level", "PUBLIC"),
        )


# Helper function (imported from storage module)
async def get_query_history_by_id(query_id: str) -> Optional[Dict[str, Any]]:
    """
    Get query history record by ID.

    Args:
        query_id: UUID of the query_history record

    Returns:
        Dict with query data or None
    """
    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT
                    id,
                    query,
                    response,
                    response_source,
                    total_latency_ms,
                    confidence,
                    created_at
                FROM query_history
                WHERE id = :id
            """),
            {"id": query_id}
        )
        row = result.fetchone()

        if not row:
            return None

        return {
            "id": str(row.id),
            "query": row.query,
            "response": row.response,
            "response_source": row.response_source,
            "confidence": row.confidence or 0.9,
            "privacy_level": "PUBLIC",  # TODO: Add to query_history table
            "contains_web_search": False,  # TODO: Add to query_history table
        }


# Global instance
_quality_cache_instance: Optional[QualityCache] = None


def get_quality_cache() -> QualityCache:
    """Get global QualityCache instance."""
    global _quality_cache_instance
    if _quality_cache_instance is None:
        _quality_cache_instance = QualityCache()
    return _quality_cache_instance
