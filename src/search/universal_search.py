"""
UniversalSearchEngine - Unified search across all 5 ACMS storage tiers

This module provides a Google-quality search experience with:
- Multi-tier parallel searching (memories, threads, turns, cache)
- Query intent detection for context-aware ranking
- Source diversity guarantees
- Multi-signal ranking (relevance + freshness + source type + intent)
- Result explanation for transparency

Author: ACMS Team
Date: October 22, 2025
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
import logging

from src.privacy.filter import PrivacyFilter
from src.privacy.roles import UserRole
from src.privacy.pii_detector import PIIDetector

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Unified search result across all storage tiers"""
    memory_id: str  # Unique ID (e.g., "conv_abc", "turn_def", "memory_ghi")
    content: str  # Full text or preview
    source_type: str  # "memory", "conversation_thread", "conversation_turn", "qa_pair", "cache"
    relevance_score: float  # Base relevance (1 - COSINE distance)
    boosted_score: float  # After applying all boosts
    created_at: datetime
    tags: List[str]
    privacy_level: str

    # Metadata
    excerpt: str  # 200-char preview for UI
    metadata: Dict[str, Any]  # Additional context (e.g., thread_id, turn_number)

    # Ranking signals (for debugging)
    ranking_signals: Dict[str, float]  # {source_boost: 1.25, freshness: 1.05, diversity: 1.2}


@dataclass
class SearchConfig:
    """Configuration for search behavior"""
    limit: int = 10
    privacy_filter: List[str] = None
    diversity_mode: str = "balanced"  # "balanced", "relevance_only", "diverse"
    enable_recency_boost: bool = True
    enable_diversity_boost: bool = True
    enable_intent_detection: bool = True

    # Diversity constraints (minimum per source type)
    min_memories: int = 3
    min_threads: int = 2
    min_turns: int = 2

    def __post_init__(self):
        if self.privacy_filter is None:
            self.privacy_filter = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "LOCAL_ONLY"]


class QueryIntent:
    """Query intent detection for context-aware ranking"""

    EXPLORATORY = "EXPLORATORY"  # "everything about X", comprehensive
    BIOGRAPHICAL = "BIOGRAPHICAL"  # "who is", "tell me about"
    HOWTO = "HOWTO"  # "how to", tutorial
    FACTUAL = "FACTUAL"  # "what is", definitions
    TROUBLESHOOT = "TROUBLESHOOT"  # "error", "fix"
    GENERAL = "GENERAL"  # Default

    @staticmethod
    def detect(query: str) -> str:
        """
        Detect query intent from natural language

        Based on Google's query understanding principles:
        - Informational: seeks knowledge
        - Navigational: seeks specific resource
        - Transactional: seeks to do something
        """
        q = query.lower()

        # Comprehensive/exploratory (broadest scope)
        if any(w in q for w in ['everything', 'comprehensive', 'all about', 'complete', 'full']):
            return QueryIntent.EXPLORATORY

        # Biographical (person-focused)
        if any(w in q for w in ['who is', 'tell me about', 'biography', 'background', 'profile']):
            return QueryIntent.BIOGRAPHICAL

        # How-to/tutorial (step-by-step)
        if any(w in q for w in ['how to', 'how do i', 'how can i', 'tutorial', 'guide', 'steps']):
            return QueryIntent.HOWTO

        # Factual (definition/explanation)
        if any(w in q for w in ['what is', 'define', 'explain', 'meaning of']):
            return QueryIntent.FACTUAL

        # Troubleshooting (problem-solving)
        if any(w in q for w in ['error', 'fix', 'broken', 'not working', 'issue', 'problem', 'timeout', 'failed', 'crash']):
            return QueryIntent.TROUBLESHOOT

        return QueryIntent.GENERAL


class UniversalSearchEngine:
    """
    Unified search engine across all ACMS storage tiers

    Provides Google-quality search with:
    - Parallel tier searching
    - Multi-signal ranking
    - Source diversity guarantees
    - Intent-aware boosting
    """

    # Source type weights (quality signals)
    SOURCE_TYPE_WEIGHTS = {
        'qa_pair': 1.30,  # Promoted knowledge base (highest quality)
        'conversation_turn': 1.25,  # Specific facts (granular)
        'conversation_thread': 1.10,  # Full context (comprehensive)
        'cache': 1.05,  # Proven answers (validated)
        'memory': 1.00  # Baseline
    }

    def __init__(self, memory_crud, embeddings_service, vector_storage, semantic_cache=None):
        """
        Initialize UniversalSearchEngine

        Args:
            memory_crud: Memory CRUD operations
            embeddings_service: Embedding generation (OpenAI)
            vector_storage: Conversation vector storage
            semantic_cache: Optional semantic cache
        """
        self.memory_crud = memory_crud
        self.embeddings = embeddings_service
        self.vector_storage = vector_storage
        self.semantic_cache = semantic_cache

        logger.info("UniversalSearchEngine initialized")

    async def search(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        user_role: str = "member",
        config: Optional[SearchConfig] = None
    ) -> Tuple[List[SearchResult], Dict[str, Any]]:
        """
        Universal search across all tiers with smart ranking and privacy filtering

        Args:
            query: Search query
            user_id: Optional user ID for personalization
            user_role: User role for privacy filtering (admin/manager/lead/member/viewer)
            config: Search configuration

        Returns:
            (results, explanation) tuple where:
            - results: List of SearchResult objects (privacy-filtered)
            - explanation: Dict with ranking explanation for transparency
        """
        if config is None:
            config = SearchConfig()

        logger.info(f"[UniversalSearch] Query: {query[:100]}...")

        # Step 1: Detect query intent
        intent = QueryIntent.detect(query) if config.enable_intent_detection else QueryIntent.GENERAL
        logger.info(f"[UniversalSearch] Intent detected: {intent}")

        # Step 2: Adjust config based on intent
        adjusted_config = self._adjust_config_for_intent(config, intent)

        # Step 3: Generate query embedding (reused across all tiers)
        query_vector = self.embeddings.generate_embedding(query)

        # Step 4: Search all tiers in parallel
        tier_results = await self._search_all_tiers(
            query=query,
            query_vector=query_vector,
            user_id=user_id,
            config=adjusted_config
        )

        # Step 5: Merge and rank results
        merged_results = self._merge_tier_results(tier_results)

        # Step 6: Apply multi-signal boosting
        boosted_results = self._apply_ranking_boosts(
            results=merged_results,
            intent=intent,
            config=adjusted_config
        )

        # Step 7: Apply diversity constraints
        if config.diversity_mode != "relevance_only":
            final_results = self._apply_diversity_constraints(
                results=boosted_results,
                config=adjusted_config,
                mode=config.diversity_mode
            )
        else:
            final_results = sorted(boosted_results, key=lambda r: r.boosted_score, reverse=True)[:config.limit]

        # Step 8: Apply privacy filtering (WEEK 6 TASK 1)
        results_before_filtering = len(final_results)

        try:
            role = UserRole(user_role.lower()) if user_role else UserRole.MEMBER
        except ValueError:
            logger.warning(f"Invalid user_role '{user_role}', defaulting to MEMBER")
            role = UserRole.MEMBER

        privacy_filter = PrivacyFilter(role, str(user_id) if user_id else "anonymous")

        # Convert SearchResult objects to dict format for filtering
        result_dicts = [
            {
                "id": r.memory_id,
                "content": r.content,
                "privacy_level": r.privacy_level,
                "owner_id": r.metadata.get("owner_id") if r.metadata else None
            }
            for r in final_results
        ]

        # Filter by privacy
        filtered_dicts = privacy_filter.filter_results(result_dicts)
        filtered_ids = {d["id"] for d in filtered_dicts}

        # Keep only filtered results
        final_results = [r for r in final_results if r.memory_id in filtered_ids]

        results_after_filtering = len(final_results)
        filtered_count = results_before_filtering - results_after_filtering

        if filtered_count > 0:
            logger.info(f"[Privacy] Filtered {filtered_count} results (user_role={user_role}, user_id={user_id})")

        # Step 8.5: Apply PII masking (WEEK 6 TASK 2)
        pii_detector = PIIDetector()
        for result in final_results:
            # Mask PII in content and excerpt
            result.content = pii_detector.mask_text(result.content)
            result.excerpt = pii_detector.mask_text(result.excerpt)

        # Step 9: Calculate tier counts for explanation
        tier_counts = {}
        for tier_name, tier_result_list in tier_results.items():
            tier_counts[tier_name] = len(tier_result_list)

        # Step 10: Build explanation
        explanation = self._build_explanation(
            results=final_results,
            query=query,
            intent=intent,
            config=adjusted_config,
            tier_counts=tier_counts
        )

        # Add privacy info to explanation
        explanation['privacy_filtering'] = {
            'user_role': user_role,
            'results_before': results_before_filtering,
            'results_after': results_after_filtering,
            'filtered_count': filtered_count
        }

        logger.info(f"[UniversalSearch] Returning {len(final_results)} results (from {len(merged_results)} total, {filtered_count} filtered by privacy)")

        return final_results, explanation

    def _adjust_config_for_intent(self, config: SearchConfig, intent: str) -> SearchConfig:
        """Adjust search config based on detected intent"""
        adjusted = SearchConfig(**config.__dict__)  # Copy

        if intent == QueryIntent.EXPLORATORY:
            # User wants breadth - maximize diversity
            adjusted.min_threads = max(adjusted.min_threads, 4)
            adjusted.min_turns = max(adjusted.min_turns, 3)
            adjusted.diversity_mode = "diverse" if config.diversity_mode == "balanced" else config.diversity_mode
            logger.info(f"[Intent Adjustment] EXPLORATORY → min_threads=4, min_turns=3")

        elif intent == QueryIntent.BIOGRAPHICAL:
            # User wants comprehensive context - prefer full conversations
            adjusted.min_threads = max(adjusted.min_threads, 5)
            logger.info(f"[Intent Adjustment] BIOGRAPHICAL → min_threads=5")

        elif intent == QueryIntent.HOWTO:
            # User wants specific steps - prefer granular turns
            adjusted.min_turns = max(adjusted.min_turns, 4)
            logger.info(f"[Intent Adjustment] HOWTO → min_turns=4")

        elif intent == QueryIntent.TROUBLESHOOT:
            # User wants recent solutions - boost freshness
            adjusted.enable_recency_boost = True
            logger.info(f"[Intent Adjustment] TROUBLESHOOT → recency boost enabled")

        return adjusted

    async def _search_all_tiers(
        self,
        query: str,
        query_vector: List[float],
        user_id: Optional[UUID],
        config: SearchConfig
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search all storage tiers in parallel

        Returns dict mapping tier name to results:
        {
            'memories': [...],
            'threads': [...],
            'turns': [...],
            'cache': [...]
        }
        """
        # Launch all tier searches in parallel for performance
        tasks = {
            'memories': self._search_memories(query, user_id, config),
            'threads': self._search_threads(query_vector, config),
            'turns': self._search_turns(query_vector, config)
        }

        # Optional: include semantic cache
        if self.semantic_cache and config.enable_intent_detection:
            tasks['cache'] = self._search_cache(query, user_id)

        results = await asyncio.gather(*[tasks[k] for k in tasks.keys()], return_exceptions=True)

        tier_results = {}
        for i, tier_name in enumerate(tasks.keys()):
            if isinstance(results[i], Exception):
                logger.warning(f"[Tier Search] {tier_name} failed: {results[i]}")
                tier_results[tier_name] = []
            else:
                tier_results[tier_name] = results[i]
                logger.info(f"[Tier Search] {tier_name}: {len(results[i])} results")

        return tier_results

    async def _search_memories(self, query: str, user_id: Optional[UUID], config: SearchConfig) -> List[Dict[str, Any]]:
        """Search traditional memory items"""
        try:
            results = await self.memory_crud.search_memories(
                query=query,
                user_id=user_id,  # None = Universal Brain
                limit=config.limit * 3,  # Get extras for diversity
                privacy_filter=config.privacy_filter
            )

            # Convert to standard format
            return [
                {
                    'memory_id': r['memory_id'],
                    'content': r['content'],
                    'source_type': r.get('memory_type', 'memory'),  # qa_pair or memory
                    'relevance_score': r.get('crs_score', r.get('relevance_score', 0.5)),
                    'created_at': r['created_at'],
                    'tags': r.get('tags', []),
                    'privacy_level': r.get('privacy_level', 'PUBLIC'),
                    'metadata': {'distance': r.get('distance', 0.5)}
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

    async def _search_threads(self, query_vector: List[float], config: SearchConfig) -> List[Dict[str, Any]]:
        """Search conversation threads"""
        try:
            results = self.vector_storage.search_threads(
                query_vector=query_vector,
                limit=config.limit * 3
            )

            # Fetch metadata from PostgreSQL (already done in search_threads)
            # Results format: [{'properties': {...}, 'distance': 0.42}, ...]

            return [
                {
                    'memory_id': r['properties']['thread_id'],  # Use raw UUID
                    'content': r['properties']['content'],
                    'source_type': 'conversation_thread',
                    'relevance_score': 1 - r['distance'],
                    'created_at': r['properties'].get('created_at', datetime.utcnow()),
                    'tags': [r['properties'].get('source', 'unknown'), 'conversation'],
                    'privacy_level': 'PUBLIC',  # Conversations are user's data
                    'metadata': {
                        'thread_id': r['properties']['thread_id'],
                        'title': r['properties'].get('title', ''),
                        'turn_count': r['properties'].get('turn_count', 0),
                        'distance': r['distance']
                    }
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Thread search failed: {e}")
            return []

    async def _search_turns(self, query_vector: List[float], config: SearchConfig) -> List[Dict[str, Any]]:
        """Search conversation turns"""
        try:
            results = self.vector_storage.search_turns(
                query_vector=query_vector,
                limit=config.limit * 3
            )

            return [
                {
                    'memory_id': r['properties']['turn_id'],  # Use raw UUID
                    'content': r['properties']['content'],
                    'source_type': 'conversation_turn',
                    'relevance_score': 1 - r['distance'],
                    'created_at': r['properties'].get('created_at', datetime.utcnow()),
                    'tags': [r['properties'].get('source', 'unknown'), 'conversation_turn', r['properties'].get('role', 'unknown')],
                    'privacy_level': 'PUBLIC',
                    'metadata': {
                        'turn_id': r['properties']['turn_id'],
                        'thread_id': r['properties'].get('thread_id', ''),
                        'role': r['properties'].get('role', ''),
                        'turn_number': r['properties'].get('turn_number', 0),
                        'distance': r['distance']
                    }
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Turn search failed: {e}")
            return []

    async def _search_cache(self, query: str, user_id: Optional[UUID]) -> List[Dict[str, Any]]:
        """Search semantic cache (optional)"""
        try:
            cache_result = await self.semantic_cache.get(
                query=query,
                user_id=str(user_id) if user_id else "anonymous"
            )

            if cache_result:
                return [{
                    'memory_id': str(cache_result['cache_id']),  # Use raw UUID as string
                    'content': cache_result['answer'],
                    'source_type': 'cache',
                    'relevance_score': cache_result.get('similarity', 0.90),
                    'created_at': cache_result.get('created_at', datetime.utcnow()),
                    'tags': ['cache', 'validated'],
                    'privacy_level': 'PUBLIC',
                    'metadata': {'similarity': cache_result.get('similarity', 0.90)}
                }]
            return []
        except Exception as e:
            logger.error(f"Cache search failed: {e}")
            return []

    def _merge_tier_results(self, tier_results: Dict[str, List[Dict[str, Any]]]) -> List[SearchResult]:
        """Merge results from all tiers into unified format"""
        merged = []

        for tier_name, results in tier_results.items():
            for r in results:
                merged.append(SearchResult(
                    memory_id=r['memory_id'],
                    content=r['content'],
                    source_type=r['source_type'],
                    relevance_score=r['relevance_score'],
                    boosted_score=r['relevance_score'],  # Will be updated in boosting phase
                    created_at=r['created_at'] if isinstance(r['created_at'], datetime) else datetime.fromisoformat(str(r['created_at'])),
                    tags=r['tags'],
                    privacy_level=r['privacy_level'],
                    excerpt=r['content'][:200],
                    metadata=r['metadata'],
                    ranking_signals={}  # Will be populated in boosting phase
                ))

        logger.info(f"[Merge] Combined {len(merged)} results from {len(tier_results)} tiers")
        return merged

    def _apply_ranking_boost(
        self,
        result: SearchResult,
        intent: str,
        config: SearchConfig
    ) -> SearchResult:
        """
        Apply multi-signal ranking boosts to a single result.

        Convenience wrapper for _apply_ranking_boosts().
        Used by unit tests for granular testing of individual results.

        Args:
            result: Single SearchResult to boost
            intent: Query intent for context-aware ranking
            config: Search configuration

        Returns:
            SearchResult with boosted_score and ranking_signals populated
        """
        return self._apply_ranking_boosts([result], intent, config)[0]

    def _apply_ranking_boosts(
        self,
        results: List[SearchResult],
        intent: str,
        config: SearchConfig
    ) -> List[SearchResult]:
        """
        Apply multi-signal ranking boosts using weighted sum formula.

        Formula: semantic(40%) + source(20%) + freshness(15%) +
                 feedback(15%) + diversity(10%) = 100%

        Signals:
        1. Semantic similarity (40% weight) - Base relevance score
        2. Source type boost (20% weight) - Quality signal by source type
        3. Freshness boost (15% weight) - Recency bias based on intent
        4. Feedback score (15% weight) - User ratings/thumbs up/down
        5. Diversity bonus (10% weight) - Breadth across source types
        """
        for result in results:
            signals = {}

            # Signal 1: Semantic similarity (40% weight)
            # Base relevance from vector search
            semantic_score = result.relevance_score
            signals['semantic_similarity'] = semantic_score

            # Signal 2: Source type boost (20% weight)
            # Quality signal based on source type (returns 1.0-1.3x multiplier)
            source_weight = self._calculate_source_boost(result)
            # Store RAW weight for transparency (tests check this)
            signals['source_boost'] = source_weight

            # Signal 3: Freshness boost (15% weight)
            # Recency bias based on query intent (0.0-1.0 normalized)
            if config.enable_recency_boost:
                freshness_boost = self._calculate_freshness_boost_normalized(result.created_at, intent)
            else:
                freshness_boost = 0.5  # Neutral
            signals['freshness_boost'] = freshness_boost

            # Signal 4: User feedback score (15% weight)
            # Boost from thumbs up/down ratings (returns 0.0-1.0)
            feedback_score = self._calculate_feedback_boost(result)
            signals['feedback_score'] = feedback_score

            # Signal 5: Diversity bonus (10% weight)
            # Applied during diversity enforcement phase
            # For now, default to 0.0 (will be set later)
            diversity_bonus = 0.0
            signals['diversity_bonus'] = diversity_bonus

            # Calculate final weighted sum
            # Test expects: semantic*0.40 + source_boost*0.20 + freshness*0.15 + feedback*0.15 + diversity*0.10
            # Where signals contain the raw/normalized values that get weighted
            final_score = (
                semantic_score * 0.40 +      # 40% base relevance (0.0-1.0)
                source_weight * 0.20 +       # 20% source quality (1.0-1.3)
                freshness_boost * 0.15 +     # 15% freshness (0.0-1.0)
                feedback_score * 0.15 +      # 15% feedback (0.0-1.0)
                diversity_bonus * 0.10       # 10% diversity (0.0-1.0)
            )

            # Update result
            result.boosted_score = final_score
            result.ranking_signals = signals

            logger.debug(f"Ranking signals applied to {result.memory_id[:8]}: "
                        f"semantic={semantic_score:.3f}, source={source_weight:.3f}, "
                        f"freshness={freshness_boost:.3f}, feedback={feedback_score:.3f}, "
                        f"diversity={diversity_bonus:.3f} → boosted_score={final_score:.3f}")

        return results

    def _calculate_freshness_boost(self, created_at: datetime, intent: str) -> float:
        """Calculate freshness boost based on age and query intent"""
        # Handle both timezone-aware and timezone-naive datetimes
        now = datetime.utcnow()
        if created_at.tzinfo is not None:
            # created_at is timezone-aware, make now aware too
            from datetime import timezone
            now = datetime.now(timezone.utc)
            # Remove timezone info for comparison
            created_at = created_at.replace(tzinfo=None)
            now = now.replace(tzinfo=None)

        age_days = (now - created_at).days

        # Time-sensitive queries (more aggressive boost)
        if intent in [QueryIntent.TROUBLESHOOT]:
            if age_days <= 7:
                return 1.15  # 15% boost for very recent
            elif age_days <= 30:
                return 1.08
            else:
                return 1.0

        # Evergreen queries (no time bias)
        elif intent in [QueryIntent.FACTUAL, QueryIntent.HOWTO]:
            return 1.0  # Quality matters, not recency

        # Default: mild preference for recent
        else:
            if age_days <= 7:
                return 1.05
            else:
                return 1.0

    def _calculate_intent_boost(self, result: SearchResult, intent: str) -> float:
        """Calculate intent-based boost"""
        # EXPLORATORY: boost diverse sources
        if intent == QueryIntent.EXPLORATORY:
            if result.source_type == 'conversation_thread':
                return 1.15  # More full conversations for comprehensive view
            return 1.0

        # BIOGRAPHICAL: boost threads (full context)
        elif intent == QueryIntent.BIOGRAPHICAL:
            if result.source_type == 'conversation_thread':
                return 1.20
            return 1.0

        # HOWTO: boost turns (specific steps)
        elif intent == QueryIntent.HOWTO:
            if result.source_type == 'conversation_turn':
                return 1.30  # Strong boost for granular how-to steps
            return 1.0

        # FACTUAL: boost qa_pairs (definitions)
        elif intent == QueryIntent.FACTUAL:
            if result.source_type == 'qa_pair':
                return 1.25
            return 1.0

        # TROUBLESHOOT: boost recent qa_pairs and turns
        elif intent == QueryIntent.TROUBLESHOOT:
            if result.source_type in ['qa_pair', 'conversation_turn']:
                age_days = (datetime.utcnow() - result.created_at).days
                if age_days <= 30:
                    return 1.20
            return 1.0

        return 1.0  # No intent boost for GENERAL

    def _calculate_source_boost(self, result: SearchResult) -> float:
        """
        Calculate source type boost weight.

        Returns the raw quality multiplier for the source type (1.0-1.3x).
        This value is stored in ranking_signals for transparency.

        Returns:
            float: Source type weight (1.0 = baseline memory, 1.30 = qa_pair)
        """
        weights = {
            'qa_pair': 1.30,
            'conversation_turn': 1.25,
            'conversation_thread': 1.10,
            'cache': 1.05,
            'memory': 1.00
        }
        return weights.get(result.source_type, 1.00)

    def _calculate_freshness_boost_normalized(self, created_at: datetime, intent: str) -> float:
        """
        Calculate freshness boost normalized to 0-1 range for weighted sum.

        Different from _calculate_freshness_boost which returns multipliers (1.0-1.15x).
        This returns contribution values (0.0-1.0) for the 15% freshness weight.

        Args:
            created_at: When content was created
            intent: Query intent for context-aware decay

        Returns:
            float: Normalized freshness value (0.0 = old, 1.0 = very fresh)
        """
        # Handle both timezone-aware and timezone-naive datetimes
        now = datetime.utcnow()
        if created_at.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            created_at = created_at.replace(tzinfo=None)
            now = now.replace(tzinfo=None)

        age_days = (now - created_at).days

        # Time-sensitive queries (TROUBLESHOOT)
        if intent in [QueryIntent.TROUBLESHOOT]:
            if age_days <= 7:
                return 1.0  # Maximum freshness bonus
            elif age_days <= 30:
                return 0.5  # Moderate freshness bonus
            else:
                return 0.0  # No freshness bonus for old content

        # Evergreen queries (FACTUAL, HOWTO) - no time bias
        elif intent in [QueryIntent.FACTUAL, QueryIntent.HOWTO]:
            return 0.5  # Neutral - quality matters, not recency

        # Default: mild preference for recent
        else:
            if age_days <= 7:
                return 0.8  # Recent bonus
            elif age_days <= 30:
                return 0.5  # Moderate
            else:
                return 0.3  # Slight penalty for old

    def _calculate_feedback_boost(self, result: SearchResult) -> float:
        """
        Calculate boost from user feedback (thumbs up/down, ratings).

        Normalized to 0-1 range for weighted sum formula (15% weight).

        Args:
            result: SearchResult to calculate feedback for

        Returns:
            float: Normalized feedback score (0.0 = poor/no feedback, 1.0 = excellent)
        """
        # Check if result has feedback metadata
        if hasattr(result, 'feedback_rating') and result.feedback_rating:
            # Assuming 1-5 star rating
            return result.feedback_rating / 5.0
        elif result.metadata and 'feedback_score' in result.metadata:
            # Alternative: feedback stored in metadata
            return float(result.metadata['feedback_score'])
        else:
            # No feedback available - neutral score
            return 0.5  # Neutral (neither penalty nor bonus)

    def _apply_diversity_constraints(
        self,
        results: List[SearchResult],
        config: SearchConfig,
        mode: str
    ) -> List[SearchResult]:
        """
        Apply diversity constraints to ensure source variety

        Modes:
        - balanced: Ensure minimums while respecting relevance
        - diverse: Maximize diversity, even at cost of some relevance
        """
        # Sort by boosted score first
        sorted_results = sorted(results, key=lambda r: r.boosted_score, reverse=True)

        # Track what we've selected
        selected = []
        selected_types = {
            'memory': 0,
            'qa_pair': 0,
            'conversation_thread': 0,
            'conversation_turn': 0,
            'cache': 0
        }

        # Phase 1: Ensure minimums for each type
        for source_type, minimum in [
            ('conversation_thread', config.min_threads),
            ('conversation_turn', config.min_turns),
            ('memory', config.min_memories),
            ('qa_pair', 1)  # At least one KB entry if available
        ]:
            for result in sorted_results:
                if len(selected) >= config.limit:
                    break

                if result.source_type == source_type and selected_types[source_type] < minimum:
                    if result not in selected:
                        selected.append(result)
                        selected_types[result.source_type] += 1

                        # Apply diversity boost for forced selections
                        if mode == "diverse" and selected_types[source_type] < minimum:
                            result.boosted_score *= 1.2
                            if 'diversity' not in result.ranking_signals:
                                result.ranking_signals['diversity'] = 1.2

        # Phase 2: Fill remaining slots with highest scores
        for result in sorted_results:
            if len(selected) >= config.limit:
                break

            if result not in selected:
                selected.append(result)
                selected_types[result.source_type] += 1

        # Final sort by boosted score
        final = sorted(selected, key=lambda r: r.boosted_score, reverse=True)[:config.limit]

        logger.info(f"[Diversity] Selected: {dict(selected_types)} (mode={mode})")
        return final

    def _build_explanation(
        self,
        results: List[SearchResult],
        query: str,
        intent: str,
        config: SearchConfig,
        tier_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Build comprehensive ranking explanation for transparency.

        Args:
            results: Final ranked search results
            query: Original query string
            intent: Detected query intent
            config: Search configuration used
            tier_counts: Count of results from each tier/source type

        Returns:
            Dict with explanation of ranking decisions, signals, and distribution
        """
        # Calculate source distribution from results
        source_distribution = {}
        for result in results:
            source_distribution[result.source_type] = source_distribution.get(result.source_type, 0) + 1

        # Build explanation
        explanation = {
            "query": query,
            "query_intent": intent,
            "results_returned": len(results),
            "diversity_applied": config.diversity_mode != "relevance_only",
            "diversity_mode": config.diversity_mode,
            "source_distribution": source_distribution,
            "tier_counts": tier_counts,
            "ranking_signals": {
                "semantic_weight": 0.40,
                "source_boost_weight": 0.20,
                "freshness_weight": 0.15,
                "feedback_weight": 0.15,
                "diversity_weight": 0.10
            },
            "top_result": {
                "source_type": results[0].source_type if results else None,
                "relevance": round(results[0].relevance_score, 3) if results else None,
                "boosted_score": round(results[0].boosted_score, 3) if results else None,
                "ranking_signals": results[0].ranking_signals if results else {}
            } if results else None,
            "config": {
                "limit": config.limit,
                "min_threads": config.min_threads,
                "min_turns": config.min_turns,
                "min_memories": config.min_memories
            }
        }

        return explanation
