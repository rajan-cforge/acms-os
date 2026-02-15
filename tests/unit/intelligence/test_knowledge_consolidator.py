# tests/unit/intelligence/test_knowledge_consolidator.py
"""
TDD Tests for Knowledge Consolidation
Sprint 3: Knowledge Consolidation

These tests define the expected behavior before implementation.
"""

import pytest
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestKnowledgeConsolidation:
    """Tests for the KnowledgeConsolidationJob."""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock database pool."""
        pool = MagicMock()
        return pool

    @pytest.fixture
    def job(self, mock_db_pool):
        """Create KnowledgeConsolidationJob with mocked dependencies."""
        from src.jobs.knowledge_consolidation import KnowledgeConsolidationJob
        return KnowledgeConsolidationJob(db_pool=mock_db_pool)

    # =========================================================================
    # Similarity Detection Tests
    # =========================================================================

    def test_similar_facts_should_consolidate(self, job):
        """Facts with high word overlap should be consolidated."""
        # These phrases have ~80% word overlap after normalization
        fact1 = "FastAPI uses Pydantic for data validation in Python"
        fact2 = "FastAPI uses Pydantic for input validation in Python"

        should_consolidate = job.should_consolidate(fact1, fact2)

        assert should_consolidate is True

    def test_different_facts_should_not_consolidate(self, job):
        """Facts with <0.9 similarity should not be consolidated."""
        fact1 = "FastAPI uses Pydantic for validation"
        fact2 = "Kubernetes uses YAML for configuration"

        should_consolidate = job.should_consolidate(fact1, fact2)

        assert should_consolidate is False

    def test_exact_duplicates_should_consolidate(self, job):
        """Exact duplicates should always consolidate."""
        fact1 = "Python is a programming language"
        fact2 = "Python is a programming language"

        should_consolidate = job.should_consolidate(fact1, fact2)

        assert should_consolidate is True

    def test_case_insensitive_comparison(self, job):
        """Comparison should be case-insensitive."""
        fact1 = "Python is great"
        fact2 = "PYTHON IS GREAT"

        should_consolidate = job.should_consolidate(fact1, fact2)

        assert should_consolidate is True

    # =========================================================================
    # Content Hash Tests
    # =========================================================================

    def test_content_hash_is_consistent(self, job):
        """Same content should produce same hash."""
        content = "FastAPI is a modern web framework"

        hash1 = job.compute_content_hash(content)
        hash2 = job.compute_content_hash(content)

        assert hash1 == hash2

    def test_content_hash_is_normalized(self, job):
        """Hash should normalize whitespace and case."""
        content1 = "FastAPI is great"
        content2 = "  FASTAPI   IS   GREAT  "

        hash1 = job.compute_content_hash(content1)
        hash2 = job.compute_content_hash(content2)

        assert hash1 == hash2

    # =========================================================================
    # Source Boost Calculation Tests
    # =========================================================================

    def test_source_boost_with_one_source(self, job):
        """Single source gives no boost."""
        boost = job.calculate_source_boost(1)
        assert boost == 0.0

    def test_source_boost_with_multiple_sources(self, job):
        """Multiple sources give proportional boost."""
        # source_boost = min(0.5, (source_count - 1) * 0.05)
        assert job.calculate_source_boost(2) == 0.05
        assert job.calculate_source_boost(3) == 0.10
        assert job.calculate_source_boost(6) == 0.25
        assert job.calculate_source_boost(11) == 0.50

    def test_source_boost_capped_at_05(self, job):
        """Source boost cannot exceed 0.5."""
        boost = job.calculate_source_boost(100)
        assert boost == 0.5

    # =========================================================================
    # Verification Boost Tests
    # =========================================================================

    def test_verification_boost_value(self, job):
        """Verification adds 0.25 to confidence."""
        boost = job.get_verification_boost(is_verified=True)
        assert boost == 0.25

    def test_no_boost_without_verification(self, job):
        """No boost without verification."""
        boost = job.get_verification_boost(is_verified=False)
        assert boost == 0.0

    # =========================================================================
    # Effective Confidence Tests
    # =========================================================================

    def test_effective_confidence_calculation(self, job):
        """Effective = base + source_boost + verification_boost."""
        effective = job.calculate_effective_confidence(
            base_confidence=0.5,
            source_count=5,
            is_verified=True
        )
        # 0.5 + 0.2 + 0.25 = 0.95
        assert effective == pytest.approx(0.95, abs=0.01)

    def test_effective_confidence_capped_at_1(self, job):
        """Confidence cannot exceed 1.0."""
        effective = job.calculate_effective_confidence(
            base_confidence=0.8,
            source_count=20,
            is_verified=True
        )
        assert effective == 1.0

    def test_effective_confidence_minimum_zero(self, job):
        """Confidence cannot be negative."""
        effective = job.calculate_effective_confidence(
            base_confidence=0.0,
            source_count=1,
            is_verified=False
        )
        assert effective >= 0.0

    # =========================================================================
    # Domain Path Tests
    # =========================================================================

    def test_extract_domain_from_content(self, job):
        """Should extract domain from content context."""
        content = "Python asyncio uses event loops for concurrent execution"

        domain = job.extract_domain(content)

        assert domain is not None
        assert 'technology' in domain or 'programming' in domain

    def test_default_domain_for_general_content(self, job):
        """General content should get default domain."""
        content = "Remember to buy groceries tomorrow"

        domain = job.extract_domain(content)

        assert domain is not None  # Should have some default

    # =========================================================================
    # Consolidation Process Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_consolidate_new_knowledge_creates_record(self, job):
        """New knowledge should create consolidated_knowledge record."""
        mock_conn = AsyncMock()
        # First call: check for existing (None = not found)
        # Second call: INSERT RETURNING (returns new knowledge_id)
        mock_conn.fetchrow.side_effect = [
            None,  # No existing match
            {'knowledge_id': 'new-knowledge-123'}  # INSERT RETURNING
        ]
        mock_conn.execute.return_value = None

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        job.db_pool = mock_pool

        result = await job.consolidate_knowledge(
            content="New fact about Python",
            source_type="query_history",
            source_id="source-123",
            base_confidence=0.6
        )

        assert result is not None
        assert result.get('is_new') is True

    @pytest.mark.asyncio
    async def test_consolidate_existing_increments_source_count(self, job):
        """Existing knowledge should increment source count."""
        existing_record = {
            'knowledge_id': 'existing-123',
            'source_count': 2,
            'source_boost': 0.05
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = existing_record

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        job.db_pool = mock_pool

        result = await job.consolidate_knowledge(
            content="Existing fact about Python",
            source_type="query_history",
            source_id="source-456",
            base_confidence=0.6
        )

        assert result.get('is_new') is False
        # Should have called update with incremented source_count

    # =========================================================================
    # Provenance Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_creates_provenance_record(self, job):
        """Should create provenance record for each consolidation."""
        mock_conn = AsyncMock()
        # First call: check for existing (None = not found)
        # Second call: INSERT RETURNING (returns new knowledge_id)
        mock_conn.fetchrow.side_effect = [
            None,  # No existing match
            {'knowledge_id': 'new-knowledge-456'}  # INSERT RETURNING
        ]
        mock_conn.execute.return_value = None

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        job.db_pool = mock_pool

        await job.consolidate_knowledge(
            content="New fact",
            source_type="query_history",
            source_id="source-123",
            base_confidence=0.6,
            source_preview="Preview text"
        )

        # Verify provenance INSERT was called
        calls = mock_conn.execute.call_args_list
        provenance_call = [c for c in calls if 'knowledge_provenance' in str(c)]
        assert len(provenance_call) > 0


class TestConfidenceIndicator:
    """Tests for confidence visualization."""

    def test_high_confidence_indicator(self):
        """0.8-1.0 should show 4 filled dots (green)."""
        from src.jobs.knowledge_consolidation import get_confidence_indicator

        dots, color = get_confidence_indicator(0.85)

        assert dots == '●●●●○'
        assert color == 'green'

    def test_medium_high_confidence_indicator(self):
        """0.6-0.8 should show 3 filled dots (blue)."""
        from src.jobs.knowledge_consolidation import get_confidence_indicator

        dots, color = get_confidence_indicator(0.65)

        assert dots == '●●●○○'
        assert color == 'blue'

    def test_medium_confidence_indicator(self):
        """0.4-0.6 should show 2 filled dots (yellow)."""
        from src.jobs.knowledge_consolidation import get_confidence_indicator

        dots, color = get_confidence_indicator(0.45)

        assert dots == '●●○○○'
        assert color == 'yellow'

    def test_low_confidence_indicator(self):
        """0.2-0.4 should show 1 filled dot (orange)."""
        from src.jobs.knowledge_consolidation import get_confidence_indicator

        dots, color = get_confidence_indicator(0.25)

        assert dots == '●○○○○'
        assert color == 'orange'

    def test_very_low_confidence_indicator(self):
        """0.0-0.2 should show no filled dots (red)."""
        from src.jobs.knowledge_consolidation import get_confidence_indicator

        dots, color = get_confidence_indicator(0.10)

        assert dots == '○○○○○'
        assert color == 'red'

    def test_boundary_values(self):
        """Test exact boundary values."""
        from src.jobs.knowledge_consolidation import get_confidence_indicator

        # At boundaries, should be in higher tier
        assert get_confidence_indicator(0.8)[1] == 'green'
        assert get_confidence_indicator(0.6)[1] == 'blue'
        assert get_confidence_indicator(0.4)[1] == 'yellow'
        assert get_confidence_indicator(0.2)[1] == 'orange'


class TestKnowledgeConsolidationJob:
    """Tests for the full job execution."""

    @pytest.fixture
    def job(self):
        from src.jobs.knowledge_consolidation import KnowledgeConsolidationJob
        return KnowledgeConsolidationJob(db_pool=MagicMock())

    @pytest.mark.asyncio
    async def test_run_processes_new_knowledge(self, job):
        """Full job should process new knowledge items."""
        mock_new_items = [
            {'id': '1', 'content': 'Fact 1', 'source_type': 'query_history'},
            {'id': '2', 'content': 'Fact 2', 'source_type': 'query_history'},
        ]

        with patch.object(job, '_fetch_new_knowledge_items') as mock_fetch, \
             patch.object(job, 'consolidate_knowledge') as mock_consolidate:

            mock_fetch.return_value = mock_new_items
            mock_consolidate.return_value = {'is_new': True}

            result = await job.run()

            assert result['items_processed'] == 2
            assert mock_consolidate.call_count == 2

    @pytest.mark.asyncio
    async def test_run_handles_errors_gracefully(self, job):
        """Job should continue processing on individual errors."""
        with patch.object(job, '_fetch_new_knowledge_items') as mock_fetch, \
             patch.object(job, 'consolidate_knowledge') as mock_consolidate:

            mock_fetch.return_value = [
                {'id': '1', 'content': 'Fact 1'},
                {'id': '2', 'content': 'Fact 2'},
            ]
            mock_consolidate.side_effect = [Exception("Error"), {'is_new': True}]

            result = await job.run()

            # Should have processed second item despite first error
            assert result['items_processed'] == 1
            assert result['errors'] == 1
