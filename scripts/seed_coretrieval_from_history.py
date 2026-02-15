#!/usr/bin/env python3
"""
Seed the co-retrieval graph by analyzing existing query_history.

Cognitive Architecture - Feb 2026

Logic: Queries within the same 30-minute window about different topics
indicate co-retrieval patterns. These become Hebbian associations.

"Neurons that fire together wire together" - Topics queried together
become associated for future retrieval.

Usage:
    python scripts/seed_coretrieval_from_history.py

This script:
1. Queries all topic_extractions with timestamps
2. Groups queries into 30-minute session windows
3. Extracts topic co-occurrences from each session
4. Stores as co-retrieval edges in PostgreSQL
"""

import asyncio
import os
import sys
from datetime import timedelta
from collections import defaultdict
from itertools import combinations

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def seed_coretrieval():
    """Main seeding function."""
    from src.storage.database import get_db_pool

    print("=" * 60)
    print("ACMS Co-Retrieval Graph Seeding")
    print("=" * 60)
    print()

    pool = await get_db_pool()

    # Step 1: Get all queries with topics, ordered by time
    print("Step 1: Fetching queries with topic extractions...")
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                qh.query_id,
                qh.question,
                qh.created_at,
                te.primary_topic
            FROM query_history qh
            JOIN topic_extractions te ON te.source_id = qh.query_id
                AND te.source_type = 'query_history'
            WHERE te.primary_topic IS NOT NULL
              AND te.primary_topic NOT IN ('transient', '', 'general')
            ORDER BY qh.created_at
        """)

    print(f"   Found {len(rows)} queries with topic extractions")

    if not rows:
        print("   No queries to process. Exiting.")
        return

    # Step 2: Group into 30-minute session windows
    print("\nStep 2: Grouping queries into session windows...")
    sessions = []
    current_session = []
    session_window = timedelta(minutes=30)

    for row in rows:
        if current_session:
            time_gap = row['created_at'] - current_session[-1]['created_at']
            if time_gap > session_window:
                # New session starts
                if len(current_session) >= 2:
                    sessions.append(current_session)
                current_session = []
        current_session.append(dict(row))

    # Don't forget the last session
    if len(current_session) >= 2:
        sessions.append(current_session)

    print(f"   Found {len(sessions)} sessions with 2+ queries")

    # Step 3: Extract topic co-occurrences from each session
    print("\nStep 3: Extracting topic co-occurrences...")
    coretrieval_counts = defaultdict(lambda: {'count': 0, 'sessions': []})

    for session in sessions:
        topics_in_session = set(row['primary_topic'] for row in session)
        session_time = session[0]['created_at']

        for topic_a, topic_b in combinations(sorted(topics_in_session), 2):
            key = (topic_a, topic_b)
            coretrieval_counts[key]['count'] += 1
            coretrieval_counts[key]['sessions'].append(session_time)

    print(f"   Found {len(coretrieval_counts)} unique topic pairs")

    # Step 4: Store as co-retrieval edges
    print("\nStep 4: Storing co-retrieval edges...")

    # Check if coretrieval_edges table exists
    async with pool.acquire() as conn:
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'coretrieval_edges'
            )
        """)

    if not table_exists:
        print("   Creating coretrieval_edges table...")
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS coretrieval_edges (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    item_a_id VARCHAR(255) NOT NULL,
                    item_b_id VARCHAR(255) NOT NULL,
                    co_retrieval_count INTEGER DEFAULT 1,
                    avg_temporal_distance FLOAT,
                    last_co_retrieval TIMESTAMP WITH TIME ZONE,
                    strength FLOAT NOT NULL DEFAULT 0.0,
                    context_topics JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT uq_coretrieval_pair UNIQUE (item_a_id, item_b_id)
                );
                CREATE INDEX IF NOT EXISTS idx_coretrieval_strength ON coretrieval_edges(strength DESC);
            """)
        print("   Table created.")

    edges_created = 0
    edges_updated = 0

    # Sort by count descending and store
    sorted_pairs = sorted(coretrieval_counts.items(), key=lambda x: -x[1]['count'])

    print("\n   Top co-retrieval patterns:")
    import json
    import math
    from datetime import datetime

    for (topic_a, topic_b), data in sorted_pairs[:20]:
        count = data['count']
        if count >= 2:  # Only store meaningful associations
            # Calculate Hebbian strength: log(count+1) * exp(-0.05 * days_since_last)
            last_session = max(data['sessions'])
            days_since = (datetime.now(last_session.tzinfo) - last_session).days
            strength = math.log(count + 1) * math.exp(-0.05 * days_since)

            context_json = json.dumps({
                "seeded_from": "query_history",
                "session_count": len(data['sessions'])
            })

            async with pool.acquire() as conn:
                # Upsert the edge
                result = await conn.execute("""
                    INSERT INTO coretrieval_edges (item_a_id, item_b_id, co_retrieval_count,
                                                   last_co_retrieval, strength, context_topics)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (item_a_id, item_b_id)
                    DO UPDATE SET
                        co_retrieval_count = EXCLUDED.co_retrieval_count,
                        last_co_retrieval = EXCLUDED.last_co_retrieval,
                        strength = EXCLUDED.strength,
                        updated_at = NOW()
                """, topic_a, topic_b, count, last_session, strength, context_json)

                if 'INSERT' in result:
                    edges_created += 1
                else:
                    edges_updated += 1

            print(f"   {topic_a} ↔ {topic_b}: {count} co-occurrences (strength: {strength:.2f})")

    # Store remaining edges with count >= 2
    for (topic_a, topic_b), data in sorted_pairs[20:]:
        count = data['count']
        if count >= 2:
            last_session = max(data['sessions'])
            days_since = (datetime.now(last_session.tzinfo) - last_session).days
            strength = math.log(count + 1) * math.exp(-0.05 * days_since)

            context_json = json.dumps({
                "seeded_from": "query_history",
                "session_count": len(data['sessions'])
            })

            async with pool.acquire() as conn:
                result = await conn.execute("""
                    INSERT INTO coretrieval_edges (item_a_id, item_b_id, co_retrieval_count,
                                                   last_co_retrieval, strength, context_topics)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (item_a_id, item_b_id)
                    DO UPDATE SET
                        co_retrieval_count = EXCLUDED.co_retrieval_count,
                        last_co_retrieval = EXCLUDED.last_co_retrieval,
                        strength = EXCLUDED.strength,
                        updated_at = NOW()
                """, topic_a, topic_b, count, last_session, strength, context_json)

                if 'INSERT' in result:
                    edges_created += 1
                else:
                    edges_updated += 1

    print(f"\n   Created {edges_created} new edges")
    print(f"   Updated {edges_updated} existing edges")

    # Step 5: Summary stats
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    async with pool.acquire() as conn:
        total_edges = await conn.fetchval("SELECT COUNT(*) FROM coretrieval_edges")
        avg_strength = await conn.fetchval("SELECT AVG(strength) FROM coretrieval_edges")
        top_edges = await conn.fetch("""
            SELECT item_a_id, item_b_id, co_retrieval_count, strength
            FROM coretrieval_edges
            ORDER BY strength DESC
            LIMIT 10
        """)

    print(f"\nTotal edges in graph: {total_edges}")
    print(f"Average strength: {avg_strength:.2f}" if avg_strength else "Average strength: N/A")
    print("\nTop 10 associations by strength:")
    for edge in top_edges:
        print(f"   {edge['item_a_id']} ↔ {edge['item_b_id']}: "
              f"{edge['co_retrieval_count']} sessions, strength={edge['strength']:.2f}")

    print("\n✅ Co-retrieval graph seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_coretrieval())
