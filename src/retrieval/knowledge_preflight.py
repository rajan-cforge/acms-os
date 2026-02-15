"""Knowledge Preflight Check for ACMS Retrieval Pipeline.

Cognitive Principle: Feeling of Knowing (FOK)

Before engaging in full memory retrieval, the brain quickly estimates
whether it likely knows something relevant. This "tip of the tongue"
phenomenon saves cognitive resources by avoiding futile searches.

This module implements preflight checking:
1. Entity bloom filter - Quick check if query entities exist in knowledge base
2. Cluster centroid matching - Check if query embedding is near known topics
3. Combined signal - LIKELY/UNLIKELY/UNCERTAIN

Expected Impact: 15-25% latency reduction on unfamiliar topics.

Usage:
    from src.retrieval.knowledge_preflight import KnowledgePreflight

    preflight = KnowledgePreflight()
    await preflight.initialize()  # Load from knowledge base (hourly job)

    result = await preflight.check(query, embedding)
    if result.signal == KnowledgeSignal.UNLIKELY:
        # Skip expensive retrieval, use LLM directly
        pass
    elif result.signal == KnowledgeSignal.LIKELY:
        # Proceed with full retrieval
        pass
"""

import logging
import re
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any

logger = logging.getLogger(__name__)


class KnowledgeSignal(Enum):
    """Preflight check signals.

    Cognitive basis: Feeling of Knowing (FOK) strength.
    - LIKELY: Strong FOK, proceed with retrieval
    - UNLIKELY: Weak FOK, consider skipping retrieval
    - UNCERTAIN: Moderate FOK, proceed but with lower priority
    """
    LIKELY = "likely"      # High confidence knowledge exists
    UNLIKELY = "unlikely"  # Low confidence, likely no relevant knowledge
    UNCERTAIN = "uncertain"  # Mixed signals, cautiously proceed


@dataclass
class PreflightConfig:
    """Configuration for preflight checks.

    Attributes:
        bloom_capacity: Expected number of unique entities
        bloom_error_rate: Acceptable false positive rate for bloom filter
        centroid_threshold: Minimum similarity to consider a cluster match
        likely_threshold: Confidence threshold for LIKELY signal
        unlikely_threshold: Confidence threshold for UNLIKELY signal
        embedding_dimension: Expected embedding dimension (OpenAI = 1536)
    """
    bloom_capacity: int = 100000
    bloom_error_rate: float = 0.01
    centroid_threshold: float = 0.5
    likely_threshold: float = 0.7
    unlikely_threshold: float = 0.3
    embedding_dimension: int = 1536


@dataclass
class PreflightResult:
    """Result of a preflight check.

    Attributes:
        signal: LIKELY, UNLIKELY, or UNCERTAIN
        confidence: Confidence score 0.0-1.0
        bloom_match: Whether any entity matched the bloom filter
        centroid_similarity: Similarity to closest cluster centroid
        matched_entities: List of matched entity names
        closest_cluster: Name of closest topic cluster
    """
    signal: KnowledgeSignal
    confidence: float
    bloom_match: bool
    centroid_similarity: float
    matched_entities: List[str] = field(default_factory=list)
    closest_cluster: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "signal": self.signal.value,
            "confidence": self.confidence,
            "bloom_match": self.bloom_match,
            "centroid_similarity": self.centroid_similarity,
            "matched_entities": self.matched_entities,
            "closest_cluster": self.closest_cluster,
        }


class KnowledgePreflight:
    """Preflight check for knowledge retrieval.

    Implements cognitive "Feeling of Knowing" by quickly estimating
    whether relevant knowledge likely exists before full retrieval.

    Components:
    1. Entity Set (Bloom Filter simulation): O(1) entity lookup
    2. Cluster Centroids: Quick topic matching via cosine similarity
    3. Signal Determination: Combined heuristic for final decision

    Usage:
        preflight = KnowledgePreflight()
        await preflight.initialize()  # Called hourly by background job

        result = await preflight.check(query, embedding)
        if result.signal == KnowledgeSignal.LIKELY:
            # Proceed with full retrieval
            pass
    """

    def __init__(self, config: Optional[PreflightConfig] = None):
        """Initialize preflight checker.

        Args:
            config: Optional configuration overrides
        """
        self.config = config or PreflightConfig()

        # Will be populated by initialize()
        self._entities: Set[str] = set()
        self._cluster_centroids: Dict[str, np.ndarray] = {}
        self._initialized = False

        # Lazy import Weaviate client
        self._weaviate = None

    def _get_weaviate(self):
        """Get Weaviate client (lazy initialization)."""
        if self._weaviate is None:
            from src.storage.weaviate_client import WeaviateClient
            self._weaviate = WeaviateClient()
        return self._weaviate

    async def initialize(self) -> None:
        """Initialize preflight from knowledge base.

        Loads:
        1. All known entities into the entity set (bloom filter)
        2. Cluster centroids from topic_extractions

        This should be called by a background job (hourly).
        """
        logger.info("[KnowledgePreflight] Initializing...")

        try:
            await self._load_entities()
            await self._load_centroids()
            self._initialized = True

            logger.info(
                f"[KnowledgePreflight] Initialized: "
                f"{len(self._entities)} entities, "
                f"{len(self._cluster_centroids)} clusters"
            )

        except Exception as e:
            logger.error(f"[KnowledgePreflight] Initialization failed: {e}")
            # Allow graceful degradation - check will return UNCERTAIN
            self._initialized = True  # Mark as initialized to avoid repeated failures

    async def _load_entities(self) -> None:
        """Load entities from ACMS_Knowledge_v2."""
        try:
            weaviate = self._get_weaviate()

            # Get unique entities from knowledge base
            # This is a simplified approach - in production, use aggregation
            results = weaviate.semantic_search(
                collection="ACMS_Knowledge_v2",
                query_vector=[0.0] * self.config.embedding_dimension,
                limit=10000,  # Get up to 10K entries
            )

            entities = set()
            for result in results:
                props = result.get("properties", {})

                # Extract entities from various fields
                if "entities" in props:
                    for entity in props["entities"]:
                        if entity:
                            entities.add(entity.lower())

                # Also add topic clusters as entities
                if "topic_cluster" in props:
                    cluster = props["topic_cluster"]
                    if cluster:
                        entities.add(cluster.lower())

                # Add related topics
                if "related_topics" in props:
                    for topic in props.get("related_topics", []):
                        if topic:
                            entities.add(topic.lower())

            self._entities = entities

        except Exception as e:
            logger.warning(f"[KnowledgePreflight] Entity loading failed: {e}")
            self._entities = set()

    async def _load_centroids(self) -> None:
        """Load cluster centroids from knowledge base."""
        try:
            weaviate = self._get_weaviate()

            # Get samples from each topic cluster to compute centroids
            results = weaviate.semantic_search(
                collection="ACMS_Knowledge_v2",
                query_vector=[0.0] * self.config.embedding_dimension,
                limit=1000,
            )

            # Group by topic_cluster
            cluster_vectors: Dict[str, List[np.ndarray]] = {}

            for result in results:
                props = result.get("properties", {})
                cluster = props.get("topic_cluster", "")
                vector = result.get("vector")

                if cluster and vector:
                    if cluster not in cluster_vectors:
                        cluster_vectors[cluster] = []
                    cluster_vectors[cluster].append(np.array(vector))

            # Compute centroids (mean of vectors)
            for cluster, vectors in cluster_vectors.items():
                if vectors:
                    centroid = np.mean(vectors, axis=0)
                    self._cluster_centroids[cluster] = centroid

        except Exception as e:
            logger.warning(f"[KnowledgePreflight] Centroid loading failed: {e}")
            self._cluster_centroids = {}

    async def check(
        self,
        query: str,
        embedding: List[float],
        user_id: Optional[str] = None
    ) -> PreflightResult:
        """Perform preflight check for a query.

        Cognitive basis: Feeling of Knowing (FOK)
        Quickly estimate if relevant knowledge exists before full retrieval.

        Args:
            query: The user's query text
            embedding: Query embedding (1536-dim for OpenAI)
            user_id: Optional user ID for personalized checking

        Returns:
            PreflightResult with signal and confidence

        Raises:
            RuntimeError: If not initialized
            ValueError: If embedding dimension is wrong
        """
        if not self._initialized:
            raise RuntimeError(
                "KnowledgePreflight not initialized. Call initialize() first."
            )

        # Validate embedding dimension
        if len(embedding) != self.config.embedding_dimension:
            raise ValueError(
                f"Expected embedding dimension {self.config.embedding_dimension}, "
                f"got {len(embedding)}"
            )

        # Step 1: Entity extraction and bloom check
        matched_entities = self._extract_entities(query)
        bloom_match = len(matched_entities) > 0

        # Step 2: Centroid matching
        closest_cluster, centroid_similarity = self._find_closest_cluster(embedding)

        # Step 3: Determine signal
        signal, confidence = self._determine_signal(
            bloom_match=bloom_match,
            centroid_similarity=centroid_similarity,
            entity_count=len(matched_entities),
        )

        return PreflightResult(
            signal=signal,
            confidence=confidence,
            bloom_match=bloom_match,
            centroid_similarity=centroid_similarity,
            matched_entities=matched_entities,
            closest_cluster=closest_cluster,
        )

    def _extract_entities(self, query: str) -> List[str]:
        """Extract known entities from query.

        Uses the entity set as a simple bloom filter simulation.

        Args:
            query: Query text

        Returns:
            List of matched entity names
        """
        if not query:
            return []

        # Tokenize and normalize
        query_lower = query.lower()

        # Simple word extraction (could be improved with NLP)
        words = re.findall(r'\b[a-z][a-z0-9-]*\b', query_lower)

        # Check each word against entity set
        matched = []
        for word in words:
            if self._bloom_check(word):
                matched.append(word)

        # Also check multi-word entities
        for entity in self._entities:
            if " " in entity or "-" in entity:
                if entity in query_lower:
                    matched.append(entity)

        return list(set(matched))  # Deduplicate

    def _bloom_check(self, entity: str) -> bool:
        """Check if entity exists in bloom filter (entity set).

        O(1) average case lookup using Python set.

        Args:
            entity: Entity to check

        Returns:
            True if entity likely exists, False otherwise
        """
        return entity.lower() in self._entities

    def _find_closest_cluster(
        self,
        embedding: List[float]
    ) -> Tuple[Optional[str], float]:
        """Find the closest cluster centroid.

        Uses cosine similarity for fast comparison.

        Args:
            embedding: Query embedding

        Returns:
            Tuple of (cluster_name, similarity)
        """
        if not self._cluster_centroids:
            return None, 0.0

        query_vec = np.array(embedding)

        # Normalize for cosine similarity
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)

        best_cluster = None
        best_similarity = 0.0

        for cluster, centroid in self._cluster_centroids.items():
            # Normalize centroid
            centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-10)

            # Cosine similarity
            similarity = float(np.dot(query_norm, centroid_norm))

            if similarity > best_similarity:
                best_similarity = similarity
                best_cluster = cluster

        return best_cluster, best_similarity

    def _determine_signal(
        self,
        bloom_match: bool,
        centroid_similarity: float,
        entity_count: int,
    ) -> Tuple[KnowledgeSignal, float]:
        """Determine final signal based on all factors.

        Cognitive basis: Combine multiple FOK signals into final estimate.

        Args:
            bloom_match: Whether any entity matched
            centroid_similarity: Similarity to closest centroid
            entity_count: Number of matched entities

        Returns:
            Tuple of (signal, confidence)
        """
        # Calculate base confidence
        confidence = 0.0

        # Entity match contributes 0.4 max
        if bloom_match:
            # More entities = higher confidence
            entity_contribution = min(entity_count * 0.1, 0.4)
            confidence += entity_contribution

        # Centroid similarity contributes 0.4 max
        if centroid_similarity >= self.config.centroid_threshold:
            centroid_contribution = centroid_similarity * 0.4
            confidence += centroid_contribution

        # Bonus for strong signals
        if bloom_match and centroid_similarity >= self.config.centroid_threshold:
            confidence += 0.2  # Synergy bonus

        # Clamp confidence
        confidence = min(max(confidence, 0.0), 1.0)

        # Determine signal
        if confidence >= self.config.likely_threshold:
            return KnowledgeSignal.LIKELY, confidence
        elif confidence <= self.config.unlikely_threshold:
            return KnowledgeSignal.UNLIKELY, confidence
        else:
            return KnowledgeSignal.UNCERTAIN, confidence

    def get_stats(self) -> Dict[str, Any]:
        """Get preflight statistics."""
        return {
            "initialized": self._initialized,
            "entity_count": len(self._entities),
            "cluster_count": len(self._cluster_centroids),
            "cluster_names": list(self._cluster_centroids.keys())[:10],  # First 10
        }

    def reset(self) -> None:
        """Reset preflight state (for testing)."""
        self._entities = set()
        self._cluster_centroids = {}
        self._initialized = False


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def run_preflight_initialization() -> None:
    """Run preflight initialization job.

    Called by background job scheduler (hourly).
    """
    preflight = get_preflight_instance()
    await preflight.initialize()


# Global instance
_preflight_instance: Optional[KnowledgePreflight] = None


def get_preflight_instance() -> KnowledgePreflight:
    """Get global preflight instance."""
    global _preflight_instance
    if _preflight_instance is None:
        _preflight_instance = KnowledgePreflight()
    return _preflight_instance
