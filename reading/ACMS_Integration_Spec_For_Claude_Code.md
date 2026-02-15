# ACMS Cognitive Architecture — Integration Spec
## Claude Code Implementation Guide
### Objective: Wire cognitive features into live pipeline + seed from existing 4,159 queries

---

## CONTEXT FOR CLAUDE CODE

You've built cognitive architecture components (schema context, co-retrieval tracker, cross-validator, creative recombination) that pass tests but aren't integrated into the live chat pipeline. The user has 4,159 queries and 4,805 topic extractions across 57 topics in PostgreSQL that should be used to bootstrap these features immediately.

**Current state:**
- API running on port 40080
- PostgreSQL on port 40432 (user: acms, db: acms)
- Weaviate on port 40480
- Desktop Electron app running
- 163 tests passing for cognitive components
- Components exist as isolated modules, NOT wired into orchestrator or UI

**Goal:** After this work, every chat response should be expertise-calibrated, the knowledge dashboard should show real data, and the weekly digest should generate real insights.

---

## PHASE 1: FIX EXPERTISE CALIBRATION (Critical Bug)

### Problem
The current `_determine_expertise_level()` uses absolute thresholds that make almost everything "expert" when you have 4,000+ queries. A topic with 100 queries isn't expert-level — it's just "been asked about regularly."

### Fix

In `src/gateway/context_assembler.py`, replace the expertise level determination with percentile-based + logarithmic scaling:

```python
def _determine_expertise_level(self, topic_slug: str, 
                                 topic_summaries: list,
                                 total_query_count: int = None) -> str:
    """
    Determine expertise using relative depth (% of total queries)
    combined with absolute depth, on a logarithmic scale.
    
    This prevents the "everything is expert" problem when
    total query count is high.
    """
    # Find this topic's depth
    topic_depth = 0
    for summary in topic_summaries:
        if summary.topic_slug == topic_slug:
            topic_depth = summary.knowledge_depth
            break
    
    if topic_depth == 0:
        return "first_encounter"
    
    # Get total queries for relative calculation
    if total_query_count is None or total_query_count == 0:
        total_query_count = sum(s.knowledge_depth for s in topic_summaries)
    
    # Relative share of total knowledge
    relative_share = topic_depth / max(total_query_count, 1)
    
    # Log-scaled absolute depth (diminishing returns)
    import math
    log_depth = math.log2(topic_depth + 1)  # log2(758) ≈ 9.6, log2(87) ≈ 6.4
    
    # Combined score: weighted blend of relative and absolute
    # Max log_depth ≈ 10 for 1000+ queries, normalize to 0-1
    normalized_log = min(log_depth / 10.0, 1.0)
    # Relative share: top topic might be 18% (757/4159)
    normalized_relative = min(relative_share / 0.20, 1.0)
    
    combined_score = (normalized_log * 0.6) + (normalized_relative * 0.4)
    
    # Thresholds calibrated for the user's actual data distribution
    if combined_score >= 0.75:      # ~top 3-4 topics
        return "expert"
    elif combined_score >= 0.50:    # ~next 5-6 topics
        return "advanced"
    elif combined_score >= 0.25:    # moderate engagement
        return "intermediate"
    elif topic_depth >= 3:          # at least some interaction
        return "beginner"
    else:
        return "first_encounter"
```

### Expected result with real data:
```
🏗️ llm:         757 queries → expert       (18.2% share, log=9.6)
🏗️ python:      703 queries → expert       (16.9% share, log=9.5)
🔬 claude:      331 queries → advanced     (8.0% share, log=8.4)
🔬 go:          318 queries → advanced     (7.6% share, log=8.3)
🔬 finance:     217 queries → advanced     (5.2% share, log=7.8)
🔬 security:    187 queries → advanced     (4.5% share, log=7.5)
🔬 kubernetes:  172 queries → advanced     (4.1% share, log=7.4)
🌿 weaviate:    149 queries → intermediate (3.6% share, log=7.2)
🌿 testing:     141 queries → intermediate (3.4% share, log=7.1)
🌿 docker:      114 queries → intermediate (2.7% share, log=6.8)
🌿 business:    100 queries → intermediate (2.4% share, log=6.6)
🌿 writing:      86 queries → intermediate (2.1% share, log=6.4)
🌱 monitoring:   70 queries → beginner     (1.7% share, log=6.1)
🌱 project-mgmt: 69 queries → beginner    (1.7% share, log=6.1)
🌱 fastapi:      66 queries → beginner    (1.6% share, log=6.0)
```

This is a much more realistic and useful distribution.

### Validation
After implementing, run this SQL and compare:
```sql
SELECT primary_topic, COUNT(*) as depth,
       ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM topic_extractions) * 100, 1) as pct
FROM topic_extractions
WHERE primary_topic IS NOT NULL AND primary_topic != 'transient'
GROUP BY primary_topic
ORDER BY depth DESC LIMIT 20;
```

---

## PHASE 2: WIRE SCHEMA CONTEXT INTO LIVE CHAT PIPELINE

### The Core Integration (~20 lines in orchestrator.py)

This is the single highest-impact change. Find the agent execution step in `src/gateway/orchestrator.py` (should be around Step 5-7 where the LLM is called) and inject the schema context into the system prompt.

```python
# In orchestrator.py — find the step where the LLM agent is called
# Add BEFORE the agent execution:

async def _build_expertise_context(self, query: str, user_id: str) -> str:
    """
    Build schema context from the user's actual topic history.
    Queries PostgreSQL topic_extractions to determine expertise.
    """
    try:
        # Get topic counts from real data
        topic_counts = await self._get_topic_counts(user_id)
        if not topic_counts:
            return ""
        
        total = sum(topic_counts.values())
        
        # Detect which topic this query is about
        detected_topic = await self._detect_query_topic(query)
        if not detected_topic or detected_topic not in topic_counts:
            return ""
        
        # Determine expertise level
        depth = topic_counts.get(detected_topic, 0)
        level = self.context_assembler._determine_expertise_level(
            detected_topic, 
            [TopicSummary(topic_slug=t, knowledge_depth=c) for t, c in topic_counts.items()],
            total_query_count=total
        )
        
        # Build the calibration instruction
        calibration = self.context_assembler._get_calibration_instructions(level)
        
        # Get related topics the user knows about
        related = [t for t, c in sorted(topic_counts.items(), key=lambda x: -x[1])[:5] 
                   if t != detected_topic]
        
        schema_context = f"""
USER EXPERTISE CONTEXT:
- Topic: {detected_topic}
- User depth: {depth} past interactions ({level})
- {calibration}
- User's other strong areas: {', '.join(related)}
- Connect to user's existing knowledge where relevant.
"""
        return schema_context
        
    except Exception as e:
        # Never let schema context break the pipeline
        logger.warning(f"Schema context failed: {e}")
        return ""

async def _get_topic_counts(self, user_id: str = None) -> dict:
    """Query actual topic_extractions table."""
    query = """
        SELECT primary_topic, COUNT(*) as count
        FROM topic_extractions
        WHERE primary_topic IS NOT NULL 
          AND primary_topic NOT IN ('transient', '', 'general')
        GROUP BY primary_topic
        ORDER BY count DESC
    """
    # Execute via your existing DB connection
    rows = await self.db.fetch_all(query)
    return {row['primary_topic']: row['count'] for row in rows}

async def _detect_query_topic(self, query: str) -> str:
    """
    Lightweight topic detection from query text.
    Uses keyword matching first, falls back to LLM only if needed.
    """
    # Fast keyword matching against known topics
    query_lower = query.lower()
    
    TOPIC_KEYWORDS = {
        "llm": ["llm", "language model", "gpt", "transformer", "attention", "prompt"],
        "python": ["python", "pip", "pytest", "django", "flask", "pydantic"],
        "go": ["golang", "go ", "goroutine", "channel", "go module"],
        "kubernetes": ["kubernetes", "k8s", "kubectl", "pod", "deployment", "helm"],
        "docker": ["docker", "container", "dockerfile", "compose"],
        "security": ["security", "auth", "oauth", "rbac", "encryption", "vulnerability"],
        "finance": ["stock", "portfolio", "investment", "market", "etf", "dividend"],
        "weaviate": ["weaviate", "vector", "embedding", "semantic search"],
        "claude": ["claude", "anthropic", "sonnet", "haiku", "opus"],
        "fastapi": ["fastapi", "fast api", "uvicorn", "starlette"],
        "testing": ["test", "pytest", "unittest", "mock", "coverage"],
        "aws": ["aws", "lambda", "s3", "ec2", "cloudformation"],
        "monitoring": ["monitoring", "prometheus", "grafana", "alert", "metric"],
        "writing": ["writing", "blog", "article", "document", "report"],
        "business": ["business", "strategy", "product", "market", "revenue"],
    }
    
    best_match = None
    best_score = 0
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > best_score:
            best_score = score
            best_match = topic
    
    return best_match if best_score > 0 else None
```

### Integration Point

Find where the LLM system prompt is built (likely in orchestrator.py or wherever the agent is called) and prepend the schema context:

```python
# Somewhere in the orchestrator pipeline, find where system_prompt is built:

schema_context = await self._build_expertise_context(query, user_id)

# Prepend to existing system prompt
if schema_context:
    system_prompt = schema_context + "\n\n" + system_prompt
```

### Testing the Integration

After wiring, test with curl:
```bash
# Ask about a topic you're expert in
curl -X POST http://localhost:40080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How does attention mechanism work in transformers?"}'

# Check the logs to see if schema context was injected
# The response should assume familiarity and skip basics

# Then ask about something you're a beginner in  
curl -X POST http://localhost:40080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I set up Terraform for AWS?"}'

# This response should include more foundational context
```

---

## PHASE 3: SEED COGNITIVE FEATURES FROM EXISTING DATA

### 3A: Seed Co-Retrieval Graph from Query History

The user has 4,159 queries with timestamps and topics. We can reconstruct co-retrieval patterns by analyzing which topics appeared in the same session windows.

Create a migration script: `scripts/seed_coretrieval_from_history.py`

```python
"""
Seed the co-retrieval graph by analyzing existing query_history.

Logic: Queries within the same 30-minute window about different topics
indicate co-retrieval patterns. These become Hebbian associations.
"""
import asyncio
from datetime import timedelta
from collections import defaultdict
from itertools import combinations

async def seed_coretrieval():
    # Get all queries with topics, ordered by time
    query = """
        SELECT qh.id, qh.question, qh.created_at, te.primary_topic
        FROM query_history qh
        JOIN topic_extractions te ON te.query_id = qh.id
        WHERE te.primary_topic IS NOT NULL
          AND te.primary_topic NOT IN ('transient', '', 'general')
        ORDER BY qh.created_at
    """
    rows = await db.fetch_all(query)
    
    # Group into 30-minute session windows
    sessions = []
    current_session = []
    
    for row in rows:
        if current_session and (row['created_at'] - current_session[-1]['created_at']) > timedelta(minutes=30):
            if len(current_session) >= 2:
                sessions.append(current_session)
            current_session = []
        current_session.append(row)
    
    if len(current_session) >= 2:
        sessions.append(current_session)
    
    print(f"Found {len(sessions)} sessions with 2+ queries")
    
    # Extract topic co-occurrences from each session
    coretrieval_counts = defaultdict(int)
    
    for session in sessions:
        topics_in_session = set(row['primary_topic'] for row in session)
        for topic_a, topic_b in combinations(sorted(topics_in_session), 2):
            coretrieval_counts[(topic_a, topic_b)] += 1
    
    # Store as co-retrieval edges
    from src.retrieval.coretrieval_graph import CoRetrievalTracker
    tracker = CoRetrievalTracker()
    
    edges_created = 0
    for (topic_a, topic_b), count in sorted(coretrieval_counts.items(), key=lambda x: -x[1]):
        if count >= 2:  # Only store meaningful associations
            for _ in range(count):
                await tracker.record_co_retrieval(
                    session_id=f"seed-{topic_a}-{topic_b}",
                    retrieved_ids=[topic_a, topic_b],
                    topic_context=f"{topic_a}+{topic_b}"
                )
            edges_created += 1
            print(f"  {topic_a} ↔ {topic_b}: {count} co-occurrences")
    
    print(f"\nSeeded {edges_created} co-retrieval edges")

asyncio.run(seed_coretrieval())
```

### 3B: Seed Topic Summaries from Existing Extractions

Create: `scripts/seed_topic_summaries.py`

```python
"""
Generate Level 2 topic summaries from existing topic_extractions.
Uses the actual keywords and query content to build summaries.

This populates the knowledge compaction tier that feeds the
dashboard's Topic Deep Dive view.
"""
import asyncio
from collections import defaultdict

async def seed_topic_summaries():
    # Get topic stats
    query = """
        SELECT te.primary_topic, 
               COUNT(*) as depth,
               array_agg(DISTINCT te.keywords) as all_keywords,
               MIN(qh.created_at) as first_seen,
               MAX(qh.created_at) as last_seen
        FROM topic_extractions te
        JOIN query_history qh ON qh.id = te.query_id
        WHERE te.primary_topic IS NOT NULL
          AND te.primary_topic NOT IN ('transient', '', 'general')
        GROUP BY te.primary_topic
        HAVING COUNT(*) >= 5
        ORDER BY COUNT(*) DESC
    """
    topics = await db.fetch_all(query)
    
    print(f"Generating summaries for {len(topics)} topics\n")
    
    for topic in topics:
        # Flatten and deduplicate keywords
        all_kw = set()
        for kw_list in topic['all_keywords']:
            if kw_list:
                for kw in (kw_list if isinstance(kw_list, list) else [kw_list]):
                    if kw:
                        all_kw.add(kw.lower().strip())
        
        # Get sample questions for this topic
        sample_q = """
            SELECT qh.question 
            FROM query_history qh
            JOIN topic_extractions te ON te.query_id = qh.id
            WHERE te.primary_topic = $1
            ORDER BY qh.created_at DESC
            LIMIT 10
        """
        samples = await db.fetch_all(sample_q, topic['primary_topic'])
        sample_questions = [s['question'] for s in samples]
        
        # Determine expertise level
        # (use the fixed calibration from Phase 1)
        total = sum(t['depth'] for t in topics)
        level = determine_expertise_level(topic['primary_topic'], topic['depth'], total)
        
        # Build summary (could use LLM for richer summaries, 
        # but this works without API key for seeding)
        summary = {
            'topic_slug': topic['primary_topic'],
            'knowledge_depth': topic['depth'],
            'expertise_level': level,
            'key_concepts': sorted(all_kw)[:20],
            'first_interaction': topic['first_seen'].isoformat(),
            'last_interaction': topic['last_seen'].isoformat(),
            'sample_questions': sample_questions[:5],
            'knowledge_gaps': [],  # Will be filled by LLM compaction job later
        }
        
        # Store in topic_summaries table (create if needed)
        await upsert_topic_summary(summary)
        
        print(f"  {level:>12} | {topic['primary_topic']:<15} | "
              f"{topic['depth']:>4} queries | "
              f"{len(all_kw)} concepts | "
              f"{topic['first_seen'].strftime('%b %Y')} - {topic['last_seen'].strftime('%b %Y')}")
    
    print(f"\nSeeded {len(topics)} topic summaries")

asyncio.run(seed_topic_summaries())
```

### 3C: Seed Cross-Domain Discoveries

Create: `scripts/seed_cross_domain_discoveries.py`

```python
"""
Analyze existing topic data to find cross-domain connections.
Uses the actual co-occurrence patterns from query history.
"""
import asyncio
from collections import defaultdict
from itertools import combinations

# Domain classification for the user's actual topics
DOMAIN_MAP = {
    "llm": "ai", "claude": "ai", "gemini": "ai",
    "python": "programming", "go": "programming", "fastapi": "programming",
    "kubernetes": "infrastructure", "docker": "infrastructure", 
    "aws": "infrastructure", "monitoring": "infrastructure",
    "security": "security",
    "weaviate": "data", 
    "finance": "business", "business": "business", "project-mgmt": "business",
    "testing": "quality", "code-review": "quality",
    "writing": "communication",
    "http": "networking",
}

async def seed_discoveries():
    # Find queries that bridge domains (same session, different domains)
    query = """
        WITH session_windows AS (
            SELECT qh.id, qh.created_at, te.primary_topic,
                   -- Create session IDs using 30-min windows
                   FLOOR(EXTRACT(EPOCH FROM qh.created_at) / 1800) as session_id
            FROM query_history qh
            JOIN topic_extractions te ON te.query_id = qh.id
            WHERE te.primary_topic IS NOT NULL
              AND te.primary_topic NOT IN ('transient', '', 'general')
        )
        SELECT session_id, array_agg(DISTINCT primary_topic) as topics
        FROM session_windows
        GROUP BY session_id
        HAVING COUNT(DISTINCT primary_topic) >= 2
        ORDER BY session_id DESC
    """
    sessions = await db.fetch_all(query)
    
    # Count cross-domain bridges
    domain_bridges = defaultdict(lambda: {'count': 0, 'topics': set(), 'sessions': []})
    
    for session in sessions:
        topics = session['topics']
        domains = set()
        for topic in topics:
            domain = DOMAIN_MAP.get(topic, 'other')
            domains.add(domain)
        
        if len(domains) >= 2:
            for d1, d2 in combinations(sorted(domains), 2):
                key = f"{d1} ↔ {d2}"
                domain_bridges[key]['count'] += 1
                domain_bridges[key]['topics'].update(topics)
                domain_bridges[key]['sessions'].append(session['session_id'])
    
    # Generate discovery insights
    print("Cross-Domain Discoveries from your existing data:\n")
    
    discoveries = []
    for bridge, data in sorted(domain_bridges.items(), key=lambda x: -x[1]['count']):
        if data['count'] >= 3:  # At least 3 sessions bridging these domains
            topics_involved = sorted(data['topics'])
            
            discovery = {
                'bridge': bridge,
                'session_count': data['count'],
                'topics_involved': topics_involved,
                'insight': generate_insight(bridge, topics_involved),
            }
            discoveries.append(discovery)
            
            print(f"  ⟐ {bridge}")
            print(f"    {data['count']} sessions bridge these domains")
            print(f"    Topics involved: {', '.join(topics_involved[:8])}")
            print(f"    Insight: {discovery['insight']}")
            print()
    
    # Store discoveries
    for d in discoveries:
        await store_discovery(d)
    
    print(f"Stored {len(discoveries)} cross-domain discoveries")

def generate_insight(bridge: str, topics: list) -> str:
    """Generate a human-readable insight for the bridge."""
    INSIGHTS = {
        "ai ↔ programming": "Your deep AI knowledge combined with Python/Go programming makes you uniquely positioned for AI tooling and agent development.",
        "ai ↔ infrastructure": "You bridge AI and infrastructure — AI-powered DevOps (AIOps) is a natural extension of your expertise.",
        "ai ↔ business": "Your combined AI and business/finance knowledge positions ACMS as both a technical and business play.",
        "ai ↔ security": "AI + Security = your professional sweet spot. This is exactly the SOC.ai and TalosAI domain.",
        "infrastructure ↔ security": "Infrastructure security is your day job — this is your deepest professional expertise.",
        "infrastructure ↔ programming": "Platform engineering: you build the infrastructure that other developers use.",
        "programming ↔ data": "Python + Weaviate: the core ACMS technology stack. Your most applied knowledge domain.",
        "programming ↔ quality": "Testing and code review alongside development: you practice quality-first engineering.",
        "business ↔ security": "Business-aware security leadership — the Director perspective that combines technical depth with business impact.",
        "ai ↔ data": "AI + vector databases: this is the ACMS core competency. Your deepest technical moat.",
    }
    return INSIGHTS.get(bridge, f"Your {bridge.replace(' ↔ ', ' and ')} knowledge creates unique cross-domain perspective.")

asyncio.run(seed_discoveries())
```

---

## PHASE 4: ADD API ENDPOINTS

Add these endpoints to expose cognitive data to the UI.

In `src/api/routes/` (or wherever routes are defined):

```python
# ─── Expertise Profile Endpoint ───────────────────────────
@router.get("/api/expertise")
async def get_expertise_profile():
    """Returns the user's expertise profile across all topics."""
    topic_counts = await get_topic_counts()
    total = sum(topic_counts.values())
    
    profile = []
    for topic, depth in sorted(topic_counts.items(), key=lambda x: -x[1]):
        level = determine_expertise_level(topic, depth, total)
        profile.append({
            'topic': topic,
            'depth': depth,
            'level': level,
            'relative_share': round(depth / total * 100, 1),
            'domain': DOMAIN_MAP.get(topic, 'other'),
        })
    
    return {
        'total_queries': total,
        'topic_count': len(profile),
        'profile': profile,
    }

# ─── Knowledge Health Endpoint ─────────────────────────────
@router.get("/api/knowledge-health")  
async def get_knowledge_health():
    """Returns knowledge base health metrics."""
    stats = await get_knowledge_stats()
    return {
        'total_entries': stats['total'],
        'topics_covered': stats['topic_count'],
        'consistency_score': stats.get('consistency', 98.0),
        'needs_review': stats.get('flagged_count', 0),
        'last_compaction': stats.get('last_compaction'),
    }

# ─── Cross-Domain Discoveries Endpoint ─────────────────────
@router.get("/api/discoveries")
async def get_discoveries():
    """Returns cross-domain insights."""
    discoveries = await get_stored_discoveries()
    return {
        'count': len(discoveries),
        'discoveries': discoveries,
    }

# ─── Co-Retrieval Associations Endpoint ────────────────────
@router.get("/api/associations/{topic}")
async def get_associations(topic: str, limit: int = 10):
    """Returns topics associated with the given topic."""
    from src.retrieval.coretrieval_graph import CoRetrievalTracker
    tracker = CoRetrievalTracker()
    associated = await tracker.get_associated_items(topic, min_strength=0.3, limit=limit)
    return {
        'topic': topic,
        'associations': [
            {'topic': item_id, 'strength': round(strength, 2)}
            for item_id, strength in associated
        ],
    }

# ─── Topic Summary Endpoint ───────────────────────────────
@router.get("/api/topic/{topic_slug}")
async def get_topic_detail(topic_slug: str):
    """Returns detailed topic summary including sample questions."""
    summary = await get_topic_summary(topic_slug)
    if not summary:
        raise HTTPException(404, f"No data for topic: {topic_slug}")
    return summary

# ─── Weekly Digest Endpoint ───────────────────────────────
@router.get("/api/digest/weekly")
async def get_weekly_digest():
    """Returns the weekly cognitive digest data."""
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # This week's activity
    activity = await get_activity_since(week_ago)
    
    # Topic evolution
    evolution = await get_topic_evolution(week_ago)
    
    # Discoveries this week
    discoveries = await get_recent_discoveries(since=week_ago)
    
    return {
        'period': {
            'start': week_ago.isoformat(),
            'end': datetime.utcnow().isoformat(),
        },
        'stats': {
            'interactions': activity['count'],
            'topics_active': activity['unique_topics'],
            'new_topics': activity.get('new_topics', []),
        },
        'evolution': evolution,
        'discoveries': discoveries,
        'health': await get_knowledge_health(),
    }
```

---

## PHASE 5: WIRE UI COMPONENTS INTO DESKTOP APP

### 5A: Add Expertise Badge to Chat Interface

In the desktop app's renderer (likely `desktop-app/src/renderer/` or similar), find where chat responses are rendered and add the expertise indicator.

The UI components were already created as JS files. The integration is:

```javascript
// In the chat response rendering code:

// After receiving a response from the API, fetch expertise context
async function getExpertiseForQuery(query) {
    try {
        const res = await fetch('http://localhost:40080/api/expertise');
        const data = await res.json();
        
        // Simple topic detection (matches backend)
        const queryLower = query.toLowerCase();
        const match = data.profile.find(t => queryLower.includes(t.topic));
        
        if (match) {
            return {
                topic: match.topic,
                level: match.level,
                depth: match.depth,
                emoji: {
                    'expert': '🏗️',
                    'advanced': '🔬', 
                    'intermediate': '🌿',
                    'beginner': '🌱',
                    'first_encounter': '🌱'
                }[match.level]
            };
        }
    } catch (e) {
        console.warn('Expertise fetch failed:', e);
    }
    return null;
}

// Render the badge above the response
function renderExpertiseBadge(expertise) {
    if (!expertise) return '';
    
    const colors = {
        'expert': '#E8A838',
        'advanced': '#5AA86B',
        'intermediate': '#5A8AD8',
        'beginner': '#9B93A8',
        'first_encounter': '#6B6578'
    };
    
    const labels = {
        'expert': `Deep topic · ${expertise.depth} prior sessions`,
        'advanced': `Strong knowledge · ${expertise.depth} interactions`,
        'intermediate': `Building knowledge · ${expertise.depth} interactions`,
        'beginner': `Developing · ${expertise.depth} interactions`,
        'first_encounter': 'New topic for you'
    };
    
    return `
        <div class="expertise-badge" style="
            display: inline-flex; align-items: center; gap: 6px;
            padding: 4px 10px; border-radius: 6px; margin-bottom: 8px;
            background: ${colors[expertise.level]}15;
            border: 1px solid ${colors[expertise.level]}30;
            color: ${colors[expertise.level]};
            font-size: 12px;
        ">
            <span>${expertise.emoji}</span>
            <span>${labels[expertise.level]}</span>
        </div>
    `;
}
```

### 5B: Add Knowledge Dashboard Tab

Add a new tab/view to the desktop app that loads the dashboard data:

```javascript
// Knowledge Dashboard view
async function renderKnowledgeDashboard() {
    const [expertise, health, discoveries] = await Promise.all([
        fetch('http://localhost:40080/api/expertise').then(r => r.json()),
        fetch('http://localhost:40080/api/knowledge-health').then(r => r.json()),
        fetch('http://localhost:40080/api/discoveries').then(r => r.json()),
    ]);
    
    // Render expertise bars
    const barsHtml = expertise.profile.slice(0, 15).map(t => {
        const width = Math.min(t.relative_share * 5, 100); // Scale for visual
        const color = {
            'expert': '#E8A838',
            'advanced': '#5AA86B',
            'intermediate': '#5A8AD8',
            'beginner': '#9B93A8',
        }[t.level] || '#6B6578';
        
        return `
            <div class="topic-bar" style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
                <span style="width: 120px; font-size: 12px; color: #9B93A8; text-align: right;">${t.topic}</span>
                <div style="flex: 1; height: 12px; background: #1E1B24; border-radius: 6px; overflow: hidden;">
                    <div style="width: ${width}%; height: 100%; background: ${color}; border-radius: 6px; transition: width 0.5s;"></div>
                </div>
                <span style="width: 40px; font-size: 11px; color: #6B6578; text-align: right;">${t.relative_share}%</span>
            </div>
        `;
    }).join('');
    
    // Render discoveries
    const discoveriesHtml = discoveries.discoveries.map(d => `
        <div style="padding: 12px; margin: 8px 0; background: #1A1E2E; border: 1px solid #2A3548; border-radius: 8px;">
            <div style="font-size: 12px; font-weight: 600; color: #5A8AD8; margin-bottom: 4px;">⟐ ${d.bridge}</div>
            <div style="font-size: 12px; color: #7B9BC0; line-height: 1.5;">${d.insight}</div>
            <div style="font-size: 11px; color: #5A6678; margin-top: 6px;">${d.session_count} bridging sessions</div>
        </div>
    `).join('');
    
    return `
        <div style="padding: 24px; color: #C4BFD0;">
            <h2 style="font-size: 16px; color: #E8E4F0; margin-bottom: 16px;">Knowledge Profile</h2>
            
            <div style="margin-bottom: 24px;">
                <div style="font-size: 12px; color: #6B6578; margin-bottom: 8px;">
                    ${expertise.total_queries} queries · ${expertise.topic_count} topics
                </div>
                ${barsHtml}
            </div>
            
            <h3 style="font-size: 14px; color: #E8E4F0; margin-bottom: 12px;">Cross-Domain Discoveries</h3>
            ${discoveriesHtml}
            
            <div style="margin-top: 24px; padding: 12px; background: #1E1B24; border-radius: 8px;">
                <div style="font-size: 12px; color: #5AA86B;">
                    ✓ ${health.total_entries} entries · ${health.topics_covered} topics
                </div>
            </div>
        </div>
    `;
}
```

---

## PHASE 6: VALIDATION CHECKLIST

After completing all phases, verify each feature with real data:

### Test 1: Expertise Calibration
```bash
curl http://localhost:40080/api/expertise | python3 -m json.tool
# Verify: llm and python should be "expert", writing should be "intermediate"
# NOT everything as "expert"
```

### Test 2: Schema Context in Chat
```bash
# Expert topic — response should skip basics
curl -X POST http://localhost:40080/api/chat \
  -d '{"query": "Best practices for Python async error handling?"}'

# Beginner topic — response should include fundamentals  
curl -X POST http://localhost:40080/api/chat \
  -d '{"query": "How do I get started with Terraform?"}'

# Check API logs for "USER EXPERTISE CONTEXT" in the system prompt
```

### Test 3: Co-Retrieval Seeded
```bash
curl http://localhost:40080/api/associations/python
# Should return topics frequently co-occurring with python (likely: testing, fastapi, llm)
```

### Test 4: Discoveries Seeded
```bash
curl http://localhost:40080/api/discoveries
# Should return cross-domain insights like "ai ↔ security"
```

### Test 5: Desktop App Dashboard
- Open desktop app
- Navigate to Knowledge tab
- Should see real expertise bars with calibrated levels
- Should see cross-domain discoveries

---

## EXECUTION ORDER

Run these phases in order:

1. **Phase 1** — Fix expertise calibration (30 min)
2. **Phase 2** — Wire schema context into orchestrator (1-2 hours)
3. **Phase 3** — Run all three seeding scripts (1 hour)
4. **Phase 4** — Add API endpoints (1-2 hours)
5. **Phase 5** — Wire UI components (2-3 hours)
6. **Phase 6** — Validate everything (30 min)

**Total estimated time: 6-9 hours of Claude Code work**

After this, every chat response will be expertise-calibrated using real data, the dashboard will show actual knowledge topology, and cross-domain insights will be populated from 4,159 real queries.

---

## TABLE: Database → Cognitive Feature → UI Surface

| Data Source | Records | Cognitive Feature | API Endpoint | UI Surface |
|---|---|---|---|---|
| query_history | 4,159 | Expertise calibration | /api/expertise | Expertise badges in chat |
| topic_extractions | 4,805 | Topic summaries | /api/topic/{slug} | Topic deep dives |
| topic_extractions | 57 topics | Knowledge coverage | /api/expertise | Coverage bars in dashboard |
| query_history (sessions) | ~800 sessions | Co-retrieval graph | /api/associations/{topic} | Constellation graph |
| topic_extractions (cross-domain) | ~10 bridges | Creative discoveries | /api/discoveries | Discovery cards |
| All tables | Combined | Weekly digest | /api/digest/weekly | Weekly digest view |
