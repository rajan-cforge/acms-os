#!/usr/bin/env python3
"""Batch extract knowledge from existing query_history records.

This script processes historical Q&A pairs and extracts:
- Intent analysis (the "why")
- Entities and relationships
- Topic clusters
- Key facts

Stores results to ACMS_Knowledge_v2.

Usage:
    # Process all records for default user
    PYTHONPATH=. python3 scripts/batch_extract_knowledge.py

    # Process specific user
    PYTHONPATH=. python3 scripts/batch_extract_knowledge.py --user-id <uuid>

    # Limit records (for testing)
    PYTHONPATH=. python3 scripts/batch_extract_knowledge.py --limit 100

    # Resume from specific offset
    PYTHONPATH=. python3 scripts/batch_extract_knowledge.py --offset 5000

    # Dry run (don't store, just extract)
    PYTHONPATH=. python3 scripts/batch_extract_knowledge.py --dry-run

Cost Estimate:
    - ~101K records
    - ~$0.004 per extraction (Claude Sonnet 4)
    - Total: ~$405 for full backfill
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def batch_extract_knowledge(
    user_id: Optional[str] = None,
    limit: int = 0,
    offset: int = 0,
    batch_size: int = 10,
    dry_run: bool = False,
    skip_existing: bool = True
):
    """Extract knowledge from query_history records.

    Args:
        user_id: Filter by user ID (None = all users)
        limit: Maximum records to process (0 = no limit)
        offset: Skip first N records
        batch_size: Records per batch
        dry_run: Extract but don't store
        skip_existing: Skip records already in ACMS_Knowledge_v2
    """
    from sqlalchemy import text
    from src.storage.database import get_session
    from src.intelligence.knowledge_extractor import get_knowledge_extractor
    from src.storage.weaviate_client import WeaviateClient
    from src.embeddings.openai_embeddings import OpenAIEmbeddings
    import json

    logger.info("=" * 60)
    logger.info("ACMS Knowledge Batch Extraction")
    logger.info("=" * 60)
    logger.info(f"User filter: {user_id or 'ALL USERS'}")
    logger.info(f"Limit: {limit or 'UNLIMITED'}")
    logger.info(f"Offset: {offset}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Skip existing: {skip_existing}")
    logger.info("=" * 60)

    # Initialize components
    extractor = get_knowledge_extractor()
    weaviate = WeaviateClient()
    embeddings = OpenAIEmbeddings()

    # Stats tracking
    stats = {
        "total_queried": 0,
        "processed": 0,
        "stored": 0,
        "skipped_existing": 0,
        "skipped_short": 0,
        "errors": 0,
        "total_cost_usd": 0.0,
        "start_time": datetime.now()
    }

    async with get_session() as session:
        # Build query
        query_parts = ["SELECT query_id, user_id, question, answer FROM query_history"]
        conditions = ["answer IS NOT NULL", "LENGTH(answer) > 100"]

        if user_id:
            conditions.append("user_id = :user_id")

        query_parts.append("WHERE " + " AND ".join(conditions))
        query_parts.append("ORDER BY created_at DESC")

        if limit > 0:
            query_parts.append(f"LIMIT {limit}")
        if offset > 0:
            query_parts.append(f"OFFSET {offset}")

        query = " ".join(query_parts)
        params = {"user_id": user_id} if user_id else {}

        # Count total records
        count_query = f"SELECT COUNT(*) FROM query_history WHERE {' AND '.join(conditions)}"
        count_result = await session.execute(text(count_query), params)
        total_count = count_result.scalar()
        logger.info(f"Total records matching criteria: {total_count}")

        # Fetch records
        result = await session.execute(text(query), params)
        records = result.fetchall()
        stats["total_queried"] = len(records)
        logger.info(f"Fetched {len(records)} records to process")

        # Process in batches
        for i, record in enumerate(records):
            query_id = str(record.query_id)
            record_user_id = str(record.user_id)
            question = record.question
            answer = record.answer

            try:
                # Check if already extracted (optional)
                if skip_existing:
                    existing = weaviate.semantic_search(
                        collection="ACMS_Knowledge_v2",
                        query_vector=embeddings.generate_embedding(question[:500]),
                        limit=1,
                        filters={"user_id": record_user_id}
                    )
                    if existing and len(existing) > 0:
                        # Check if it's a close match
                        if existing[0].get("distance", 1.0) < 0.05:
                            stats["skipped_existing"] += 1
                            if i % 100 == 0:
                                logger.info(f"[{i+1}/{len(records)}] Skipped (already extracted): {question[:50]}...")
                            continue

                # Skip very short answers
                if len(answer) < 100:
                    stats["skipped_short"] += 1
                    continue

                # Extract knowledge
                logger.info(f"[{i+1}/{len(records)}] Extracting: {question[:60]}...")

                knowledge_entry = await extractor.extract(
                    query=question,
                    answer=answer,
                    user_id=record_user_id,
                    source_query_id=query_id
                )

                # Estimate cost (~$0.004 per extraction)
                stats["total_cost_usd"] += 0.004
                stats["processed"] += 1

                if not dry_run:
                    # Generate embedding
                    embedding = embeddings.generate_embedding(knowledge_entry.canonical_query[:8000])

                    # Prepare properties
                    entities_json = json.dumps([
                        {"name": e.name, "canonical": e.canonical, "type": e.entity_type, "importance": e.importance}
                        for e in knowledge_entry.entities
                    ])
                    relations_json = json.dumps([
                        {"from": r.from_entity, "to": r.to_entity, "type": r.relation_type}
                        for r in knowledge_entry.relations
                    ])

                    properties = {
                        "canonical_query": knowledge_entry.canonical_query,
                        "answer_summary": knowledge_entry.answer_summary,
                        "full_answer": knowledge_entry.full_answer[:50000],
                        "primary_intent": knowledge_entry.intent.primary_intent,
                        "problem_domain": knowledge_entry.intent.problem_domain,
                        "why_context": knowledge_entry.intent.why_context,
                        "user_context_signals": knowledge_entry.intent.user_context_signals,
                        "entities_json": entities_json,
                        "relations_json": relations_json,
                        "topic_cluster": knowledge_entry.topic_cluster,
                        "related_topics": knowledge_entry.related_topics,
                        "key_facts": knowledge_entry.key_facts,
                        "user_id": record_user_id,
                        "source_query_id": query_id,
                        "extraction_model": knowledge_entry.extraction_model,
                        "extraction_confidence": knowledge_entry.extraction_confidence,
                        "created_at": knowledge_entry.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "usage_count": 0,
                        "feedback_score": 0.0
                    }

                    # Store to Weaviate
                    weaviate_id = weaviate.insert_vector(
                        collection="ACMS_Knowledge_v2",
                        vector=embedding,
                        data=properties
                    )
                    stats["stored"] += 1
                    logger.info(f"  → Stored: {weaviate_id[:8]}... topic={knowledge_entry.topic_cluster}")

                # Progress update every 50 records
                if (i + 1) % 50 == 0:
                    elapsed = (datetime.now() - stats["start_time"]).total_seconds()
                    rate = stats["processed"] / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {i+1}/{len(records)} | Processed: {stats['processed']} | "
                               f"Rate: {rate:.1f}/s | Cost: ${stats['total_cost_usd']:.2f}")

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"  ERROR processing {query_id}: {e}")
                continue

            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)

    # Final summary
    elapsed = (datetime.now() - stats["start_time"]).total_seconds()
    logger.info("=" * 60)
    logger.info("EXTRACTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total queried: {stats['total_queried']}")
    logger.info(f"Processed: {stats['processed']}")
    logger.info(f"Stored: {stats['stored']}")
    logger.info(f"Skipped (existing): {stats['skipped_existing']}")
    logger.info(f"Skipped (short): {stats['skipped_short']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info(f"Total cost: ${stats['total_cost_usd']:.2f}")
    logger.info(f"Elapsed time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    logger.info("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Batch extract knowledge from query_history")
    parser.add_argument("--user-id", type=str, help="Filter by user ID")
    parser.add_argument("--limit", type=int, default=0, help="Maximum records to process (0 = no limit)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N records")
    parser.add_argument("--batch-size", type=int, default=10, help="Records per batch")
    parser.add_argument("--dry-run", action="store_true", help="Extract but don't store")
    parser.add_argument("--no-skip-existing", action="store_true", help="Don't skip existing extractions")

    args = parser.parse_args()

    asyncio.run(batch_extract_knowledge(
        user_id=args.user_id,
        limit=args.limit,
        offset=args.offset,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip_existing
    ))


if __name__ == "__main__":
    main()
