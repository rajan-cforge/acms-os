#!/usr/bin/env python3
"""
Seed cross-domain discoveries from existing topic data.

Cognitive Architecture - Feb 2026

Analyzes existing topic data to find cross-domain connections.
Uses the actual co-occurrence patterns from query history.

This populates the "Creative Recombination" cognitive feature
that generates cross-domain insights.

Usage:
    python scripts/seed_cross_domain_discoveries.py
"""

import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Domain classification for the user's actual topics
DOMAIN_MAP = {
    # AI/ML
    "llm": "ai",
    "claude": "ai",
    "gemini": "ai",
    "openai": "ai",
    "chatgpt": "ai",
    "embedding": "ai",

    # Programming
    "python": "programming",
    "go": "programming",
    "golang": "programming",
    "fastapi": "programming",
    "javascript": "programming",
    "typescript": "programming",
    "code-review": "programming",

    # Infrastructure
    "kubernetes": "infrastructure",
    "docker": "infrastructure",
    "aws": "infrastructure",
    "monitoring": "infrastructure",
    "helm": "infrastructure",
    "prometheus": "infrastructure",

    # Security
    "security": "security",
    "rbac": "security",
    "oauth": "security",

    # Data
    "weaviate": "data",
    "postgresql": "data",
    "database": "data",
    "redis": "data",

    # Business
    "finance": "business",
    "business": "business",
    "project-mgmt": "business",

    # Quality
    "testing": "quality",

    # Communication
    "writing": "communication",

    # Networking
    "http": "networking",
    "api": "networking",
}

# Insights for domain bridges
DOMAIN_INSIGHTS = {
    "ai ↔ programming": "Your deep AI knowledge combined with Python/Go programming makes you uniquely positioned for AI tooling and agent development.",
    "ai ↔ infrastructure": "You bridge AI and infrastructure — AI-powered DevOps (AIOps) is a natural extension of your expertise.",
    "ai ↔ business": "Your combined AI and business/finance knowledge positions ACMS as both a technical and business play.",
    "ai ↔ security": "AI + Security = your professional sweet spot. This is exactly the SOC.ai and TalosAI domain.",
    "ai ↔ data": "AI + vector databases: this is the ACMS core competency. Your deepest technical moat.",
    "infrastructure ↔ security": "Infrastructure security is your day job — this is your deepest professional expertise.",
    "infrastructure ↔ programming": "Platform engineering: you build the infrastructure that other developers use.",
    "programming ↔ data": "Python + Weaviate: the core ACMS technology stack. Your most applied knowledge domain.",
    "programming ↔ quality": "Testing and code review alongside development: you practice quality-first engineering.",
    "business ↔ security": "Business-aware security leadership — the Director perspective that combines technical depth with business impact.",
    "programming ↔ security": "Security-aware development: you understand both the attacker and defender perspectives.",
    "data ↔ infrastructure": "Data platform engineering: deploying and managing data systems at scale.",
    "ai ↔ quality": "AI quality assurance: testing ML models and AI systems for reliability.",
}


def generate_insight(bridge: str, topics: list) -> str:
    """Generate a human-readable insight for the bridge."""
    # Try exact match first
    if bridge in DOMAIN_INSIGHTS:
        return DOMAIN_INSIGHTS[bridge]

    # Try reversed order
    parts = bridge.split(" ↔ ")
    if len(parts) == 2:
        reversed_bridge = f"{parts[1]} ↔ {parts[0]}"
        if reversed_bridge in DOMAIN_INSIGHTS:
            return DOMAIN_INSIGHTS[reversed_bridge]

    # Generate generic insight
    domain_names = bridge.replace(" ↔ ", " and ")
    return f"Your {domain_names} knowledge creates unique cross-domain perspective. Topics involved: {', '.join(topics[:5])}"


async def seed_discoveries():
    """Main seeding function."""
    from src.storage.database import get_db_pool

    print("=" * 60)
    print("ACMS Cross-Domain Discoveries Seeding")
    print("=" * 60)
    print()

    pool = await get_db_pool()

    # Step 1: Check/create cross_domain_discoveries table
    print("Step 1: Checking cross_domain_discoveries table...")
    async with pool.acquire() as conn:
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'cross_domain_discoveries'
            )
        """)

    if not table_exists:
        print("   Creating cross_domain_discoveries table...")
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cross_domain_discoveries (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    bridge VARCHAR(100) NOT NULL,
                    domain_a VARCHAR(50) NOT NULL,
                    domain_b VARCHAR(50) NOT NULL,
                    session_count INTEGER NOT NULL DEFAULT 0,
                    topics_involved TEXT[] DEFAULT '{}',
                    insight TEXT NOT NULL,
                    creativity_score FLOAT DEFAULT 0.0,
                    status VARCHAR(20) DEFAULT 'pending',
                    user_feedback VARCHAR(20),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT uq_discovery_bridge UNIQUE (bridge)
                );
                CREATE INDEX IF NOT EXISTS idx_discoveries_status ON cross_domain_discoveries(status);
                CREATE INDEX IF NOT EXISTS idx_discoveries_score ON cross_domain_discoveries(creativity_score DESC);
            """)
        print("   Table created.")
    else:
        print("   Table exists.")

    # Step 2: Find cross-domain sessions
    print("\nStep 2: Analyzing session windows for cross-domain patterns...")
    async with pool.acquire() as conn:
        sessions = await conn.fetch("""
            WITH session_windows AS (
                SELECT
                    qh.query_id,
                    qh.created_at,
                    te.primary_topic,
                    -- Create session IDs using 30-min windows
                    FLOOR(EXTRACT(EPOCH FROM qh.created_at) / 1800) as session_id
                FROM query_history qh
                JOIN topic_extractions te ON te.source_id = qh.query_id
                    AND te.source_type = 'query_history'
                WHERE te.primary_topic IS NOT NULL
                  AND te.primary_topic NOT IN ('transient', '', 'general')
            )
            SELECT session_id, array_agg(DISTINCT primary_topic) as topics
            FROM session_windows
            GROUP BY session_id
            HAVING COUNT(DISTINCT primary_topic) >= 2
            ORDER BY session_id DESC
        """)

    print(f"   Found {len(sessions)} sessions with 2+ topics")

    # Step 3: Count cross-domain bridges
    print("\nStep 3: Extracting domain bridges...")
    domain_bridges = defaultdict(lambda: {'count': 0, 'topics': set(), 'sessions': []})

    for session in sessions:
        topics = session['topics']
        domains = {}

        # Map topics to domains
        for topic in topics:
            domain = DOMAIN_MAP.get(topic.lower(), 'other')
            if domain != 'other':
                domains[topic] = domain

        # Find unique domain pairs in this session
        unique_domains = set(domains.values())
        if len(unique_domains) >= 2:
            for d1, d2 in combinations(sorted(unique_domains), 2):
                key = f"{d1} ↔ {d2}"
                domain_bridges[key]['count'] += 1
                domain_bridges[key]['topics'].update(t for t, d in domains.items() if d in (d1, d2))
                domain_bridges[key]['sessions'].append(session['session_id'])

    print(f"   Found {len(domain_bridges)} unique domain bridges")

    # Step 4: Generate and store discoveries
    print("\nStep 4: Storing discoveries...")
    print("\n   Cross-Domain Discoveries from your existing data:\n")

    discoveries_created = 0
    discoveries_updated = 0

    for bridge, data in sorted(domain_bridges.items(), key=lambda x: -x[1]['count']):
        if data['count'] >= 3:  # At least 3 sessions bridging these domains
            topics_involved = sorted(data['topics'])
            insight = generate_insight(bridge, topics_involved)

            # Parse domains from bridge
            parts = bridge.split(" ↔ ")
            domain_a = parts[0]
            domain_b = parts[1] if len(parts) > 1 else "unknown"

            # Calculate creativity score (higher for less common bridges)
            # More sessions = less creative (it's expected), but still valuable
            creativity_score = 1.0 / (1.0 + data['count'] * 0.1)

            metadata = json.dumps({
                "seeded_from": "query_history",
                "seeded_at": datetime.now(timezone.utc).isoformat(),
                "session_ids": [int(s) for s in data['sessions'][-10:]]  # Keep last 10 session IDs
            })

            async with pool.acquire() as conn:
                result = await conn.execute("""
                    INSERT INTO cross_domain_discoveries (
                        bridge, domain_a, domain_b, session_count,
                        topics_involved, insight, creativity_score, status, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'confirmed', $8)
                    ON CONFLICT (bridge)
                    DO UPDATE SET
                        session_count = EXCLUDED.session_count,
                        topics_involved = EXCLUDED.topics_involved,
                        insight = EXCLUDED.insight,
                        creativity_score = EXCLUDED.creativity_score,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """, bridge, domain_a, domain_b, data['count'],
                    topics_involved[:20], insight, creativity_score, metadata)

                if 'INSERT' in result:
                    discoveries_created += 1
                else:
                    discoveries_updated += 1

            print(f"   ⟐ {bridge}")
            print(f"      {data['count']} sessions bridge these domains")
            print(f"      Topics: {', '.join(topics_involved[:8])}")
            print(f"      Insight: {insight[:100]}...")
            print()

    print(f"   Created {discoveries_created} new discoveries")
    print(f"   Updated {discoveries_updated} existing discoveries")

    # Step 5: Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM cross_domain_discoveries")
        top_discoveries = await conn.fetch("""
            SELECT bridge, session_count, creativity_score
            FROM cross_domain_discoveries
            ORDER BY session_count DESC
            LIMIT 5
        """)

    print(f"\nTotal discoveries: {total}")
    print("\nTop 5 discoveries by session count:")
    for row in top_discoveries:
        print(f"   ⟐ {row['bridge']}: {row['session_count']} sessions "
              f"(creativity: {row['creativity_score']:.2f})")

    print("\n✅ Cross-domain discoveries seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_discoveries())
