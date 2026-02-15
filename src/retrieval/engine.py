"""Unified Retrieval Engine - Single interface for all memory operations.

This is the single source of truth for memory retrieval, consolidating:
- Dual memory search (cache + knowledge)
- Legacy memory search (fallback)
- Web search integration
- Privacy filtering via RBAC
- Context ranking and building
- Adaptive thresholds based on query intent (pattern separation/completion)

Part of Sprint 2 Architecture (Days 8-9).
Updated: Cognitive Architecture Sprint 1 - Adaptive Thresholds
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from src.gateway.tracing import get_trace_id
from src.privacy.policy import get_access_filter, filter_results_by_access, audit_access
from src.gateway.context_sanitizer import get_context_sanitizer
from src.retrieval.threshold_resolver import ThresholdResolver, ThresholdSet, RetrievalMode
from src.retrieval.coretrieval_graph import CoRetrievalTracker, get_coretrieval_tracker

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Types of retrieval sources."""
    CACHE = "cache"
    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    WEB = "web"


@dataclass
class RetrievalSource:
    """A single source retrieved from memory or web."""
    id: str
    content: str
    similarity: float
    source_type: SourceType
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "similarity": round(self.similarity, 3),
            "source_type": self.source_type.value,
            "metadata": self.metadata
        }


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    query: str
    context: str
    sanitized_context: str
    sources: List[RetrievalSource]
    cache_hits: int = 0
    knowledge_hits: int = 0
    memory_hits: int = 0
    web_hits: int = 0
    is_context_clean: bool = True
    sanitization_count: int = 0
    trace_id: str = ""
    # Adaptive threshold info (Cognitive Architecture Sprint 1)
    retrieval_mode: str = "default"
    thresholds_used: Optional[Dict[str, float]] = None
    # Co-retrieval tracking (Cognitive Architecture Sprint 3)
    associated_items_preloaded: int = 0
    co_retrieval_recorded: bool = False

    @property
    def total_sources(self) -> int:
        return len(self.sources)

    def to_dict(self) -> dict:
        return {
            "query": self.query[:50] + "..." if len(self.query) > 50 else self.query,
            "total_sources": self.total_sources,
            "cache_hits": self.cache_hits,
            "knowledge_hits": self.knowledge_hits,
            "memory_hits": self.memory_hits,
            "web_hits": self.web_hits,
            "context_chars": len(self.sanitized_context),
            "is_context_clean": self.is_context_clean,
            "sanitization_count": self.sanitization_count,
            "trace_id": self.trace_id,
            "retrieval_mode": self.retrieval_mode,
            "thresholds_used": self.thresholds_used,
            # Co-retrieval tracking (Cognitive Architecture Sprint 3)
            "associated_items_preloaded": self.associated_items_preloaded,
            "co_retrieval_recorded": self.co_retrieval_recorded,
        }


class RetrievalEngine:
    """Unified retrieval engine for all memory operations.

    This is the single interface for:
    1. Searching dual memory (cache + knowledge)
    2. Falling back to legacy memory
    3. Executing web search
    4. Applying RBAC privacy filters
    5. Ranking and deduplicating results
    6. Building and sanitizing context

    Usage:
        engine = RetrievalEngine(
            dual_memory=dual_memory_service,
            memory_crud=memory_crud,
            web_search=tavily_client,
            context_sanitizer=get_context_sanitizer()
        )
        result = await engine.retrieve_context(
            query="What is X?",
            user_id="user1",
            role="member",
            tenant_id="tenant1",
            intent="general",
            limit=10
        )
    """

    def __init__(
        self,
        dual_memory=None,
        memory_crud=None,
        web_search=None,
        context_sanitizer=None,
        ranker=None,
        threshold_resolver=None,
        coretrieval_tracker=None,
        enable_web_search: bool = True,
        enable_legacy_memory: bool = True,
        enable_adaptive_thresholds: bool = True,
        enable_coretrieval_tracking: bool = True
    ):
        """Initialize retrieval engine.

        Args:
            dual_memory: DualMemoryService for cache + knowledge search
            memory_crud: MemoryCRUD for legacy memory search
            web_search: Web search service (Tavily)
            context_sanitizer: Context sanitization service
            ranker: Optional custom ranker
            threshold_resolver: Optional ThresholdResolver for adaptive thresholds
            coretrieval_tracker: Optional CoRetrievalTracker for Hebbian learning
            enable_web_search: Whether web search is enabled
            enable_legacy_memory: Whether to fall back to legacy memory
            enable_adaptive_thresholds: Whether to use adaptive thresholds (default True)
            enable_coretrieval_tracking: Whether to track co-retrieval patterns (default True)
        """
        self.dual_memory = dual_memory
        self.memory_crud = memory_crud
        self.web_search = web_search
        self.context_sanitizer = context_sanitizer or get_context_sanitizer()
        self.ranker = ranker
        self.threshold_resolver = threshold_resolver or ThresholdResolver()
        self.coretrieval_tracker = coretrieval_tracker or get_coretrieval_tracker()
        self.enable_web_search = enable_web_search
        self.enable_legacy_memory = enable_legacy_memory
        self.enable_adaptive_thresholds = enable_adaptive_thresholds
        self.enable_coretrieval_tracking = enable_coretrieval_tracking

    async def retrieve_context(
        self,
        query: str,
        user_id: str,
        role: str,
        tenant_id: str,
        intent: str = "general",
        limit: int = 10,
        augmented_queries: Optional[List[str]] = None,
        needs_web_search: bool = False,
        conversation_id: Optional[str] = None,
        intent_hint: Optional[str] = None
    ) -> RetrievalResult:
        """Retrieve context from all sources.

        Args:
            query: The user's query
            user_id: User identifier
            role: User role for RBAC (public, member, admin)
            tenant_id: Tenant identifier
            intent: Query intent for ranking optimization
            limit: Maximum number of sources to return
            augmented_queries: Additional query variations
            needs_web_search: Whether web search is needed
            conversation_id: Optional conversation context
            intent_hint: Optional hint for threshold resolution (exact, explore, etc.)

        Returns:
            RetrievalResult with context and sources
        """
        trace_id = get_trace_id()
        all_sources: List[RetrievalSource] = []

        # ============================================================
        # ADAPTIVE THRESHOLD RESOLUTION (Cognitive Architecture)
        # ============================================================
        # Cognitive basis: Pattern Separation vs Pattern Completion
        # - Exact recall queries (Dentate Gyrus) → high thresholds
        # - Exploratory queries (CA3) → lower thresholds
        if self.enable_adaptive_thresholds:
            thresholds = self.threshold_resolver.resolve(query, intent_hint=intent_hint)
            retrieval_mode = self.threshold_resolver.get_mode(query, intent_hint)
            logger.info(
                f"[{trace_id}] Adaptive thresholds: mode={retrieval_mode.value}, "
                f"cache={thresholds.cache:.2f}, raw={thresholds.raw:.2f}, "
                f"knowledge={thresholds.knowledge:.2f}"
            )
        else:
            # Fall back to default fixed thresholds
            thresholds = ThresholdSet(cache=0.95, raw=0.85, knowledge=0.60)
            retrieval_mode = RetrievalMode.DEFAULT

        # Build list of queries to search
        queries = [query]
        if augmented_queries:
            queries.extend(augmented_queries[:2])  # Limit augmented queries

        # Get access filter for RBAC
        access_filter = get_access_filter(role, user_id, tenant_id)

        # Step 1: Web Search (if needed)
        web_results = []
        if needs_web_search and self.enable_web_search:
            web_results = await self._web_search(query)
            for i, result in enumerate(web_results[:5]):
                all_sources.append(RetrievalSource(
                    id=f"web_{i}",
                    content=result.get("content", ""),
                    similarity=1.0 - (i * 0.1),
                    source_type=SourceType.WEB,
                    metadata={
                        "title": result.get("title", ""),
                        "url": result.get("url", "")
                    }
                ))

        # Step 2: Dual Memory Search (with adaptive thresholds)
        cache_hits, knowledge_hits = await self._search_dual_memory(
            queries=queries,
            user_id=user_id,
            conversation_id=conversation_id,
            limit=limit,
            access_filter=access_filter,
            thresholds=thresholds
        )
        all_sources.extend(cache_hits)
        all_sources.extend(knowledge_hits)

        # Step 3: Legacy Memory Fallback
        if self.enable_legacy_memory:
            memory_hits = await self._search_legacy_memory(
                queries=queries,
                user_id=user_id,
                limit=limit,
                access_filter=access_filter
            )
            all_sources.extend(memory_hits)

        # Step 4: Deduplicate and Rank
        unique_sources = self._deduplicate(all_sources)
        ranked_sources = self._rank(unique_sources, intent)

        # ============================================================
        # CO-RETRIEVAL TRACKING (Cognitive Architecture Sprint 3)
        # ============================================================
        # Cognitive basis: Hebbian Learning
        # "Neurons that fire together, wire together"
        # Items retrieved together form associations that strengthen over time
        associated_items_preloaded = 0
        co_retrieval_recorded = False

        if self.enable_coretrieval_tracking and self.coretrieval_tracker:
            # Get item IDs from retrieved sources (exclude web)
            retrieved_ids = [
                s.id for s in ranked_sources
                if s.id and s.source_type != SourceType.WEB
            ]

            # Step 4.5a: Get associated items for top result (preloading)
            if retrieved_ids:
                try:
                    associated = await self.coretrieval_tracker.get_associated_items(
                        item_id=retrieved_ids[0],
                        min_strength=0.3,
                        limit=3
                    )
                    associated_items_preloaded = len(associated)
                    if associated:
                        logger.debug(
                            f"[{trace_id}] Hebbian preload: {len(associated)} "
                            f"associated items for {retrieved_ids[0][:8]}..."
                        )
                except Exception as e:
                    logger.debug(f"[{trace_id}] Associated items fetch failed: {e}")

            # Step 4.5b: Record co-retrieval for future associations
            if len(retrieved_ids) >= 2:
                try:
                    # Extract topic from intent or query
                    topic = intent if intent != "general" else query[:50]
                    edges_created = await self.coretrieval_tracker.record_co_retrieval(
                        session_id=conversation_id,
                        retrieved_ids=retrieved_ids,
                        topic=topic
                    )
                    co_retrieval_recorded = edges_created > 0
                    if co_retrieval_recorded:
                        logger.debug(
                            f"[{trace_id}] Hebbian learning: recorded {edges_created} "
                            f"co-retrieval edges for {len(retrieved_ids)} items"
                        )
                except Exception as e:
                    logger.debug(f"[{trace_id}] Co-retrieval recording failed: {e}")

        # Step 5: Build Context
        context = self._build_context(
            ranked_sources[:limit],
            web_results,
            intent
        )

        # Step 6: Sanitize Context
        sanitization_result = self.context_sanitizer.sanitize(
            context,
            add_delimiters=True
        )

        # Audit access
        audit_access(
            user_id=user_id,
            role=role,
            tenant_id=tenant_id,
            tiers_searched=access_filter.privacy_tiers,
            results_per_tier={
                "cache": len([s for s in all_sources if s.source_type == SourceType.CACHE]),
                "knowledge": len([s for s in all_sources if s.source_type == SourceType.KNOWLEDGE]),
                "memory": len([s for s in all_sources if s.source_type == SourceType.MEMORY]),
                "web": len(web_results)
            }
        )

        return RetrievalResult(
            query=query,
            context=context,
            sanitized_context=sanitization_result.sanitized_context,
            sources=ranked_sources[:limit],
            cache_hits=len([s for s in all_sources if s.source_type == SourceType.CACHE]),
            knowledge_hits=len([s for s in all_sources if s.source_type == SourceType.KNOWLEDGE]),
            memory_hits=len([s for s in all_sources if s.source_type == SourceType.MEMORY]),
            web_hits=len(web_results),
            is_context_clean=sanitization_result.is_clean,
            sanitization_count=sanitization_result.detection_count,
            trace_id=trace_id,
            retrieval_mode=retrieval_mode.value,
            thresholds_used=thresholds.to_dict(),
            # Co-retrieval tracking (Cognitive Architecture Sprint 3)
            associated_items_preloaded=associated_items_preloaded,
            co_retrieval_recorded=co_retrieval_recorded,
        )

    async def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """Execute web search."""
        if not self.web_search:
            return []

        try:
            results = await self.web_search.search(query)
            logger.info(f"[{get_trace_id()}] Web search returned {len(results)} results")
            return results
        except Exception as e:
            logger.warning(f"[{get_trace_id()}] Web search failed: {e}")
            return []

    async def _search_dual_memory(
        self,
        queries: List[str],
        user_id: str,
        conversation_id: Optional[str],
        limit: int,
        access_filter,
        thresholds: Optional[ThresholdSet] = None
    ) -> Tuple[List[RetrievalSource], List[RetrievalSource]]:
        """Search dual memory (cache + knowledge) with adaptive thresholds.

        Args:
            queries: List of query strings to search
            user_id: User identifier
            conversation_id: Optional conversation context
            limit: Maximum results per source
            access_filter: RBAC access filter
            thresholds: Adaptive thresholds (cache, raw, knowledge)

        Returns:
            Tuple of (cache_sources, knowledge_sources)
        """
        if not self.dual_memory:
            return ([], [])

        # Use adaptive thresholds or defaults
        cache_threshold = thresholds.raw if thresholds else 0.85  # raw maps to cache search
        knowledge_threshold = thresholds.knowledge if thresholds else 0.60

        cache_sources = []
        knowledge_sources = []

        try:
            for query in queries[:3]:
                c_hits, k_hits = await self.dual_memory.search_dual(
                    query=query,
                    query_vector=None,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    cache_limit=limit // 2,
                    knowledge_limit=limit // 2,
                    cache_threshold=cache_threshold,
                    knowledge_threshold=knowledge_threshold
                )

                for hit in c_hits:
                    cache_sources.append(RetrievalSource(
                        id=hit.get("id", ""),
                        content=hit.get("content", ""),
                        similarity=hit.get("similarity", 0.0),
                        source_type=SourceType.CACHE,
                        metadata=hit.get("metadata", {})
                    ))

                for hit in k_hits:
                    knowledge_sources.append(RetrievalSource(
                        id=hit.get("id", ""),
                        content=hit.get("content", ""),
                        similarity=hit.get("similarity", 0.0),
                        source_type=SourceType.KNOWLEDGE,
                        metadata=hit.get("metadata", {})
                    ))

            # Apply RBAC filter
            cache_sources = self._apply_access_filter(cache_sources, access_filter)
            knowledge_sources = self._apply_access_filter(knowledge_sources, access_filter)

        except Exception as e:
            logger.warning(f"[{get_trace_id()}] Dual memory search failed: {e}")

        return (cache_sources, knowledge_sources)

    async def _search_legacy_memory(
        self,
        queries: List[str],
        user_id: str,
        limit: int,
        access_filter
    ) -> List[RetrievalSource]:
        """Search legacy memory system."""
        if not self.memory_crud:
            return []

        sources = []

        try:
            for query in queries[:2]:
                memories = await self.memory_crud.search_memories(
                    query=query,
                    user_id=user_id,
                    limit=limit,
                    privacy_filter=access_filter.privacy_tiers
                )

                for mem in memories:
                    sources.append(RetrievalSource(
                        id=mem.get("id", ""),
                        content=mem.get("content", ""),
                        similarity=mem.get("similarity", 0.0),
                        source_type=SourceType.MEMORY,
                        metadata=mem.get("metadata", {})
                    ))

            # Apply RBAC filter
            sources = self._apply_access_filter(sources, access_filter)

        except Exception as e:
            logger.warning(f"[{get_trace_id()}] Legacy memory search failed: {e}")

        return sources

    def _apply_access_filter(
        self,
        sources: List[RetrievalSource],
        access_filter
    ) -> List[RetrievalSource]:
        """Apply RBAC access filter to sources."""
        # Convert to dicts for filtering
        source_dicts = [
            {"id": s.id, "content": s.content, "similarity": s.similarity,
             "source_type": s.source_type, "metadata": s.metadata}
            for s in sources
        ]

        # Filter using RBAC policy
        filtered = filter_results_by_access(source_dicts, access_filter)

        # Convert back to RetrievalSource
        return [
            RetrievalSource(
                id=f.get("id", ""),
                content=f.get("content", ""),
                similarity=f.get("similarity", 0.0),
                source_type=f.get("source_type", SourceType.MEMORY),
                metadata=f.get("metadata", {})
            )
            for f in filtered
        ]

    def _deduplicate(
        self,
        sources: List[RetrievalSource]
    ) -> List[RetrievalSource]:
        """Remove duplicate sources by ID."""
        seen = set()
        unique = []

        for source in sources:
            if source.id and source.id not in seen:
                seen.add(source.id)
                unique.append(source)
            elif not source.id:
                # Keep sources without IDs (web results)
                unique.append(source)

        return unique

    def _rank(
        self,
        sources: List[RetrievalSource],
        intent: str
    ) -> List[RetrievalSource]:
        """Rank sources by relevance."""
        if self.ranker:
            try:
                return self.ranker.rank(sources, intent)
            except Exception as e:
                logger.warning(f"[{get_trace_id()}] Ranking failed: {e}")

        # Default: sort by similarity, web results first for fresh queries
        def rank_key(s):
            # Boost web results for certain intents
            boost = 0.1 if s.source_type == SourceType.WEB and intent in ["news", "current_events"] else 0
            return s.similarity + boost

        return sorted(sources, key=rank_key, reverse=True)

    def _build_context(
        self,
        sources: List[RetrievalSource],
        web_results: List[Dict[str, Any]],
        intent: str
    ) -> str:
        """Build context string from sources."""
        parts = []

        # Web results first (fresh information)
        web_sources = [s for s in sources if s.source_type == SourceType.WEB]
        if web_sources:
            parts.append("# Web Search Results\n")
            for source in web_sources[:5]:
                title = source.metadata.get("title", "Untitled")
                url = source.metadata.get("url", "")
                content = source.content[:500]
                parts.append(f"## {title}\n{content}\nSource: {url}\n")

        # Knowledge base (extracted facts)
        knowledge_sources = [s for s in sources if s.source_type == SourceType.KNOWLEDGE]
        if knowledge_sources:
            parts.append("\n# Knowledge Base\n")
            for source in knowledge_sources[:5]:
                parts.append(f"- {source.content[:300]}\n")

        # Cache (previous high-quality Q&A)
        cache_sources = [s for s in sources if s.source_type == SourceType.CACHE]
        if cache_sources:
            parts.append("\n# Relevant Context\n")
            for source in cache_sources[:5]:
                parts.append(f"- {source.content[:300]}\n")

        # Memory (general memories)
        memory_sources = [s for s in sources if s.source_type == SourceType.MEMORY]
        if memory_sources:
            parts.append("\n# Related Memories\n")
            for source in memory_sources[:5]:
                parts.append(f"- {source.content[:300]}\n")

        return "\n".join(parts)

    def get_search_stats(self) -> Dict[str, Any]:
        """Get statistics about search capabilities."""
        stats = {
            "dual_memory_available": self.dual_memory is not None,
            "legacy_memory_available": self.memory_crud is not None,
            "web_search_available": self.web_search is not None,
            "web_search_enabled": self.enable_web_search,
            "legacy_memory_enabled": self.enable_legacy_memory,
            "has_ranker": self.ranker is not None,
            # Co-retrieval tracking (Cognitive Architecture Sprint 3)
            "coretrieval_tracking_enabled": self.enable_coretrieval_tracking,
            "coretrieval_tracker_available": self.coretrieval_tracker is not None,
        }

        # Add co-retrieval stats if tracker is available
        if self.coretrieval_tracker:
            stats["coretrieval_stats"] = self.coretrieval_tracker.get_stats()

        return stats
