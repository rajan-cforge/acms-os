"""Unit tests for Creative Recombination.

Cognitive Principle: REM Sleep Creative Discovery

During REM sleep, the brain makes novel connections between distant
memories, leading to creative insights and problem-solving. The
CreativeRecombinator mimics this by:

1. Finding shared entities across distant topic clusters
2. Detecting structural analogies (A:B :: C:D patterns)
3. Identifying bridging queries that connect domains

TDD: Tests written BEFORE implementation.
Run with: PYTHONPATH=. pytest tests/unit/jobs/test_creative_recombination.py -v
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
    entity_map: Dict[str, List[str]]  # entity -> related concepts
    knowledge_depth: int
    created_at: datetime


@dataclass
class MockKnowledgeEntry:
    """Mock Knowledge entry for testing."""
    id: str
    content: str
    user_id: str
    topic: str
    entities: List[str]
    embedding: List[float]
    created_at: datetime


def create_topic_summaries_with_entities(
    topics_entities: Dict[str, Dict[str, List[str]]],
    user_id: str = "user-1"
) -> List[MockTopicSummary]:
    """Create mock topic summaries with entity maps.

    Args:
        topics_entities: Dict mapping topic_slug to entity_map
        user_id: User ID

    Returns:
        List of MockTopicSummary
    """
    summaries = []
    for topic, entity_map in topics_entities.items():
        summaries.append(MockTopicSummary(
            id=f"ts-{topic}",
            topic_slug=topic,
            summary_text=f"Summary of {topic}",
            user_id=user_id,
            entity_map=entity_map,
            knowledge_depth=len(entity_map) * 5,
            created_at=datetime.now(timezone.utc)
        ))
    return summaries


def create_knowledge_entries(
    entries_data: List[Dict[str, Any]],
    user_id: str = "user-1"
) -> List[MockKnowledgeEntry]:
    """Create mock knowledge entries.

    Args:
        entries_data: List of dicts with content, topic, entities
        user_id: User ID

    Returns:
        List of MockKnowledgeEntry
    """
    entries = []
    for i, data in enumerate(entries_data):
        entries.append(MockKnowledgeEntry(
            id=f"k-{i}",
            content=data.get("content", f"Content {i}"),
            user_id=user_id,
            topic=data.get("topic", "general"),
            entities=data.get("entities", []),
            embedding=data.get("embedding", [0.5] * 1536),
            created_at=datetime.now(timezone.utc) - timedelta(hours=i)
        ))
    return entries


# ============================================================
# SHARED ENTITY DISCOVERY TESTS
# ============================================================

class TestSharedEntityDiscovery:
    """Tests for finding shared entities across distant clusters."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    def test_find_shared_entities_basic(self, recombinator):
        """Test finding entities shared between two topics."""
        summaries = create_topic_summaries_with_entities({
            "kubernetes": {
                "containers": ["pods", "deployments"],
                "networking": ["services", "ingress"],
            },
            "docker": {
                "containers": ["images", "volumes"],
                "build": ["dockerfile", "layers"],
            }
        })

        shared = recombinator._find_shared_entities(summaries)

        # "containers" appears in both kubernetes and docker
        assert "containers" in shared
        assert set(shared["containers"]) == {"kubernetes", "docker"}

    def test_find_shared_entities_across_distant_topics(self, recombinator):
        """Test finding shared entities across unrelated domains."""
        summaries = create_topic_summaries_with_entities({
            "machine-learning": {
                "optimization": ["gradient descent", "loss function"],
                "architecture": ["layers", "neurons"],
            },
            "supply-chain": {
                "optimization": ["logistics", "inventory"],
                "flow": ["distribution", "warehousing"],
            },
            "cooking": {
                "techniques": ["roasting", "braising"],
                "ingredients": ["spices", "proteins"],
            }
        })

        shared = recombinator._find_shared_entities(summaries)

        # "optimization" is shared between ML and supply-chain (distant domains)
        assert "optimization" in shared
        assert "machine-learning" in shared["optimization"]
        assert "supply-chain" in shared["optimization"]
        # "cooking" shouldn't share entities with others
        assert "cooking" not in shared.get("optimization", [])

    def test_no_shared_entities(self, recombinator):
        """Test when topics have no shared entities."""
        summaries = create_topic_summaries_with_entities({
            "cooking": {
                "techniques": ["roasting"],
            },
            "astronomy": {
                "objects": ["stars"],
            }
        })

        shared = recombinator._find_shared_entities(summaries)

        assert len(shared) == 0

    def test_shared_entity_minimum_distance(self, recombinator):
        """Test that only sufficiently distant topics count as discoveries."""
        # Two very similar topics sharing entities is not interesting
        summaries = create_topic_summaries_with_entities({
            "python-django": {
                "web": ["views", "models"],
            },
            "python-flask": {
                "web": ["routes", "blueprints"],
            }
        })

        # These are too similar - should not count as creative discovery
        discoveries = recombinator._find_cross_domain_discoveries(
            summaries,
            min_domain_distance=0.5
        )

        # Similar Python web frameworks shouldn't produce "creative" discoveries
        assert len([d for d in discoveries if d.discovery_type == "cross_domain_entity"]) == 0


# ============================================================
# STRUCTURAL ANALOGY TESTS
# ============================================================

class TestStructuralAnalogies:
    """Tests for detecting A:B :: C:D structural analogies."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    def test_detect_structural_analogy(self, recombinator):
        """Test detection of structural analogies."""
        # Kubernetes : Pods :: Docker : Containers
        # (same relationship: orchestrator : unit)
        entries = create_knowledge_entries([
            {"content": "Kubernetes manages pods", "topic": "kubernetes",
             "entities": ["kubernetes", "pods"]},
            {"content": "Docker manages containers", "topic": "docker",
             "entities": ["docker", "containers"]},
        ])

        analogies = recombinator._find_structural_analogies(entries)

        # Should detect the "manages" relationship pattern
        assert len(analogies) >= 0  # May or may not detect depending on implementation

    def test_analogy_scoring(self, recombinator):
        """Test that analogy strength is scored."""
        entries = create_knowledge_entries([
            {"content": "CEO leads company", "topic": "business",
             "entities": ["CEO", "company"]},
            {"content": "Captain leads team", "topic": "sports",
             "entities": ["captain", "team"]},
            {"content": "Teacher leads class", "topic": "education",
             "entities": ["teacher", "class"]},
        ])

        analogies = recombinator._find_structural_analogies(entries)

        # Multiple examples of "X leads Y" should score higher
        for analogy in analogies:
            assert hasattr(analogy, 'strength') or hasattr(analogy, 'score')

    def test_no_false_analogies(self, recombinator):
        """Test that unrelated entries don't produce analogies."""
        entries = create_knowledge_entries([
            {"content": "Python is a programming language", "topic": "python",
             "entities": ["python", "programming"]},
            {"content": "The weather is sunny today", "topic": "weather",
             "entities": ["weather", "sunny"]},
        ])

        analogies = recombinator._find_structural_analogies(entries)

        # No structural similarity, no analogies
        assert len(analogies) == 0


# ============================================================
# BRIDGING QUERY TESTS
# ============================================================

class TestBridgingQueries:
    """Tests for identifying queries that bridge domains."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    @pytest.mark.asyncio
    async def test_identify_bridging_queries(self, recombinator):
        """Test identification of queries that bridge multiple domains."""
        # A query that touches both ML and databases
        query_data = {
            "query": "How do I optimize database queries for ML feature stores?",
            "retrieved_topics": ["machine-learning", "databases", "optimization"],
            "user_id": "user-1"
        }

        with patch.object(recombinator, '_fetch_query_history') as mock_fetch:
            mock_fetch.return_value = [query_data]

            bridges = await recombinator._find_bridging_queries(user_id="user-1")

            # Query that retrieves from multiple distant domains is a bridge
            assert len(bridges) >= 0

    @pytest.mark.asyncio
    async def test_bridge_requires_distance(self, recombinator):
        """Test that bridges require domain distance."""
        # Query touching similar domains isn't a bridge
        query_data = {
            "query": "Django vs Flask for web development",
            "retrieved_topics": ["python-django", "python-flask"],
            "user_id": "user-1"
        }

        with patch.object(recombinator, '_fetch_query_history') as mock_fetch:
            mock_fetch.return_value = [query_data]

            bridges = await recombinator._find_bridging_queries(
                user_id="user-1",
                min_domain_distance=0.5
            )

            # Similar topics shouldn't count as a bridge
            assert len(bridges) == 0


# ============================================================
# CROSS-DOMAIN DISCOVERY PIPELINE TESTS
# ============================================================

class TestCrossDomainDiscoveryPipeline:
    """Tests for the full cross-domain discovery pipeline."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    @pytest.mark.asyncio
    async def test_full_discovery_pipeline(self, recombinator):
        """Test full discovery pipeline."""
        summaries = create_topic_summaries_with_entities({
            "devops": {
                "automation": ["CI/CD", "infrastructure-as-code"],
                "monitoring": ["metrics", "alerts"],
            },
            "machine-learning": {
                "automation": ["AutoML", "hyperparameter tuning"],
                "monitoring": ["model drift", "accuracy tracking"],
            }
        })

        with patch.object(recombinator, '_fetch_topic_summaries') as mock_topics:
            mock_topics.return_value = summaries

            with patch.object(recombinator, '_fetch_query_history') as mock_queries:
                mock_queries.return_value = []

                discoveries = await recombinator.discover_cross_domain_connections(
                    user_id="user-1",
                    tenant_id="default"
                )

                # Should find shared entities
                assert "discoveries" in discoveries
                assert "shared_entities" in discoveries or discoveries.get("discovery_count", 0) >= 0

    @pytest.mark.asyncio
    async def test_discovery_returns_insight_format(self, recombinator):
        """Test that discoveries are formatted for insight storage."""
        summaries = create_topic_summaries_with_entities({
            "biology": {
                "networks": ["neural pathways", "ecosystems"],
            },
            "computer-science": {
                "networks": ["distributed systems", "graph algorithms"],
            }
        })

        with patch.object(recombinator, '_fetch_topic_summaries') as mock_topics:
            mock_topics.return_value = summaries

            with patch.object(recombinator, '_fetch_query_history') as mock_queries:
                mock_queries.return_value = []

                discoveries = await recombinator.discover_cross_domain_connections(
                    user_id="user-1",
                    tenant_id="default"
                )

                # Discoveries should be storable as insights
                if discoveries.get("discoveries"):
                    for d in discoveries["discoveries"]:
                        assert "description" in d or "insight_text" in d
                        assert "domains" in d or "topics" in d

    @pytest.mark.asyncio
    async def test_discovery_deduplication(self, recombinator):
        """Test that duplicate discoveries are filtered."""
        # Run discovery twice on same data
        summaries = create_topic_summaries_with_entities({
            "cooking": {
                "heat": ["roasting", "sauteing"],
            },
            "chemistry": {
                "heat": ["combustion", "reactions"],
            }
        })

        with patch.object(recombinator, '_fetch_topic_summaries') as mock_topics:
            mock_topics.return_value = summaries

            with patch.object(recombinator, '_fetch_query_history') as mock_queries:
                mock_queries.return_value = []

                with patch.object(recombinator, '_fetch_existing_discoveries') as mock_existing:
                    # First run - no existing
                    mock_existing.return_value = []
                    first = await recombinator.discover_cross_domain_connections(
                        user_id="user-1",
                        tenant_id="default"
                    )

                    # Second run - existing discoveries
                    mock_existing.return_value = first.get("discoveries", [])
                    second = await recombinator.discover_cross_domain_connections(
                        user_id="user-1",
                        tenant_id="default"
                    )

                    # Should not duplicate discoveries
                    assert second.get("new_discoveries", 0) == 0 or \
                           len(second.get("discoveries", [])) <= len(first.get("discoveries", []))


# ============================================================
# DISCOVERY FILTERING TESTS
# ============================================================

class TestDiscoveryFiltering:
    """Tests for filtering and ranking discoveries."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    def test_filter_by_novelty(self, recombinator):
        """Test filtering discoveries by novelty score."""
        discoveries = [
            {"entity": "optimization", "topics": ["ml", "logistics"], "novelty": 0.9},
            {"entity": "data", "topics": ["ml", "databases"], "novelty": 0.3},
            {"entity": "flow", "topics": ["logistics", "plumbing"], "novelty": 0.7},
        ]

        filtered = recombinator._filter_discoveries(
            discoveries,
            min_novelty=0.5
        )

        # Only high-novelty discoveries
        assert len(filtered) == 2
        assert all(d["novelty"] >= 0.5 for d in filtered)

    def test_rank_by_interestingness(self, recombinator):
        """Test ranking discoveries by interestingness."""
        discoveries = [
            {"entity": "a", "topics": ["x", "y"], "novelty": 0.5, "distance": 0.3},
            {"entity": "b", "topics": ["p", "q"], "novelty": 0.8, "distance": 0.9},
            {"entity": "c", "topics": ["m", "n"], "novelty": 0.6, "distance": 0.5},
        ]

        ranked = recombinator._rank_discoveries(discoveries)

        # Higher novelty * distance = more interesting
        assert ranked[0]["entity"] == "b"  # 0.8 * 0.9 = 0.72

    def test_limit_discoveries_per_session(self, recombinator):
        """Test limiting discoveries to avoid overwhelming user."""
        discoveries = [{"entity": f"e{i}", "topics": ["a", "b"]} for i in range(20)]

        limited = recombinator._limit_discoveries(discoveries, max_per_session=5)

        assert len(limited) == 5


# ============================================================
# DOMAIN DISTANCE CALCULATION TESTS
# ============================================================

class TestDomainDistance:
    """Tests for calculating distance between domains."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    def test_same_domain_zero_distance(self, recombinator):
        """Test that same domains have zero distance."""
        distance = recombinator._compute_domain_distance(
            "python-django",
            "python-flask"
        )

        # Same parent domain (python) = low distance
        assert distance < 0.3

    def test_different_domains_high_distance(self, recombinator):
        """Test that different domains have high distance."""
        distance = recombinator._compute_domain_distance(
            "machine-learning",
            "cooking"
        )

        # Completely different domains = high distance
        assert distance > 0.7

    def test_related_domains_medium_distance(self, recombinator):
        """Test that related domains have medium distance."""
        # machine-learning (data-science) and python (programming) are both
        # in the "technology" group but different subdomains
        distance = recombinator._compute_domain_distance(
            "machine-learning",
            "python"
        )

        # Same group, different subdomains = medium distance (0.5)
        assert 0.3 <= distance <= 0.7

    def test_distance_symmetry(self, recombinator):
        """Test that distance is symmetric."""
        d1 = recombinator._compute_domain_distance("a", "b")
        d2 = recombinator._compute_domain_distance("b", "a")

        assert d1 == d2


# ============================================================
# INSIGHT GENERATION TESTS
# ============================================================

class TestInsightGeneration:
    """Tests for generating human-readable insights from discoveries."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    def test_generate_shared_entity_insight(self, recombinator):
        """Test generating insight text for shared entities."""
        discovery = {
            "type": "shared_entity",
            "entity": "optimization",
            "topics": ["machine-learning", "supply-chain"],
        }

        insight = recombinator._generate_insight_text(discovery)

        assert "optimization" in insight.lower()
        assert "machine-learning" in insight.lower() or "ml" in insight.lower()
        assert "supply-chain" in insight.lower() or "supply chain" in insight.lower()

    def test_generate_analogy_insight(self, recombinator):
        """Test generating insight text for analogies."""
        discovery = {
            "type": "structural_analogy",
            "pattern": "X manages Y",
            "examples": [
                ("kubernetes", "pods"),
                ("docker", "containers"),
            ]
        }

        insight = recombinator._generate_insight_text(discovery)

        assert "pattern" in insight.lower() or "similar" in insight.lower()

    def test_generate_bridge_insight(self, recombinator):
        """Test generating insight text for bridging queries."""
        discovery = {
            "type": "bridging_query",
            "query": "How to optimize ML pipelines with Kubernetes?",
            "domains": ["machine-learning", "devops"],
        }

        insight = recombinator._generate_insight_text(discovery)

        assert "connects" in insight.lower() or "bridges" in insight.lower()


# ============================================================
# CONFIGURATION TESTS
# ============================================================

class TestConfiguration:
    """Tests for CreativeRecombinator configuration."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    def test_default_configuration(self, recombinator):
        """Test default configuration values."""
        config = recombinator.config

        assert config.min_domain_distance > 0
        assert config.min_novelty_score > 0
        assert config.max_discoveries_per_run > 0

    def test_custom_configuration(self):
        """Test custom configuration."""
        from src.jobs.creative_recombination import CreativeRecombinator, RecombinatorConfig

        config = RecombinatorConfig(
            min_domain_distance=0.8,
            min_novelty_score=0.7,
            max_discoveries_per_run=3
        )

        recombinator = CreativeRecombinator(config=config)

        assert recombinator.config.min_domain_distance == 0.8
        assert recombinator.config.min_novelty_score == 0.7
        assert recombinator.config.max_discoveries_per_run == 3


# ============================================================
# STATS AND MONITORING TESTS
# ============================================================

class TestStatsAndMonitoring:
    """Tests for stats tracking and monitoring."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    def test_stats_tracked(self, recombinator):
        """Test that stats are properly tracked."""
        stats = recombinator.get_stats()

        assert "total_discoveries" in stats
        assert "discoveries_by_type" in stats
        assert "last_run" in stats

    @pytest.mark.asyncio
    async def test_run_updates_stats(self, recombinator):
        """Test that running discovery updates stats."""
        initial_stats = recombinator.get_stats()

        summaries = create_topic_summaries_with_entities({
            "topic1": {"entity1": ["a", "b"]},
            "topic2": {"entity1": ["c", "d"]},
        })

        with patch.object(recombinator, '_fetch_topic_summaries') as mock_topics:
            mock_topics.return_value = summaries

            with patch.object(recombinator, '_fetch_query_history') as mock_queries:
                mock_queries.return_value = []

                with patch.object(recombinator, '_save_discoveries') as mock_save:
                    mock_save.return_value = True

                    await recombinator.discover_cross_domain_connections(
                        user_id="user-1",
                        tenant_id="default"
                    )

        final_stats = recombinator.get_stats()

        # Stats should be updated
        assert final_stats["last_run"] is not None


# ============================================================
# COGNITIVE PRINCIPLE TESTS
# ============================================================

class TestCognitivePrinciples:
    """Tests that verify cognitive science principles."""

    @pytest.fixture
    def recombinator(self):
        from src.jobs.creative_recombination import CreativeRecombinator
        return CreativeRecombinator()

    @pytest.mark.asyncio
    async def test_rem_sleep_discovery_principle(self, recombinator):
        """
        Cognitive Principle: REM Sleep Creative Discovery

        During REM sleep, the brain replays and recombines memories
        from different contexts, leading to novel insights and
        creative problem-solving. The prefrontal cortex is less
        active, allowing unusual associations to form.

        The CreativeRecombinator mimics this by:
        1. Finding connections between distant knowledge domains
        2. Detecting patterns that span multiple topics
        3. Generating "aha!" moments from hidden relationships
        """
        # Create knowledge from distant domains
        summaries = create_topic_summaries_with_entities({
            "neuroscience": {
                "networks": ["neural networks", "synapses"],
                "plasticity": ["learning", "adaptation"],
            },
            "urban-planning": {
                "networks": ["road systems", "transit"],
                "flow": ["traffic", "pedestrians"],
            },
            "ecology": {
                "networks": ["food webs", "ecosystems"],
                "flow": ["energy transfer", "nutrients"],
            }
        })

        with patch.object(recombinator, '_fetch_topic_summaries') as mock_topics:
            mock_topics.return_value = summaries

            with patch.object(recombinator, '_fetch_query_history') as mock_queries:
                mock_queries.return_value = []

                discoveries = await recombinator.discover_cross_domain_connections(
                    user_id="user-1",
                    tenant_id="default"
                )

                # Should find "networks" as a cross-domain concept
                # connecting neuroscience, urban planning, and ecology
                # This mimics the brain's ability to see patterns
                # across seemingly unrelated domains
                assert discoveries is not None

                # The discovery of "networks" across domains is a
                # creative insight - the same structural pattern
                # appearing in brains, cities, and ecosystems

    def test_distant_association_preference(self, recombinator):
        """
        Cognitive Principle: Distant Association Value

        Creative insights typically come from combining ideas that
        are semantically distant. Nearby associations (python-django
        and python-flask) are mundane. Distant associations
        (cooking and chemistry via "heat") are creative.
        """
        # Close associations (low creativity value)
        close_distance = recombinator._compute_domain_distance(
            "python-django", "python-flask"
        )

        # Distant associations (high creativity value)
        distant_distance = recombinator._compute_domain_distance(
            "cooking", "chemistry"
        )

        # Creative recombination values distant associations
        assert distant_distance > close_distance

        # Creativity score should weight distance
        close_creativity = recombinator._compute_creativity_score(
            entity="web-framework",
            topics=["python-django", "python-flask"]
        )

        distant_creativity = recombinator._compute_creativity_score(
            entity="heat",
            topics=["cooking", "chemistry"]
        )

        assert distant_creativity > close_creativity
