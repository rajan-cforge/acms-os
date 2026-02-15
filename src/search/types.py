"""
Type definitions for ACMS search interfaces.

This module defines TypedDict contracts for all search-related data structures
to ensure type safety and prevent interface mismatches between components.

Usage:
    from src.search.types import SearchExplanation, SearchResult

    explanation: SearchExplanation = {
        "query": "How to build REST API?",
        "query_intent": "HOWTO",
        "results_returned": 10,
        ...
    }
"""

from typing import TypedDict, Dict, List, Any, Optional, Literal
from datetime import datetime


# Query Intent Types
QueryIntentType = Literal[
    "EXPLORATORY",      # "everything about", "tell me about"
    "BIOGRAPHICAL",     # "who is", "tell me about [person]"
    "HOWTO",           # "how to", "steps to"
    "FACTUAL",         # "what is", "define"
    "TROUBLESHOOT"     # "error", "broken", "fix"
]


# Pipeline Stage Status Types
PipelineStageStatus = Literal[
    "success",    # Stage completed successfully
    "miss",       # Cache miss
    "hit",        # Cache hit
    "skipped",    # Stage was skipped
    "error"       # Stage encountered an error
]


class RankingSignals(TypedDict):
    """
    Individual ranking signal values for a search result.

    Used for transparency - shows why a result ranked where it did.
    """
    semantic_similarity: float  # 0.0-1.0 (vector distance)
    source_boost: float         # 1.0-1.30 (quality multiplier)
    freshness_boost: float      # 0.0-1.0 (time decay)
    feedback_score: float       # 0.0-1.0 (user ratings)
    diversity_bonus: float      # 0.0-1.0 (source variety)


class RankingWeights(TypedDict):
    """
    Weights for the multi-signal ranking formula.

    These define how much each signal contributes to the final score.
    Total must sum to 1.0.
    """
    semantic_weight: float       # Default: 0.40 (40%)
    source_boost_weight: float   # Default: 0.20 (20%)
    freshness_weight: float      # Default: 0.15 (15%)
    feedback_weight: float       # Default: 0.15 (15%)
    diversity_weight: float      # Default: 0.10 (10%)


class TopResult(TypedDict):
    """
    Summary of the top-ranked search result.

    Used in SearchExplanation to show why the #1 result won.
    """
    source_type: Optional[str]              # "memory", "conversation_thread", etc.
    relevance: Optional[float]              # Raw semantic similarity (0.0-1.0)
    boosted_score: Optional[float]          # Final score after all signals applied
    ranking_signals: RankingSignals         # Individual signal values


class SearchConfig(TypedDict, total=False):
    """
    Configuration for search behavior.

    Controls diversity enforcement, ranking toggles, and result limits.

    Note: total=False means all fields are optional
    """
    limit: int                      # Max results to return (default: 10)
    min_threads: int                # Min conversation threads (default: 0)
    min_turns: int                  # Min conversation turns (default: 0)
    min_memories: int               # Min memory items (default: 0)
    diversity_mode: str             # "strict", "balanced", "disabled"
    enable_recency_boost: bool      # Apply freshness decay (default: True)
    enable_intent_detection: bool   # Detect query intent (default: True)
    enable_feedback_boost: bool     # Use user ratings (default: True)
    max_per_tier: int              # Max results per tier before ranking (default: 50)
    privacy_filter: List[str]       # Privacy levels to include


class SearchExplanation(TypedDict):
    """
    Comprehensive explanation of search ranking decisions.

    Returned by UniversalSearchEngine.search() alongside results.
    Provides transparency into why results ranked as they did.

    **CRITICAL**: This is the interface contract between:
    - src/search/universal_search.py (producer)
    - src/api_server.py (consumer - analytics)
    - Desktop app (consumer - transparency UI)

    Used by:
    - api_server.py line 881-882 (analytics.memories_searched, memories_filtered)
    - api_server.py line 895 (response.explanation)
    - Desktop app (future - "Why these results?" UI)
    """
    query: str                              # Original query string
    query_intent: QueryIntentType           # Detected intent type
    results_returned: int                   # Number of results returned
    diversity_applied: bool                 # Was diversity enforcement used?
    diversity_mode: str                     # "strict", "balanced", or "disabled"
    source_distribution: Dict[str, int]     # Count by source type {"memory": 3, "thread": 2}
    tier_counts: Dict[str, int]             # Count by tier {"memories": 30, "threads": 30}
    ranking_signals: RankingWeights         # Signal weights used in formula
    top_result: Optional[TopResult]         # Summary of #1 ranked result
    config: SearchConfig                    # Search config that was used


class SearchResultMetadata(TypedDict, total=False):
    """
    Metadata attached to search results.

    Varies by source type:
    - conversation_thread: thread_id, title, message_count
    - conversation_turn: thread_id, turn_number, role
    - memory: original source, import date
    """
    thread_id: str              # For conversation sources
    turn_number: int            # For conversation_turn
    role: str                   # "user" or "assistant"
    conversation_title: str     # For conversation sources
    message_count: int          # For conversation_thread
    source: str                 # Original source of memory
    import_date: str           # When imported


class SearchResult(TypedDict):
    """
    Individual search result with ranking information.

    Returned by UniversalSearchEngine.search() as a list.
    """
    memory_id: str                      # Unique identifier
    content: str                        # Full content or excerpt
    source_type: str                    # "memory", "conversation_thread", "conversation_turn", etc.
    created_at: datetime                # When created/imported
    tags: List[str]                     # Associated tags
    privacy_level: str                  # "PUBLIC", "INTERNAL", "CONFIDENTIAL", "LOCAL_ONLY"
    relevance_score: float              # Raw semantic similarity (0.0-1.0)
    boosted_score: float                # Final score after multi-signal ranking
    ranking_signals: RankingSignals     # Individual signal values
    metadata: SearchResultMetadata      # Source-specific metadata


# Type aliases for common patterns
SearchResults = List[SearchResult]
TierCounts = Dict[str, int]  # {"memories": 30, "threads": 30, "turns": 30}
SourceDistribution = Dict[str, int]  # {"memory": 5, "conversation_thread": 3}


def validate_ranking_weights(weights: RankingWeights) -> None:
    """
    Validate that ranking weights sum to 1.0 (100%).

    Args:
        weights: RankingWeights dict to validate

    Raises:
        ValueError: If weights don't sum to 1.0 (within 0.01 tolerance)
    """
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        raise ValueError(
            f"Ranking weights must sum to 1.0, got {total:.2f}. "
            f"Weights: {weights}"
        )


def validate_query_intent(intent: str) -> QueryIntentType:
    """
    Validate and cast query intent string to typed literal.

    Args:
        intent: Intent string to validate

    Returns:
        Typed QueryIntentType

    Raises:
        ValueError: If intent is not a valid type
    """
    valid_intents = ["EXPLORATORY", "BIOGRAPHICAL", "HOWTO", "FACTUAL", "TROUBLESHOOT"]
    if intent not in valid_intents:
        raise ValueError(
            f"Invalid query intent: {intent}. "
            f"Must be one of: {', '.join(valid_intents)}"
        )
    return intent  # type: ignore


# Example usage (for documentation)
if __name__ == "__main__":
    # Example: Create a search explanation
    explanation: SearchExplanation = {
        "query": "How to build REST API with Python?",
        "query_intent": "HOWTO",
        "results_returned": 10,
        "diversity_applied": True,
        "diversity_mode": "balanced",
        "source_distribution": {
            "memory": 3,
            "conversation_thread": 4,
            "conversation_turn": 3
        },
        "tier_counts": {
            "memories": 30,
            "threads": 30,
            "turns": 30,
            "cache": 0
        },
        "ranking_signals": {
            "semantic_weight": 0.40,
            "source_boost_weight": 0.20,
            "freshness_weight": 0.15,
            "feedback_weight": 0.15,
            "diversity_weight": 0.10
        },
        "top_result": {
            "source_type": "conversation_turn",
            "relevance": 0.89,
            "boosted_score": 0.92,
            "ranking_signals": {
                "semantic_similarity": 0.89,
                "source_boost": 1.25,
                "freshness_boost": 0.85,
                "feedback_score": 0.50,
                "diversity_bonus": 0.10
            }
        },
        "config": {
            "limit": 10,
            "min_threads": 2,
            "min_turns": 2,
            "min_memories": 1,
            "diversity_mode": "balanced"
        }
    }

    # Validate weights
    validate_ranking_weights(explanation["ranking_signals"])

    # Validate intent
    intent = validate_query_intent("HOWTO")

    print("✅ Type definitions loaded successfully")
    print(f"   Example query intent: {intent}")
    print(f"   Example results returned: {explanation['results_returned']}")


# ==============================================================================
# PIPELINE TRACKING INTERFACES
# ==============================================================================


class PipelineStage(TypedDict, total=False):
    """
    A single stage in the query processing pipeline.

    Provides transparency into how ACMS processes each query.
    Shows users where time is spent and costs are incurred.

    **Required Fields**:
        name: Stage identifier (e.g., "cache_check", "search", "llm_generation")
        status: Outcome of this stage ("success", "miss", "hit", "skipped", "error")
        latency_ms: Time spent in this stage (milliseconds)

    **Optional Fields**:
        cost: Financial cost of this stage (USD)
        cost_saved: Cost avoided (e.g., cache hit saves LLM cost)
        tokens_used: Token count (for LLM stages)
        tokens_saved: Tokens avoided (for cache hits)
        results_found: Number of results found (for search stages)
        intent_detected: Query intent (for search stages)
        model_used: AI model selected (for LLM stages)
        response_source: Where response came from (for LLM stages)
        sources_used: Data sources searched (for search stages)
        details: Additional stage-specific metadata

    **Producers**:
        - src/api_server.py (ask_question endpoint)

    **Consumers**:
        - Desktop app (pipeline visualization)
        - Analytics (performance monitoring)

    **Example**:
        cache_stage: PipelineStage = {
            "name": "cache_check",
            "status": "hit",
            "latency_ms": 45,
            "cost_saved": 0.024,
            "tokens_saved": 1500
        }
    """
    # Required fields
    name: str
    status: PipelineStageStatus
    latency_ms: float

    # Optional financial metrics
    cost: float
    cost_saved: float

    # Optional token metrics
    tokens_used: int
    tokens_saved: int

    # Optional search metrics
    results_found: int
    intent_detected: QueryIntentType
    sources_used: List[str]

    # Optional LLM metrics
    model_used: Optional[str]
    response_source: str

    # Additional metadata
    details: Dict[str, Any]


class Pipeline(TypedDict):
    """
    Complete pipeline execution tracking for a query.

    Shows the full lifecycle of how ACMS processed a question:
    1. Cache check (hit/miss)
    2. Search (if cache miss)
    3. LLM generation (if needed)

    **CRITICAL**: This is the interface contract for pipeline visibility.

    **Fields**:
        stages: List of pipeline stages in chronological order
        total_latency_ms: Sum of all stage latencies
        total_cost: Total financial cost (after savings)

    **Producers**:
        - src/api_server.py (ask_question endpoint)

    **Consumers**:
        - Desktop app (visual timeline component)
        - Dashboard (performance analytics)

    **Example**:
        pipeline: Pipeline = {
            "stages": [
                {
                    "name": "cache_check",
                    "status": "miss",
                    "latency_ms": 12,
                    "cost_saved": 0.0
                },
                {
                    "name": "search",
                    "status": "success",
                    "latency_ms": 234,
                    "results_found": 15,
                    "intent_detected": "HOWTO"
                },
                {
                    "name": "llm_generation",
                    "status": "success",
                    "latency_ms": 1850,
                    "model_used": "claude-sonnet-4.5",
                    "tokens_used": 2500,
                    "cost": 0.038
                }
            ],
            "total_latency_ms": 2096,
            "total_cost": 0.038
        }
    """
    stages: List[PipelineStage]
    total_latency_ms: float
    total_cost: float
