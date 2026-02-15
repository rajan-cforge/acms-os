"""Retrieval Coordinator - Unified memory retrieval and context building.

Responsibilities:
1. Search dual memory (cache + knowledge)
2. Execute web search if needed
3. Rank and deduplicate results
4. Build context with sanitization
5. Apply privacy filtering

Part of Sprint 2 Architecture & Resilience (Days 6-7).
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.gateway.tracing import get_trace_id
from src.gateway.coordinators.query_planner import QueryPlan
from src.gateway.context_sanitizer import get_context_sanitizer
from src.privacy.policy import get_access_filter, filter_results_by_access, audit_access

logger = logging.getLogger(__name__)


@dataclass
class RetrievalSource:
    """A single retrieval source result."""
    id: str
    content: str
    similarity: float
    source_type: str  # "cache", "knowledge", "memory", "web"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result of retrieval operation."""
    context: str
    sanitized_context: str
    sources: List[RetrievalSource]
    web_results: List[Dict[str, Any]]
    cache_hits: int
    knowledge_hits: int
    memory_hits: int
    web_hits: int
    total_sources: int
    is_context_clean: bool
    sanitization_count: int
    trace_id: str = ""

    def to_dict(self) -> dict:
        return {
            "total_sources": self.total_sources,
            "cache_hits": self.cache_hits,
            "knowledge_hits": self.knowledge_hits,
            "memory_hits": self.memory_hits,
            "web_hits": self.web_hits,
            "context_chars": len(self.sanitized_context),
            "is_context_clean": self.is_context_clean,
            "sanitization_count": self.sanitization_count,
            "trace_id": self.trace_id
        }


class RetrievalCoordinator:
    """Coordinates all retrieval operations.

    Provides a single interface for:
    - Dual memory search (cache + knowledge)
    - Legacy memory search (fallback)
    - Web search integration
    - Context building and sanitization
    - Privacy filtering

    Usage:
        coordinator = RetrievalCoordinator(
            dual_memory=DualMemoryService(),
            memory_crud=MemoryCRUD(),
            web_search=web_search_service,
            context_sanitizer=get_context_sanitizer()
        )
        result = await coordinator.retrieve(plan, user_ctx)
    """

    def __init__(
        self,
        dual_memory=None,
        memory_crud=None,
        web_search=None,
        context_sanitizer=None,
        context_builder=None,
        ranker=None
    ):
        """Initialize retrieval coordinator.

        Args:
            dual_memory: DualMemoryService for cache + knowledge search
            memory_crud: MemoryCRUD for legacy memory search
            web_search: Web search service (Tavily)
            context_sanitizer: Context sanitization service
            context_builder: Context builder for formatting
            ranker: Result ranker
        """
        self.dual_memory = dual_memory
        self.memory_crud = memory_crud
        self.web_search = web_search
        self.context_sanitizer = context_sanitizer or get_context_sanitizer()
        self.context_builder = context_builder
        self.ranker = ranker

    async def retrieve(
        self,
        plan: QueryPlan,
        user_id: str,
        role: str,
        tenant_id: str,
        context_limit: int = 10,
        conversation_id: Optional[str] = None
    ) -> RetrievalResult:
        """Retrieve context for a query plan.

        Args:
            plan: Query plan from QueryPlanner
            user_id: User identifier
            role: User role for privacy filtering
            tenant_id: Tenant identifier
            context_limit: Maximum context items
            conversation_id: Optional conversation context

        Returns:
            RetrievalResult with context and sources
        """
        trace_id = get_trace_id()
        all_sources: List[RetrievalSource] = []
        web_results: List[Dict[str, Any]] = []

        # Get access filter for privacy
        access_filter = get_access_filter(role, user_id, tenant_id)

        # Step 1: Web Search (if needed)
        if plan.needs_web_search and self.web_search:
            web_results = await self._execute_web_search(plan.sanitized_query)
            for i, result in enumerate(web_results[:5]):  # Limit web results
                all_sources.append(RetrievalSource(
                    id=f"web_{i}",
                    content=result.get("content", ""),
                    similarity=1.0 - (i * 0.1),  # Rank by position
                    source_type="web",
                    metadata={
                        "title": result.get("title", ""),
                        "url": result.get("url", "")
                    }
                ))

        # Step 2: Dual Memory Search
        cache_hits, knowledge_hits = await self._search_dual_memory(
            queries=plan.augmented_queries,
            user_id=user_id,
            conversation_id=conversation_id,
            limit=context_limit,
            access_filter=access_filter
        )

        for hit in cache_hits:
            all_sources.append(RetrievalSource(
                id=hit.get("id", ""),
                content=hit.get("content", ""),
                similarity=hit.get("similarity", 0.0),
                source_type="cache",
                metadata=hit.get("metadata", {})
            ))

        for hit in knowledge_hits:
            all_sources.append(RetrievalSource(
                id=hit.get("id", ""),
                content=hit.get("content", ""),
                similarity=hit.get("similarity", 0.0),
                source_type="knowledge",
                metadata=hit.get("metadata", {})
            ))

        # Step 3: Legacy Memory Search (fallback/supplement)
        memory_results = await self._search_legacy_memory(
            queries=plan.augmented_queries,
            user_id=user_id,
            limit=context_limit,
            access_filter=access_filter
        )

        for result in memory_results:
            all_sources.append(RetrievalSource(
                id=result.get("id", ""),
                content=result.get("content", ""),
                similarity=result.get("similarity", 0.0),
                source_type="memory",
                metadata=result.get("metadata", {})
            ))

        # Step 4: Deduplicate and Rank
        unique_sources = self._deduplicate_sources(all_sources)
        ranked_sources = self._rank_sources(unique_sources, plan.intent)

        # Step 5: Build Context
        raw_context = self._build_context(
            ranked_sources[:context_limit],
            web_results,
            plan.intent
        )

        # Step 6: Sanitize Context
        sanitization_result = self.context_sanitizer.sanitize(
            raw_context,
            add_delimiters=True
        )

        # Audit access
        audit_access(
            user_id=user_id,
            role=role,
            tenant_id=tenant_id,
            tiers_searched=access_filter.privacy_tiers,
            results_per_tier={
                "cache": len(cache_hits),
                "knowledge": len(knowledge_hits),
                "memory": len(memory_results),
                "web": len(web_results)
            }
        )

        return RetrievalResult(
            context=raw_context,
            sanitized_context=sanitization_result.sanitized_context,
            sources=ranked_sources[:context_limit],
            web_results=web_results,
            cache_hits=len(cache_hits),
            knowledge_hits=len(knowledge_hits),
            memory_hits=len(memory_results),
            web_hits=len(web_results),
            total_sources=len(ranked_sources),
            is_context_clean=sanitization_result.is_clean,
            sanitization_count=sanitization_result.detection_count,
            trace_id=trace_id
        )

    async def _execute_web_search(self, query: str) -> List[Dict[str, Any]]:
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
        access_filter
    ) -> tuple:
        """Search dual memory system."""
        if not self.dual_memory:
            return ([], [])

        cache_hits = []
        knowledge_hits = []

        try:
            for query in queries[:3]:  # Limit query variations
                c_hits, k_hits = await self.dual_memory.search_dual(
                    query=query,
                    query_vector=None,  # Let service generate
                    user_id=user_id,
                    conversation_id=conversation_id,
                    cache_limit=limit // 2,
                    knowledge_limit=limit // 2
                )
                cache_hits.extend(c_hits)
                knowledge_hits.extend(k_hits)

            # Apply privacy filter
            cache_hits = filter_results_by_access(cache_hits, access_filter)
            knowledge_hits = filter_results_by_access(knowledge_hits, access_filter)

        except Exception as e:
            logger.warning(f"[{get_trace_id()}] Dual memory search failed: {e}")

        return (cache_hits, knowledge_hits)

    async def _search_legacy_memory(
        self,
        queries: List[str],
        user_id: str,
        limit: int,
        access_filter
    ) -> List[Dict[str, Any]]:
        """Search legacy memory system."""
        if not self.memory_crud:
            return []

        results = []
        try:
            for query in queries[:2]:  # Limit variations
                memories = await self.memory_crud.search_memories(
                    query=query,
                    user_id=user_id,
                    limit=limit,
                    privacy_filter=access_filter.privacy_tiers
                )
                results.extend(memories)

            # Apply privacy filter
            results = filter_results_by_access(results, access_filter)

        except Exception as e:
            logger.warning(f"[{get_trace_id()}] Legacy memory search failed: {e}")

        return results

    def _deduplicate_sources(
        self,
        sources: List[RetrievalSource]
    ) -> List[RetrievalSource]:
        """Remove duplicate sources by ID."""
        seen_ids = set()
        unique = []

        for source in sources:
            if source.id not in seen_ids:
                seen_ids.add(source.id)
                unique.append(source)

        return unique

    def _rank_sources(
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

        # Default: sort by similarity
        return sorted(sources, key=lambda s: s.similarity, reverse=True)

    def _build_context(
        self,
        sources: List[RetrievalSource],
        web_results: List[Dict[str, Any]],
        intent: str
    ) -> str:
        """Build context string from sources."""
        if self.context_builder:
            try:
                return self.context_builder.build(sources, web_results, intent)
            except Exception as e:
                logger.warning(f"[{get_trace_id()}] Context builder failed: {e}")

        # Default context building
        parts = []

        # Web results first (if any)
        if web_results:
            parts.append("# Web Search Results\n")
            for result in web_results[:5]:
                title = result.get("title", "Untitled")
                content = result.get("content", "")[:500]
                url = result.get("url", "")
                parts.append(f"## {title}\n{content}\nSource: {url}\n")

        # Memory context
        if sources:
            parts.append("\n# Memory Context\n")
            for source in sources:
                parts.append(f"- {source.content[:300]}\n")

        return "\n".join(parts)

    def create_events(self, result: RetrievalResult) -> List[Dict[str, Any]]:
        """Create UI events for retrieval progress.

        Returns:
            List of event dictionaries for UI
        """
        events = []

        # Web search event
        if result.web_hits > 0:
            events.append({
                "type": "status",
                "step": "web_search",
                "message": f"Found {result.web_hits} web sources",
                "details": {
                    "output": {"web_hits": result.web_hits}
                }
            })

        # Memory search event
        total_memory = result.cache_hits + result.knowledge_hits + result.memory_hits
        if total_memory > 0:
            events.append({
                "type": "status",
                "step": "context_assembly",
                "message": f"Retrieved {total_memory} memory sources",
                "details": {
                    "output": {
                        "cache_hits": result.cache_hits,
                        "knowledge_hits": result.knowledge_hits,
                        "memory_hits": result.memory_hits
                    }
                }
            })

        # Sanitization event
        if not result.is_context_clean:
            events.append({
                "type": "status",
                "step": "context_sanitization",
                "message": f"Sanitized {result.sanitization_count} potential issues",
                "details": {
                    "output": {
                        "is_clean": False,
                        "sanitization_count": result.sanitization_count
                    }
                }
            })

        return events
