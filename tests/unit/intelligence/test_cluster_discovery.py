# tests/unit/intelligence/test_cluster_discovery.py
"""
TDD Tests for Memory Cluster Discovery
Sprint 2: Memory Clustering

These tests define the expected behavior before implementation.
Write tests first, then make them pass.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestClusterDiscovery:
    """Tests for the ClusterDiscoveryJob."""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock database pool."""
        pool = MagicMock()
        pool.acquire = MagicMock(return_value=AsyncMock())
        return pool

    @pytest.fixture
    def mock_weaviate_client(self):
        """Mock Weaviate client."""
        return MagicMock()

    @pytest.fixture
    def job(self, mock_db_pool, mock_weaviate_client):
        """Create ClusterDiscoveryJob with mocked dependencies."""
        from src.jobs.cluster_discovery import ClusterDiscoveryJob
        return ClusterDiscoveryJob(
            db_pool=mock_db_pool,
            weaviate_client=mock_weaviate_client
        )

    # =========================================================================
    # Clustering Algorithm Tests
    # =========================================================================

    def test_cluster_embeddings_groups_similar_items(self, job):
        """Similar embeddings should be in same cluster."""
        # Create embeddings where items 0,1,2 are similar, 3,4,5 are similar
        embeddings = np.array([
            [1.0, 0.0, 0.0],  # Group A
            [0.99, 0.01, 0.0],
            [0.98, 0.02, 0.0],
            [0.0, 1.0, 0.0],  # Group B
            [0.01, 0.99, 0.0],
            [0.02, 0.98, 0.0],
        ])

        clusters = job._cluster_embeddings(embeddings)

        assert len(clusters) >= 2
        # Verify items 0,1,2 are in same cluster
        found_group_a = False
        found_group_b = False
        for cluster in clusters:
            if 0 in cluster and 1 in cluster and 2 in cluster:
                found_group_a = True
            if 3 in cluster and 4 in cluster and 5 in cluster:
                found_group_b = True

        assert found_group_a, "Group A (0,1,2) should be clustered together"
        assert found_group_b, "Group B (3,4,5) should be clustered together"

    def test_noise_points_not_assigned(self, job):
        """Outlier embeddings should not be forced into clusters."""
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.99, 0.01, 0.0],
            [0.98, 0.02, 0.0],
            [0.5, 0.5, 0.0],  # Outlier - equidistant from both groups
        ])

        clusters = job._cluster_embeddings(embeddings)

        # Get all assigned indices
        all_assigned = set()
        for cluster in clusters:
            all_assigned.update(cluster)

        # Outlier (index 3) should not be in any cluster
        assert 3 not in all_assigned, "Outlier should not be assigned to a cluster"

    def test_minimum_cluster_size_respected(self, job):
        """Clusters must have minimum number of members (min_samples=3)."""
        embeddings = np.array([
            [1.0, 0.0, 0.0],  # Only 2 similar items - too small
            [0.99, 0.01, 0.0],
            [0.0, 1.0, 0.0],  # 3 similar items - valid cluster
            [0.01, 0.99, 0.0],
            [0.02, 0.98, 0.0],
        ])

        clusters = job._cluster_embeddings(embeddings, min_samples=3)

        # Should only have one cluster (the one with 3+ members)
        for cluster in clusters:
            assert len(cluster) >= 3, "Cluster must have at least min_samples members"

    def test_empty_embeddings_returns_empty_clusters(self, job):
        """Empty input should return empty clusters."""
        embeddings = np.array([]).reshape(0, 3)

        clusters = job._cluster_embeddings(embeddings)

        assert len(clusters) == 0

    def test_single_embedding_returns_empty_clusters(self, job):
        """Single embedding cannot form a cluster."""
        embeddings = np.array([[1.0, 0.0, 0.0]])

        clusters = job._cluster_embeddings(embeddings)

        assert len(clusters) == 0

    # =========================================================================
    # Cluster Name Generation Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_generate_cluster_name_from_samples(self, job):
        """Should generate meaningful cluster name from sample contents."""
        sample_contents = [
            "How do I configure API authentication?",
            "What's the best way to set up OAuth tokens?",
            "Help me understand JWT authentication",
        ]

        with patch.object(job, '_call_llm_for_name') as mock_llm:
            mock_llm.return_value = "API Authentication & Security"

            name = await job._generate_cluster_name(sample_contents)

            assert name is not None
            assert len(name) > 0
            assert len(name) <= 50  # Reasonable length limit
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_cluster_name_fallback_on_error(self, job):
        """Should return fallback name if LLM fails."""
        sample_contents = ["test content"]

        with patch.object(job, '_call_llm_for_name') as mock_llm:
            mock_llm.side_effect = Exception("LLM error")

            name = await job._generate_cluster_name(sample_contents)

            # Should return a fallback name, not raise
            assert name is not None
            assert "Topic" in name or "Cluster" in name

    # =========================================================================
    # Centroid Computation Tests
    # =========================================================================

    def test_compute_centroid_is_average(self, job):
        """Centroid should be the normalized mean of member embeddings."""
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])
        member_indices = [0, 1, 2]

        centroid = job._compute_centroid(embeddings, member_indices)

        # Expected: mean = [1/3, 1/3, 1/3], normalized = [1/sqrt(3), 1/sqrt(3), 1/sqrt(3)]
        expected_mean = np.array([1/3, 1/3, 1/3])
        expected = expected_mean / np.linalg.norm(expected_mean)
        np.testing.assert_array_almost_equal(centroid, expected)

    def test_centroid_is_normalized(self, job):
        """Centroid should be unit normalized for cosine similarity."""
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ])
        member_indices = [0, 1]

        centroid = job._compute_centroid(embeddings, member_indices)

        # Should be normalized (length ~= 1)
        norm = np.linalg.norm(centroid)
        assert abs(norm - 1.0) < 0.001, "Centroid should be unit normalized"

    # =========================================================================
    # Similarity Score Tests
    # =========================================================================

    def test_similarity_score_between_embedding_and_centroid(self, job):
        """Should compute cosine similarity between embedding and centroid."""
        embedding = np.array([1.0, 0.0, 0.0])
        centroid = np.array([1.0, 0.0, 0.0])

        similarity = job._compute_similarity(embedding, centroid)

        assert similarity == pytest.approx(1.0, abs=0.001)  # Identical vectors

    def test_similarity_score_perpendicular_vectors(self, job):
        """Perpendicular vectors should have 0 similarity."""
        embedding = np.array([1.0, 0.0, 0.0])
        centroid = np.array([0.0, 1.0, 0.0])

        similarity = job._compute_similarity(embedding, centroid)

        assert similarity == pytest.approx(0.0, abs=0.001)

    # =========================================================================
    # Database Integration Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_fetch_unassigned_memories_returns_memory_ids(self, job):
        """Should fetch memories not yet assigned to any cluster."""
        # Mock the database pool
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {'memory_id': 'mem-001'},
            {'memory_id': 'mem-002'},
            {'memory_id': 'mem-003'},
        ]

        # Create async context manager mock
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        job.db_pool = mock_pool

        memory_ids = await job._fetch_unassigned_memories()

        assert len(memory_ids) == 3
        assert 'mem-001' in memory_ids

    @pytest.mark.asyncio
    async def test_create_cluster_record(self, job):
        """Should create a new cluster record in database."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'cluster_id': 'cluster-001'}

        # Create async context manager mock
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        job.db_pool = mock_pool

        cluster_id = await job._create_cluster(
            canonical_topic="api_authentication",
            display_name="API Authentication",
            description="Questions about API auth and tokens",
            member_count=5
        )

        assert cluster_id == 'cluster-001'
        mock_conn.fetchrow.assert_called()

    @pytest.mark.asyncio
    async def test_assign_memory_to_cluster(self, job):
        """Should create cluster membership record."""
        mock_conn = AsyncMock()

        # Create async context manager mock
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        job.db_pool = mock_pool

        await job._assign_to_cluster(
            memory_id='mem-001',
            cluster_id='cluster-001',
            similarity=0.95,
            is_canonical=False
        )

        mock_conn.execute.assert_called()

    # =========================================================================
    # Full Job Run Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_run_creates_clusters_for_unassigned_memories(self, job):
        """Full job run should discover and create clusters."""
        # Setup mocks for the full flow
        mock_fetch = AsyncMock(return_value=['mem-001', 'mem-002', 'mem-003'])
        mock_embeddings = AsyncMock(return_value=(
            np.array([
                [1.0, 0.0, 0.0],
                [0.99, 0.01, 0.0],
                [0.98, 0.02, 0.0],
            ]),
            ['content1', 'content2', 'content3']
        ))
        mock_cluster = MagicMock(return_value=[[0, 1, 2]])
        mock_name = AsyncMock(return_value="Test Topic")
        mock_create = AsyncMock(return_value="cluster-001")
        mock_assign = AsyncMock()

        with patch.object(job, '_fetch_unassigned_memories', mock_fetch), \
             patch.object(job, '_get_embeddings', mock_embeddings), \
             patch.object(job, '_cluster_embeddings', mock_cluster), \
             patch.object(job, '_generate_cluster_name', mock_name), \
             patch.object(job, '_create_cluster', mock_create), \
             patch.object(job, '_assign_to_cluster', mock_assign):

            result = await job.run()

            assert result['clusters_created'] >= 1
            mock_create.assert_called()
            assert mock_assign.call_count == 3  # All 3 memories assigned


class TestClusterDiscoveryConfiguration:
    """Tests for cluster discovery configuration."""

    def test_default_eps_value(self):
        """Default DBSCAN eps should be 0.15."""
        from src.jobs.cluster_discovery import ClusterDiscoveryJob
        job = ClusterDiscoveryJob(db_pool=MagicMock(), weaviate_client=MagicMock())
        assert job.eps == 0.15

    def test_default_min_samples_value(self):
        """Default DBSCAN min_samples should be 3."""
        from src.jobs.cluster_discovery import ClusterDiscoveryJob
        job = ClusterDiscoveryJob(db_pool=MagicMock(), weaviate_client=MagicMock())
        assert job.min_samples == 3

    def test_configurable_parameters(self):
        """Should allow custom clustering parameters."""
        from src.jobs.cluster_discovery import ClusterDiscoveryJob
        job = ClusterDiscoveryJob(
            db_pool=MagicMock(),
            weaviate_client=MagicMock(),
            eps=0.2,
            min_samples=5
        )
        assert job.eps == 0.2
        assert job.min_samples == 5
