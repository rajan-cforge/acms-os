# ACMS Cognitive Architecture Implementation Plan

## Document Overview

**Author:** Claude Code (Architecture Analysis)
**Date:** February 2026
**Status:** Ready for Implementation
**Source:** Architecture of Cognition Reading Series + Codebase Analysis

This document translates cognitive science principles from the reading series into implementable improvements for ACMS. Each component is mapped to specific files, database tables, and tests.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Cognitive Science Foundations](#cognitive-science-foundations)
3. [Current State Analysis](#current-state-analysis)
4. [Implementation Components](#implementation-components)
5. [Sprint Schedule](#sprint-schedule)
6. [Database Migrations](#database-migrations)
7. [New Files](#new-files)
8. [Files to Modify](#files-to-modify)
9. [Deprecations and Removals](#deprecations-and-removals)
10. [UI Components](#ui-components)
11. [Test Requirements](#test-requirements)
12. [Verification Checklist](#verification-checklist)

---

## Executive Summary

### The Core Principle

> **"The highest-value memory systems are not databases. They are reconstruction engines."**
> — Architecture of Cognition, Chapter 2

ACMS already embodies this principle through LLM-based response generation. These improvements extend it deeper into the architecture: selective consolidation, adaptive retrieval, associative pre-loading, cross-domain discovery, and schema-driven context assembly.

### Expected Outcomes

| Metric | Current | Expected | Improvement |
|--------|---------|----------|-------------|
| LLM extraction cost | 100% queries processed | 40-60% processed | 40-60% cost reduction |
| Retrieval latency (unfamiliar topics) | ~300ms | ~220ms | 15-25% faster |
| Knowledge consistency | Unknown | 95%+ validated | Self-healing KB |
| Response calibration | One-size-fits-all | Expertise-aware | Personalized depth |

### Implementation Timeline

```
Week 1-2:   Sprint 1 - Tier 1 Foundations (Triage, Thresholds, Forgetting)
Week 3-4:   Sprint 2 - Preflight and Salience
Week 5-7:   Sprint 3 - Hebbian Learning and Cross-Validation
Week 8-11:  Sprint 4 - Knowledge Compaction and Schema Context
Week 12-13: Sprint 5 - Creative Recombination and UI
```

---

## Cognitive Science Foundations

### Chapter 1: The Memory Palace and the Machine

**Key Insight:** The Greeks discovered that spatial encoding is the brain's native indexing system. ACMS's semantic cache serves the same purpose — creating high-speed retrieval paths to information.

**Three Properties of Effective Memory:**
1. **Context-Sensitive Retrieval** — Return the right data for current context (→ Adaptive Thresholds)
2. **Intelligent Forgetting** — Selective pruning based on importance (→ Consolidation Triage, Propagated Forgetting)
3. **Generative Reconstruction** — Synthesize rather than replay (→ Schema-Driven Context)

### Chapter 2: The Hippocampus as Semantic Cache

**Five-Stage Consolidation Pipeline:**
1. Sensory Buffer (~250ms) → Request intake
2. Working Memory (seconds) → Thread context
3. Hippocampal Encoding (minutes) → Query History + ACMS_Raw_v1
4. Systems Consolidation (days) → Intelligence Pipeline
5. Cortical Storage (lifetime) → ACMS_Knowledge_v2

**Pattern Separation vs. Pattern Completion:**
- Dentate Gyrus: Keep similar things distinct (high threshold)
- CA3: Reconstruct from partial cues (low threshold)
- ACMS: Should dynamically switch based on query intent (→ Adaptive Thresholds)

**Forgetting as Feature:**
- Decay (TTL-based) ✓ Already implemented
- Interference (semantic similarity) ✓ Already implemented
- Active forgetting (explicit deletion) ✓ Partially implemented
- **Missing:** Cascading invalidation (→ Propagated Forgetting)

### Chapter 3: The Extended Mind

**Four Conditions for Cognitive Extension:**
1. Reliability — System must be consistently available
2. Accessibility — Information must be easily retrievable
3. Trust — User must rely on the system
4. Past Endorsement — User participated in encoding

**Design Principle:** The more the user is aware of the interface, the less it functions as a cognitive extension.

### Chapter 4: From Biological to Digital Architecture

**Seven Engineering Patterns:**
1. Write-Ahead Logging → Already in PostgreSQL
2. LSM Trees → Knowledge Compaction Tiers
3. Content-Addressable Memory → Semantic Search
4. Bloom Filters → Preflight Knowledge Check
5. Hebbian Learning → Co-Retrieval Graph
6. Error-Correcting Codes → Cross-Validation
7. Sparse Representations → Embedding Space

### Chapter 5: The Augmented Mind

**Three Eras of Cognitive Technology:**
1. Externalized Storage (3200 BCE — 1945) — Human generates, system stores
2. Augmented Retrieval (1945 — 2022) — Human generates, system stores and retrieves
3. **Augmented Cognition (2022 — present)** — Human and system generate together

**Consolidation Feedback Loop:** Knowledge about what the user knows shapes how new knowledge is generated (→ Schema-Driven Context)

---

## Current State Analysis

### Fixed Thresholds (To Be Made Adaptive)

| File | Line | Current Value | Component |
|------|------|---------------|-----------|
| `src/cache/quality_cache.py` | 221 | 0.95 | Cache similarity |
| `src/storage/dual_memory.py` | 54 | 0.85 | Raw threshold |
| `src/storage/dual_memory.py` | 55 | 0.60 | Knowledge threshold |
| `src/gateway/context_assembler.py` | 17 | 0.60 | Relevance threshold |
| `src/gateway/orchestrator.py` | 1505 | 0.60 | Passthrough gate |

### Missing Cognitive Components

| Component | Status | Impact |
|-----------|--------|--------|
| Consolidation Triage | ❌ Not implemented | All queries get expensive LLM extraction |
| Salience Scoring | ❌ Not implemented | All queries treated equally |
| Preflight Check | ❌ Not implemented | Full retrieval even for unknown topics |
| Co-Retrieval Graph | ❌ Not implemented | No Hebbian associations |
| Cross-Validation | ❌ Not implemented | Raw/Knowledge can diverge silently |
| Knowledge Compaction | ⚠️ Partial (2 levels) | No topic summaries or domain maps |
| Schema-Driven Context | ⚠️ Partial | Insights exist but not injected into prompts |
| Creative Recombination | ⚠️ Within-cluster only | No cross-domain discovery |

### Existing Infrastructure (Good Foundation)

| Component | File | Status |
|-----------|------|--------|
| Topic Extraction | `src/intelligence/topic_extractor.py` | ✅ Working (keyword + LLM) |
| Quality Cache | `src/cache/quality_cache.py` | ✅ Working (0.95 threshold) |
| Insights Engine | `src/intelligence/insights_engine.py` | ✅ Working (within-cluster) |
| Intent Classification | `src/gateway/intent_classifier.py` | ✅ Working (9 intent types) |
| Dual Memory Search | `src/storage/dual_memory.py` | ✅ Working (Raw + Knowledge) |

---

## Implementation Components

### Tier 1: Immediate Improvements (1-3 Days Each)

#### 1.1 Consolidation Triage

**Cognitive Principle:** Hippocampus selectively replays experiences during sleep, prioritizing novel, emotionally significant, and goal-relevant memories.

**Current Problem:** All `query_history` records go through full LLM extraction ($0.10/hour budget). Transient queries ("what time is it?") consume same budget as high-value interactions.

**Solution:**
```python
class ConsolidationPriority(Enum):
    FULL_EXTRACTION = "full"        # Full knowledge extraction with Claude
    LIGHTWEIGHT_TAGGING = "light"   # Keyword-only topic tagging, no LLM
    TRANSIENT = "transient"         # Mark for TTL expiration, skip extraction

class ConsolidationTriager:
    HIGH_VALUE_SIGNALS = {
        "follow_up_detected": 0.15,    # User asked follow-ups
        "long_response": 0.10,          # Response > 500 words
        "code_in_response": 0.10,       # Contains code blocks
        "explicit_positive_feedback": 0.20,  # Thumbs up
        "session_duration_gt_5min": 0.10,    # Extended engagement
        "novel_topic": 0.15,            # Topic not in existing clusters
    }

    TRANSIENT_PATTERNS = [
        r"\b(what time|convert|calculate|translate)\b",
        r"\b(hello|hi|thanks|thank you|goodbye)\b",
        r"^.{0,20}$",  # Very short queries (< 20 chars)
    ]
```

**Integration:** Modify `run_topic_extraction()` in `src/jobs/intelligence_jobs.py` to call `triager.triage()` before processing.

**Expected Impact:** 40-60% reduction in LLM extraction costs.

#### 1.2 Adaptive Similarity Thresholds

**Cognitive Principle:** Hippocampus dynamically switches between pattern separation (high precision) and pattern completion (high recall).

**Current Problem:** Fixed thresholds. "What was the exact kubectl command?" and "What do I know about Kubernetes?" use same thresholds.

**Solution:**
```python
class RetrievalMode(Enum):
    EXACT_RECALL = "exact"          # "What was the command..."
    CONCEPTUAL_EXPLORE = "explore"  # "What do I know about..."
    TROUBLESHOOT = "troubleshoot"   # "Why is X failing..."
    COMPARE = "compare"             # "Difference between X and Y"
    DEFAULT = "default"

THRESHOLD_MAP = {
    RetrievalMode.EXACT_RECALL: {"cache": 0.96, "raw": 0.90, "knowledge": 0.80},
    RetrievalMode.CONCEPTUAL_EXPLORE: {"cache": 0.92, "raw": 0.75, "knowledge": 0.55},
    RetrievalMode.TROUBLESHOOT: {"cache": 0.90, "raw": 0.80, "knowledge": 0.60},
    RetrievalMode.COMPARE: {"cache": 0.94, "raw": 0.82, "knowledge": 0.55},
    RetrievalMode.DEFAULT: {"cache": 0.95, "raw": 0.85, "knowledge": 0.60},
}
```

**Integration:** Create `src/retrieval/threshold_resolver.py`, import in `engine.py` and `orchestrator.py`.

**Expected Impact:** Better recall on exploratory queries, better precision on exact recall.

#### 1.3 Propagated Forgetting

**Cognitive Principle:** Active forgetting (dopamine-mediated hippocampal trace deletion) prevents outdated information from interfering.

**Current Problem:** When cache entry deleted after 3 downvotes, related entries in ACMS_Raw_v1, ACMS_Knowledge_v2 remain untouched. Creates "knowledge zombies."

**Solution:**
```python
async def propagated_forget(deleted_entry: CacheEntry):
    """Flag semantically similar entries for review when entry is actively forgotten."""
    deleted_embedding = await get_embedding(deleted_entry.query_text)

    similar_raw = await weaviate_search("ACMS_Raw_v1", deleted_embedding, 0.85)
    similar_knowledge = await weaviate_search("ACMS_Knowledge_v2", deleted_embedding, 0.80)

    for entry in similar_raw + similar_knowledge:
        await flag_for_review(
            entry_id=entry.id,
            reason=f"Related to actively forgotten entry: {deleted_entry.query_text[:100]}",
            review_priority="medium"
        )
```

**Integration:** Call `propagated_forget()` after `negative_feedback_count > 2` in `quality_cache.py`.

**Expected Impact:** Prevents incorrect information from persisting in one collection after being killed in another.

### Tier 2: Medium-Effort Improvements (1-2 Weeks Each)

#### 2.1 Preflight Knowledge Check

**Cognitive Principle:** "Feeling of knowing" — fast approximate membership test before committing to full retrieval.

**Solution:** Bloom filter for entity membership + cluster centroid distance check.

**Expected Impact:** 15-25% latency reduction on queries about unfamiliar topics.

#### 2.2 Salience Scoring

**Cognitive Principle:** Amygdala modulates encoding strength based on emotional significance.

**Solution:** Score based on engagement signals (follow-ups, session duration), content signals (code, length), feedback, emotional markers.

**Expected Impact:** Knowledge base weighted toward genuinely important interactions.

#### 2.3 Co-Retrieval Graph

**Cognitive Principle:** "Neurons that fire together wire together" — Hebbian learning.

**Solution:** Track which items are retrieved together, build association network, preload associated items.

**Expected Impact:** Richer context assembly without explicit queries.

#### 2.4 Cross-Validation

**Cognitive Principle:** Redundant encoding across modalities for error correction.

**Solution:** Check consistency between Raw and Knowledge collections, flag divergent entries.

**Expected Impact:** Self-healing knowledge base.

### Tier 3: Larger Projects (2-4 Weeks Each)

#### 3.1 Knowledge Compaction Tiers

**Cognitive Principle:** Neocortex extracts abstractions from specific episodes, building schemas.

**Current:** 2 levels (Raw, Knowledge)
**Proposed:** 4 levels (Raw → Knowledge → Topics → Domains)

**Expected Impact:** Dramatically richer context assembly, expertise-calibrated responses.

#### 3.2 Creative Recombination

**Cognitive Principle:** REM sleep recombines patterns, discovering connections between unrelated experiences.

**Solution:** Find unexpected connections across distant topic clusters.

**Expected Impact:** Surfaces non-obvious connections, "aha moments."

#### 3.3 Schema-Driven Context Assembly

**Cognitive Principle:** Consolidated knowledge influences subsequent encoding. Experts encode differently than novices.

**Solution:** Build user cognitive state model, inject into LLM system prompt.

**Expected Impact:** Responses calibrated to actual user expertise, proactive gap-filling.

---

## Sprint Schedule

### Sprint 1: Tier 1 Foundations (Weeks 1-2)

| Day | Task | Files | Tests |
|-----|------|-------|-------|
| 1-2 | ConsolidationTriager class | NEW: `src/intelligence/consolidation_triager.py` | `test_consolidation_triager.py` |
| 3-4 | Integration with intelligence_jobs | MODIFY: `src/jobs/intelligence_jobs.py` | Integration test |
| 5-6 | ThresholdResolver class | NEW: `src/retrieval/threshold_resolver.py` | `test_threshold_resolver.py` |
| 7-8 | Integration with retrieval | MODIFY: `engine.py`, `orchestrator.py` | Integration test |
| 9 | propagated_forget() | MODIFY: `src/cache/quality_cache.py` | `test_propagated_forgetting.py` |
| 10 | Knowledge review CRUD | NEW: `src/storage/knowledge_review_crud.py` | CRUD tests |

### Sprint 2: Preflight and Salience (Weeks 3-4)

| Day | Task | Files | Tests |
|-----|------|-------|-------|
| 1-3 | Bloom filter + preflight | NEW: `src/retrieval/knowledge_preflight.py` | `test_knowledge_preflight.py` |
| 4-5 | Cluster centroid computation | MODIFY: `intelligence_jobs.py` | Integration test |
| 6-8 | SalienceScorer class | NEW: `src/intelligence/salience_scorer.py` | `test_salience_scorer.py` |
| 9-10 | Integration with triage | MODIFY: `consolidation_triager.py` | Integration test |

### Sprint 3: Hebbian Learning and Cross-Validation (Weeks 5-7)

| Day | Task | Files | Tests |
|-----|------|-------|-------|
| 1-5 | CoRetrievalEdge + tracker | NEW: `src/retrieval/coretrieval_graph.py` | `test_coretrieval_graph.py` |
| 6-8 | Associative pre-loading | MODIFY: `src/retrieval/engine.py` | Integration test |
| 9-12 | CrossValidator class | NEW: `src/intelligence/cross_validator.py` | `test_cross_validator.py` |
| 13-15 | Batch consistency job | MODIFY: `intelligence_jobs.py` | Integration test |

### Sprint 4: Knowledge Compaction + Schema Context (Weeks 8-11)

| Day | Task | Files | Tests |
|-----|------|-------|-------|
| 1-5 | ACMS_Topics_v1 collection | Weaviate schema script | Collection test |
| 6-10 | Level 1→2 compaction | NEW: `src/jobs/knowledge_compaction.py` | `test_knowledge_compaction.py` |
| 11-15 | ACMS_Domains_v1 (Level 3) | Weaviate schema script | Collection test |
| 16-20 | Schema-driven context | MODIFY: `context_assembler.py`, `orchestrator.py` | Integration test |

### Sprint 5: Creative Recombination + UI (Weeks 12-13)

| Day | Task | Files | Tests |
|-----|------|-------|-------|
| 1-5 | CreativeRecombinator | NEW: `src/jobs/creative_recombination.py` | `test_creative_recombination.py` |
| 6-8 | Integration with reports | MODIFY: `report_generator.py` | Integration test |
| 9-10 | UI components | NEW: `desktop-app/.../cognitive/` | UI tests |

---

## Database Migrations

### Migration 021: Cognitive Architecture Tables

```sql
-- 1. Knowledge Review Queue (Sprint 1)
CREATE TABLE knowledge_review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id VARCHAR(255) NOT NULL,
    entry_collection VARCHAR(50) NOT NULL,  -- ACMS_Raw_v1, ACMS_Knowledge_v2
    reason TEXT NOT NULL,
    source_deletion_id UUID,
    review_priority VARCHAR(20) DEFAULT 'medium',  -- low, medium, high
    status VARCHAR(20) DEFAULT 'pending',  -- pending, reviewed, dismissed
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_review_status ON knowledge_review_queue(status, created_at);
CREATE INDEX idx_review_priority ON knowledge_review_queue(review_priority, created_at);

-- 2. Salience Scores (Sprint 2)
CREATE TABLE salience_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id UUID NOT NULL REFERENCES query_history(query_id),
    user_id UUID NOT NULL REFERENCES users(user_id),
    score FLOAT NOT NULL CHECK (score >= 0.0 AND score <= 1.0),
    signals_used JSONB NOT NULL DEFAULT '{}',
    context_window_ids UUID[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_salience_query ON salience_scores(query_id);
CREATE INDEX idx_salience_user_score ON salience_scores(user_id, score DESC);

-- 3. Co-Retrieval Edges (Sprint 3)
CREATE TABLE coretrieval_edges (
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

CREATE INDEX idx_coretrieval_item_a ON coretrieval_edges(item_a_id);
CREATE INDEX idx_coretrieval_item_b ON coretrieval_edges(item_b_id);
CREATE INDEX idx_coretrieval_strength ON coretrieval_edges(strength DESC);

-- 4. Cross-Validation Inconsistencies (Sprint 3)
CREATE TABLE cross_validation_inconsistencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_id VARCHAR(255) NOT NULL,
    knowledge_id VARCHAR(255) NOT NULL,
    consistency_score FLOAT NOT NULL,
    raw_date TIMESTAMP WITH TIME ZONE,
    knowledge_date TIMESTAMP WITH TIME ZONE,
    resolution_hint TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_inconsistency_status ON cross_validation_inconsistencies(status, created_at);
```

### Weaviate Collections (Sprint 4)

```python
# scripts/create_topics_v1_schema.py
weaviate_client.collections.create(
    name="ACMS_Topics_v1",
    description="Topic-level knowledge summaries (Level 2 compaction)",
    vectorizer_config=Configure.Vectorizer.none(),
    properties=[
        Property(name="topic_slug", data_type=DataType.TEXT),
        Property(name="summary_text", data_type=DataType.TEXT),
        Property(name="entity_map", data_type=DataType.TEXT),  # JSON
        Property(name="knowledge_depth", data_type=DataType.INT),
        Property(name="knowledge_gaps", data_type=DataType.TEXT_ARRAY),
        Property(name="user_id", data_type=DataType.TEXT),
        Property(name="source_entry_ids", data_type=DataType.TEXT_ARRAY),
        Property(name="last_compacted", data_type=DataType.DATE),
    ]
)

# scripts/create_domains_v1_schema.py
weaviate_client.collections.create(
    name="ACMS_Domains_v1",
    description="Domain-level knowledge topology (Level 3 compaction)",
    vectorizer_config=Configure.Vectorizer.none(),
    properties=[
        Property(name="domain_name", data_type=DataType.TEXT),
        Property(name="topology_json", data_type=DataType.TEXT),
        Property(name="cross_topic_relationships", data_type=DataType.TEXT),
        Property(name="knowledge_strengths", data_type=DataType.TEXT_ARRAY),
        Property(name="knowledge_gaps", data_type=DataType.TEXT_ARRAY),
        Property(name="emerging_themes", data_type=DataType.TEXT_ARRAY),
        Property(name="user_id", data_type=DataType.TEXT),
        Property(name="source_topic_slugs", data_type=DataType.TEXT_ARRAY),
        Property(name="last_compacted", data_type=DataType.DATE),
    ]
)
```

---

## New Files

| Sprint | File | Purpose |
|--------|------|---------|
| 1 | `src/intelligence/consolidation_triager.py` | Triage queries into FULL/LIGHT/TRANSIENT |
| 1 | `src/retrieval/threshold_resolver.py` | Dynamic thresholds by RetrievalMode |
| 1 | `src/storage/knowledge_review_crud.py` | CRUD for review queue |
| 2 | `src/retrieval/knowledge_preflight.py` | Bloom filter + centroid preflight |
| 2 | `src/intelligence/salience_scorer.py` | Engagement-based priority scoring |
| 3 | `src/retrieval/coretrieval_graph.py` | Hebbian association tracking |
| 3 | `src/intelligence/cross_validator.py` | Raw/Knowledge consistency checking |
| 4 | `src/jobs/knowledge_compaction.py` | Level 1→2→3 compaction jobs |
| 4 | `scripts/create_topics_v1_schema.py` | Weaviate ACMS_Topics_v1 |
| 4 | `scripts/create_domains_v1_schema.py` | Weaviate ACMS_Domains_v1 |
| 5 | `src/jobs/creative_recombination.py` | Cross-domain discovery |

---

## Files to Modify

| Sprint | File | Modification |
|--------|------|--------------|
| 1 | `src/jobs/intelligence_jobs.py` | Add triage before extraction |
| 1 | `src/retrieval/engine.py` | Use dynamic thresholds |
| 1 | `src/gateway/orchestrator.py` | Pass intent to retrieval |
| 1 | `src/cache/quality_cache.py` | Add propagated_forget() |
| 1 | `src/storage/dual_memory.py` | Accept threshold params |
| 1 | `src/gateway/context_assembler.py` | Remove fixed threshold |
| 2 | `src/gateway/orchestrator.py` | Insert preflight check |
| 2 | `src/intelligence/consolidation_triager.py` | Integrate salience |
| 3 | `src/retrieval/engine.py` | Track co-retrievals |
| 3 | `src/storage/models.py` | Add CoRetrievalEdge model |
| 4 | `src/gateway/context_assembler.py` | Add schema context |
| 4 | `src/gateway/orchestrator.py` | Inject schema into prompt |
| 5 | `src/intelligence/report_generator.py` | Include discoveries |

---

## Deprecations and Removals

### Code to Deprecate

| Item | Location | Replacement |
|------|----------|-------------|
| `SIMILARITY_THRESHOLD = 0.95` | `quality_cache.py:221` | `THRESHOLD_MAP[mode]["cache"]` |
| `cache_threshold=0.85` | `dual_memory.py:54` | Dynamic from ThresholdResolver |
| `knowledge_threshold=0.60` | `dual_memory.py:55` | Dynamic from ThresholdResolver |
| `RELEVANCE_THRESHOLD = 0.60` | `context_assembler.py:17` | Dynamic from ThresholdResolver |

### Dead Code to Remove (After Sprint 1 Verification)

- Hardcoded threshold constants
- Comments referencing old fixed thresholds
- Any remaining references to deprecated `QueryCache_v1`

---

## UI Components

Based on `reading/ACMS_Cognitive_Architecture_UI_Specification.md`:

### Conversation Stream Enhancements

| Component | Purpose | Visual |
|-----------|---------|--------|
| `consolidation-indicator.js` | Show memory depth | ◆ Deep / ◇ Light / ○ Ephemeral |
| `retrieval-mode-header.js` | Show retrieval mode | 🔍 Exact / 🧠 Explore / 🔧 Debug / ⚖️ Compare |
| `correction-ripple.js` | Show forgetting cascade | "3 related entries flagged" |
| `expertise-indicator.js` | Show user expertise level | 🌱 New / 🌿 Developing / 🔬 Deep / 🏗️ Active |
| `proactive-suggestion.js` | Knowledge gap suggestions | "You might want to explore PKCE" |

### Knowledge Dashboard

| Component | Purpose |
|-----------|---------|
| `knowledge-coverage-map.js` | Bar chart of topic depth |
| `memory-heatmap.js` | GitHub-style activity calendar |
| `knowledge-constellation.js` | D3 force-directed graph of associations |
| `consistency-alerts.js` | Review queue for flagged items |

### Topic and Domain Views

| Component | Purpose |
|-----------|---------|
| `topic-deep-dive.js` | Topic summary with gaps and timeline |
| `domain-map.js` | Cross-topic relationship topology |
| `cross-domain-discovery.js` | Insight cards for discoveries |

### Weekly Digest

| Component | Purpose |
|-----------|---------|
| `weekly-digest.js` | Full weekly cognitive summary |

---

## Test Requirements

### Unit Tests

```
tests/unit/intelligence/test_consolidation_triager.py
tests/unit/intelligence/test_salience_scorer.py
tests/unit/intelligence/test_cross_validator.py
tests/unit/retrieval/test_threshold_resolver.py
tests/unit/retrieval/test_knowledge_preflight.py
tests/unit/retrieval/test_coretrieval_graph.py
tests/unit/cache/test_propagated_forgetting.py
tests/unit/jobs/test_knowledge_compaction.py
tests/unit/jobs/test_creative_recombination.py
```

### Integration Tests

```
tests/integration/test_consolidation_pipeline.py
tests/integration/test_adaptive_retrieval.py
tests/integration/test_coretrieval_learning.py
tests/integration/test_knowledge_compaction_e2e.py
tests/integration/test_schema_driven_context.py
```

---

## Verification Checklist

### Sprint 1
- [ ] LLM extraction costs reduced (compare before/after weekly spend)
- [ ] Transient queries correctly identified and skipped
- [ ] Adaptive thresholds active (verify different modes produce different thresholds)
- [ ] Propagated forgetting flags related entries

### Sprint 2
- [ ] Preflight reduces latency on unfamiliar topics
- [ ] Salience scores computed and stored
- [ ] High-salience entries get priority in consolidation

### Sprint 3
- [ ] Co-retrieval edges accumulate over sessions
- [ ] Associated items appear in context (preloading works)
- [ ] Cross-validation detects inconsistencies

### Sprint 4
- [ ] Topic summaries generated for major clusters
- [ ] Domain maps show cross-topic relationships
- [ ] Schema context appears in LLM prompts
- [ ] Responses calibrated to user expertise

### Sprint 5
- [ ] Cross-domain discoveries in weekly digest
- [ ] UI components render correctly
- [ ] User can confirm/dismiss discoveries

---

## Appendix: Cognitive Principle Mapping

| Improvement | Cognitive Principle | Brain Region/Function |
|-------------|--------------------|-----------------------|
| Consolidation Triage | Selective hippocampal replay | Hippocampus |
| Adaptive Thresholds | Pattern separation vs completion | Dentate Gyrus / CA3 |
| Propagated Forgetting | Active forgetting cascade | Dopamine-mediated trace deletion |
| Preflight Check | Feeling of knowing | Familiarity signal |
| Salience Scoring | Emotional priority queue | Amygdala modulation |
| Co-Retrieval Graph | Hebbian learning | Synaptic plasticity |
| Cross-Validation | Error-correcting codes | Redundant encoding |
| Knowledge Compaction | Schema formation | Neocortical abstraction |
| Creative Recombination | REM sleep pattern mixing | Hippocampal-cortical dialogue |
| Schema-Driven Context | Expertise-driven encoding | Top-down modulation |

---

## References

1. Foer, Joshua. *Moonwalking with Einstein.* 2011.
2. Yates, Frances A. *The Art of Memory.* 1966.
3. Loftus, Elizabeth F. *Eyewitness Testimony.* 1979.
4. Clark, Andy and David Chalmers. "The Extended Mind." 1998.
5. Bjork, Robert A. "A New Theory of Disuse." 1992.
6. Bush, Vannevar. "As We May Think." 1945.
7. Hawkins, Jeff. *A Thousand Brains.* 2021.

---

*"The palace is ancient. The engineering challenge is eternal. The opportunity is unprecedented. Build the palace well."*
