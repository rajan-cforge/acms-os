"""
Pattern Detection Engine for Enterprise Intelligence (Week 6 Task 3)

Finds recurring organizational patterns across memory_items using:
1. TF-IDF Vectorization: Convert text to numerical features
2. DBSCAN Clustering: Group similar memories semantically
3. Trend Analysis: Detect increasing/stable/decreasing patterns
4. Cost Quantification: Calculate business impact

Adapted to work with memory_items table (all conversations stored there).
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import logging

from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.cluster import DBSCAN
import numpy as np

from src.intelligence.categorizer import MemoryCategory
from src.intelligence.priority_scorer import PriorityScorer

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Detected organizational pattern"""
    pattern_id: str
    category: MemoryCategory
    description: str  # Human-readable summary
    mentions: int  # Frequency (how many memories mention this)
    memory_ids: List[str]  # IDs of memories in this pattern
    negative_feedback_rate: float  # % thumbs down
    trend_30day: float  # Change rate (-1.0 to +1.0)
    estimated_impact: float  # Business impact (0-10 scale)
    priority_score: float  # Overall priority (0-10)
    detected_at: datetime


class PatternDetector:
    """
    Detect recurring organizational patterns in memory_items

    Uses TF-IDF + DBSCAN for semantic clustering.
    """

    def __init__(self, db_pool):
        """
        Initialize pattern detector

        Args:
            db_pool: AsyncPG connection pool
        """
        self.db_pool = db_pool
        self.priority_scorer = PriorityScorer()

    async def detect_patterns(
        self,
        lookback_days: int = 30,
        min_mentions: int = 3
    ) -> List[Pattern]:
        """
        Detect patterns across memory_items

        Args:
            lookback_days: How far back to analyze (default 30 days)
            min_mentions: Minimum frequency to be considered a pattern

        Returns:
            List of Pattern objects sorted by priority

        Example:
            >>> detector = PatternDetector(db_pool)
            >>> patterns = await detector.detect_patterns(lookback_days=30, min_mentions=3)
            >>> patterns[0].description
            'CI deployment takes 3 hours (mentioned 12 times)'
        """
        # Step 1: Fetch memories from lookback window
        memories = await self._fetch_memories(lookback_days)

        if len(memories) < min_mentions:
            logger.warning(f"Only {len(memories)} memories found, cannot detect patterns")
            return []

        # Step 2: Vectorize text using TF-IDF
        texts = [m['content'] for m in memories]
        memory_ids = [str(m['memory_id']) for m in memories]

        try:
            vectors, vectorizer = self._vectorize_texts(texts)
        except Exception as e:
            logger.error(f"Vectorization failed: {e}")
            return []

        # Step 3: Cluster similar memories using DBSCAN
        clusters = self._cluster_memories(vectors, min_samples=min_mentions)

        # Step 4: Extract patterns from clusters
        patterns = []

        for cluster_id in set(clusters):
            if cluster_id == -1:  # Skip noise
                continue

            # Get memories in this cluster
            cluster_indices = [i for i, c in enumerate(clusters) if c == cluster_id]

            if len(cluster_indices) < min_mentions:
                continue

            cluster_memories = [memories[i] for i in cluster_indices]
            cluster_memory_ids = [memory_ids[i] for i in cluster_indices]

            # Analyze cluster
            pattern = await self._analyze_cluster(
                cluster_memories,
                cluster_memory_ids,
                vectorizer,
                vectors[cluster_indices],
                lookback_days
            )

            if pattern:
                patterns.append(pattern)

        # Step 5: Filter out overly broad patterns (likely noise)
        filtered_patterns = []
        total_memories = len(memories)

        for pattern in patterns:
            # Calculate what % of memories this pattern represents
            coverage = len(pattern.memory_ids) / total_memories if total_memories > 0 else 0

            # Skip patterns that match >20% of all memories (too broad)
            if coverage > 0.20:
                logger.debug(f"Filtering broad pattern: {pattern.description} ({coverage:.1%} coverage)")
                continue

            # Skip patterns with gibberish descriptions
            words = pattern.description.split()
            if len(words) < 2:  # Single word patterns usually noise
                logger.debug(f"Filtering single-word pattern: {pattern.description}")
                continue

            # Skip if description has too many repeated words
            unique_words = len(set(words))
            if len(words) > 3 and unique_words / len(words) < 0.5:
                # >50% repeated words = "term long term long" style noise
                logger.debug(f"Filtering repeated-word pattern: {pattern.description}")
                continue

            filtered_patterns.append(pattern)

        patterns = filtered_patterns

        # Step 6: Sort by priority score
        patterns.sort(key=lambda p: p.priority_score, reverse=True)

        logger.info(f"Detected {len(patterns)} patterns from {len(memories)} memories (filtered from broader set)")

        return patterns

    async def _fetch_memories(self, lookback_days: int) -> List[Dict[str, Any]]:
        """Fetch memories from lookback window"""
        cutoff_date = datetime.now() - timedelta(days=lookback_days)

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    memory_id,
                    content,
                    created_at,
                    feedback_summary,
                    tags
                FROM memory_items
                WHERE created_at >= $1
                  AND memory_type = 'note'
                ORDER BY created_at DESC
            """, cutoff_date)

            return [dict(row) for row in rows]

    def _vectorize_texts(self, texts: List[str]) -> tuple:
        """
        Convert texts to TF-IDF vectors

        Args:
            texts: List of text strings

        Returns:
            (vectors, vectorizer) tuple
        """
        if not texts:
            raise ValueError("Cannot vectorize empty text list")

        # Adjust parameters based on corpus size
        if len(texts) < 5:
            # For small datasets, relax constraints
            min_df = 1
            max_df = 1.0
        else:
            min_df = 2
            max_df = 0.8

        # Custom stop words to filter domain-specific noise
        custom_stop_words = list(ENGLISH_STOP_WORDS) + [
            'like', 'would', 'could', 'get', 'make', 'want',
            'need', 'think', 'know', 'really', 'much', 'many',
            'also', 'well', 'way', 'thing', 'things', 'just',
            'long', 'term', 'short'  # Filter noise from overly broad patterns
        ]

        vectorizer = TfidfVectorizer(
            max_features=500,  # Limit vocabulary size
            min_df=min_df,  # Adjust based on corpus size
            max_df=max_df,  # Adjust based on corpus size
            stop_words=custom_stop_words,  # Custom stop words
            ngram_range=(1, 2),  # Unigrams and bigrams only
            token_pattern=r'\b[a-zA-Z]{3,}\b'  # Require 3+ letter words
        )

        vectors = vectorizer.fit_transform(texts)

        return vectors.toarray(), vectorizer

    def _cluster_memories(
        self,
        vectors: np.ndarray,
        min_samples: int = 3
    ) -> np.ndarray:
        """
        Cluster memory vectors using DBSCAN

        Args:
            vectors: TF-IDF vectors
            min_samples: Minimum cluster size

        Returns:
            Cluster labels array (-1 = noise)
        """
        # DBSCAN parameters:
        # - eps: Maximum distance between points in a cluster
        # - min_samples: Minimum points to form a cluster

        dbscan = DBSCAN(
            eps=0.2,  # Cosine similarity threshold (0.2 = stricter, more similar)
            min_samples=min_samples,
            metric='cosine'
        )

        clusters = dbscan.fit_predict(vectors)

        return clusters

    async def _analyze_cluster(
        self,
        memories: List[Dict[str, Any]],
        memory_ids: List[str],
        vectorizer,
        cluster_vectors: np.ndarray,
        lookback_days: int
    ) -> Optional[Pattern]:
        """
        Analyze a cluster to extract pattern

        Args:
            memories: Memories in cluster
            memory_ids: Memory IDs
            vectorizer: TF-IDF vectorizer
            cluster_vectors: Vectors for this cluster
            lookback_days: Lookback window

        Returns:
            Pattern object or None
        """
        # Calculate negative feedback rate
        negative_feedback_rate = self._calculate_negative_feedback(memories)

        # Extract key terms (TF-IDF features)
        description = self._extract_description(cluster_vectors, vectorizer)

        # Detect category
        category = self._detect_category(memories, negative_feedback_rate)

        # Calculate trend
        trend_30day = self._calculate_trend(memories, lookback_days)

        # Estimate business impact
        estimated_impact = self._estimate_impact(
            category,
            len(memories),
            negative_feedback_rate
        )

        # Calculate priority score
        priority_score = self.priority_scorer.calculate_score({
            'category': category.value if category else 'KNOWLEDGE_GAP',
            'mentions': len(memories),
            'negative_feedback_rate': negative_feedback_rate,
            'trend_30day': trend_30day,
            'estimated_impact': estimated_impact
        })

        pattern = Pattern(
            pattern_id=f"pattern_{hash(description) % 100000}",
            category=category or MemoryCategory.KNOWLEDGE_GAP,
            description=description,
            mentions=len(memories),
            memory_ids=memory_ids,
            negative_feedback_rate=negative_feedback_rate,
            trend_30day=trend_30day,
            estimated_impact=estimated_impact,
            priority_score=priority_score,
            detected_at=datetime.now()
        )

        return pattern

    def _calculate_negative_feedback(self, memories: List[Dict[str, Any]]) -> float:
        """
        Calculate % of memories with negative feedback

        Args:
            memories: List of memory dicts with feedback_summary

        Returns:
            Negative feedback rate (0.0-1.0)
        """
        if not memories:
            return 0.0

        negative_count = 0

        for memory in memories:
            feedback = memory.get('feedback_summary', {})

            if isinstance(feedback, dict):
                thumbs_down = feedback.get('thumbs_down', 0)
                regenerate = feedback.get('regenerate', 0)

                if thumbs_down > 0 or regenerate > 0:
                    negative_count += 1

        return negative_count / len(memories)

    def _extract_description(
        self,
        vectors: np.ndarray,
        vectorizer
    ) -> str:
        """
        Extract human-readable description from cluster

        Uses top TF-IDF terms as keywords.

        Args:
            vectors: Cluster vectors
            vectorizer: TF-IDF vectorizer

        Returns:
            Description string
        """
        # Average vector across cluster
        centroid = vectors.mean(axis=0)

        # Get top terms by TF-IDF weight
        feature_names = vectorizer.get_feature_names_out()
        top_indices = centroid.argsort()[-5:][::-1]  # Top 5 terms

        top_terms = [feature_names[i] for i in top_indices if centroid[i] > 0]

        if not top_terms:
            return "Pattern detected"

        return " ".join(top_terms[:3])  # Use top 3 terms

    def _detect_category(
        self,
        memories: List[Dict[str, Any]],
        negative_feedback_rate: float
    ) -> MemoryCategory:
        """
        Detect category based on patterns

        Uses heuristics:
        - High negative feedback + "slow", "takes long" → PRODUCTIVITY_BLOCKER
        - Questions ("where", "how", "what") + high regenerate → KNOWLEDGE_GAP
        - "bug", "error", "broken" → QUALITY_ISSUE
        - Positive feedback → POSITIVE_TREND or INNOVATION_IDEA
        """
        # Sample some memory contents for analysis
        sample_texts = [m['content'].lower() for m in memories[:10]]
        combined_text = " ".join(sample_texts)

        # Check for productivity blockers
        if negative_feedback_rate > 0.5 and any(
            keyword in combined_text
            for keyword in ['slow', 'takes long', 'waiting', 'blocked', 'stuck', 'delay']
        ):
            return MemoryCategory.PRODUCTIVITY_BLOCKER

        # Check for quality issues
        if any(
            keyword in combined_text
            for keyword in ['bug', 'error', 'broken', 'crash', 'fail', 'issue']
        ):
            return MemoryCategory.QUALITY_ISSUE

        # Check for knowledge gaps
        if any(
            keyword in combined_text
            for keyword in ['how', 'where', 'what', 'why', 'docs', 'documentation', '?']
        ):
            return MemoryCategory.KNOWLEDGE_GAP

        # Check for innovation/positive
        if negative_feedback_rate < 0.2 and any(
            keyword in combined_text
            for keyword in ['idea', 'proposal', 'suggest', 'improve', 'could we', 'feature']
        ):
            return MemoryCategory.INNOVATION_IDEA

        # Default
        return MemoryCategory.KNOWLEDGE_GAP

    def _calculate_trend(
        self,
        memories: List[Dict[str, Any]],
        lookback_days: int
    ) -> float:
        """
        Calculate 30-day trend

        Returns:
            Trend rate (-1.0 to +1.0)
            - Positive: Increasing mentions (getting worse)
            - Negative: Decreasing mentions (getting better)
            - Zero: Stable
        """
        if len(memories) < 2:
            return 0.0

        # Sort by created_at
        sorted_memories = sorted(memories, key=lambda m: m['created_at'])

        # Split into first half and second half
        midpoint = len(sorted_memories) // 2
        first_half = sorted_memories[:midpoint]
        second_half = sorted_memories[midpoint:]

        if len(first_half) == 0:
            return 0.0

        # Calculate rate of change
        change_rate = (len(second_half) - len(first_half)) / len(first_half)

        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, change_rate))

    def _estimate_impact(
        self,
        category: MemoryCategory,
        mentions: int,
        negative_feedback_rate: float
    ) -> float:
        """
        Estimate business impact (0-10 scale)

        Based on category, frequency, and negative feedback.

        Args:
            category: Pattern category
            mentions: Frequency
            negative_feedback_rate: % negative feedback

        Returns:
            Impact score (0-10)
        """
        # Base score from frequency
        frequency_score = min(10, mentions / 2)  # 20 mentions = max

        # Amplify by negative feedback
        feedback_multiplier = 1.0 + negative_feedback_rate

        # Category weight
        category_weights = {
            MemoryCategory.PRODUCTIVITY_BLOCKER: 1.5,
            MemoryCategory.QUALITY_ISSUE: 1.3,
            MemoryCategory.KNOWLEDGE_GAP: 1.0,
            MemoryCategory.INNOVATION_IDEA: 0.8,
            MemoryCategory.POSITIVE_TREND: 0.5
        }

        category_weight = category_weights.get(category, 1.0)

        # Calculate final impact
        impact = frequency_score * feedback_multiplier * category_weight

        # Clamp to 0-10
        return min(10.0, max(0.0, impact))


async def detect_patterns(db_pool, lookback_days: int = 30) -> List[Pattern]:
    """
    Convenience function to detect patterns

    Args:
        db_pool: Database pool
        lookback_days: Lookback window

    Returns:
        List of Pattern objects

    Example:
        >>> patterns = await detect_patterns(db_pool, lookback_days=30)
        >>> print(f"Found {len(patterns)} patterns")
    """
    detector = PatternDetector(db_pool)
    return await detector.detect_patterns(lookback_days=lookback_days)
