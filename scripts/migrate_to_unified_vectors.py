#!/usr/bin/env python3
"""
ACMS Vector Migration Script
=============================

Migrates from fragmented 768-dim collections to unified 1536-dim architecture.

Before:
- ACMS_MemoryItems_v1 (768d, 1 object - broken)
- ACMS_Raw_v1 (768d, 1 object)
- ACMS_Knowledge_v1 (768d, 1 object)
- ACMS_Enriched_v1 (768d, unused)
- QueryCache_v1 (768d, disabled)

After:
- ACMS_Raw_v1 (1536d) - All Q&A pairs from memory_items + query_history
- ACMS_Knowledge_v1 (1536d) - Extracted facts only

Usage:
    PYTHONPATH=. python3 scripts/migrate_to_unified_vectors.py

This script will:
1. Delete all existing Weaviate collections
2. Create new schema with 1536 dimensions
3. Clear Redis embedding cache
4. Re-embed and migrate memory_items (97K) to ACMS_Raw_v1
5. Re-embed and migrate query_history (3.9K) to ACMS_Raw_v1
6. Verify migration
"""

import os
import sys
import json
import asyncio
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

import asyncpg
import requests
import redis

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:40480")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:40379")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "40432"))
PG_USER = os.getenv("PG_USER", "acms")
PG_PASSWORD = os.getenv("PG_PASSWORD", "acms_password")
PG_DATABASE = os.getenv("PG_DATABASE", "acms")

# New embedding dimensions
EMBEDDING_DIMENSIONS = 1536

# Batch size for processing
BATCH_SIZE = 100


class WeaviateManager:
    """Manage Weaviate collections."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def delete_all_collections(self) -> List[str]:
        """Delete all existing collections."""
        deleted = []

        # Get existing classes
        response = requests.get(f"{self.base_url}/v1/schema")
        if response.status_code != 200:
            raise Exception(f"Failed to get schema: {response.text}")

        classes = response.json().get("classes", [])

        for cls in classes:
            class_name = cls["class"]
            logger.info(f"Deleting collection: {class_name}")

            response = requests.delete(f"{self.base_url}/v1/schema/{class_name}")
            if response.status_code in [200, 204]:
                deleted.append(class_name)
                logger.info(f"  ✓ Deleted {class_name}")
            else:
                logger.warning(f"  ✗ Failed to delete {class_name}: {response.text}")

        return deleted

    def create_collection(self, class_name: str, properties: List[Dict], description: str = ""):
        """Create a new collection with 1536-dim vectors."""
        schema = {
            "class": class_name,
            "description": description,
            "vectorizer": "none",  # We provide our own vectors
            "vectorIndexConfig": {
                "distance": "cosine"
            },
            "properties": properties
        }

        response = requests.post(
            f"{self.base_url}/v1/schema",
            json=schema
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create {class_name}: {response.text}")

        logger.info(f"✓ Created collection: {class_name} ({EMBEDDING_DIMENSIONS}d)")

    def insert_object(self, class_name: str, properties: Dict, vector: List[float]) -> str:
        """Insert an object with vector."""
        object_id = str(uuid4())

        data = {
            "class": class_name,
            "id": object_id,
            "properties": properties,
            "vector": vector
        }

        response = requests.post(
            f"{self.base_url}/v1/objects",
            json=data
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to insert object: {response.text}")

        return object_id

    def batch_insert(self, class_name: str, objects: List[Dict]) -> int:
        """Batch insert objects with vectors."""
        if not objects:
            return 0

        batch_data = {
            "objects": [
                {
                    "class": class_name,
                    "id": str(uuid4()),
                    "properties": obj["properties"],
                    "vector": obj["vector"]
                }
                for obj in objects
            ]
        }

        response = requests.post(
            f"{self.base_url}/v1/batch/objects",
            json=batch_data
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Batch insert failed: {response.text}")

        return len(objects)

    def get_count(self, class_name: str) -> int:
        """Get object count for a collection."""
        response = requests.get(
            f"{self.base_url}/v1/objects?limit=1&class={class_name}"
        )
        if response.status_code == 200:
            return response.json().get("totalResults", 0)
        return 0


class EmbeddingGenerator:
    """Generate embeddings using OpenAI."""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "text-embedding-3-small"
        self.dimensions = EMBEDDING_DIMENSIONS
        self._count = 0

    def generate(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.dimensions

        # Truncate if needed
        if len(text) > 32000:
            text = text[:32000]

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions
            )
            self._count += 1
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return [0.0] * self.dimensions

    @property
    def count(self) -> int:
        return self._count


def clear_redis_cache():
    """Clear old embedding cache from Redis."""
    try:
        r = redis.from_url(REDIS_URL)

        # Find and delete all embedding cache keys
        cursor = 0
        deleted = 0

        while True:
            cursor, keys = r.scan(cursor, match="emb:*", count=1000)
            if keys:
                r.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break

        logger.info(f"✓ Cleared {deleted} embedding cache entries from Redis")
        return deleted
    except Exception as e:
        logger.warning(f"Redis cache clear failed: {e}")
        return 0


async def migrate_memory_items(
    pg_conn: asyncpg.Connection,
    weaviate: WeaviateManager,
    embeddings: EmbeddingGenerator
) -> int:
    """Migrate memory_items table to ACMS_Raw_v1."""

    # Count total
    total = await pg_conn.fetchval("SELECT COUNT(*) FROM memory_items")
    logger.info(f"Migrating {total} memory_items to ACMS_Raw_v1...")

    migrated = 0
    offset = 0

    while offset < total:
        # Fetch batch
        rows = await pg_conn.fetch("""
            SELECT
                memory_id, user_id, content, tier, tags,
                privacy_level, created_at, metadata_json
            FROM memory_items
            ORDER BY created_at
            LIMIT $1 OFFSET $2
        """, BATCH_SIZE, offset)

        if not rows:
            break

        batch_objects = []

        for row in rows:
            content = row['content'] or ""

            # Generate new 1536-dim embedding
            vector = embeddings.generate(content)

            # Prepare properties for Weaviate
            properties = {
                "content": content[:10000],  # Truncate for Weaviate
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                "user_id": str(row['user_id']),
                "source_type": "chrome_extension",
                "source_id": str(row['memory_id']),
                "privacy_level": row['privacy_level'] or "PUBLIC",
                "tags": row['tags'] or [],
                "created_at": row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat()
            }

            batch_objects.append({
                "properties": properties,
                "vector": vector
            })

        # Batch insert to Weaviate
        try:
            weaviate.batch_insert("ACMS_Raw_v1", batch_objects)
            migrated += len(batch_objects)
        except Exception as e:
            logger.error(f"Batch insert failed at offset {offset}: {e}")

        offset += BATCH_SIZE

        # Progress update
        if migrated % 1000 == 0 or migrated == total:
            pct = (migrated / total) * 100
            logger.info(f"  Progress: {migrated}/{total} ({pct:.1f}%) - {embeddings.count} embeddings generated")

    return migrated


async def migrate_query_history(
    pg_conn: asyncpg.Connection,
    weaviate: WeaviateManager,
    embeddings: EmbeddingGenerator
) -> int:
    """Migrate query_history table to ACMS_Raw_v1."""

    # Count total
    total = await pg_conn.fetchval("SELECT COUNT(*) FROM query_history")
    logger.info(f"Migrating {total} query_history to ACMS_Raw_v1...")

    migrated = 0
    offset = 0

    while offset < total:
        # Fetch batch
        rows = await pg_conn.fetch("""
            SELECT
                query_id, user_id, question, answer,
                response_source, created_at, est_cost_usd,
                data_source
            FROM query_history
            ORDER BY created_at
            LIMIT $1 OFFSET $2
        """, BATCH_SIZE, offset)

        if not rows:
            break

        batch_objects = []

        for row in rows:
            question = row['question'] or ""
            answer = row['answer'] or ""

            # Combine Q&A for embedding
            content = f"Q: {question}\nA: {answer}" if answer else question

            # Generate new 1536-dim embedding
            vector = embeddings.generate(content)

            # Determine source type
            data_source = row['data_source'] or ""
            if "chatgpt" in data_source.lower():
                source_type = "chatgpt_import"
            elif "claude" in data_source.lower():
                source_type = "claude_import"
            else:
                source_type = "desktop_chat"

            # Prepare properties for Weaviate
            properties = {
                "content": content[:10000],  # Truncate for Weaviate
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                "user_id": str(row['user_id']),
                "source_type": source_type,
                "source_id": str(row['query_id']),
                "agent": row['response_source'] or "unknown",
                "cost_usd": float(row['est_cost_usd']) if row['est_cost_usd'] else 0.0,
                "created_at": row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat()
            }

            batch_objects.append({
                "properties": properties,
                "vector": vector
            })

        # Batch insert to Weaviate
        try:
            weaviate.batch_insert("ACMS_Raw_v1", batch_objects)
            migrated += len(batch_objects)
        except Exception as e:
            logger.error(f"Batch insert failed at offset {offset}: {e}")

        offset += BATCH_SIZE

        # Progress update
        if migrated % 500 == 0 or migrated == total:
            pct = (migrated / total) * 100
            logger.info(f"  Progress: {migrated}/{total} ({pct:.1f}%) - {embeddings.count} embeddings generated")

    return migrated


async def main():
    """Run the migration."""
    logger.info("=" * 60)
    logger.info("ACMS Vector Migration: 768d → 1536d, Unified Collections")
    logger.info("=" * 60)

    # Initialize clients
    weaviate = WeaviateManager(WEAVIATE_URL)
    embeddings = EmbeddingGenerator()

    # Step 1: Delete all existing collections
    logger.info("\n[Step 1] Deleting existing Weaviate collections...")
    deleted = weaviate.delete_all_collections()
    logger.info(f"Deleted {len(deleted)} collections: {deleted}")

    # Step 2: Create new schema with 1536 dimensions
    logger.info("\n[Step 2] Creating new Weaviate schema (1536d)...")

    # ACMS_Raw_v1 - All Q&A pairs
    raw_properties = [
        {"name": "content", "dataType": ["text"], "description": "Q&A content"},
        {"name": "content_hash", "dataType": ["text"], "description": "Content hash for dedup"},
        {"name": "user_id", "dataType": ["text"], "description": "User ID"},
        {"name": "source_type", "dataType": ["text"], "description": "chrome_extension, chatgpt_import, claude_import, desktop_chat"},
        {"name": "source_id", "dataType": ["text"], "description": "Original record ID"},
        {"name": "agent", "dataType": ["text"], "description": "LLM agent used"},
        {"name": "privacy_level", "dataType": ["text"], "description": "Privacy level"},
        {"name": "tags", "dataType": ["text[]"], "description": "Tags"},
        {"name": "cost_usd", "dataType": ["number"], "description": "Cost in USD"},
        {"name": "created_at", "dataType": ["text"], "description": "Created timestamp"},
    ]
    weaviate.create_collection(
        "ACMS_Raw_v1",
        raw_properties,
        "All Q&A pairs from all sources (1536d embeddings)"
    )

    # ACMS_Knowledge_v1 - Extracted facts
    knowledge_properties = [
        {"name": "content", "dataType": ["text"], "description": "Extracted fact"},
        {"name": "content_hash", "dataType": ["text"], "description": "Content hash for dedup"},
        {"name": "user_id", "dataType": ["text"], "description": "User ID"},
        {"name": "source_type", "dataType": ["text"], "description": "Source of fact"},
        {"name": "source_id", "dataType": ["text"], "description": "Source record ID"},
        {"name": "verified", "dataType": ["boolean"], "description": "Verified by user"},
        {"name": "created_at", "dataType": ["text"], "description": "Created timestamp"},
    ]
    weaviate.create_collection(
        "ACMS_Knowledge_v1",
        knowledge_properties,
        "Extracted knowledge facts (1536d embeddings)"
    )

    # Step 3: Clear Redis embedding cache
    logger.info("\n[Step 3] Clearing Redis embedding cache...")
    clear_redis_cache()

    # Step 4 & 5: Migrate data
    logger.info("\n[Step 4] Connecting to PostgreSQL...")
    pg_conn = await asyncpg.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DATABASE
    )

    logger.info("\n[Step 5] Migrating memory_items...")
    memory_count = await migrate_memory_items(pg_conn, weaviate, embeddings)

    logger.info("\n[Step 6] Migrating query_history...")
    query_count = await migrate_query_history(pg_conn, weaviate, embeddings)

    await pg_conn.close()

    # Step 7: Verify migration
    logger.info("\n[Step 7] Verifying migration...")
    raw_count = weaviate.get_count("ACMS_Raw_v1")
    knowledge_count = weaviate.get_count("ACMS_Knowledge_v1")

    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"ACMS_Raw_v1: {raw_count} objects (from {memory_count} memories + {query_count} queries)")
    logger.info(f"ACMS_Knowledge_v1: {knowledge_count} objects")
    logger.info(f"Total embeddings generated: {embeddings.count}")
    logger.info(f"Embedding dimensions: {EMBEDDING_DIMENSIONS}")
    logger.info("=" * 60)

    return raw_count, knowledge_count


if __name__ == "__main__":
    asyncio.run(main())
