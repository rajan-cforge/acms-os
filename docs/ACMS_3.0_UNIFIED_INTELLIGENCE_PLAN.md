# ACMS 3.0: Unified Intelligence Platform

## Complete Implementation Plan with Self-Reflection Analysis

**Document Version:** 1.1
**Created:** December 20, 2025
**Updated:** December 23, 2025
**Status:** Phase 2 Complete, Planning Phase 3+

---

## Table of Contents

### Overview
1. [Executive Summary](#1-executive-summary)
2. [Foundation: Audit & Observability](#2-foundation-audit--observability)
3. [Database Architecture Decisions](#3-database-architecture-decisions)
4. [Core Features Analysis](#4-core-features-analysis)
5. [Learning Agents & UI Visibility](#5-learning-agents--ui-visibility)

### Implementation Phases
6. [Phase 0: Audit Foundation](#phase-0-audit-foundation-week-1) ✅ COMPLETE
7. [Phase 1: Gmail Integration](#phase-1-gmail-integration-weeks-2-3) ✅ COMPLETE
   - [1.1 Decision Log](#decision-log-what-were-building--why)
   - [1.2 UX Design](#superhuman-inspired-ux-design)
   - [1.3 Implementation Plan](#implementation-plan-pragmatic-mvp---5-7-days)
   - [1.4 Technical Design](#phase-1-technical-design-staff-engineer-deep-dive)
     - [1.4.1 Code Organization](#141-code-organization)
     - [1.4.2 Data Model](#142-data-model-postgresql-schemas)
     - [1.4.3 OAuth Security](#143-oauth-token-security)
     - [1.4.4 Gmail API Client](#144-gmail-api-client-architecture)
     - [1.4.5 Sender Importance Model](#145-senderimportancemodel-v1)
     - [1.4.6 AI Summarization](#146-ai-summarization-pipeline)
     - [1.4.7 Desktop UI Integration](#147-desktop-ui-integration)
   - [1.5 TDD Test Specifications](#phase-1-tdd-test-specifications)
   - [1.6 Testing Checkpoints](#phase-1-testing-checkpoints)
8. [Phase 1.5: Unified Intelligence Layer](#phase-15-unified-intelligence-layer) ✅ COMPLETE
   - [1.5.1 Problem Statement](#151-problem-statement)
   - [1.5.2 Architecture](#152-architecture)
   - [1.5.3 Implementation Plan](#153-implementation-plan)
9. [Phase 2: Financial Integration](#phase-2-financial-integration-weeks-4-5) ✅ COMPLETE (2A/2B), ⏸️ 2C/2D deferred
10. [Phase 3: Calendar Integration](#phase-3-calendar-integration-week-6) ⏸️ DEFERRED
11. [Phase 4: File Upload & Processing](#phase-4-file-upload--processing-week-7) ⏸️ DEFERRED
12. [Phase 5: Browser Session Control](#phase-5-browser-session-control-weeks-8-9) ⏸️ DEFERRED
13. [Phase 6: ACMS Pulse](#phase-6-acms-pulse-weeks-10-11) 🎯 NEXT (Reduced Scope)

### Quality & Operations
13. [TDD & Testing Strategy](#7-tdd--testing-strategy)
14. [Security & Privacy](#8-security--privacy)
15. [Success Metrics](#9-success-metrics)
16. [Risk Analysis](#10-risk-analysis)

---

## 1. Executive Summary

### Vision
Transform ACMS from a memory-augmented chat system into the **ultimate local-first AI desktop hub** that:
- Controls your AI chat sessions (ChatGPT, Claude, Gemini)
- Manages your email, calendar, and finances
- Learns from your behavior to personalize everything
- Delivers proactive intelligence (like ChatGPT Pulse, but private)
- Never sends your data to external servers

### Key Differentiator
**Data never leaves your laptop.** Unlike ChatGPT Pulse ($200/month, data on OpenAI servers), ACMS keeps everything local while providing superior personalization.

### Core Principle
**Audit First.** Before any feature, we build comprehensive observability so we can see exactly what enters and leaves the system.

---

## 2. Foundation: Audit & Observability

### Self-Reflection Analysis

#### WHAT
A complete audit trail system that tracks:
- Every piece of data that enters ACMS
- Every piece of data that leaves ACMS
- Every transformation applied to data
- Every external API call made
- Every learning signal captured
- Every model prediction and its accuracy

#### WHY
1. **Trust:** Users must trust that data stays local
2. **Debugging:** Need to trace issues through the system
3. **Compliance:** Enterprise users need audit trails
4. **Learning validation:** Verify learning signals are correct
5. **Privacy verification:** Prove no data leakage
6. **Performance optimization:** Identify bottlenecks

#### HOW
```
┌─────────────────────────────────────────────────────────────────────┐
│                     AUDIT ARCHITECTURE                              │
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   DATA INGRESS  │    │  TRANSFORMATIONS │   │   DATA EGRESS   │ │
│  │                 │    │                  │   │                 │ │
│  │ • Gmail fetch   │───▶│ • Summarization  │──▶│ • LLM API calls │ │
│  │ • Plaid sync    │    │ • Embedding      │   │ • Browser auto  │ │
│  │ • Calendar sync │    │ • Learning       │   │ • Notifications │ │
│  │ • File upload   │    │ • Analysis       │   │ • Exports       │ │
│  │ • Browser cap   │    │                  │   │                 │ │
│  └────────┬────────┘    └────────┬─────────┘   └────────┬────────┘ │
│           │                      │                      │          │
│           ▼                      ▼                      ▼          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    AUDIT EVENT STREAM                        │   │
│  │                                                              │   │
│  │  {                                                           │   │
│  │    "event_id": "uuid",                                       │   │
│  │    "timestamp": "2025-12-20T10:30:00Z",                     │   │
│  │    "event_type": "data_ingress|transform|egress",           │   │
│  │    "source": "gmail|plaid|calendar|file|browser",           │   │
│  │    "operation": "fetch|summarize|embed|send",               │   │
│  │    "data_classification": "public|internal|confidential",   │   │
│  │    "data_hash": "sha256:...",  // Verify integrity          │   │
│  │    "data_size_bytes": 1234,                                 │   │
│  │    "destination": "local|weaviate|postgres|external_api",   │   │
│  │    "correlation_id": "session-uuid",                        │   │
│  │    "user_id": "default",                                    │   │
│  │    "metadata": {...}                                        │   │
│  │  }                                                           │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                      │
│                             ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    AUDIT STORAGE                             │   │
│  │                                                              │   │
│  │  PostgreSQL: audit_events table (append-only)               │   │
│  │  + Daily rollup tables for dashboard                        │   │
│  │  + 90-day retention by default (configurable)               │   │
│  │  + Export to JSON for compliance                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                             │                                      │
│                             ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    AUDIT DASHBOARD                           │   │
│  │                                                              │   │
│  │  Desktop App View: "Data Flow" tab                          │   │
│  │  • Real-time event stream                                   │   │
│  │  • Daily ingress/egress summary                             │   │
│  │  • Data by source pie chart                                 │   │
│  │  • External API calls list                                  │   │
│  │  • "End of Day Report" button                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### USER EXPERIENCE

**In Desktop App:**

1. **New sidebar item: "Data Flow"** (icon: 🔄)
   - Real-time activity feed
   - Shows what's happening right now

2. **Activity indicators:**
   - Small badge on integrations when syncing
   - "Last synced: 5 min ago" labels

3. **End of Day Report:**
   - Button in Data Flow view
   - Generates summary of all data activity
   - Shows: emails processed, transactions synced, LLM calls made
   - Exportable as PDF/JSON

4. **Privacy verification:**
   - "Data Destinations" section
   - Visual confirmation: "All data stayed local today ✓"
   - Or warning: "12 LLM API calls sent to external services"

**Sample End of Day Report:**
```
╔════════════════════════════════════════════════════════════════╗
║              ACMS DATA FLOW REPORT                             ║
║              December 20, 2025                                 ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  📥 DATA INGRESS                                               ║
║  ├─ Gmail: 47 emails fetched                                  ║
║  ├─ Calendar: 12 events synced                                ║
║  ├─ Plaid: 23 transactions fetched                            ║
║  └─ Files: 2 files uploaded                                   ║
║                                                                ║
║  🔄 TRANSFORMATIONS                                            ║
║  ├─ Summaries generated: 47                                   ║
║  ├─ Embeddings created: 84                                    ║
║  ├─ Learning signals captured: 156                            ║
║  └─ Knowledge extracted: 12 facts                             ║
║                                                                ║
║  📤 DATA EGRESS                                                ║
║  ├─ LLM API calls: 34                                         ║
║  │   ├─ Claude Sonnet: 12 calls ($0.08)                      ║
║  │   ├─ GPT-5.1: 8 calls ($0.03)                             ║
║  │   └─ Gemini 3 Flash: 14 calls ($0.01)                     ║
║  ├─ Browser automation: 3 tasks                               ║
║  └─ External APIs: 0                                          ║
║                                                                ║
║  🔒 PRIVACY STATUS                                             ║
║  ├─ Confidential data: 100% local                            ║
║  ├─ Internal data: 100% local                                ║
║  └─ Public data: 34 items sent to LLM APIs                   ║
║                                                                ║
║  💾 STORAGE                                                    ║
║  ├─ PostgreSQL: +2.3 MB today (847 MB total)                 ║
║  ├─ Weaviate: +1.1 MB today (234 MB total)                   ║
║  └─ Files: +5.2 MB today (128 MB total)                      ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

### Database Schema for Audit

```sql
-- Core audit events (append-only)
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Event classification
    event_type VARCHAR(20) NOT NULL,  -- ingress, transform, egress
    source VARCHAR(50) NOT NULL,       -- gmail, plaid, calendar, file, browser, llm
    operation VARCHAR(100) NOT NULL,   -- fetch, summarize, embed, send, etc.

    -- Data info
    data_classification VARCHAR(20),   -- public, internal, confidential, local_only
    data_hash VARCHAR(64),             -- SHA-256 for integrity
    data_size_bytes INTEGER,
    item_count INTEGER DEFAULT 1,

    -- Flow tracking
    destination VARCHAR(100),          -- local, weaviate, postgres, claude_api, etc.
    correlation_id UUID,               -- Links related events
    parent_event_id UUID,              -- For transformation chains

    -- Context
    user_id VARCHAR(100) DEFAULT 'default',
    session_id UUID,

    -- Details
    metadata JSONB,

    -- Indexing
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_type ON audit_events(event_type);
CREATE INDEX idx_audit_source ON audit_events(source);
CREATE INDEX idx_audit_correlation ON audit_events(correlation_id);
CREATE INDEX idx_audit_date ON audit_events(DATE(timestamp));

-- Daily rollups for dashboard
CREATE TABLE audit_daily_summary (
    date DATE PRIMARY KEY,

    -- Ingress
    gmail_emails_fetched INTEGER DEFAULT 0,
    calendar_events_synced INTEGER DEFAULT 0,
    plaid_transactions_fetched INTEGER DEFAULT 0,
    files_uploaded INTEGER DEFAULT 0,
    browser_captures INTEGER DEFAULT 0,

    -- Transforms
    summaries_generated INTEGER DEFAULT 0,
    embeddings_created INTEGER DEFAULT 0,
    learning_signals INTEGER DEFAULT 0,
    knowledge_extracted INTEGER DEFAULT 0,

    -- Egress
    llm_calls_claude INTEGER DEFAULT 0,
    llm_calls_gpt INTEGER DEFAULT 0,
    llm_calls_gemini INTEGER DEFAULT 0,
    llm_cost_usd DECIMAL(10, 4) DEFAULT 0,
    browser_automations INTEGER DEFAULT 0,

    -- Storage delta
    postgres_bytes_added BIGINT DEFAULT 0,
    weaviate_bytes_added BIGINT DEFAULT 0,
    files_bytes_added BIGINT DEFAULT 0,

    -- Privacy
    confidential_items_local INTEGER DEFAULT 0,
    confidential_items_external INTEGER DEFAULT 0,  -- Should always be 0!

    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger to update daily summary
CREATE OR REPLACE FUNCTION update_audit_daily_summary()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_daily_summary (date)
    VALUES (DATE(NEW.timestamp))
    ON CONFLICT (date) DO NOTHING;

    -- Update based on event type
    -- (Detailed update logic here)

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_summary_trigger
AFTER INSERT ON audit_events
FOR EACH ROW EXECUTE FUNCTION update_audit_daily_summary();
```

### TDD Checkpoints for Audit System

```python
# tests/unit/test_audit_system.py

class TestAuditEventCreation:
    """TDD: Audit events are created correctly"""

    def test_ingress_event_has_required_fields(self):
        """Every ingress event must have source, size, classification"""
        event = create_audit_event(
            event_type="ingress",
            source="gmail",
            operation="fetch_emails"
        )
        assert event.source is not None
        assert event.data_size_bytes is not None
        assert event.data_classification is not None

    def test_egress_event_has_destination(self):
        """Every egress event must specify destination"""
        event = create_audit_event(
            event_type="egress",
            operation="llm_call"
        )
        assert event.destination is not None
        assert event.destination in ["claude_api", "openai_api", "gemini_api", "local"]

    def test_confidential_data_never_external(self):
        """CRITICAL: Confidential data must never have external destination"""
        with pytest.raises(AuditViolationError):
            create_audit_event(
                event_type="egress",
                data_classification="confidential",
                destination="claude_api"
            )

class TestAuditDailySummary:
    """TDD: Daily summaries aggregate correctly"""

    def test_daily_summary_updates_on_event(self):
        """Summary should update when events are created"""
        initial = get_daily_summary(today())
        create_audit_event(event_type="ingress", source="gmail")
        updated = get_daily_summary(today())
        assert updated.gmail_emails_fetched == initial.gmail_emails_fetched + 1

    def test_end_of_day_report_generation(self):
        """End of day report should include all required sections"""
        report = generate_end_of_day_report(today())
        assert "DATA INGRESS" in report
        assert "DATA EGRESS" in report
        assert "PRIVACY STATUS" in report
        assert "STORAGE" in report

class TestAuditIntegrity:
    """TDD: Audit trail integrity"""

    def test_audit_events_are_immutable(self):
        """Audit events cannot be modified after creation"""
        event = create_audit_event(...)
        with pytest.raises(ImmutableRecordError):
            event.data_size_bytes = 999

    def test_correlation_id_links_events(self):
        """Related events share correlation ID"""
        correlation_id = uuid4()
        event1 = create_audit_event(correlation_id=correlation_id, ...)
        event2 = create_audit_event(correlation_id=correlation_id, ...)

        chain = get_event_chain(correlation_id)
        assert len(chain) == 2
```

---

## 3. Database Architecture Decisions

### Self-Reflection Analysis

#### WHAT
Choose the right storage technology for each data type:
- Audit logs
- Learning models
- Email metadata
- Financial data
- Vector embeddings
- User preferences
- File storage

#### WHY Different Databases?
1. **PostgreSQL (RDBMS):** Structured data, ACID transactions, complex queries
2. **Weaviate (Vector):** Semantic search, embeddings, similarity matching
3. **File System (Object):** Large files, documents, images
4. **SQLite (Optional):** Fast local cache, offline support

#### HOW

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DATABASE ARCHITECTURE                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL (Primary)                      │   │
│  │                                                              │   │
│  │  WHY: ACID transactions, complex queries, relationships     │   │
│  │                                                              │   │
│  │  TABLES:                                                     │   │
│  │  ├─ audit_events (append-only audit trail)                  │   │
│  │  ├─ audit_daily_summary (dashboard rollups)                 │   │
│  │  ├─ user_learning_profiles (personalization state)          │   │
│  │  ├─ email_sender_scores (learned importance)                │   │
│  │  ├─ email_metadata (message metadata, not content)          │   │
│  │  ├─ finance_accounts (linked accounts)                      │   │
│  │  ├─ finance_transactions (transaction history)              │   │
│  │  ├─ finance_patterns (spending patterns)                    │   │
│  │  ├─ calendar_events (event metadata)                        │   │
│  │  ├─ pulse_editions (generated Pulse content)                │   │
│  │  ├─ pulse_feedback (user feedback)                          │   │
│  │  ├─ integration_status (OAuth tokens, sync state)           │   │
│  │  ├─ learning_feedback_events (for model training)           │   │
│  │  └─ query_history (existing, expanded)                      │   │
│  │                                                              │   │
│  │  ESTIMATED SIZE: 2-5 GB/year typical use                    │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Weaviate (Vector DB)                      │   │
│  │                                                              │   │
│  │  WHY: Semantic search, similarity matching, RAG             │   │
│  │                                                              │   │
│  │  COLLECTIONS:                                                │   │
│  │  ├─ ACMS_Memories (existing - chat memories)                │   │
│  │  ├─ ACMS_Knowledge (existing - extracted facts)             │   │
│  │  ├─ ACMS_Emails (email embeddings for search)               │   │
│  │  │   └─ Properties: message_id, subject, sender,            │   │
│  │  │      snippet, importance_score, embedding                │   │
│  │  ├─ ACMS_Documents (uploaded file embeddings)               │   │
│  │  │   └─ Properties: file_id, filename, chunk_text,          │   │
│  │  │      page_num, embedding                                 │   │
│  │  └─ ACMS_Topics (topic/interest embeddings)                 │   │
│  │      └─ Properties: topic, description, user_interest,      │   │
│  │         embedding                                           │   │
│  │                                                              │   │
│  │  ESTIMATED SIZE: 500 MB - 2 GB/year typical use             │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    File System (Object Store)                │   │
│  │                                                              │   │
│  │  WHY: Large files, binary data, documents                   │   │
│  │                                                              │   │
│  │  STRUCTURE:                                                  │   │
│  │  ~/.acms/                                                   │   │
│  │  ├─ files/                                                  │   │
│  │  │   ├─ uploads/           # User uploaded files            │   │
│  │  │   ├─ attachments/       # Email attachments              │   │
│  │  │   └─ exports/           # Generated reports              │   │
│  │  ├─ cache/                                                  │   │
│  │  │   ├─ email_bodies/      # Full email content cache       │   │
│  │  │   └─ thumbnails/        # Image previews                 │   │
│  │  ├─ models/                                                 │   │
│  │  │   └─ learning/          # Serialized learning models     │   │
│  │  └─ config/                                                 │   │
│  │      ├─ oauth_tokens.enc   # Encrypted OAuth tokens         │   │
│  │      └─ preferences.json   # User settings                  │   │
│  │                                                              │   │
│  │  ESTIMATED SIZE: 1-10 GB/year depending on file use         │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Redis (Optional Cache)                    │   │
│  │                                                              │   │
│  │  WHY: Fast session data, rate limiting, real-time state     │   │
│  │                                                              │   │
│  │  KEYS:                                                       │   │
│  │  ├─ session:{id}           # Active session state           │   │
│  │  ├─ ratelimit:{api}:{min}  # Rate limit counters            │   │
│  │  ├─ sync:{source}:status   # Real-time sync status          │   │
│  │  └─ cache:email:{id}       # Hot email cache                │   │
│  │                                                              │   │
│  │  NOTE: Already have Redis in stack, extend usage            │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Decision Matrix

| Data Type | Store | Reason |
|-----------|-------|--------|
| Audit events | PostgreSQL | ACID, complex queries, compliance |
| Learning scores | PostgreSQL | Needs transactions, relationships |
| Email metadata | PostgreSQL | Structured, queryable, joins |
| Email content | File System | Large text, not frequently queried |
| Email embeddings | Weaviate | Semantic search |
| Financial transactions | PostgreSQL | ACID, complex queries |
| Financial patterns | PostgreSQL | Aggregations, time series |
| Calendar events | PostgreSQL | Structured, queryable |
| Uploaded files | File System | Binary, large |
| File embeddings | Weaviate | Semantic search in documents |
| OAuth tokens | File System (encrypted) | Security, file-based encryption |
| User preferences | PostgreSQL | Queryable, relationships |
| Topic interests | PostgreSQL + Weaviate | Both queryable and searchable |

#### USER EXPERIENCE Impact

**Invisible to user, but enables:**
- Fast email search (Weaviate)
- Instant preference loading (PostgreSQL)
- Large file support (File System)
- Offline document access (local storage)
- Quick dashboard loads (Redis cache)

**Visible to user:**
- Storage section in Settings showing usage per database
- "Compact Database" button in Settings
- Export/backup options for each data type

---

## 4. Core Features Analysis

### 4.1 Gmail Integration

#### WHAT
Full Gmail access: read, search, mark read/unread, archive, delete (with confirmation).

#### WHY
- Email is central to daily workflow
- AI can prioritize and summarize
- Reduces context-switching to Gmail app
- Enables Pulse email digests

#### HOW

```python
# Architecture
Gmail API (OAuth2)
    │
    ├─► GmailMCPServer (MCP tools)
    │       ├─ gmail_inbox_summary
    │       ├─ gmail_list_emails
    │       ├─ gmail_get_email
    │       ├─ gmail_search (natural language)
    │       ├─ gmail_mark_read
    │       ├─ gmail_mark_unread
    │       ├─ gmail_archive
    │       └─ gmail_delete (double confirm)
    │
    ├─► GmailLearningAgent (learns from behavior)
    │       ├─ SenderImportanceModel
    │       ├─ ContentRelevanceModel
    │       └─ BehaviorTracker
    │
    └─► GmailSyncWorker (background sync)
            ├─ Incremental sync every 5 min
            ├─ Full sync on startup
            └─ Real-time webhook (if configured)
```

#### USER EXPERIENCE

**Chat Commands:**
```
User: "How many unread emails do I have?"
ACMS: "You have 23 unread emails. 3 are from priority contacts."

User: "Show me important unread emails"
ACMS: [Shows prioritized list based on learned importance]

User: "Summarize emails from John this week"
ACMS: [AI summary of John's emails]

User: "Mark the first 5 as read"
ACMS: "Marked 5 emails as read. ✓"

User: "Delete the newsletter from TechCrunch"
ACMS: "⚠️ You're about to delete 1 email:
       • 'This Week in Tech' from newsletter@techcrunch.com

       Type 'confirm delete' to proceed."

User: "confirm delete"
ACMS: "Deleted 1 email. This action is logged in your audit trail."
```

**Sidebar View: "📧 Email" (new)**
- Inbox with smart prioritization
- Quick actions: mark read, archive, star
- Search bar with natural language
- Sender reputation indicators (learned)

**Learning Visibility:**
- Small indicator next to sender: ⭐ (priority), ⚡ (quick responder), 📰 (newsletter)
- "Learning from your behavior" tooltip
- Settings: "View learned senders" → table of sender scores

---

### 4.2 Financial Integration (Plaid)

#### WHAT
Connect bank accounts, view balances, transactions, investments. AI-powered insights.

#### WHY
- Financial awareness without opening 5 apps
- Personalized spending insights
- Portfolio tracking
- "How much did I spend on X?" questions

#### HOW

```python
# Architecture
Plaid API
    │
    ├─► FinanceMCPServer (MCP tools)
    │       ├─ finance_overview
    │       ├─ finance_accounts
    │       ├─ finance_transactions
    │       ├─ finance_portfolio
    │       ├─ finance_insights
    │       └─ finance_ask (natural language)
    │
    ├─► FinanceLearningAgent
    │       ├─ SpendingPatternModel
    │       ├─ PersonalizedAnomalyDetector
    │       └─ FinancialInterestTracker
    │
    └─► PlaidSyncWorker
            ├─ Daily transaction sync
            ├─ Real-time balance check
            └─ Weekly holdings update
```

#### USER EXPERIENCE

**Chat Commands:**
```
User: "What's my net worth?"
ACMS: "Your current net worth is $XXX,XXX.
       • Checking: $X,XXX
       • Savings: $XX,XXX
       • Investments: $XXX,XXX
       • Credit debt: -$X,XXX

       Up 2.3% from last month."

User: "How much did I spend on food this month?"
ACMS: "You've spent $847 on food this month.
       • Restaurants: $523 (12 transactions)
       • Groceries: $324 (8 transactions)

       This is 15% higher than your monthly average of $736.
       Top merchants: Whole Foods ($187), DoorDash ($156)"

User: "Show me unusual transactions"
ACMS: [Shows transactions flagged by personalized anomaly detector]
```

**Sidebar View: "💰 Finance" (new)**
- Net worth card at top
- Account balances
- Recent transactions (smart categorized)
- Spending by category chart
- Portfolio summary (if investments linked)

**Learning Visibility:**
- "Unusual" badge on anomalous transactions
- "Recurring" indicator on detected subscriptions
- Settings: "Spending thresholds" → sliders per category
- Settings: "Alert preferences" → what to notify about

---

### 4.3 Calendar Integration

#### WHAT
View and search calendar events. AI-generated meeting prep notes.

#### WHY
- Context for meetings (who, what was discussed before)
- Agenda planning
- Time awareness in responses

#### HOW

```python
# Architecture
Google Calendar API (OAuth2)
    │
    ├─► CalendarMCPServer
    │       ├─ calendar_today
    │       ├─ calendar_week
    │       ├─ calendar_event_detail
    │       ├─ calendar_free_slots
    │       └─ calendar_prep_notes (AI-generated)
    │
    └─► CalendarLearningAgent
            ├─ MeetingPrepPreferences
            └─ ReminderOptimizer
```

#### USER EXPERIENCE

**Chat Commands:**
```
User: "What's on my calendar today?"
ACMS: "You have 4 events today:
       • 9:00 AM - Team Standup (30 min)
       • 11:00 AM - Client Call with Acme Corp (1 hr)
         📋 Prep: Last discussed pricing on Dec 15.
            They had concerns about implementation timeline.
       • 2:00 PM - Design Review (45 min)
       • 5:00 PM - Gym"

User: "Prepare me for the Acme call"
ACMS: [Detailed prep with context from past conversations, emails]
```

**Learning Visibility:**
- Prep note depth indicator (brief/normal/detailed)
- "Based on your past meetings" explanation
- Settings: "Meeting prep style" preference

---

### 4.4 Browser Session Control

#### WHAT
Control your logged-in ChatGPT, Claude, Gemini sessions via ACMS.

#### WHY
- Use existing subscriptions (ChatGPT Plus, Claude Pro)
- Access features not in API (file upload, image gen)
- ACMS as unified interface
- Save API costs

#### HOW

```python
# Architecture
Playwright Browser
    │
    ├─► BrowserMCPServer
    │       ├─ browser_session_status
    │       ├─ browser_send_to_chatgpt
    │       ├─ browser_send_to_claude
    │       ├─ browser_send_to_gemini
    │       └─ browser_upload_file
    │
    └─► BrowserSessionManager
            ├─ Session persistence
            ├─ Login detection
            └─ Response extraction
```

#### USER EXPERIENCE

**Chat Commands:**
```
User: "Tell ChatGPT to analyze this PDF" [attaches file]
ACMS: "Sending to ChatGPT...

       [ChatGPT's response appears here]

       💡 Response captured and stored in your memory."

User: "Ask Gemini to search for recent news about Rust"
ACMS: "Delegating to Gemini (has web search)...

       [Gemini's response with citations]"
```

**Sidebar View: "🌐 Sessions" (new)**
- Status of each AI session (logged in/logged out)
- "Open in browser" button for each
- Recent delegations log
- Tokens saved vs API calls counter

**Learning Visibility:**
- "Best for this task" indicator based on past delegations
- Success rate per platform
- Average response time per platform

---

### 4.5 File Upload & Processing

#### WHAT
Upload files (PDF, images, spreadsheets), process with AI, store for search.

#### WHY
- Work with documents in ACMS
- Search across all uploaded files
- Extract knowledge from documents

#### HOW

```python
# Architecture
File Upload
    │
    ├─► FileProcessor
    │       ├─ PDF → text extraction → chunking
    │       ├─ Image → OCR + vision analysis
    │       ├─ Excel/CSV → structured parsing
    │       └─ Code → syntax-aware chunking
    │
    ├─► EmbeddingPipeline
    │       └─ Chunk → embed → store in Weaviate
    │
    └─► KnowledgeExtractor
            └─ Extract facts → store as knowledge
```

#### USER EXPERIENCE

**Chat Interface:**
- Drag-and-drop zone in input area
- File preview before sending
- Progress indicator during processing
- "File processed. Ask me anything about it."

**Sidebar View: "📁 Files" (new)**
- List of uploaded files
- Search across all files
- Storage usage
- "Extract knowledge" button per file

---

### 4.6 ACMS Pulse (Proactive Intelligence)

#### WHAT
Daily personalized briefings like ChatGPT Pulse, but local and customizable.

#### WHY
- Start day with relevant information
- Reduce information overload
- Proactive, not just reactive
- Differentiator vs ChatGPT Pulse (privacy, customization)

#### HOW

```python
# Architecture
PulseScheduler (runs at configured time)
    │
    ├─► PulseGenerator
    │       ├─ EmailDigestGenerator (uses GmailLearningAgent)
    │       ├─ CalendarPrepGenerator (uses CalendarAgent)
    │       ├─ FinanceInsightsGenerator (uses FinanceAgent)
    │       ├─ TopicResearchGenerator (uses TopicInterestModel)
    │       └─ PulseRanker (uses PulsePreferenceModel)
    │
    └─► PulseLearningAgent
            ├─ EngagementTracker
            ├─ PreferenceModel
            └─ TopicInterestModel
```

#### USER EXPERIENCE

**New View: "Pulse" (icon: ⚡)**

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚡ Good morning, Rajan!                      December 20, 2025 │
│                                                                 │
│  Your personalized briefing is ready.                          │
│  Learning confidence: ████████░░ 80%                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📧 EMAIL DIGEST                                    [Expand ▼] │
│  ├─ 3 priority emails need attention                           │
│  │   • John Smith: "Re: Q1 Planning" - awaiting your response │
│  │   • Finance Team: Invoice #1234 due tomorrow               │
│  │   • Sarah: Meeting reschedule request                      │
│  ├─ 12 newsletters (auto-archived based on your preferences)  │
│  └─ 👍 👎                                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📅 TODAY'S AGENDA                                  [Expand ▼] │
│  ├─ 9:00 AM - Team Standup                                    │
│  ├─ 11:00 AM - Client Call with Acme Corp                     │
│  │   📋 Prep notes ready (based on your last 3 interactions)  │
│  ├─ 2:00 PM - Design Review                                   │
│  └─ 👍 👎                                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  💰 FINANCIAL SNAPSHOT                              [Expand ▼] │
│  ├─ Portfolio: +1.2% today ($XXX,XXX)                         │
│  ├─ Spending this week: $XXX (on track with budget)           │
│  ├─ ⚠️ Unusual: $89 charge at Apple Store                     │
│  └─ 👍 👎                                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔍 YOUR INTERESTS                                  [Expand ▼] │
│  ├─ Rust: New async features in 1.80 release                  │
│  ├─ AI: Anthropic announced MCP improvements                  │
│  └─ 👍 👎                                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [✨ Curate Tomorrow's Pulse]              [View Full Report]  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Curate Dialog:**
```
What would you like to see in tomorrow's Pulse?

[Text input: "Focus on Kubernetes news, skip crypto updates"]

Or choose from suggestions:
☐ More financial details
☐ Deeper email summaries
☐ Add weather forecast
☐ Include RSS feeds
☑ Skip newsletters summary

[Save Preferences]
```

**Learning Visibility:**
- "Learning confidence" bar shows personalization level
- Thumbs up/down on each section
- "Based on your past week" explanations
- Settings: Full learning profile view

---

## 5. Learning Agents & UI Visibility

### Self-Reflection Analysis

#### WHAT
Learning agents that adapt to user behavior, visible in the UI.

#### WHY
1. **Transparency:** Users should know AI is learning from them
2. **Trust:** Seeing learning builds confidence
3. **Control:** Users can correct/adjust learning
4. **Feedback:** Encourages providing signals

#### HOW: Learning Visibility Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│                 LEARNING VISIBILITY LAYERS                          │
│                                                                     │
│  LAYER 1: SUBTLE INDICATORS (Always visible)                       │
│  ├─ ⭐ Priority sender badge (learned importance > 80)             │
│  ├─ 📈 Trending topic indicator (interest increasing)              │
│  ├─ ⚠️ Anomaly badge on transactions                               │
│  ├─ 🔄 "Learning..." spinner during observation                    │
│  └─ Personalization confidence bar in Pulse                        │
│                                                                     │
│  LAYER 2: EXPLANATIONS (On hover/expand)                           │
│  ├─ "Marked priority because you replied within 5 min 8 times"    │
│  ├─ "Flagged unusual: 3x your average for this category"          │
│  ├─ "Topic boosted: you asked about this 12 times this month"     │
│  └─ "Summarized briefly: you usually skim this sender's emails"   │
│                                                                     │
│  LAYER 3: CONTROLS (In Settings)                                   │
│  ├─ View all learned sender scores with sliders                    │
│  ├─ View/edit topic interests                                      │
│  ├─ Adjust anomaly thresholds per category                        │
│  ├─ Reset learning for specific sender/topic                      │
│  └─ Export learning profile                                        │
│                                                                     │
│  LAYER 4: DASHBOARD (Dedicated view)                               │
│  ├─ Learning summary stats                                         │
│  ├─ Model accuracy metrics                                         │
│  ├─ Feedback history                                               │
│  └─ A/B test results (if running experiments)                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### UI Components for Learning

#### 1. Learning Status Bar (Global, subtle)

```
┌─────────────────────────────────────────────────────────────────────┐
│ ACMS                                    🧠 Learning: Active (156)   │
└─────────────────────────────────────────────────────────────────────┘
                                          ▲
                                          │
                              Click to see: "156 learning signals
                                            captured today"
```

#### 2. Sender Score Tooltip (Email list)

```
┌─────────────────────────────────────────────────────┐
│ John Smith ⭐                                       │
│ john@company.com                                    │
├─────────────────────────────────────────────────────┤
│ 📊 Importance Score: 87/100                        │
│                                                     │
│ Why:                                                │
│ • You replied to 15 of 18 emails                   │
│ • Average reply time: 23 minutes                   │
│ • Last interaction: 2 days ago                     │
│                                                     │
│ [Adjust Score] [Mark Not Priority]                 │
└─────────────────────────────────────────────────────┘
```

#### 3. Learning Profile View (Settings → Learning)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🧠 Your Learning Profile                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ PERSONALIZATION CONFIDENCE                                          │
│ ████████████████████████░░░░░░  80%                                │
│ Based on 2,341 learning signals over 45 days                       │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ EMAIL LEARNING                                                      │
│                                                                     │
│ Priority Contacts (12)                          [View All ▶]       │
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │ John Smith          ████████████████████ 92   [Adjust]     │    │
│ │ Sarah Connor        ███████████████████░ 87   [Adjust]     │    │
│ │ Boss                ██████████████████░░ 85   [Adjust]     │    │
│ └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│ Deprioritized (newsletters you rarely read)     [View All ▶]       │
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │ TechCrunch          ██░░░░░░░░░░░░░░░░░░ 15   [Unblock]    │    │
│ │ Marketing Weekly    █░░░░░░░░░░░░░░░░░░░ 8    [Unblock]    │    │
│ └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ FINANCE LEARNING                                                    │
│                                                                     │
│ Anomaly Thresholds (personalized)               [Adjust All ▶]     │
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │ Restaurants      Alert if > $150  (your avg: $45)          │    │
│ │ Shopping         Alert if > $300  (your avg: $89)          │    │
│ │ Subscriptions    Alert if > $50   (your avg: $15)          │    │
│ └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ TOPIC INTERESTS                                                     │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │ Rust              ████████████████████ High   [Remove]     │    │
│ │ AI/ML             ███████████████████░ High   [Remove]     │    │
│ │ Kubernetes        ██████████████░░░░░░ Medium [Remove]     │    │
│ │ Crypto            ██░░░░░░░░░░░░░░░░░░ Low    [Boost]      │    │
│ └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│ [Add Topic]  [Import from Browser History]                         │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ [Reset All Learning]  [Export Profile]  [Import Profile]           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4. Model Accuracy Dashboard (API Analytics → Learning tab)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🧠 Learning Model Performance                     Last 30 days     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ MODEL                      ACCURACY    SAMPLES    TREND             │
│ ──────────────────────────────────────────────────────────────────  │
│ Sender Importance          82.3%       1,234      📈 +2.1%         │
│ Content Relevance          76.8%       2,456      📈 +1.5%         │
│ Anomaly Detection          89.2%       456        📊 Stable        │
│ Pulse Ranking              71.4%       89         📈 +5.2%         │
│ Topic Interest             84.1%       678        📊 Stable        │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ FEEDBACK SUMMARY                                                    │
│                                                                     │
│ 👍 Positive: 145 (78%)                                             │
│ 👎 Negative: 41 (22%)                                              │
│                                                                     │
│ Top Corrections:                                                    │
│ • "Mark John as priority" (3 times)                                │
│ • "This isn't unusual spending" (5 times)                          │
│ • "Show more AI news" (2 times)                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Phases

### Phase 0: Audit Foundation (Week 1)
**Priority: CRITICAL - Do First**
**Status: ✅ COMPLETE (December 21, 2025)**

| Day | Task | TDD Checkpoint | Status |
|-----|------|----------------|--------|
| 1 | Design audit schema | Tests for event creation pass | ✅ |
| 1 | Create migrations | Schema deploys successfully | ✅ |
| 2 | Implement AuditLogger class | Unit tests for all event types | ✅ |
| 2 | Add audit decorators for existing endpoints | Integration tests pass | ✅ |
| 3 | Create audit REST endpoints | API tests return correct data | ✅ |
| 3 | Build Data Flow UI view | UI renders audit events | ✅ |
| 4 | Implement End of Day report | Report generates correctly | ✅ |
| 4 | Add daily summary rollup | Aggregations match raw events | ✅ |
| 5 | Integration testing | Full flow audit verified | ✅ |

**Verification:**
- [x] Every API call creates audit event
- [x] Daily summary updates correctly
- [x] End of Day report generates
- [x] UI shows real-time events
- [x] No data leaves system without audit

#### Phase 0 Completion Evidence

**Implementation Details:**
- `src/audit/logger.py` - AuditLogger with log_ingress(), log_egress(), log_transform()
- `src/audit/models.py` - AuditEvent, AuditEventType, DataClassification
- `src/audit/endpoints.py` - REST API for dashboard and event queries
- `src/audit/privacy.py` - PrivacyEnforcer blocks confidential→external

**Audit Points Added:**
| Location | Event Type | What's Logged |
|----------|------------|---------------|
| `orchestrator.py:207` | INGRESS | User query received |
| `orchestrator.py:883` | EGRESS | LLM API call (claude_api, openai_api, gemini_api) |
| `api_server.py:3203` | INGRESS | File upload |
| `memory_crud.py:276` | TRANSFORM | Memory creation → Weaviate |

**Test Coverage:**
- 15 integration tests in `tests/integration/test_audit_integration.py`
- All tests passing ✅

**Lessons Learned:**
1. **TDD at integration level, not just unit level** - Unit tests passed but integration was broken
2. **E2E verification is non-negotiable** - "Does a query create an audit event?" must be tested
3. **asyncpg requires JSON serialization** - Fixed metadata dict→JSON string issue

---

### Phase 1: Gmail Integration (Weeks 2-3)
**Priority: HIGH**
**Status: 📋 PLANNED (December 21, 2025)**

---

#### Decision Log: What We're Building & Why

**Date:** December 21, 2025
**Decision Makers:** Product discussion between user and Claude
**Iteration:** 3 (final after PM + Staff Engineer brainstorming)

---

##### The Core Insight (After 3 Iterations)

**We are NOT building an email client. We are building an Email Intelligence Layer.**

| What We're NOT | What We ARE |
|----------------|-------------|
| Superhuman clone | Intelligence layer on top of Gmail |
| Gmail replacement | Gmail augmentation |
| Email CRUD app | Email insights + actions app |
| Full email rendering | Metadata + AI summaries |

**The "Aha" Moment:**
> "I don't need to open Gmail to know what matters. ACMS tells me, and I can act from here."

---

##### Decision 1: Architecture Philosophy

**What:** Delegate email complexity to Gmail, own the intelligence layer
**Why:**
- Gmail does email CRUD well - no value in replicating
- Our unique value is AI intelligence + cross-source context
- Faster to ship, lower risk, higher differentiation
- Users will still have Gmail open - that's okay

**Principle:** "Own the intelligence, delegate the plumbing"

| ACMS Owns | Gmail Does |
|-----------|------------|
| AI summarization | Full HTML rendering |
| Sender importance scoring | Compose/rich text editing |
| Priority classification | Threading/conversation view |
| Cross-source context | Search (initially) |
| Action triggers (tasks, calendar) | Send/receive |

---

##### Decision 2: UX Philosophy (Refined)

**Original (Iteration 1):** Build a Superhuman-inspired email command center
**Refined (Iteration 3):** Build an Email Intelligence Dashboard that surfaces insights

**The Litmus Test:**
> "User knows what emails need attention WITHOUT opening Gmail, and can trigger actions from ACMS."

**What "Act" Means (Pragmatic):**
- ✅ See AI summary of important emails
- ✅ Create ACMS task from email
- ✅ Create calendar event from email
- ✅ Open in Gmail for full view/reply
- 🔜 Reply from ACMS (future)
- 🔜 Snooze/archive from ACMS (future)

---

##### Decision 3: Implementation Order (Pragmatic MVP)

**What:** Start with intelligence dashboard, add CRUD later
**Why:**
- Prove value in 5-7 days, not 3 weeks
- Lower risk (read-only first)
- Ship fast, iterate based on real usage

| Phase | Scope | Days | Risk |
|-------|-------|------|------|
| 1A | Intelligence Dashboard (insights, summaries, priority) | 5-7 | Low |
| 1B | Actions (tasks, calendar, open in Gmail) | 3-4 | Low |
| 1C | CRUD (mark read, archive, reply in ACMS) | 5-7 | Medium |

**What we explicitly DEFER to later phases:**
- ❌ Compose/reply in ACMS → Use Gmail (Phase 1C)
- ❌ Full email body rendering → Link to Gmail
- ❌ Background sync worker → Manual refresh first
- ❌ Keyboard shortcuts → Phase 2
- ❌ Delete from ACMS → Phase 1C

---

##### Decision 4: Learning Model Architecture

**What:** Build architecture for full ML, start with simple scoring
**Why:**
- Ship value fast with simple rules
- Collect behavior data from day 1
- Evolve to ML as data accumulates

| Stage | Model | When |
|-------|-------|------|
| MVP | SenderImportanceModel v1 (reply frequency, recency) | Phase 1A |
| v2 | ContentRelevanceModel (topic matching to ACMS knowledge) | Phase 1C |
| v3 | BehaviorPredictionModel (what will user do with this email?) | Phase 2 |

**Key Learning Signals to Capture:**
- Which emails does user open in Gmail?
- Which emails does user create tasks from?
- Which senders does user reply to fastest?
- Which emails does user ignore?

---

##### Decision 5: Google Cloud Project

**Status:** User has existing Google Cloud project

**OAuth Requirements:**
```
Client Type: Web application
Scopes (Phase 1A): https://www.googleapis.com/auth/gmail.readonly
Scopes (Phase 1C): + gmail.modify, gmail.send
Scopes (Actions): + calendar.events
Redirect URI: http://localhost:40080/oauth/callback
```

**Environment Variables:**
```bash
GOOGLE_CLIENT_ID=<from-user>
GOOGLE_CLIENT_SECRET=<from-user>
GOOGLE_REDIRECT_URI=http://localhost:40080/oauth/callback
```

---

#### Superhuman-Inspired UX Design

##### Email Command Center (NOT a Gmail Clone)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📧 Email Intelligence                                    [Sync: 2 min ago] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 📊 INBOX INSIGHTS                                                    │   │
│  │                                                                      │   │
│  │  Unread: 23        Priority: 5        Needs Reply: 3                │   │
│  │                                                                      │   │
│  │  [PIE CHART: By Sender Type]          [BAR: By Category]            │   │
│  │   ◉ Priority (22%)                     ████████ Work (45%)          │   │
│  │   ◉ Personal (18%)                     █████░░░ Personal (25%)      │   │
│  │   ◉ Newsletters (40%)                  ███░░░░░ Newsletters (20%)   │   │
│  │   ◉ Notifications (20%)                ██░░░░░░ Automated (10%)     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ⚡ NEEDS YOUR ATTENTION (5)                           [Expand All ▼] │   │
│  │                                                                      │   │
│  │  ⭐ John Smith · Q1 Planning Discussion                  10:23 AM   │   │
│  │     📝 Summary: Requesting your input on Q1 budget...               │   │
│  │     [Reply] [Create Task] [Schedule Meeting] [Snooze ▼]             │   │
│  │                                                                      │   │
│  │  ⭐ Sarah Chen · Client Proposal Review                  Yesterday   │   │
│  │     📝 Summary: Final review needed before sending to Acme Corp...  │   │
│  │     [Reply] [Create Task] [Schedule Meeting] [Snooze ▼]             │   │
│  │                                                                      │   │
│  │  ⭐ Finance Team · Invoice #4521 Approval                Yesterday   │   │
│  │     📝 Summary: $12,500 invoice requires your approval...           │   │
│  │     [Approve] [Reject] [Ask Question] [Snooze ▼]                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 📬 RECENT (showing 10 of 156)                    [Filter ▼] [⌘K]    │   │
│  │                                                                      │   │
│  │  ○ TechCrunch Newsletter · This Week in Tech           8:00 AM     │   │
│  │  ○ GitHub · [acms] PR #234 merged                       7:45 AM     │   │
│  │  ● Mike Johnson · Re: Project Update                   Yesterday    │   │
│  │  ○ Slack · New messages in #engineering                Yesterday    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ✅ TODAY'S EMAIL ACTIONS                                             │   │
│  │                                                                      │   │
│  │  • Replied to 3 priority emails                                     │   │
│  │  • Created 2 calendar events from emails                            │   │
│  │  • Archived 12 newsletters                                          │   │
│  │  • Set 1 reminder for follow-up                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [Compose ⌘N]  [Search ⌘K]  [Keyboard Shortcuts ?]                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

##### Key UX Principles

| Principle | Implementation |
|-----------|----------------|
| **Intelligence First** | Show insights/metrics before raw email list |
| **Action-Oriented** | Every email has action buttons (Reply, Task, Meeting, Snooze) |
| **AI Summarization** | One-line summary for every priority email |
| **Keyboard-First** | ⌘K command palette, keyboard shortcuts for all actions |
| **Never Leave ACMS** | Reply, compose, schedule - all in ACMS |
| **Learning Visible** | Priority badges, sender scores shown |

##### Actions Available Per Email

| Action | What It Does | Creates |
|--------|--------------|---------|
| **Reply** | Opens compose in ACMS | Sends via Gmail API |
| **Create Task** | Extract action items → Task | ACMS task + optional reminder |
| **Schedule Meeting** | Opens meeting scheduler | Google Calendar event + Zoom link |
| **Snooze** | Hide until specified time | ACMS reminder, reappears in priority |
| **Archive** | Remove from inbox | Gmail archive + audit log |
| **Mark Important** | Boost sender score | Updates SenderImportanceModel |

---

#### Implementation Plan (Pragmatic MVP - 5-7 Days)

**Philosophy:** Ship intelligence first, add CRUD later. Prove value fast.

##### Phase 1A: Intelligence Dashboard (Days 1-5)
**Goal:** User knows what emails need attention WITHOUT opening Gmail

| Day | Task | TDD Test First | E2E Verification | Audit |
|-----|------|----------------|------------------|-------|
| 1 | OAuth2 flow (read-only scopes) | `test_oauth_flow_returns_tokens` | Consent screen → token | log_ingress(oauth_token) |
| 1 | Token storage & refresh | `test_token_refresh_before_expiry` | Verify refresh works | - |
| 2 | Gmail service layer | `test_gmail_service_connects` | API responds | - |
| 2 | `gmail_inbox_summary` | `test_summary_returns_counts` | Correct unread/total | log_ingress(gmail_sync) |
| 3 | `gmail_list_emails` (metadata) | `test_list_returns_metadata` | Subject, sender, date | log_ingress(gmail_fetch) |
| 3 | SenderImportanceModel v1 | `test_scoring_rules_apply` | Priority contacts scored | - |
| 4 | AI Summarization (priority only) | `test_summary_generated` | LLM summarizes top 5 | log_egress(llm_summarize) |
| 4 | Priority classification | `test_priority_classification` | Top N emails identified | - |
| 5 | Email Intelligence sidebar view | `test_ui_renders_insights` | Pie chart, priority list | - |
| 5 | "Open in Gmail" action | `test_opens_gmail_link` | Click → Gmail tab opens | - |

**Day 5 Checkpoint:** Demo intelligence dashboard with real emails

##### Phase 1B: Actions (Days 6-8)
**Goal:** User can ACT on emails without full CRUD

| Day | Task | TDD Test First | E2E Verification | Audit |
|-----|------|----------------|------------------|-------|
| 6 | "Create Task" from email | `test_task_created_from_email` | Task appears in ACMS | log_transform(task_create) |
| 6 | "Create Calendar Event" | `test_calendar_event_created` | Event in Google Calendar | log_transform(calendar_create) |
| 7 | Manual refresh button | `test_refresh_fetches_new` | New emails appear | log_ingress(gmail_sync) |
| 7 | Learning signal capture | `test_signals_captured` | Opens/tasks logged | - |
| 8 | End-to-end integration test | Full user journey | Complete flow works | All events logged |

**Day 8 Checkpoint:** User can create tasks/calendar from emails

##### Phase 1C: CRUD (Days 9-14) - OPTIONAL EXTENSION
**Goal:** Full email management (defer if Phase 1A/1B prove value)

| Day | Task | TDD Test First | E2E Verification | Audit |
|-----|------|----------------|------------------|-------|
| 9 | `gmail_mark_read/unread` | `test_mark_read_persists` | Verify in Gmail | log_transform(gmail_modify) |
| 9 | `gmail_archive` | `test_archive_removes` | Gone from inbox | log_transform(gmail_modify) |
| 10 | `gmail_delete` with confirm | `test_delete_requires_confirm` | Warning dialog | log_transform(gmail_delete) |
| 11 | Reply compose (basic) | `test_reply_sends` | Verify in Sent | log_egress(gmail_send) |
| 12 | Snooze functionality | `test_snooze_works` | Reappears at time | - |
| 13 | Background sync worker | `test_sync_runs_periodically` | Auto-refreshes | log_ingress(gmail_sync) |
| 14 | Keyboard shortcuts | `test_shortcuts_work` | ⌘K command palette | - |

**Day 14 Checkpoint:** Full email client functionality

---

##### What We Explicitly DEFER (Not Forgotten, Just Later)

| Feature | Why Defer | When to Add |
|---------|-----------|-------------|
| Compose new email | Gmail does this well | Phase 2 |
| Full email body rendering | Link to Gmail sufficient | Phase 2 |
| Background sync worker | Manual refresh first | Phase 1C |
| Keyboard shortcuts | Nice-to-have, not MVP | Phase 1C |
| Snooze | Complex UX, low priority | Phase 1C |
| Thread/conversation view | Gmail does this better | Maybe never |

---

#### Verification Checklist

**Phase 1A (Intelligence Dashboard) - Days 1-5:** ✅ COMPLETE (Dec 21, 2025)
- [x] OAuth connects with read-only scopes
- [x] Emails list with correct metadata (subject, sender, date)
- [x] Inbox insights display correctly (Daily Brief, Insights panels)
- [x] Priority classification works (SenderImportanceModel v1)
- [x] AI summaries generate for priority emails (Gemini 3 Flash)
- [x] "Open in Gmail" links work correctly
- [x] All read operations create audit events
- [x] Timeline selector (7/30/90/120 days) - ADDED
- [x] Accurate unread count from Gmail Labels API - ADDED
- [x] LLM egress audit logging (token counts, cost estimates) - ADDED

**Phase 1B (Actions) - Days 6-8:** ⏸️ PARTIAL (Dec 21, 2025)
- [ ] "Create Task" from email works - DEFERRED to Phase 3 (Calendar integration)
- [ ] "Create Calendar Event" from email works - DEFERRED to Phase 3
- [x] Manual refresh fetches new emails (sync button)
- [x] Learning signals captured (opens tracked via email_actions table)
- [x] End-to-end flow works completely
- [x] Learning signal API: POST /api/gmail/actions
- [x] Learning signal stats: GET /api/gmail/actions/stats

**Phase 1C (CRUD) - Days 9-14 (Optional Extension):** 📋 PLANNED
- [ ] Mark read/unread persists to Gmail
- [ ] Archive removes from inbox view
- [ ] Delete requires confirmation
- [ ] Reply/compose sends successfully
- [ ] Snooze works correctly
- [ ] Background sync runs periodically
- [ ] All write operations create audit events

**The Litmus Test (Phase 1A Complete):** ✅ PASSED
> "User knows what emails need attention WITHOUT opening Gmail, and can trigger actions from ACMS."

- [x] User sees AI summaries of important emails (Gemini 3 Flash powered)
- [ ] User can create ACMS tasks from emails - DEFERRED to Phase 3
- [ ] User can create calendar events from emails - DEFERRED to Phase 3
- [x] User can open specific email in Gmail for full view/reply
- [x] User understands why emails are prioritized (score_factors visible)

---

#### Google Cloud Project Requirements

**What We Need:**
```
1. OAuth 2.0 Client ID (Web application)
2. Client Secret
3. Authorized redirect URI: http://localhost:40080/oauth/callback

Scopes Required:
- https://www.googleapis.com/auth/gmail.readonly (Phase 1A)
- https://www.googleapis.com/auth/gmail.modify (Phase 1B)
- https://www.googleapis.com/auth/gmail.send (Phase 1B)
- https://www.googleapis.com/auth/calendar (Phase 1C)
```

**Environment Variables to Add:**
```bash
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:40080/oauth/callback
```

---

### Phase 1 Technical Design (Staff Engineer Deep Dive)

This section contains the complete technical implementation design for Phase 1 Gmail Integration. Every class, function, and database table is specified with production-quality patterns.

---

#### 1.4.1 Code Organization

**Principle:** Separation of concerns with clear boundaries between layers.

```
src/
├── integrations/
│   └── gmail/
│       ├── __init__.py           # Public API exports
│       ├── oauth.py              # OAuth2 flow + token management
│       ├── client.py             # Gmail API client wrapper
│       ├── models.py             # Data models (Pydantic)
│       ├── service.py            # Business logic layer
│       ├── sender_model.py       # SenderImportanceModel
│       ├── summarizer.py         # AI summarization
│       ├── repository.py         # Database operations
│       └── exceptions.py         # Gmail-specific exceptions
│
├── api/
│   └── gmail_endpoints.py        # REST API endpoints for Gmail
│
└── desktop/
    └── gmail_ui.py               # UI component helpers (optional)

tests/
├── unit/
│   └── integrations/
│       └── gmail/
│           ├── test_oauth.py
│           ├── test_client.py
│           ├── test_sender_model.py
│           ├── test_summarizer.py
│           └── test_service.py
│
└── integration/
    └── test_gmail_integration.py

migrations/
└── 013_gmail_integration.sql     # Database schema
```

**Layer Responsibilities:**

| Layer | File | Responsibility |
|-------|------|----------------|
| **API** | `gmail_endpoints.py` | HTTP request handling, validation, response formatting |
| **Service** | `service.py` | Business logic, orchestration, audit logging |
| **Client** | `client.py` | Gmail API calls, rate limiting, error handling |
| **Repository** | `repository.py` | Database CRUD, caching |
| **Models** | `models.py` | Data structures, validation |
| **OAuth** | `oauth.py` | Token management, encryption, refresh |

**Dependency Flow (strict unidirectional):**
```
API → Service → Client → Gmail API
         ↓
    Repository → PostgreSQL
         ↓
    SenderModel / Summarizer
```

---

#### 1.4.2 Data Model (PostgreSQL Schemas)

**Migration File:** `migrations/013_gmail_integration.sql`

```sql
-- ============================================
-- GMAIL INTEGRATION SCHEMA
-- Migration: 013_gmail_integration.sql
-- Created: December 2025
-- ============================================

-- 1. OAuth Tokens (encrypted at rest)
-- Stores OAuth tokens for all providers (Google, Microsoft, etc.)
CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,              -- 'google', 'microsoft', etc.
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',

    -- Encrypted tokens (Fernet symmetric encryption)
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NOT NULL,

    -- Token metadata
    token_expiry TIMESTAMPTZ NOT NULL,
    scopes TEXT[] NOT NULL,                     -- Array of granted scopes

    -- Account info (from ID token)
    email VARCHAR(255),
    account_name VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,

    -- Constraints
    UNIQUE(provider, user_id)
);

-- Index for token lookup
CREATE INDEX idx_oauth_tokens_provider_user ON oauth_tokens(provider, user_id);
CREATE INDEX idx_oauth_tokens_expiry ON oauth_tokens(token_expiry);


-- 2. Email Metadata (cached, not full content)
-- Stores email metadata for quick access without hitting Gmail API
CREATE TABLE email_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Gmail identifiers
    gmail_message_id VARCHAR(100) UNIQUE NOT NULL,
    gmail_thread_id VARCHAR(100) NOT NULL,

    -- Sender info
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),

    -- Email content (metadata only)
    subject TEXT,
    snippet TEXT,                               -- First ~200 chars from Gmail

    -- Timestamps
    received_at TIMESTAMPTZ NOT NULL,
    internal_date BIGINT,                       -- Gmail internal timestamp

    -- Status
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    is_starred BOOLEAN NOT NULL DEFAULT FALSE,
    is_important BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,

    -- Gmail labels
    labels TEXT[] NOT NULL DEFAULT '{}',

    -- ACMS enrichment
    importance_score DECIMAL(5,2),              -- 0-100 calculated score
    priority_rank INTEGER,                      -- 1, 2, 3... for ordering
    sender_type VARCHAR(50),                    -- 'priority', 'regular', 'newsletter', 'automated'

    -- AI summarization
    ai_summary TEXT,
    ai_summary_model VARCHAR(100),
    ai_summary_generated_at TIMESTAMPTZ,

    -- Sync tracking
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sync_version INTEGER NOT NULL DEFAULT 1,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_email_metadata_sender ON email_metadata(sender_email);
CREATE INDEX idx_email_metadata_received ON email_metadata(received_at DESC);
CREATE INDEX idx_email_metadata_importance ON email_metadata(importance_score DESC NULLS LAST);
CREATE INDEX idx_email_metadata_thread ON email_metadata(gmail_thread_id);
CREATE INDEX idx_email_metadata_unread ON email_metadata(is_read) WHERE is_read = FALSE;
CREATE INDEX idx_email_metadata_priority ON email_metadata(priority_rank) WHERE priority_rank IS NOT NULL;


-- 3. Sender Scores (learned importance)
-- Stores learned importance scores for email senders
CREATE TABLE sender_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Sender identification
    sender_email VARCHAR(255) UNIQUE NOT NULL,
    sender_name VARCHAR(255),
    sender_domain VARCHAR(255) NOT NULL,

    -- Calculated score
    importance_score DECIMAL(5,2) NOT NULL DEFAULT 50.0,

    -- Behavior signals (raw counts)
    total_emails_received INTEGER NOT NULL DEFAULT 0,
    emails_opened INTEGER NOT NULL DEFAULT 0,
    emails_replied_to INTEGER NOT NULL DEFAULT 0,
    emails_archived_unread INTEGER NOT NULL DEFAULT 0,
    emails_deleted INTEGER NOT NULL DEFAULT 0,
    tasks_created_from INTEGER NOT NULL DEFAULT 0,
    calendar_events_from INTEGER NOT NULL DEFAULT 0,
    emails_starred INTEGER NOT NULL DEFAULT 0,

    -- Timing signals
    total_reply_time_minutes DECIMAL(12,2) DEFAULT 0,  -- Sum for avg calculation
    reply_count INTEGER DEFAULT 0,                      -- Count for avg calculation
    avg_reply_time_minutes DECIMAL(10,2) GENERATED ALWAYS AS (
        CASE WHEN reply_count > 0
             THEN total_reply_time_minutes / reply_count
             ELSE NULL
        END
    ) STORED,

    -- Interaction tracking
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_email_at TIMESTAMPTZ,
    last_interaction_at TIMESTAMPTZ,
    last_reply_at TIMESTAMPTZ,

    -- Classification
    sender_type VARCHAR(50) NOT NULL DEFAULT 'unknown',  -- 'priority', 'regular', 'newsletter', 'automated', 'unknown'
    is_in_contacts BOOLEAN NOT NULL DEFAULT FALSE,
    is_manually_prioritized BOOLEAN NOT NULL DEFAULT FALSE,
    is_manually_deprioritized BOOLEAN NOT NULL DEFAULT FALSE,

    -- Model metadata
    score_version INTEGER NOT NULL DEFAULT 1,
    last_score_update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sender_scores_email ON sender_scores(sender_email);
CREATE INDEX idx_sender_scores_domain ON sender_scores(sender_domain);
CREATE INDEX idx_sender_scores_importance ON sender_scores(importance_score DESC);
CREATE INDEX idx_sender_scores_type ON sender_scores(sender_type);


-- 4. Email Actions (for learning)
-- Logs user actions on emails for learning signal capture
CREATE TABLE email_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Email reference
    email_id UUID REFERENCES email_metadata(id) ON DELETE CASCADE,
    gmail_message_id VARCHAR(100) NOT NULL,
    sender_email VARCHAR(255) NOT NULL,

    -- Action details
    action_type VARCHAR(50) NOT NULL,           -- See enum below
    action_source VARCHAR(50) NOT NULL,         -- 'acms', 'gmail_detected', 'sync'

    -- Action-specific metadata
    action_metadata JSONB NOT NULL DEFAULT '{}',

    -- Timing
    action_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- For learning
    is_processed_for_learning BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMPTZ,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Action type enum (documented, not enforced in DB for flexibility)
-- 'open'           - Email was opened/viewed
-- 'mark_read'      - Marked as read
-- 'mark_unread'    - Marked as unread
-- 'archive'        - Archived
-- 'delete'         - Deleted
-- 'star'           - Starred
-- 'unstar'         - Unstarred
-- 'reply'          - Reply sent
-- 'forward'        - Forwarded
-- 'create_task'    - Task created from email
-- 'create_event'   - Calendar event created from email
-- 'open_in_gmail'  - Opened in Gmail (clicked through)
-- 'snooze'         - Snoozed
-- 'unsnooze'       - Unsnoozed

-- Indexes
CREATE INDEX idx_email_actions_email ON email_actions(email_id);
CREATE INDEX idx_email_actions_gmail_id ON email_actions(gmail_message_id);
CREATE INDEX idx_email_actions_sender ON email_actions(sender_email);
CREATE INDEX idx_email_actions_type ON email_actions(action_type);
CREATE INDEX idx_email_actions_unprocessed ON email_actions(is_processed_for_learning)
    WHERE is_processed_for_learning = FALSE;


-- 5. Email Sync State
-- Tracks sync state for incremental Gmail syncing
CREATE TABLE email_sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',

    -- Gmail sync tokens
    history_id BIGINT,                          -- Gmail history ID for incremental sync
    last_full_sync_at TIMESTAMPTZ,
    last_incremental_sync_at TIMESTAMPTZ,

    -- Sync stats
    total_emails_synced INTEGER NOT NULL DEFAULT 0,
    last_sync_emails_count INTEGER DEFAULT 0,
    last_sync_duration_ms INTEGER,

    -- Error tracking
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_error_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id)
);


-- 6. Email Tasks (actions created from emails)
-- Links emails to ACMS tasks/calendar events
CREATE TABLE email_derived_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source email
    email_id UUID REFERENCES email_metadata(id) ON DELETE SET NULL,
    gmail_message_id VARCHAR(100) NOT NULL,

    -- Derived item
    item_type VARCHAR(50) NOT NULL,             -- 'task', 'calendar_event', 'reminder'
    item_id UUID,                               -- Reference to task/event ID
    item_title TEXT NOT NULL,
    item_description TEXT,

    -- For calendar events
    event_start_at TIMESTAMPTZ,
    event_end_at TIMESTAMPTZ,
    event_google_id VARCHAR(255),               -- Google Calendar event ID

    -- Metadata
    created_by VARCHAR(50) NOT NULL DEFAULT 'user',  -- 'user', 'ai_suggested'
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_email_derived_email ON email_derived_items(email_id);
CREATE INDEX idx_email_derived_type ON email_derived_items(item_type);


-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables
CREATE TRIGGER update_oauth_tokens_updated_at
    BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_metadata_updated_at
    BEFORE UPDATE ON email_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sender_scores_updated_at
    BEFORE UPDATE ON sender_scores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_sync_state_updated_at
    BEFORE UPDATE ON email_sync_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_derived_items_updated_at
    BEFORE UPDATE ON email_derived_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- AUDIT INTEGRATION
-- ============================================
-- All Gmail operations should create audit events via application code.
-- See src/integrations/gmail/service.py for audit logging.
```

---

#### 1.4.3 OAuth Token Security

**Security Principles:**
1. Tokens encrypted at rest using Fernet (AES-128-CBC)
2. Encryption key derived from master secret + PBKDF2
3. Tokens never logged, even in debug mode
4. Proactive refresh before expiry
5. Audit logging for all token operations

**Implementation:**

```python
# src/integrations/gmail/oauth.py
"""
OAuth2 Token Management with Encryption at Rest

Security Model:
- Tokens encrypted using Fernet symmetric encryption
- Key derived via PBKDF2 from master secret
- Master secret from env var or machine-derived fallback
- Refresh tokens proactively before expiry
- All operations logged to audit trail
"""

import os
import json
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.audit.logger import get_audit_logger
from src.audit.models import DataClassification
from .exceptions import OAuthError, TokenExpiredError, TokenRefreshError

logger = logging.getLogger(__name__)

# Constants
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
TOKEN_REFRESH_BUFFER_MINUTES = 5  # Refresh 5 min before expiry


@dataclass
class OAuthTokens:
    """Decrypted OAuth tokens with metadata."""
    access_token: str
    refresh_token: str
    expiry: datetime
    scopes: list[str]
    email: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        """Check if token is expired or about to expire."""
        buffer = timedelta(minutes=TOKEN_REFRESH_BUFFER_MINUTES)
        return datetime.utcnow() >= (self.expiry - buffer)


class TokenEncryption:
    """
    Encrypts OAuth tokens at rest using Fernet symmetric encryption.

    Key Derivation:
    - Uses PBKDF2 with SHA256
    - 100,000 iterations (OWASP recommendation)
    - Static salt for deterministic key derivation
    """

    # Static salt - okay because master secret is unique per install
    SALT = b'acms-oauth-tokens-v1'
    ITERATIONS = 100_000

    def __init__(self, master_secret: Optional[str] = None):
        """
        Initialize encryption with master secret.

        Args:
            master_secret: Secret key for encryption. If None, uses
                          ACMS_TOKEN_SECRET env var or machine-derived fallback.
        """
        self.master_secret = master_secret or self._get_master_secret()
        self._fernet = self._create_fernet()

    def _get_master_secret(self) -> str:
        """Get master secret from env or derive from machine."""
        # Priority 1: Environment variable
        secret = os.getenv("ACMS_TOKEN_SECRET")
        if secret:
            return secret

        # Priority 2: Machine-derived (fallback, less secure)
        logger.warning(
            "ACMS_TOKEN_SECRET not set. Using machine-derived secret. "
            "Set ACMS_TOKEN_SECRET in production for better security."
        )
        import uuid
        machine_id = str(uuid.getnode())  # MAC address based
        return f"acms-machine-{machine_id}-oauth-v1"

    def _create_fernet(self) -> Fernet:
        """Create Fernet instance from master secret using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.SALT,
            iterations=self.ITERATIONS,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.master_secret.encode())
        )
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string value."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            raise OAuthError("Failed to decrypt token - key may have changed")


class GoogleOAuthClient:
    """
    Google OAuth2 Client with token management.

    Handles:
    - Authorization URL generation
    - Token exchange (code → tokens)
    - Token refresh
    - Secure storage via TokenEncryption
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        db_pool = None,  # asyncpg pool
    ):
        self.client_id = client_id or os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:40080/oauth/callback"
        )
        self.db_pool = db_pool
        self.encryption = TokenEncryption()

        if not self.client_id or not self.client_secret:
            raise OAuthError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set"
            )

    def get_authorization_url(
        self,
        scopes: list[str],
        state: Optional[str] = None,
    ) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            scopes: List of OAuth scopes to request
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",        # Always show consent for refresh token
        }
        if state:
            params["state"] = state

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        user_id: str = "default",
    ) -> OAuthTokens:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback
            user_id: User identifier for token storage

        Returns:
            OAuthTokens with access and refresh tokens
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise OAuthError(f"Token exchange failed: {response.status_code}")

        data = response.json()

        # Calculate expiry
        expires_in = data.get("expires_in", 3600)
        expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        # Get user info
        email = await self._get_user_email(data["access_token"])

        tokens = OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expiry=expiry,
            scopes=data.get("scope", "").split(),
            email=email,
        )

        # Store encrypted tokens
        await self._store_tokens(tokens, user_id)

        # Audit log
        try:
            audit = get_audit_logger()
            await audit.log_ingress(
                source="oauth",
                operation="token_exchange",
                item_count=1,
                metadata={
                    "provider": "google",
                    "email": email,
                    "scopes": tokens.scopes,
                    # Never log actual tokens!
                }
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

        return tokens

    async def get_valid_token(self, user_id: str = "default") -> str:
        """
        Get a valid access token, refreshing if necessary.

        Args:
            user_id: User identifier

        Returns:
            Valid access token string

        Raises:
            TokenExpiredError: If refresh token is invalid
        """
        tokens = await self._load_tokens(user_id)

        if tokens is None:
            raise OAuthError("No tokens found - user needs to authenticate")

        if tokens.is_expired:
            logger.info("Access token expired, refreshing...")
            tokens = await self._refresh_tokens(tokens, user_id)

        return tokens.access_token

    async def _refresh_tokens(
        self,
        tokens: OAuthTokens,
        user_id: str,
    ) -> OAuthTokens:
        """Refresh expired tokens."""
        if not tokens.refresh_token:
            raise TokenRefreshError("No refresh token available")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": tokens.refresh_token,
                    "grant_type": "refresh_token",
                },
            )

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            raise TokenRefreshError(
                "Token refresh failed - user may need to re-authenticate"
            )

        data = response.json()

        expires_in = data.get("expires_in", 3600)
        expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        new_tokens = OAuthTokens(
            access_token=data["access_token"],
            # Refresh token may not be returned; keep existing
            refresh_token=data.get("refresh_token", tokens.refresh_token),
            expiry=expiry,
            scopes=data.get("scope", "").split() or tokens.scopes,
            email=tokens.email,
        )

        # Update stored tokens
        await self._store_tokens(new_tokens, user_id)

        logger.info("Successfully refreshed OAuth tokens")
        return new_tokens

    async def _get_user_email(self, access_token: str) -> Optional[str]:
        """Get user email from Google userinfo endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            if response.status_code == 200:
                return response.json().get("email")
        except Exception as e:
            logger.warning(f"Failed to get user email: {e}")
        return None

    async def _store_tokens(
        self,
        tokens: OAuthTokens,
        user_id: str,
    ) -> None:
        """Store encrypted tokens in database."""
        encrypted_access = self.encryption.encrypt(tokens.access_token)
        encrypted_refresh = self.encryption.encrypt(tokens.refresh_token)

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO oauth_tokens (
                    provider, user_id,
                    access_token_encrypted, refresh_token_encrypted,
                    token_expiry, scopes, email, last_used_at
                ) VALUES (
                    'google', $1, $2, $3, $4, $5, $6, NOW()
                )
                ON CONFLICT (provider, user_id) DO UPDATE SET
                    access_token_encrypted = EXCLUDED.access_token_encrypted,
                    refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                    token_expiry = EXCLUDED.token_expiry,
                    scopes = EXCLUDED.scopes,
                    email = EXCLUDED.email,
                    last_used_at = NOW(),
                    updated_at = NOW()
            """,
                user_id,
                encrypted_access,
                encrypted_refresh,
                tokens.expiry,
                tokens.scopes,
                tokens.email,
            )

    async def _load_tokens(self, user_id: str) -> Optional[OAuthTokens]:
        """Load and decrypt tokens from database."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    access_token_encrypted,
                    refresh_token_encrypted,
                    token_expiry,
                    scopes,
                    email
                FROM oauth_tokens
                WHERE provider = 'google' AND user_id = $1
            """, user_id)

        if not row:
            return None

        try:
            return OAuthTokens(
                access_token=self.encryption.decrypt(row["access_token_encrypted"]),
                refresh_token=self.encryption.decrypt(row["refresh_token_encrypted"]),
                expiry=row["token_expiry"],
                scopes=list(row["scopes"]) if row["scopes"] else [],
                email=row["email"],
            )
        except OAuthError:
            logger.error("Failed to decrypt stored tokens")
            return None

    async def revoke_tokens(self, user_id: str = "default") -> bool:
        """Revoke tokens and remove from storage."""
        tokens = await self._load_tokens(user_id)

        if tokens:
            # Revoke with Google
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": tokens.access_token},
                    )
            except Exception as e:
                logger.warning(f"Token revocation failed: {e}")

        # Remove from database regardless
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM oauth_tokens
                WHERE provider = 'google' AND user_id = $1
            """, user_id)

        logger.info(f"Revoked tokens for user {user_id}")
        return True
```

---

#### 1.4.4 Gmail API Client Architecture

**Design Principles:**
1. Thin wrapper over Gmail API
2. Automatic retry with exponential backoff
3. Rate limiting awareness
4. Consistent error handling
5. Audit logging for all operations

```python
# src/integrations/gmail/client.py
"""
Gmail API Client Wrapper

Provides a clean interface to Gmail API with:
- Automatic token refresh
- Retry with exponential backoff
- Rate limit handling
- Consistent error handling
- Audit logging
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import asyncio
import base64

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .oauth import GoogleOAuthClient
from .models import EmailMetadata, EmailDetail
from .exceptions import GmailAPIError, RateLimitError, EmailNotFoundError
from src.audit.logger import get_audit_logger

logger = logging.getLogger(__name__)

# Gmail API base URL
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Rate limit settings
MAX_RETRIES = 3
RETRY_MIN_WAIT = 1  # seconds
RETRY_MAX_WAIT = 30  # seconds


class GmailClient:
    """
    Gmail API Client with automatic token refresh and error handling.

    Usage:
        client = GmailClient(oauth_client)
        emails = await client.list_messages(max_results=50)
        email = await client.get_message(message_id)
    """

    def __init__(
        self,
        oauth_client: GoogleOAuthClient,
        user_id: str = "default",
    ):
        self.oauth = oauth_client
        self.user_id = user_id
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with valid token."""
        token = await self.oauth.get_valid_token(self.user_id)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type((httpx.HTTPStatusError, RateLimitError)),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Gmail API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (appended to base URL)
            params: Query parameters
            json_data: JSON body for POST/PUT

        Returns:
            Response JSON as dict

        Raises:
            GmailAPIError: For API errors
            RateLimitError: When rate limited (triggers retry)
        """
        client = await self._get_client()
        headers = await self._get_headers()
        url = f"{GMAIL_API_BASE}{endpoint}"

        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data,
        )

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning(f"Rate limited, waiting {retry_after}s")
            await asyncio.sleep(retry_after)
            raise RateLimitError(f"Rate limited, retry after {retry_after}s")

        # Handle errors
        if response.status_code >= 400:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("error", {}).get("message", response.text)

            if response.status_code == 404:
                raise EmailNotFoundError(f"Resource not found: {endpoint}")

            raise GmailAPIError(
                f"Gmail API error {response.status_code}: {error_msg}"
            )

        return response.json() if response.content else {}

    # ==========================================
    # MESSAGE LISTING
    # ==========================================

    async def list_messages(
        self,
        max_results: int = 50,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        include_spam_trash: bool = False,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List messages in user's mailbox.

        Args:
            max_results: Maximum number of messages to return
            query: Gmail search query (e.g., "from:boss@company.com")
            label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"])
            include_spam_trash: Include spam and trash
            page_token: Token for pagination

        Returns:
            Dict with 'messages' list and optional 'nextPageToken'
        """
        params = {
            "maxResults": min(max_results, 500),  # Gmail API limit
        }

        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids
        if include_spam_trash:
            params["includeSpamTrash"] = "true"
        if page_token:
            params["pageToken"] = page_token

        result = await self._request("GET", "/messages", params=params)

        # Audit log
        try:
            audit = get_audit_logger()
            await audit.log_ingress(
                source="gmail",
                operation="list_messages",
                item_count=len(result.get("messages", [])),
                metadata={
                    "query": query,
                    "max_results": max_results,
                    "has_next_page": "nextPageToken" in result,
                }
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

        return result

    async def get_message(
        self,
        message_id: str,
        format: str = "metadata",  # 'minimal', 'metadata', 'full', 'raw'
        metadata_headers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific message by ID.

        Args:
            message_id: Gmail message ID
            format: Response format level
            metadata_headers: Headers to include if format='metadata'

        Returns:
            Full message data
        """
        params = {"format": format}

        if format == "metadata" and metadata_headers:
            params["metadataHeaders"] = metadata_headers

        result = await self._request(
            "GET",
            f"/messages/{message_id}",
            params=params
        )

        return result

    async def get_message_detail(self, message_id: str) -> EmailDetail:
        """
        Get full message details parsed into EmailDetail model.

        Args:
            message_id: Gmail message ID

        Returns:
            EmailDetail with parsed content
        """
        raw_message = await self.get_message(
            message_id,
            format="full",
        )

        return self._parse_message_detail(raw_message)

    def _parse_message_detail(self, raw: Dict[str, Any]) -> EmailDetail:
        """Parse raw Gmail message into EmailDetail."""
        headers = {
            h["name"].lower(): h["value"]
            for h in raw.get("payload", {}).get("headers", [])
        }

        # Extract body
        body_text = self._extract_body(raw.get("payload", {}))

        return EmailDetail(
            gmail_message_id=raw["id"],
            gmail_thread_id=raw["threadId"],
            sender_email=self._parse_email_address(headers.get("from", "")),
            sender_name=self._parse_sender_name(headers.get("from", "")),
            subject=headers.get("subject", "(no subject)"),
            snippet=raw.get("snippet", ""),
            body_text=body_text,
            received_at=self._parse_internal_date(raw.get("internalDate")),
            labels=raw.get("labelIds", []),
            is_read="UNREAD" not in raw.get("labelIds", []),
            is_starred="STARRED" in raw.get("labelIds", []),
        )

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract plain text body from message payload."""
        # Check for direct body
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8", errors="replace")

        # Check parts (multipart messages)
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                if part.get("body", {}).get("data"):
                    return base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8", errors="replace")
            # Recurse into nested parts
            if part.get("parts"):
                result = self._extract_body(part)
                if result:
                    return result

        return ""

    @staticmethod
    def _parse_email_address(from_header: str) -> str:
        """Extract email address from From header."""
        import re
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1).lower()
        return from_header.lower().strip()

    @staticmethod
    def _parse_sender_name(from_header: str) -> str:
        """Extract sender name from From header."""
        import re
        match = re.search(r'^([^<]+)<', from_header)
        if match:
            return match.group(1).strip().strip('"')
        return ""

    @staticmethod
    def _parse_internal_date(internal_date: Optional[str]) -> datetime:
        """Parse Gmail internal date (milliseconds since epoch)."""
        if internal_date:
            timestamp_ms = int(internal_date)
            return datetime.utcfromtimestamp(timestamp_ms / 1000)
        return datetime.utcnow()

    # ==========================================
    # INBOX SUMMARY
    # ==========================================

    async def get_inbox_summary(self) -> Dict[str, int]:
        """
        Get inbox summary statistics.

        Returns:
            Dict with counts: total, unread, starred, important
        """
        # Get profile for total count
        profile = await self._request("GET", "/profile")

        # Get unread count
        unread_result = await self.list_messages(
            max_results=1,
            label_ids=["INBOX", "UNREAD"],
        )

        # Get starred count
        starred_result = await self.list_messages(
            max_results=1,
            label_ids=["STARRED"],
        )

        return {
            "total_messages": profile.get("messagesTotal", 0),
            "total_threads": profile.get("threadsTotal", 0),
            "unread_estimate": len(unread_result.get("messages", [])),
            "starred_estimate": len(starred_result.get("messages", [])),
            "email": profile.get("emailAddress"),
        }

    # ==========================================
    # LABELS
    # ==========================================

    async def list_labels(self) -> List[Dict[str, Any]]:
        """List all labels in the mailbox."""
        result = await self._request("GET", "/labels")
        return result.get("labels", [])

    # ==========================================
    # HISTORY (for incremental sync)
    # ==========================================

    async def get_history(
        self,
        start_history_id: int,
        label_id: Optional[str] = "INBOX",
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """
        Get message history for incremental sync.

        Args:
            start_history_id: History ID to start from
            label_id: Filter by label
            max_results: Maximum history records

        Returns:
            History data with changes since start_history_id
        """
        params = {
            "startHistoryId": start_history_id,
            "maxResults": max_results,
        }
        if label_id:
            params["labelId"] = label_id

        try:
            return await self._request("GET", "/history", params=params)
        except GmailAPIError as e:
            # History ID may be expired (>7 days)
            if "historyId" in str(e).lower():
                logger.warning("History ID expired, need full sync")
                return {"historyId": None, "history": []}
            raise

    # ==========================================
    # MODIFICATIONS (Phase 1C)
    # ==========================================

    async def modify_message(
        self,
        message_id: str,
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Modify message labels (mark read, archive, etc.).

        Args:
            message_id: Gmail message ID
            add_labels: Labels to add
            remove_labels: Labels to remove

        Returns:
            Modified message data
        """
        body = {}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels

        result = await self._request(
            "POST",
            f"/messages/{message_id}/modify",
            json_data=body
        )

        # Audit log
        try:
            audit = get_audit_logger()
            await audit.log_transform(
                source="gmail",
                operation="modify_message",
                destination="gmail_api",
                item_count=1,
                metadata={
                    "message_id": message_id,
                    "add_labels": add_labels,
                    "remove_labels": remove_labels,
                }
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

        return result

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark message as read."""
        return await self.modify_message(
            message_id,
            remove_labels=["UNREAD"]
        )

    async def mark_as_unread(self, message_id: str) -> Dict[str, Any]:
        """Mark message as unread."""
        return await self.modify_message(
            message_id,
            add_labels=["UNREAD"]
        )

    async def archive_message(self, message_id: str) -> Dict[str, Any]:
        """Archive message (remove from inbox)."""
        return await self.modify_message(
            message_id,
            remove_labels=["INBOX"]
        )

    async def star_message(self, message_id: str) -> Dict[str, Any]:
        """Star a message."""
        return await self.modify_message(
            message_id,
            add_labels=["STARRED"]
        )

    async def trash_message(self, message_id: str) -> Dict[str, Any]:
        """Move message to trash."""
        return await self._request(
            "POST",
            f"/messages/{message_id}/trash"
        )
```

---

#### 1.4.5 SenderImportanceModel v1

**Model Design:**
- Rule-based scoring (no ML yet)
- Explicit, auditable weights
- Designed for easy evolution to ML
- Captures learning signals for future training

```python
# src/integrations/gmail/sender_model.py
"""
Sender Importance Model v1 - Rule-Based Scoring

This model calculates an importance score (0-100) for email senders
based on user behavior signals. V1 uses explicit rules; future versions
will use ML trained on captured behavior data.

Score Interpretation:
- 80-100: Priority sender (always show prominently)
- 60-79:  Regular important sender
- 40-59:  Neutral (default for new senders)
- 20-39:  Low priority (newsletters, etc.)
- 0-19:   Likely automated/spam

Design Principles:
1. Start neutral (50), adjust based on evidence
2. Positive signals increase score
3. Negative signals decrease score
4. Recency matters (recent interactions weighted more)
5. Explicit user actions override algorithm
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)


class SenderType(str, Enum):
    """Sender classification types."""
    PRIORITY = "priority"        # High importance, always show
    REGULAR = "regular"          # Normal importance
    NEWSLETTER = "newsletter"    # Subscriptions, bulk mail
    AUTOMATED = "automated"      # System notifications, receipts
    UNKNOWN = "unknown"          # Not enough data


@dataclass
class SenderSignals:
    """
    Behavioral signals for a sender.

    These are the raw counts and metrics used to calculate
    the importance score.
    """
    sender_email: str
    sender_domain: str

    # Volume signals
    total_emails: int = 0

    # Engagement signals (positive)
    opened_count: int = 0
    replied_count: int = 0
    starred_count: int = 0
    tasks_created: int = 0
    calendar_events_created: int = 0

    # Disengagement signals (negative)
    archived_unread_count: int = 0
    deleted_count: int = 0

    # Timing signals
    avg_reply_time_minutes: Optional[float] = None
    last_interaction_at: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None

    # External data
    is_in_contacts: bool = False

    # User overrides
    is_manually_prioritized: bool = False
    is_manually_deprioritized: bool = False


@dataclass
class SenderScore:
    """
    Calculated importance score with breakdown.

    Includes the final score plus component breakdown
    for transparency and debugging.
    """
    sender_email: str
    score: float                           # 0-100
    sender_type: SenderType

    # Score components (for explainability)
    components: Dict[str, float] = field(default_factory=dict)

    # Metadata
    confidence: float = 0.0                # 0-1, based on data volume
    last_updated: datetime = field(default_factory=datetime.utcnow)


class SenderImportanceModelV1:
    """
    Rule-based sender importance scoring.

    Calculates a 0-100 importance score based on behavioral signals.
    Designed for transparency and easy tuning.
    """

    # ==========================================
    # SCORING WEIGHTS
    # ==========================================

    # Positive signals (add to score)
    WEIGHTS = {
        # Engagement signals
        "reply_rate": {
            "max_contribution": 25.0,
            "description": "Higher score for senders you reply to",
        },
        "open_rate": {
            "max_contribution": 10.0,
            "description": "Higher score for senders you open emails from",
        },
        "fast_reply_bonus": {
            "contribution": 10.0,
            "threshold_minutes": 30,
            "description": "+10 if avg reply time < 30 min",
        },
        "action_creation": {
            "contribution": 10.0,
            "description": "+10 if you've created tasks/events from their emails",
        },
        "starred": {
            "contribution": 5.0,
            "description": "+5 if you've starred their emails",
        },
        "recent_interaction": {
            "contribution": 10.0,
            "threshold_days": 7,
            "description": "+10 if interaction within 7 days",
        },
        "is_contact": {
            "contribution": 10.0,
            "description": "+10 if in your contacts",
        },

        # Negative signals
        "archived_unread_rate": {
            "max_contribution": -20.0,
            "description": "Lower score for senders you archive without reading",
        },
        "deleted_rate": {
            "max_contribution": -25.0,
            "description": "Lower score for senders you delete",
        },
        "newsletter_domain": {
            "contribution": -15.0,
            "description": "-15 for known newsletter domains",
        },
        "no_reply_pattern": {
            "contribution": -10.0,
            "min_emails": 5,
            "description": "-10 if never replied (5+ emails)",
        },
    }

    # Known newsletter/automated sender patterns
    NEWSLETTER_PATTERNS = [
        "substack.com",
        "mailchimp.com",
        "sendgrid.net",
        "constantcontact.com",
        "hubspot.com",
        "marketo.com",
        "noreply@",
        "no-reply@",
        "newsletter@",
        "updates@",
        "notifications@",
        "donotreply@",
        "mailer-daemon@",
        "bounces@",
        "support@",  # Often automated
    ]

    # Base score for new senders
    BASE_SCORE = 50.0

    def calculate_score(self, signals: SenderSignals) -> SenderScore:
        """
        Calculate importance score from behavioral signals.

        Args:
            signals: SenderSignals with behavioral data

        Returns:
            SenderScore with score, type, and breakdown
        """
        # Handle manual overrides first
        if signals.is_manually_prioritized:
            return SenderScore(
                sender_email=signals.sender_email,
                score=95.0,
                sender_type=SenderType.PRIORITY,
                components={"manual_override": 95.0},
                confidence=1.0,
            )

        if signals.is_manually_deprioritized:
            return SenderScore(
                sender_email=signals.sender_email,
                score=10.0,
                sender_type=SenderType.AUTOMATED,
                components={"manual_override": 10.0},
                confidence=1.0,
            )

        # Start at base score
        score = self.BASE_SCORE
        components = {"base": self.BASE_SCORE}

        # Need some emails to calculate rates
        if signals.total_emails == 0:
            return SenderScore(
                sender_email=signals.sender_email,
                score=score,
                sender_type=SenderType.UNKNOWN,
                components=components,
                confidence=0.0,
            )

        # ==========================================
        # POSITIVE SIGNALS
        # ==========================================

        # Reply rate: High reply rate = important sender
        reply_rate = signals.replied_count / signals.total_emails
        reply_contribution = self.WEIGHTS["reply_rate"]["max_contribution"] * reply_rate
        score += reply_contribution
        components["reply_rate"] = round(reply_contribution, 2)

        # Open rate: Opening emails = interested
        open_rate = signals.opened_count / signals.total_emails
        open_contribution = self.WEIGHTS["open_rate"]["max_contribution"] * open_rate
        score += open_contribution
        components["open_rate"] = round(open_contribution, 2)

        # Fast reply bonus: Quick replies = high priority sender
        if signals.avg_reply_time_minutes is not None:
            threshold = self.WEIGHTS["fast_reply_bonus"]["threshold_minutes"]
            if signals.avg_reply_time_minutes < threshold:
                bonus = self.WEIGHTS["fast_reply_bonus"]["contribution"]
                score += bonus
                components["fast_reply_bonus"] = bonus

        # Action creation: Creating tasks/events = actionable emails
        if signals.tasks_created > 0 or signals.calendar_events_created > 0:
            contribution = self.WEIGHTS["action_creation"]["contribution"]
            score += contribution
            components["action_creation"] = contribution

        # Starred: Starring = important
        if signals.starred_count > 0:
            contribution = self.WEIGHTS["starred"]["contribution"]
            score += contribution
            components["starred"] = contribution

        # Recent interaction: Recency matters
        if signals.last_interaction_at:
            days_since = (datetime.utcnow() - signals.last_interaction_at).days
            threshold = self.WEIGHTS["recent_interaction"]["threshold_days"]
            if days_since <= threshold:
                contribution = self.WEIGHTS["recent_interaction"]["contribution"]
                score += contribution
                components["recent_interaction"] = contribution

        # Is contact: Contacts are important
        if signals.is_in_contacts:
            contribution = self.WEIGHTS["is_contact"]["contribution"]
            score += contribution
            components["is_contact"] = contribution

        # ==========================================
        # NEGATIVE SIGNALS
        # ==========================================

        # Archived unread: Archiving without reading = low priority
        archived_unread_rate = signals.archived_unread_count / signals.total_emails
        archived_contribution = (
            self.WEIGHTS["archived_unread_rate"]["max_contribution"]
            * archived_unread_rate
        )
        score += archived_contribution  # Negative value
        if archived_contribution != 0:
            components["archived_unread_rate"] = round(archived_contribution, 2)

        # Deleted: Deleting = not wanted
        deleted_rate = signals.deleted_count / signals.total_emails
        deleted_contribution = (
            self.WEIGHTS["deleted_rate"]["max_contribution"]
            * deleted_rate
        )
        score += deleted_contribution  # Negative value
        if deleted_contribution != 0:
            components["deleted_rate"] = round(deleted_contribution, 2)

        # Newsletter domain: Known newsletter patterns
        if self._is_newsletter_sender(signals.sender_email, signals.sender_domain):
            contribution = self.WEIGHTS["newsletter_domain"]["contribution"]
            score += contribution  # Negative value
            components["newsletter_domain"] = contribution

        # No reply pattern: Never replied to = low priority
        min_emails = self.WEIGHTS["no_reply_pattern"]["min_emails"]
        if signals.total_emails >= min_emails and signals.replied_count == 0:
            contribution = self.WEIGHTS["no_reply_pattern"]["contribution"]
            score += contribution  # Negative value
            components["no_reply_pattern"] = contribution

        # ==========================================
        # FINALIZE
        # ==========================================

        # Clamp score to 0-100
        score = max(0.0, min(100.0, score))

        # Calculate confidence based on data volume
        confidence = min(1.0, signals.total_emails / 20)  # Full confidence at 20 emails

        # Determine sender type
        sender_type = self._classify_sender(score)

        return SenderScore(
            sender_email=signals.sender_email,
            score=round(score, 2),
            sender_type=sender_type,
            components=components,
            confidence=round(confidence, 2),
        )

    def _is_newsletter_sender(self, email: str, domain: str) -> bool:
        """Check if sender looks like a newsletter/automated sender."""
        email_lower = email.lower()
        domain_lower = domain.lower()

        for pattern in self.NEWSLETTER_PATTERNS:
            if pattern in email_lower or pattern in domain_lower:
                return True

        return False

    def _classify_sender(self, score: float) -> SenderType:
        """Classify sender based on score."""
        if score >= 70:
            return SenderType.PRIORITY
        elif score >= 50:
            return SenderType.REGULAR
        elif score >= 30:
            return SenderType.NEWSLETTER
        else:
            return SenderType.AUTOMATED

    def explain_score(self, sender_score: SenderScore) -> str:
        """
        Generate human-readable explanation of score.

        Args:
            sender_score: Calculated SenderScore

        Returns:
            Human-readable explanation string
        """
        lines = [
            f"Importance Score: {sender_score.score}/100 ({sender_score.sender_type.value})",
            f"Confidence: {sender_score.confidence * 100:.0f}%",
            "",
            "Score Breakdown:",
        ]

        for component, value in sender_score.components.items():
            if component == "base":
                continue
            sign = "+" if value > 0 else ""
            weight_info = self.WEIGHTS.get(component, {})
            description = weight_info.get("description", component)
            lines.append(f"  {sign}{value:.1f}: {description}")

        return "\n".join(lines)
```

---

#### 1.4.6 AI Summarization Pipeline

**Design Principles:**
1. Use Gemini Flash for cost-effective summarization
2. Cache summaries to avoid redundant LLM calls
3. Only summarize priority emails (cost control)
4. Prompt optimized for one-sentence actionable summaries

```python
# src/integrations/gmail/summarizer.py
"""
AI Email Summarization Pipeline

Uses Gemini Flash to generate one-sentence summaries of emails.
Designed for efficiency and cost control:
- Only summarizes priority emails
- Caches summaries in database
- Uses short, focused prompts
- Audits all LLM calls
"""

import os
import logging
from datetime import datetime
from typing import Optional

import google.generativeai as genai

from src.audit.logger import get_audit_logger
from src.audit.models import DataClassification

logger = logging.getLogger(__name__)


# ==========================================
# PROMPT TEMPLATES
# ==========================================

SUMMARY_PROMPT = """Summarize this email in ONE sentence (max 100 chars).
Focus on: What action is needed? What's the key information?
Don't start with "This email" or "The sender".
Be specific and actionable.

From: {sender_name} <{sender_email}>
Subject: {subject}

{body}

One-sentence summary:"""


PRIORITY_DETECTION_PROMPT = """Analyze this email and determine if it requires urgent attention.

From: {sender_name} <{sender_email}>
Subject: {subject}
Preview: {snippet}

Respond with ONLY one of:
- URGENT: Needs immediate attention (deadlines, time-sensitive requests)
- ACTION: Needs response or action soon
- INFO: Informational, no action needed
- BULK: Newsletter, promotion, or automated

Category:"""


class EmailSummarizer:
    """
    AI-powered email summarization using Gemini Flash.

    Features:
    - One-sentence summaries optimized for quick scanning
    - Priority detection for email classification
    - Caching to avoid redundant API calls
    - Full audit logging
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.0-flash-exp",
    ):
        """
        Initialize summarizer with Gemini API.

        Args:
            api_key: Google AI API key. Uses GOOGLE_API_KEY env var if not provided.
            model_name: Gemini model to use.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY must be set")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    async def summarize_email(
        self,
        subject: str,
        sender_name: str,
        sender_email: str,
        body: str,
        max_body_length: int = 2000,
    ) -> Optional[str]:
        """
        Generate a one-sentence summary of an email.

        Args:
            subject: Email subject line
            sender_name: Sender's display name
            sender_email: Sender's email address
            body: Email body text
            max_body_length: Maximum body length to send to LLM

        Returns:
            One-sentence summary, or None if summarization fails
        """
        # Truncate body to control token usage
        truncated_body = body[:max_body_length]
        if len(body) > max_body_length:
            truncated_body += "\n[... truncated]"

        prompt = SUMMARY_PROMPT.format(
            sender_name=sender_name or "Unknown",
            sender_email=sender_email,
            subject=subject or "(no subject)",
            body=truncated_body,
        )

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={
                    "max_output_tokens": 100,
                    "temperature": 0.3,  # Low for consistency
                },
            )

            summary = response.text.strip()

            # Ensure it's one sentence (truncate if needed)
            if len(summary) > 150:
                summary = summary[:147] + "..."

            # Audit the LLM call
            await self._audit_summarization(
                sender_email=sender_email,
                input_length=len(prompt),
                output_length=len(summary),
            )

            return summary

        except Exception as e:
            logger.error(f"Email summarization failed: {e}")
            return None

    async def detect_priority(
        self,
        subject: str,
        sender_name: str,
        sender_email: str,
        snippet: str,
    ) -> str:
        """
        Detect email priority category using AI.

        Args:
            subject: Email subject line
            sender_name: Sender's display name
            sender_email: Sender's email address
            snippet: Email preview snippet

        Returns:
            Priority category: 'URGENT', 'ACTION', 'INFO', or 'BULK'
        """
        prompt = PRIORITY_DETECTION_PROMPT.format(
            sender_name=sender_name or "Unknown",
            sender_email=sender_email,
            subject=subject or "(no subject)",
            snippet=snippet or "",
        )

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={
                    "max_output_tokens": 20,
                    "temperature": 0.1,  # Very low for classification
                },
            )

            result = response.text.strip().upper()

            # Validate response
            valid_categories = {"URGENT", "ACTION", "INFO", "BULK"}
            if result in valid_categories:
                return result

            # Try to extract category from response
            for cat in valid_categories:
                if cat in result:
                    return cat

            return "INFO"  # Default

        except Exception as e:
            logger.error(f"Priority detection failed: {e}")
            return "INFO"

    async def batch_summarize(
        self,
        emails: list,
        max_concurrent: int = 5,
    ) -> dict:
        """
        Summarize multiple emails efficiently.

        Args:
            emails: List of dicts with email data
            max_concurrent: Maximum concurrent API calls

        Returns:
            Dict mapping message_id to summary
        """
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def summarize_one(email: dict) -> tuple:
            async with semaphore:
                summary = await self.summarize_email(
                    subject=email.get("subject", ""),
                    sender_name=email.get("sender_name", ""),
                    sender_email=email.get("sender_email", ""),
                    body=email.get("body", email.get("snippet", "")),
                )
                return email.get("message_id"), summary

        tasks = [summarize_one(email) for email in emails]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            msg_id: summary
            for msg_id, summary in results
            if not isinstance(summary, Exception) and summary is not None
        }

    async def _audit_summarization(
        self,
        sender_email: str,
        input_length: int,
        output_length: int,
    ) -> None:
        """Log summarization to audit trail."""
        try:
            audit = get_audit_logger()
            await audit.log_egress(
                source="gmail",
                operation="email_summarization",
                destination="gemini_api",
                data_classification=DataClassification.PUBLIC,
                metadata={
                    "model": self.model_name,
                    "sender_email": sender_email,
                    "input_chars": input_length,
                    "output_chars": output_length,
                    # Rough token estimate
                    "est_input_tokens": input_length // 4,
                    "est_output_tokens": output_length // 4,
                },
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")
```

---

#### 1.4.7 Desktop UI Integration

**Design Principles:**
1. New sidebar item: "📧 Email Intelligence"
2. Follow existing ACMS styling patterns
3. Progressive loading (insights first, then emails)
4. Actions work without leaving ACMS

**File Structure:**
```
desktop-app/src/renderer/
├── components/
│   └── email/
│       ├── emailView.js          # Main email view
│       ├── inboxInsights.js      # Pie chart, stats
│       ├── priorityList.js       # Priority emails list
│       └── emailActions.js       # Action buttons
└── styles/
    └── email.css                 # Email-specific styles
```

**API Endpoints (for UI):**

```python
# src/api/gmail_endpoints.py
"""
Gmail REST API Endpoints for Desktop UI

All endpoints require authentication and create audit events.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


# ==========================================
# MODELS
# ==========================================

class InboxSummary(BaseModel):
    """Inbox overview statistics."""
    total_emails: int
    unread_count: int
    priority_count: int
    needs_reply_count: int
    connected_email: str


class EmailPreview(BaseModel):
    """Email list item preview."""
    message_id: str
    sender_email: str
    sender_name: Optional[str]
    subject: str
    snippet: str
    received_at: str
    is_read: bool
    is_starred: bool
    importance_score: float
    sender_type: str
    ai_summary: Optional[str]


class InboxInsights(BaseModel):
    """Inbox analytics for charts."""
    by_sender_type: dict  # {priority: 5, regular: 20, newsletter: 50, automated: 25}
    by_category: dict     # {work: 45, personal: 25, newsletters: 20, automated: 10}
    unread_by_priority: dict


class EmailListResponse(BaseModel):
    """Paginated email list."""
    emails: List[EmailPreview]
    total_count: int
    has_more: bool
    next_cursor: Optional[str]


class CreateTaskRequest(BaseModel):
    """Request to create task from email."""
    message_id: str
    task_title: Optional[str]  # Auto-generated if not provided
    due_date: Optional[str]


class CreateEventRequest(BaseModel):
    """Request to create calendar event from email."""
    message_id: str
    event_title: Optional[str]
    start_time: str
    end_time: str


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/status")
async def get_connection_status():
    """Check if Gmail is connected."""
    # Returns: {connected: bool, email: str | null, scopes: [...]}
    pass


@router.get("/connect")
async def initiate_oauth():
    """Start OAuth flow, returns authorization URL."""
    # Returns: {auth_url: str}
    pass


@router.get("/callback")
async def oauth_callback(code: str, state: Optional[str] = None):
    """Handle OAuth callback."""
    pass


@router.get("/summary", response_model=InboxSummary)
async def get_inbox_summary():
    """Get inbox overview statistics."""
    pass


@router.get("/insights", response_model=InboxInsights)
async def get_inbox_insights():
    """Get inbox analytics for charts."""
    pass


@router.get("/emails", response_model=EmailListResponse)
async def list_emails(
    limit: int = 50,
    cursor: Optional[str] = None,
    filter: Optional[str] = None,  # 'unread', 'priority', 'starred'
):
    """Get paginated email list."""
    pass


@router.get("/emails/priority", response_model=EmailListResponse)
async def list_priority_emails(limit: int = 10):
    """Get priority emails with AI summaries."""
    pass


@router.get("/emails/{message_id}")
async def get_email_detail(message_id: str):
    """Get full email details."""
    pass


@router.post("/emails/{message_id}/read")
async def mark_as_read(message_id: str):
    """Mark email as read."""
    pass


@router.post("/emails/{message_id}/star")
async def toggle_star(message_id: str):
    """Toggle email star."""
    pass


@router.post("/emails/{message_id}/archive")
async def archive_email(message_id: str):
    """Archive email."""
    pass


@router.post("/emails/{message_id}/task", response_model=dict)
async def create_task_from_email(message_id: str, request: CreateTaskRequest):
    """Create ACMS task from email."""
    pass


@router.post("/emails/{message_id}/event", response_model=dict)
async def create_event_from_email(message_id: str, request: CreateEventRequest):
    """Create calendar event from email."""
    pass


@router.get("/emails/{message_id}/gmail-link")
async def get_gmail_link(message_id: str):
    """Get direct link to email in Gmail."""
    # Returns: {url: "https://mail.google.com/mail/u/0/#inbox/..."}
    pass


@router.post("/sync")
async def trigger_sync():
    """Manually trigger email sync."""
    pass


@router.get("/senders")
async def list_sender_scores(
    limit: int = 50,
    sort_by: str = "importance_score",  # or 'email_count', 'last_interaction'
):
    """Get sender importance scores for learning visibility."""
    pass


@router.post("/senders/{sender_email}/priority")
async def set_sender_priority(sender_email: str, is_priority: bool):
    """Manually set sender as priority/not priority."""
    pass
```

---

### Phase 1 TDD Test Specifications

**Test Organization:**
```
tests/
├── unit/
│   └── integrations/
│       └── gmail/
│           ├── test_oauth.py           # 12 tests
│           ├── test_client.py          # 15 tests
│           ├── test_sender_model.py    # 18 tests
│           ├── test_summarizer.py      # 8 tests
│           └── test_service.py         # 10 tests
│
└── integration/
    ├── test_gmail_oauth_flow.py        # 5 tests
    ├── test_gmail_sync.py              # 8 tests
    └── test_gmail_actions.py           # 10 tests
```

**Unit Tests (Write First):**

```python
# tests/unit/integrations/gmail/test_sender_model.py
"""
TDD Tests for SenderImportanceModel v1

Write these tests BEFORE implementing the model.
"""

import pytest
from datetime import datetime, timedelta

from src.integrations.gmail.sender_model import (
    SenderImportanceModelV1,
    SenderSignals,
    SenderType,
)


class TestSenderImportanceModelV1:
    """Test the rule-based sender importance model."""

    @pytest.fixture
    def model(self):
        return SenderImportanceModelV1()

    # ==========================================
    # BASE SCORE TESTS
    # ==========================================

    def test_new_sender_gets_neutral_score(self, model):
        """New sender with no history should get 50 (neutral)."""
        signals = SenderSignals(
            sender_email="new@example.com",
            sender_domain="example.com",
            total_emails=0,
        )
        result = model.calculate_score(signals)
        assert result.score == 50.0
        assert result.sender_type == SenderType.UNKNOWN
        assert result.confidence == 0.0

    def test_minimal_history_low_confidence(self, model):
        """Sender with few emails should have low confidence."""
        signals = SenderSignals(
            sender_email="test@example.com",
            sender_domain="example.com",
            total_emails=3,
            opened_count=2,
        )
        result = model.calculate_score(signals)
        assert result.confidence < 0.5

    def test_sufficient_history_high_confidence(self, model):
        """Sender with 20+ emails should have full confidence."""
        signals = SenderSignals(
            sender_email="test@example.com",
            sender_domain="example.com",
            total_emails=25,
            opened_count=20,
        )
        result = model.calculate_score(signals)
        assert result.confidence == 1.0

    # ==========================================
    # POSITIVE SIGNAL TESTS
    # ==========================================

    def test_high_reply_rate_increases_score(self, model):
        """Sender you always reply to should score high."""
        signals = SenderSignals(
            sender_email="boss@company.com",
            sender_domain="company.com",
            total_emails=10,
            replied_count=9,  # 90% reply rate
            opened_count=10,
        )
        result = model.calculate_score(signals)
        assert result.score > 70
        assert "reply_rate" in result.components
        assert result.components["reply_rate"] > 20

    def test_fast_reply_time_adds_bonus(self, model):
        """Quick reply time should add bonus points."""
        signals = SenderSignals(
            sender_email="urgent@company.com",
            sender_domain="company.com",
            total_emails=10,
            replied_count=5,
            avg_reply_time_minutes=15,  # Fast!
        )
        result = model.calculate_score(signals)
        assert "fast_reply_bonus" in result.components
        assert result.components["fast_reply_bonus"] == 10.0

    def test_slow_reply_no_bonus(self, model):
        """Slow reply time should not add bonus."""
        signals = SenderSignals(
            sender_email="test@example.com",
            sender_domain="example.com",
            total_emails=10,
            replied_count=5,
            avg_reply_time_minutes=120,  # 2 hours
        )
        result = model.calculate_score(signals)
        assert "fast_reply_bonus" not in result.components

    def test_task_creation_increases_score(self, model):
        """Creating tasks from sender's emails should increase score."""
        signals = SenderSignals(
            sender_email="project@company.com",
            sender_domain="company.com",
            total_emails=10,
            tasks_created=3,
        )
        result = model.calculate_score(signals)
        assert "action_creation" in result.components

    def test_calendar_event_creation_increases_score(self, model):
        """Creating calendar events from emails should increase score."""
        signals = SenderSignals(
            sender_email="meetings@company.com",
            sender_domain="company.com",
            total_emails=10,
            calendar_events_created=2,
        )
        result = model.calculate_score(signals)
        assert "action_creation" in result.components

    def test_recent_interaction_adds_bonus(self, model):
        """Recent interaction should add bonus points."""
        signals = SenderSignals(
            sender_email="recent@example.com",
            sender_domain="example.com",
            total_emails=10,
            opened_count=5,
            last_interaction_at=datetime.utcnow() - timedelta(days=2),
        )
        result = model.calculate_score(signals)
        assert "recent_interaction" in result.components

    def test_old_interaction_no_bonus(self, model):
        """Old interaction should not add bonus."""
        signals = SenderSignals(
            sender_email="old@example.com",
            sender_domain="example.com",
            total_emails=10,
            opened_count=5,
            last_interaction_at=datetime.utcnow() - timedelta(days=30),
        )
        result = model.calculate_score(signals)
        assert "recent_interaction" not in result.components

    def test_contact_adds_bonus(self, model):
        """Being in contacts should add bonus."""
        signals = SenderSignals(
            sender_email="friend@example.com",
            sender_domain="example.com",
            total_emails=5,
            is_in_contacts=True,
        )
        result = model.calculate_score(signals)
        assert "is_contact" in result.components

    # ==========================================
    # NEGATIVE SIGNAL TESTS
    # ==========================================

    def test_high_archive_unread_rate_decreases_score(self, model):
        """Archiving emails unread should decrease score."""
        signals = SenderSignals(
            sender_email="boring@newsletter.com",
            sender_domain="newsletter.com",
            total_emails=20,
            archived_unread_count=18,  # 90% archived unread
        )
        result = model.calculate_score(signals)
        assert result.score < 50
        assert "archived_unread_rate" in result.components
        assert result.components["archived_unread_rate"] < 0

    def test_high_delete_rate_decreases_score(self, model):
        """Deleting emails should significantly decrease score."""
        signals = SenderSignals(
            sender_email="spam@example.com",
            sender_domain="example.com",
            total_emails=10,
            deleted_count=8,  # 80% deleted
        )
        result = model.calculate_score(signals)
        assert result.score < 40
        assert "deleted_rate" in result.components

    def test_newsletter_domain_decreases_score(self, model):
        """Known newsletter domains should decrease score."""
        signals = SenderSignals(
            sender_email="updates@substack.com",
            sender_domain="substack.com",
            total_emails=5,
        )
        result = model.calculate_score(signals)
        assert "newsletter_domain" in result.components
        assert result.components["newsletter_domain"] < 0

    def test_noreply_address_decreases_score(self, model):
        """noreply@ addresses should decrease score."""
        signals = SenderSignals(
            sender_email="noreply@company.com",
            sender_domain="company.com",
            total_emails=5,
        )
        result = model.calculate_score(signals)
        assert result.sender_type in [SenderType.NEWSLETTER, SenderType.AUTOMATED]

    def test_never_replied_pattern_decreases_score(self, model):
        """Never replying after many emails should decrease score."""
        signals = SenderSignals(
            sender_email="ignored@example.com",
            sender_domain="example.com",
            total_emails=10,  # More than threshold
            replied_count=0,  # Never replied
            opened_count=10,  # But opened
        )
        result = model.calculate_score(signals)
        assert "no_reply_pattern" in result.components

    # ==========================================
    # MANUAL OVERRIDE TESTS
    # ==========================================

    def test_manual_priority_override(self, model):
        """Manually prioritized sender should always score high."""
        signals = SenderSignals(
            sender_email="vip@example.com",
            sender_domain="example.com",
            total_emails=1,
            is_manually_prioritized=True,
        )
        result = model.calculate_score(signals)
        assert result.score >= 90
        assert result.sender_type == SenderType.PRIORITY
        assert result.confidence == 1.0

    def test_manual_depriority_override(self, model):
        """Manually deprioritized sender should always score low."""
        signals = SenderSignals(
            sender_email="blocked@example.com",
            sender_domain="example.com",
            total_emails=100,
            replied_count=50,  # Would normally score high
            is_manually_deprioritized=True,
        )
        result = model.calculate_score(signals)
        assert result.score <= 15
        assert result.sender_type == SenderType.AUTOMATED

    # ==========================================
    # CLASSIFICATION TESTS
    # ==========================================

    def test_priority_classification(self, model):
        """High scores should be classified as PRIORITY."""
        signals = SenderSignals(
            sender_email="boss@company.com",
            sender_domain="company.com",
            total_emails=20,
            replied_count=18,
            opened_count=20,
            avg_reply_time_minutes=10,
            is_in_contacts=True,
        )
        result = model.calculate_score(signals)
        assert result.sender_type == SenderType.PRIORITY

    def test_newsletter_classification(self, model):
        """Low-medium scores from newsletters should be NEWSLETTER."""
        signals = SenderSignals(
            sender_email="news@techcrunch.com",
            sender_domain="techcrunch.com",
            total_emails=50,
            opened_count=10,  # 20% open rate
            archived_unread_count=35,
        )
        result = model.calculate_score(signals)
        assert result.sender_type in [SenderType.NEWSLETTER, SenderType.AUTOMATED]

    # ==========================================
    # SCORE BOUNDS TESTS
    # ==========================================

    def test_score_never_below_zero(self, model):
        """Score should never go below 0."""
        signals = SenderSignals(
            sender_email="terrible@spam.com",
            sender_domain="spam.com",
            total_emails=100,
            deleted_count=100,
            archived_unread_count=0,  # All deleted
        )
        result = model.calculate_score(signals)
        assert result.score >= 0

    def test_score_never_above_hundred(self, model):
        """Score should never go above 100."""
        signals = SenderSignals(
            sender_email="perfect@company.com",
            sender_domain="company.com",
            total_emails=100,
            replied_count=100,
            opened_count=100,
            starred_count=50,
            tasks_created=20,
            calendar_events_created=10,
            avg_reply_time_minutes=5,
            is_in_contacts=True,
            last_interaction_at=datetime.utcnow(),
        )
        result = model.calculate_score(signals)
        assert result.score <= 100
```

---

### Phase 1 Testing Checkpoints

**Checkpoint 1: OAuth Flow (Day 1)**
```bash
# Test OAuth implementation
pytest tests/unit/integrations/gmail/test_oauth.py -v

# Expected: All 12 tests pass
# ✓ test_authorization_url_generation
# ✓ test_code_exchange
# ✓ test_token_encryption
# ✓ test_token_storage
# ✓ test_token_refresh
# ✓ test_expired_token_detection
# etc.

# E2E Verification:
# 1. Start ACMS
# 2. Navigate to Settings → Integrations
# 3. Click "Connect Gmail"
# 4. Complete Google consent
# 5. Verify token stored in database
```

**Checkpoint 2: Gmail API Client (Day 2)**
```bash
# Test Gmail client
pytest tests/unit/integrations/gmail/test_client.py -v

# Expected: All 15 tests pass
# ✓ test_list_messages
# ✓ test_get_message
# ✓ test_parse_email_headers
# ✓ test_rate_limit_handling
# ✓ test_error_handling
# etc.

# E2E Verification:
# 1. Use ACMS chat: "How many unread emails do I have?"
# 2. Verify response includes correct count
# 3. Check audit_events for gmail ingress
```

**Checkpoint 3: Sender Model (Day 3)**
```bash
# Test sender importance model
pytest tests/unit/integrations/gmail/test_sender_model.py -v

# Expected: All 18 tests pass
# Run BEFORE implementation (TDD)

# E2E Verification:
# 1. Sync emails
# 2. Check sender_scores table populated
# 3. Verify priority senders at top of list
```

**Checkpoint 4: AI Summarization (Day 4)**
```bash
# Test summarization
pytest tests/unit/integrations/gmail/test_summarizer.py -v

# Expected: All 8 tests pass

# E2E Verification:
# 1. View priority emails
# 2. Verify AI summaries displayed
# 3. Check audit_events for gemini egress
```

**Checkpoint 5: Desktop UI (Day 5)**
```bash
# Integration tests
pytest tests/integration/test_gmail_sync.py -v

# E2E Verification:
# 1. Open Email Intelligence view
# 2. Verify:
#    - Inbox insights pie chart
#    - Priority email list
#    - AI summaries
#    - "Open in Gmail" works
# 3. Check all audit events created
```

**Checkpoint 6: Actions (Day 6-7)**
```bash
# Test actions
pytest tests/integration/test_gmail_actions.py -v

# E2E Verification:
# 1. Create task from email → verify in Tasks view
# 2. Create calendar event → verify in Google Calendar
# 3. Check email_derived_items table
# 4. Check email_actions table for learning signals
```

**Checkpoint 7: Full Integration (Day 8)**
```bash
# Full test suite
pytest tests/ -v --cov=src/integrations/gmail

# Expected:
# - All tests pass
# - Coverage > 85%

# E2E User Journey:
# 1. Connect Gmail
# 2. View inbox insights
# 3. See priority emails with summaries
# 4. Create task from email
# 5. Open email in Gmail
# 6. Return to ACMS, verify action logged
# 7. Check all audit events complete
```

---

### Phase 1.5: Unified Intelligence Layer
**Priority: HIGH**
**Status: DESIGN COMPLETE**
**Full Spec:** `docs/UNIFIED_INTELLIGENCE_ARCHITECTURE.md`

---

#### 1.5.1 Problem Statement

**Current State:** Each data source (AI Chat, Email, Financial, Calendar) is siloed. Users cannot ask cross-source questions like:
- "What emails relate to my AWS spending?" (Email + Financial)
- "Who should I follow up with this week?" (Email + Calendar)
- "What did I discuss with Sarah about budgets?" (Chat + Email)

**Desired State:** A unified intelligence layer where:
1. Each source extracts **insights** (not raw data) into a common format
2. Insights are vectorized for semantic search
3. A query router understands which sources to search
4. Responses cite their sources clearly
5. Privacy is maintained (financial amounts never to LLM)

---

#### 1.5.2 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      UNIFIED INTELLIGENCE ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  DATA SOURCES              INSIGHT EXTRACTORS           UNIFIED STORE            │
│  ────────────              ──────────────────           ─────────────            │
│                                                                                  │
│  ┌─────────────┐          ┌────────────────────┐       ┌────────────────────┐   │
│  │ AI Chats    │──────────│ KnowledgeExtractor │──────▶│ PostgreSQL:        │   │
│  │ (97K mems)  │          │ (existing)         │       │ unified_insights   │   │
│  └─────────────┘          └────────────────────┘       │                    │   │
│                                                        │ - insight_id       │   │
│  ┌─────────────┐          ┌────────────────────┐       │ - source           │   │
│  │ Email       │──────────│ EmailInsight       │──────▶│ - insight_type     │   │
│  │ (Gmail)     │          │ Extractor (NEW)    │       │ - entities (JSONB) │   │
│  └─────────────┘          └────────────────────┘       │ - privacy_level    │   │
│                                                        └────────────────────┘   │
│  ┌─────────────┐          ┌────────────────────┐                │              │
│  │ Financial   │──────────│ FinanceInsight     │                │              │
│  │ (Phase 2)   │          │ Extractor (NEW)    │                ▼              │
│  └─────────────┘          │ NO AMOUNTS TO LLM  │       ┌────────────────────┐   │
│                           └────────────────────┘       │ Weaviate:          │   │
│  ┌─────────────┐                                       │ ACMS_Insights_v1   │   │
│  │ Calendar    │          ┌────────────────────┐       │                    │   │
│  │ (Phase 3)   │──────────│ CalendarInsight    │──────▶│ - insight_vector   │   │
│  └─────────────┘          │ Extractor (NEW)    │       │ - source_tags      │   │
│                           └────────────────────┘       │ - entity_refs      │   │
│                                                        └────────────────────┘   │
│                                                                 │               │
│                                                                 ▼               │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                          QUERY ROUTER                                     │   │
│  │                                                                           │   │
│  │  1. Detect intent + entities (people, topics, dates)                     │   │
│  │  2. Determine which sources to query based on entity types               │   │
│  │  3. Execute parallel search across relevant sources                      │   │
│  │  4. Aggregate results with source attribution                            │   │
│  │  5. Return response with proper citations                                │   │
│  │                                                                           │   │
│  │  Example: "emails about AWS spending"                                    │   │
│  │  → Detects: topic="AWS", topic="spending"                                │   │
│  │  → Routes to: Email insights + Financial patterns (no amounts)           │   │
│  │  → Returns: Emails with vendor mentions + spending categories            │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

#### 1.5.3 Implementation Plan

**Week 1: Foundation**
- Day 1-2: Create `unified_insights` PostgreSQL table + migration
- Day 2-3: Create `ACMS_Insights_v1` Weaviate collection
- Day 3-4: Build base `InsightExtractor` class with common interface

**Week 2: Email Insights**
- Day 1-2: Implement `EmailInsightExtractor`
  - Extract action items from emails
  - Extract key dates/deadlines
  - Categorize email topics
- Day 3-4: Build batch extraction job for existing emails
- Day 5: Write TDD tests for email insight extraction

**Week 3: Query Router**
- Day 1-2: Build intent + entity detection for cross-source queries
- Day 3-4: Implement parallel source search with aggregation
- Day 5: Add source citations to responses

**Week 4: Integration**
- Day 1-2: Integrate query router with chat pipeline
- Day 3-4: Add UI indicators for cross-source answers
- Day 5: E2E testing

---

#### 1.5.4 Privacy Rules

| Rule | Description |
|------|-------------|
| Financial amounts | NEVER sent to LLM - only patterns/categories |
| Raw email content | Only summaries/insights stored in unified layer |
| Confidential data | Never leaves local storage |
| Entity references | Use reference IDs, not PII directly |

---

#### 1.5.5 Success Criteria

1. Cross-source queries work for Email + Chat
2. Query router correctly identifies which sources to search
3. Responses include source citations
4. No financial amounts ever sent to LLM
5. Latency < 3s for cross-source queries

---

### Phase 2: Financial Integration (Weeks 4-5)
**Priority: HIGH**
**Status: ✅ COMPLETE (2A/2B) | ⏸️ DEFERRED (2C/2D)**

#### Completion Summary (December 23, 2025)
| Stage | Status | What Was Built |
|-------|--------|----------------|
| **2A** | ✅ Complete | Plaid OAuth, token encryption, holdings/transactions sync |
| **2B** | ✅ Complete | 25 Constitution rules, Advisor dashboard, health score, principle cards |
| **2C** | ⏸️ Deferred | Pulse integration (waiting for Phase 6) |
| **2D** | ⏸️ Deferred | Fundamentals data (R11/R12 quality scores) |

**Key UX Improvements:**
- Transformed technical rule checklist into "Advisor + Principles" layout
- Portfolio health score (0-100) with natural language commentary
- 6 principle cards with expandable rule details
- Quick action buttons for suggested improvements
- Progressive disclosure (summary → detail)

---

#### Phase 2 Technical Design (FinTech Compliance Standards)

This section contains a comprehensive 3-pass analysis of Phase 2 implementation, designed to FinTech compliance standards from the ground up. Every decision is made with enterprise-grade security, privacy, and operational rigor.

---

##### Pass 1: Security & Compliance Architecture

###### 1.1 Data Classification Matrix

| Data Type | Classification | Storage | Encryption | LLM Allowed | Retention |
|-----------|---------------|---------|------------|-------------|-----------|
| Plaid Access Token | SECRET | PostgreSQL | Fernet (AES-256) | ❌ NEVER | Until revoked |
| Account Numbers (masked) | PII | PostgreSQL | AES-256-GCM | ❌ NEVER | User discretion |
| Full Account Numbers | PII-SENSITIVE | ❌ Never stored | N/A | ❌ NEVER | Never |
| Transaction Amounts | FINANCIAL | PostgreSQL | AES-256-GCM | ❌ NEVER | User discretion |
| Transaction Merchant | FINANCIAL | PostgreSQL | AES-256-GCM | ⚠️ Aggregated only | 7 years |
| Balance Data | FINANCIAL | PostgreSQL | AES-256-GCM | ❌ NEVER | Real-time only |
| Spending Categories | DERIVED | PostgreSQL | Plain (non-PII) | ✅ Categories only | User discretion |
| Anomaly Flags | DERIVED | PostgreSQL | Plain | ✅ Alert text only | 90 days |

**Key Principle:** Financial amounts, account numbers, and identifiers are NEVER sent to any LLM API. Only derived insights (categories, anomaly descriptions) may be used for NL processing.

###### 1.2 Token Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PLAID TOKEN SECURITY                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────────────────┐ │
│  │  Plaid Link  │───►│  Link Token      │───►│  Public Token          │ │
│  │  (Frontend)  │    │  (short-lived)   │    │  (one-time exchange)   │ │
│  └──────────────┘    └──────────────────┘    └───────────┬────────────┘ │
│                                                          │              │
│                                     ┌────────────────────▼──────────────┤
│                                     │  Backend Token Exchange           │
│                                     │  POST /api/plaid/exchange         │
│                                     │  - Public token → Access token    │
│                                     │  - Immediate encryption           │
│                                     │  - Never logged in plain text     │
│                                     └────────────────────┬──────────────┤
│                                                          │              │
│  ┌──────────────────────────────────────────────────────▼──────────────┤
│  │  ENCRYPTED STORAGE                                                   │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  │  Table: plaid_tokens                                            │ │
│  │  │  - access_token_encrypted: Fernet(AES-256-CBC + HMAC)           │ │
│  │  │  - item_id: UUID (for revocation)                               │ │
│  │  │  - institution_id: VARCHAR                                      │ │
│  │  │  - consent_expiration: TIMESTAMPTZ                              │ │
│  │  │  - last_successful_sync: TIMESTAMPTZ                            │ │
│  │  └─────────────────────────────────────────────────────────────────┘ │
│  │                                                                       │
│  │  Encryption Key: PLAID_ENCRYPTION_KEY env var                        │
│  │  Key Rotation: Supported via versioned Fernet keys                   │
│  │  Key Storage: Environment variable (not in code/config files)        │
│  └───────────────────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────────────┘
```

###### 1.3 PCI-DSS Alignment (SAQ-A Equivalent)

ACMS does NOT store, process, or transmit full card numbers (PAN). We operate as a data aggregator using Plaid's tokenized approach:

| PCI-DSS Requirement | ACMS Approach |
|---------------------|---------------|
| Req 3: Protect stored data | Full account numbers never stored |
| Req 4: Encrypt transmission | HTTPS only, TLS 1.3 |
| Req 6: Secure systems | Dependency scanning, no known vulns |
| Req 7: Restrict access | Single-user local deployment |
| Req 10: Track access | Full audit trail via audit_events |
| Req 12: Security policy | This document + ACMS_ARCHITECTURE |

###### 1.4 SOC 2 Control Mapping

| SOC 2 Trust Criteria | ACMS Control |
|---------------------|--------------|
| CC6.1: Logical access | Local-only deployment, no network exposure |
| CC6.6: System boundaries | Docker containers with network isolation |
| CC6.7: Disposal | Secure token revocation via Plaid API |
| CC7.1: Detect anomalies | Audit event monitoring, unusual access patterns |
| CC7.2: Evaluate events | Audit log analysis, privacy violation tracking |

---

##### Pass 2: Privacy & Data Governance

###### 2.1 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FINANCIAL DATA FLOW (Privacy-First)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐     ┌────────────────┐     ┌──────────────────────────┐   │
│  │  Plaid   │────►│ ACMS Backend   │────►│ Local PostgreSQL         │   │
│  │  API     │     │ (Python)       │     │ (Encrypted at rest)      │   │
│  └──────────┘     └───────┬────────┘     └──────────────────────────┘   │
│                           │                                              │
│                           │ AUDIT LOG                                    │
│                           ▼                                              │
│                   ┌───────────────────────────────────────────────────┐ │
│                   │  audit_events table                                │ │
│                   │  - source: 'plaid'                                 │ │
│                   │  - operation: 'sync_accounts' | 'sync_transactions'│ │
│                   │  - data_classification: 'financial'                │ │
│                   │  - item_count: N                                   │ │
│                   │  - NO financial values in metadata                 │ │
│                   └───────────────────────────────────────────────────┘ │
│                                                                          │
│                   ┌───────────────────────────────────────────────────┐ │
│                   │  ❌ BLOCKED: LLM EGRESS                            │ │
│                   │  Financial data NEVER leaves local system          │ │
│                   │  - No transaction amounts to Claude/GPT/Gemini    │ │
│                   │  - No account numbers to any external API         │ │
│                   │  - Only derived categories for NL queries         │ │
│                   └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

###### 2.2 What We Store vs. Never Store

| Data Element | Store? | Justification |
|--------------|--------|---------------|
| Transaction ID | ✅ Yes | Deduplication, audit trail |
| Transaction Date | ✅ Yes | Required for analysis |
| Transaction Amount | ✅ Yes (encrypted) | Spending analysis |
| Merchant Name | ✅ Yes (encrypted) | Pattern detection |
| Category | ✅ Yes | Non-PII, analytics |
| Account ID (Plaid) | ✅ Yes | Account reference |
| Account Name | ✅ Yes (encrypted) | User display |
| Account Mask (last 4) | ✅ Yes | User identification |
| Full Account Number | ❌ NEVER | Not provided by Plaid, not needed |
| Routing Number | ❌ NEVER | Not needed for analytics |
| SSN/Tax ID | ❌ NEVER | Not requested from Plaid |
| Balance (live) | ⚠️ Cached 5min | Real-time from Plaid |
| Investment Holdings | ✅ Yes (encrypted) | Portfolio tracking |
| Investment Cost Basis | ✅ Yes (encrypted) | P&L calculations |

###### 2.3 Data Retention Policy

```python
# src/integrations/plaid/retention_policy.py
"""
Financial Data Retention Policy (FinTech Compliance)

Retention periods designed for:
1. User utility - keep data useful for analysis
2. Regulatory compliance - 7 years for tax-related
3. Privacy - user can request deletion anytime
"""

RETENTION_POLICY = {
    # Core transaction data - 7 years (tax compliance)
    "transactions": {
        "retention_years": 7,
        "deletion_method": "hard_delete",
        "audit_required": True,
    },

    # Balance snapshots - 90 days (trend analysis)
    "balance_history": {
        "retention_days": 90,
        "deletion_method": "hard_delete",
        "audit_required": False,
    },

    # Derived insights - 1 year
    "spending_insights": {
        "retention_years": 1,
        "deletion_method": "soft_delete",
        "audit_required": False,
    },

    # Anomaly alerts - 90 days
    "anomaly_alerts": {
        "retention_days": 90,
        "deletion_method": "hard_delete",
        "audit_required": False,
    },

    # Plaid tokens - until revoked
    "plaid_tokens": {
        "retention": "until_revoked",
        "deletion_method": "secure_wipe",
        "audit_required": True,
    },
}
```

###### 2.4 Right to Deletion (GDPR/CCPA Compliance)

```python
# src/integrations/plaid/data_subject_rights.py
"""
Data Subject Rights - Financial Data Deletion

Implements:
- GDPR Article 17 (Right to Erasure)
- CCPA 1798.105 (Right to Delete)
"""

async def handle_deletion_request(user_id: str) -> DeletionReport:
    """
    Complete financial data deletion for a user.

    Steps:
    1. Revoke Plaid access tokens
    2. Delete all transaction records
    3. Delete all balance history
    4. Delete all derived insights
    5. Create audit trail of deletion
    6. Return deletion report
    """
    report = DeletionReport(user_id=user_id)

    # 1. Revoke Plaid tokens (prevents future data sync)
    tokens = await PlaidTokenStore.get_all_for_user(user_id)
    for token in tokens:
        await plaid_client.item_remove(token.access_token)
        await PlaidTokenStore.delete(token.id)
        report.tokens_revoked += 1

    # 2. Delete transactions
    tx_count = await TransactionStore.delete_all_for_user(user_id)
    report.transactions_deleted = tx_count

    # 3. Delete balance history
    bal_count = await BalanceHistory.delete_all_for_user(user_id)
    report.balance_records_deleted = bal_count

    # 4. Delete insights
    insight_count = await SpendingInsights.delete_all_for_user(user_id)
    report.insights_deleted = insight_count

    # 5. Audit log (required - keep for compliance)
    await audit_logger.log_transform(
        source="plaid",
        operation="data_deletion_request",
        destination="local",
        item_count=report.total_deleted,
        metadata={
            "user_id": user_id,
            "deletion_type": "user_requested",
            "report": report.to_dict(),
        }
    )

    return report
```

---

##### Pass 3: Operational Security & Monitoring

###### 3.1 Error Handling (No Data Leakage)

```python
# src/integrations/plaid/error_handling.py
"""
Financial Error Handling - No Data Leakage

Critical: Error messages must NEVER contain:
- Account numbers
- Transaction amounts
- Balance values
- Personal identifiers
"""

class FinancialErrorHandler:
    """Safe error handling for financial operations."""

    @staticmethod
    def sanitize_error(error: Exception, context: dict) -> SafeError:
        """
        Convert exception to safe, loggable error.

        Removes all PII/financial data from error messages.
        """
        # Extract error type and code
        error_type = type(error).__name__
        error_code = getattr(error, 'code', 'UNKNOWN')

        # Safe context (no values, only structure)
        safe_context = {
            "operation": context.get("operation"),
            "has_account_id": bool(context.get("account_id")),
            "has_transaction_id": bool(context.get("transaction_id")),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # NEVER include these in logs
        forbidden_keys = [
            "amount", "balance", "account_number", "routing",
            "ssn", "tax_id", "access_token", "merchant_name"
        ]

        for key in forbidden_keys:
            if key in str(error):
                # Redact the error message
                return SafeError(
                    code="REDACTED_FINANCIAL_ERROR",
                    message="Financial operation failed (details redacted for security)",
                    context=safe_context,
                )

        return SafeError(
            code=error_code,
            message=str(error)[:200],  # Truncate
            context=safe_context,
        )

    @staticmethod
    def log_error(error: SafeError, severity: str = "ERROR"):
        """Log sanitized error."""
        logger.log(
            severity,
            f"[Finance] {error.code}: {error.message}",
            extra={"context": error.context}
        )
```

###### 3.2 Rate Limiting & Abuse Prevention

```python
# src/integrations/plaid/rate_limiting.py
"""
Plaid API Rate Limiting

Plaid limits:
- 100 requests/minute per item
- 15 requests/minute for /transactions/sync
- Token exchange: 1 per public_token

ACMS additional limits:
- Max 10 accounts per user (abuse prevention)
- Max 1 full sync per hour (cost control)
- Max 100 transaction fetches per day (API cost)
"""

class PlaidRateLimiter:
    """Rate limiter for Plaid API calls."""

    LIMITS = {
        "transactions_sync": RateLimit(calls=15, period_seconds=60),
        "accounts_get": RateLimit(calls=60, period_seconds=60),
        "balance_get": RateLimit(calls=30, period_seconds=60),
        "full_sync": RateLimit(calls=1, period_seconds=3600),
    }

    USER_LIMITS = {
        "max_connected_accounts": 10,
        "max_transactions_per_day": 10000,
        "max_sync_requests_per_hour": 6,
    }

    async def check_rate_limit(self, operation: str, user_id: str) -> bool:
        """Check if operation is allowed."""
        limit = self.LIMITS.get(operation)
        if not limit:
            return True

        key = f"plaid_rate:{operation}:{user_id}"
        current = await redis.get(key) or 0

        if int(current) >= limit.calls:
            logger.warning(
                f"[Plaid] Rate limit exceeded: {operation} for user {user_id}"
            )
            return False

        await redis.incr(key)
        await redis.expire(key, limit.period_seconds)
        return True
```

###### 3.3 Anomaly Detection Architecture

```python
# src/integrations/plaid/anomaly_detector.py
"""
Personalized Financial Anomaly Detection

Design principles:
1. Learn from user's OWN patterns (not generic thresholds)
2. Minimize false positives (alert fatigue is dangerous)
3. Never expose raw amounts in alerts (privacy)
4. Configurable sensitivity per category
"""

@dataclass
class AnomalyConfig:
    """User-configurable anomaly detection settings."""

    # Sensitivity multiplier (1.0 = normal, 2.0 = strict, 0.5 = relaxed)
    sensitivity: float = 1.5

    # Minimum transaction amount to trigger anomaly check ($ value)
    min_amount_threshold: float = 50.0

    # Categories to monitor (user can disable specific categories)
    monitored_categories: List[str] = field(default_factory=lambda: [
        "restaurants", "shopping", "travel", "entertainment",
        "subscriptions", "utilities", "healthcare"
    ])

    # Quiet hours (no alerts during these times)
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 7    # 7 AM


class PersonalizedAnomalyDetector:
    """
    Learns user spending patterns and detects anomalies.

    Uses rolling 90-day window for baseline calculation.
    """

    def __init__(self, db_pool, user_id: str):
        self.db = db_pool
        self.user_id = user_id
        self.config = AnomalyConfig()  # Will load from user prefs

    async def compute_baselines(self) -> Dict[str, CategoryBaseline]:
        """
        Compute spending baselines per category.

        Returns mean, std, and threshold for each category
        based on last 90 days of transactions.
        """
        query = """
            SELECT
                category,
                AVG(amount) as mean_amount,
                STDDEV(amount) as std_amount,
                COUNT(*) as transaction_count,
                MAX(amount) as max_amount
            FROM financial_transactions
            WHERE user_id = $1
              AND transaction_date > NOW() - INTERVAL '90 days'
              AND amount > 0  -- Only debits
            GROUP BY category
            HAVING COUNT(*) >= 5  -- Need minimum data
        """
        rows = await self.db.fetch(query, self.user_id)

        baselines = {}
        for row in rows:
            # Threshold = mean + (sensitivity * std)
            # Minimum threshold is 2x mean to avoid noise
            threshold = max(
                row["mean_amount"] + (self.config.sensitivity * row["std_amount"]),
                row["mean_amount"] * 2
            )

            baselines[row["category"]] = CategoryBaseline(
                mean=row["mean_amount"],
                std=row["std_amount"],
                threshold=threshold,
                sample_size=row["transaction_count"],
                max_seen=row["max_amount"],
            )

        return baselines

    async def check_transaction(
        self,
        transaction: Transaction
    ) -> Optional[AnomalyAlert]:
        """
        Check if transaction is anomalous.

        Returns alert if anomaly detected, None otherwise.
        """
        # Skip small transactions
        if transaction.amount < self.config.min_amount_threshold:
            return None

        # Skip unmonitored categories
        if transaction.category not in self.config.monitored_categories:
            return None

        # Get baseline for category
        baselines = await self.compute_baselines()
        baseline = baselines.get(transaction.category)

        if not baseline:
            # New category - can't detect anomaly yet
            return None

        # Check if above threshold
        if transaction.amount > baseline.threshold:
            # Calculate severity (1-5 scale)
            excess_ratio = transaction.amount / baseline.mean
            severity = min(5, int(excess_ratio))

            # Create alert (NO raw amounts in description)
            return AnomalyAlert(
                transaction_id=transaction.id,
                category=transaction.category,
                severity=severity,
                alert_type="unusual_amount",
                description=self._generate_safe_description(
                    transaction, baseline, severity
                ),
                created_at=datetime.utcnow(),
            )

        return None

    def _generate_safe_description(
        self,
        transaction: Transaction,
        baseline: CategoryBaseline,
        severity: int
    ) -> str:
        """
        Generate privacy-safe alert description.

        NEVER includes actual amounts or merchant names.
        """
        severity_words = {
            1: "slightly higher",
            2: "notably higher",
            3: "significantly higher",
            4: "much higher",
            5: "exceptionally higher",
        }

        return (
            f"A {transaction.category} transaction was "
            f"{severity_words.get(severity, 'higher')} than your typical spending "
            f"in this category over the past 90 days."
        )
```

###### 3.4 Audit Trail Requirements

```python
# All financial operations MUST create audit events:

# 1. Token operations
await audit.log_ingress(
    source="plaid",
    operation="token_exchange",
    item_count=1,
    data_classification=DataClassification.SECRET,
    metadata={"institution_id": "chase", "products": ["transactions"]},
)

# 2. Account sync
await audit.log_ingress(
    source="plaid",
    operation="accounts_sync",
    item_count=len(accounts),
    data_classification=DataClassification.FINANCIAL,
    metadata={"institution_id": "chase", "account_types": ["checking", "savings"]},
)

# 3. Transaction sync
await audit.log_ingress(
    source="plaid",
    operation="transactions_sync",
    item_count=len(transactions),
    data_classification=DataClassification.FINANCIAL,
    metadata={
        "date_range": {"start": start_date, "end": end_date},
        "has_pending": any(t.pending for t in transactions),
    },
)

# 4. Anomaly detection
await audit.log_transform(
    source="plaid",
    operation="anomaly_detection",
    destination="local",
    item_count=len(transactions_checked),
    metadata={
        "anomalies_found": len(alerts),
        "categories_analyzed": list(baselines.keys()),
    },
)

# 5. Data deletion
await audit.log_transform(
    source="plaid",
    operation="data_deletion",
    destination="local",
    item_count=deleted_count,
    metadata={
        "deletion_type": "user_request",
        "tokens_revoked": tokens_revoked,
    },
)
```

---

##### Phase 2 Implementation Plan (Revised)

| Day | Task | TDD Test First | Security Checkpoint |
|-----|------|----------------|---------------------|
| 1 | Set up Plaid account + encryption | `test_plaid_credentials_exist` | Verify PLAID_ENCRYPTION_KEY set |
| 1 | Implement token encryption module | `test_token_encryption_roundtrip` | Fernet key rotation support |
| 2 | Implement Plaid Link flow | `test_link_flow_exchanges_token` | Token never logged in plain text |
| 2 | Create plaid_tokens table (encrypted) | `test_token_stored_encrypted` | Verify encrypted at rest |
| 3 | Implement account sync | `test_accounts_sync_stores_masked` | Full account numbers never stored |
| 3 | Implement transaction sync | `test_transactions_encrypted` | Amounts encrypted at rest |
| 4 | Create Finance MCP server | `test_mcp_tools_register` | No financial data in tool descriptions |
| 4 | Implement finance_overview | `test_overview_returns_totals` | LLM sees only categories, not amounts |
| 5 | Implement finance_accounts | `test_accounts_returns_masked` | Account masks only (last 4) |
| 5 | Implement finance_transactions | `test_transactions_never_to_llm` | Assert no LLM egress |
| 6 | Create Finance sidebar view | `test_ui_renders_accounts` | No sensitive data in DOM/console |
| 7 | Implement PlaidSyncWorker | `test_sync_respects_rate_limits` | Rate limiting verified |
| 8 | Create SpendingPatternModel | `test_patterns_no_amounts` | Patterns use categories only |
| 9 | Implement PersonalizedAnomalyDetector | `test_anomaly_alerts_safe` | Alerts never contain amounts |
| 10 | Create finance_ask NL interface | `test_nl_response_no_amounts` | LLM response sanitized |
| 11 | Implement data deletion | `test_deletion_complete` | All data removed on request |
| 12 | Security audit & documentation | Manual review | Penetration testing if possible |

##### Phase 2 Verification Checklist

**Security & Compliance:**
- [ ] PLAID_ENCRYPTION_KEY is set and not in version control
- [ ] Access tokens encrypted with Fernet (AES-256)
- [ ] Full account numbers NEVER stored (verify schema)
- [ ] Token revocation works (Plaid /item/remove)
- [ ] Data deletion removes ALL user financial data
- [ ] Audit events created for ALL financial operations

**Privacy:**
- [ ] Transaction amounts NEVER sent to LLM APIs
- [ ] Account numbers NEVER in logs or error messages
- [ ] Anomaly alerts contain NO raw amounts
- [ ] Spending insights use categories only
- [ ] User can export all their financial data
- [ ] User can delete all their financial data

**Operational:**
- [ ] Rate limiting prevents API abuse
- [ ] Error handling sanitizes all financial data
- [ ] Sync failures don't expose tokens
- [ ] Retry logic with exponential backoff
- [ ] Connection status clearly shown in UI
- [ ] Disconnection revokes tokens properly

**Testing:**
- [ ] Unit tests for encryption/decryption
- [ ] Unit tests for anomaly detection logic
- [ ] Integration tests for Plaid flow (sandbox)
- [ ] Security test: grep codebase for leaked tokens
- [ ] Security test: verify no amounts in logs
- [ ] E2E test: full connect → sync → delete flow

---

##### Phase 2 Database Schema

```sql
-- Migration: 014_financial_integration.sql
-- FinTech Compliance Design

-- 1. Plaid Tokens (encrypted at rest)
CREATE TABLE IF NOT EXISTS plaid_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',

    -- Encrypted with Fernet (AES-256-CBC + HMAC)
    access_token_encrypted TEXT NOT NULL,

    -- Plaid identifiers
    item_id VARCHAR(100) UNIQUE NOT NULL,
    institution_id VARCHAR(100) NOT NULL,
    institution_name VARCHAR(255),

    -- Connection metadata
    products TEXT[] NOT NULL DEFAULT '{}',
    consent_expiration TIMESTAMPTZ,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    error_code VARCHAR(100),
    error_message TEXT,

    -- Sync tracking
    last_successful_sync TIMESTAMPTZ,
    last_sync_attempt TIMESTAMPTZ,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, institution_id)
);

-- Index for user lookups
CREATE INDEX IF NOT EXISTS idx_plaid_tokens_user ON plaid_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_plaid_tokens_active ON plaid_tokens(is_active) WHERE is_active = TRUE;


-- 2. Financial Accounts
CREATE TABLE IF NOT EXISTS financial_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',

    -- Plaid identifiers
    plaid_account_id VARCHAR(100) UNIQUE NOT NULL,
    plaid_item_id VARCHAR(100) NOT NULL REFERENCES plaid_tokens(item_id) ON DELETE CASCADE,

    -- Account info (encrypted sensitive fields)
    name_encrypted TEXT NOT NULL,       -- e.g., "Chase Checking"
    official_name_encrypted TEXT,       -- e.g., "CHASE TOTAL CHECKING"
    mask VARCHAR(4),                    -- Last 4 digits only
    account_type VARCHAR(50) NOT NULL,  -- checking, savings, credit, investment
    account_subtype VARCHAR(50),        -- e.g., 401k, cd, money market

    -- Institution
    institution_id VARCHAR(100) NOT NULL,
    institution_name VARCHAR(255),

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Current balance (encrypted, cached)
    balance_current_encrypted TEXT,
    balance_available_encrypted TEXT,
    balance_limit_encrypted TEXT,       -- For credit cards
    balance_currency VARCHAR(3) DEFAULT 'USD',
    balance_updated_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_accounts_user ON financial_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_item ON financial_accounts(plaid_item_id);


-- 3. Financial Transactions
CREATE TABLE IF NOT EXISTS financial_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',

    -- Plaid identifiers
    plaid_transaction_id VARCHAR(100) UNIQUE NOT NULL,
    plaid_account_id VARCHAR(100) NOT NULL,

    -- Transaction details (encrypted)
    amount_encrypted TEXT NOT NULL,
    merchant_name_encrypted TEXT,

    -- Non-sensitive (safe for analytics)
    category VARCHAR(100),
    category_detailed VARCHAR(255),
    transaction_date DATE NOT NULL,
    authorized_date DATE,
    is_pending BOOLEAN NOT NULL DEFAULT FALSE,
    payment_channel VARCHAR(50),  -- online, in_store, other

    -- Derived (for learning, safe to use in LLM context)
    amount_bucket VARCHAR(20),    -- '<$10', '$10-50', '$50-100', etc.
    day_of_week INTEGER,
    hour_of_day INTEGER,

    -- Sync tracking
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON financial_transactions(user_id, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON financial_transactions(plaid_account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON financial_transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_pending ON financial_transactions(is_pending) WHERE is_pending = TRUE;


-- 4. Spending Insights (derived, safe for LLM)
CREATE TABLE IF NOT EXISTS spending_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',

    -- Insight type
    insight_type VARCHAR(50) NOT NULL,  -- 'spending_trend', 'category_change', 'recurring_detected'

    -- Non-sensitive description (safe for LLM)
    description TEXT NOT NULL,

    -- Category reference
    category VARCHAR(100),

    -- Trend data (percentages, not amounts)
    trend_direction VARCHAR(10),        -- 'up', 'down', 'stable'
    trend_percentage DECIMAL(5,2),

    -- Period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Status
    is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insights_user ON spending_insights(user_id, created_at DESC);


-- 5. Anomaly Alerts
CREATE TABLE IF NOT EXISTS financial_anomaly_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',

    -- Reference (not the actual transaction for privacy)
    transaction_id UUID REFERENCES financial_transactions(id) ON DELETE CASCADE,

    -- Alert details (NO raw amounts)
    alert_type VARCHAR(50) NOT NULL,    -- 'unusual_amount', 'new_merchant', 'unusual_location'
    severity INTEGER NOT NULL,          -- 1-5 scale
    description TEXT NOT NULL,          -- Privacy-safe description

    -- Status
    is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ,
    is_false_positive BOOLEAN,          -- User feedback for learning

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomalies_user ON financial_anomaly_alerts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_active ON financial_anomaly_alerts(is_dismissed) WHERE is_dismissed = FALSE;


-- 6. User-configurable spending baselines (for anomaly detection)
CREATE TABLE IF NOT EXISTS spending_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',

    category VARCHAR(100) NOT NULL,

    -- Computed baselines (encrypted amounts)
    mean_amount_encrypted TEXT NOT NULL,
    std_amount_encrypted TEXT NOT NULL,
    threshold_encrypted TEXT NOT NULL,

    -- Metadata (safe)
    sample_size INTEGER NOT NULL,
    computation_date DATE NOT NULL,

    -- User overrides
    is_manually_adjusted BOOLEAN NOT NULL DEFAULT FALSE,
    sensitivity_multiplier DECIMAL(3,2) DEFAULT 1.5,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, category)
);

CREATE INDEX IF NOT EXISTS idx_baselines_user ON spending_baselines(user_id);
```

##### Supported Financial Institutions

**Banks (Plaid Verified):**
| Institution | Type | Plaid Support | Priority |
|-------------|------|---------------|----------|
| Wells Fargo | Checking/Savings | ✅ Full | HIGH |
| Discover Bank | Checking/Savings | ✅ Full | HIGH |

**Credit Cards (10-12 cards expected):**
| Network | Example Issuers | Plaid Support | Notes |
|---------|-----------------|---------------|-------|
| Mastercard | Capital One, Citi, USAA | ✅ Full | Most common network |
| Visa | Chase, Wells Fargo, BofA | ✅ Full | Largest network |
| American Express | Amex Blue, Gold, Platinum | ✅ Full | Premium cards |

**Investment Accounts:**
| Institution | Account Types | Plaid Support | Priority |
|-------------|---------------|---------------|----------|
| Fidelity Investments | Brokerage, 401k, IRA | ✅ Full | HIGH |
| Vanguard | 529 Plan, Brokerage | ✅ Full | HIGH |

**Plaid Products Required:**
```
# For Banks & Credit Cards
products = ["transactions", "balance"]

# For Investment Accounts
products = ["investments", "transactions", "balance"]
```

**Institution-Specific Considerations:**
1. **Wells Fargo**: May require MFA re-authentication every 90 days
2. **Fidelity**: Investment holdings include cost basis for tax calculations
3. **Vanguard 529**: Beneficiary info (filter out - not needed for spending analysis)
4. **Amex**: Statement dates vary - use `authorized_date` for accurate timing

**Encryption Per Data Type:**
| Institution Type | Sensitive Fields | Encryption |
|-----------------|------------------|------------|
| All | access_token | Fernet (AES-256) |
| All | account_name, balance | AES-256-GCM |
| All | transaction_amount, merchant | AES-256-GCM |
| Investment | holdings, cost_basis | AES-256-GCM |
| 529 Plan | beneficiary_name | ❌ Not stored |

---

##### Phase 2B: Financial Constitution & Portfolio Governance Engine

**Status: 📋 DESIGNED (Dec 21, 2025)**

###### Overview

The Financial Constitution transforms ACMS from a data aggregator into a **governed decision-making system**. It enables:

1. **Investment Constitution** - Articles → Rules → Signals → Exceptions
2. **Deterministic Portfolio Evaluation** - 25 rules across 6 articles
3. **Unified Intelligence Insights** - Violations, drift, behavioral risks
4. **ACMS Pulse Integration** - Daily/weekly governance summary

This is **not** a robo-advisor. It is a **decision-governance system** that enforces stated investment beliefs.

###### Architecture

```
Financial Data (Plaid / Fidelity)
        ↓
Canonical Finance Tables (Postgres, encrypted)
        ↓
Derived Portfolio Snapshots (percentages only)
        ↓
Constitution Rule Engine (deterministic)
        ↓
Compliance & Drift Results
        ↓
Unified Insights (Postgres + Weaviate)
        ↓
Query Router + Pulse + Chat
```

###### Constitution Schema: 6 Articles, 25 Rules

| Article | Focus | Rules |
|---------|-------|-------|
| A1 | Capital Preservation & Survivability | R1-R5 |
| A2 | Long-Term Compounding | R6-R9 |
| A3 | Quality + Value Discipline | R10-R13 |
| A4 | AI Infrastructure Thesis | R14-R17 |
| A5 | Tax-Aware Wealth Building | R18-R22 |
| A6 | Behavioral & Process Integrity | R23-R25 |

**Key Rules:**
- **R1**: Max single-name concentration ≤15% (FAIL)
- **R5**: Drawdown guardrail ≥-20% 12m (FAIL)
- **R10**: Thesis required for every single-name (FAIL)
- **R15**: AI-infra concentration cap: warn >40%, fail >55%
- **R19**: Wash sale risk alert (FAIL)
- **R23**: FOMO pattern detector (WARN)
- **R24**: Panic-sell detector (WARN)

###### Approved Configuration (Dec 21, 2025)

**Allocation Targets:**
| Bucket | Target | Min | Max |
|--------|--------|-----|-----|
| AI_INFRA | 35% | 25% | 45% |
| INDEX_CORE | 30% | 25% | 40% |
| QUALITY | 22% | 15% | 30% |
| SPECULATIVE | 5% | 0% | 7% |
| CASH | 8% | 5% | 12% |

**AI Infrastructure Seed Tags:**
- **AI_INFRA_CORE**: NVDA, AMD, AVGO, ANET, MRVL, MSFT, GOOGL, TSM, ASML, AMAT, LRCX, KLAC
- **AI_INFRA_ADJACENT**: VRT, ETN, AMZN, META

**Review Cadence by Tag:**
| Tag | Cadence | Rationale |
|-----|---------|-----------|
| AI_INFRA_CORE | 45 days | Fast-moving capex, margins, geopolitics |
| QUALITY_COMPOUNDER | 90 days | Slower thesis decay |
| INDEX_CORE | 365 days | Structural exposure |
| SPECULATIVE | 30 days | High decay risk |

###### Database Schema

Migration: `migrations/015_financial_constitution.sql`

**19 tables supporting all 25 rules:**

| Table | Purpose |
|-------|---------|
| `securities_master` | Central security registry with multi-ID mapping |
| `security_tags` | 3-tier tagging (manual/seed/inferred) |
| `security_seed_data` | Pre-populated ~30 common tickers |
| `financial_accounts` | Plaid-linked brokerage accounts |
| `positions_daily` | Daily position snapshots |
| `financial_transactions` | Normalized trade history |
| `portfolio_snapshots_daily` | Derived metrics (all %) |
| `market_data_daily` | Price history for held securities |
| `position_lots` | Tax lot tracking (inferred or actual) |
| `security_equivalence_map` | Wash sale detection groups |
| `investment_theses` | Thesis per single-name |
| `thesis_reviews` | Timestamped thesis check-ins |
| `tag_review_cadence` | Tag-specific review schedules |
| `allocation_targets` | Bucket targets with bands |
| `portfolio_mode_config` | Operating modes (normal/concentrated/etc) |
| `investment_constitutions` | Rule definitions |
| `investment_rules` | Individual rule specs |
| `investment_exceptions` | Time-boxed overrides |
| `constitution_evaluations` | Immutable evaluation ledger |
| `constitution_rule_results` | Per-rule results with signals |
| `behavioral_events` | FOMO/panic/narrative detection |

###### Key Design Decisions

1. **Internal UUID for security_id** - Stable across brokers, supports deduplication
2. **App-level Fernet encryption** - Dollar amounts encrypted, percentages plain
3. **3-tier security tagging** - Manual (authoritative) > Seed > Inferred
4. **Tag-specific review cadence** - AI_INFRA_CORE=45d, QUALITY=90d, etc.
5. **Graceful degradation** - Cost basis confidence gating for tax rules

###### LLM Boundary (Critical)

**LLMs are used ONLY for:**
- Explanation of rule violations
- Summarization of governance status
- Narrative synthesis for Pulse

**LLMs are NEVER used for:**
- Pass/fail decisions
- Metric computation
- Rule overrides
- Accessing raw financial values

###### Phase 2 Implementation Stages

| Stage | Focus | Status |
|-------|-------|--------|
| **2A** | Data Foundation (Plaid integration, canonical tables) | 📋 Designed |
| **2B** | Constitution Engine (rules, evaluator, 25 rules) | 📋 Designed |
| **2C** | Pulse Integration (governance section, violation alerts) | 📋 Planned |
| **2D** | Fundamentals (R11/R12 quality/valuation - deferred) | ⏸️ Future |

---

### Phase 3: Calendar Integration (Week 6)
**Priority: MEDIUM**

| Day | Task | TDD Checkpoint |
|-----|------|----------------|
| 1 | Set up Google Calendar OAuth | OAuth works |
| 2 | Create Calendar MCP server | MCP tools register |
| 2 | Implement calendar_today/week | Events retrieved |
| 3 | Implement calendar_event_detail | Details correct |
| 4 | Create meeting prep generator | Context assembled |
| 5 | Create Calendar sidebar view | UI renders events |

**Verification:**
- [ ] Calendar syncs correctly
- [ ] Events display in UI
- [ ] Meeting prep includes context
- [ ] All operations create audit events

---

### Phase 4: File Upload & Processing (Week 7)
**Priority: High**

| Day | Task | TDD Checkpoint |
|-----|------|----------------|
| 1 | Design file upload API | Endpoint accepts files |
| 2 | Implement PDF processing | Text extracted |
| 2 | Implement image OCR | Text extracted |
| 3 | Implement chunking pipeline | Chunks created |
| 4 | Implement embedding storage | Vectors in Weaviate |
| 5 | Create Files sidebar view | UI shows files |
| 5 | Implement file search | Search returns results |

**Verification:**
- [ ] PDF uploads and extracts
- [ ] Images OCR correctly
- [ ] Search finds content in files
- [ ] All operations create audit events

---

### Phase 5: Browser Session Control (Weeks 8-9)
**Priority: HIGH**

| Day | Task | TDD Checkpoint |
|-----|------|----------------|
| 1 | Set up Playwright | Browser launches |
| 2 | Implement session detection | Login status detected |
| 3 | Implement ChatGPT automation | Message sent/received |
| 4 | Implement Claude automation | Message sent/received |
| 5 | Implement Gemini automation | Message sent/received |
| 6 | Create Browser MCP server | MCP tools work |
| 7 | Handle file uploads | Files uploaded via browser |
| 8 | Create Sessions sidebar view | UI shows status |
| 9 | Response capture and storage | Responses saved |
| 10 | Error handling and retries | Graceful failures |

**Verification:**
- [ ] Detects logged-in status per platform
- [ ] Sends messages correctly
- [ ] Receives and parses responses
- [ ] File upload works
- [ ] All operations create audit events

---

### Phase 6: ACMS Pulse (Weeks 10-11)
**Priority: HIGH**
**Status: 🎯 NEXT**

---

#### ACMS Pulse - Definitive Specification (December 23, 2025)

##### 1. Core Philosophy

> **Pulse answers "What should I know today?" — not "What data do we have?"**

ACMS Pulse is an **autonomous daily research agent**, not a dashboard. It proactively discovers, researches, and summarizes what matters to the user based on their actual behavior, memories, and private data.

**Design Principles:**
- Pulse must feel **alive, opinionated, and personalized** to the user's world
- **"YOUR world, not THE world"** — leverage local data unavailable to cloud systems
- Every card must answer **"Why should I care?"**
- **Fewer, better cards** (5-7/day max)

##### 2. Daily Execution Cycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PULSE DAILY CYCLE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  EVENING (11 PM) — INTEREST DETECTION                               │   │
│  │                                                                      │   │
│  │  Scan signals to identify what matters:                             │   │
│  │  1. Query history (last 7 days)                                     │   │
│  │  2. Long-term memories                                              │   │
│  │  3. Connected emails (VIP senders, active threads)                  │   │
│  │  4. Portfolio holdings (if enabled)                                 │   │
│  │  5. Explicit pins / saved interests                                 │   │
│  │  6. Scheduled tasks                                                 │   │
│  │                                                                      │   │
│  │  Output: Ranked PulseTopics with confidence + reason                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  OVERNIGHT — ASYNC RESEARCH JOBS (per topic)                        │   │
│  │                                                                      │   │
│  │  For each PulseTopic:                                               │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 1. Context Retrieval                                        │   │   │
│  │  │    • Relevant memories                                      │   │   │
│  │  │    • Past questions + conclusions                           │   │   │
│  │  │    • Related emails / documents                             │   │   │
│  │  │    • Portfolio positions (if applicable)                    │   │   │
│  │  ├─────────────────────────────────────────────────────────────┤   │   │
│  │  │ 2. External Research (policy-gated)                         │   │   │
│  │  │    • Web search (news, releases, filings)                   │   │   │
│  │  │    • Time-bounded and source-diverse                        │   │   │
│  │  │    • Cached with provenance                                 │   │   │
│  │  ├─────────────────────────────────────────────────────────────┤   │   │
│  │  │ 3. Delta Analysis                                           │   │   │
│  │  │    • What changed since last time?                          │   │   │
│  │  │    • Detect contradictions or reversals                     │   │   │
│  │  │    • Highlight surprises                                    │   │   │
│  │  ├─────────────────────────────────────────────────────────────┤   │   │
│  │  │ 4. Synthesis                                                │   │   │
│  │  │    • Generate concise insight                               │   │   │
│  │  │    • Quantify impact where possible                         │   │   │
│  │  │    • Propose next actions                                   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MORNING (8 AM) — CARD PRESENTATION                                 │   │
│  │                                                                      │   │
│  │  Each topic produces one Pulse Card:                                │   │
│  │  • Title                                                            │   │
│  │  • 1-2 sentence executive summary                                   │   │
│  │  • Key facts (bullets, each with evidence)                          │   │
│  │  • Personal relevance ("why this matters to you")                   │   │
│  │  • Actions (optional)                                               │   │
│  │  • Confidence score                                                 │   │
│  │  • Provenance links                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  USER INTERACTION — LEARNING LOOP                                   │   │
│  │                                                                      │   │
│  │  👍 Positive feedback → increase topic weight                       │   │
│  │  👎 Negative feedback → decay or suppress topic                     │   │
│  │  "Save to Memory" → persist insight permanently                     │   │
│  │  "Ask Follow-up" → open contextual chat seeded with card evidence   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

##### 3. Card Types (First-Class Objects)

| Card Type | Trigger | Example |
|-----------|---------|---------|
| **Topic Update** | Topic queried ≥3 times or pinned | "NVIDIA: earnings beat, stock +3.2%" |
| **Email Digest** | Unread/active thread from VIP | "3 emails from Sarah need attention" |
| **Portfolio Alert** | Price move, earnings, rule violation | "Cash buffer low at 4.8%" |
| **Action Item Due** | Deadline within 48 hours | "Budget approval due tomorrow" |
| **Memory Refresh** | Old memory + new conflicting info | "React 19 released (contradicts your March notes)" |
| **Scheduled Task** | User-defined recurring prompt | "Weekly portfolio summary: +2.3%" |

Each card must declare: **Trigger source**, **Freshness window**, **Learning impact**

##### 4. Pulse Card Schema

```json
{
  "card_id": "uuid",
  "type": "topic_update | email_digest | portfolio_alert | action_item | memory_refresh | scheduled_task",
  "title": "NVIDIA Update",
  "summary": "Stock up 3.2% after earnings beat. Your position is +$240.",
  "key_facts": [
    { "fact": "Data center revenue +22% QoQ", "source": "Q3 earnings call" },
    { "fact": "Guidance raised for Q4", "source": "Reuters" }
  ],
  "why_this_matters": "You queried NVIDIA 4x this week and hold 50 shares",
  "actions": ["follow_up", "save", "view_position"],
  "confidence": 0.87,
  "provenance": {
    "memories_used": 3,
    "web_sources": ["reuters.com", "sec.gov"],
    "emails_referenced": 0,
    "delta_from_last": "New: earnings beat (previously expected miss)"
  },
  "generated_at": "2025-12-23T08:00:00Z"
}
```

##### 5. API Contracts

```
GET /api/v2/pulse/topics
Response: {
  "topics": [
    { "topic_id": "uuid", "name": "NVIDIA", "score": 0.92, "reason": "Queried 4x + portfolio exposure" },
    { "topic_id": "uuid", "name": "Sarah's Project", "score": 0.81, "reason": "Active email thread + open action" }
  ]
}

POST /api/v2/pulse/run
Request: { "run_type": "scheduled | manual", "scope": "daily" }
Response: { "job_id": "uuid", "status": "started", "estimated_completion": "2025-12-23T08:00:00Z" }

GET /api/v2/pulse/cards
Response: {
  "generated_at": "2025-12-23T08:00:00Z",
  "cards": [ ... ],
  "card_count": 6,
  "topics_researched": 8
}

POST /api/v2/pulse/feedback
Request: { "card_id": "uuid", "feedback": "positive | negative", "action": "save | follow_up | dismiss" }
```

##### 6. ACMS Differentiators (Non-Negotiable)

| Capability | Why It Matters |
|------------|----------------|
| Cross-reference emails with memories | "Sarah mentioned X in email, you learned Y in March" |
| Tie news to personal portfolio | "NVIDIA up 3% — your position +$240" |
| Highlight contradictions | "React 19 released — contradicts your March notes on v18 being latest" |
| Full provenance | Every fact cites source, every card shows reasoning |
| Local-first | All data stays on device, web search is opt-in augmentation |

##### 7. LLM Execution Prompt

```
SYSTEM: You are ACMS Pulse, an autonomous daily research agent.
Your task is to generate a concise, high-signal insight card.

CONSTRAINTS:
- Use only provided evidence
- Highlight deltas since last run
- Tie insight to user context
- Cite sources explicitly

OUTPUT FORMAT:
Title:
Summary (2 lines max):
Key Facts (bullets):
Why This Matters:
Suggested Actions:
Confidence (0–1):
```

##### 8. Implementation Phases

| Phase | Days | Focus | Deliverables |
|-------|------|-------|--------------|
| **Phase 1** | 5 | Interest-Based Cards (MVP) | Local signals only, no web search, basic cards |
| **Phase 2** | 5 | Async Research | Overnight jobs, web search, delta analysis |
| **Phase 3** | 4 | UI + Feedback | Card UI, expand/follow-up, feedback learning |
| **Phase 4** | 3 | Scheduled Tasks | User-defined prompts, cron execution |

**Total: 17 days**

##### 9. Phase 1 Detail: Interest-Based Cards (MVP)

| Day | Task | Output |
|-----|------|--------|
| 1 | Database schema: `pulse_topics`, `pulse_cards`, `pulse_feedback` | Tables created |
| 2 | Topic extraction from query_history (last 7 days) | `/api/v2/pulse/topics` works |
| 3 | Card generation: action_item_due, portfolio_alert, vip_email | Basic cards from existing data |
| 4 | Card UI component + Pulse sidebar view | Cards render |
| 5 | Feedback buttons + manual refresh | Feedback captured |

**Phase 1 Output:** 3-5 cards/day from local intelligence, no web search

##### 10. Phase 2 Detail: Async Research

| Day | Task | Output |
|-----|------|--------|
| 6 | Topic extraction from emails (VIP senders, subjects) | Email topics detected |
| 7 | Topic extraction from portfolio (tickers → company topics) | Portfolio topics detected |
| 8 | Topic scoring algorithm (frequency × recency × engagement) | Ranked topic list |
| 9 | Web search integration for top 3 topics | External research works |
| 10 | Delta analysis (compare to last run, detect changes) | "New since yesterday" |

**Phase 2 Output:** +2-3 research-based cards with web augmentation

##### 11. Phase 3 Detail: UI + Feedback

| Day | Task | Output |
|-----|------|--------|
| 11 | Card expand/collapse with evidence section | Provenance visible |
| 12 | "Ask Follow-up" → opens chat with card context | Contextual chat |
| 13 | "Save to Memory" → persists insight | Memory integration |
| 14 | Feedback learning → adjusts topic scores | Personalization starts |

**Phase 3 Output:** Full interactive card experience

##### 12. Phase 4 Detail: Scheduled Tasks

| Day | Task | Output |
|-----|------|--------|
| 15 | Task definition UI (prompt, schedule, output format) | Users can create tasks |
| 16 | Task execution engine (cron-like scheduler) | Tasks run on schedule |
| 17 | Task output as Pulse cards | Tasks appear in Pulse |

**Phase 4 Output:** "Weekly Portfolio Review" runs every Monday

##### 13. Success Criteria

| Metric | Target |
|--------|--------|
| Daily check rate | User opens Pulse without prompting |
| Card action rate | >50% of cards trigger follow-up or save |
| Topic evolution | Topics change based on feedback, not manual tuning |
| Anticipatory feel | Cards surface things user didn't ask for but needed |

##### 14. Governance & Safety

Every Pulse job must log:
- Sources used
- Data boundaries crossed
- Cost and latency
- Model decisions
- Cache hits

Policy rules:
- No external calls without explicit permission
- PII redaction before web search
- Immutable artifacts for reproducibility

---

#### Original Phase 6 Plan (For Reference)

| Day | Task | TDD Checkpoint |
|-----|------|----------------|
| 1 | Design Pulse data model | Schema created |
| 2 | Create PulseScheduler | Scheduler runs |
| 3 | Implement email digest generator | Digest generated |
| 4 | Implement calendar prep generator | Prep notes created |
| 5 | Implement finance insights generator | Insights generated |
| 6 | Implement topic research generator | Research performed |
| 7 | Create PulseRanker | Items ranked |
| 8 | Create Pulse UI view | UI renders Pulse |
| 9 | Implement feedback collection | Feedback saved |
| 10 | Implement curate feature | Preferences saved |
| 11 | Integrate learning into generation | Personalization works |
| 12 | A/B testing framework | Experiments run |

**Verification:**
- [ ] Pulse generates at scheduled time
- [ ] All sections populated correctly
- [ ] Feedback updates learning
- [ ] Curate changes next Pulse
- [ ] Personalization improves over time
- [ ] All operations create audit events

---

### Phase 7: Learning Dashboard & Polish (Week 12)
**Priority: HIGH**

| Day | Task | TDD Checkpoint |
|-----|------|----------------|
| 1 | Create Learning Profile view | UI renders profile |
| 2 | Add learning indicators to email list | Badges show |
| 3 | Add learning indicators to finance | Badges show |
| 4 | Create model accuracy dashboard | Metrics displayed |
| 5 | Implement profile export/import | Export works |

---

## 7. TDD & Testing Strategy

### Testing Pyramid

```
                    ┌───────────────┐
                    │    E2E Tests   │  ◄── 10% of tests
                    │   (Playwright) │      Full user flows
                    └───────┬───────┘
                            │
               ┌────────────┴────────────┐
               │   Integration Tests      │  ◄── 30% of tests
               │   (API + DB + Weaviate)  │      Component interaction
               └────────────┬─────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          │          Unit Tests                │  ◄── 60% of tests
          │   (Functions, Classes, Logic)      │      Isolated logic
          └────────────────────────────────────┘
```

### Test Categories

#### Unit Tests (pytest)
```python
# tests/unit/test_gmail_agent.py

class TestSenderImportanceModel:
    def test_new_sender_starts_at_neutral(self):
        model = SenderImportanceModel()
        score = model.get_score("new@example.com")
        assert score == 50.0

    def test_positive_signal_increases_score(self):
        model = SenderImportanceModel()
        model.update("test@example.com", importance_delta=5.0)
        score = model.get_score("test@example.com")
        assert score > 50.0

    def test_score_bounded_0_to_100(self):
        model = SenderImportanceModel()
        for _ in range(100):
            model.update("test@example.com", importance_delta=10.0)
        score = model.get_score("test@example.com")
        assert score <= 100.0

class TestPersonalizedAnomalyDetector:
    def test_learns_user_baseline(self):
        detector = PersonalizedAnomalyDetector()
        transactions = [
            Transaction(amount=50, category="restaurants"),
            Transaction(amount=45, category="restaurants"),
            Transaction(amount=55, category="restaurants"),
        ]
        detector.train_on_history(transactions)
        assert detector.baselines["restaurants"]["mean"] == 50.0

    def test_flags_anomaly_above_threshold(self):
        detector = PersonalizedAnomalyDetector()
        detector.baselines["restaurants"] = {
            "mean": 50, "std": 10, "threshold_multiplier": 2.0
        }
        txn = Transaction(amount=150, category="restaurants")
        score = detector.score(txn)
        assert score > 0.5  # High anomaly score
```

#### Integration Tests
```python
# tests/integration/test_gmail_integration.py

class TestGmailIntegration:
    @pytest.fixture
    def gmail_agent(self, test_oauth_token):
        return GmailMCPServer(oauth_token=test_oauth_token)

    async def test_list_emails_creates_audit_event(self, gmail_agent, db):
        await gmail_agent.gmail_list_emails(limit=5)

        audit_events = await db.fetch(
            "SELECT * FROM audit_events WHERE source = 'gmail'"
        )
        assert len(audit_events) >= 1
        assert audit_events[0].event_type == "ingress"

    async def test_mark_read_persists_to_gmail(self, gmail_agent, test_email_id):
        await gmail_agent.gmail_mark_read([test_email_id])

        email = await gmail_agent.gmail_get_email(test_email_id)
        assert email.is_read == True

    async def test_delete_requires_confirmation(self, gmail_agent, test_email_id):
        result = await gmail_agent.gmail_delete([test_email_id])

        assert isinstance(result, DeletePreview)
        assert result.confirmation_token is not None
        assert "confirm" in result.warning.lower()
```

#### E2E Tests (Playwright)
```python
# tests/e2e/test_pulse_flow.py

class TestPulseUserFlow:
    async def test_morning_pulse_flow(self, desktop_app):
        # Open Pulse view
        await desktop_app.click('[data-view="pulse"]')

        # Verify Pulse loaded
        await expect(desktop_app.locator('.pulse-header')).to_be_visible()
        await expect(desktop_app.locator('.pulse-section')).to_have_count(4)

        # Give feedback on email section
        await desktop_app.click('.pulse-section[data-type="email"] .thumbs-up')

        # Verify feedback recorded
        await expect(
            desktop_app.locator('.feedback-toast')
        ).to_contain_text('Feedback recorded')

    async def test_email_mark_read_flow(self, desktop_app):
        # Navigate to emails
        await desktop_app.click('[data-view="email"]')

        # Select an email
        await desktop_app.click('.email-item:first-child')

        # Mark as read
        await desktop_app.click('.action-mark-read')

        # Verify state change
        await expect(
            desktop_app.locator('.email-item:first-child')
        ).not_to_have_class('unread')
```

### Test Data Strategy

```python
# tests/conftest.py

@pytest.fixture
def test_emails():
    """Generate realistic test email data"""
    return [
        Email(
            sender="boss@company.com",
            subject="Q1 Planning",
            importance_should_be="high"
        ),
        Email(
            sender="newsletter@techcrunch.com",
            subject="This Week in Tech",
            importance_should_be="low"
        ),
    ]

@pytest.fixture
def test_transactions():
    """Generate realistic test transaction data"""
    return [
        Transaction(merchant="Whole Foods", amount=87.50, category="groceries"),
        Transaction(merchant="Amazon", amount=250.00, category="shopping"),
        Transaction(merchant="Unusual Store", amount=500.00, category="unknown"),
    ]
```

### Coverage Requirements

| Component | Minimum Coverage | Notes |
|-----------|------------------|-------|
| Audit system | 95% | Critical for trust |
| Learning models | 90% | Core differentiator |
| MCP servers | 85% | User-facing functionality |
| API endpoints | 85% | Core functionality |
| UI components | 70% | E2E tests cover more |

---

## 8. Security & Privacy

### Threat Model

| Threat | Mitigation |
|--------|------------|
| OAuth token theft | Encrypted storage, short-lived tokens |
| API key exposure | Environment variables, never in code |
| Data exfiltration | Audit trail, classification enforcement |
| Unauthorized access | Local-only by default |
| Malicious extensions | Validate Chrome extension signatures |

### Privacy Guarantees

```python
# CRITICAL: Enforce privacy classification

class PrivacyEnforcer:
    """Ensures confidential data never leaves local system"""

    EXTERNAL_DESTINATIONS = [
        "claude_api", "openai_api", "gemini_api",
        "plaid_api", "google_api"
    ]

    def validate_egress(self, data, destination):
        if data.classification in ["confidential", "local_only"]:
            if destination in self.EXTERNAL_DESTINATIONS:
                raise PrivacyViolationError(
                    f"Cannot send {data.classification} data to {destination}"
                )

        # Always create audit event
        create_audit_event(
            event_type="egress_validation",
            data_classification=data.classification,
            destination=destination,
            allowed=True
        )
```

### Encryption

| Data Type | Encryption | Notes |
|-----------|------------|-------|
| OAuth tokens | AES-256 at rest | Key derived from machine ID |
| Email content | None (local only) | Never sent externally |
| Financial data | None (local only) | Never sent externally |
| Learning models | None | Metadata only, no PII |
| Audit logs | None | Should be inspectable |

---

## 9. Success Metrics

### User Engagement

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pulse open rate | >80% | Daily opens / days active |
| Pulse action rate | >40% | Actions from Pulse / Pulse views |
| Email response via ACMS | >20% | Emails read in ACMS / total |
| Finance queries | >5/week | Natural language finance questions |

### Learning Quality

| Metric | Target | Measurement |
|--------|--------|-------------|
| Sender importance accuracy | >80% | User corrections / predictions |
| Anomaly detection precision | >85% | Useful alerts / total alerts |
| Pulse item relevance | >75% | Thumbs up / total feedback |
| Personalization confidence | >70% | Model confidence after 30 days |

### System Health

| Metric | Target | Measurement |
|--------|--------|-------------|
| Sync success rate | >99% | Successful syncs / attempts |
| API latency p95 | <500ms | 95th percentile response time |
| Audit coverage | 100% | Operations with audit / total |
| Privacy violations | 0 | Confidential data sent externally |

---

## 10. Risk Analysis

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Gmail API changes | Low | High | Monitor deprecations, abstract API |
| Plaid cost scaling | Medium | Medium | Usage monitoring, caching |
| Browser automation fragility | High | Medium | Fallback to API, robust selectors |
| Learning model drift | Medium | Medium | Continuous accuracy monitoring |

### User Adoption Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Privacy concerns | Medium | High | Transparent audit, local-first messaging |
| Learning feels creepy | Medium | Medium | Visibility, control, explanations |
| Too complex | Medium | High | Progressive disclosure, good defaults |
| Pulse not useful | Medium | Medium | Fast iteration, feedback loops |

### Compliance Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| GDPR violations | Low | High | Local-first, data export, deletion |
| Financial data regulations | Low | High | Plaid handles compliance |
| Email access misuse | Low | Medium | Audit trail, user consent |

---

## Appendix A: API Reference

See [API_REFERENCE.md](./API_REFERENCE.md) (to be created)

## Appendix B: Database Migrations

See [MIGRATIONS.md](./MIGRATIONS.md) (to be created)

## Appendix C: UI Mockups

See [UI_MOCKUPS.md](./UI_MOCKUPS.md) (to be created)

---

**Document Status:** Living document, updated as implementation progresses.

**Current Status (December 21, 2025):**
- Phase 0 (Audit Foundation): ✅ COMPLETE
- Phase 1 (Gmail Integration):
  - Phase 1A (Intelligence Dashboard): ✅ COMPLETE
    - OAuth2 flow with read-only scopes
    - Email listing with priority scoring (SenderImportanceModel v1)
    - AI summaries via Gemini 3 Flash
    - Daily Brief & Inbox Insights panels
    - Timeline selector (7/30/90/120 days)
    - Accurate unread count from Gmail Labels API
    - LLM egress audit logging (tokens, cost)
    - Learning signals (open_in_gmail tracked)
  - Phase 1B (Actions): ⏸️ PARTIAL
    - Create Task/Calendar Event: DEFERRED to Phase 3
    - Learning signal API: ✅ POST /api/gmail/actions
    - Learning stats API: ✅ GET /api/gmail/actions/stats
  - Phase 1C (CRUD): 📋 PLANNED

**Next Steps:**
1. ~~Phase 0 (Audit Foundation)~~ ✅ COMPLETE
2. ~~Phase 1A (Intelligence Dashboard)~~ ✅ COMPLETE
3. ~~Phase 1B (Learning Signals)~~ ✅ COMPLETE
4. **Phase 2 (Financial Integration)**: Expand implementation details with 3-pass FinTech compliance review
5. Phase 1C (CRUD) can be done in parallel or after Phase 2
