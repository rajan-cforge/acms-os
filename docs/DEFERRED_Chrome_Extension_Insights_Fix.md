# DEFERRED: Chrome Extension → Insights Data Flow Fix

**Status**: DEFERRED (Prioritizing ChatGPT History Ingestion first)
**Created**: December 14, 2025
**Priority**: P1 (after ChatGPT ingestion)
**Estimated Effort**: 2.5 hours

---

## Why This Plan Exists

### The Problem

Chrome extension captures (95K+ memories) are **invisible** to Insights/Reports:

```
CURRENT STATE (Broken):
┌────────────────────────────────────────────────────────────────────────┐
│  Chrome Extensions → memory_items (95,128) ──X──> [NOT CONNECTED]      │
│  Desktop Chat → query_history (389) ──────────────> InsightsEngine     │
└────────────────────────────────────────────────────────────────────────┘

Result: InsightsEngine only sees 0.4% of your data (389 out of 95,517 items)
```

### Root Cause

InsightsEngine SQL queries only JOIN `topic_extractions` to `query_history`, completely missing the `memory_items` table where Chrome extension captures are stored.

```sql
-- Current query pattern (misses 99.6% of data)
SELECT ... FROM topic_extractions te
JOIN query_history qh ON te.source_id = qh.query_id::text
WHERE te.source_type = 'query_history'  -- Only this type!
```

### Why It Matters

1. **95K captured memories** from ChatGPT, Claude, Gemini conversations are not analyzed
2. **Insights are incomplete** - only showing desktop chat patterns
3. **Reports undercount activity** - missing extension captures entirely
4. **Topics are skewed** - only representing a tiny slice of actual usage

---

## The Solution

```
FIXED STATE:
┌────────────────────────────────────────────────────────────────────────┐
│  Chrome Extensions → memory_items ─────┐                               │
│                                        ├──> topic_extractions ──> Insights
│  Desktop Chat → query_history ─────────┘                               │
└────────────────────────────────────────────────────────────────────────┘
```

### Implementation Phases

#### Phase 1: Implement Topic Extraction DB Functions (P0 - Blocking)
**File**: `src/intelligence/topic_extractor.py`
**Lines**: 552-587

The `_get_cached_extraction()` and `_save_extraction()` methods are TODO placeholders:

```python
# Current state - BROKEN
async def _get_cached_extraction(...) -> Optional[Dict[str, Any]]:
    # TODO: Implement actual DB lookup
    return None  # Always cache miss!

async def _save_extraction(...) -> None:
    # TODO: Implement actual DB upsert
    pass  # Never saves!
```

**Why**: Without these, topic extractions are never persisted. Every extraction is recalculated and lost.

**Implementation**:
```python
async def _get_cached_extraction(
    self, tenant_id: str, source_type: str, source_id: str
) -> Optional[Dict[str, Any]]:
    result = await self.db.execute(text("""
        SELECT id, topics, primary_topic, extraction_method,
               extractor_version, confidence, tokens_used, created_at
        FROM topic_extractions
        WHERE tenant_id = :tenant_id
          AND source_type = :source_type
          AND source_id = :source_id
          AND extractor_version = :version
    """), {...})
    row = result.fetchone()
    return dict(row._mapping) if row else None

async def _save_extraction(...) -> None:
    await self.db.execute(text("""
        INSERT INTO topic_extractions (...)
        VALUES (...)
        ON CONFLICT (tenant_id, source_type, source_id, extractor_version)
        DO UPDATE SET topics = EXCLUDED.topics, ...
    """), {...})
    await self.db.commit()
```

---

#### Phase 2: Batch Topic Extraction Script
**File**: `scripts/batch_extract_memory_topics.py` (new)

**Why**: 95K memories need topic extraction. Can't do this on-demand - need batch processing.

```python
async def batch_extract_memory_topics(user_id: str, batch_size: int = 100):
    """Extract topics from all memory_items for a user."""

    # Get memories without topic extractions
    memories = await session.execute(text("""
        SELECT m.memory_id, m.content, m.user_id, m.tags
        FROM memory_items m
        LEFT JOIN topic_extractions te
            ON te.source_type = 'memory_items'
            AND te.source_id = m.memory_id::text
        WHERE m.user_id = :user_id
          AND te.id IS NULL  -- Not yet extracted
    """))

    # Process in batches using keyword extraction (free, fast)
    for batch in batches(memories, batch_size):
        await extractor.batch_extract(items=batch, budget_usd=0.05)
```

**Cost**: Keyword extraction is FREE (no LLM calls). ~440 memories/second.

---

#### Phase 3: Modify InsightsEngine Queries
**File**: `src/intelligence/insights_engine.py`

**Why**: InsightsEngine needs to see both `query_history` AND `memory_items`.

**Key Changes**:

1. `_get_key_stats()` - Add `memories_captured` stat
2. `_get_sample_queries_for_topic()` - UNION with memory_items
3. `_get_queries_for_topic()` - UNION with memory_items

```sql
-- Pattern: UNION query_history with memory_items
SELECT qh.question, 'query' as source_type FROM query_history qh
JOIN topic_extractions te ON te.source_id = qh.query_id::text
WHERE te.source_type = 'query_history' AND te.primary_topic = :topic

UNION ALL

SELECT LEFT(m.content, 200), 'memory' as source_type FROM memory_items m
JOIN topic_extractions te ON te.source_id = m.memory_id::text
WHERE te.source_type = 'memory_items' AND te.primary_topic = :topic
```

---

#### Phase 4: Update ReportGenerator
**File**: `src/intelligence/report_generator.py`

**Why**: Reports should show memory capture stats and extension breakdown.

**Changes**:
- Add `memories_captured` to KnowledgeGrowth
- Add `extension_sources` breakdown (ChatGPT, Claude, Gemini counts)
- Update markdown template to show these stats

---

#### Phase 5: Integration Tests
**File**: `tests/integration/test_memory_insights_integration.py` (new)

**Why**: Ensure the fix works end-to-end.

```python
async def test_memory_topics_appear_in_insights(db_session):
    # Create memory + extract topics
    memory_id = await create_memory(content="Python is great for ML")
    await extractor.extract_topics_idempotent(source_type="memory_items", ...)

    # Generate insights
    summary = await engine.generate_summary(user_id=TEST_USER_ID)

    # Verify memory-based topics appear
    assert "python" in [t.topic for t in summary.top_topics]
```

---

## Non-Negotiable Invariants

| # | Invariant | Why |
|---|-----------|-----|
| 1 | **RBAC at query time** | User can only see their own data |
| 2 | **Privacy levels respected** | No CONFIDENTIAL/LOCAL_ONLY leaks |
| 3 | **Idempotent extractions** | Same input → same output, no duplicates |
| 4 | **Cost-guarded LLM** | Budget caps on batch extraction |
| 5 | **Trace ID everywhere** | Debugging and audit trail |

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `src/intelligence/topic_extractor.py` | Implement DB functions | P0 |
| `scripts/batch_extract_memory_topics.py` | New batch script | P0 |
| `src/intelligence/insights_engine.py` | UNION queries | P0 |
| `src/intelligence/report_generator.py` | Memory stats | P1 |
| `tests/integration/test_memory_insights_integration.py` | Tests | P1 |

---

## Validation Checklist

After implementation:
- [ ] `topic_extractions` has entries with `source_type='memory_items'`
- [ ] `/api/v2/insights/summary` shows memory-based topics
- [ ] `/api/v2/insights/analyze` includes memory content
- [ ] Reports show "Memories Captured" stat
- [ ] Privacy filtering works (no CONFIDENTIAL in results)
- [ ] All tests pass

---

## Why Deferred?

**ChatGPT History Ingestion** is prioritized because:
1. It's the primary data source for most users
2. Once ingested, this same fix will make that data visible too
3. The spec explicitly says "Build history ingestion first"

This plan will be executed after ChatGPT ingestion is complete.

---

*Document created: December 14, 2025*
