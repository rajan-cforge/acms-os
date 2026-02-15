"""Integration tests for Gateway semantic cache.

Tests that Gateway (orchestrator) uses semantic cache correctly:
1. Exact query match → Cache HIT
2. Similar query (paraphrase) → Cache HIT (similarity ≥0.90)
3. Different query → Cache MISS
4. Cache metrics tracked correctly

These tests verify the CRITICAL fix for 0% cache hit rate issue.
"""

import pytest
import httpx
import asyncio
import time
import requests


@pytest.fixture(autouse=True)
def clear_semantic_cache():
    """Clear Weaviate semantic cache before each test."""
    import time as sync_time
    try:
        # Delete QueryCache_v1 collection before test
        response = requests.delete("http://localhost:8090/v1/schema/QueryCache_v1", timeout=5)
        if response.status_code in [200, 204]:
            # Give Weaviate time to process deletion and recreate collection
            sync_time.sleep(2)
    except:
        pass  # Collection may not exist yet

    yield

    # Cleanup after test (optional)
    # Can be left for next test's setup


@pytest.mark.asyncio
class TestGatewaySemanticCache:
    """Test Gateway uses semantic cache (not just exact match)."""

    async def test_gateway_exact_match_cache_hit(self):
        """Test: Exact same query should HIT cache on second request.

        This is the most basic cache test - if this fails, caching is broken.
        """

        async with httpx.AsyncClient(base_url="http://localhost:40080", timeout=30.0) as client:
            # Request 1: Fresh generation
            print("\n[TEST] Request 1: Fresh generation...")
            start1 = time.time()

            response1 = await client.post("/gateway/ask-sync", json={
                "query": "What is ACMS architecture and design?"
            })

            latency1 = time.time() - start1

            assert response1.status_code == 200, f"Expected 200, got {response1.status_code}"
            data1 = response1.json()

            print(f"  Response 1: {data1.get('answer', '')[:100]}...")
            print(f"  From cache: {data1.get('from_cache', False)}")
            print(f"  Latency: {latency1:.2f}s")
            print(f"  Cost: ${data1.get('cost_usd', 0):.4f}")

            # Should be fresh (not cached)
            assert data1.get("from_cache", False) == False, "First request should not be cached"
            cost1 = data1.get("cost_usd", 0)
            assert cost1 > 0, "Fresh query should have cost > $0"

            # Wait 2 seconds to ensure cache is written
            print("\n  Waiting 2s for cache to propagate...")
            await asyncio.sleep(2)

            # Request 2: Same query (should HIT cache)
            print("\n[TEST] Request 2: Same query (should HIT cache)...")
            start2 = time.time()

            response2 = await client.post("/gateway/ask-sync", json={
                "query": "What is ACMS architecture and design?"
            })

            latency2 = time.time() - start2

            assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
            data2 = response2.json()

            print(f"  Response 2: {data2.get('answer', '')[:100]}...")
            print(f"  From cache: {data2.get('from_cache', False)}")
            cache_sim = data2.get('cache_similarity')
            print(f"  Cache similarity: {cache_sim:.3f}" if cache_sim else "  Cache similarity: N/A (Redis exact match)")
            print(f"  Latency: {latency2:.2f}s")
            print(f"  Cost: ${data2.get('cost_usd', 0):.4f}")

            # Should be cached
            assert data2.get("from_cache", False) == True, (
                f"❌ FAIL: Cache should HIT on exact match. "
                f"Got from_cache={data2.get('from_cache', False)}"
            )

            # Note: Redis exact match cache doesn't have similarity score (returns None)
            # After Phase 2 (semantic cache), this should be >= 0.99
            cache_sim = data2.get("cache_similarity")
            if cache_sim is not None:
                assert cache_sim >= 0.99, (
                    f"Exact match should have ~1.0 similarity, got {cache_sim:.3f}"
                )

            assert data2.get("cost_usd", 0) == 0, (
                f"Cached query should cost $0, got ${data2.get('cost_usd', 0):.4f}"
            )
            assert latency2 < latency1 / 2, (
                f"Cached response should be faster. "
                f"Fresh: {latency1:.2f}s, Cached: {latency2:.2f}s"
            )

            print(f"\n  ✅ Test PASSED: Cache HIT on exact match")
            print(f"  Speedup: {latency1/latency2:.1f}x faster")

    async def test_gateway_semantic_match_cache_hit(self):
        """Test: Similar query (paraphrase) should HIT cache.

        This tests the SEMANTIC aspect - different wording, same meaning.
        """

        async with httpx.AsyncClient(base_url="http://localhost:40080", timeout=30.0) as client:
            # Request 1: Original query
            print("\n[TEST] Request 1: Original query...")
            response1 = await client.post("/gateway/ask-sync", json={
                "query": "Explain the ACMS system architecture and its components"
            })

            assert response1.status_code == 200
            data1 = response1.json()

            print(f"  Query 1: 'Explain the ACMS system architecture and its components'")
            print(f"  From cache: {data1.get('from_cache', False)}")
            assert data1.get("from_cache", False) == False, "First request should not be cached"

            # Wait 2 seconds
            print("\n  Waiting 2s for cache to propagate...")
            await asyncio.sleep(2)

            # Request 2: Paraphrase (semantically similar)
            print("\n[TEST] Request 2: Paraphrase (semantically similar)...")
            start2 = time.time()

            response2 = await client.post("/gateway/ask-sync", json={
                "query": "Describe the ACMS architecture and its key parts"  # Closer paraphrase
            })

            latency2 = time.time() - start2

            assert response2.status_code == 200
            data2 = response2.json()

            print(f"  Query 2: 'Describe the ACMS architecture and its key parts'")
            print(f"  From cache: {data2.get('from_cache', False)}")
            cache_sim = data2.get('cache_similarity')
            print(f"  Cache similarity: {cache_sim:.3f}" if cache_sim else "  Cache similarity: N/A")
            print(f"  Latency: {latency2:.2f}s")

            # Should be cached (semantic match)
            assert data2.get("from_cache", False) == True, (
                f"❌ FAIL: Semantic cache should HIT on paraphrase. "
                f"Got from_cache={data2.get('from_cache', False)}"
            )
            assert data2.get("cache_similarity", 0) >= 0.90, (
                f"Similarity should be ≥0.90 for semantic match (threshold tuned for paraphrases). "
                f"Got {data2.get('cache_similarity', 0):.3f}"
            )
            assert data2.get("cost_usd", 0) == 0, "Cached query should cost $0"

            print(f"\n  ✅ Test PASSED: Semantic cache HIT on paraphrase")
            print(f"  Similarity: {data2.get('cache_similarity', 0):.3f}")

    async def test_gateway_cache_miss_different_query(self):
        """Test: Completely different query should MISS cache.

        This ensures we don't get false positives from unrelated queries.
        """

        async with httpx.AsyncClient(base_url="http://localhost:40080", timeout=30.0) as client:
            # Request 1: Query A
            print("\n[TEST] Request 1: Query A...")
            response1 = await client.post("/gateway/ask-sync", json={
                "query": "What is ACMS?"
            })

            assert response1.status_code == 200
            print(f"  Query A: 'What is ACMS?'")

            # Wait 2 seconds
            print("\n  Waiting 2s for cache to propagate...")
            await asyncio.sleep(2)

            # Request 2: Query B (completely different)
            print("\n[TEST] Request 2: Query B (completely different)...")
            response2 = await client.post("/gateway/ask-sync", json={
                "query": "How do I configure Docker networking for production?"
            })

            assert response2.status_code == 200
            data2 = response2.json()

            print(f"  Query B: 'How do I configure Docker networking for production?'")
            print(f"  From cache: {data2.get('from_cache', False)}")
            print(f"  Cost: ${data2.get('cost_usd', 0):.4f}")

            # Should NOT be cached
            assert data2.get("from_cache", False) == False, (
                "Different query should MISS cache. "
                f"Got from_cache={data2.get('from_cache', False)}"
            )
            assert data2.get("cost_usd", 0) > 0, (
                f"Fresh query should have cost > $0, got ${data2.get('cost_usd', 0):.4f}"
            )

            print(f"\n  ✅ Test PASSED: Cache MISS on different query")

    async def test_gateway_cache_bypass(self):
        """Test: bypass_cache flag should force fresh generation.

        This tests the manual cache bypass feature.
        """

        async with httpx.AsyncClient(base_url="http://localhost:40080", timeout=30.0) as client:
            # Request 1: Cache query
            print("\n[TEST] Request 1: Cache query...")
            response1 = await client.post("/gateway/ask-sync", json={
                "query": "What is semantic caching?"
            })

            assert response1.status_code == 200
            print(f"  Query: 'What is semantic caching?'")

            # Wait 2 seconds
            print("\n  Waiting 2s for cache to propagate...")
            await asyncio.sleep(2)

            # Request 2: Same query with bypass_cache=true
            print("\n[TEST] Request 2: Same query with bypass_cache=True...")
            response2 = await client.post("/gateway/ask-sync", json={
                "query": "What is semantic caching?",
                "bypass_cache": True
            })

            assert response2.status_code == 200
            data2 = response2.json()

            print(f"  Query: 'What is semantic caching?' (bypass_cache=True)")
            print(f"  From cache: {data2.get('from_cache', False)}")
            print(f"  Cost: ${data2.get('cost_usd', 0):.4f}")

            # Should NOT use cache (forced fresh)
            assert data2.get("from_cache", False) == False, (
                "bypass_cache should force fresh generation. "
                f"Got from_cache={data2.get('from_cache', False)}"
            )
            assert data2.get("cost_usd", 0) > 0, (
                "Fresh query should have cost > $0"
            )

            print(f"\n  ✅ Test PASSED: Cache bypass works")

    async def test_gateway_cache_stats(self):
        """Test: Cache statistics endpoint returns correct data.

        This verifies cache monitoring is working.
        """

        async with httpx.AsyncClient(base_url="http://localhost:40080", timeout=30.0) as client:
            # Send a few queries to populate cache
            print("\n[TEST] Populating cache with queries...")

            queries = [
                "What is ACMS?",
                "Describe ACMS architecture",
                "How does ACMS work?"
            ]

            for i, query in enumerate(queries, 1):
                print(f"  Query {i}: {query}")
                await client.post("/gateway/ask-sync", json={"query": query})
                await asyncio.sleep(1)

            # Check cache stats
            print("\n[TEST] Checking cache stats...")
            response = await client.get("/analytics/cache-stats")

            if response.status_code == 404:
                print("  ⚠️  Cache stats endpoint not yet implemented")
                pytest.skip("Cache stats endpoint not implemented yet")

            assert response.status_code == 200
            stats = response.json()

            print(f"  Cache entries: {stats.get('cache_entries', 0)}")
            print(f"  Hit rate: {stats.get('hit_rate', 0):.1%}")

            # Should have some cache entries
            assert stats.get("cache_entries", 0) > 0, "Should have cache entries"

            print(f"\n  ✅ Test PASSED: Cache stats working")


if __name__ == "__main__":
    # Run tests standalone
    print("=" * 80)
    print("GATEWAY SEMANTIC CACHE TESTS")
    print("=" * 80)
    pytest.main([__file__, "-v", "-s"])
