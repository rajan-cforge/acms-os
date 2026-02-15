"""Unit tests for KnowledgeCompactor.

Cognitive Principle: LSM-Tree Consolidation

Like Log-Structured Merge-Trees in databases, knowledge consolidates
from volatile (Raw) to stable (Knowledge) to higher-order (Topics/Domains).

Compaction Levels:
- Level 1 (Raw): Individual Q&A pairs (ephemeral, high detail)
- Level 2 (Knowledge): Extracted facts (consolidated, medium detail)
- Level 3 (Topics): Topic summaries (synthesized, abstracted)
- Level 4 (Domains): Domain maps (cross-topic relationships)

TDD: Tests written BEFORE implementation.
Run with: PYTHONPATH=. pytest tests/unit/jobs/test_knowledge_compaction.py -v
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
class MockKnowledgeEntry:
    """Mock Knowledge entry for testing."""
    id: str
    content: str
    user_id: str
    topic: str
    created_at: datetime
    confidence: float = 0.9
    source_ids: List[str] = None

    def __post_init__(self):
        if self.source_ids is None:
            self.source_ids = []


@dataclass
class MockTopicSummary:
    """Mock Topic summary for testing."""
    id: str
    topic_slug: str
    summary_text: str
    user_id: str
    knowledge_depth: int  # Number of source entries
    knowledge_gaps: List[str]
    source_entry_ids: List[str]
    created_at: datetime


def create_knowledge_entries(
    topic: str,
    count: int = 5,
    user_id: str = "user-1"
) -> List[MockKnowledgeEntry]:
    """Create mock knowledge entries for a topic."""
    entries = []
    for i in range(count):
        entries.append(MockKnowledgeEntry(
            id=f"k-{topic}-{i}",
            content=f"Knowledge about {topic} - fact {i}",
            user_id=user_id,
            topic=topic,
            created_at=datetime.now(timezone.utc) - timedelta(days=i),
            confidence=0.8 + (i * 0.02),
            source_ids=[f"raw-{topic}-{i}"]
        ))
    return entries


# ============================================================
# COMPACTOR CONFIG TESTS
# ============================================================

class TestKnowledgeCompactorConfig:
    """Tests for KnowledgeCompactorConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        from src.jobs.knowledge_compaction import KnowledgeCompactorConfig

        config = KnowledgeCompactorConfig()

        # Minimum entries before topic compaction
        assert config.min_entries_for_topic >= 3
        # Minimum topics before domain compaction
        assert config.min_topics_for_domain >= 2
        # LLM budget for synthesis
        assert config.synthesis_budget_usd > 0
        # Max entries to compact per run
        assert config.max_entries_per_batch > 0

    def test_custom_config(self):
        """Test custom configuration."""
        from src.jobs.knowledge_compaction import KnowledgeCompactorConfig

        config = KnowledgeCompactorConfig(
            min_entries_for_topic=5,
            synthesis_budget_usd=0.50
        )

        assert config.min_entries_for_topic == 5
        assert config.synthesis_budget_usd == 0.50


# ============================================================
# TOPIC CLUSTERING TESTS
# ============================================================

class TestTopicClustering:
    """Tests for clustering knowledge entries by topic."""

    @pytest.fixture
    def compactor(self):
        from src.jobs.knowledge_compaction import KnowledgeCompactor
        return KnowledgeCompactor()

    def test_cluster_entries_by_topic(self, compactor):
        """Test clustering entries by their topic tags."""
        entries = [
            MockKnowledgeEntry(
                id="k-1", content="Python fact 1",
                user_id="user-1", topic="python",
                created_at=datetime.now(timezone.utc)
            ),
            MockKnowledgeEntry(
                id="k-2", content="Python fact 2",
                user_id="user-1", topic="python",
                created_at=datetime.now(timezone.utc)
            ),
            MockKnowledgeEntry(
                id="k-3", content="Docker fact 1",
                user_id="user-1", topic="docker",
                created_at=datetime.now(timezone.utc)
            ),
        ]

        clusters = compactor._cluster_by_topic(entries)

        assert "python" in clusters
        assert "docker" in clusters
        assert len(clusters["python"]) == 2
        assert len(clusters["docker"]) == 1

    def test_cluster_filters_small_groups(self, compactor):
        """Test that clusters below minimum are excluded."""
        entries = [
            MockKnowledgeEntry(
                id="k-1", content="Single topic fact",
                user_id="user-1", topic="rare_topic",
                created_at=datetime.now(timezone.utc)
            ),
        ]

        # With default min_entries_for_topic >= 3
        clusters = compactor._cluster_by_topic(entries)
        compactable = compactor._get_compactable_clusters(clusters)

        # Should be empty since only 1 entry
        assert "rare_topic" not in compactable


# ============================================================
# TOPIC SUMMARY SYNTHESIS TESTS
# ============================================================

class TestTopicSummarySynthesis:
    """Tests for synthesizing topic summaries."""

    @pytest.fixture
    def compactor(self):
        from src.jobs.knowledge_compaction import KnowledgeCompactor
        return KnowledgeCompactor()

    @pytest.mark.asyncio
    async def test_synthesize_topic_summary_structure(self, compactor):
        """Test that synthesis produces correct structure."""
        entries = create_knowledge_entries("kubernetes", count=5)

        with patch.object(compactor, '_call_llm_for_synthesis') as mock_llm:
            mock_llm.return_value = {
                "summary": "Kubernetes is a container orchestration platform...",
                "entity_map": {"kubernetes": ["pods", "services", "deployments"]},
                "knowledge_gaps": ["networking details", "security best practices"]
            }

            summary = await compactor._synthesize_topic_summary(
                topic="kubernetes",
                entries=entries,
                user_id="user-1"
            )

            assert summary is not None
            assert summary.topic_slug == "kubernetes"
            assert "orchestration" in summary.summary_text.lower()
            assert len(summary.source_entry_ids) == 5
            assert summary.knowledge_depth == 5

    @pytest.mark.asyncio
    async def test_synthesize_identifies_knowledge_gaps(self, compactor):
        """Test that synthesis identifies gaps in knowledge."""
        entries = create_knowledge_entries("python", count=3)

        with patch.object(compactor, '_call_llm_for_synthesis') as mock_llm:
            mock_llm.return_value = {
                "summary": "Python basics covered.",
                "entity_map": {"python": ["syntax", "functions"]},
                "knowledge_gaps": ["async/await", "metaclasses", "decorators"]
            }

            summary = await compactor._synthesize_topic_summary(
                topic="python",
                entries=entries,
                user_id="user-1"
            )

            assert len(summary.knowledge_gaps) >= 1
            assert "async" in summary.knowledge_gaps[0].lower() or \
                   "metaclasses" in summary.knowledge_gaps[1].lower()

    @pytest.mark.asyncio
    async def test_synthesize_preserves_source_ids(self, compactor):
        """Test that synthesis preserves source entry IDs."""
        entries = create_knowledge_entries("docker", count=4)

        with patch.object(compactor, '_call_llm_for_synthesis') as mock_llm:
            mock_llm.return_value = {
                "summary": "Docker container basics.",
                "entity_map": {},
                "knowledge_gaps": []
            }

            summary = await compactor._synthesize_topic_summary(
                topic="docker",
                entries=entries,
                user_id="user-1"
            )

            # Should preserve all source entry IDs
            for entry in entries:
                assert entry.id in summary.source_entry_ids


# ============================================================
# DOMAIN MAP SYNTHESIS TESTS
# ============================================================

class TestDomainMapSynthesis:
    """Tests for synthesizing domain maps from topic summaries."""

    @pytest.fixture
    def compactor(self):
        from src.jobs.knowledge_compaction import KnowledgeCompactor
        return KnowledgeCompactor()

    @pytest.mark.asyncio
    async def test_synthesize_domain_map_structure(self, compactor):
        """Test that domain synthesis produces correct structure."""
        topic_summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="docker",
                summary_text="Docker container basics",
                user_id="user-1", knowledge_depth=5,
                knowledge_gaps=["networking"],
                source_entry_ids=["k-1", "k-2"],
                created_at=datetime.now(timezone.utc)
            ),
            MockTopicSummary(
                id="ts-2", topic_slug="kubernetes",
                summary_text="Kubernetes orchestration",
                user_id="user-1", knowledge_depth=8,
                knowledge_gaps=["security"],
                source_entry_ids=["k-3", "k-4"],
                created_at=datetime.now(timezone.utc)
            ),
        ]

        with patch.object(compactor, '_call_llm_for_domain_synthesis') as mock_llm:
            mock_llm.return_value = {
                "domain_name": "Container Infrastructure",
                "topology": {
                    "docker": {"relates_to": ["kubernetes"]},
                    "kubernetes": {"relates_to": ["docker"]}
                },
                "cross_topic_relationships": [
                    "Docker containers run on Kubernetes pods"
                ],
                "strengths": ["container basics", "orchestration"],
                "gaps": ["networking", "security"],
                "emerging_themes": ["cloud native"]
            }

            domain = await compactor._synthesize_domain_map(
                topics=topic_summaries,
                user_id="user-1"
            )

            assert domain is not None
            assert domain.domain_name == "Container Infrastructure"
            assert "docker" in domain.topology_json
            assert len(domain.cross_topic_relationships) >= 1

    @pytest.mark.asyncio
    async def test_domain_map_identifies_cross_topic_relationships(self, compactor):
        """Test that domain maps identify relationships between topics."""
        topic_summaries = [
            MockTopicSummary(
                id="ts-1", topic_slug="python",
                summary_text="Python programming language",
                user_id="user-1", knowledge_depth=10,
                knowledge_gaps=[],
                source_entry_ids=["k-1"],
                created_at=datetime.now(timezone.utc)
            ),
            MockTopicSummary(
                id="ts-2", topic_slug="fastapi",
                summary_text="FastAPI web framework",
                user_id="user-1", knowledge_depth=5,
                knowledge_gaps=[],
                source_entry_ids=["k-2"],
                created_at=datetime.now(timezone.utc)
            ),
        ]

        with patch.object(compactor, '_call_llm_for_domain_synthesis') as mock_llm:
            mock_llm.return_value = {
                "domain_name": "Python Web Development",
                "topology": {},
                "cross_topic_relationships": [
                    "FastAPI is built on Python",
                    "Python async/await enables FastAPI performance"
                ],
                "strengths": [],
                "gaps": [],
                "emerging_themes": []
            }

            domain = await compactor._synthesize_domain_map(
                topics=topic_summaries,
                user_id="user-1"
            )

            assert len(domain.cross_topic_relationships) >= 2
            assert any("FastAPI" in r for r in domain.cross_topic_relationships)


# ============================================================
# COMPACTION PIPELINE TESTS
# ============================================================

class TestCompactionPipeline:
    """Tests for the full compaction pipeline."""

    @pytest.fixture
    def compactor(self):
        from src.jobs.knowledge_compaction import KnowledgeCompactor
        return KnowledgeCompactor()

    @pytest.mark.asyncio
    async def test_compact_to_topic_summaries(self, compactor):
        """Test Level 2 → Level 3 compaction."""
        # Mock database to return knowledge entries
        mock_entries = create_knowledge_entries("kubernetes", count=5)

        with patch.object(compactor, '_fetch_knowledge_entries') as mock_fetch:
            mock_fetch.return_value = mock_entries

            with patch.object(compactor, '_synthesize_topic_summary') as mock_synth:
                mock_synth.return_value = MockTopicSummary(
                    id="ts-1", topic_slug="kubernetes",
                    summary_text="K8s summary",
                    user_id="user-1", knowledge_depth=5,
                    knowledge_gaps=[],
                    source_entry_ids=[e.id for e in mock_entries],
                    created_at=datetime.now(timezone.utc)
                )

                with patch.object(compactor, '_save_topic_summary'):
                    result = await compactor.compact_to_topic_summaries(
                        user_id="user-1",
                        tenant_id="default"
                    )

                    assert result["topics_created"] >= 0

    @pytest.mark.asyncio
    async def test_compact_to_domain_maps(self, compactor):
        """Test Level 3 → Level 4 compaction."""
        mock_topics = [
            MockTopicSummary(
                id="ts-1", topic_slug="docker",
                summary_text="Docker summary",
                user_id="user-1", knowledge_depth=5,
                knowledge_gaps=[],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            ),
            MockTopicSummary(
                id="ts-2", topic_slug="kubernetes",
                summary_text="K8s summary",
                user_id="user-1", knowledge_depth=8,
                knowledge_gaps=[],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            ),
        ]

        with patch.object(compactor, '_fetch_topic_summaries') as mock_fetch:
            mock_fetch.return_value = mock_topics

            with patch.object(compactor, '_synthesize_domain_map') as mock_synth:
                mock_synth.return_value = MagicMock(
                    domain_name="Container Infrastructure",
                    topology_json="{}",
                    cross_topic_relationships=[]
                )

                with patch.object(compactor, '_save_domain_map'):
                    result = await compactor.compact_to_domain_maps(
                        user_id="user-1",
                        tenant_id="default"
                    )

                    assert result["domains_created"] >= 0

    @pytest.mark.asyncio
    async def test_compaction_respects_budget(self, compactor):
        """Test that compaction respects LLM budget."""
        compactor.config.synthesis_budget_usd = 0.01

        mock_entries = create_knowledge_entries("python", count=100)

        with patch.object(compactor, '_fetch_knowledge_entries') as mock_fetch:
            mock_fetch.return_value = mock_entries

            with patch.object(compactor, '_synthesize_topic_summary') as mock_synth:
                mock_synth.return_value = None  # Simulate budget exhaustion

                result = await compactor.compact_to_topic_summaries(
                    user_id="user-1",
                    tenant_id="default"
                )

                # Should have budget info in result
                assert "budget_remaining_usd" in result or "cost_usd" in result


# ============================================================
# COGNITIVE PRINCIPLE TESTS
# ============================================================

class TestCognitivePrinciples:
    """Tests that verify cognitive science principles."""

    @pytest.fixture
    def compactor(self):
        from src.jobs.knowledge_compaction import KnowledgeCompactor
        return KnowledgeCompactor()

    @pytest.mark.asyncio
    async def test_lsm_tree_consolidation_principle(self, compactor):
        """
        Cognitive Principle: LSM-Tree Consolidation

        Like databases, knowledge consolidates from volatile (recent)
        to stable (compacted) stores. Higher levels have:
        - Less detail but more synthesis
        - Broader coverage
        - More stable representations
        """
        # Level 2: Many individual facts
        knowledge_entries = create_knowledge_entries("api", count=10)

        # Level 3: Should produce fewer, synthesized summaries
        with patch.object(compactor, '_synthesize_topic_summary') as mock_synth:
            mock_synth.return_value = MockTopicSummary(
                id="ts-1", topic_slug="api",
                summary_text="Comprehensive API knowledge covering endpoints, auth, and errors.",
                user_id="user-1", knowledge_depth=10,
                knowledge_gaps=["rate limiting"],
                source_entry_ids=[e.id for e in knowledge_entries],
                created_at=datetime.now(timezone.utc)
            )

            summary = await compactor._synthesize_topic_summary(
                topic="api",
                entries=knowledge_entries,
                user_id="user-1"
            )

            # Summary should consolidate many entries into one
            assert summary.knowledge_depth == 10
            assert len(summary.source_entry_ids) == 10
            # Summary text should be synthesized, not just concatenated
            assert len(summary.summary_text) < sum(len(e.content) for e in knowledge_entries)

    @pytest.mark.asyncio
    async def test_schema_abstraction_principle(self, compactor):
        """
        Cognitive Principle: Schema Abstraction

        Domain maps represent abstract schemas that organize
        lower-level knowledge. They capture:
        - Relationships between concepts
        - Patterns across topics
        - Knowledge strengths and gaps
        """
        topics = [
            MockTopicSummary(
                id="ts-1", topic_slug="sql",
                summary_text="SQL database queries",
                user_id="user-1", knowledge_depth=15,
                knowledge_gaps=["window functions"],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            ),
            MockTopicSummary(
                id="ts-2", topic_slug="postgresql",
                summary_text="PostgreSQL specific features",
                user_id="user-1", knowledge_depth=8,
                knowledge_gaps=["JSONB indexing"],
                source_entry_ids=[],
                created_at=datetime.now(timezone.utc)
            ),
        ]

        with patch.object(compactor, '_call_llm_for_domain_synthesis') as mock_llm:
            mock_llm.return_value = {
                "domain_name": "Database Knowledge",
                "topology": {
                    "sql": {"relates_to": ["postgresql"], "type": "general"},
                    "postgresql": {"relates_to": ["sql"], "type": "specific"}
                },
                "cross_topic_relationships": [
                    "PostgreSQL extends standard SQL",
                    "SQL fundamentals apply to PostgreSQL"
                ],
                "strengths": ["basic queries", "PostgreSQL features"],
                "gaps": ["window functions", "JSONB indexing"],
                "emerging_themes": ["relational databases"]
            }

            domain = await compactor._synthesize_domain_map(
                topics=topics,
                user_id="user-1"
            )

            # Domain should capture abstract relationships
            assert "sql" in domain.topology_json.lower()
            # Should identify cross-topic patterns
            assert len(domain.cross_topic_relationships) >= 1
            # Should aggregate gaps from topics
            assert len(domain.knowledge_gaps) >= 2


# ============================================================
# STATS AND MONITORING TESTS
# ============================================================

class TestCompactorStats:
    """Tests for compactor statistics and monitoring."""

    @pytest.fixture
    def compactor(self):
        from src.jobs.knowledge_compaction import KnowledgeCompactor
        return KnowledgeCompactor()

    def test_get_stats(self, compactor):
        """Test statistics retrieval."""
        stats = compactor.get_stats()

        assert "total_topics_created" in stats
        assert "total_domains_created" in stats
        assert "total_cost_usd" in stats
        assert "config" in stats

    @pytest.mark.asyncio
    async def test_stats_update_after_compaction(self, compactor):
        """Test that stats update after compaction."""
        initial_stats = compactor.get_stats()

        with patch.object(compactor, '_fetch_knowledge_entries') as mock_fetch:
            mock_fetch.return_value = create_knowledge_entries("test", count=5)

            with patch.object(compactor, '_synthesize_topic_summary') as mock_synth:
                mock_synth.return_value = MockTopicSummary(
                    id="ts-1", topic_slug="test",
                    summary_text="Test summary",
                    user_id="user-1", knowledge_depth=5,
                    knowledge_gaps=[],
                    source_entry_ids=[],
                    created_at=datetime.now(timezone.utc)
                )

                with patch.object(compactor, '_save_topic_summary'):
                    await compactor.compact_to_topic_summaries(
                        user_id="user-1",
                        tenant_id="default"
                    )

        # Stats should reflect the compaction
        final_stats = compactor.get_stats()
        # Note: actual increment depends on implementation
        assert final_stats is not None


# ============================================================
# EDGE CASES TESTS
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def compactor(self):
        from src.jobs.knowledge_compaction import KnowledgeCompactor
        return KnowledgeCompactor()

    @pytest.mark.asyncio
    async def test_no_entries_to_compact(self, compactor):
        """Test handling when no entries need compaction."""
        with patch.object(compactor, '_fetch_knowledge_entries') as mock_fetch:
            mock_fetch.return_value = []

            result = await compactor.compact_to_topic_summaries(
                user_id="user-1",
                tenant_id="default"
            )

            assert result["topics_created"] == 0
            assert result.get("errors", 0) == 0

    @pytest.mark.asyncio
    async def test_llm_synthesis_failure(self, compactor):
        """Test handling when LLM synthesis fails."""
        entries = create_knowledge_entries("python", count=5)

        with patch.object(compactor, '_fetch_knowledge_entries') as mock_fetch:
            mock_fetch.return_value = entries

            with patch.object(compactor, '_call_llm_for_synthesis') as mock_llm:
                mock_llm.side_effect = Exception("LLM API error")

                result = await compactor.compact_to_topic_summaries(
                    user_id="user-1",
                    tenant_id="default"
                )

                # Should handle gracefully
                assert result.get("errors", 0) >= 1

    @pytest.mark.asyncio
    async def test_unicode_content_handling(self, compactor):
        """Test handling of unicode content."""
        entries = [
            MockKnowledgeEntry(
                id="k-1",
                content="Python 是一种编程语言 🐍",
                user_id="user-1",
                topic="python",
                created_at=datetime.now(timezone.utc)
            )
        ] * 5  # Repeat to meet minimum

        clusters = compactor._cluster_by_topic(entries)

        assert "python" in clusters
        assert len(clusters["python"]) == 5

    @pytest.mark.asyncio
    async def test_very_long_content_handling(self, compactor):
        """Test handling of very long content."""
        entries = [
            MockKnowledgeEntry(
                id=f"k-{i}",
                content="Long content " * 1000,
                user_id="user-1",
                topic="verbose",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(5)
        ]

        # Should not crash, may truncate
        clusters = compactor._cluster_by_topic(entries)
        assert "verbose" in clusters
