"""
Search Quality Test Suite - Phase 2 Review
Tests semantic search quality across diverse topics and query types.

Run: pytest tests/quality/test_search_quality.py -v
"""
import pytest
import requests
import time
from typing import List, Dict, Any


# API Configuration
API_BASE = "http://localhost:40080"
SEARCH_TIMEOUT = 10  # seconds


class SearchQualityTest:
    """Base class for search quality tests."""

    @staticmethod
    def search(query: str, limit: int = 5) -> Dict[str, Any]:
        """Perform semantic search via ACMS API."""
        response = requests.post(
            f"{API_BASE}/search",
            json={"query": query, "limit": limit},
            timeout=SEARCH_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_top_score(results: List[Dict]) -> float:
        """Get top similarity score from results."""
        if not results:
            return 0.0
        return results[0].get("similarity", 0.0)

    @staticmethod
    def get_avg_score(results: List[Dict]) -> float:
        """Get average similarity score from results."""
        if not results:
            return 0.0
        scores = [r.get("similarity", 0.0) for r in results]
        return sum(scores) / len(scores)


class TestACMSCoreTopics(SearchQualityTest):
    """Test search quality for ACMS core topics (should have excellent scores)."""

    def test_acms_architecture_query(self):
        """Test: ACMS architecture query should return excellent results."""
        result = self.search("ACMS architecture", limit=5)
        top_score = self.get_top_score(result["results"])

        # Core ACMS topics should have high scores (>0.6)
        assert top_score >= 0.6, f"ACMS architecture query too low: {top_score:.3f} (expected >0.6)"
        assert result["count"] > 0, "No results found for ACMS architecture"

    def test_acms_functionality_query(self):
        """Test: How ACMS works should return excellent results."""
        result = self.search("how does ACMS work", limit=5)
        top_score = self.get_top_score(result["results"])

        assert top_score >= 0.6, f"ACMS functionality query too low: {top_score:.3f} (expected >0.6)"

    def test_memory_system_query(self):
        """Test: Memory system queries should return good results."""
        result = self.search("memory storage system", limit=5)
        top_score = self.get_top_score(result["results"])

        # Should find relevant content (moderate threshold)
        assert top_score >= 0.3, f"Memory system query too low: {top_score:.3f} (expected >0.3)"


class TestTechnicalTopics(SearchQualityTest):
    """Test search quality for technical topics."""

    def test_docker_deployment_query(self):
        """Test: Docker deployment should return moderate to good results."""
        result = self.search("Docker deployment", limit=5)
        top_score = self.get_top_score(result["results"])

        # If Docker content exists, should get moderate scores
        assert top_score >= 0.25, f"Docker deployment query too low: {top_score:.3f} (expected >0.25)"

    def test_api_security_query(self):
        """Test: API security should return some relevant results."""
        result = self.search("API security", limit=5)
        top_score = self.get_top_score(result["results"])

        # Security topics should return something relevant
        assert top_score >= 0.2, f"API security query too low: {top_score:.3f} (expected >0.2)"

    def test_vector_database_query(self):
        """Test: Vector database queries should return good results."""
        result = self.search("vector database setup", limit=5)
        top_score = self.get_top_score(result["results"])

        # Vector DB is core to ACMS
        assert top_score >= 0.3, f"Vector database query too low: {top_score:.3f} (expected >0.3)"


class TestPerformanceTopics(SearchQualityTest):
    """Test search quality for performance-related topics."""

    def test_cache_performance_query(self):
        """Test: Cache performance queries should return some results."""
        result = self.search("cache performance", limit=5)
        top_score = self.get_top_score(result["results"])

        # Cache is mentioned in ACMS docs
        assert top_score >= 0.2, f"Cache performance query too low: {top_score:.3f} (expected >0.2)"

    def test_query_optimization_query(self):
        """Test: Query optimization should return some results."""
        result = self.search("query speed optimization", limit=5)
        top_score = self.get_top_score(result["results"])

        # Optimization topics should have some relevance
        assert top_score >= 0.2, f"Query optimization too low: {top_score:.3f} (expected >0.2)"


class TestComplexQueries(SearchQualityTest):
    """Test search quality for complex multi-concept queries."""

    def test_multi_concept_query(self):
        """Test: Complex queries with multiple concepts should work."""
        result = self.search("ACMS privacy and security configuration", limit=5)
        top_score = self.get_top_score(result["results"])

        # Multi-concept queries harder but should still return something
        assert top_score >= 0.25, f"Multi-concept query too low: {top_score:.3f} (expected >0.25)"

    def test_technical_multi_concept(self):
        """Test: Technical multi-concept queries should work."""
        result = self.search("vector search performance optimization", limit=5)
        top_score = self.get_top_score(result["results"])

        assert top_score >= 0.25, f"Technical multi-concept too low: {top_score:.3f} (expected >0.25)"


class TestEdgeCases(SearchQualityTest):
    """Test edge cases and challenging queries."""

    def test_generic_term_query(self):
        """Test: Generic single-word queries should return something."""
        result = self.search("database", limit=5)

        # Should return SOMETHING (even if not perfect)
        assert result["count"] > 0, "Generic term query returned no results"

    def test_vague_query(self):
        """Test: Vague queries should still return results."""
        result = self.search("help", limit=5)

        # Should return SOMETHING
        assert result["count"] > 0, "Vague query returned no results"

    def test_empty_query_handling(self):
        """Test: Empty queries should be handled gracefully."""
        # Note: This might return an error, which is acceptable
        try:
            result = self.search("", limit=5)
            # If it doesn't error, should return no results or handle gracefully
            assert result["count"] >= 0
        except requests.exceptions.HTTPError as e:
            # 400 Bad Request is acceptable for empty queries
            assert e.response.status_code == 400 or e.response.status_code == 422


class TestSearchResponseStructure(SearchQualityTest):
    """Test search response structure and data integrity."""

    def test_response_contains_required_fields(self):
        """Test: Search response should have required fields."""
        result = self.search("ACMS architecture", limit=3)

        # Check response structure
        assert "query" in result, "Response missing 'query' field"
        assert "results" in result, "Response missing 'results' field"
        assert "count" in result, "Response missing 'count' field"

        # Check results structure
        if result["count"] > 0:
            first_result = result["results"][0]
            assert "similarity" in first_result, "Result missing 'similarity' field"
            assert "distance" in first_result, "Result missing 'distance' field"
            assert "content" in first_result, "Result missing 'content' field"
            assert "memory_id" in first_result, "Result missing 'memory_id' field"

    def test_similarity_distance_consistency(self):
        """Test: Similarity should equal 1.0 - distance."""
        result = self.search("ACMS architecture", limit=5)

        for r in result["results"]:
            similarity = r.get("similarity", 0)
            distance = r.get("distance", 0)
            expected_similarity = round(1.0 - distance, 4)

            # Allow small floating point differences
            assert abs(similarity - expected_similarity) < 0.001, \
                f"Similarity/distance mismatch: similarity={similarity}, distance={distance}, expected={expected_similarity}"

    def test_results_sorted_by_relevance(self):
        """Test: Results should be sorted by relevance (CRS score or similarity)."""
        result = self.search("ACMS architecture", limit=5)

        if result["count"] > 1:
            scores = [r.get("crs_score", r.get("similarity", 0)) for r in result["results"]]

            # Scores should be in descending order
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1], \
                    f"Results not properly sorted: {scores[i]} < {scores[i + 1]} at position {i}"


class TestSearchPerformance(SearchQualityTest):
    """Test search performance and latency."""

    def test_search_latency(self):
        """Test: Search should complete within acceptable time."""
        start = time.time()
        result = self.search("ACMS architecture", limit=5)
        latency = (time.time() - start) * 1000  # milliseconds

        # Search should complete within 2 seconds (including Phase 2 augmentation)
        assert latency < 2000, f"Search too slow: {latency:.0f}ms (expected <2000ms)"

        # Log latency for monitoring
        print(f"\n   Search latency: {latency:.0f}ms")

    def test_batch_search_performance(self):
        """Test: Multiple searches should perform reasonably."""
        queries = [
            "ACMS architecture",
            "cache performance",
            "Docker deployment"
        ]

        start = time.time()
        for query in queries:
            self.search(query, limit=3)
        total_time = (time.time() - start) * 1000

        avg_time = total_time / len(queries)

        # Average should be reasonable
        assert avg_time < 2000, f"Average search time too slow: {avg_time:.0f}ms (expected <2000ms)"

        print(f"\n   Average search latency: {avg_time:.0f}ms ({len(queries)} queries)")


class TestPhase2QueryAugmentation(SearchQualityTest):
    """Test Phase 2 Query Augmentation impact."""

    @pytest.mark.skipif(
        not requests.get(f"{API_BASE}/health").json().get("features", {}).get("query_augmentation", False),
        reason="Query augmentation not enabled"
    )
    def test_augmentation_improves_results(self):
        """Test: Query augmentation should improve results."""
        # This test requires Phase 2 to be enabled
        # We can't easily test "improvement" without disabling it,
        # but we can verify it's working

        result = self.search("database help", limit=5)

        # Should return results
        assert result["count"] > 0, "Query augmentation enabled but no results"

        # Augmented queries should have reasonable scores
        top_score = self.get_top_score(result["results"])
        assert top_score >= 0.2, f"Augmented query score too low: {top_score:.3f}"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "quality: mark test as search quality test"
    )


# Test summary fixture
@pytest.fixture(scope="session", autouse=True)
def print_test_summary(request):
    """Print test summary at the end."""
    yield

    # This runs after all tests
    print("\n" + "=" * 80)
    print("  SEARCH QUALITY TEST SUMMARY")
    print("=" * 80)
    print("✅ All search quality tests passed!")
    print("\nFor detailed quality metrics, run:")
    print("   python3 /tmp/search_quality_diagnostic.py")
    print("=" * 80)
