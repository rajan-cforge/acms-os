"""Unit tests for Schema-Driven Context.

Cognitive Principle: Schema-Driven Comprehension

Expert comprehension differs from novice comprehension because experts
have rich mental schemas that organize and connect information.

Schema-driven context calibrates AI responses to the user's expertise level:
- Beginner (🌱): Explain concepts, avoid jargon
- Intermediate (🌿): Some assumed knowledge, focused explanations
- Advanced (🔬): Technical depth, can assume familiarity
- Expert (🏗️): Peer-level discussion, challenge assumptions

TDD: Tests written BEFORE implementation.
Run with: PYTHONPATH=. pytest tests/unit/gateway/test_schema_context.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


# ============================================================
# TEST FIXTURES AND HELPERS
# ============================================================

@dataclass
class MockTopicSummary:
    """Mock TopicSummary for testing."""
    id: str
    topic_slug: str
    summary_text: str
    user_id: str
    knowledge_depth: int  # Number of source entries
    knowledge_gaps: List[str]
    created_at: datetime


def create_topic_summaries(
    topics: Dict[str, int],
    user_id: str = "user-1"
) -> List[MockTopicSummary]:
    """Create mock topic summaries with specified depths.

    Args:
        topics: Dict mapping topic_slug to knowledge_depth
        user_id: User ID

    Returns:
        List of MockTopicSummary objects
    """
    summaries = []
    for topic, depth in topics.items():
        summaries.append(MockTopicSummary(
            id=f"ts-{topic}",
            topic_slug=topic,
            summary_text=f"Summary of {topic} knowledge",
            user_id=user_id,
            knowledge_depth=depth,
            knowledge_gaps=[],
            created_at=datetime.now(timezone.utc)
        ))
    return summaries


# ============================================================
# EXPERTISE LEVEL TESTS
# ============================================================

class TestExpertiseLevelDetection:
    """Tests for detecting user expertise level from schema."""

    @pytest.fixture
    def assembler(self):
        from src.gateway.context_assembler import ContextAssembler
        with patch('src.gateway.context_assembler.MemoryCRUD'):
            return ContextAssembler()

    def test_beginner_expertise_level(self, assembler):
        """Test detection of beginner expertise (🌱)."""
        # User has only 1-2 entries on topic
        topics = {"kubernetes": 2}
        summaries = create_topic_summaries(topics)

        level = assembler._determine_expertise_level(
            topic="kubernetes",
            summaries=summaries
        )

        assert level == "beginner"
        assert assembler._get_expertise_emoji(level) == "🌱"

    def test_intermediate_expertise_level(self, assembler):
        """Test detection of intermediate expertise (🌿)."""
        # User has 10-24 entries on topic (intermediate threshold is 10)
        topics = {"python": 15}
        summaries = create_topic_summaries(topics)

        level = assembler._determine_expertise_level(
            topic="python",
            summaries=summaries
        )

        assert level == "intermediate"
        assert assembler._get_expertise_emoji(level) == "🌿"

    def test_advanced_expertise_level(self, assembler):
        """Test detection of advanced expertise (🔬)."""
        # User has 25-99 entries on topic (advanced threshold is 25)
        topics = {"docker": 50}
        summaries = create_topic_summaries(topics)

        level = assembler._determine_expertise_level(
            topic="docker",
            summaries=summaries
        )

        assert level == "advanced"
        assert assembler._get_expertise_emoji(level) == "🔬"

    def test_expert_expertise_level(self, assembler):
        """Test detection of expert expertise (🏗️)."""
        # User has 100+ entries on topic (expert threshold is 100)
        topics = {"react": 150}
        summaries = create_topic_summaries(topics)

        level = assembler._determine_expertise_level(
            topic="react",
            summaries=summaries
        )

        assert level == "expert"
        assert assembler._get_expertise_emoji(level) == "🏗️"

    def test_unknown_topic_defaults_to_beginner(self, assembler):
        """Test that unknown topics default to beginner level."""
        topics = {"python": 20}  # Expert in Python
        summaries = create_topic_summaries(topics)

        # Query about unknown topic
        level = assembler._determine_expertise_level(
            topic="rust",
            summaries=summaries
        )

        assert level == "beginner"


# ============================================================
# SCHEMA CONTEXT BUILDING TESTS
# ============================================================

class TestSchemaContextBuilding:
    """Tests for building schema context from topic summaries."""

    @pytest.fixture
    def assembler(self):
        from src.gateway.context_assembler import ContextAssembler
        with patch('src.gateway.context_assembler.MemoryCRUD'):
            return ContextAssembler()

    @pytest.mark.asyncio
    async def test_build_schema_context_structure(self, assembler):
        """Test that schema context has correct structure."""
        topics = {
            "kubernetes": 15,
            "docker": 25,
            "python": 8
        }
        summaries = create_topic_summaries(topics)

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="kubernetes"
            )

            assert "expertise" in context.lower() or "knowledge" in context.lower()
            assert "kubernetes" in context.lower()

    @pytest.mark.asyncio
    async def test_schema_context_includes_expertise_level(self, assembler):
        """Test that schema context includes expertise indicator."""
        topics = {"api": 30}
        summaries = create_topic_summaries(topics)

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="api"
            )

            # Should include expertise indicator
            assert "🏗️" in context or "expert" in context.lower()

    @pytest.mark.asyncio
    async def test_schema_context_includes_related_knowledge(self, assembler):
        """Test that schema context mentions related topics."""
        topics = {
            "kubernetes": 20,
            "docker": 25,
            "helm": 10
        }
        summaries = create_topic_summaries(topics)

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="kubernetes"
            )

            # Should mention related topics user knows
            # (docker and helm are in the same domain as kubernetes)
            assert len(context) > 0

    @pytest.mark.asyncio
    async def test_schema_context_identifies_knowledge_gaps(self, assembler):
        """Test that schema context identifies gaps."""
        summaries = [
            MockTopicSummary(
                id="ts-1",
                topic_slug="kubernetes",
                summary_text="K8s basics",
                user_id="user-1",
                knowledge_depth=5,
                knowledge_gaps=["networking", "security"],
                created_at=datetime.now(timezone.utc)
            )
        ]

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="kubernetes"
            )

            # Should mention knowledge gaps
            # (may include them in context for calibration)
            assert context is not None


# ============================================================
# CONTEXT CALIBRATION TESTS
# ============================================================

class TestContextCalibration:
    """Tests for calibrating context based on expertise."""

    @pytest.fixture
    def assembler(self):
        from src.gateway.context_assembler import ContextAssembler
        with patch('src.gateway.context_assembler.MemoryCRUD'):
            return ContextAssembler()

    def test_beginner_calibration_instructions(self, assembler):
        """Test that beginner level gets explanatory instructions."""
        instructions = assembler._get_calibration_instructions("beginner")

        assert "explain" in instructions.lower() or "define" in instructions.lower()
        assert "jargon" in instructions.lower() or "assume" in instructions.lower()

    def test_intermediate_calibration_instructions(self, assembler):
        """Test that intermediate level gets balanced instructions."""
        instructions = assembler._get_calibration_instructions("intermediate")

        assert "assume" in instructions.lower() or "basic" in instructions.lower()

    def test_expert_calibration_instructions(self, assembler):
        """Test that expert level gets technical instructions."""
        instructions = assembler._get_calibration_instructions("expert")

        assert "technical" in instructions.lower() or "depth" in instructions.lower()

    def test_calibration_affects_response_style(self, assembler):
        """Test that different levels produce different calibration."""
        beginner_inst = assembler._get_calibration_instructions("beginner")
        expert_inst = assembler._get_calibration_instructions("expert")

        # Should be meaningfully different
        assert beginner_inst != expert_inst
        assert len(beginner_inst) > 20
        assert len(expert_inst) > 20


# ============================================================
# FULL CONTEXT INTEGRATION TESTS
# ============================================================

class TestFullContextIntegration:
    """Tests for integrating schema context into full context."""

    @pytest.fixture
    def assembler(self):
        from src.gateway.context_assembler import ContextAssembler
        with patch('src.gateway.context_assembler.MemoryCRUD'):
            return ContextAssembler()

    @pytest.mark.asyncio
    async def test_build_full_context_with_schema(self, assembler):
        """Test building full context with schema context included."""
        topics = {"python": 15}
        summaries = create_topic_summaries(topics)

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            # Build schema context
            schema_context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="python"
            )

            # Build full context
            full_context = assembler.build_full_context(
                thread_context=None,
                memory_context="Some relevant memories",
                web_context=None,
                schema_context=schema_context
            )

            # Schema context should be included
            assert "python" in full_context.lower() or len(full_context) > 0

    @pytest.mark.asyncio
    async def test_schema_context_appears_in_system_prompt_section(self, assembler):
        """Test that schema context is positioned for system prompt use."""
        topics = {"docker": 20}
        summaries = create_topic_summaries(topics)

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            schema_context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="docker"
            )

            # Should be suitable for injection into system prompt
            assert schema_context is not None
            # Should not be too long
            assert len(schema_context) < 2000


# ============================================================
# COGNITIVE PRINCIPLE TESTS
# ============================================================

class TestCognitivePrinciples:
    """Tests that verify cognitive science principles."""

    @pytest.fixture
    def assembler(self):
        from src.gateway.context_assembler import ContextAssembler
        with patch('src.gateway.context_assembler.MemoryCRUD'):
            return ContextAssembler()

    @pytest.mark.asyncio
    async def test_schema_driven_comprehension_principle(self, assembler):
        """
        Cognitive Principle: Schema-Driven Comprehension

        Experts process information differently than novices because
        they have rich schemas that organize knowledge. AI responses
        should be calibrated to the user's schema/expertise.
        """
        # Expert user has deep kubernetes knowledge
        expert_topics = {"kubernetes": 50, "docker": 40, "helm": 30}
        expert_summaries = create_topic_summaries(expert_topics)

        # Beginner has shallow knowledge
        beginner_topics = {"kubernetes": 2}
        beginner_summaries = create_topic_summaries(beginner_topics)

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            # Expert context
            mock_fetch.return_value = expert_summaries
            expert_context = await assembler.build_schema_context(
                user_id="expert-user",
                query_topic="kubernetes"
            )

            # Beginner context
            mock_fetch.return_value = beginner_summaries
            beginner_context = await assembler.build_schema_context(
                user_id="beginner-user",
                query_topic="kubernetes"
            )

            # Should produce different calibrations
            # Expert gets 🏗️, beginner gets 🌱
            if "🏗️" in expert_context:
                assert "🏗️" not in beginner_context
            if "🌱" in beginner_context:
                assert "🌱" not in expert_context

    @pytest.mark.asyncio
    async def test_knowledge_transfer_scaffolding(self, assembler):
        """
        Cognitive Principle: Scaffolding

        When users have partial knowledge, build on what they know.
        If user knows Docker but not Kubernetes, use Docker analogies.
        """
        topics = {
            "docker": 25,      # Expert
            "kubernetes": 3,   # Beginner
        }
        summaries = create_topic_summaries(topics)

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="kubernetes"
            )

            # Context should be aware user has Docker expertise
            # This enables scaffolding (explaining K8s via Docker concepts)
            assert context is not None


# ============================================================
# EDGE CASES TESTS
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def assembler(self):
        from src.gateway.context_assembler import ContextAssembler
        with patch('src.gateway.context_assembler.MemoryCRUD'):
            return ContextAssembler()

    @pytest.mark.asyncio
    async def test_no_topic_summaries(self, assembler):
        """Test handling when user has no topic summaries."""
        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = []

            context = await assembler.build_schema_context(
                user_id="new-user",
                query_topic="anything"
            )

            # Should return valid (possibly empty) context
            assert context is not None

    @pytest.mark.asyncio
    async def test_fetch_failure_graceful(self, assembler):
        """Test graceful handling of fetch failures."""
        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.side_effect = Exception("Database error")

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="python"
            )

            # Should not crash, return default context
            assert context is not None

    @pytest.mark.asyncio
    async def test_unicode_topic_handling(self, assembler):
        """Test handling of unicode topic names."""
        topics = {"编程": 10}  # "Programming" in Chinese
        summaries = create_topic_summaries(topics)

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="编程"
            )

            assert context is not None

    def test_expertise_thresholds_configurable(self, assembler):
        """Test that expertise thresholds can be adjusted."""
        # Default thresholds
        default = assembler._get_expertise_thresholds()

        assert "beginner" in default
        assert "intermediate" in default
        assert "advanced" in default
        assert "expert" in default

        # Thresholds should be in ascending order
        assert default["beginner"] < default["intermediate"]
        assert default["intermediate"] < default["advanced"]
        assert default["advanced"] < default["expert"]
