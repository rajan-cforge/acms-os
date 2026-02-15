"""Memory Quality Gate - Validates content before storage.

Phase 1: Quality validation to prevent memory pollution.

Scoring factors:
- Content length (too short = low quality)
- Information density (repetitive = penalized)
- Uncertainty language (hedging = penalized)
- Q&A format detection (misclassification prevention)
- Source trust level

Usage:
    gate = MemoryQualityGate(threshold=0.8)
    decision = gate.evaluate(candidate)

    if decision.should_store:
        await memory_service.create_memory(...)
    else:
        logger.info(f"Rejected: {decision.reason}")
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, List
from collections import Counter

from src.memory.models import MemoryType, CandidateMemory

logger = logging.getLogger(__name__)


@dataclass
class QualityDecision:
    """Result of quality evaluation."""
    score: float  # 0.0 to 1.0
    should_store: bool
    reason: Optional[str]
    suggested_type: Optional[MemoryType]

    def to_dict(self):
        """Convert to dict for JSON serialization."""
        return {
            "score": self.score,
            "should_store": self.should_store,
            "reason": self.reason,
            "suggested_type": self.suggested_type.value if self.suggested_type else None
        }


class MemoryQualityGate:
    """Quality gate for memory storage decisions.

    Evaluates candidate memories and decides:
    1. Should this content be stored?
    2. Is the memory type correct?
    3. What's the quality score?

    Prevents:
    - Short, meaningless content
    - Repetitive text
    - Hedging/uncertain language
    - Misclassified Q&A (Q&A stored as SEMANTIC)
    """

    # Q&A format patterns
    QA_PATTERNS = [
        r'^Q:\s*.+\n+A:\s*.+',  # "Q: ... A: ..." format
        r'^User:\s*.+\n+Assistant:\s*.+',  # Conversation format
        r'^Query:\s*.+\n+Response:\s*.+',  # Query format
        r'^Question:\s*.+\n+Answer:\s*.+',  # Question/Answer format
        r'^\*\*Q:\*\*\s*.+\n+\*\*A:\*\*\s*.+',  # Markdown Q&A
    ]

    # Uncertainty keywords (hedging language)
    UNCERTAINTY_KEYWORDS = [
        "might", "could", "possibly", "perhaps", "maybe",
        "i'm not sure", "i don't know", "i don't have access",
        "i cannot", "i'm unable", "uncertain", "unclear",
        "not certain", "probably", "likely", "unlikely"
    ]

    # Minimum content lengths by type
    MIN_LENGTH = {
        MemoryType.SEMANTIC: 20,
        MemoryType.EPISODIC: 10,
        MemoryType.CACHE_ENTRY: 30,
        MemoryType.DOCUMENT: 50
    }

    # Quality thresholds by type
    TYPE_THRESHOLDS = {
        MemoryType.SEMANTIC: 0.8,
        MemoryType.EPISODIC: 0.6,
        MemoryType.CACHE_ENTRY: 0.6,
        MemoryType.DOCUMENT: 0.7
    }

    def __init__(self, threshold: float = 0.8):
        """Initialize quality gate.

        Args:
            threshold: Default quality threshold (0.0-1.0)
        """
        self.threshold = threshold
        logger.info(f"[QualityGate] Initialized with threshold={threshold}")

    def evaluate(self, candidate: CandidateMemory) -> QualityDecision:
        """Evaluate candidate memory quality.

        Args:
            candidate: CandidateMemory to evaluate

        Returns:
            QualityDecision with score and recommendation
        """
        scores = []
        reasons = []

        # 1. Length check
        length_score, length_reason = self._score_length(candidate)
        scores.append(length_score)
        if length_reason:
            reasons.append(length_reason)

        # 2. Information density (repetition penalty)
        density_score, density_reason = self._score_density(candidate)
        scores.append(density_score)
        if density_reason:
            reasons.append(density_reason)

        # 3. Uncertainty language penalty
        uncertainty_score, uncertainty_reason = self._score_uncertainty(candidate)
        scores.append(uncertainty_score)
        if uncertainty_reason:
            reasons.append(uncertainty_reason)

        # 4. Q&A format check (for SEMANTIC type)
        qa_check, qa_reason, suggested_type = self._check_qa_format(candidate)
        if qa_check < 1.0:
            scores.append(qa_check)
            if qa_reason:
                reasons.append(qa_reason)

        # 5. Source trust level
        source_score = self._score_source(candidate)
        scores.append(source_score)

        # Calculate final score (weighted average)
        final_score = sum(scores) / len(scores) if scores else 0.0

        # Determine threshold based on memory type
        type_threshold = self.TYPE_THRESHOLDS.get(candidate.memory_type, self.threshold)
        should_store = final_score >= type_threshold

        # Build reason string
        reason = "; ".join(reasons) if reasons and not should_store else None

        decision = QualityDecision(
            score=round(final_score, 3),
            should_store=should_store,
            reason=reason,
            suggested_type=suggested_type
        )

        logger.debug(
            f"[QualityGate] Evaluated: score={decision.score}, "
            f"store={decision.should_store}, type={candidate.memory_type.value}"
        )

        return decision

    def is_qa_format(self, text: str) -> bool:
        """Check if text matches Q&A format patterns.

        Args:
            text: Content to check

        Returns:
            True if matches Q&A pattern
        """
        for pattern in self.QA_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return True
        return False

    def suggest_type(self, candidate: CandidateMemory) -> MemoryType:
        """Suggest correct memory type based on content.

        Args:
            candidate: CandidateMemory to analyze

        Returns:
            Suggested MemoryType
        """
        # If content is Q&A format but not CACHE_ENTRY, suggest CACHE_ENTRY
        if self.is_qa_format(candidate.text):
            if candidate.memory_type != MemoryType.CACHE_ENTRY:
                return MemoryType.CACHE_ENTRY

        # If has conversation_id context, suggest EPISODIC
        if candidate.context.get("conversation_id"):
            if candidate.memory_type != MemoryType.CACHE_ENTRY:
                return MemoryType.EPISODIC

        # Otherwise, keep original type
        return candidate.memory_type

    def _score_length(self, candidate: CandidateMemory) -> tuple[float, Optional[str]]:
        """Score based on content length.

        Returns:
            (score, reason) tuple
        """
        min_len = self.MIN_LENGTH.get(candidate.memory_type, 20)
        text_len = len(candidate.text)

        if text_len < min_len:
            score = max(0.2, text_len / min_len)
            return score, f"Content too short ({text_len} chars, min {min_len})"

        # Bonus for substantial content (up to 200 chars)
        if text_len >= 200:
            return 1.0, None
        elif text_len >= 100:
            return 0.9, None
        else:
            return 0.8, None

    def _score_density(self, candidate: CandidateMemory) -> tuple[float, Optional[str]]:
        """Score based on information density (penalize repetition).

        Returns:
            (score, reason) tuple
        """
        words = candidate.text.lower().split()
        if not words:
            return 0.0, "Empty content"

        # Count word frequencies
        word_counts = Counter(words)
        unique_words = len(word_counts)
        total_words = len(words)

        # Unique ratio: 1.0 = all unique, 0.0 = all same word
        unique_ratio = unique_words / total_words if total_words > 0 else 0

        if unique_ratio < 0.3:
            return 0.3, "Content is highly repetitive"
        elif unique_ratio < 0.5:
            return 0.6, "Content has repetitive patterns"
        else:
            return 1.0, None

    def _score_uncertainty(self, candidate: CandidateMemory) -> tuple[float, Optional[str]]:
        """Score based on uncertainty/hedging language.

        Returns:
            (score, reason) tuple
        """
        text_lower = candidate.text.lower()

        uncertainty_count = sum(
            1 for keyword in self.UNCERTAINTY_KEYWORDS
            if keyword in text_lower
        )

        if uncertainty_count == 0:
            return 1.0, None
        elif uncertainty_count == 1:
            return 0.8, None
        elif uncertainty_count == 2:
            return 0.6, "Contains hedging language"
        else:
            return max(0.3, 1.0 - uncertainty_count * 0.15), "High uncertainty in content"

    def _check_qa_format(self, candidate: CandidateMemory) -> tuple[float, Optional[str], Optional[MemoryType]]:
        """Check for Q&A format misclassification.

        Returns:
            (score, reason, suggested_type) tuple
        """
        is_qa = self.is_qa_format(candidate.text)

        if is_qa:
            if candidate.memory_type == MemoryType.SEMANTIC:
                # Q&A stored as SEMANTIC is wrong!
                return 0.5, "Q&A format detected - should be CACHE_ENTRY", MemoryType.CACHE_ENTRY
            elif candidate.memory_type == MemoryType.CACHE_ENTRY:
                # Q&A as CACHE_ENTRY is correct
                return 1.0, None, None
            else:
                # Other types with Q&A - suggest CACHE_ENTRY
                return 0.7, "Q&A format - consider CACHE_ENTRY type", MemoryType.CACHE_ENTRY

        return 1.0, None, None

    def _score_source(self, candidate: CandidateMemory) -> float:
        """Score based on source trust level.

        Returns:
            Score from 0.0 to 1.0
        """
        source_map = {
            "user": 0.9,        # User-provided = high trust
            "extracted": 0.8,  # System-extracted = good trust
            "imported": 0.85,  # Imported docs = good trust
            "ai": 0.6,         # AI-generated = lower trust
            "system": 0.7,     # System = medium trust
        }

        return source_map.get(candidate.source, 0.5)
