#!/usr/bin/env python3
"""
Seed topic summaries from existing topic_extractions.

Cognitive Architecture - Feb 2026

Generates Level 2 topic summaries from existing topic_extractions.
Uses the actual keywords and query content to build summaries.

This populates the knowledge compaction tier that feeds the
dashboard's Topic Deep Dive view.

Usage:
    python scripts/seed_topic_summaries.py
"""

import asyncio
import json
import math
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def determine_expertise_level(topic_depth: int, total: int) -> str:
    """
    Determine expertise level using same algorithm as context_assembler.

    Uses relative depth (% of total queries) combined with absolute depth,
    on a logarithmic scale.
    """
    if topic_depth == 0:
        return "first_encounter"

    if total == 0:
        return "beginner"

    # Relative share of total knowledge
    relative_share = topic_depth / max(total, 1)

    # Log-scaled absolute depth (diminishing returns)
    log_depth = math.log2(topic_depth + 1)

    # Combined score: weighted blend of relative and absolute
    normalized_log = min(log_depth / 10.0, 1.0)
    normalized_relative = min(relative_share / 0.20, 1.0)

    combined_score = (normalized_log * 0.6) + (normalized_relative * 0.4)

    # Thresholds calibrated for realistic distribution
    if combined_score >= 0.75:
        return "expert"
    elif combined_score >= 0.50:
        return "advanced"
    elif combined_score >= 0.25:
        return "intermediate"
    elif topic_depth >= 3:
        return "beginner"
    else:
        return "first_encounter"


async def seed_topic_summaries():
    """Main seeding function."""
    from src.storage.database import get_db_pool

    print("=" * 60)
    print("ACMS Topic Summaries Seeding")
    print("=" * 60)
    print()

    pool = await get_db_pool()

    # Step 1: Check/create topic_summaries table
    print("Step 1: Checking topic_summaries table...")
    async with pool.acquire() as conn:
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'topic_summaries'
            )
        """)

    if not table_exists:
        print("   Creating topic_summaries table...")
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS topic_summaries (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    topic_slug VARCHAR(100) UNIQUE NOT NULL,
                    knowledge_depth INTEGER NOT NULL DEFAULT 0,
                    expertise_level VARCHAR(20) NOT NULL DEFAULT 'beginner',
                    key_concepts TEXT[] DEFAULT '{}',
                    sample_questions TEXT[] DEFAULT '{}',
                    first_interaction TIMESTAMP WITH TIME ZONE,
                    last_interaction TIMESTAMP WITH TIME ZONE,
                    knowledge_gaps TEXT[] DEFAULT '{}',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_topic_summaries_slug ON topic_summaries(topic_slug);
                CREATE INDEX IF NOT EXISTS idx_topic_summaries_depth ON topic_summaries(knowledge_depth DESC);
            """)
        print("   Table created.")
    else:
        print("   Table exists.")

    # Step 2: Get topic stats from topic_extractions
    print("\nStep 2: Aggregating topic statistics...")
    async with pool.acquire() as conn:
        topics = await conn.fetch("""
            SELECT
                te.primary_topic,
                COUNT(*) as depth,
                array_agg(DISTINCT unnest_topics) FILTER (WHERE unnest_topics IS NOT NULL) as all_topics,
                MIN(qh.created_at) as first_seen,
                MAX(qh.created_at) as last_seen
            FROM topic_extractions te
            JOIN query_history qh ON qh.query_id = te.source_id
                AND te.source_type = 'query_history'
            CROSS JOIN LATERAL unnest(te.topics) AS unnest_topics
            WHERE te.primary_topic IS NOT NULL
              AND te.primary_topic NOT IN ('transient', '', 'general')
            GROUP BY te.primary_topic
            HAVING COUNT(*) >= 3
            ORDER BY COUNT(*) DESC
        """)

    print(f"   Found {len(topics)} topics with 3+ queries")

    # Calculate total for expertise levels
    total_depth = sum(t['depth'] for t in topics)
    print(f"   Total knowledge depth: {total_depth}")

    # Step 3: Get sample questions for each topic
    print("\nStep 3: Generating topic summaries...")
    summaries_created = 0
    summaries_updated = 0

    for topic in topics:
        topic_slug = topic['primary_topic']
        depth = topic['depth']

        # Get sample questions
        async with pool.acquire() as conn:
            samples = await conn.fetch("""
                SELECT qh.question, MAX(qh.created_at) as latest
                FROM query_history qh
                JOIN topic_extractions te ON te.source_id = qh.query_id
                    AND te.source_type = 'query_history'
                WHERE te.primary_topic = $1
                GROUP BY qh.question
                ORDER BY latest DESC
                LIMIT 10
            """, topic_slug)

        sample_questions = [s['question'][:500] for s in samples]

        # Get all keywords/concepts for this topic
        all_keywords = topic['all_topics'] if topic['all_topics'] else []
        key_concepts = sorted(set(str(kw).lower().strip() for kw in all_keywords if kw))[:20]

        # Determine expertise level
        level = determine_expertise_level(depth, total_depth)

        # Build metadata
        metadata = json.dumps({
            "seeded_from": "topic_extractions",
            "seeded_at": datetime.utcnow().isoformat(),
            "total_context_depth": total_depth
        })

        # Upsert the summary
        async with pool.acquire() as conn:
            result = await conn.execute("""
                INSERT INTO topic_summaries (
                    topic_slug, knowledge_depth, expertise_level,
                    key_concepts, sample_questions,
                    first_interaction, last_interaction, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (topic_slug)
                DO UPDATE SET
                    knowledge_depth = EXCLUDED.knowledge_depth,
                    expertise_level = EXCLUDED.expertise_level,
                    key_concepts = EXCLUDED.key_concepts,
                    sample_questions = EXCLUDED.sample_questions,
                    first_interaction = EXCLUDED.first_interaction,
                    last_interaction = EXCLUDED.last_interaction,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, topic_slug, depth, level,
                key_concepts, sample_questions,
                topic['first_seen'], topic['last_seen'], metadata)

            if 'INSERT' in result:
                summaries_created += 1
            else:
                summaries_updated += 1

        # Pretty emoji for level
        emoji_map = {
            "expert": "🏗️",
            "advanced": "🔬",
            "intermediate": "🌿",
            "beginner": "🌱",
            "first_encounter": "👋"
        }
        emoji = emoji_map.get(level, "📚")

        # Print first 15 topics
        if summaries_created + summaries_updated <= 15:
            first_date = topic['first_seen'].strftime('%b %Y') if topic['first_seen'] else 'N/A'
            last_date = topic['last_seen'].strftime('%b %Y') if topic['last_seen'] else 'N/A'
            print(f"   {emoji} {level:>12} | {topic_slug:<15} | "
                  f"{depth:>4} queries | "
                  f"{len(key_concepts)} concepts | "
                  f"{first_date} - {last_date}")

    print(f"\n   Created {summaries_created} new summaries")
    print(f"   Updated {summaries_updated} existing summaries")

    # Step 4: Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    async with pool.acquire() as conn:
        # Count by expertise level
        level_counts = await conn.fetch("""
            SELECT expertise_level, COUNT(*) as count
            FROM topic_summaries
            GROUP BY expertise_level
            ORDER BY count DESC
        """)

        total = await conn.fetchval("SELECT COUNT(*) FROM topic_summaries")
        total_depth = await conn.fetchval("SELECT SUM(knowledge_depth) FROM topic_summaries")

    print(f"\nTotal topics: {total}")
    print(f"Total knowledge depth: {total_depth}")
    print("\nExpertise distribution:")
    for row in level_counts:
        emoji = emoji_map.get(row['expertise_level'], "📚")
        print(f"   {emoji} {row['expertise_level']}: {row['count']} topics")

    print("\n✅ Topic summaries seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_topic_summaries())
