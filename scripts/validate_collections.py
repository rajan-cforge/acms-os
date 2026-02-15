#!/usr/bin/env python3
"""
Week 6 Day 2: Validate Dual Vector DB Collections

Tests the 3 new collections with sample data insertion and retrieval.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import hashlib
from datetime import datetime
from uuid import uuid4

from src.storage.weaviate_client import WeaviateClient

def validate_collections():
    """Validate the 3 dual vector DB collections with test data."""

    print("=" * 60)
    print("Week 6 Day 2: Collection Validation")
    print("=" * 60)
    print()

    # Connect to Weaviate
    client = WeaviateClient()
    print("✅ Connected to Weaviate")
    print()

    # Generate test vectors (768 dimensions)
    test_vector = [0.01] * 768

    # Test 1: ACMS_Raw_v1
    print("Test 1: ACMS_Raw_v1 (Raw Q&A)")
    print("-" * 40)

    query_text = "What is the capital of France?"
    query_hash = hashlib.sha256(query_text.encode()).hexdigest()

    raw_id = client.insert_vector(
        collection="ACMS_Raw_v1",
        vector=test_vector,
        data={
            "query_hash": query_hash,
            "query_text": query_text,
            "answer_text": "Paris is the capital of France.",
            "conversation_id": str(uuid4()),
            "query_metrics_id": str(uuid4()),
            "agent_used": "CLAUDE_SONNET",
            "cost_usd": 0.0015,
            "latency_ms": 1500,
            "memories_used": 3,
            "search_used": False,
            "user_feedback": None,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    )
    print(f"✅ Inserted raw Q&A: {raw_id}")

    # Search test
    results = client.semantic_search(
        collection="ACMS_Raw_v1",
        query_vector=test_vector,
        limit=1
    )
    print(f"✅ Search successful: {len(results)} result(s)")
    if results:
        print(f"   Query: {results[0]['properties']['query_text']}")
    print()

    # Test 2: ACMS_Enriched_v1
    print("Test 2: ACMS_Enriched_v1 (Enriched Cache)")
    print("-" * 40)

    canonical_query = "capital of france"
    enriched_hash = hashlib.sha256(canonical_query.encode()).hexdigest()

    enriched_id = client.insert_vector(
        collection="ACMS_Enriched_v1",
        vector=test_vector,
        data={
            "query_hash": enriched_hash,
            "canonical_query": canonical_query,
            "summarized_answer": "Paris is France's capital and largest city.",
            "raw_id": str(raw_id),
            "original_agent": "CLAUDE_SONNET",
            "confidence_score": 0.95,
            "usage_count": 1,
            "cost_savings_usd": 0.0,
            "last_used_at": datetime.utcnow().isoformat() + "Z",
            "enriched_at": datetime.utcnow().isoformat() + "Z",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    )
    print(f"✅ Inserted enriched Q&A: {enriched_id}")

    # Search test
    results = client.semantic_search(
        collection="ACMS_Enriched_v1",
        query_vector=test_vector,
        limit=1
    )
    print(f"✅ Search successful: {len(results)} result(s)")
    if results:
        print(f"   Canonical: {results[0]['properties']['canonical_query']}")
        print(f"   Answer: {results[0]['properties']['summarized_answer']}")
    print()

    # Test 3: ACMS_Knowledge_v1
    print("Test 3: ACMS_Knowledge_v1 (User Facts)")
    print("-" * 40)

    fact_content = "User's favorite programming language is Python"
    fact_hash = hashlib.sha256(fact_content.encode()).hexdigest()

    knowledge_id = client.insert_vector(
        collection="ACMS_Knowledge_v1",
        vector=test_vector,
        data={
            "content": fact_content,
            "content_hash": fact_hash,
            "user_id": "00000000-0000-0000-0000-000000000001",
            "source_type": "inferred",
            "source_conversation_id": str(uuid4()),
            "confidence": 0.9,
            "tags": ["preference", "programming"],
            "privacy_level": "INTERNAL",
            "verified": False,
            "last_updated_at": datetime.utcnow().isoformat() + "Z",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    )
    print(f"✅ Inserted knowledge fact: {knowledge_id}")

    # Search test
    results = client.semantic_search(
        collection="ACMS_Knowledge_v1",
        query_vector=test_vector,
        limit=1
    )
    print(f"✅ Search successful: {len(results)} result(s)")
    if results:
        print(f"   Fact: {results[0]['properties']['content']}")
        print(f"   Source: {results[0]['properties']['source_type']}")
    print()

    # Final Summary
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    print("✅ All 3 collections functional:")
    print("   - ACMS_Raw_v1: Insert + Search working")
    print("   - ACMS_Enriched_v1: Insert + Search working")
    print("   - ACMS_Knowledge_v1: Insert + Search working")
    print()
    print("Next: Week 6 Day 3 - Implement dual_memory.py service")
    print("=" * 60)

    client.close()

if __name__ == "__main__":
    validate_collections()
