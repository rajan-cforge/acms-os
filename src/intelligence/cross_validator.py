"""Cross-Validator for ACMS Intelligence Pipeline.

Cognitive Principle: Error-Correcting Codes

The brain maintains consistency across memory stores. When the hippocampus
(Raw/episodic memory) and neocortex (Knowledge/semantic memory) have
conflicting information, error-correcting mechanisms resolve inconsistencies.

This module implements cross-validation between Raw and Knowledge entries:
1. Compute content similarity using text overlap
2. Compute embedding similarity using cosine distance
3. Flag inconsistencies for human review
4. Suggest resolution hints (prefer newer, prefer verified)

Expected Impact:
- Improved knowledge base accuracy
- Detection of outdated or conflicting information
- Human-in-the-loop correction for complex conflicts

Usage:
    from src.intelligence.cross_validator import CrossValidator

    validator = CrossValidator()
    result = await validator.validate(raw_entry, knowledge_entry)

    if not result.is_consistent:
        await validator.flag_for_review(result)
"""

import logging
import re
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class CrossValidatorConfig:
    """Configuration for cross-validation.

    Attributes:
        consistency_threshold: Score below this = inconsistent (0.0-1.0)
        embedding_weight: Weight for embedding similarity (0.0-1.0)
        content_weight: Weight for content similarity (0.0-1.0)
        min_overlap_tokens: Minimum tokens to consider for content comparison
    """
    consistency_threshold: float = 0.70
    embedding_weight: float = 0.4
    content_weight: float = 0.4
    date_weight: float = 0.2
    min_overlap_tokens: int = 3


@dataclass
class ValidationResult:
    """Result of cross-validation.

    Attributes:
        raw_id: ID of the Raw entry
        knowledge_id: ID of the Knowledge entry
        consistency_score: Overall consistency score (0.0-1.0)
        content_similarity: Content-based similarity (0.0-1.0)
        embedding_similarity: Embedding-based similarity (0.0-1.0)
        is_consistent: Whether entries are considered consistent
        resolution_hint: Suggested resolution if inconsistent
    """
    raw_id: str
    knowledge_id: str
    consistency_score: float
    content_similarity: float
    embedding_similarity: float
    is_consistent: bool
    resolution_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "raw_id": self.raw_id,
            "knowledge_id": self.knowledge_id,
            "consistency_score": self.consistency_score,
            "content_similarity": self.content_similarity,
            "embedding_similarity": self.embedding_similarity,
            "is_consistent": self.is_consistent,
            "resolution_hint": self.resolution_hint,
        }


class RawEntry(Protocol):
    """Protocol for Raw entries."""
    id: str
    content: str
    user_id: str
    created_at: datetime
    embedding: Optional[List[float]]


class KnowledgeEntry(Protocol):
    """Protocol for Knowledge entries."""
    id: str
    content: str
    user_id: str
    created_at: datetime
    confidence: float
    embedding: Optional[List[float]]


class CrossValidator:
    """Validates consistency between Raw and Knowledge entries.

    Implements cognitive "error-correcting codes" principle:
    detects inconsistencies between episodic (Raw) and
    semantic (Knowledge) memory stores.

    Usage:
        validator = CrossValidator()
        result = await validator.validate(raw, knowledge)
        if not result.is_consistent:
            await validator.flag_for_review(result)
    """

    def __init__(self, config: Optional[CrossValidatorConfig] = None):
        """Initialize cross-validator.

        Args:
            config: Optional configuration overrides
        """
        self.config = config or CrossValidatorConfig()

        # Statistics
        self._total_validated = 0
        self._consistent_count = 0
        self._inconsistent_count = 0

    def _compute_content_similarity(
        self,
        content_a: str,
        content_b: str,
    ) -> float:
        """Compute content similarity using token overlap.

        Uses Jaccard similarity on normalized tokens.

        Args:
            content_a: First content string
            content_b: Second content string

        Returns:
            Similarity score (0.0-1.0)
        """
        if not content_a or not content_b:
            return 0.0

        # Tokenize and normalize
        def tokenize(text: str) -> set:
            # Lowercase, remove punctuation, split on whitespace
            text = text.lower()
            text = re.sub(r'[^\w\s]', ' ', text)
            tokens = set(text.split())
            # Filter short tokens
            return {t for t in tokens if len(t) >= 2}

        tokens_a = tokenize(content_a)
        tokens_b = tokenize(content_b)

        if not tokens_a or not tokens_b:
            return 0.0

        # Jaccard similarity
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)

        if union == 0:
            return 0.0

        return intersection / union

    def _compute_embedding_similarity(
        self,
        embedding_a: Optional[List[float]],
        embedding_b: Optional[List[float]],
    ) -> float:
        """Compute embedding similarity using cosine distance.

        Args:
            embedding_a: First embedding vector
            embedding_b: Second embedding vector

        Returns:
            Cosine similarity (0.0-1.0)
        """
        if not embedding_a or not embedding_b:
            return 0.0

        if len(embedding_a) != len(embedding_b):
            return 0.0

        a = np.array(embedding_a)
        b = np.array(embedding_b)

        # Normalize
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        # Cosine similarity
        similarity = float(np.dot(a, b) / (norm_a * norm_b))

        # Clamp to [0, 1]
        return max(0.0, min(1.0, similarity))

    def _suggest_resolution(
        self,
        raw: Any,
        knowledge: Any,
        content_sim: float,
        embedding_sim: float,
    ) -> str:
        """Suggest resolution for inconsistency.

        Args:
            raw: Raw entry
            knowledge: Knowledge entry
            content_sim: Content similarity score
            embedding_sim: Embedding similarity score

        Returns:
            Resolution hint string
        """
        raw_date = getattr(raw, 'created_at', None)
        knowledge_date = getattr(knowledge, 'created_at', None)
        knowledge_confidence = getattr(knowledge, 'confidence', 0.5)

        hints = []

        # Check date difference
        if raw_date and knowledge_date:
            date_diff = (knowledge_date - raw_date).total_seconds()
            if date_diff > 86400:  # Knowledge is newer by > 1 day
                hints.append("prefer_newer_knowledge")
            elif date_diff < -86400:  # Raw is newer by > 1 day
                hints.append("prefer_newer_raw")

        # Check confidence
        if knowledge_confidence >= 0.9:
            hints.append("prefer_verified_knowledge")
        elif knowledge_confidence < 0.5:
            hints.append("low_confidence_knowledge")

        # Check similarity pattern
        if content_sim > 0.8 and embedding_sim < 0.5:
            hints.append("semantic_drift")
        elif content_sim < 0.3 and embedding_sim > 0.8:
            hints.append("paraphrased_content")

        if not hints:
            return "manual_review_required"

        return "; ".join(hints)

    async def validate(
        self,
        raw: Any,
        knowledge: Any,
    ) -> ValidationResult:
        """Validate consistency between Raw and Knowledge entries.

        Cognitive basis: Error-correcting codes in memory.

        Args:
            raw: Raw entry (episodic memory)
            knowledge: Knowledge entry (semantic memory)

        Returns:
            ValidationResult with consistency assessment
        """
        raw_content = getattr(raw, 'content', '')
        knowledge_content = getattr(knowledge, 'content', '')
        raw_embedding = getattr(raw, 'embedding', None)
        knowledge_embedding = getattr(knowledge, 'embedding', None)

        # Compute similarities
        content_sim = self._compute_content_similarity(
            raw_content, knowledge_content
        )
        embedding_sim = self._compute_embedding_similarity(
            raw_embedding, knowledge_embedding
        )

        # Compute overall consistency score
        consistency_score = (
            self.config.content_weight * content_sim +
            self.config.embedding_weight * embedding_sim +
            self.config.date_weight * 1.0  # Base score
        )

        # Normalize to [0, 1]
        total_weight = (
            self.config.content_weight +
            self.config.embedding_weight +
            self.config.date_weight
        )
        if total_weight > 0:
            consistency_score /= total_weight
        else:
            consistency_score = 0.0

        is_consistent = consistency_score >= self.config.consistency_threshold

        # Suggest resolution if inconsistent
        resolution_hint = None
        if not is_consistent:
            resolution_hint = self._suggest_resolution(
                raw, knowledge, content_sim, embedding_sim
            )

        # Update statistics
        self._total_validated += 1
        if is_consistent:
            self._consistent_count += 1
        else:
            self._inconsistent_count += 1

        return ValidationResult(
            raw_id=getattr(raw, 'id', 'unknown'),
            knowledge_id=getattr(knowledge, 'id', 'unknown'),
            consistency_score=consistency_score,
            content_similarity=content_sim,
            embedding_similarity=embedding_sim,
            is_consistent=is_consistent,
            resolution_hint=resolution_hint,
        )

    async def batch_validate(
        self,
        pairs: List[Tuple[Any, Any]],
    ) -> List[ValidationResult]:
        """Validate multiple entry pairs.

        Args:
            pairs: List of (raw, knowledge) tuples

        Returns:
            List of ValidationResults
        """
        results = []
        for raw, knowledge in pairs:
            result = await self.validate(raw, knowledge)
            results.append(result)
        return results

    async def flag_if_inconsistent(
        self,
        result: ValidationResult,
    ) -> bool:
        """Flag inconsistency for review if needed.

        Args:
            result: Validation result

        Returns:
            True if flagged, False otherwise
        """
        if result.is_consistent:
            return False

        await self._flag_for_review(result)
        return True

    async def _flag_for_review(self, result: ValidationResult) -> None:
        """Create inconsistency flag in database.

        Args:
            result: Validation result to flag
        """
        try:
            from src.storage.database import get_session
            from sqlalchemy import text

            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO cross_validation_inconsistencies (
                            raw_id, knowledge_id, consistency_score,
                            resolution_hint, status, created_at
                        ) VALUES (
                            :raw_id, :knowledge_id, :score,
                            :hint, 'pending', NOW()
                        )
                    """),
                    {
                        "raw_id": result.raw_id,
                        "knowledge_id": result.knowledge_id,
                        "score": result.consistency_score,
                        "hint": result.resolution_hint,
                    }
                )
                await session.commit()

            logger.info(
                f"[CrossValidator] Flagged inconsistency: "
                f"raw={result.raw_id[:8]}... knowledge={result.knowledge_id[:8]}... "
                f"score={result.consistency_score:.2f}"
            )

        except ImportError:
            logger.debug("[CrossValidator] Database not available")
        except Exception as e:
            logger.error(f"[CrossValidator] Failed to flag: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics.

        Returns:
            Dict with total_validated, consistent_count, etc.
        """
        return {
            "total_validated": self._total_validated,
            "consistent_count": self._consistent_count,
            "inconsistent_count": self._inconsistent_count,
            "consistency_threshold": self.config.consistency_threshold,
            "consistency_rate": (
                self._consistent_count / self._total_validated
                if self._total_validated > 0 else 0.0
            ),
        }

    def reset_stats(self) -> None:
        """Reset statistics (for testing)."""
        self._total_validated = 0
        self._consistent_count = 0
        self._inconsistent_count = 0


# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Global instance
_validator_instance: Optional[CrossValidator] = None


def get_cross_validator() -> CrossValidator:
    """Get global cross-validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = CrossValidator()
    return _validator_instance
