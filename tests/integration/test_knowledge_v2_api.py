# tests/integration/test_knowledge_v2_api.py
"""
Integration Tests for Knowledge V2 API
Sprint 3: Knowledge Consolidation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi.testclient import TestClient


class TestKnowledgeV2Endpoints:
    """Integration tests for knowledge v2 API endpoints."""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock database pool."""
        pool = MagicMock()
        return pool

    @pytest.fixture
    def client(self, mock_db_pool):
        """Create test client with mocked dependencies."""
        with patch('src.api.knowledge_v2_endpoints.get_db_pool') as mock_get_pool:
            mock_get_pool.return_value = mock_db_pool
            from src.api_server import app
            return TestClient(app)

    # =========================================================================
    # List Knowledge Tests
    # =========================================================================

    def test_list_knowledge_empty(self, client, mock_db_pool):
        """Should return empty list when no knowledge."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 0
        mock_conn.fetch.return_value = []

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.get("/api/v2/knowledge/")

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert data['items'] == []

    def test_list_knowledge_with_domain_filter(self, client, mock_db_pool):
        """Should filter by domain path."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_conn.fetch.return_value = [{
            'knowledge_id': uuid4(),
            'canonical_content': 'Python is great',
            'knowledge_type': 'fact',
            'domain_path': 'technology/programming',
            'effective_confidence': 0.8,
            'base_confidence': 0.5,
            'source_count': 3,
            'source_boost': 0.1,
            'verification_boost': 0.25,
            'is_verified': True,
            'is_active': True,
            'needs_review': False,
            'first_derived_at': datetime.now(timezone.utc),
            'last_confirmed_at': datetime.now(timezone.utc)
        }]

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.get("/api/v2/knowledge/?domain=technology")

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 1
        assert len(data['items']) == 1

    # =========================================================================
    # Domain Tests
    # =========================================================================

    def test_list_domains(self, client, mock_db_pool):
        """Should return all domains."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {
                'domain_id': uuid4(),
                'name': 'technology',
                'display_name': 'Technology',
                'parent_path': None,
                'level': 0,
                'knowledge_count': 10,
                'verified_count': 5,
                'icon': '💻',
                'color': '#2196F3'
            },
            {
                'domain_id': uuid4(),
                'name': 'technology/programming',
                'display_name': 'Programming',
                'parent_path': 'technology',
                'level': 1,
                'knowledge_count': 5,
                'verified_count': 2,
                'icon': '📝',
                'color': '#4CAF50'
            }
        ]

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.get("/api/v2/knowledge/domains")

        assert response.status_code == 200
        domains = response.json()
        assert len(domains) == 2
        assert domains[0]['name'] == 'technology'

    def test_domain_tree(self, client, mock_db_pool):
        """Should return hierarchical domain tree."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {
                'domain_id': uuid4(),
                'name': 'technology',
                'display_name': 'Technology',
                'parent_path': None,
                'level': 0,
                'knowledge_count': 10,
                'verified_count': 5,
                'icon': '💻',
                'color': '#2196F3'
            },
            {
                'domain_id': uuid4(),
                'name': 'technology/programming',
                'display_name': 'Programming',
                'parent_path': 'technology',
                'level': 1,
                'knowledge_count': 5,
                'verified_count': 2,
                'icon': '📝',
                'color': '#4CAF50'
            }
        ]

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.get("/api/v2/knowledge/domains/tree")

        assert response.status_code == 200
        tree = response.json()
        assert len(tree) == 1  # Only root nodes
        assert tree[0]['domain']['name'] == 'technology'
        assert len(tree[0]['children']) == 1

    # =========================================================================
    # Knowledge Detail Tests
    # =========================================================================

    def test_get_knowledge_detail(self, client, mock_db_pool):
        """Should return knowledge with provenance."""
        knowledge_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            'knowledge_id': knowledge_id,
            'canonical_content': 'Python is great',
            'knowledge_type': 'fact',
            'domain_path': 'technology/programming',
            'effective_confidence': 0.8,
            'base_confidence': 0.5,
            'source_count': 3,
            'source_boost': 0.1,
            'verification_boost': 0.25,
            'is_verified': True,
            'is_active': True,
            'needs_review': False,
            'first_derived_at': datetime.now(timezone.utc),
            'last_confirmed_at': datetime.now(timezone.utc)
        }
        mock_conn.fetch.return_value = [
            {
                'provenance_id': uuid4(),
                'source_type': 'query_history',
                'source_id': uuid4(),
                'source_timestamp': datetime.now(timezone.utc),
                'source_preview': 'User asked about Python...',
                'contribution_type': 'original',
                'confidence_at_extraction': 0.5,
                'created_at': datetime.now(timezone.utc)
            }
        ]

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.get(f"/api/v2/knowledge/{knowledge_id}")

        assert response.status_code == 200
        data = response.json()
        assert 'knowledge' in data
        assert 'provenance' in data
        assert len(data['provenance']) == 1

    def test_get_knowledge_not_found(self, client, mock_db_pool):
        """Should return 404 for missing knowledge."""
        knowledge_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.get(f"/api/v2/knowledge/{knowledge_id}")

        assert response.status_code == 404

    # =========================================================================
    # Confidence Breakdown Tests
    # =========================================================================

    def test_confidence_breakdown(self, client, mock_db_pool):
        """Should return confidence breakdown with indicators."""
        knowledge_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            'base_confidence': 0.5,
            'source_boost': 0.2,
            'verification_boost': 0.25,
            'effective_confidence': 0.95,
            'source_count': 5,
            'is_verified': True
        }

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.get(f"/api/v2/knowledge/{knowledge_id}/confidence")

        assert response.status_code == 200
        data = response.json()
        assert data['effective_confidence'] == 0.95
        assert data['indicator_dots'] == '●●●●○'
        assert data['indicator_color'] == 'green'

    # =========================================================================
    # Verification Tests
    # =========================================================================

    def test_verify_knowledge(self, client, mock_db_pool):
        """Should verify knowledge item."""
        knowledge_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            'knowledge_id': knowledge_id,
            'canonical_content': 'Python is great',
            'knowledge_type': 'fact',
            'domain_path': 'technology/programming',
            'effective_confidence': 0.75,
            'base_confidence': 0.5,
            'source_count': 1,
            'source_boost': 0.0,
            'verification_boost': 0.25,
            'is_verified': True,
            'is_active': True,
            'needs_review': False,
            'first_derived_at': datetime.now(timezone.utc),
            'last_confirmed_at': None
        }

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.post(
                f"/api/v2/knowledge/{knowledge_id}/verify",
                json={"verified_by": "test_user"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data['is_verified'] is True

    def test_unverify_knowledge(self, client, mock_db_pool):
        """Should remove verification from knowledge."""
        knowledge_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            'knowledge_id': knowledge_id,
            'canonical_content': 'Python is great',
            'knowledge_type': 'fact',
            'domain_path': 'technology/programming',
            'effective_confidence': 0.5,
            'base_confidence': 0.5,
            'source_count': 1,
            'source_boost': 0.0,
            'verification_boost': 0.0,
            'is_verified': False,
            'is_active': True,
            'needs_review': False,
            'first_derived_at': datetime.now(timezone.utc),
            'last_confirmed_at': None
        }

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.post(f"/api/v2/knowledge/{knowledge_id}/unverify")

        assert response.status_code == 200
        data = response.json()
        assert data['is_verified'] is False

    # =========================================================================
    # Update/Delete Tests
    # =========================================================================

    def test_update_knowledge(self, client, mock_db_pool):
        """Should update knowledge content."""
        knowledge_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            'knowledge_id': knowledge_id,
            'canonical_content': 'Updated content',
            'knowledge_type': 'fact',
            'domain_path': 'technology',
            'effective_confidence': 0.5,
            'base_confidence': 0.5,
            'source_count': 1,
            'source_boost': 0.0,
            'verification_boost': 0.0,
            'is_verified': False,
            'is_active': True,
            'needs_review': False,
            'first_derived_at': datetime.now(timezone.utc),
            'last_confirmed_at': None
        }

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.patch(
                f"/api/v2/knowledge/{knowledge_id}",
                json={"canonical_content": "Updated content"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data['canonical_content'] == 'Updated content'

    def test_delete_knowledge(self, client, mock_db_pool):
        """Should soft delete knowledge."""
        knowledge_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 1"

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.delete(f"/api/v2/knowledge/{knowledge_id}")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'deleted'

    # =========================================================================
    # Stats Tests
    # =========================================================================

    def test_knowledge_stats(self, client, mock_db_pool):
        """Should return knowledge base statistics."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            'total': 100,
            'verified': 25,
            'needs_review': 10,
            'avg_confidence': 0.72,
            'avg_sources': 2.5,
            'domain_count': 8
        }
        mock_conn.fetch.return_value = [
            {'domain_path': 'technology/programming', 'count': 50},
            {'domain_path': 'personal/preferences', 'count': 30}
        ]

        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.knowledge_v2_endpoints.get_db_pool', return_value=mock_db_pool):
            response = client.get("/api/v2/knowledge/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 100
        assert data['verified'] == 25
        assert len(data['top_domains']) == 2
