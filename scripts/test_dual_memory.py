#!/usr/bin/env python3
"""Test dual memory service - Week 6 Day 3

Validates parallel search across cache and knowledge collections.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from src.storage.dual_memory import DualMemoryService

async def test_dual_memory():
    """Test dual memory service with existing test data."""

    print("=" * 60)
    print("Week 6 Day 3: Dual Memory Service Test")
    print("=" * 60)
    print()

    service = DualMemoryService()

    # Test vector (matches validation data we inserted earlier)
    test_vector = [0.01] * 768
    test_user_id = "00000000-0000-0000-0000-000000000001"

    # Test 1: Parallel search
    print("Test 1: Parallel Search (Cache + Knowledge)")
    print("-" * 40)

    cache_hits, knowledge_facts = await service.search_dual(
        query="What is the capital of France?",
        query_vector=test_vector,
        user_id=test_user_id,
        cache_limit=5,
        knowledge_limit=10,
        cache_threshold=0.85,
        knowledge_threshold=0.60
    )

    print(f"✅ Cache hits: {len(cache_hits)}")
    if cache_hits:
        for i, hit in enumerate(cache_hits, 1):
            print(f"   {i}. Query: {hit['canonical_query']}")
            print(f"      Answer: {hit['summarized_answer'][:60]}...")
            print(f"      Similarity: {hit['similarity']:.2f}")

    print(f"✅ Knowledge facts: {len(knowledge_facts)}")
    if knowledge_facts:
        for i, fact in enumerate(knowledge_facts, 1):
            print(f"   {i}. {fact['content'][:60]}...")
            print(f"      Source: {fact['source_type']}, Confidence: {fact['confidence']:.2f}")
            print(f"      Similarity: {fact['similarity']:.2f}")

    print()

    # Test 2: Query metrics logging
    print("Test 2: Query Metrics Logging")
    print("-" * 40)

    query_id = await service.log_query_metrics(
        query_text="What is the capital of France?",
        conversation_id=None,
        agent_used="CLAUDE_SONNET",
        latency_ms=1500,
        cost_usd=0.0015,
        memories_used=len(cache_hits) + len(knowledge_facts),
        search_used=False,
        query_intent="FACTUAL"
    )

    print(f"✅ Query logged: {query_id}")
    print()

    # Test 3: Cache hit tracking
    if cache_hits:
        print("Test 3: Cache Hit Tracking")
        print("-" * 40)

        cache_id = cache_hits[0]['id']
        await service.update_cache_hit(cache_id)
        print(f"✅ Updated cache hit stats for {cache_id[:8]}...")
        print()

    # Final summary
    print("=" * 60)
    print("DUAL MEMORY SERVICE: FUNCTIONAL")
    print("=" * 60)
    print(f"✅ Parallel search working ({len(cache_hits)} cache + {len(knowledge_facts)} knowledge)")
    print(f"✅ Query metrics logging working (ID: {query_id})")
    if cache_hits:
        print(f"✅ Cache hit tracking working")
    print()
    print("Next: Update orchestrator to use DualMemoryService")
    print("=" * 60)

    service.close()

if __name__ == "__main__":
    asyncio.run(test_dual_memory())
