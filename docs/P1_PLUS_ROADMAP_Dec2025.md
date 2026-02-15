# P1+ Roadmap: ACMS Intelligence Platform Expansion

**Created**: December 14, 2025
**Source**: `ACMS_Insights_and_AI_Governance_Spec.md` + Analysis Session
**Status**: Planning Phase

---

## Executive Summary

ACMS is evolving from "chat with memory" into an **Organizational Intelligence Platform**. This roadmap covers the next phase of development after completing P0 (RBAC audit + Conversation Continuity).

---

## Current State vs. Target State

```
CURRENT STATE (December 2025):
┌─────────────────────────────────────────────────────────────────────────────┐
│  Desktop Chat ──────────> query_history (389) ──────> InsightsEngine       │
│  Chrome Extensions ─────> memory_items (95K) ──X──> [NOT CONNECTED]        │
│  ChatGPT Export ────────> ??? (not imported) ──X──> [NOT AVAILABLE]        │
└─────────────────────────────────────────────────────────────────────────────┘

TARGET STATE:
┌─────────────────────────────────────────────────────────────────────────────┐
│  Desktop Chat ──────────> query_history ─────┐                              │
│  Chrome Extensions ─────> memory_items ──────┼──> topic_extractions ──┐    │
│  ChatGPT Export ────────> conversations ─────┘                        │    │
│                                                                       ▼    │
│                                              ┌──────────────────────────┐  │
│                                              │ Unified Intelligence     │  │
│                                              │ - Insights Engine        │  │
│                                              │ - Report Generator       │  │
│                                              │ - AI Governance (future) │  │
│                                              └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What Already Exists vs. Gaps

| Component | Exists? | What Works | Gap |
|-----------|---------|------------|-----|
| `ChatGPTHistoryImporter` | ✅ Yes | Parsing ChatGPT export format | Topic extraction not running on imported data |
| `InsightsEngine` | ✅ Yes | Generates insights from query_history | Only reads query_history, misses 95K memory_items |
| `TopicExtractor` | ✅ Yes | Keyword + LLM extraction methods | DB save functions are TODO placeholders |
| `ReportGenerator` | ✅ Yes | Weekly/monthly report generation | Missing `memories_captured` stat, extension breakdown |
| AI Governance | ❌ No | N/A | Future enterprise feature |

---

## Priority Order (From Spec)

The spec (`ACMS_Insights_and_AI_Governance_Spec.md`) explicitly states:

> **"Build history ingestion first."**

### Execution Order:

1. **ChatGPT History Ingestion** ← START HERE
2. **Insights v2** (memory_items integration)
3. **Reports v2** (memory stats)
4. **AI Governance Dashboards** (future)

---

## Phase 1: ChatGPT History Ingestion (PRIORITY)

### Why This First?

1. **High-Signal Data**: ChatGPT history is rich, long-horizon data
2. **User Request**: Direct ask to import existing conversations
3. **Foundation**: Same pipeline will work for Claude/Gemini exports
4. **Spec Mandate**: "Build history ingestion first"

### Design Questions (Need Brainstorming)

| Question | Options | Decision |
|----------|---------|----------|
| What is "raw Q&A"? | Imported conversations stored as-is | TBD |
| What becomes "memory"? | Promoted facts/insights | TBD |
| Auto-promote to knowledge? | NEVER (per spec) | ✅ Decided |
| How to handle topics? | Extract on import vs. batch later | TBD |

### Key Rule from Spec:

> **"ChatGPT history is always RAW. Never auto-promoted to knowledge."**

### Data Flow:

```
ChatGPT Export (JSON)
       │
       ▼
┌─────────────────────────────────────────┐
│ ChatGPTHistoryImporter.parse_export()   │
│ - Parse conversations.json              │
│ - Extract messages, timestamps          │
│ - Identify Q&A pairs                    │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ Store in DB                             │
│ - conversations table (metadata)        │
│ - conversation_turns table (messages)   │
│ - Status: RAW (never auto-promoted)     │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ TopicExtractor.batch_extract()          │
│ - Extract topics from conversations     │
│ - Store in topic_extractions            │
│ - Link source_type='chatgpt_import'     │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ InsightsEngine + ReportGenerator        │
│ - Query topic_extractions               │
│ - Include chatgpt_import in analysis    │
│ - Generate insights/reports             │
└─────────────────────────────────────────┘
```

### Files Involved:

| File | Purpose | Status |
|------|---------|--------|
| `src/importers/chatgpt_importer.py` | Parse ChatGPT export | Exists (needs review) |
| `src/storage/conversation_crud.py` | Store imported conversations | May need updates |
| `src/intelligence/topic_extractor.py` | Extract topics | DB functions TODO |
| API endpoint for upload | `POST /import/chatgpt` | Needs implementation |

---

## Phase 2: Chrome Extension → Insights Fix

**Status**: DEFERRED (documented in `docs/DEFERRED_Chrome_Extension_Insights_Fix.md`)

### Why Deferred?

Once ChatGPT ingestion works, the same topic_extractions pipeline will:
1. Already have working DB save functions (fixed in Phase 1)
2. Already have InsightsEngine UNION queries (fixed in Phase 1)
3. Just need batch extraction for existing 95K memories

### Summary of Fix:

1. Implement `_get_cached_extraction()` and `_save_extraction()` in TopicExtractor
2. Create batch extraction script for memory_items
3. Modify InsightsEngine queries to UNION memory_items
4. Update ReportGenerator with memory stats

**Detailed plan**: See `docs/DEFERRED_Chrome_Extension_Insights_Fix.md`

---

## Phase 3: Insights v2 Enhancements

### From Spec - Invariants:

| Invariant | Enforcement |
|-----------|-------------|
| Evidence required | Every insight linked to source data |
| Confidence scored | 0.0-1.0 confidence on all insights |
| RBAC enforced | User can only see their own data |

### Schema Enhancement:

```sql
CREATE TABLE insight_events (
  insight_id UUID PRIMARY KEY,
  tenant_id TEXT,
  scope TEXT,              -- 'user' or 'org'
  user_id TEXT,
  title TEXT,
  summary TEXT,
  evidence_ids JSONB,      -- Links to source data
  metrics JSONB,
  confidence REAL,         -- 0.0 to 1.0
  created_at TIMESTAMPTZ
);
```

### New Insight Types:

- **Emerging Theme**: Topic trending up over time
- **Knowledge Gap**: Frequently asked but poorly answered
- **Pattern Detection**: Recurring question patterns
- **Cross-Source Synthesis**: Insights spanning multiple AI tools

---

## Phase 4: Reports v2

### From Spec:

- **Weekly Personal Reports**: Individual user activity
- **Monthly Executive Reports**: Organization-wide patterns (admin only)
- **Evidence-Backed**: Every claim linked to source

### Enhancements Needed:

1. Add `memories_captured` stat (currently missing)
2. Add `extension_sources` breakdown (ChatGPT, Claude, Gemini counts)
3. Add ChatGPT import stats when available
4. Cross-source synthesis section

---

## Phase 5: AI Governance (Future)

### From Spec - Four Pillars:

| Pillar | Description |
|--------|-------------|
| **Inventory** | AI apps, agents, MCP servers, extensions |
| **Access & Data Flow** | Permissions, integrations, data shared |
| **Usage, Risk & Value** | Cost, cache hits, PII blocks, ROI |
| **Policy Compliance** | Automated policy checks |

### Dashboards:

1. AI Inventory Dashboard
2. Data Flow & Risk Dashboard
3. Cost & Value Dashboard
4. Policy Compliance Dashboard

**Status**: Future roadmap - enterprise feature

---

## Testing Strategy (From Spec)

### Unit Tests:
- Importer parsing (all edge cases)
- Insight evidence enforcement
- Topic extraction accuracy

### Integration Tests:
- Import → topics → insights → reports
- RBAC enforced at every step
- Cross-source queries work

---

## Non-Negotiable Invariants (All Phases)

| # | Invariant | Enforcement |
|---|-----------|-------------|
| 1 | **RBAC at query time** | `user_id` filter in ALL queries |
| 2 | **Privacy levels respected** | `privacy_level IN ('PUBLIC', 'INTERNAL')` for non-admin |
| 3 | **Idempotent operations** | UNIQUE constraints, ON CONFLICT handlers |
| 4 | **Cost-guarded LLM** | Budget caps on all LLM operations |
| 5 | **Trace ID everywhere** | All DB writes include `trace_id` |
| 6 | **RAW never auto-promoted** | ChatGPT imports stay RAW until explicit user action |

---

## Next Action

**START WITH**: ChatGPT History Ingestion

Questions to resolve in brainstorming:
1. What format is the ChatGPT export?
2. What tables store the imported data?
3. What becomes "raw Q&A" vs "memory"?
4. How do topics flow to insights?
5. API endpoint design for upload

---

*Document created: December 14, 2025*
*Based on: ACMS_Insights_and_AI_Governance_Spec.md + P1+ Analysis Session*
