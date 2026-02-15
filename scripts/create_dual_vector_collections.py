#!/usr/bin/env python3
"""
Week 6 Day 2: Create Dual Vector DB Collections

Creates 3 Weaviate collections for dual vector DB architecture:
1. ACMS_Raw_v1 - Raw Q&A pairs (30-day retention)
2. ACMS_Enriched_v1 - Enriched cache (permanent, replaces semantic_cache.py)
3. ACMS_Knowledge_v1 - User facts and preferences (permanent)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import weaviate
from weaviate.classes.config import Property, DataType, Configure, VectorDistances
from datetime import datetime

def create_collections():
    """Create the 3 dual vector DB collections."""

    # Connect to Weaviate using environment variables (Docker-aware)
    # Inside container: weaviate:8080, Outside: localhost:40480
    host = os.getenv("WEAVIATE_HOST", "localhost")
    port = int(os.getenv("WEAVIATE_PORT", "40480"))
    grpc_port = int(os.getenv("WEAVIATE_GRPC_PORT", "40481"))

    print(f"Connecting to Weaviate at {host}:{port}...")
    client = weaviate.connect_to_local(
        host=host,
        port=port,
        grpc_port=grpc_port
    )

    try:
        print(f"✅ Connected to Weaviate v{client.get_meta()['version']}")
        print()

        # ============================================================
        # Collection 1: ACMS_Raw_v1 (Raw Q&A, 30-day retention)
        # ============================================================
        print("Creating ACMS_Raw_v1 collection...")

        if client.collections.exists("ACMS_Raw_v1"):
            print("  Collection already exists, deleting...")
            client.collections.delete("ACMS_Raw_v1")

        client.collections.create(
            name="ACMS_Raw_v1",
            description="Raw Q&A pairs with 30-day retention (SHORT tier)",
            vectorizer_config=None,  # Manual vectors from OpenAI
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
                ef=128,
                ef_construction=256,
                max_connections=64
            ),
            properties=[
                Property(name="query_hash", data_type=DataType.TEXT, description="SHA256 hash of query_text for deduplication"),
                Property(name="query_text", data_type=DataType.TEXT, description="Original user query"),
                Property(name="query_embedding", data_type=DataType.NUMBER_ARRAY, description="Vector embedding of query"),
                Property(name="answer_text", data_type=DataType.TEXT, description="Original AI response"),
                Property(name="conversation_id", data_type=DataType.UUID, description="Link to conversations table"),
                Property(name="query_metrics_id", data_type=DataType.UUID, description="Link to query_metrics table"),
                Property(name="agent_used", data_type=DataType.TEXT, description="AI agent that generated response"),
                Property(name="cost_usd", data_type=DataType.NUMBER, description="Cost to generate this Q&A"),
                Property(name="latency_ms", data_type=DataType.INT, description="Response time in milliseconds"),
                Property(name="memories_used", data_type=DataType.INT, description="Number of memories used"),
                Property(name="search_used", data_type=DataType.BOOL, description="Whether web search was used"),
                Property(name="user_feedback", data_type=DataType.TEXT, description="thumbs_up, thumbs_down, regenerate, null"),
                Property(name="created_at", data_type=DataType.DATE, description="Timestamp for 30-day TTL"),
            ]
        )
        print("✅ ACMS_Raw_v1 created (30-day retention)")
        print()

        # ============================================================
        # Collection 2: ACMS_Enriched_v1 (Enriched Cache, permanent)
        # ============================================================
        print("Creating ACMS_Enriched_v1 collection...")

        if client.collections.exists("ACMS_Enriched_v1"):
            print("  Collection already exists, deleting...")
            client.collections.delete("ACMS_Enriched_v1")

        client.collections.create(
            name="ACMS_Enriched_v1",
            description="Enriched Q&A cache (LONG tier, replaces semantic_cache.py)",
            vectorizer_config=None,  # Manual vectors from OpenAI
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
                ef=128,
                ef_construction=256,
                max_connections=64
            ),
            properties=[
                Property(name="query_hash", data_type=DataType.TEXT, description="SHA256 hash for deduplication"),
                Property(name="canonical_query", data_type=DataType.TEXT, description="Rewritten query (canonical form)"),
                Property(name="query_embedding", data_type=DataType.NUMBER_ARRAY, description="Vector of canonical_query"),
                Property(name="summarized_answer", data_type=DataType.TEXT, description="Compressed, factual summary"),
                Property(name="raw_id", data_type=DataType.UUID, description="Link to ACMS_Raw_v1"),
                Property(name="original_agent", data_type=DataType.TEXT, description="Original AI agent used"),
                Property(name="confidence_score", data_type=DataType.NUMBER, description="Quality score (0.0-1.0)"),
                Property(name="usage_count", data_type=DataType.INT, description="Cache hit counter"),
                Property(name="cost_savings_usd", data_type=DataType.NUMBER, description="Cumulative savings from cache hits"),
                Property(name="last_used_at", data_type=DataType.DATE, description="Most recent cache hit"),
                Property(name="enriched_at", data_type=DataType.DATE, description="When enrichment completed"),
                Property(name="created_at", data_type=DataType.DATE, description="Original creation timestamp"),
            ]
        )
        print("✅ ACMS_Enriched_v1 created (permanent, replaces semantic_cache.py)")
        print()

        # ============================================================
        # Collection 3: ACMS_Knowledge_v1 (User Facts, permanent)
        # ============================================================
        print("Creating ACMS_Knowledge_v1 collection...")

        if client.collections.exists("ACMS_Knowledge_v1"):
            print("  Collection already exists, deleting...")
            client.collections.delete("ACMS_Knowledge_v1")

        client.collections.create(
            name="ACMS_Knowledge_v1",
            description="User facts, preferences, and extracted knowledge (LONG tier)",
            vectorizer_config=None,  # Manual vectors from OpenAI
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
                ef=128,
                ef_construction=256,
                max_connections=64
            ),
            properties=[
                Property(name="content", data_type=DataType.TEXT, description="Knowledge fact or preference"),
                Property(name="content_hash", data_type=DataType.TEXT, description="SHA256 hash for deduplication"),
                Property(name="user_id", data_type=DataType.UUID, description="Link to users table"),
                Property(name="source_type", data_type=DataType.TEXT, description="extracted, user_stated, inferred"),
                Property(name="source_conversation_id", data_type=DataType.UUID, description="Where this knowledge came from"),
                Property(name="confidence", data_type=DataType.NUMBER, description="Confidence score (0.0-1.0)"),
                Property(name="tags", data_type=DataType.TEXT_ARRAY, description="Categories for filtering"),
                Property(name="privacy_level", data_type=DataType.TEXT, description="PUBLIC, INTERNAL, CONFIDENTIAL, LOCAL_ONLY"),
                Property(name="verified", data_type=DataType.BOOL, description="User-confirmed accuracy"),
                Property(name="last_updated_at", data_type=DataType.DATE, description="Last modification"),
                Property(name="created_at", data_type=DataType.DATE, description="Creation timestamp"),
            ]
        )
        print("✅ ACMS_Knowledge_v1 created (permanent user facts)")
        print()

        # ============================================================
        # Validation: List all collections
        # ============================================================
        print("=" * 60)
        print("VALIDATION: All Collections")
        print("=" * 60)

        collections = client.collections.list_all()
        for name, config in collections.items():
            if name.startswith("ACMS_"):
                props = config.properties
                print(f"✅ {name}: {len(props)} properties")
                print(f"   Description: {config.description}")

        print()
        print("=" * 60)
        print("Week 6 Day 2: COMPLETE")
        print("=" * 60)
        print("Next: Day 3 - Implement dual_memory.py service")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        client.close()

if __name__ == "__main__":
    create_collections()
