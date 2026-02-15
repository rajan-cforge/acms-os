# tests/unit/api/test_clusters_endpoints.py
"""
TDD Tests for Memory Clusters API Endpoints
Sprint 2: Memory Clustering

These tests define the expected API behavior before implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4


class TestListClustersEndpoint:
    """Tests for GET /api/v2/clusters endpoint."""

    @pytest.fixture
    def mock_db(self):
        """Mock database pool."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_returns_list_of_clusters(self, mock_db):
        """Should return paginated list of clusters."""
        from src.api.clusters_endpoints import list_clusters

        mock_clusters = [
            {
                'cluster_id': str(uuid4()),
                'canonical_topic': 'api_authentication',
                'display_name': 'API Authentication',
                'member_count': 15,
                'first_memory_at': datetime.now(timezone.utc),
                'last_memory_at': datetime.now(timezone.utc),
            },
            {
                'cluster_id': str(uuid4()),
                'canonical_topic': 'database_queries',
                'display_name': 'Database Queries',
                'member_count': 8,
                'first_memory_at': datetime.now(timezone.utc),
                'last_memory_at': datetime.now(timezone.utc),
            },
        ]

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_db.acquire.return_value.__aenter__.return_value.fetch.return_value = mock_clusters

            response = await list_clusters(limit=50, offset=0)

        assert 'clusters' in response
        assert len(response['clusters']) == 2
        assert response['clusters'][0]['display_name'] == 'API Authentication'

    @pytest.mark.asyncio
    async def test_respects_pagination_parameters(self, mock_db):
        """Should respect limit and offset parameters."""
        from src.api.clusters_endpoints import list_clusters

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch.return_value = []

            await list_clusters(limit=10, offset=20)

            # Verify the query includes limit and offset
            call_args = mock_conn.fetch.call_args
            assert 'LIMIT' in call_args[0][0] or 10 in call_args[0]
            assert 'OFFSET' in call_args[0][0] or 20 in call_args[0]

    @pytest.mark.asyncio
    async def test_returns_total_count(self, mock_db):
        """Should include total cluster count for pagination."""
        from src.api.clusters_endpoints import list_clusters

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch.return_value = []
            mock_conn.fetchval.return_value = 100

            response = await list_clusters(limit=50, offset=0)

        assert 'total' in response
        assert response['total'] == 100

    @pytest.mark.asyncio
    async def test_empty_result_when_no_clusters(self, mock_db):
        """Should return empty list when no clusters exist."""
        from src.api.clusters_endpoints import list_clusters

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch.return_value = []
            mock_conn.fetchval.return_value = 0

            response = await list_clusters()

        assert response['clusters'] == []
        assert response['total'] == 0


class TestGetClusterEndpoint:
    """Tests for GET /api/v2/clusters/{cluster_id} endpoint."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_returns_cluster_details(self, mock_db):
        """Should return full cluster details."""
        from src.api.clusters_endpoints import get_cluster

        cluster_id = str(uuid4())
        mock_cluster = {
            'cluster_id': cluster_id,
            'canonical_topic': 'api_authentication',
            'display_name': 'API Authentication',
            'description': 'Questions about API auth, OAuth, JWT',
            'member_count': 15,
            'first_memory_at': datetime.now(timezone.utc),
            'last_memory_at': datetime.now(timezone.utc),
            'avg_quality_score': 0.78,
        }

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetchrow.return_value = mock_cluster

            response = await get_cluster(cluster_id)

        assert response['cluster_id'] == cluster_id
        assert response['display_name'] == 'API Authentication'
        assert 'member_count' in response

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_cluster(self, mock_db):
        """Should return 404 when cluster doesn't exist."""
        from src.api.clusters_endpoints import get_cluster
        from fastapi import HTTPException

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetchrow.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await get_cluster("nonexistent-id")

            assert exc_info.value.status_code == 404


class TestGetClusterMembersEndpoint:
    """Tests for GET /api/v2/clusters/{cluster_id}/members endpoint."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_returns_cluster_members(self, mock_db):
        """Should return memories belonging to cluster."""
        from src.api.clusters_endpoints import get_cluster_members

        cluster_id = str(uuid4())
        mock_members = [
            {
                'memory_id': str(uuid4()),
                'content': 'How do I configure OAuth?',
                'similarity_score': 0.95,
                'is_canonical': True,
                'created_at': datetime.now(timezone.utc),
            },
            {
                'memory_id': str(uuid4()),
                'content': 'JWT token configuration help',
                'similarity_score': 0.87,
                'is_canonical': False,
                'created_at': datetime.now(timezone.utc),
            },
        ]

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch.return_value = mock_members

            response = await get_cluster_members(cluster_id, limit=20, offset=0)

        assert 'members' in response
        assert len(response['members']) == 2
        assert response['members'][0]['is_canonical'] is True

    @pytest.mark.asyncio
    async def test_members_ordered_by_similarity(self, mock_db):
        """Members should be ordered by similarity score descending."""
        from src.api.clusters_endpoints import get_cluster_members

        cluster_id = str(uuid4())

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch.return_value = [
                {'memory_id': 'm1', 'similarity_score': 0.95},
                {'memory_id': 'm2', 'similarity_score': 0.87},
                {'memory_id': 'm3', 'similarity_score': 0.82},
            ]

            response = await get_cluster_members(cluster_id)

        # Verify ordering
        scores = [m['similarity_score'] for m in response['members']]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_canonical_member_marked(self, mock_db):
        """Should mark the canonical (most representative) member."""
        from src.api.clusters_endpoints import get_cluster_members

        cluster_id = str(uuid4())

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch.return_value = [
                {'memory_id': 'm1', 'is_canonical': True, 'similarity_score': 0.95},
                {'memory_id': 'm2', 'is_canonical': False, 'similarity_score': 0.87},
            ]

            response = await get_cluster_members(cluster_id)

        canonical_members = [m for m in response['members'] if m.get('is_canonical')]
        assert len(canonical_members) == 1


class TestUpdateClusterEndpoint:
    """Tests for PATCH /api/v2/clusters/{cluster_id} endpoint."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_can_update_display_name(self, mock_db):
        """Should allow updating cluster display name."""
        from src.api.clusters_endpoints import update_cluster

        cluster_id = str(uuid4())

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetchrow.return_value = {
                'cluster_id': cluster_id,
                'display_name': 'Updated Name',
            }

            response = await update_cluster(
                cluster_id,
                display_name='Updated Name'
            )

        assert response['display_name'] == 'Updated Name'

    @pytest.mark.asyncio
    async def test_can_update_description(self, mock_db):
        """Should allow updating cluster description."""
        from src.api.clusters_endpoints import update_cluster

        cluster_id = str(uuid4())

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetchrow.return_value = {
                'cluster_id': cluster_id,
                'description': 'New description',
            }

            response = await update_cluster(
                cluster_id,
                description='New description'
            )

        assert response['description'] == 'New description'


class TestDeleteClusterEndpoint:
    """Tests for DELETE /api/v2/clusters/{cluster_id} endpoint."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_deletes_cluster(self, mock_db):
        """Should delete cluster and unassign members."""
        from src.api.clusters_endpoints import delete_cluster

        cluster_id = str(uuid4())

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.execute.return_value = 'DELETE 1'

            response = await delete_cluster(cluster_id)

        assert response['deleted'] is True
        mock_conn.execute.assert_called()

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_cluster(self, mock_db):
        """Should return 404 when deleting nonexistent cluster."""
        from src.api.clusters_endpoints import delete_cluster
        from fastapi import HTTPException

        with patch('src.api.clusters_endpoints.get_db_pool', return_value=mock_db):
            mock_conn = AsyncMock()
            mock_db.acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.execute.return_value = 'DELETE 0'

            with pytest.raises(HTTPException) as exc_info:
                await delete_cluster("nonexistent-id")

            assert exc_info.value.status_code == 404
