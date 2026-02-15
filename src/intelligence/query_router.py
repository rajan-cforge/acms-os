"""Query Router - Routes queries to appropriate data sources.

The query router is the core of the Unified Intelligence Layer. It:
1. Analyzes queries to detect intent and entities
2. Determines which sources need to be searched
3. Executes parallel searches across sources
4. Aggregates results with source attribution
5. Returns responses with proper citations

Example queries and routing:
- "What emails relate to AWS spending?" -> email + financial
- "Who should I follow up with?" -> email + calendar
- "What did Sarah say about the budget?" -> email + chat

Usage:
    router = QueryRouter()
    result = await router.route_query("What emails discuss AWS?")
    print(result.answer)
    print(result.sources)  # ["email:msg123", "email:msg456"]
"""

import os
import re
import json
import logging
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class QueryIntent(str, Enum):
    """Types of query intents for routing."""
    SEARCH = "search"           # Find specific information
    SUMMARIZE = "summarize"     # Get overview/summary
    ACTION = "action"           # Find action items
    TIMELINE = "timeline"       # Chronological information
    RELATIONSHIP = "relationship"  # People/entity connections
    COMPARISON = "comparison"   # Compare across sources
    GENERAL = "general"         # General question


@dataclass
class DetectedEntity:
    """An entity detected in the query."""
    value: str              # The entity value
    entity_type: str        # person, topic, date, organization, amount
    confidence: float = 0.8
    source_hint: Optional[str] = None  # Hint about which source


@dataclass
class SourceResult:
    """Result from a single source search."""
    source: str             # 'email', 'chat', 'financial', 'calendar'
    insight_id: str         # Reference to unified_insights
    insight_text: str       # The insight content
    insight_type: str       # action_item, deadline, topic, etc.
    confidence: float       # Match confidence
    source_timestamp: datetime
    entities: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class RouteResult:
    """Complete result of a routed query."""
    query: str
    intent: QueryIntent
    detected_entities: List[DetectedEntity]
    sources_queried: List[str]
    results: List[SourceResult]
    answer: str
    citations: List[str]    # Source references
    latency_ms: int = 0


# ============================================================================
# Entity Detection
# ============================================================================

class EntityDetector:
    """Detects entities in queries for routing decisions."""

    # Patterns for entity detection
    PERSON_PATTERNS = [
        (r'\b(?:from|by|with|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', 0.8),
        (r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', 0.95),
        (r'\bwho\s+(?:is|was|did)\s+([A-Z][a-z]+)\b', 0.7),
    ]

    TOPIC_PATTERNS = [
        (r'\babout\s+(?:the\s+)?([a-zA-Z]+(?:\s+[a-zA-Z]+){0,3})\b', 0.7),
        (r'\bregarding\s+([a-zA-Z]+(?:\s+[a-zA-Z]+){0,3})\b', 0.75),
        (r'\b(?:AWS|GCP|Azure|kubernetes|docker|python|javascript)\b', 0.9),
        (r'\b(?:budget|spending|cost|expense|revenue|invoice)\b', 0.85),
        (r'\b(?:meeting|calendar|schedule|appointment)\b', 0.85),
    ]

    DATE_PATTERNS = [
        (r'\b(?:today|tomorrow|yesterday)\b', 0.9),
        (r'\b(?:this|last|next)\s+(?:week|month|quarter|year)\b', 0.85),
        (r'\b\d{4}-\d{2}-\d{2}\b', 0.95),
        (r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', 0.8),
    ]

    # Source hint keywords
    SOURCE_HINTS = {
        "email": ["email", "emails", "inbox", "mail", "message", "sent", "received", "from", "to"],
        "financial": ["spending", "budget", "cost", "expense", "transaction", "payment", "invoice", "money", "dollar", "$"],
        "calendar": ["meeting", "calendar", "schedule", "appointment", "event", "agenda"],
        "chat": ["discussed", "talked", "conversation", "chat", "asked", "answered", "said"],
    }

    def detect(self, query: str) -> List[DetectedEntity]:
        """Detect entities in a query.

        Args:
            query: The user's query

        Returns:
            List of detected entities
        """
        entities = []
        query_lower = query.lower()

        # Detect people
        for pattern, confidence in self.PERSON_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append(DetectedEntity(
                    value=match,
                    entity_type="person",
                    confidence=confidence,
                    source_hint=self._get_source_hint(query_lower, "person"),
                ))

        # Detect topics
        for pattern, confidence in self.TOPIC_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and len(match) > 2:
                    entities.append(DetectedEntity(
                        value=match.strip(),
                        entity_type="topic",
                        confidence=confidence,
                        source_hint=self._get_source_hint(query_lower, "topic"),
                    ))

        # Detect dates
        for pattern, confidence in self.DATE_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append(DetectedEntity(
                    value=match,
                    entity_type="date",
                    confidence=confidence,
                ))

        return entities

    def _get_source_hint(self, query: str, entity_type: str) -> Optional[str]:
        """Determine which source an entity likely refers to."""
        for source, keywords in self.SOURCE_HINTS.items():
            if any(kw in query for kw in keywords):
                return source
        return None


# ============================================================================
# Intent Classifier
# ============================================================================

class IntentClassifier:
    """Classifies query intent for routing decisions."""

    INTENT_PATTERNS = {
        QueryIntent.SEARCH: [
            r'\bfind\b', r'\bsearch\b', r'\blook for\b', r'\bwhere\b',
            r'\bwhich\b', r'\bwhat\b.*\bsay\b', r'\bshow\b',
        ],
        QueryIntent.SUMMARIZE: [
            r'\bsummarize\b', r'\boverview\b', r'\bsummary\b',
            r'\bhow much\b', r'\bhow many\b', r'\btotal\b',
        ],
        QueryIntent.ACTION: [
            r'\baction\b', r'\btodo\b', r'\bto.?do\b', r'\btask\b',
            r'\bfollow.?up\b', r'\bneed to\b', r'\bshould\b',
        ],
        QueryIntent.TIMELINE: [
            r'\bwhen\b', r'\btimeline\b', r'\bhistory\b',
            r'\blast\s+\w+\b', r'\brecent\b', r'\bthis week\b',
        ],
        QueryIntent.RELATIONSHIP: [
            r'\bwho\b', r'\brelate\b', r'\bconnect\b',
            r'\bwork with\b', r'\binteract\b',
        ],
        QueryIntent.COMPARISON: [
            r'\bcompare\b', r'\bversus\b', r'\bvs\b',
            r'\bdifference\b', r'\bbetween\b',
        ],
    }

    def classify(self, query: str) -> Tuple[QueryIntent, float]:
        """Classify the intent of a query.

        Args:
            query: The user's query

        Returns:
            Tuple of (intent, confidence)
        """
        query_lower = query.lower()
        scores = {intent: 0.0 for intent in QueryIntent}

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    scores[intent] += 1.0

        # Find best match
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        if best_score == 0:
            return QueryIntent.GENERAL, 0.5

        # Normalize confidence
        confidence = min(best_score / 3.0, 1.0)
        return best_intent, confidence


# ============================================================================
# Source Router
# ============================================================================

class SourceRouter:
    """Determines which sources to query based on intent and entities."""

    # Source relevance by intent
    INTENT_SOURCE_MAP = {
        QueryIntent.SEARCH: ["email", "chat", "financial", "calendar"],
        QueryIntent.SUMMARIZE: ["email", "chat", "financial"],
        QueryIntent.ACTION: ["email", "calendar"],
        QueryIntent.TIMELINE: ["email", "calendar", "chat"],
        QueryIntent.RELATIONSHIP: ["email", "chat", "calendar"],
        QueryIntent.COMPARISON: ["email", "financial", "chat"],
        QueryIntent.GENERAL: ["chat", "email"],
    }

    # Entity type to source mapping
    ENTITY_SOURCE_MAP = {
        "person": ["email", "chat", "calendar"],
        "topic": ["chat", "email"],
        "date": ["calendar", "email"],
        "amount": ["financial"],
        "organization": ["email", "financial"],
    }

    def determine_sources(
        self,
        intent: QueryIntent,
        entities: List[DetectedEntity],
        available_sources: Set[str] = None,
    ) -> List[str]:
        """Determine which sources to query.

        Args:
            intent: Detected query intent
            entities: Detected entities
            available_sources: Sources currently available

        Returns:
            List of sources to query, ordered by relevance
        """
        if available_sources is None:
            available_sources = {"email", "chat"}  # Currently available

        # Start with intent-based sources
        sources = set(self.INTENT_SOURCE_MAP.get(intent, ["chat"]))

        # Add entity-based sources
        for entity in entities:
            if entity.source_hint:
                sources.add(entity.source_hint)
            entity_sources = self.ENTITY_SOURCE_MAP.get(entity.entity_type, [])
            sources.update(entity_sources)

        # Filter to available sources
        sources = sources.intersection(available_sources)

        # Default to chat if no sources
        if not sources:
            sources = {"chat"}

        return list(sources)


# ============================================================================
# Query Router (Main Class)
# ============================================================================

class QueryRouter:
    """Main query router for cross-source intelligence.

    Orchestrates entity detection, intent classification, source routing,
    parallel search, and result aggregation.
    """

    def __init__(self):
        self.entity_detector = EntityDetector()
        self.intent_classifier = IntentClassifier()
        self.source_router = SourceRouter()
        self.logger = logging.getLogger(f"{__name__}.QueryRouter")

    async def route_query(
        self,
        query: str,
        available_sources: Set[str] = None,
        max_results_per_source: int = 5,
    ) -> RouteResult:
        """Route a query to appropriate sources and aggregate results.

        Args:
            query: The user's query
            available_sources: Sources to consider (default: email, chat)
            max_results_per_source: Max results per source

        Returns:
            RouteResult with aggregated answer and citations
        """
        import time
        start_time = time.time()

        if available_sources is None:
            available_sources = {"email", "chat"}

        # 1. Detect entities
        entities = self.entity_detector.detect(query)
        self.logger.debug(f"Detected {len(entities)} entities")

        # 2. Classify intent
        intent, intent_confidence = self.intent_classifier.classify(query)
        self.logger.debug(f"Intent: {intent.value} (confidence: {intent_confidence})")

        # 3. Determine sources to query
        sources = self.source_router.determine_sources(
            intent, entities, available_sources
        )
        self.logger.debug(f"Routing to sources: {sources}")

        # 4. Execute parallel searches
        results = await self._search_sources(
            query, entities, sources, max_results_per_source
        )

        # 5. Aggregate results
        answer, citations = self._aggregate_results(query, intent, results)

        latency_ms = int((time.time() - start_time) * 1000)

        return RouteResult(
            query=query,
            intent=intent,
            detected_entities=entities,
            sources_queried=sources,
            results=results,
            answer=answer,
            citations=citations,
            latency_ms=latency_ms,
        )

    async def _search_sources(
        self,
        query: str,
        entities: List[DetectedEntity],
        sources: List[str],
        max_results: int,
    ) -> List[SourceResult]:
        """Search multiple sources in parallel.

        Args:
            query: Original query
            entities: Detected entities for filtering
            sources: Sources to search
            max_results: Max results per source

        Returns:
            Combined results from all sources
        """
        # Create search tasks
        tasks = []
        for source in sources:
            task = self._search_source(query, entities, source, max_results)
            tasks.append(task)

        # Execute in parallel
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and filter errors
        all_results = []
        for result_list in results_lists:
            if isinstance(result_list, Exception):
                self.logger.error(f"Source search failed: {result_list}")
            elif result_list:
                all_results.extend(result_list)

        # Sort by confidence
        all_results.sort(key=lambda r: r.confidence, reverse=True)
        return all_results

    async def _search_source(
        self,
        query: str,
        entities: List[DetectedEntity],
        source: str,
        max_results: int,
    ) -> List[SourceResult]:
        """Search a single source.

        Args:
            query: Original query
            entities: Detected entities
            source: Source to search
            max_results: Max results

        Returns:
            Results from this source
        """
        try:
            if source == "email":
                return await self._search_email_insights(query, entities, max_results)
            elif source == "chat":
                return await self._search_chat_insights(query, entities, max_results)
            elif source == "financial":
                return await self._search_financial_insights(query, entities, max_results)
            elif source == "calendar":
                return await self._search_calendar_insights(query, entities, max_results)
            else:
                self.logger.warning(f"Unknown source: {source}")
                return []
        except Exception as e:
            self.logger.error(f"Error searching {source}: {e}")
            return []

    async def _search_email_insights(
        self,
        query: str,
        entities: List[DetectedEntity],
        max_results: int,
    ) -> List[SourceResult]:
        """Search email insights in unified_insights table."""
        from src.storage.database import get_db_connection
        from src.embeddings.openai_embeddings import OpenAIEmbeddings
        from src.storage.weaviate_client import WeaviateClient

        results = []

        # First try semantic search via Weaviate
        try:
            embedder = OpenAIEmbeddings()
            query_vector = embedder.generate_embedding(query)
            client = WeaviateClient()

            search_results = client.semantic_search(
                collection="ACMS_Insights_v1",
                query_vector=query_vector,
                limit=max_results,
            )
            client.close()

            for sr in search_results:
                if sr["properties"].get("source") == "email":
                    results.append(SourceResult(
                        source="email",
                        insight_id=sr["properties"].get("insight_id", ""),
                        insight_text=sr["properties"].get("insight_text", ""),
                        insight_type=sr["properties"].get("insight_type", "topic"),
                        confidence=1.0 - sr["distance"],  # Convert distance to confidence
                        source_timestamp=datetime.now(timezone.utc),  # Would need to parse
                    ))

        except Exception as e:
            self.logger.warning(f"Weaviate search failed, falling back to SQL: {e}")

        # Fallback to SQL if no results
        if not results:
            async with get_db_connection() as conn:
                rows = await conn.fetch("""
                    SELECT id, insight_text, insight_type, confidence_score, source_timestamp, entities
                    FROM unified_insights
                    WHERE source = 'email' AND is_active = TRUE
                    ORDER BY source_timestamp DESC
                    LIMIT $1
                """, max_results)

                for row in rows:
                    results.append(SourceResult(
                        source="email",
                        insight_id=str(row["id"]),
                        insight_text=row["insight_text"],
                        insight_type=row["insight_type"],
                        confidence=float(row["confidence_score"]) if row["confidence_score"] else 0.7,
                        source_timestamp=row["source_timestamp"],
                        entities=json.loads(row["entities"]) if isinstance(row["entities"], str) else row["entities"] or {},
                    ))

        return results

    async def _search_chat_insights(
        self,
        query: str,
        entities: List[DetectedEntity],
        max_results: int,
    ) -> List[SourceResult]:
        """Search chat/knowledge insights."""
        # For now, search ACMS_Knowledge_v2 directly
        from src.embeddings.openai_embeddings import OpenAIEmbeddings
        from src.storage.weaviate_client import WeaviateClient

        results = []

        try:
            embedder = OpenAIEmbeddings()
            query_vector = embedder.generate_embedding(query)
            client = WeaviateClient()

            search_results = client.semantic_search(
                collection="ACMS_Knowledge_v2",
                query_vector=query_vector,
                limit=max_results,
            )
            client.close()

            for sr in search_results:
                results.append(SourceResult(
                    source="chat",
                    insight_id=sr["uuid"],
                    insight_text=sr["properties"].get("content", ""),
                    insight_type="fact",
                    confidence=1.0 - sr["distance"],
                    source_timestamp=datetime.now(timezone.utc),
                ))

        except Exception as e:
            self.logger.warning(f"Chat insight search failed: {e}")

        return results

    async def _search_financial_insights(
        self,
        query: str,
        entities: List[DetectedEntity],
        max_results: int,
    ) -> List[SourceResult]:
        """Search financial insights (Phase 2)."""
        # Not implemented yet
        return []

    async def _search_calendar_insights(
        self,
        query: str,
        entities: List[DetectedEntity],
        max_results: int,
    ) -> List[SourceResult]:
        """Search calendar insights (Phase 3)."""
        # Not implemented yet
        return []

    def _aggregate_results(
        self,
        query: str,
        intent: QueryIntent,
        results: List[SourceResult],
    ) -> Tuple[str, List[str]]:
        """Aggregate results into a coherent answer with citations.

        Args:
            query: Original query
            intent: Detected intent
            results: Results from all sources

        Returns:
            Tuple of (answer, citations)
        """
        if not results:
            return "No relevant information found across your data sources.", []

        # Group by source
        by_source: Dict[str, List[SourceResult]] = {}
        for r in results:
            if r.source not in by_source:
                by_source[r.source] = []
            by_source[r.source].append(r)

        # Build answer
        answer_parts = []
        citations = []

        for source, source_results in by_source.items():
            if source_results:
                # Add source header
                source_label = source.capitalize()
                answer_parts.append(f"\n**From {source_label}:**")

                # Add top results
                for i, r in enumerate(source_results[:3]):
                    answer_parts.append(f"- {r.insight_text}")
                    citations.append(f"{source}:{r.insight_id}")

        answer = "\n".join(answer_parts).strip()

        # Add summary header
        sources_mentioned = ", ".join(by_source.keys())
        header = f"Found {len(results)} relevant items from {sources_mentioned}."
        answer = f"{header}\n{answer}"

        return answer, citations


# ============================================================================
# Convenience Functions
# ============================================================================

async def route_cross_source_query(query: str) -> RouteResult:
    """Route a query across all available sources.

    Args:
        query: User's question

    Returns:
        RouteResult with answer and sources
    """
    router = QueryRouter()
    return await router.route_query(query)
