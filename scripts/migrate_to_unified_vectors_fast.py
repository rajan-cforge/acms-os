#!/usr/bin/env python3
"""
ACMS Vector Migration Script - FAST VERSION
============================================

Uses OpenAI batch embeddings (up to 2048 texts at once) for 50x speedup.

Usage:
    PYTHONPATH=. python3 scripts/migrate_to_unified_vectors_fast.py
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
from openai import OpenAI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress OpenAI HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)

# Configuration
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:40480")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:40379")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "40432"))
PG_USER = os.getenv("PG_USER", "acms")
PG_PASSWORD = os.getenv("PG_PASSWORD", "acms_password")
PG_DATABASE = os.getenv("PG_DATABASE", "acms")

EMBEDDING_DIMENSIONS = 1536
EMBEDDING_BATCH_SIZE = 100  # Reduced from 500 to stay under 300K token limit
WEAVIATE_BATCH_SIZE = 100
MAX_TEXT_CHARS = 2000  # ~500 tokens per text, 100 texts = ~50K tokens (safely under 300K)


class BatchEmbeddings:
    """Generate embeddings in batches using OpenAI."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "text-embedding-3-small"
        self.dimensions = EMBEDDING_DIMENSIONS
        self._count = 0

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if not texts:
            return []

        # Clean and truncate texts to stay under token limits
        # MAX_TEXT_CHARS (2000) * BATCH_SIZE (100) = ~50K tokens (well under 300K limit)
        cleaned = []
        for text in texts:
            if not text or not text.strip():
                cleaned.append("empty")  # Placeholder for empty texts
            elif len(text) > MAX_TEXT_CHARS:
                cleaned.append(text[:MAX_TEXT_CHARS])
            else:
                cleaned.append(text)

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=cleaned,
                dimensions=self.dimensions
            )
            self._count += len(cleaned)

            # Extract embeddings in order
            embeddings = [None] * len(cleaned)
            for item in response.data:
                embeddings[item.index] = item.embedding

            return embeddings
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # Return zero vectors as fallback
            return [[0.0] * self.dimensions for _ in texts]

    @property
    def count(self) -> int:
        return self._count


class WeaviateManager:
    """Manage Weaviate collections."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def delete_all_collections(self) -> List[str]:
        """Delete all existing collections."""
        deleted = []
        response = requests.get(f"{self.base_url}/v1/schema")
        if response.status_code != 200:
            return deleted

        for cls in response.json().get("classes", []):
            class_name = cls["class"]
            resp = requests.delete(f"{self.base_url}/v1/schema/{class_name}")
            if resp.status_code in [200, 204]:
                deleted.append(class_name)
                logger.info(f"  ✓ Deleted {class_name}")

        return deleted

    def create_raw_collection(self):
        """Create ACMS_Raw_v1 collection."""
        schema = {
            "class": "ACMS_Raw_v1",
            "description": "All Q&A pairs from all sources (1536d embeddings)",
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"},
            "properties": [
                {"name": "content", "dataType": ["text"]},
                {"name": "content_hash", "dataType": ["text"]},
                {"name": "user_id", "dataType": ["text"]},
                {"name": "source_type", "dataType": ["text"]},
                {"name": "source_id", "dataType": ["text"]},
                {"name": "agent", "dataType": ["text"]},
                {"name": "privacy_level", "dataType": ["text"]},
                {"name": "tags", "dataType": ["text[]"]},
                {"name": "cost_usd", "dataType": ["number"]},
                {"name": "created_at", "dataType": ["text"]},
            ]
        }
        response = requests.post(f"{self.base_url}/v1/schema", json=schema)
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create ACMS_Raw_v1: {response.text}")
        logger.info(f"✓ Created ACMS_Raw_v1 ({EMBEDDING_DIMENSIONS}d)")

    def create_knowledge_collection(self):
        """Create ACMS_Knowledge_v1 collection."""
        schema = {
            "class": "ACMS_Knowledge_v1",
            "description": "Extracted knowledge facts (1536d embeddings)",
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"},
            "properties": [
                {"name": "content", "dataType": ["text"]},
                {"name": "content_hash", "dataType": ["text"]},
                {"name": "user_id", "dataType": ["text"]},
                {"name": "source_type", "dataType": ["text"]},
                {"name": "source_id", "dataType": ["text"]},
                {"name": "verified", "dataType": ["boolean"]},
                {"name": "created_at", "dataType": ["text"]},
            ]
        }
        response = requests.post(f"{self.base_url}/v1/schema", json=schema)
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create ACMS_Knowledge_v1: {response.text}")
        logger.info(f"✓ Created ACMS_Knowledge_v1 ({EMBEDDING_DIMENSIONS}d)")

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

        response = requests.post(f"{self.base_url}/v1/batch/objects", json=batch_data)
        if response.status_code not in [200, 201]:
            logger.error(f"Batch insert failed: {response.text[:200]}")
            return 0

        return len(objects)

    def get_count(self, class_name: str) -> int:
        """Get object count for a collection using GraphQL aggregate."""
        query = {
            "query": f"""{{
                Aggregate {{
                    {class_name} {{
                        meta {{
                            count
                        }}
                    }}
                }}
            }}"""
        }
        response = requests.post(f"{self.base_url}/v1/graphql", json=query)
        if response.status_code == 200:
            try:
                data = response.json()
                return data["data"]["Aggregate"][class_name][0]["meta"]["count"]
            except (KeyError, IndexError, TypeError):
                return 0
        return 0


def clear_redis_cache():
    """Clear old embedding cache from Redis."""
    try:
        import redis as redis_lib
        r = redis_lib.from_url(REDIS_URL)
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


async def migrate_memory_items(pg_conn, weaviate: WeaviateManager, embeddings: BatchEmbeddings) -> int:
    """Migrate memory_items table to ACMS_Raw_v1 using batch embeddings."""

    total = await pg_conn.fetchval("SELECT COUNT(*) FROM memory_items")
    logger.info(f"Migrating {total} memory_items to ACMS_Raw_v1...")

    migrated = 0
    offset = 0

    while offset < total:
        # Fetch a large batch for embedding
        rows = await pg_conn.fetch("""
            SELECT memory_id, user_id, content, tier, tags,
                   privacy_level, created_at, metadata_json
            FROM memory_items
            ORDER BY created_at
            LIMIT $1 OFFSET $2
        """, EMBEDDING_BATCH_SIZE, offset)

        if not rows:
            break

        # Prepare texts for batch embedding
        texts = [row['content'] or "" for row in rows]

        # Generate embeddings in ONE API call
        vectors = embeddings.generate_batch(texts)

        # Prepare objects for Weaviate
        objects = []
        for i, row in enumerate(rows):
            content = row['content'] or ""
            objects.append({
                "properties": {
                    "content": content[:MAX_TEXT_CHARS],  # Match embedding truncation
                    "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                    "user_id": str(row['user_id']),
                    "source_type": "chrome_extension",
                    "source_id": str(row['memory_id']),
                    "privacy_level": row['privacy_level'] or "PUBLIC",
                    "tags": row['tags'] or [],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat()
                },
                "vector": vectors[i]
            })

        # Insert to Weaviate in smaller batches
        for i in range(0, len(objects), WEAVIATE_BATCH_SIZE):
            batch = objects[i:i+WEAVIATE_BATCH_SIZE]
            inserted = weaviate.batch_insert("ACMS_Raw_v1", batch)
            migrated += inserted

        offset += EMBEDDING_BATCH_SIZE

        # Progress
        pct = (migrated / total) * 100
        logger.info(f"  memory_items: {migrated}/{total} ({pct:.1f}%) - {embeddings.count} embeddings")

    return migrated


async def migrate_query_history(pg_conn, weaviate: WeaviateManager, embeddings: BatchEmbeddings) -> int:
    """Migrate query_history table to ACMS_Raw_v1 using batch embeddings."""

    total = await pg_conn.fetchval("SELECT COUNT(*) FROM query_history")
    logger.info(f"Migrating {total} query_history to ACMS_Raw_v1...")

    migrated = 0
    offset = 0

    while offset < total:
        rows = await pg_conn.fetch("""
            SELECT query_id, user_id, question, answer,
                   response_source, created_at, est_cost_usd, data_source
            FROM query_history
            ORDER BY created_at
            LIMIT $1 OFFSET $2
        """, EMBEDDING_BATCH_SIZE, offset)

        if not rows:
            break

        # Prepare texts
        texts = []
        for row in rows:
            q = row['question'] or ""
            a = row['answer'] or ""
            texts.append(f"Q: {q}\nA: {a}" if a else q)

        # Batch embedding
        vectors = embeddings.generate_batch(texts)

        # Prepare objects
        objects = []
        for i, row in enumerate(rows):
            content = texts[i]
            data_source = row['data_source'] or ""

            if "chatgpt" in data_source.lower():
                source_type = "chatgpt_import"
            elif "claude" in data_source.lower():
                source_type = "claude_import"
            else:
                source_type = "desktop_chat"

            objects.append({
                "properties": {
                    "content": content[:MAX_TEXT_CHARS],  # Match embedding truncation
                    "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                    "user_id": str(row['user_id']),
                    "source_type": source_type,
                    "source_id": str(row['query_id']),
                    "agent": row['response_source'] or "unknown",
                    "cost_usd": float(row['est_cost_usd']) if row['est_cost_usd'] else 0.0,
                    "created_at": row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat()
                },
                "vector": vectors[i]
            })

        # Insert to Weaviate
        for i in range(0, len(objects), WEAVIATE_BATCH_SIZE):
            batch = objects[i:i+WEAVIATE_BATCH_SIZE]
            inserted = weaviate.batch_insert("ACMS_Raw_v1", batch)
            migrated += inserted

        offset += EMBEDDING_BATCH_SIZE

        pct = (migrated / total) * 100
        logger.info(f"  query_history: {migrated}/{total} ({pct:.1f}%)")

    return migrated


async def main():
    """Run the fast migration."""
    logger.info("=" * 60)
    logger.info("ACMS Vector Migration - FAST (Batch Embeddings)")
    logger.info("=" * 60)

    weaviate = WeaviateManager(WEAVIATE_URL)
    embeddings = BatchEmbeddings()

    # Step 1: Delete old collections
    logger.info("\n[Step 1] Deleting existing collections...")
    deleted = weaviate.delete_all_collections()
    logger.info(f"Deleted {len(deleted)} collections")

    # Step 2: Create new schema
    logger.info("\n[Step 2] Creating new schema (1536d)...")
    weaviate.create_raw_collection()
    weaviate.create_knowledge_collection()

    # Step 3: Clear Redis cache
    logger.info("\n[Step 3] Clearing Redis cache...")
    clear_redis_cache()

    # Step 4: Connect to PostgreSQL
    logger.info("\n[Step 4] Connecting to PostgreSQL...")
    pg_conn = await asyncpg.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD, database=PG_DATABASE
    )

    # Step 5: Migrate data
    logger.info("\n[Step 5] Migrating data with batch embeddings...")
    memory_count = await migrate_memory_items(pg_conn, weaviate, embeddings)
    query_count = await migrate_query_history(pg_conn, weaviate, embeddings)

    await pg_conn.close()

    # Step 6: Verify
    logger.info("\n[Step 6] Verifying...")
    raw_count = weaviate.get_count("ACMS_Raw_v1")
    knowledge_count = weaviate.get_count("ACMS_Knowledge_v1")

    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"ACMS_Raw_v1: {raw_count} objects")
    logger.info(f"ACMS_Knowledge_v1: {knowledge_count} objects")
    logger.info(f"Total embeddings: {embeddings.count}")
    logger.info(f"Dimensions: {EMBEDDING_DIMENSIONS}")
    logger.info("=" * 60)

    return raw_count, knowledge_count


if __name__ == "__main__":
    asyncio.run(main())
