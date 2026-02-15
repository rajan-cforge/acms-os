# ACMS Technology Stack - Actual Implementation

**Last Updated:** December 21, 2025
**Status:** Current Production State (verified against code)
**See Also:** [ACMS_ARCHITECTURE_2025.md](../ACMS_ARCHITECTURE_2025.md) - Master architecture reference

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ACMS SYSTEM ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT SOURCES                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Desktop App  │  │ Chrome Ext   │  │ Claude Imp   │  │ ChatGPT Imp  │    │
│  │  (Electron)  │  │ (97K mems)   │  │              │  │ (3.5K Q&As)  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
│         ▼                 ▼                 ▼                 ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI SERVER (port 40080)                      │   │
│  │  /gateway/chat  │  /memories  │  /api/import/*  │  /api/v2/*        │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                        │
│                                   ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        CORE SERVICES                                │   │
│  │                                                                     │   │
│  │  GatewayOrchestrator ─────▶ AgentSelector ─────▶ Agents            │   │
│  │         │                         │             (Claude/GPT/Gemini) │   │
│  │         │                         │                                 │   │
│  │         ├── IntentClassifier      ├── FactExtractor (GPT-3.5)      │   │
│  │         ├── SearchDetector        │                                 │   │
│  │         ├── PreflightGate         │                                 │   │
│  │         └── ContextAssembler      │                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                        │
│                                   ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          DATA STORES                                │   │
│  │                                                                     │   │
│  │  PostgreSQL (port 40432)        │  Weaviate v4 (port 40480)        │   │
│  │  ─────────────────────────────  │  ────────────────────────────    │   │
│  │  • users                        │  • ACMS_Raw_v1 (Q&A, uploads)    │   │
│  │  • query_history (3.9K rows)    │  • ACMS_Knowledge_v2 (facts)     │   │
│  │  • memory_items (97K rows)      │  • QueryCache_v1 (deprecated)    │   │
│  │  • topic_extractions (4.8K)     │                                   │   │
│  │  • intelligence_reports         │                                   │   │
│  │  • org_knowledge, user_insights │                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Port | Purpose |
|-------|------------|------|---------|
| Frontend | Electron (Vanilla JS) | - | Desktop application |
| Backend | FastAPI (Python 3.11) | 40080 | REST API server |
| Database | PostgreSQL 15 | 40432 | Relational data |
| Vector DB | Weaviate v4 | 40480 | Semantic search, embeddings |
| Cache | Redis | 40479 | Session cache (NOT for query caching) |
| AI Agents | Claude Sonnet 4.5, GPT-5.1, Gemini 3 Flash | - | LLM providers |
| Web Search | Tavily | - | Real-time web search |
| Scheduler | APScheduler | - | Background jobs |

---

## 2. Chat Flow - Actual 8-Step Pipeline

**File:** `src/gateway/orchestrator.py:161-1000`

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 1: INTENT DETECTION                                                │
│ File: src/gateway/intent_classifier.py                                  │
│                                                                         │
│ Classifies query into: factual, creative, coding, web_search, etc.     │
│ Output: Intent enum + confidence score (0.0-1.0)                        │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 1.5: PREFLIGHT GATE (Security)                                     │
│ File: src/gateway/preflight_gate.py                                     │
│                                                                         │
│ BLOCKS if: SSN, credit cards, API keys, passwords, injection attempts  │
│ Can SANITIZE: emails, phone numbers → [REDACTED]                        │
│ Sets: allow_web_search = false if injection detected                    │
│ Rate limiting: Blocks after 3 blocked requests in 60s                   │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 2: CACHE CHECK (DISABLED)                                          │
│                                                                         │
│ Status: DISABLED since Nov 14, 2025                                     │
│ Reason: Prevents pollution (wrong agents, stale web data)               │
│ All queries generate fresh responses                                    │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 3: AGENT SELECTION                                                 │
│ File: src/gateway/agent_selector.py                                     │
│                                                                         │
│ Selects based on intent + cost optimization:                            │
│ • claude_sonnet: coding, complex reasoning ($3/1M in, $15/1M out)       │
│ • chatgpt_4o: general, creative ($2.50/1M in, $10/1M out)               │
│ • gemini_flash: factual, translations ($0.075/1M)                       │
│ • tavily: web_search intent                                             │
│                                                                         │
│ Stats tracked: query_history.response_source column                     │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 3.25: WEB SEARCH (Tavily)                                          │
│ File: src/gateway/search_detector.py + src/gateway/agents/tavily.py     │
│                                                                         │
│ Triggers when:                                                          │
│ • Keywords: "latest", "current", "today", "news", stock tickers, etc.   │
│ • Time-sensitive queries detected                                       │
│ • AND PreflightGate.allow_web_search = true                             │
│                                                                         │
│ Returns: List[SearchResult] with title, url, content                    │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 4: CONTEXT ASSEMBLY                                                │
│ File: src/gateway/context_assembler.py                                  │
│                                                                         │
│ Retrieves context from:                                                 │
│ 1. Thread context (conversation history) - if continuing chat           │
│ 2. Web search results (if Step 3.25 ran)                                │
│ 3. Memory search:                                                       │
│    - Weaviate: ACMS_Raw_v1 + ACMS_Knowledge_v2 (semantic search)        │
│    - PostgreSQL: memory_items table (fallback)                          │
│                                                                         │
│ Retrieval searches both raw Q&A and extracted knowledge                 │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 4.5: CONTEXT SANITIZATION                                          │
│ File: src/gateway/context_sanitizer.py                                  │
│                                                                         │
│ Neutralizes injection attempts in retrieved context                     │
│ (memories/web results may contain malicious content)                    │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 5: COMPLIANCE CHECK                                                │
│ File: src/gateway/compliance_checker.py                                 │
│                                                                         │
│ Final check before LLM call:                                            │
│ • PII detection (SSN, credit cards, phone numbers)                      │
│ • Prohibited content (violence, illegal activities)                     │
│ • Privacy level enforcement                                             │
│ • Token limit validation                                                │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 6: AGENT EXECUTION (Streaming)                                     │
│ Files: src/gateway/agents/claude.py, chatgpt.py, gemini.py              │
│                                                                         │
│ Sends: query + assembled context to selected LLM                        │
│ Streams: response chunks back to UI                                     │
│ Tracks: input_tokens, output_tokens, cost_usd, latency_ms               │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 7: FACT EXTRACTION & STORAGE                                       │
│ Files: src/memory/fact_extractor.py, src/gateway/orchestrator.py:810+   │
│                                                                         │
│ ONLY runs if: answer.length > 100 chars AND ENABLE_FACT_EXTRACTION=true │
│                                                                         │
│ Step 7a: Store raw Q&A to ACMS_Raw_v1 (Weaviate)                        │
│          - For future cache lookup                                      │
│          - Properties: question, answer, user_id, agent, cost, latency  │
│                                                                         │
│ Step 7b: Extract facts using LLM (GPT-3.5-turbo)                        │
│          - Prompt extracts 0-3 standalone facts                         │
│          - Removes Q&A format, conversational fluff                     │
│          - Returns: List[str] of facts                                  │
│                                                                         │
│ Step 7c: Store facts to ACMS_Knowledge_v2 (Weaviate)                    │
│          - Clean, standalone facts                                      │
│          - Properties: content, content_hash, user_id, source_id        │
│                                                                         │
│ OUTPUT (what user sees):                                                │
│ {                                                                       │
│   "facts_extracted": 2,                                                 │
│   "facts": ["fact 1...", "fact 2..."],                                  │
│   "raw_stored": {"collection": "ACMS_Raw_v1", "stored": true},          │
│   "knowledge_stored": {"collection": "ACMS_Knowledge_v2", "stored": true}│
│ }                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 8: QUERY HISTORY STORAGE                                           │
│ File: src/storage/query_history_crud.py                                 │
│                                                                         │
│ Stores to PostgreSQL query_history:                                     │
│ • query_id, question, answer                                            │
│ • response_source (agent used)                                          │
│ • est_cost_usd, total_latency_ms                                        │
│ • tokens_in, tokens_out                                                 │
│ • from_cache (always false currently)                                   │
│ • data_source ('api', 'chatgpt_import', 'claude_import')                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Weaviate Collections (Actual State - Dec 20, 2025)

**Port:** 40480 (HTTP), 40481 (gRPC)

| Collection | Purpose | Status |
|------------|---------|--------|
| `ACMS_Raw_v1` | Raw Q&A pairs, file uploads (1536d embeddings) | ✅ Active |
| `ACMS_Knowledge_v2` | Structured knowledge (topics, entities, facts) | ✅ Active |
| `QueryCache_v1` | OLD semantic cache | ❌ DEPRECATED (delete) |

**Retrieval Sources** (orchestrator.py:1264):
- `raw` → ACMS_Raw_v1
- `knowledge` → ACMS_Knowledge_v2

**Deleted Collections** (merged into ACMS_Raw_v1):
- ACMS_MemoryItems_v1
- ACMS_Knowledge_v1
- ACMS_Enriched_v1

---

## 4. Key Files Reference

### Chat Pipeline

| File | Purpose |
|------|---------|
| `src/gateway/orchestrator.py` | 8-step pipeline execution |
| `src/gateway/intent_classifier.py` | Intent detection (step 1) |
| `src/gateway/preflight_gate.py` | Security gate (step 1.5) |
| `src/gateway/search_detector.py` | Web search detection (step 3.25) |
| `src/gateway/context_assembler.py` | Context building (step 4) |
| `src/gateway/agents/claude.py` | Claude Sonnet integration |
| `src/gateway/agents/chatgpt.py` | GPT-5.1 integration |
| `src/gateway/agents/gemini.py` | Gemini Flash integration |
| `src/gateway/agents/tavily.py` | Web search |
| `src/memory/fact_extractor.py` | LLM fact extraction (step 7b) |

### Storage

| File | Purpose |
|------|---------|
| `src/storage/memory_crud.py` | Memory CRUD + Weaviate search |
| `src/storage/query_history_crud.py` | Query history storage |
| `src/storage/weaviate_client.py` | Weaviate v4 client |
| `src/storage/database.py` | PostgreSQL connection |

### Intelligence Pipeline

| File | Purpose |
|------|---------|
| `src/intelligence/topic_extractor.py` | Keyword + LLM topic extraction |
| `src/intelligence/insights_engine.py` | Insights generation |
| `src/intelligence/report_generator.py` | Weekly reports |
| `src/jobs/intelligence_jobs.py` | Scheduled job definitions |

---

## 5. Agent Selection Stats

Agent usage is tracked in `query_history.response_source`:

```sql
SELECT response_source, COUNT(*) as count,
       SUM(est_cost_usd) as total_cost
FROM query_history
GROUP BY response_source
ORDER BY count DESC;
```

Current stats (as of Dec 15, 2025):
- `chatgpt` (imports): 3,508 queries
- `claude`: 133 queries, $3.08
- `semantic_cache`: 120 queries, $0 (historical)
- `claude_sonnet`: 117 queries, $1.70
- `gemini`: 19 queries, $0.11

---

## 6. API Endpoints

### Chat

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/gateway/chat` | Streaming chat (desktop app uses this) |
| POST | `/gateway/ask` | Single Q&A (non-streaming, legacy) |

**Why two endpoints?**
- `/gateway/chat`: Streaming, supports conversation threads, used by desktop UI
- `/gateway/ask`: Non-streaming, simpler response, used for API integrations

### Query History (NEW)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/query-history` | List Q&A pairs with filtering |
| GET | `/query-history/{id}` | Get full Q&A detail |
| GET | `/query-history/topics/summary` | Topic distribution |

### Intelligence

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v2/insights/summary` | Insights summary |
| POST | `/api/v2/insights/analyze` | Deep topic analysis |
| POST | `/api/v2/reports/generate` | Generate report |
| GET | `/api/v2/reports` | List reports |

---

## 7. Intelligence Pipeline

### Stage 1: Topic Extraction (Hourly)

**Schedule:** Every hour at :15
**File:** `src/jobs/intelligence_jobs.py:32-155`

```
query_history (unprocessed)
         │
         ▼
┌─────────────────────────────────────────┐
│ TopicExtractor.batch_extract()          │
│                                         │
│ 1. KEYWORD extraction (FREE)            │
│    - 50+ patterns: python, kubernetes,  │
│      finance, stocks, automotive, etc.  │
│                                         │
│ 2. LLM fallback (if confidence < 0.5)   │
│    - Budget: $0.10/hour max             │
│                                         │
│ Output: topics[], primary_topic,        │
│         confidence, extraction_method   │
└─────────────────────────────────────────┘
         │
         ▼
   topic_extractions table (4,805 rows)
```

### Stage 2: Insight Generation (Daily 2AM)

**File:** `src/jobs/intelligence_jobs.py:177-282`

Aggregates topics → user_insights + org_knowledge tables

### Stage 3: Weekly Reports (Monday 6AM)

**File:** `src/jobs/intelligence_jobs.py:285-398`

Generates executive reports → intelligence_reports table

---

## 8. Current Data State

### PostgreSQL

| Table | Rows | Notes |
|-------|------|-------|
| users | 200+ | Most are demo users |
| query_history | 3,917 | 3,508 ChatGPT imports |
| memory_items | 97,255 | Chrome extension captures |
| topic_extractions | 4,805 | Backfilled Dec 15, 2025 |
| intelligence_reports | ~10 | Generated reports |

### Weaviate

All collections have ~1 object due to incomplete re-sync.

---

## 9. Environment Variables

```bash
# Fact extraction (Step 7)
ENABLE_FACT_EXTRACTION=true    # Enable/disable fact extraction

# Web search
TAVILY_API_KEY=xxx             # Required for web search

# LLM providers
OPENAI_API_KEY=xxx             # For GPT-5.1 + FactExtractor
ANTHROPIC_API_KEY=xxx          # For Claude Sonnet
GOOGLE_API_KEY=xxx             # For Gemini Flash

# Jobs
ACMS_JOB_TOPIC_EXTRACTION_ENABLED=true
ACMS_JOB_INSIGHT_GENERATION_ENABLED=true
ACMS_JOB_WEEKLY_REPORT_ENABLED=true
```

---

## 10. Known Issues

1. **QueryCache_v1 deprecated** - Should be deleted (causes pollution)
2. **Cache disabled** - All queries generate fresh responses
3. **GPT-5.1 requires max_completion_tokens** - Not max_tokens (fixed in code)
4. **Ollama running but unused** - Can stop acms_ollama container

---

## 11. Gmail Integration (Phase 1)

**Status:** Phase 1A COMPLETE, Phase 1B IN PROGRESS

### Key Files

| File | Purpose |
|------|---------|
| `src/integrations/gmail/oauth.py` | Google OAuth 2.0 flow |
| `src/integrations/gmail/client.py` | Gmail API client wrapper |
| `src/integrations/gmail/service.py` | Business logic layer |
| `src/integrations/gmail/models.py` | Pydantic models |

### PostgreSQL Tables

| Table | Purpose |
|-------|---------|
| `gmail_oauth_tokens` | Encrypted OAuth credentials |
| `email_sender_scores` | Learned sender importance |
| `email_insights` | AI-generated email summaries |
| `email_actions` | Learning signals (opens, stars, replies) |

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/gmail/auth/start` | Initiate OAuth flow |
| `GET /api/gmail/auth/callback` | OAuth callback |
| `GET /api/gmail/inbox` | List emails with pagination |
| `GET /api/gmail/inbox/summary` | Accurate unread/starred counts |
| `GET /api/gmail/insights` | Top senders, AI insights |
| `GET /api/gmail/actions/stats` | Learning signal stats |

### Features Implemented

1. **OAuth 2.0** - Secure token storage with encryption
2. **Inbox View** - Paginated email list with timeline selector (7/30/90/120 days)
3. **Accurate Counts** - Uses Gmail Labels API for unread/starred
4. **AI Summaries** - Gemini Flash generates email summaries
5. **Sender Scoring** - Learns important senders from user actions
6. **Learning Signals** - Tracks opens, stars, replies for personalization
7. **Clickable Sender Chips** - Filter inbox by sender from insights panel

---

## 12. Unified Intelligence Layer (Phase 1.5)

**Status:** DESIGN COMPLETE, IMPLEMENTATION PENDING
**Spec:** `docs/UNIFIED_INTELLIGENCE_ARCHITECTURE.md`

### Purpose

Enable cross-source queries across AI Chat, Email, Financial, and Calendar data:
- "What emails relate to my AWS spending?"
- "Who should I follow up with this week?"
- "What did I discuss with Sarah about budgets?"

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────────┐
│ DATA SOURCES → INSIGHT EXTRACTORS → UNIFIED STORE → QUERY ROUTER  │
└─────────────────────────────────────────────────────────────────────┘
```

### New Database Tables

| Table | Purpose |
|-------|---------|
| `unified_insights` | Cross-source insight storage |

### New Weaviate Collection

| Collection | Purpose |
|------------|---------|
| `ACMS_Insights_v1` | Vectorized cross-source insights |

### Query Router Steps

1. **Detect** - Intent classification + entity extraction
2. **Route** - Determine which sources to query
3. **Execute** - Parallel search across relevant sources
4. **Aggregate** - Merge results with source tags
5. **Respond** - Return with proper citations

### Privacy Rules

| Rule | Description |
|------|-------------|
| Financial amounts | NEVER sent to LLM |
| Raw email content | Only summaries to unified layer |
| Entity references | Use IDs, not PII |

---

**Document Version:** 5.0
**Reflects:** Actual production code as of December 21, 2025
