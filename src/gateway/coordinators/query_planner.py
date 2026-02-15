"""Query Planner Coordinator - Intent detection and query augmentation.

Responsibilities:
1. Classify query intent (general, memory_query, creative, analysis)
2. Determine if web search is needed
3. Augment query with variations for better retrieval
4. Package results into QueryPlan for downstream coordinators

Part of Sprint 2 Architecture & Resilience (Days 6-7).
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, AsyncIterator
from enum import Enum

from src.gateway.tracing import get_trace_id
from src.gateway.preflight_gate import PreflightResult

logger = logging.getLogger(__name__)


@dataclass
class QueryPlan:
    """Plan for processing a query."""
    original_query: str
    sanitized_query: str
    augmented_queries: List[str]
    intent: str
    intent_confidence: float
    allow_web_search: bool
    needs_web_search: bool
    web_search_reason: Optional[str] = None
    trace_id: str = ""

    def to_dict(self) -> dict:
        return {
            "original_query": self.original_query[:50] + "..." if len(self.original_query) > 50 else self.original_query,
            "intent": self.intent,
            "intent_confidence": round(self.intent_confidence, 2),
            "query_count": len(self.augmented_queries),
            "allow_web_search": self.allow_web_search,
            "needs_web_search": self.needs_web_search,
            "web_search_reason": self.web_search_reason,
            "trace_id": self.trace_id
        }


class QueryPlanner:
    """Plans query processing strategy.

    Coordinates:
    - Intent classification
    - Web search decision
    - Query augmentation

    Usage:
        planner = QueryPlanner(
            intent_classifier=get_intent_classifier(),
            search_detector=SearchDetector(),
            query_augmenter=QueryAugmenter()
        )
        plan = await planner.plan(query, preflight_result, user_id)
    """

    def __init__(
        self,
        intent_classifier=None,
        search_detector=None,
        query_augmenter=None,
        enable_augmentation: bool = True,
        enable_web_search: bool = True
    ):
        """Initialize query planner.

        Args:
            intent_classifier: Intent classification service
            search_detector: Web search need detector
            query_augmenter: Query augmentation service
            enable_augmentation: Whether to augment queries
            enable_web_search: Whether to allow web search
        """
        self.intent_classifier = intent_classifier
        self.search_detector = search_detector
        self.query_augmenter = query_augmenter
        self.enable_augmentation = enable_augmentation
        self.enable_web_search = enable_web_search

    async def plan(
        self,
        query: str,
        preflight_result: PreflightResult,
        user_id: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> QueryPlan:
        """Create execution plan for a query.

        Args:
            query: Original user query
            preflight_result: Result from PreflightGate
            user_id: User identifier
            conversation_history: Optional conversation context

        Returns:
            QueryPlan with processing strategy
        """
        trace_id = get_trace_id()

        # Use sanitized query if available
        working_query = preflight_result.sanitized_query or query

        # Step 1: Intent Classification
        intent, confidence = await self._classify_intent(working_query)
        logger.info(f"[{trace_id}] Intent: {intent} (confidence: {confidence:.2f})")

        # Step 2: Web Search Decision
        allow_web_search = preflight_result.allow_web_search and self.enable_web_search
        needs_search, search_reason = await self._check_web_search_need(
            working_query,
            intent,
            allow_web_search
        )

        # Step 3: Query Augmentation
        augmented_queries = await self._augment_query(
            working_query,
            intent,
            conversation_history
        )

        return QueryPlan(
            original_query=query,
            sanitized_query=working_query,
            augmented_queries=augmented_queries,
            intent=intent,
            intent_confidence=confidence,
            allow_web_search=allow_web_search,
            needs_web_search=needs_search,
            web_search_reason=search_reason,
            trace_id=trace_id
        )

    async def _classify_intent(self, query: str) -> tuple:
        """Classify query intent.

        Returns:
            Tuple of (intent_name, confidence)
        """
        if self.intent_classifier is None:
            return ("general", 0.5)

        try:
            intent, confidence = self.intent_classifier.classify(query)
            return (intent.value if hasattr(intent, 'value') else str(intent), confidence)
        except Exception as e:
            logger.warning(f"[{get_trace_id()}] Intent classification failed: {e}")
            return ("general", 0.5)

    async def _check_web_search_need(
        self,
        query: str,
        intent: str,
        allow_web_search: bool
    ) -> tuple:
        """Determine if web search is needed.

        Returns:
            Tuple of (needs_search, reason)
        """
        if not allow_web_search:
            return (False, "disabled by security gate")

        if self.search_detector is None:
            return (False, "search detector not configured")

        try:
            needs_search, reason = self.search_detector.should_search(query)
            return (needs_search, reason)
        except Exception as e:
            logger.warning(f"[{get_trace_id()}] Search detection failed: {e}")
            return (False, f"detection error: {e}")

    async def _augment_query(
        self,
        query: str,
        intent: str,
        conversation_history: Optional[List[Dict]]
    ) -> List[str]:
        """Augment query with variations.

        Returns:
            List of query variations (always includes original)
        """
        if not self.enable_augmentation or self.query_augmenter is None:
            return [query]

        try:
            augmented = await self.query_augmenter.augment(
                query=query,
                intent=intent,
                conversation_history=conversation_history
            )
            # Ensure original query is first
            if query not in augmented:
                augmented.insert(0, query)
            return augmented
        except Exception as e:
            logger.warning(f"[{get_trace_id()}] Query augmentation failed: {e}")
            return [query]

    def create_events(self, plan: QueryPlan) -> List[Dict[str, Any]]:
        """Create UI events for the planning steps.

        Returns:
            List of event dictionaries for UI
        """
        events = []

        # Intent detection event
        events.append({
            "type": "status",
            "step": "intent_detection",
            "message": f"Intent: {plan.intent} ({plan.intent_confidence:.0%} confidence)",
            "details": {
                "input": {"query_chars": len(plan.original_query)},
                "output": {
                    "intent": plan.intent,
                    "confidence": round(plan.intent_confidence, 2)
                }
            }
        })

        # Web search decision event
        if plan.needs_web_search:
            events.append({
                "type": "status",
                "step": "web_search_decision",
                "message": f"Web search needed: {plan.web_search_reason}",
                "details": {
                    "output": {
                        "needs_search": True,
                        "reason": plan.web_search_reason
                    }
                }
            })

        # Query augmentation event
        if len(plan.augmented_queries) > 1:
            events.append({
                "type": "status",
                "step": "query_augmentation",
                "message": f"Generated {len(plan.augmented_queries)} query variations",
                "details": {
                    "output": {
                        "query_count": len(plan.augmented_queries),
                        "queries": plan.augmented_queries[:3]  # First 3 for UI
                    }
                }
            })

        return events
