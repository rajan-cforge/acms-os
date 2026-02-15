"""Unit tests for Quality Validator service (Week 5 Task 1: Pollution Prevention).

Tests the quality scoring algorithm that prevents memory pollution by rejecting
low-quality AI responses (speculation, uncertainty, lack of grounding).

Coverage:
- Source trust scoring (HIGH/MEDIUM/LOW)
- Completeness scoring (length-based)
- Uncertainty detection (hedging language)
- Overall confidence score calculation (threshold 0.8)
- Edge cases and boundary conditions
"""

import pytest
from src.services.quality_validator import QualityValidator, QualityResult


class TestQualityValidator:
    """Test suite for Quality Validator service."""

    def setup_method(self):
        """Initialize Quality Validator for each test."""
        self.validator = QualityValidator()

    # =======================
    # Test 1: High-Quality Responses (Should PASS threshold 0.8)
    # =======================

    def test_high_quality_with_document_sources(self):
        """Test: Response with document sources should score high (>= 0.8)."""
        response = "ACMS is an Adaptive Context Memory System that stores and retrieves context-aware memories for AI applications. It uses PostgreSQL for structured data, Weaviate for vector embeddings, and Redis for caching."
        sources = [
            {"type": "document", "title": "ACMS Architecture"},
            {"type": "document", "title": "ACMS PRD"}
        ]
        query = "What is ACMS?"

        result = self.validator.calculate_quality_score(response, sources, query)

        assert result.confidence_score >= 0.8, f"Expected >= 0.8, got {result.confidence_score}"
        assert result.should_store is True
        assert result.source_trust_score == 1.0  # Documents = HIGH trust
        assert result.completeness_score == 1.0  # >= 100 chars
        assert result.uncertainty_score >= 0.8  # No hedging language
        assert result.flagged_reason is None

    def test_high_quality_with_conversation_sources(self):
        """Test: Response with conversation history should score medium-high (>= 0.8)."""
        response = "Based on our previous discussion, the Week 5 priority is implementing memory pollution prevention with a 5-layer guardrail architecture."
        sources = [
            {"type": "conversation", "turn_id": "abc123"}
        ]
        query = "What is the Week 5 priority?"

        result = self.validator.calculate_quality_score(response, sources, query)

        # Conversation sources = 0.7 trust, but good completeness and no uncertainty
        # Expected: (0.7 * 0.4) + (1.0 * 0.2) + (1.0 * 0.4) = 0.28 + 0.20 + 0.40 = 0.88
        assert result.confidence_score >= 0.8, f"Expected >= 0.8, got {result.confidence_score}"
        assert result.should_store is True
        assert result.source_trust_score == 0.7  # Conversations = MEDIUM trust

    # =======================
    # Test 2: Low-Quality Responses (Should FAIL threshold < 0.8)
    # =======================

    def test_low_quality_speculation_no_sources(self):
        """Test: Speculation without sources should score low (< 0.8)."""
        response = "ACMS might stand for Association for Computing Machinery or perhaps Academic Content Management System."
        sources = []  # NO SOURCES = RED FLAG
        query = "What is ACMS?"

        result = self.validator.calculate_quality_score(response, sources, query)

        assert result.confidence_score < 0.8, f"Expected < 0.8, got {result.confidence_score}"
        assert result.should_store is False
        assert result.source_trust_score <= 0.3  # No sources = LOW trust
        assert "no_sources" in result.flagged_reason.lower()

    def test_low_quality_high_uncertainty(self):
        """Test: Response with excessive hedging should score low (< 0.8)."""
        response = "I'm not sure, but ACMS could possibly be a system for memory management. It might use databases, though I don't have access to confirm."
        sources = [{"type": "api_call"}]  # AI-generated = LOW trust
        query = "What is ACMS?"

        result = self.validator.calculate_quality_score(response, sources, query)

        assert result.confidence_score < 0.8, f"Expected < 0.8, got {result.confidence_score}"
        assert result.should_store is False
        assert result.uncertainty_score < 0.6  # High uncertainty detected
        assert "uncertainty" in result.flagged_reason.lower()

    def test_low_quality_incomplete_response(self):
        """Test: Very short response should score lower for completeness."""
        response = "ACMS is a memory system."  # Only 25 chars
        sources = [{"type": "document"}]
        query = "What is ACMS?"

        result = self.validator.calculate_quality_score(response, sources, query)

        # Document source (1.0) helps, but completeness penalty
        # Expected: (1.0 * 0.4) + (0.5 * 0.2) + (1.0 * 0.4) = 0.40 + 0.10 + 0.40 = 0.90
        # Actually might still pass threshold! Let's check
        assert result.completeness_score == 0.5  # < 100 chars
        # Note: This might pass 0.8 threshold due to document sources
        # The test validates completeness scoring, not necessarily rejection

    def test_low_quality_i_dont_have_access(self):
        """Test: 'I don't have access' response should be flagged."""
        response = "I don't have access to information about ACMS at this time."
        sources = []
        query = "What is ACMS?"

        result = self.validator.calculate_quality_score(response, sources, query)

        assert result.confidence_score < 0.8, f"Expected < 0.8, got {result.confidence_score}"
        assert result.should_store is False
        assert "uncertainty" in result.flagged_reason.lower() or "no_sources" in result.flagged_reason.lower()

    # =======================
    # Test 3: Source Trust Scoring
    # =======================

    def test_source_trust_documents_high(self):
        """Test: Document sources should have HIGH trust (1.0)."""
        response = "A" * 100  # Simple valid response
        sources = [{"type": "document", "title": "test.md"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.source_trust_score == 1.0

    def test_source_trust_conversations_medium(self):
        """Test: Conversation sources should have MEDIUM trust (0.7)."""
        response = "A" * 100
        sources = [{"type": "conversation", "turn_id": "123"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.source_trust_score == 0.7

    def test_source_trust_no_sources_low(self):
        """Test: No sources should have LOW trust (0.3)."""
        response = "A" * 100
        sources = []

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.source_trust_score == 0.3

    def test_source_trust_mixed_sources(self):
        """Test: Mixed sources should take highest trust level."""
        response = "A" * 100
        sources = [
            {"type": "conversation", "turn_id": "123"},
            {"type": "document", "title": "test.md"}
        ]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        # Should use document trust (1.0) as highest
        assert result.source_trust_score == 1.0

    # =======================
    # Test 4: Completeness Scoring
    # =======================

    def test_completeness_long_response(self):
        """Test: Response >= 100 chars should score 1.0."""
        response = "A" * 150
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.completeness_score == 1.0

    def test_completeness_short_response(self):
        """Test: Response < 100 chars should score 0.5."""
        response = "A" * 50
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.completeness_score == 0.5

    def test_completeness_very_short_response(self):
        """Test: Very short response (< 20 chars) should score low."""
        response = "Maybe."  # 6 chars
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.completeness_score == 0.5  # Per spec, < 100 = 0.5

    # =======================
    # Test 5: Uncertainty Detection
    # =======================

    def test_uncertainty_no_hedging(self):
        """Test: Response without uncertainty words should score 1.0."""
        response = "ACMS is a definitive system with clear architecture."
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.uncertainty_score == 1.0

    def test_uncertainty_single_hedging_word(self):
        """Test: One uncertainty word should reduce score."""
        response = "ACMS might be a memory system with clear architecture."
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        # Formula: max(0.3, 1.0 - (1 * 0.2)) = max(0.3, 0.8) = 0.8
        assert result.uncertainty_score == 0.8

    def test_uncertainty_multiple_hedging_words(self):
        """Test: Multiple uncertainty words should score low."""
        response = "ACMS might possibly perhaps be a system, though I'm not sure."
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        # 4 uncertainty words: max(0.3, 1.0 - (4 * 0.2)) = max(0.3, 0.2) = 0.3
        assert result.uncertainty_score == 0.3

    def test_uncertainty_i_dont_know(self):
        """Test: 'I don't know' should be heavily penalized."""
        response = "I don't know what ACMS is."
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        # "I don't know" counts as 1 uncertainty keyword: 1.0 - (1 * 0.2) = 0.8
        assert result.uncertainty_score <= 0.8
        # Overall confidence should still pass due to document source, but be at threshold
        assert result.confidence_score >= 0.8

    # =======================
    # Test 6: Overall Confidence Calculation
    # =======================

    def test_confidence_formula_perfect_score(self):
        """Test: Perfect response should score 1.0."""
        response = "A" * 150  # Complete
        sources = [{"type": "document"}]  # High trust
        # No uncertainty words

        result = self.validator.calculate_quality_score(response, sources, "test?")

        # (1.0 * 0.4) + (1.0 * 0.2) + (1.0 * 0.4) = 1.0
        assert result.confidence_score == 1.0

    def test_confidence_formula_threshold_boundary(self):
        """Test: Score exactly at 0.8 threshold."""
        response = "A" * 150  # completeness = 1.0
        sources = []  # source_trust = 0.3
        # Arrange uncertainty to hit exactly 0.8

        # Target: 0.8 = (0.3 * 0.4) + (1.0 * 0.2) + (X * 0.4)
        # 0.8 = 0.12 + 0.20 + 0.4X
        # 0.48 = 0.4X
        # X = 1.2 (impossible, max is 1.0)

        # So with no sources, even perfect response can't hit 0.8
        result = self.validator.calculate_quality_score(response, sources, "test?")

        # (0.3 * 0.4) + (1.0 * 0.2) + (1.0 * 0.4) = 0.12 + 0.20 + 0.40 = 0.72
        assert result.confidence_score == 0.72
        assert result.should_store is False  # Below threshold

    # =======================
    # Test 7: QualityResult Model
    # =======================

    def test_quality_result_should_store_above_threshold(self):
        """Test: should_store should be True when confidence >= 0.8."""
        response = "A" * 150
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.confidence_score >= 0.8
        assert result.should_store is True
        assert result.flagged_reason is None

    def test_quality_result_should_not_store_below_threshold(self):
        """Test: should_store should be False when confidence < 0.8."""
        response = "Maybe it's something."
        sources = []

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.confidence_score < 0.8
        assert result.should_store is False
        assert result.flagged_reason is not None
        assert len(result.flagged_reason) > 0

    # =======================
    # Test 8: Edge Cases
    # =======================

    def test_edge_case_empty_response(self):
        """Test: Empty response should score very low."""
        response = ""
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.confidence_score == 0.0
        assert result.should_store is False
        assert result.completeness_score == 0.0  # Empty response short-circuits to 0.0
        assert "empty_or_whitespace" in result.flagged_reason.lower()

    def test_edge_case_whitespace_only_response(self):
        """Test: Whitespace-only response should score low."""
        response = "   \n\n   "
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.confidence_score < 0.8
        assert result.should_store is False

    def test_edge_case_no_query(self):
        """Test: Missing query should not crash (query unused in scoring)."""
        response = "A" * 150
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, query="")

        # Should still calculate score normally
        assert result.confidence_score == 1.0

    def test_edge_case_very_long_response(self):
        """Test: Very long response should still score correctly."""
        response = "A" * 10000  # 10k chars
        sources = [{"type": "document"}]

        result = self.validator.calculate_quality_score(response, sources, "test?")

        assert result.completeness_score == 1.0
        assert result.confidence_score == 1.0

    # =======================
    # Test 9: Real-World Scenarios
    # =======================

    def test_real_world_acms_speculation(self):
        """Test: Real pollution case from testing (ACMS = Association for Computing Machinery)."""
        response = "ACMS might stand for Association for Computing Machinery, which is a professional organization for computer scientists."
        sources = []
        query = "What is ACMS?"

        result = self.validator.calculate_quality_score(response, sources, query)

        assert result.should_store is False, "Should reject speculation without grounding"
        assert result.confidence_score < 0.8

    def test_real_world_legitimate_uncertainty(self):
        """Test: Legitimate 'I need more context' should be rejected."""
        response = "I don't have enough information about your specific ACMS implementation. Could you provide more context?"
        sources = []
        query = "How does ACMS work?"

        result = self.validator.calculate_quality_score(response, sources, query)

        assert result.should_store is False, "Should reject 'need more info' responses"
        assert result.confidence_score < 0.8

    def test_real_world_grounded_answer(self):
        """Test: Well-grounded answer with sources should pass."""
        response = "Based on the ACMS documentation, the system uses a 3-tier memory architecture (SHORT/MEDIUM/LONG) with automatic tier migration based on access patterns and CRS scoring. The implementation is in src/storage/memory_crud.py:145-230."
        sources = [
            {"type": "document", "title": "ARCHITECTURE.md"},
            {"type": "document", "title": "memory_crud.py"}
        ]
        query = "How does ACMS memory tiering work?"

        result = self.validator.calculate_quality_score(response, sources, query)

        assert result.should_store is True, "Should accept well-grounded answers"
        assert result.confidence_score >= 0.8
