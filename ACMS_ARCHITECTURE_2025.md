# ACMS Production Architecture (December 2025)

**Status**: Active Development
**Last Updated**: December 21, 2025
**Vision**: Local-First AI Desktop Hub with Unified Intelligence

---

## Executive Summary

ACMS is a production-grade **local-first AI platform** that:

1. **Multi-Agent AI Gateway** - Claude Sonnet 4.5, GPT-5.1, Gemini 3 Flash with smart routing
2. **Intelligence Pipeline** - 3-stage automated knowledge extraction (Hourly → Daily → Weekly)
3. **Gmail Integration** - Superhuman-inspired email view with AI insights
4. **Unified Intelligence Layer** - Cross-source queries across AI Chat, Email, Financial, Calendar
5. **Desktop App** - Production-quality Electron app with chat, insights, reports, email views

**Key Differentiator**: All data stays local. Unlike ChatGPT Pulse ($200/mo), ACMS provides AI intelligence with complete privacy.

---

## Table of Contents

1. [Current State](#1-current-state)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Chat Pipeline](#4-chat-pipeline-8-steps)
5. [Storage Architecture](#5-storage-architecture)
6. [Intelligence Pipeline](#6-intelligence-pipeline)
7. [Gmail Integration](#7-gmail-integration-phase-1)
8. [Unified Intelligence Layer](#8-unified-intelligence-layer-phase-15)
9. [Desktop Application](#9-desktop-application)
10. [API Reference](#10-api-reference)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Related Documents](#12-related-documents)

---

## 1. Current State

### Implemented Features

| Feature | Status | Description |
|---------|--------|-------------|
| Multi-Agent Chat | COMPLETE | Claude/GPT/Gemini with streaming |
| Memory Retrieval | COMPLETE | 97K+ memories, semantic search |
| Intelligence Pipeline | COMPLETE | Topic extraction, insights, weekly reports |
| Desktop App | COMPLETE | Electron with chat, insights, reports |
| Gmail Integration | Phase 1A COMPLETE | OAuth, inbox view, AI summaries |
| Audit System | COMPLETE | Full data flow tracking |
| Security | COMPLETE | PII detection, compliance checks |

### Data Statistics (as of Dec 21, 2025)

| Metric | Count |
|--------|-------|
| Memory items | 97,255 |
| Query history | 3,917+ |
| ChatGPT imports | 3,508 |
| Topic extractions | 4,805 |
| Intelligence reports | ~10 |

### Key Services

| Service | Port | Purpose |
|---------|------|---------|
| FastAPI Server | 40080 | REST API |
| PostgreSQL | 40432 | Relational data |
| Weaviate v4 | 40480 | Vector search |
| Redis | 40479 | Session cache |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ACMS SYSTEM ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  INPUT SOURCES                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Desktop App  │  │ Chrome Ext   │  │ Gmail        │  │ ChatGPT Imp  │         │
│  │  (Electron)  │  │ (97K mems)   │  │ (Phase 1)    │  │ (3.5K Q&As)  │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                 │                 │
│         ▼                 ▼                 ▼                 ▼                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI SERVER (port 40080)                          │    │
│  │  /gateway/chat  │  /memories  │  /api/gmail/*  │  /api/v2/*             │    │
│  └────────────────────────────────┬────────────────────────────────────────┘    │
│                                   │                                             │
│                                   ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        CORE SERVICES                                    │    │
│  │                                                                         │    │
│  │  GatewayOrchestrator ─────▶ AgentSelector ─────▶ Agents                │    │
│  │         │                         │             (Claude/GPT/Gemini)     │    │
│  │         │                         │                                     │    │
│  │         ├── IntentClassifier      ├── FactExtractor (GPT-3.5)          │    │
│  │         ├── SearchDetector        │                                     │    │
│  │         ├── PreflightGate         │   NEW: Unified Intelligence        │    │
│  │         ├── ContextAssembler      │   ├── InsightExtractor             │    │
│  │         └── ComplianceChecker     │   ├── QueryRouter                  │    │
│  │                                   │   └── SourceAggregator             │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                   │                                             │
│                                   ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                          DATA STORES                                    │    │
│  │                                                                         │    │
│  │  PostgreSQL (port 40432)          │  Weaviate v4 (port 40480)          │    │
│  │  ─────────────────────────────    │  ────────────────────────────      │    │
│  │  • query_history (3.9K rows)      │  • ACMS_Raw_v1 (Q&A, uploads)      │    │
│  │  • memory_items (97K rows)        │  • ACMS_Knowledge_v2 (facts)       │    │
│  │  • topic_extractions (4.8K)       │  • ACMS_Insights_v1 (NEW)          │    │
│  │  • intelligence_reports           │                                     │    │
│  │  • gmail_oauth_tokens             │                                     │    │
│  │  • email_insights                 │                                     │    │
│  │  • unified_insights (NEW)         │                                     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Frontend | Electron | - | Desktop application |
| Frontend | Vanilla JavaScript | ES6+ | UI rendering |
| Backend | FastAPI | 0.104+ | REST API server |
| Backend | Python | 3.11 | Core language |
| Database | PostgreSQL | 15 | Relational data |
| Vector DB | Weaviate | v4 | Semantic search, embeddings |
| Cache | Redis | - | Session cache |
| AI Agents | Claude Sonnet 4.5 | - | Coding, complex reasoning |
| AI Agents | GPT-5.1 | - | General, creative |
| AI Agents | Gemini 3 Flash | - | Factual, translations |
| Web Search | Tavily | - | Real-time web search |
| Scheduler | APScheduler | - | Background jobs |
| OAuth | Google OAuth 2.0 | - | Gmail integration |

### AI Provider Costs

| Provider | Model | Input Cost | Output Cost | Use Case |
|----------|-------|------------|-------------|----------|
| Anthropic | Claude Sonnet 4.5 | $3/1M tokens | $15/1M tokens | Coding, analysis |
| OpenAI | GPT-5.1 | $2.50/1M | $10/1M | General, creative |
| Google | Gemini 3 Flash | $0.075/1M | $0.30/1M | Factual, quick |

---

## 4. Chat Pipeline (8 Steps)

**File**: `src/gateway/orchestrator.py:161-1000`

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
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 2: CACHE CHECK (DISABLED)                                          │
│                                                                         │
│ Status: DISABLED since Nov 14, 2025                                     │
│ Reason: Prevents pollution (wrong agents, stale web data)               │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 3: AGENT SELECTION                                                 │
│ File: src/gateway/agent_selector.py                                     │
│                                                                         │
│ Routes based on intent + cost optimization:                             │
│ • claude_sonnet: coding, complex reasoning                              │
│ • chatgpt_4o: general, creative                                         │
│ • gemini_flash: factual, translations                                   │
│ • tavily: web_search intent                                             │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 3.25: WEB SEARCH (Tavily)                                          │
│ File: src/gateway/search_detector.py + src/gateway/agents/tavily.py     │
│                                                                         │
│ Triggers when: "latest", "current", "today", news, stock tickers        │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 4: CONTEXT ASSEMBLY                                                │
│ File: src/gateway/context_assembler.py                                  │
│                                                                         │
│ Retrieves context from:                                                 │
│ 1. Thread context (conversation history)                                │
│ 2. Web search results (if Step 3.25 ran)                                │
│ 3. Memory search: ACMS_Raw_v1 + ACMS_Knowledge_v2                       │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 4.5: CONTEXT SANITIZATION                                          │
│ File: src/gateway/context_sanitizer.py                                  │
│                                                                         │
│ Neutralizes injection attempts in retrieved context                     │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 5: COMPLIANCE CHECK                                                │
│ File: src/gateway/compliance_checker.py                                 │
│                                                                         │
│ Final check: PII detection, prohibited content, privacy enforcement     │
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
│ Files: src/memory/fact_extractor.py                                     │
│                                                                         │
│ Step 7a: Store raw Q&A to ACMS_Raw_v1 (Weaviate)                        │
│ Step 7b: Extract facts using GPT-3.5-turbo                              │
│ Step 7c: Store facts to ACMS_Knowledge_v2 (Weaviate)                    │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 8: QUERY HISTORY STORAGE                                           │
│ File: src/storage/query_history_crud.py                                 │
│                                                                         │
│ Stores to PostgreSQL: query_id, question, answer, response_source,      │
│ est_cost_usd, total_latency_ms, tokens_in, tokens_out                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Storage Architecture

### 5.1 PostgreSQL Tables (Key Tables)

| Table | Purpose | Row Count |
|-------|---------|-----------|
| users | User accounts | 200+ |
| query_history | All Q&A pairs | 3,917 |
| memory_items | Chrome captures | 97,255 |
| topic_extractions | Extracted topics | 4,805 |
| org_knowledge | Organization facts | - |
| user_insights | User-specific insights | - |
| intelligence_reports | Weekly reports | ~10 |
| gmail_oauth_tokens | OAuth credentials (encrypted) | - |
| email_sender_scores | Learned sender importance | - |
| email_insights | Email AI summaries | - |
| email_actions | Learning signals (opens, stars) | - |
| audit_events | Data flow audit | - |
| unified_insights | Cross-source insights (NEW) | - |

### 5.2 Weaviate Collections

| Collection | Purpose | Status |
|------------|---------|--------|
| ACMS_Raw_v1 | Raw Q&A pairs, file uploads | ACTIVE |
| ACMS_Knowledge_v2 | Extracted facts, topics | ACTIVE |
| ACMS_Insights_v1 | Cross-source unified insights | NEW (Phase 1.5) |
| QueryCache_v1 | Old semantic cache | DEPRECATED |

### 5.3 File System Structure

```
~/.acms/
├── files/
│   ├── uploads/           # User uploaded files
│   ├── attachments/       # Email attachments
│   └── exports/           # Generated reports
├── cache/
│   ├── email_bodies/      # Full email content cache
│   └── thumbnails/        # Image previews
└── config/
    ├── oauth_tokens.enc   # Encrypted OAuth tokens
    └── preferences.json   # User settings
```

---

## 6. Intelligence Pipeline

### 6.1 Three-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STAGE 1: TOPIC EXTRACTION (Hourly at :15)                              │
│  ─────────────────────────────────────────                              │
│  File: src/jobs/intelligence_jobs.py:32-155                             │
│                                                                          │
│  query_history (unprocessed)                                             │
│         │                                                                │
│         ▼                                                                │
│  ┌─────────────────────────────────────────┐                            │
│  │ TopicExtractor.batch_extract()          │                            │
│  │                                         │                            │
│  │ 1. KEYWORD extraction (FREE)            │                            │
│  │    - 50+ patterns: python, kubernetes,  │                            │
│  │      finance, stocks, automotive, etc.  │                            │
│  │                                         │                            │
│  │ 2. LLM fallback (if confidence < 0.5)   │                            │
│  │    - Budget: $0.10/hour max             │                            │
│  └─────────────────────────────────────────┘                            │
│         │                                                                │
│         ▼                                                                │
│  topic_extractions table (4,805 rows)                                   │
│                                                                          │
│  STAGE 2: INSIGHT GENERATION (Daily at 2AM)                             │
│  ──────────────────────────────────────────                             │
│  File: src/jobs/intelligence_jobs.py:177-282                            │
│                                                                          │
│  Aggregates topics → user_insights + org_knowledge tables               │
│                                                                          │
│  STAGE 3: WEEKLY REPORTS (Monday 6AM)                                   │
│  ─────────────────────────────────────                                  │
│  File: src/jobs/intelligence_jobs.py:285-398                            │
│                                                                          │
│  Generates executive reports → intelligence_reports table               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Scheduled Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| topic_extraction | Hourly at :15 | Extract topics from new Q&As |
| insight_generation | Daily 2AM | Aggregate insights |
| weekly_reports | Monday 6AM | Generate executive reports |
| memory_sync | Hourly at :30 | Sync PostgreSQL → Weaviate |
| cache_cleanup | Daily 3AM | Clean expired cache |
| audit_rollup | Daily 1AM | Aggregate audit events |

---

## 7. Gmail Integration (Phase 1)

**Status**: Phase 1A COMPLETE, Phase 1B IN PROGRESS

### 7.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GMAIL INTEGRATION                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐     │
│  │ Desktop App  │────▶│  /api/gmail/*    │────▶│  Gmail API       │     │
│  │ Email View   │     │  OAuth, Inbox    │     │  (googleapis)    │     │
│  └──────────────┘     └──────────────────┘     └──────────────────┘     │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    DATA LAYER                                     │   │
│  │                                                                   │   │
│  │  PostgreSQL                         Weaviate                     │   │
│  │  ──────────                         ────────                     │   │
│  │  • gmail_oauth_tokens (encrypted)   • ACMS_Insights_v1 (future)  │   │
│  │  • email_sender_scores              │                            │   │
│  │  • email_insights                   │                            │   │
│  │  • email_actions (learning signals) │                            │   │
│  │                                                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Key Features

| Feature | Status | File |
|---------|--------|------|
| OAuth 2.0 flow | COMPLETE | src/integrations/gmail/oauth.py |
| Gmail API client | COMPLETE | src/integrations/gmail/client.py |
| Inbox listing | COMPLETE | src/integrations/gmail/service.py |
| Unread count (Labels API) | COMPLETE | Fixed accurate counts |
| Timeline selector (7/30/90/120d) | COMPLETE | views.js |
| AI email summaries | COMPLETE | Gemini Flash |
| Sender importance scoring | COMPLETE | email_sender_scores table |
| Learning signals | COMPLETE | email_actions table |
| Clickable sender filtering | COMPLETE | Insights panel |

### 7.3 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| GET /api/gmail/auth/start | Initiate OAuth flow |
| GET /api/gmail/auth/callback | OAuth callback |
| GET /api/gmail/inbox | List emails with pagination |
| GET /api/gmail/inbox/summary | Unread/starred counts |
| GET /api/gmail/insights | Top senders, AI insights |
| GET /api/gmail/actions/stats | Learning signal stats |
| POST /api/gmail/actions/track | Record user actions |

---

## 8. Unified Intelligence Layer (Phase 1.5)

**Status**: DESIGN COMPLETE, IMPLEMENTATION PENDING
**Spec**: `docs/UNIFIED_INTELLIGENCE_ARCHITECTURE.md`

### 8.1 Purpose

Enable cross-source queries:
- "What emails relate to my AWS spending?" (Email + Financial)
- "Who should I follow up with this week?" (Email + Calendar)
- "What did I discuss with Sarah about budgets?" (Chat + Email)

### 8.2 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 UNIFIED INTELLIGENCE LAYER                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DATA SOURCES              INSIGHT EXTRACTORS                            │
│  ────────────              ──────────────────                            │
│                                                                          │
│  ┌─────────────┐          ┌───────────────────────────────────┐         │
│  │ AI Chats    │──────────│ KnowledgeExtractor (existing)     │         │
│  │ (97K mems)  │          │ • Entity extraction               │         │
│  └─────────────┘          │ • Topic clustering                │         │
│                           │ • Fact synthesis                  │         │
│  ┌─────────────┐          └───────────────────────────────────┘         │
│  │ Email       │                        │                               │
│  │ (Gmail)     │──────────│ EmailInsightExtractor (NEW)       │         │
│  └─────────────┘          │ • Action items                    │         │
│                           │ • Key dates/deadlines             │         │
│  ┌─────────────┐          │ • Sender importance signals       │         │
│  │ Financial   │──────────│ • Topic categorization            │         │
│  │ (Phase 2)   │          └───────────────────────────────────┘         │
│  └─────────────┘                        │                               │
│                           ┌─────────────┴─────────────┐                 │
│  ┌─────────────┐          │ FinanceInsightExtractor   │                 │
│  │ Calendar    │          │ • Spending patterns       │                 │
│  │ (Phase 3)   │──────────│ • Category trends         │                 │
│  └─────────────┘          │ • NO AMOUNTS TO LLM       │                 │
│                           └───────────────────────────┘                 │
│                                         │                               │
│                                         ▼                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  UNIFIED INSIGHTS STORE                          │   │
│  │                                                                  │   │
│  │  PostgreSQL: unified_insights        Weaviate: ACMS_Insights_v1  │   │
│  │  ────────────────────────────        ────────────────────────── │   │
│  │  • insight_id                        • insight_id               │   │
│  │  • source (chat|email|finance|cal)   • content_vector           │   │
│  │  • insight_type                      • insight_text             │   │
│  │  • entities (JSONB)                  • source_tags              │   │
│  │  • privacy_level                     • entity_refs              │   │
│  │  • created_at                                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                         │                               │
│                                         ▼                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      QUERY ROUTER                                │   │
│  │                                                                  │   │
│  │  1. Detect intent + entities                                     │   │
│  │  2. Determine source requirements                                │   │
│  │  3. Execute parallel source searches                             │   │
│  │  4. Aggregate with source tags                                   │   │
│  │  5. Return with citations                                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Privacy Rules

| Rule | Description |
|------|-------------|
| Financial amounts | NEVER sent to LLM, only patterns/categories |
| Raw email content | Only summaries/insights to unified layer |
| Confidential data | Never leaves local storage |
| Entity linking | Uses reference IDs, not PII |

---

## 9. Desktop Application

### 9.1 Views

| View | File Location | Purpose |
|------|---------------|---------|
| Chat | views.js:1-400 | AI conversation interface |
| Insights | views.js:660-960 | Topic analysis, trends |
| Reports | views.js:962-1270 | Weekly executive reports |
| Email | views.js:1300+ | Gmail inbox with AI insights |
| History | views.js | Query history browser |
| Settings | views.js | User preferences |
| Data Flow | views.js | Audit trail visualization |

### 9.2 Key Files

| File | Purpose |
|------|---------|
| desktop-app/src/renderer/app.js | Main application |
| desktop-app/src/renderer/components/views.js | All view rendering |
| desktop-app/src/renderer/components/chat.js | Chat functionality |
| desktop-app/src/renderer/components/login.js | Auth flow |
| desktop-app/src/renderer/components/message.js | Message rendering |
| desktop-app/src/renderer/styles/chat.css | All styling |

---

## 10. API Reference

### 10.1 Chat Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /gateway/chat | Streaming chat (SSE) |
| POST | /gateway/ask | Non-streaming Q&A |

### 10.2 Intelligence Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/v2/insights/summary | Insights summary |
| POST | /api/v2/insights/analyze | Deep topic analysis |
| GET | /api/v2/insights/trends | Usage trends |
| POST | /api/v2/reports/generate | Generate report |
| GET | /api/v2/reports | List reports |
| GET | /api/v2/reports/{id} | Get specific report |

### 10.3 Analytics Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /analytics/dashboard | Cache, performance, satisfaction |
| GET | /stats | Memory distribution by source |
| GET | /query-history | Query history with filters |

### 10.4 Gmail Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/gmail/auth/start | Initiate OAuth |
| GET | /api/gmail/auth/callback | OAuth callback |
| GET | /api/gmail/inbox | Email listing |
| GET | /api/gmail/inbox/summary | Counts |
| GET | /api/gmail/insights | AI insights |

---

## 11. Implementation Roadmap

### Completed

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Audit Foundation | COMPLETE |
| Phase 1A | Gmail OAuth + Inbox View | COMPLETE |
| Phase 1B | Email AI Summaries + Learning | PARTIAL |

### In Progress / Planned

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1.5 | Unified Intelligence Layer | DESIGN COMPLETE |
| Phase 2 | Financial Integration (Plaid) | PLANNED |
| Phase 3 | Calendar Integration (Google) | PLANNED |
| Phase 4 | File Upload & Processing | PLANNED |
| Phase 5 | Browser Session Control | PLANNED |
| Phase 6 | ACMS Pulse | PLANNED |

---

## 12. Related Documents

| Document | Purpose |
|----------|---------|
| [TECHNOLOGY_STACK_REFRESHER.md](docs/TECHNOLOGY_STACK_REFRESHER.md) | Current implementation details |
| [UNIFIED_INTELLIGENCE_ARCHITECTURE.md](docs/UNIFIED_INTELLIGENCE_ARCHITECTURE.md) | Phase 1.5 design spec |
| [ACMS_3.0_UNIFIED_INTELLIGENCE_PLAN.md](docs/ACMS_3.0_UNIFIED_INTELLIGENCE_PLAN.md) | Complete implementation plan |
| [MCP_SETUP.md](MCP_SETUP.md) | MCP server configuration |
| [QUICK_START.md](QUICK_START.md) | Getting started guide |

---

## Appendix: Environment Variables

```bash
# Core
DATABASE_URL=postgresql://...
WEAVIATE_URL=http://localhost:40480

# AI Providers
ANTHROPIC_API_KEY=xxx          # Claude Sonnet
OPENAI_API_KEY=xxx             # GPT-5.1 + FactExtractor
GOOGLE_API_KEY=xxx             # Gemini Flash
TAVILY_API_KEY=xxx             # Web search

# Features
ENABLE_FACT_EXTRACTION=true

# Jobs
ACMS_JOB_TOPIC_EXTRACTION_ENABLED=true
ACMS_JOB_INSIGHT_GENERATION_ENABLED=true
ACMS_JOB_WEEKLY_REPORT_ENABLED=true

# Gmail
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
```

---

**Document Version**: 5.0
**Last Updated**: December 21, 2025
**Reflects**: Complete production system including Gmail Integration and Unified Intelligence design
