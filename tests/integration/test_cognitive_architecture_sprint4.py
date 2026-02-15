"""Integration tests for Cognitive Architecture Sprint 4.

Sprint 4 Focus: Knowledge Compaction & Schema-Driven Context
- 3.1 Knowledge Compaction (LSM-Tree Consolidation)
- 3.3 Schema-Driven Context (Expertise Calibration)

Cognitive Principles Tested:
1. LSM-Tree Consolidation: Knowledge consolidates from volatile to stable
   - Level 2 (Knowledge) → Level 3 (Topics) → Level 4 (Domains)
   - Higher levels have less detail but more synthesis

2. Schema-Driven Comprehension: Experts process info differently
   - Calibrate responses to user's expertise level
   - Use topic summaries to gauge knowledge depth

Run with: PYTHONPATH=. pytest tests/integration/test_cognitive_architecture_sprint4.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


# ============================================================
# TEST FIXTURES
# ============================================================

@dataclass
class MockKnowledgeEntry:
    """Mock Knowledge entry for testing."""
    id: str
    content: str
    user_id: str
    topic: str
    created_at: datetime
    confidence: float = 0.9


@dataclass
class MockTopicSummary:
    """Mock TopicSummary for testing."""
    id: str
    topic_slug: str
    summary_text: str
    user_id: str
    knowledge_depth: int
    knowledge_gaps: List[str]
    source_entry_ids: List[str]
    created_at: datetime


def create_knowledge_entries(
    topics: Dict[str, int],
    user_id: str = "user-1"
) -> List[MockKnowledgeEntry]:
    """Create mock knowledge entries for multiple topics.

    Args:
        topics: Dict mapping topic → entry count
        user_id: User ID

    Returns:
        List of MockKnowledgeEntry
    """
    entries = []
    for topic, count in topics.items():
        for i in range(count):
            entries.append(MockKnowledgeEntry(
                id=f"k-{topic}-{i}",
                content=f"Knowledge about {topic}: fact {i}",
                user_id=user_id,
                topic=topic,
                created_at=datetime.now(timezone.utc) - timedelta(hours=i),
            ))
    return entries


@pytest.fixture
def compactor():
    """Create KnowledgeCompactor for testing."""
    from src.jobs.knowledge_compaction import KnowledgeCompactor
    return KnowledgeCompactor()


@pytest.fixture
def assembler():
    """Create ContextAssembler for testing."""
    from src.gateway.context_assembler import ContextAssembler
    with patch('src.gateway.context_assembler.MemoryCRUD'):
        return ContextAssembler()


# ============================================================
# KNOWLEDGE COMPACTION INTEGRATION TESTS
# ============================================================

class TestKnowledgeCompactionIntegration:
    """Integration tests for knowledge compaction pipeline."""

    @pytest.mark.asyncio
    async def test_full_compaction_pipeline(self, compactor):
        """Test full Level 2 → Level 3 → Level 4 compaction."""
        # Create mock knowledge entries
        entries = create_knowledge_entries({
            "kubernetes": 10,
            "docker": 8,
            "helm": 5
        })

        with patch.object(compactor, '_fetch_knowledge_entries') as mock_fetch:
            mock_fetch.return_value = entries

            with patch.object(compactor, '_call_llm_for_synthesis') as mock_llm:
                mock_llm.return_value = {
                    "summary": "Synthesized knowledge summary",
                    "entity_map": {},
                    "knowledge_gaps": []
                }

                with patch.object(compactor, '_save_topic_summary') as mock_save:
                    mock_save.return_value = True

                    # Run topic compaction
                    result = await compactor.compact_to_topic_summaries(
                        user_id="user-1",
                        tenant_id="default"
                    )

                    # Should create topic summaries
                    assert result["entries_processed"] > 0
                    # Should find compactable clusters
                    assert result["clusters_found"] >= 2

    @pytest.mark.asyncio
    async def test_compaction_clusters_by_topic(self, compactor):
        """Test that compaction correctly clusters by topic."""
        entries = create_knowledge_entries({
            "python": 6,
            "javascript": 4,
            "rust": 2  # Below threshold
        })

        clusters = compactor._cluster_by_topic(entries)

        assert "python" in clusters
        assert "javascript" in clusters
        assert "rust" in clusters
        assert len(clusters["python"]) == 6
        assert len(clusters["javascript"]) == 4
        assert len(clusters["rust"]) == 2

        # Filter compactable (min 3 entries)
        compactable = compactor._get_compactable_clusters(clusters)
        assert "python" in compactable
        assert "javascript" in compactable
        assert "rust" not in compactable  # Only 2 entries

    @pytest.mark.asyncio
    async def test_compaction_tracks_source_entries(self, compactor):
        """Test that topic summaries track their source entries."""
        entries = create_knowledge_entries({"api": 5})

        with patch.object(compactor, '_call_llm_for_synthesis') as mock_llm:
            mock_llm.return_value = {
                "summary": "API knowledge summary",
                "entity_map": {},
                "knowledge_gaps": []
            }

            summary = await compactor._synthesize_topic_summary(
                topic="api",
                entries=entries,
                user_id="user-1"
            )

            # Should preserve all source IDs
            assert len(summary.source_entry_ids) == 5
            assert summary.knowledge_depth == 5


# ============================================================
# SCHEMA-DRIVEN CONTEXT INTEGRATION TESTS
# ============================================================

class TestSchemaContextIntegration:
    """Integration tests for schema-driven context."""

    @pytest.mark.asyncio
    async def test_schema_context_calibrates_to_expertise(self, assembler):
        """Test that schema context calibrates to user expertise."""
        # Expert user
        expert_summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="kubernetes",
                summary_text="K8s expertise",
                user_id="user-1", knowledge_depth=150,
                knowledge_gaps=[],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            )
        ]

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = expert_summaries

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="kubernetes"
            )

            # Should indicate expert level
            assert "🏗️" in context or "Expert" in context

    @pytest.mark.asyncio
    async def test_schema_context_includes_calibration_instructions(self, assembler):
        """Test that schema context includes LLM calibration instructions."""
        summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="python",
                summary_text="Python basics",
                user_id="user-1", knowledge_depth=5,
                knowledge_gaps=[],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            )
        ]

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="python"
            )

            # Should include calibration instructions
            assert "beginner" in context.lower() or "explain" in context.lower()

    @pytest.mark.asyncio
    async def test_full_context_includes_schema(self, assembler):
        """Test that full context building includes schema context."""
        summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="docker",
                summary_text="Docker knowledge",
                user_id="user-1", knowledge_depth=30,
                knowledge_gaps=["networking"],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            )
        ]

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            schema_context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="docker"
            )

            full_context = assembler.build_full_context(
                thread_context=None,
                memory_context="Some memories",
                web_context=None,
                schema_context=schema_context
            )

            # Schema context should be in full context
            assert "docker" in full_context.lower()
            assert "Some memories" in full_context


# ============================================================
# END-TO-END PIPELINE TESTS
# ============================================================

class TestCognitiveArchitecturePipelineS4:
    """End-to-end tests for Sprint 4 cognitive architecture."""

    @pytest.mark.asyncio
    async def test_compaction_to_schema_context_pipeline(self, compactor, assembler):
        """Test full pipeline: Knowledge → Topics → Schema Context."""
        # Step 1: Create knowledge entries
        entries = create_knowledge_entries({
            "fastapi": 15,
            "python": 25,
            "asyncio": 8
        })

        # Step 2: Compact to topic summaries
        with patch.object(compactor, '_fetch_knowledge_entries') as mock_fetch:
            mock_fetch.return_value = entries

            with patch.object(compactor, '_call_llm_for_synthesis') as mock_llm:
                mock_llm.return_value = {
                    "summary": "Python web development knowledge",
                    "entity_map": {"python": ["fastapi", "asyncio"]},
                    "knowledge_gaps": ["testing"]
                }

                with patch.object(compactor, '_save_topic_summary') as mock_save:
                    mock_save.return_value = True

                    result = await compactor.compact_to_topic_summaries(
                        user_id="user-1",
                        tenant_id="default"
                    )

                    assert result["entries_processed"] > 0

        # Step 3: Use schema context for response calibration
        summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="python",
                summary_text="Python expertise",
                user_id="user-1", knowledge_depth=25,
                knowledge_gaps=["testing"],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            )
        ]

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = summaries

            context = await assembler.build_schema_context(
                user_id="user-1",
                query_topic="python"
            )

            # Should be advanced level (25 entries)
            assert "advanced" in context.lower() or "🔬" in context

    @pytest.mark.asyncio
    async def test_expertise_evolution_over_time(self, assembler):
        """Test that expertise level can evolve as user learns more."""
        # Initial: Beginner
        beginner_summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="rust",
                summary_text="Rust basics",
                user_id="user-1", knowledge_depth=2,
                knowledge_gaps=["ownership", "lifetimes"],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            )
        ]

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = beginner_summaries

            beginner_level = assembler._determine_expertise_level(
                "rust", beginner_summaries
            )
            assert beginner_level == "beginner"

        # After learning: Intermediate
        intermediate_summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="rust",
                summary_text="Rust intermediate knowledge",
                user_id="user-1", knowledge_depth=15,
                knowledge_gaps=["advanced macros"],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            )
        ]

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            mock_fetch.return_value = intermediate_summaries

            intermediate_level = assembler._determine_expertise_level(
                "rust", intermediate_summaries
            )
            assert intermediate_level == "intermediate"


# ============================================================
# COGNITIVE PRINCIPLE TESTS
# ============================================================

class TestCognitivePrinciples:
    """Tests that verify cognitive science principles."""

    @pytest.mark.asyncio
    async def test_lsm_tree_consolidation_principle(self, compactor):
        """
        Cognitive Principle: LSM-Tree Consolidation

        Knowledge consolidates from volatile (recent, detailed) to
        stable (compacted, synthesized) stores. Higher levels have:
        - Less detail but more synthesis
        - Broader coverage
        - More stable representations
        """
        # Level 2: Many individual facts
        entries = create_knowledge_entries({"databases": 20})

        with patch.object(compactor, '_call_llm_for_synthesis') as mock_llm:
            mock_llm.return_value = {
                "summary": "Comprehensive database knowledge covering SQL, indexes, and optimization.",
                "entity_map": {"databases": ["sql", "indexes", "normalization"]},
                "knowledge_gaps": ["NoSQL"]
            }

            summary = await compactor._synthesize_topic_summary(
                topic="databases",
                entries=entries,
                user_id="user-1"
            )

            # Level 3 summary should consolidate many into one
            assert summary.knowledge_depth == 20
            # Summary should be synthesized (shorter than sum of all entries)
            total_content = sum(len(e.content) for e in entries)
            assert len(summary.summary_text) < total_content

    @pytest.mark.asyncio
    async def test_schema_driven_comprehension_principle(self, assembler):
        """
        Cognitive Principle: Schema-Driven Comprehension

        Experts process information differently than novices because
        they have rich mental schemas. AI responses should be
        calibrated to match the user's schema depth.
        """
        # Expert has rich schema
        expert_summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="machine-learning",
                summary_text="Deep ML expertise",
                user_id="expert", knowledge_depth=200,
                knowledge_gaps=[],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            )
        ]

        # Novice has shallow schema
        novice_summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="machine-learning",
                summary_text="ML basics",
                user_id="novice", knowledge_depth=2,
                knowledge_gaps=["everything"],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            )
        ]

        with patch.object(assembler, '_fetch_user_topic_summaries') as mock_fetch:
            # Expert context
            mock_fetch.return_value = expert_summaries
            expert_context = await assembler.build_schema_context(
                user_id="expert",
                query_topic="machine-learning"
            )

            # Novice context
            mock_fetch.return_value = novice_summaries
            novice_context = await assembler.build_schema_context(
                user_id="novice",
                query_topic="machine-learning"
            )

            # Should produce different calibrations
            expert_level = assembler._determine_expertise_level(
                "machine-learning", expert_summaries
            )
            novice_level = assembler._determine_expertise_level(
                "machine-learning", novice_summaries
            )

            assert expert_level == "expert"
            assert novice_level == "beginner"


# ============================================================
# STATS AND MONITORING TESTS
# ============================================================

class TestSprintFourMonitoring:
    """Tests for Sprint 4 monitoring and observability."""

    def test_compactor_stats_tracked(self, compactor):
        """Test that compactor stats are properly tracked."""
        stats = compactor.get_stats()

        assert "total_topics_created" in stats
        assert "total_domains_created" in stats
        assert "total_cost_usd" in stats
        assert "config" in stats

    def test_expertise_thresholds_accessible(self, assembler):
        """Test that expertise thresholds are accessible."""
        thresholds = assembler._get_expertise_thresholds()

        assert "beginner" in thresholds
        assert "intermediate" in thresholds
        assert "advanced" in thresholds
        assert "expert" in thresholds

        # Should be in ascending order
        assert thresholds["beginner"] < thresholds["intermediate"]
        assert thresholds["intermediate"] < thresholds["advanced"]
        assert thresholds["advanced"] < thresholds["expert"]

    def test_calibration_instructions_for_all_levels(self, assembler):
        """Test that calibration instructions exist for all levels."""
        levels = ["beginner", "intermediate", "advanced", "expert"]

        for level in levels:
            instructions = assembler._get_calibration_instructions(level)
            assert len(instructions) > 20
            # Should mention the level or related concepts
            assert level in instructions.lower() or \
                   any(word in instructions.lower() for word in ["explain", "assume", "technical", "peer"])
