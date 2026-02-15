"""Tests for Memory Quality Gate - TDD: Write tests FIRST.

Phase 1: Quality Gate Integration
Goal: Validate memories before storage, reject low-quality content

Run with: PYTHONPATH=. pytest tests/unit/memory/test_quality_gate.py -v
"""
import pytest
from uuid import uuid4

from src.memory.models import MemoryType, CandidateMemory
from src.memory.quality_gate import MemoryQualityGate, QualityDecision


class TestQualityGateInit:
    """Test Quality Gate initialization."""

    def test_gate_initializes_with_default_threshold(self):
        """Gate should initialize with 0.8 threshold by default."""
        gate = MemoryQualityGate()
        assert gate.threshold == 0.8

    def test_gate_accepts_custom_threshold(self):
        """Gate should accept custom threshold."""
        gate = MemoryQualityGate(threshold=0.6)
        assert gate.threshold == 0.6


class TestQualityDecision:
    """Test QualityDecision dataclass."""

    def test_decision_has_required_fields(self):
        """Decision should have score, should_store, and reason."""
        decision = QualityDecision(
            score=0.9,
            should_store=True,
            reason=None,
            suggested_type=None
        )
        assert decision.score == 0.9
        assert decision.should_store is True
        assert decision.reason is None


class TestQualityScoring:
    """Test quality scoring for different content types."""

    @pytest.fixture
    def gate(self):
        return MemoryQualityGate(threshold=0.8)

    def test_high_quality_semantic_passes(self, gate):
        """Informative semantic memory should score >= 0.8."""
        candidate = CandidateMemory(
            text="User prefers Python 3.11 for new projects due to pattern matching and improved error messages",
            memory_type=MemoryType.SEMANTIC,
            source="extracted"
        )

        decision = gate.evaluate(candidate)

        assert decision.score >= 0.8
        assert decision.should_store is True

    def test_short_content_rejected(self, gate):
        """Very short content should score < 0.8."""
        candidate = CandidateMemory(
            text="ok",
            memory_type=MemoryType.SEMANTIC,
            source="user"
        )

        decision = gate.evaluate(candidate)

        assert decision.score < 0.8
        assert decision.should_store is False
        assert "too short" in decision.reason.lower()

    def test_qa_format_detected(self, gate):
        """Q&A format in SEMANTIC should be flagged."""
        candidate = CandidateMemory(
            text="Q: What is Python?\n\nA: Python is a programming language",
            memory_type=MemoryType.SEMANTIC,  # Wrong type!
            source="ai"
        )

        decision = gate.evaluate(candidate)

        # Should suggest CACHE_ENTRY instead
        assert decision.suggested_type == MemoryType.CACHE_ENTRY

    def test_repetitive_content_penalized(self, gate):
        """Highly repetitive content should score lower."""
        candidate = CandidateMemory(
            text="test test test test test test test test test test",
            memory_type=MemoryType.SEMANTIC,
            source="user"
        )

        decision = gate.evaluate(candidate)

        # Highly repetitive content should be penalized (unique_ratio < 0.3)
        assert decision.score < 0.8

    def test_uncertainty_language_penalized(self, gate):
        """Hedging language should lower score."""
        candidate = CandidateMemory(
            text="I'm not sure, but maybe the user might possibly prefer Python perhaps",
            memory_type=MemoryType.SEMANTIC,
            source="ai"
        )

        decision = gate.evaluate(candidate)

        assert decision.score < 0.8
        assert decision.should_store is False

    def test_cache_entry_type_lenient(self, gate):
        """CACHE_ENTRY type should have different thresholds."""
        candidate = CandidateMemory(
            text="Q: What is X?\nA: X is Y with some details about the topic",
            memory_type=MemoryType.CACHE_ENTRY,
            source="ai"
        )

        decision = gate.evaluate(candidate)

        # Q&A is expected for CACHE_ENTRY - should pass
        assert decision.score >= 0.6  # Lower threshold for cache

    def test_document_type_allows_longer_content(self, gate):
        """DOCUMENT type should allow longer content without penalty."""
        long_content = "This is a detailed document. " * 50  # ~1500 chars

        candidate = CandidateMemory(
            text=long_content,
            memory_type=MemoryType.DOCUMENT,
            source="imported"
        )

        decision = gate.evaluate(candidate)

        assert decision.should_store is True


class TestQAPollutionDetection:
    """Test Q&A pollution detection."""

    @pytest.fixture
    def gate(self):
        return MemoryQualityGate()

    def test_detects_q_a_format(self, gate):
        """Should detect 'Q: ... A: ...' format."""
        assert gate.is_qa_format("Q: What is X?\nA: X is Y") is True
        assert gate.is_qa_format("Q: Hello\n\nA: Hi there") is True

    def test_detects_question_answer_format(self, gate):
        """Should detect 'Question: ... Answer: ...' format."""
        assert gate.is_qa_format("Question: What?\nAnswer: This.") is True

    def test_detects_user_assistant_format(self, gate):
        """Should detect 'User: ... Assistant: ...' format."""
        assert gate.is_qa_format("User: Hi\nAssistant: Hello") is True

    def test_normal_text_not_qa(self, gate):
        """Normal text should not be flagged as Q&A."""
        assert gate.is_qa_format("User prefers Python for data science") is False
        assert gate.is_qa_format("The project uses React and TypeScript") is False


class TestTypeRecommendation:
    """Test memory type recommendation."""

    @pytest.fixture
    def gate(self):
        return MemoryQualityGate()

    def test_suggests_cache_for_qa(self, gate):
        """Q&A content should suggest CACHE_ENTRY type."""
        candidate = CandidateMemory(
            text="Q: What is ACMS?\nA: ACMS is a memory system",
            memory_type=MemoryType.SEMANTIC,
            source="ai"
        )

        suggested = gate.suggest_type(candidate)

        assert suggested == MemoryType.CACHE_ENTRY

    def test_keeps_semantic_for_facts(self, gate):
        """Factual content should keep SEMANTIC type."""
        candidate = CandidateMemory(
            text="User works at Anthropic as a software engineer",
            memory_type=MemoryType.SEMANTIC,
            source="extracted"
        )

        suggested = gate.suggest_type(candidate)

        assert suggested == MemoryType.SEMANTIC

    def test_keeps_episodic_for_conversations(self, gate):
        """Conversation context should keep EPISODIC type."""
        candidate = CandidateMemory(
            text="User asked about deployment strategies in this conversation",
            memory_type=MemoryType.EPISODIC,
            source="system",
            context={"conversation_id": str(uuid4())}
        )

        suggested = gate.suggest_type(candidate)

        assert suggested == MemoryType.EPISODIC
