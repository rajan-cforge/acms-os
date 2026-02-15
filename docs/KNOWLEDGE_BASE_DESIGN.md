# ACMS Knowledge Base Design

**Date**: December 16, 2025
**Status**: DRAFT - For Review

---

## Vision

Transform ACMS from a "fact extractor" into an **Intelligent Knowledge Base** that captures:
- **WHAT**: The query and answer content
- **MEANING**: What concepts/topics are involved, relationships between them
- **WHY**: User intent, learning journey, context signals

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE EXTRACTION PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Query ──────┐                                                          │
│                   │                                                          │
│                   ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 1: INTENT UNDERSTANDING (Claude Sonnet)                      │    │
│  │  ────────────────────────────────────────────────────────────────── │    │
│  │  • What is the user trying to learn/do?                             │    │
│  │  • What problem are they solving?                                   │    │
│  │  • What's their likely context/background?                          │    │
│  │                                                                      │    │
│  │  Output: IntentAnalysis {                                           │    │
│  │    primary_intent: "Learn OAuth2 implementation"                    │    │
│  │    problem_domain: "API Security"                                   │    │
│  │    user_context: "Building production web service"                  │    │
│  │    confidence: 0.85                                                 │    │
│  │  }                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                   │                                                          │
│                   ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2: ENTITY & CONCEPT EXTRACTION                               │    │
│  │  ────────────────────────────────────────────────────────────────── │    │
│  │  From Query + Answer, extract:                                      │    │
│  │  • Named entities (technologies, frameworks, concepts)              │    │
│  │  • Relationships between entities                                   │    │
│  │  • Topic classification                                             │    │
│  │                                                                      │    │
│  │  Output: Entities[] {                                               │    │
│  │    { name: "OAuth2", type: "protocol", canonical: "oauth2" }        │    │
│  │    { name: "FastAPI", type: "framework", canonical: "fastapi" }     │    │
│  │    { name: "JWT", type: "technology", canonical: "jwt" }            │    │
│  │  }                                                                  │    │
│  │  Relations[] {                                                      │    │
│  │    { from: "OAuth2", to: "JWT", type: "USES" }                      │    │
│  │    { from: "FastAPI", to: "OAuth2", type: "IMPLEMENTS" }            │    │
│  │  }                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                   │                                                          │
│                   ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 3: KNOWLEDGE SYNTHESIS                                       │    │
│  │  ────────────────────────────────────────────────────────────────── │    │
│  │  Combine into structured knowledge entry:                           │    │
│  │  • Canonical Q&A pair (cleaned, normalized)                         │    │
│  │  • Topic cluster assignment                                         │    │
│  │  • "Why" context summary                                            │    │
│  │  • Key learnings/facts                                              │    │
│  │                                                                      │    │
│  │  Output: KnowledgeEntry {                                           │    │
│  │    canonical_query: "How to implement OAuth2 in FastAPI?"           │    │
│  │    answer_summary: "Use OAuth2PasswordBearer with JWT tokens..."    │    │
│  │    why_context: "User is building secure API authentication"        │    │
│  │    topic_cluster: "api-security"                                    │    │
│  │    entities: [...],                                                 │    │
│  │    relations: [...],                                                │    │
│  │    key_facts: [                                                     │    │
│  │      "OAuth2PasswordBearer is FastAPI's built-in OAuth2 class",     │    │
│  │      "JWT tokens should use RS256 for production"                   │    │
│  │    ]                                                                │    │
│  │  }                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### ACMS_Knowledge_v2 Collection (Weaviate)

```python
schema = {
    "class": "ACMS_Knowledge_v2",
    "description": "Structured knowledge entries with intent and relationships",
    "vectorizer": "none",  # We generate embeddings
    "properties": [
        # Core Content
        {"name": "canonical_query", "dataType": ["text"]},      # Normalized question
        {"name": "answer_summary", "dataType": ["text"]},       # Condensed answer
        {"name": "full_answer", "dataType": ["text"]},          # Complete answer for reference

        # Intent & Context (THE "WHY")
        {"name": "primary_intent", "dataType": ["text"]},       # What user wants to achieve
        {"name": "problem_domain", "dataType": ["text"]},       # Area of problem
        {"name": "why_context", "dataType": ["text"]},          # Human-readable "why" summary
        {"name": "user_context_signals", "dataType": ["text[]"]}, # Inferred context clues

        # Entities & Relationships
        {"name": "entities", "dataType": ["text[]"]},           # JSON array of entities
        {"name": "relations", "dataType": ["text[]"]},          # JSON array of relations
        {"name": "topic_cluster", "dataType": ["text"]},        # Primary topic cluster
        {"name": "related_topics", "dataType": ["text[]"]},     # Related topic clusters

        # Extracted Facts
        {"name": "key_facts", "dataType": ["text[]"]},          # Atomic facts from answer

        # Metadata
        {"name": "user_id", "dataType": ["text"]},
        {"name": "source_query_id", "dataType": ["text"]},      # Link to original Q&A
        {"name": "extraction_model", "dataType": ["text"]},     # claude-sonnet-4 or claude-opus-4-5
        {"name": "extraction_confidence", "dataType": ["number"]},
        {"name": "created_at", "dataType": ["date"]},
        {"name": "usage_count", "dataType": ["int"]},           # How often retrieved
        {"name": "feedback_score", "dataType": ["number"]},     # User feedback
    ]
}
```

### Topic Clusters Table (PostgreSQL)

```sql
CREATE TABLE topic_clusters (
    cluster_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,           -- e.g., "api-security"
    display_name TEXT NOT NULL,          -- e.g., "API Security"
    description TEXT,
    parent_cluster_id UUID REFERENCES topic_clusters(cluster_id),
    query_count INT DEFAULT 0,           -- Number of queries in this cluster
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example clusters
INSERT INTO topic_clusters (name, display_name, description) VALUES
('python-development', 'Python Development', 'Python programming and ecosystem'),
('api-security', 'API Security', 'Authentication, authorization, and API protection'),
('machine-learning', 'Machine Learning', 'ML algorithms, training, and deployment'),
('database-design', 'Database Design', 'SQL, NoSQL, and data modeling');
```

### Entity Graph Table (PostgreSQL)

```sql
CREATE TABLE knowledge_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT NOT NULL,        -- e.g., "fastapi"
    display_name TEXT NOT NULL,          -- e.g., "FastAPI"
    entity_type TEXT NOT NULL,           -- framework, language, concept, tool
    description TEXT,
    mention_count INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE entity_relations (
    relation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_entity_id UUID REFERENCES knowledge_entities(entity_id),
    to_entity_id UUID REFERENCES knowledge_entities(entity_id),
    relation_type TEXT NOT NULL,         -- USES, IMPLEMENTS, PART_OF, RELATED_TO
    strength FLOAT DEFAULT 1.0,          -- How strong is this relation
    occurrence_count INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Extraction Prompt (Claude Sonnet)

```python
KNOWLEDGE_EXTRACTION_PROMPT = """You are a knowledge extraction system for a developer's personal knowledge base.

Analyze this Q&A interaction and extract structured knowledge.

## Query
{query}

## Answer
{answer}

## Your Task

Extract the following in JSON format:

```json
{
  "intent_analysis": {
    "primary_intent": "What is the user fundamentally trying to learn or accomplish?",
    "problem_domain": "What area/field does this relate to?",
    "why_context": "A 1-2 sentence explanation of WHY the user is asking this - what's their likely goal or situation?",
    "user_context_signals": ["List of inferred context clues about the user"]
  },
  "entities": [
    {
      "name": "Entity name as mentioned",
      "canonical": "Normalized lowercase version",
      "type": "framework|language|concept|tool|protocol|library",
      "importance": "primary|secondary|mentioned"
    }
  ],
  "relations": [
    {
      "from": "entity canonical name",
      "to": "entity canonical name",
      "type": "USES|IMPLEMENTS|PART_OF|ALTERNATIVE_TO|REQUIRES|PRODUCES"
    }
  ],
  "topic_cluster": "A descriptive slug for the primary topic (e.g., 'api-authentication', 'python-async-patterns', 'react-state-management')",
  "related_topics": ["Other relevant clusters"],
  "key_facts": [
    "Standalone factual statements extracted from the answer (max 5)",
    "Each should be self-contained and useful out of context"
  ],
  "canonical_query": "A cleaned, normalized version of the question",
  "answer_summary": "A 2-3 sentence summary of the key points in the answer"
}
```

Rules:
1. The "why_context" should explain the user's situation, not just restate the question
2. Entity names should be normalized (e.g., "React.js" → "react", "Python 3" → "python")
3. Only extract facts that are genuinely useful to remember long-term
4. If the query is trivial/greeting/meta, return minimal extraction with low confidence
"""
```

---

## UI Integration: "Why" Thinking Step

Add a new thinking step in the gateway response:

```python
yield create_step_event(
    "knowledge_understanding",  # NEW STEP
    f"Understanding context: {why_context[:80]}...",
    {
        "output": {
            "why_context": why_context,
            "primary_intent": primary_intent,
            "problem_domain": problem_domain,
            "topic_cluster": topic_cluster,
            "entities_found": len(entities),
            "confidence": extraction_confidence
        }
    }
)
```

**Desktop UI Display:**
```
┌─────────────────────────────────────────────────────────────────┐
│ 🧠 Understanding Context                                         │
├─────────────────────────────────────────────────────────────────┤
│ WHY: User is building secure API authentication for a           │
│      production web service and needs to understand             │
│      OAuth2 implementation patterns in FastAPI.                 │
│                                                                  │
│ Domain: API Security                                             │
│ Topics: api-security, python-development                        │
│ Key Concepts: OAuth2, JWT, FastAPI, Authentication             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cost Analysis

**Model Options:**
- **Claude Sonnet 4** (`claude-sonnet-4-20250514`) - Recommended for extraction
- **Claude Opus 4.5** (`claude-opus-4-5-20251101`) - Premium option for complex analysis

**Claude Sonnet 4 Pricing** (as of Dec 2025):
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

**Per Query Extraction Cost:**
- Avg input: ~2000 tokens (query + answer + prompt)
- Avg output: ~500 tokens (structured JSON)
- Cost: (2000 × $3 + 500 × $15) / 1M = $0.0135 per extraction

**Monthly Cost Estimate:**
- 1000 queries/day × 30 days = 30,000 extractions
- 30,000 × $0.0135 = **$405/month**

**Optimization Options:**
1. Only extract for "significant" queries (>100 char answer)
2. Use Gemini 2.0 Flash for simple queries (~$0.001 per extraction)
3. Batch extraction during off-peak hours
4. Cache similar queries to avoid duplicate extraction

---

## Implementation Plan

### Phase 1: Core Extraction (Week 1)
- [ ] Create ACMS_Knowledge_v2 schema in Weaviate
- [ ] Implement KnowledgeExtractor class using Claude Sonnet
- [ ] Add extraction to orchestrator pipeline
- [ ] Store to new collection

### Phase 2: UI Integration (Week 1-2)
- [ ] Add "knowledge_understanding" thinking step
- [ ] Display "why" context in desktop UI
- [ ] Add feedback mechanism for "why" accuracy

### Phase 3: Entity Graph (Week 2-3)
- [ ] Create PostgreSQL tables for entities/relations
- [ ] Build entity disambiguation (merge duplicates)
- [ ] Create topic cluster hierarchy

### Phase 4: Search Integration (Week 3-4)
- [ ] Use topic clusters to improve search relevance
- [ ] Show "why" context when retrieving past knowledge
- [ ] Build entity-based navigation

---

## Design Decisions (Dec 16, 2025)

| Question | Decision |
|----------|----------|
| **Extraction Trigger** | Every query (no filtering) |
| **Topic Clusters** | Dynamic discovery by model (no fixed set) |
| **Historical Backfill** | Yes - run on 101K existing Q&As as validation test |
| **Cost Threshold** | ~$405/month acceptable |

## Open Questions (Remaining)

1. **User Feedback Loop**: How do we let users correct the "why"?
2. **Multi-user**: How do entity graphs work across users?

---

## Sources

- [Neo4j: Unstructured Text to Knowledge Graph](https://neo4j.com/blog/developer/unstructured-text-to-knowledge-graph/)
- [Mastering Knowledge Graph Construction with AI and LLMs](https://sparkco.ai/blog/mastering-knowledge-graph-construction-with-ai-and-llms)
- [Build and Query Knowledge Graphs with LLMs](https://towardsdatascience.com/build-query-knowledge-graphs-with-llms/)
- [NVIDIA: LLM-Driven Knowledge Graphs](https://developer.nvidia.com/blog/insights-techniques-and-evaluation-for-llm-driven-knowledge-graphs/)
