"""Quality Validator Service for Memory Pollution Prevention (Week 5 Task 1).

Implements 5-layer AI guardrail architecture to prevent low-quality AI responses
from being stored in ACMS memory system.

Scoring Algorithm:
    confidence_score = (source_trust * 0.4) + (completeness * 0.2) + (uncertainty * 0.4)

Threshold: 0.8
- Responses with confidence >= 0.8 are stored
- Responses with confidence < 0.8 are rejected and flagged

Source Trust Levels:
- HIGH (1.0): Document sources (grounded in code/docs)
- MEDIUM (0.7): Conversation history
- LOW (0.3): AI-generated without sources

Completeness:
- COMPLETE (1.0): Response >= 100 characters
- INCOMPLETE (0.5): Response < 100 characters

Uncertainty Detection:
- Penalizes hedging language: "might", "could", "possibly", "perhaps", "I'm not sure", "I don't know", etc.
- Formula: max(0.3, 1.0 - (uncertainty_count * 0.2))
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """Result of quality validation with detailed scoring breakdown."""

    confidence_score: float  # Overall confidence (0.0-1.0)
    should_store: bool  # True if >= 0.8 threshold
    source_trust_score: float  # Source trust component (0.0-1.0)
    completeness_score: float  # Completeness component (0.0-1.0)
    uncertainty_score: float  # Uncertainty component (0.0-1.0)
    flagged_reason: Optional[str]  # Reason if flagged (confidence < 0.8)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "confidence_score": self.confidence_score,
            "should_store": self.should_store,
            "source_trust_score": self.source_trust_score,
            "completeness_score": self.completeness_score,
            "uncertainty_score": self.uncertainty_score,
            "flagged_reason": self.flagged_reason,
        }


class QualityValidator:
    """Quality Validator service for pollution prevention."""

    # Quality threshold for storage decision
    CONFIDENCE_THRESHOLD = 0.8

    # Source trust levels
    SOURCE_TRUST_HIGH = 1.0  # Documents
    SOURCE_TRUST_MEDIUM = 0.7  # Conversations
    SOURCE_TRUST_LOW = 0.3  # No sources or AI-generated

    # Completeness threshold
    COMPLETENESS_THRESHOLD = 100  # characters

    # Uncertainty keywords (hedging language)
    UNCERTAINTY_KEYWORDS = [
        "might",
        "could",
        "possibly",
        "perhaps",
        "maybe",
        "I'm not sure",
        "I don't know",
        "I don't have access",
        "I cannot",
        "I'm unable",
        "uncertain",
        "unclear",
        "not certain",
    ]

    # Weighting factors (must sum to 1.0)
    WEIGHT_SOURCE_TRUST = 0.4
    WEIGHT_COMPLETENESS = 0.2
    WEIGHT_UNCERTAINTY = 0.4

    def __init__(self):
        """Initialize Quality Validator."""
        logger.info("Quality Validator initialized with threshold=%.2f", self.CONFIDENCE_THRESHOLD)

    def calculate_quality_score(
        self,
        response: str,
        sources: List[Dict],
        query: str
    ) -> QualityResult:
        """Calculate quality confidence score for a response.

        Args:
            response: AI-generated response text
            sources: List of sources used to generate response
                     Each source: {"type": "document"|"conversation"|"api_call", ...}
            query: Original user query (currently unused, reserved for future)

        Returns:
            QualityResult with detailed scoring breakdown and storage decision

        Algorithm:
            confidence_score = (source_trust * 0.4) + (completeness * 0.2) + (uncertainty * 0.4)

        Example:
            >>> validator = QualityValidator()
            >>> result = validator.calculate_quality_score(
            ...     response="ACMS is an Adaptive Context Memory System...",
            ...     sources=[{"type": "document", "title": "ARCHITECTURE.md"}],
            ...     query="What is ACMS?"
            ... )
            >>> result.confidence_score >= 0.8
            True
        """
        # EDGE CASE: Reject empty or whitespace-only responses immediately
        if not response or len(response.strip()) == 0:
            return QualityResult(
                confidence_score=0.0,
                should_store=False,
                source_trust_score=0.0,
                completeness_score=0.0,
                uncertainty_score=0.0,
                flagged_reason="empty_or_whitespace_response (confidence=0.00)"
            )

        # Calculate component scores
        source_trust_score = self._calculate_source_trust(sources)
        completeness_score = self._calculate_completeness(response)
        uncertainty_score = self._calculate_uncertainty(response)

        # Calculate weighted confidence score
        confidence_score = (
            source_trust_score * self.WEIGHT_SOURCE_TRUST +
            completeness_score * self.WEIGHT_COMPLETENESS +
            uncertainty_score * self.WEIGHT_UNCERTAINTY
        )

        # Ensure score is in valid range [0.0, 1.0]
        confidence_score = max(0.0, min(1.0, confidence_score))

        # Determine storage decision
        should_store = confidence_score >= self.CONFIDENCE_THRESHOLD

        # Generate flagged reason if rejected
        flagged_reason = None
        if not should_store:
            flagged_reason = self._generate_flagged_reason(
                confidence_score,
                source_trust_score,
                completeness_score,
                uncertainty_score,
                sources,
                response
            )

        return QualityResult(
            confidence_score=confidence_score,
            should_store=should_store,
            source_trust_score=source_trust_score,
            completeness_score=completeness_score,
            uncertainty_score=uncertainty_score,
            flagged_reason=flagged_reason,
        )

    def _calculate_source_trust(self, sources: List[Dict]) -> float:
        """Calculate source trust score based on source types.

        Args:
            sources: List of source dictionaries with "type" key

        Returns:
            Float score: 1.0 (document), 0.7 (conversation), 0.3 (none/api_call)

        Logic:
            - If any document sources exist: HIGH (1.0)
            - Else if any conversation sources exist: MEDIUM (0.7)
            - Else (no sources or only api_call): LOW (0.3)
        """
        if not sources:
            return self.SOURCE_TRUST_LOW

        # Check for document sources (highest trust)
        has_documents = any(s.get("type") == "document" for s in sources)
        if has_documents:
            return self.SOURCE_TRUST_HIGH

        # Check for conversation sources (medium trust)
        has_conversations = any(s.get("type") == "conversation" for s in sources)
        if has_conversations:
            return self.SOURCE_TRUST_MEDIUM

        # Default: no trusted sources
        return self.SOURCE_TRUST_LOW

    def _calculate_completeness(self, response: str) -> float:
        """Calculate completeness score based on response length.

        Args:
            response: Response text

        Returns:
            1.0 if >= 100 chars, 0.5 otherwise

        Rationale:
            Short responses often indicate incomplete or vague answers.
            100 character threshold balances conciseness with substance.
        """
        response_length = len(response.strip())

        if response_length >= self.COMPLETENESS_THRESHOLD:
            return 1.0
        else:
            return 0.5

    def _calculate_uncertainty(self, response: str) -> float:
        """Calculate uncertainty score by detecting hedging language.

        Args:
            response: Response text

        Returns:
            Float score: max(0.3, 1.0 - (uncertainty_count * 0.2))

        Algorithm:
            - Start at 1.0 (no uncertainty)
            - Subtract 0.2 for each uncertainty keyword found
            - Floor at 0.3 (minimum score)

        Examples:
            - No uncertainty words: 1.0
            - 1 word ("might"): 0.8
            - 2 words: 0.6
            - 3 words: 0.4
            - 4+ words: 0.3 (floor)
        """
        response_lower = response.lower()

        # Count occurrences of uncertainty keywords
        uncertainty_count = sum(
            1 for keyword in self.UNCERTAINTY_KEYWORDS
            if keyword.lower() in response_lower
        )

        # Calculate score with penalty per keyword
        uncertainty_score = 1.0 - (uncertainty_count * 0.2)

        # Apply floor of 0.3
        return max(0.3, uncertainty_score)

    def _generate_flagged_reason(
        self,
        confidence_score: float,
        source_trust_score: float,
        completeness_score: float,
        uncertainty_score: float,
        sources: List[Dict],
        response: str
    ) -> str:
        """Generate human-readable reason for why response was flagged.

        Args:
            confidence_score: Overall confidence score
            source_trust_score: Source trust component
            completeness_score: Completeness component
            uncertainty_score: Uncertainty component
            sources: Original sources list
            response: Response text

        Returns:
            String describing primary reasons for flagging

        Logic:
            Prioritizes issues in order:
            1. No sources (most critical)
            2. High uncertainty (hedging language)
            3. Incomplete response (too short)
            4. Low confidence (catch-all)
        """
        reasons = []

        # Check for no sources (critical)
        if not sources or source_trust_score <= self.SOURCE_TRUST_LOW:
            reasons.append("no_sources_or_low_trust")

        # Check for high uncertainty
        if uncertainty_score < 0.6:
            reasons.append("uncertainty_detected")

        # Check for incompleteness
        if completeness_score < 1.0:
            reasons.append("incomplete_response")

        # Fallback reason
        if not reasons:
            reasons.append("low_confidence")

        return ", ".join(reasons) + f" (confidence={confidence_score:.2f})"

    def should_store_response(self, response: str, sources: List[Dict], query: str) -> bool:
        """Convenience method: Returns True if response should be stored.

        Args:
            response: AI-generated response
            sources: Sources used for generation
            query: Original query

        Returns:
            Boolean indicating storage decision

        Example:
            >>> validator = QualityValidator()
            >>> validator.should_store_response("Well-grounded answer", [{"type": "document"}], "What?")
            True
        """
        result = self.calculate_quality_score(response, sources, query)
        return result.should_store

    def get_storage_metadata(self, response: str, sources: List[Dict], query: str) -> Dict:
        """Get metadata for storing quality-validated response in database.

        Args:
            response: AI-generated response
            sources: Sources used for generation
            query: Original query

        Returns:
            Dictionary with database fields:
                - confidence_score: float
                - flagged: bool
                - flagged_reason: str or None

        Example:
            >>> validator = QualityValidator()
            >>> metadata = validator.get_storage_metadata("Answer", [], "Q?")
            >>> metadata["flagged"]
            True
        """
        result = self.calculate_quality_score(response, sources, query)

        return {
            "confidence_score": result.confidence_score,
            "flagged": not result.should_store,
            "flagged_reason": result.flagged_reason,
        }
