# ACMS Unified Intelligence Architecture

**Date**: December 21, 2025
**Status**: DESIGN SPECIFICATION
**Author**: AI Architecture Design (3-Pass Analysis)

---

## Executive Summary

This document defines the architecture for ACMS's **Unified Intelligence Layer** - the system that enables cross-source intelligence by extracting, storing, and querying insights from multiple data sources (Email, Financial, Calendar, AI Conversations) through a single natural language interface.

**Key Principle**: Raw data stays in source-specific tables (encrypted where needed). Only **derived insights** (patterns, summaries, facts) flow into the unified intelligence layer for cross-source queries.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Source Analysis](#3-data-source-analysis)
4. [Insight Extraction Pipeline](#4-insight-extraction-pipeline)
5. [Storage Architecture](#5-storage-architecture)
6. [Query Router Design](#6-query-router-design)
7. [Privacy & Security](#7-privacy--security)
8. [Implementation Plan](#8-implementation-plan)
9. [TDD Specifications](#9-tdd-specifications)
10. [Future: Pulse Integration](#10-future-pulse-integration)

---

## 1. Problem Statement

### Current State

ACMS currently has:
- **AI Conversations**: 97K+ memories, 3.5K+ Q&As with topic extraction and knowledge graphs
- **Email Integration**: Gmail connected, sender scoring, AI summaries - but NOT searchable via chat
- **Financial**: Planned (Phase 2) - will have transaction data but isolated from other sources
- **Calendar**: Planned (Phase 3) - will have events but no cross-source context

**The Gap**: Each data source is siloed. User cannot ask:
- "What emails relate to my AWS spending?" (crosses Email + Financial)
- "Who should I follow up with this week?" (crosses Email + Calendar)
- "What did I discuss with Sarah about budgets?" (crosses AI Chat + Email)

### Desired State

A unified intelligence layer where:
1. Each source extracts **insights** (not raw data) into a common format
2. Insights are vectorized for semantic search
3. A query router understands which sources to search
4. Responses cite their sources clearly
5. Privacy is maintained (financial amounts never to LLM)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      UNIFIED INTELLIGENCE ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  DATA SOURCES                    INSIGHT EXTRACTORS                              │
│  ────────────                    ──────────────────                              │
│                                                                                  │
│  ┌─────────────┐                ┌─────────────────────────────────────┐         │
│  │ AI Chats    │───existing────►│ KnowledgeExtractor                  │         │
│  │ (97K mems)  │                │ • Entity extraction                 │         │
│  └─────────────┘                │ • Topic clustering                  │         │
│                                 │ • Fact synthesis                    │         │
│  ┌─────────────┐                └──────────────┬──────────────────────┘         │
│  │ Email       │                               │                                │
│  │ (Gmail)     │───NEW─────────►┌──────────────┴──────────────────────┐         │
│  └─────────────┘                │ EmailInsightExtractor               │         │
│                                 │ • Action items                      │         │
│  ┌─────────────┐                │ • Key dates/deadlines               │         │
│  │ Financial   │                │ • Sender importance signals         │         │
│  │ (Plaid)     │───NEW─────────►│ • Topic categorization              │         │
│  └─────────────┘                └──────────────┬──────────────────────┘         │
│                                                │                                │
│  ┌─────────────┐                ┌──────────────┴──────────────────────┐         │
│  │ Calendar    │───NEW─────────►│ FinanceInsightExtractor             │         │
│  │ (Google)    │                │ • Spending patterns (NO amounts)    │         │
│  └─────────────┘                │ • Category trends                   │         │
│                                 │ • Anomaly descriptions              │         │
│                                 │ • Recurring expenses                │         │
│                                 └──────────────┬──────────────────────┘         │
│                                                │                                │
│                                 ┌──────────────┴──────────────────────┐         │
│                                 │ CalendarInsightExtractor            │         │
│                                 │ • Meeting prep context              │         │
│                                 │ • Schedule patterns                 │         │
│                                 │ • Participant relationships         │         │
│                                 └──────────────┬──────────────────────┘         │
│                                                │                                │
│                                                ▼                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                     UNIFIED INSIGHTS STORE                                │  │
│  │  ┌────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ PostgreSQL: unified_insights                                       │  │  │
│  │  │ • id, source_type, insight_type, content, entities, metadata       │  │  │
│  │  │ • source_id (reference to original record)                         │  │  │
│  │  │ • created_at, expires_at (for time-sensitive insights)             │  │  │
│  │  └────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                          │  │
│  │  ┌────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ Weaviate: ACMS_Insights_v1                                         │  │  │
│  │  │ • Vectorized insights for semantic search                          │  │  │
│  │  │ • Properties: content, source_type, insight_type, entities, ...    │  │  │
│  │  │ • Filterable by source_type, date range, entities                  │  │  │
│  │  └────────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                │                                │
│                                                ▼                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                        QUERY ROUTER                                       │  │
│  │                                                                          │  │
│  │  User Query: "What did I discuss with Sarah about AWS?"                  │  │
│  │                                                                          │  │
│  │  Step 1: Intent + Entity Detection                                       │  │
│  │          → Entities: [Sarah (person), AWS (service)]                     │  │
│  │          → Intent: CROSS_SOURCE_LOOKUP                                   │  │
│  │          → Suggested sources: [email, ai_chat, calendar]                 │  │
│  │                                                                          │  │
│  │  Step 2: Source-Aware Search                                             │  │
│  │          → Search ACMS_Insights_v1 with filters                          │  │
│  │          → Search ACMS_Knowledge_v2 (existing knowledge)                 │  │
│  │          → Search ACMS_Raw_v1 (past conversations)                       │  │
│  │                                                                          │  │
│  │  Step 3: Context Assembly                                                │  │
│  │          → Combine results from all sources                              │  │
│  │          → Tag each result with source                                   │  │
│  │          → Apply privacy rules (no financial amounts)                    │  │
│  │                                                                          │  │
│  │  Step 4: Response Generation                                             │  │
│  │          → Generate response citing sources                              │  │
│  │          → "Based on 3 emails and 2 past conversations..."              │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                │                                │
│                                                ▼                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                        UNIFIED CHAT UI                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Context: [All Sources ▼] | 📧 Email | 💰 Finance | 📅 Cal | 💬 AI   │ │  │
│  │  └─────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                          │  │
│  │  Response with source tags:                                              │  │
│  │  📧 From email with Sarah on Dec 15: "AWS budget discussion..."         │  │
│  │  💬 From chat on Dec 10: "You asked about AWS cost optimization..."     │  │
│  │                                                                          │  │
│  │  Sources: 3 emails, 2 chats, 0 calendar events                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Source Analysis

### 3.1 What Each Source Contributes

| Source | Raw Data (NEVER to LLM for finance) | Derived Insights (OK for LLM) |
|--------|-------------------------------------|------------------------------|
| **AI Chat** | Full Q&A, code, explanations | Topics, entities, facts, intents |
| **Email** | Full email body, attachments | Action items, key dates, sender patterns, topics |
| **Financial** | Transaction amounts, account numbers | Spending categories, patterns, anomalies (no $) |
| **Calendar** | Event details, attendees | Meeting prep, schedule patterns, relationships |

### 3.2 Insight Types by Source

```python
# Enum of insight types for classification
class InsightType(Enum):
    # From AI Chat
    KNOWLEDGE_FACT = "knowledge_fact"           # Extracted factual statement
    TOPIC_INTEREST = "topic_interest"           # User interest pattern
    LEARNING_JOURNEY = "learning_journey"       # What user is learning

    # From Email
    ACTION_ITEM = "action_item"                 # Something to do
    DEADLINE = "deadline"                       # Date/time commitment
    SENDER_PATTERN = "sender_pattern"           # Communication pattern
    EMAIL_TOPIC = "email_topic"                 # What emails are about

    # From Financial
    SPENDING_PATTERN = "spending_pattern"       # Category trends
    ANOMALY_ALERT = "anomaly_alert"            # Unusual activity
    RECURRING_EXPENSE = "recurring_expense"     # Regular payments
    BUDGET_STATUS = "budget_status"            # Budget tracking

    # From Calendar
    MEETING_CONTEXT = "meeting_context"         # Prep for meetings
    SCHEDULE_PATTERN = "schedule_pattern"       # Time usage patterns
    RELATIONSHIP_SIGNAL = "relationship_signal" # Who you meet with
    TIME_COMMITMENT = "time_commitment"         # Scheduled obligations

    # Cross-Source
    CROSS_SOURCE_CORRELATION = "correlation"    # Pattern across sources
```

### 3.3 Entity Types for Cross-Source Linking

Entities are the glue that connects insights across sources:

```python
class EntityType(Enum):
    PERSON = "person"           # Sarah, John (from email/calendar)
    ORGANIZATION = "org"        # AWS, Google (from all sources)
    SERVICE = "service"         # AWS, Plaid (from all)
    TOPIC = "topic"             # kubernetes, budgeting (from all)
    LOCATION = "location"       # Office, Home (from calendar)
    PROJECT = "project"         # "Q1 Migration" (inferred)
```

**Cross-Source Linking Example:**
- Email from "sarah@company.com" about "AWS costs"
- Calendar meeting with "Sarah" titled "AWS Review"
- AI Chat about "AWS cost optimization"
- Financial transactions to "Amazon Web Services"

All linked by entities: `[Sarah, AWS]`

---

## 4. Insight Extraction Pipeline

### 4.1 Common Interface

All insight extractors implement this interface:

```python
# src/intelligence/insight_extractor.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

@dataclass
class ExtractedInsight:
    """Common insight format across all sources."""

    # Core content
    content: str                    # Human-readable insight text
    insight_type: InsightType       # Categorization

    # Source tracking
    source_type: str                # 'email', 'financial', 'calendar', 'ai_chat'
    source_id: str                  # Reference to original record
    source_metadata: Dict[str, Any] # Source-specific context

    # Entities for cross-source linking
    entities: List[Dict[str, str]] # [{"name": "AWS", "type": "service"}]

    # Temporal
    created_at: datetime
    expires_at: Optional[datetime]  # For time-sensitive insights
    relevance_date: Optional[datetime]  # When this insight is about

    # Quality
    confidence: float               # 0.0 - 1.0
    extraction_method: str          # 'llm', 'rule', 'pattern'


class InsightExtractor(ABC):
    """Base class for all insight extractors."""

    @abstractmethod
    async def extract(self, source_data: Any) -> List[ExtractedInsight]:
        """Extract insights from source data."""
        pass

    @abstractmethod
    def get_source_type(self) -> str:
        """Return source type identifier."""
        pass
```

### 4.2 Email Insight Extractor

```python
# src/intelligence/email_insight_extractor.py

class EmailInsightExtractor(InsightExtractor):
    """
    Extracts insights from emails.

    Insight Types:
    - ACTION_ITEM: "Reply to John about project proposal"
    - DEADLINE: "Q4 report due by Dec 31"
    - EMAIL_TOPIC: "Discussion about AWS infrastructure"
    - SENDER_PATTERN: "John sends 5+ emails/week about project updates"
    """

    def __init__(self, db_pool, model: str = "gemini-3-flash-preview"):
        self.db = db_pool
        self.model_name = model
        # Use Gemini for email extraction (fast, cost-effective)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(model)

    async def extract(self, email: Dict[str, Any]) -> List[ExtractedInsight]:
        """Extract insights from a single email."""
        insights = []

        # Rule-based extraction (fast, no API cost)
        insights.extend(self._extract_action_items_rules(email))
        insights.extend(self._extract_deadlines_rules(email))

        # LLM extraction for complex understanding
        if self._needs_llm_extraction(email):
            llm_insights = await self._extract_with_llm(email)
            insights.extend(llm_insights)

        # Entity extraction
        for insight in insights:
            insight.entities = self._extract_entities(email, insight)

        return insights

    def _extract_action_items_rules(self, email: Dict) -> List[ExtractedInsight]:
        """Rule-based action item detection."""
        patterns = [
            r"(?:please|could you|can you)\s+(.+?)(?:\.|$)",
            r"(?:action required|todo|follow up)[:.]?\s*(.+?)(?:\.|$)",
            r"(?:by|before|deadline)\s+(\w+\s+\d+)",
        ]
        # Implementation...
        return []

    async def _extract_with_llm(self, email: Dict) -> List[ExtractedInsight]:
        """LLM-based extraction for complex insights."""
        prompt = f"""Analyze this email and extract insights.

From: {email.get('sender_email')}
Subject: {email.get('subject')}
Content: {email.get('body_text', '')[:1500]}

Extract in JSON format:
{{
    "action_items": ["list of things the user should do"],
    "deadlines": ["list of dates/deadlines mentioned"],
    "main_topic": "what this email is primarily about",
    "key_entities": [
        {{"name": "entity name", "type": "person|org|service|project"}}
    ],
    "importance": "high|medium|low",
    "requires_response": true/false
}}
"""
        response = await self.model.generate_content_async(prompt)
        # Parse and convert to ExtractedInsight objects...
        return []

    def get_source_type(self) -> str:
        return "email"
```

### 4.3 Financial Insight Extractor

```python
# src/intelligence/finance_insight_extractor.py

class FinanceInsightExtractor(InsightExtractor):
    """
    Extracts insights from financial transactions.

    CRITICAL PRIVACY RULES:
    - NEVER include actual dollar amounts in insight content
    - NEVER include account numbers
    - Only use category names, percentages, and relative terms

    Insight Types:
    - SPENDING_PATTERN: "Dining spending increased this month" (no $)
    - ANOMALY_ALERT: "Unusual activity in travel category"
    - RECURRING_EXPENSE: "Monthly AWS subscription detected"
    """

    async def extract_patterns(
        self,
        transactions: List[Dict],
        period_days: int = 30
    ) -> List[ExtractedInsight]:
        """Extract spending patterns from transactions."""
        insights = []

        # Category distribution (percentages, not amounts)
        category_pcts = self._compute_category_percentages(transactions)
        for category, pct in category_pcts.items():
            if pct > 20:  # Only significant categories
                insights.append(ExtractedInsight(
                    content=f"Significant spending in {category} ({pct:.0f}% of total)",
                    insight_type=InsightType.SPENDING_PATTERN,
                    source_type="financial",
                    source_id=f"pattern_{category}_{period_days}d",
                    source_metadata={"category": category, "period_days": period_days},
                    entities=[{"name": category, "type": "category"}],
                    confidence=0.9,
                    extraction_method="rule",
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=7),
                ))

        # Trend detection (up/down, not amounts)
        trends = self._detect_trends(transactions, period_days)
        for trend in trends:
            insights.append(ExtractedInsight(
                content=f"{trend['category']} spending {trend['direction']} "
                        f"compared to previous period",
                insight_type=InsightType.SPENDING_PATTERN,
                source_type="financial",
                source_id=f"trend_{trend['category']}",
                source_metadata=trend,
                entities=[{"name": trend['category'], "type": "category"}],
                confidence=trend['confidence'],
                extraction_method="rule",
                created_at=datetime.utcnow(),
            ))

        return insights

    def _compute_category_percentages(self, transactions: List[Dict]) -> Dict[str, float]:
        """Compute spending percentages by category (no raw amounts)."""
        # Implementation - returns {"dining": 25.5, "shopping": 30.2, ...}
        pass

    def get_source_type(self) -> str:
        return "financial"
```

### 4.4 Calendar Insight Extractor

```python
# src/intelligence/calendar_insight_extractor.py

class CalendarInsightExtractor(InsightExtractor):
    """
    Extracts insights from calendar events.

    Insight Types:
    - MEETING_CONTEXT: "Meeting with Sarah about Q4 planning"
    - SCHEDULE_PATTERN: "3 meetings scheduled this week with AWS team"
    - RELATIONSHIP_SIGNAL: "Frequent meetings with Sarah (5 this month)"
    """

    async def extract(self, events: List[Dict]) -> List[ExtractedInsight]:
        """Extract insights from calendar events."""
        insights = []

        # Meeting prep context
        for event in events:
            if self._is_upcoming(event):
                prep_insight = await self._generate_meeting_prep(event)
                if prep_insight:
                    insights.append(prep_insight)

        # Relationship patterns
        attendee_counts = self._count_attendees(events)
        for attendee, count in attendee_counts.items():
            if count >= 3:  # Frequent collaborator
                insights.append(ExtractedInsight(
                    content=f"Frequent meetings with {attendee} ({count} this month)",
                    insight_type=InsightType.RELATIONSHIP_SIGNAL,
                    source_type="calendar",
                    source_id=f"relationship_{attendee}",
                    entities=[{"name": attendee, "type": "person"}],
                    confidence=0.95,
                    extraction_method="rule",
                    created_at=datetime.utcnow(),
                ))

        return insights

    async def _generate_meeting_prep(self, event: Dict) -> Optional[ExtractedInsight]:
        """Generate meeting prep by searching related context."""
        # Search emails from attendees
        # Search past chat about meeting topic
        # Compile prep notes
        pass

    def get_source_type(self) -> str:
        return "calendar"
```

---

## 5. Storage Architecture

### 5.1 PostgreSQL: unified_insights Table

```sql
-- Migration: 015_unified_insights.sql

CREATE TABLE IF NOT EXISTS unified_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core content
    content TEXT NOT NULL,                    -- Human-readable insight
    insight_type VARCHAR(50) NOT NULL,        -- From InsightType enum

    -- Source tracking
    source_type VARCHAR(20) NOT NULL,         -- 'email', 'financial', 'calendar', 'ai_chat'
    source_id VARCHAR(255) NOT NULL,          -- Reference to original record
    source_metadata JSONB DEFAULT '{}',       -- Source-specific context

    -- Entities for cross-source linking
    entities JSONB DEFAULT '[]',              -- [{"name": "AWS", "type": "service"}]

    -- Temporal
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,                   -- NULL = never expires
    relevance_date TIMESTAMPTZ,               -- When insight is about

    -- Quality & state
    confidence FLOAT NOT NULL DEFAULT 0.8,
    extraction_method VARCHAR(20) NOT NULL,   -- 'llm', 'rule', 'pattern'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Weaviate sync
    weaviate_id UUID,                         -- Reference to vector
    vectorized_at TIMESTAMPTZ,

    -- User context
    user_id VARCHAR(100) NOT NULL DEFAULT 'default'
);

-- Indexes for efficient querying
CREATE INDEX idx_insights_source_type ON unified_insights(source_type);
CREATE INDEX idx_insights_insight_type ON unified_insights(insight_type);
CREATE INDEX idx_insights_user ON unified_insights(user_id);
CREATE INDEX idx_insights_created ON unified_insights(created_at DESC);
CREATE INDEX idx_insights_relevance ON unified_insights(relevance_date DESC);
CREATE INDEX idx_insights_active ON unified_insights(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_insights_entities ON unified_insights USING GIN(entities);

-- Expiration cleanup (run daily)
CREATE OR REPLACE FUNCTION cleanup_expired_insights()
RETURNS void AS $$
BEGIN
    UPDATE unified_insights
    SET is_active = FALSE
    WHERE expires_at < NOW() AND is_active = TRUE;
END;
$$ LANGUAGE plpgsql;
```

### 5.2 Weaviate: ACMS_Insights_v1 Collection

```python
# src/storage/weaviate_schemas.py

ACMS_INSIGHTS_V1_SCHEMA = {
    "class": "ACMS_Insights_v1",
    "description": "Unified insights from all data sources for cross-source intelligence",
    "vectorizer": "none",  # We provide embeddings via OpenAI
    "properties": [
        # Core content (embedded)
        {
            "name": "content",
            "dataType": ["text"],
            "description": "Human-readable insight text"
        },

        # Classification
        {
            "name": "source_type",
            "dataType": ["text"],
            "description": "Source: email, financial, calendar, ai_chat"
        },
        {
            "name": "insight_type",
            "dataType": ["text"],
            "description": "Type of insight"
        },

        # Entities (for filtering)
        {
            "name": "entities",
            "dataType": ["text[]"],
            "description": "Entity names mentioned"
        },
        {
            "name": "entity_types",
            "dataType": ["text[]"],
            "description": "Types of entities"
        },

        # Source reference
        {
            "name": "source_id",
            "dataType": ["text"],
            "description": "Reference to original record"
        },
        {
            "name": "postgres_id",
            "dataType": ["text"],
            "description": "Reference to unified_insights table"
        },

        # Temporal
        {
            "name": "created_at",
            "dataType": ["date"],
            "description": "When insight was extracted"
        },
        {
            "name": "relevance_date",
            "dataType": ["date"],
            "description": "When insight is about"
        },

        # Metadata
        {
            "name": "user_id",
            "dataType": ["text"],
            "description": "User identifier"
        },
        {
            "name": "confidence",
            "dataType": ["number"],
            "description": "Extraction confidence"
        },
    ]
}
```

### 5.3 Collection Strategy

```
Weaviate Collections (After Unified Intelligence):
├── ACMS_Raw_v1           # Raw Q&A pairs from AI chat (existing)
├── ACMS_Knowledge_v2     # Extracted facts from AI chat (existing)
├── ACMS_Insights_v1      # NEW: Cross-source insights
└── QueryCache_v1         # DEPRECATED (to delete)

Search Priority Order:
1. ACMS_Insights_v1       # Cross-source insights first
2. ACMS_Knowledge_v2      # Then extracted knowledge
3. ACMS_Raw_v1            # Then raw Q&A as fallback
```

---

## 6. Query Router Design

### 6.1 Router Architecture

```python
# src/gateway/query_router.py

class QueryRouter:
    """
    Routes queries to appropriate data sources based on intent and entities.

    Responsibilities:
    1. Detect query intent and entities
    2. Determine which sources to search
    3. Execute searches in parallel
    4. Combine and rank results
    5. Apply privacy filters
    """

    def __init__(self, db_pool, weaviate_client):
        self.db = db_pool
        self.weaviate = weaviate_client
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()

    async def route(
        self,
        query: str,
        context_filter: Optional[str] = None  # 'all', 'email', 'financial', 'calendar', 'ai_chat'
    ) -> RouterResult:
        """
        Route query to appropriate sources and return combined results.

        Args:
            query: User's natural language query
            context_filter: Optional filter to limit sources

        Returns:
            RouterResult with sources_searched, results, and source_tags
        """
        # Step 1: Intent + Entity Detection
        intent = await self.intent_classifier.classify(query)
        entities = await self.entity_extractor.extract(query)

        # Step 2: Determine sources to search
        sources = self._determine_sources(intent, entities, context_filter)

        # Step 3: Execute parallel searches
        search_tasks = []
        for source in sources:
            task = self._search_source(source, query, entities)
            search_tasks.append(task)

        results = await asyncio.gather(*search_tasks)

        # Step 4: Combine and rank
        combined = self._combine_results(results, sources)
        ranked = self._rank_results(combined, query, intent)

        # Step 5: Apply privacy filters
        filtered = self._apply_privacy_filters(ranked)

        return RouterResult(
            query=query,
            intent=intent,
            entities=entities,
            sources_searched=sources,
            results=filtered,
            result_count_by_source={s: len([r for r in filtered if r.source == s]) for s in sources}
        )

    def _determine_sources(
        self,
        intent: Intent,
        entities: List[Entity],
        context_filter: Optional[str]
    ) -> List[str]:
        """Determine which sources to search based on intent and entities."""

        if context_filter and context_filter != 'all':
            return [context_filter]

        sources = []

        # Financial intent keywords
        if intent.category in ['FINANCIAL_QUERY', 'SPENDING', 'BUDGET']:
            sources.append('financial')

        # People/communication queries → email + calendar
        if any(e.type == 'person' for e in entities):
            sources.extend(['email', 'calendar'])

        # Service/technology queries → all sources
        if any(e.type in ['service', 'technology'] for e in entities):
            sources.extend(['email', 'financial', 'ai_chat'])

        # Calendar-specific
        if intent.category in ['SCHEDULE', 'MEETING', 'TIME']:
            sources.append('calendar')

        # Default: search all if unclear
        if not sources:
            sources = ['ai_chat', 'email']  # Most common

        return list(set(sources))

    async def _search_source(
        self,
        source: str,
        query: str,
        entities: List[Entity]
    ) -> List[SearchResult]:
        """Search a specific source."""

        if source == 'ai_chat':
            # Search existing collections
            return await self._search_weaviate(
                collections=['ACMS_Knowledge_v2', 'ACMS_Raw_v1'],
                query=query,
                filters={}
            )
        else:
            # Search unified insights collection
            return await self._search_weaviate(
                collections=['ACMS_Insights_v1'],
                query=query,
                filters={"source_type": source}
            )

    def _apply_privacy_filters(self, results: List[SearchResult]) -> List[SearchResult]:
        """Apply privacy rules to results."""
        filtered = []
        for result in results:
            # Financial results: ensure no amounts leaked
            if result.source == 'financial':
                result = self._sanitize_financial_result(result)
            filtered.append(result)
        return filtered
```

### 6.2 Intent Categories for Routing

```python
class QueryIntent(Enum):
    # Financial
    SPENDING_QUERY = "spending_query"       # "What did I spend on..."
    BUDGET_CHECK = "budget_check"           # "Am I over budget..."
    FINANCIAL_OVERVIEW = "financial_overview"  # "What's my financial situation"

    # Email
    EMAIL_SEARCH = "email_search"           # "Find emails about..."
    SENDER_LOOKUP = "sender_lookup"         # "What did X send me..."
    ACTION_ITEMS = "action_items"           # "What do I need to do..."

    # Calendar
    SCHEDULE_QUERY = "schedule_query"       # "What's on my calendar..."
    MEETING_PREP = "meeting_prep"           # "Prepare me for meeting with..."
    AVAILABILITY = "availability"           # "When am I free..."

    # Cross-Source
    PERSON_CONTEXT = "person_context"       # "Tell me about my interactions with X"
    TOPIC_DEEP_DIVE = "topic_deep_dive"     # "Everything about AWS"
    TIMELINE_QUERY = "timeline_query"       # "What happened last week"

    # General
    GENERAL_KNOWLEDGE = "general_knowledge" # Falls back to AI chat
    FACTUAL = "factual"                     # Facts from knowledge base
```

---

## 7. Privacy & Security

### 7.1 Data Classification

| Classification | Sources | LLM Allowed | Storage | Examples |
|---------------|---------|-------------|---------|----------|
| **PUBLIC** | All | Yes | Plain | Topic names, categories |
| **INTERNAL** | Email, Calendar | Yes | Plain | Meeting subjects, email topics |
| **CONFIDENTIAL** | Financial, Email | Partial | Encrypted | Spending patterns (no $), sender names |
| **RESTRICTED** | Financial | Never | Encrypted | Transaction amounts, account numbers |

### 7.2 Privacy Rules in Query Router

```python
PRIVACY_RULES = {
    "financial": {
        # Never include in LLM context
        "blocked_fields": ["amount", "balance", "account_number", "routing"],

        # Allowed in LLM context
        "allowed_fields": ["category", "merchant_category", "trend_direction", "pattern_description"],

        # Transform before including
        "transforms": {
            "amount": lambda x: None,  # Drop entirely
            "merchant": lambda x: x.split()[0] if x else None,  # First word only
        }
    },

    "email": {
        # Allowed in LLM context
        "allowed_fields": ["subject", "sender_name", "date", "topic", "action_items"],

        # Never include
        "blocked_patterns": [r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"],  # Phone numbers
    },

    "calendar": {
        # All fields allowed
        "allowed_fields": "*",
    }
}
```

### 7.3 Audit Trail

Every query through the router is logged:

```python
await audit.log_transform(
    source="query_router",
    operation="cross_source_query",
    destination="llm_context",
    item_count=len(results),
    metadata={
        "query_hash": hash(query),
        "sources_searched": sources,
        "results_per_source": result_counts,
        "privacy_filters_applied": True,
        "financial_amounts_blocked": financial_count,
    }
)
```

---

## 8. Implementation Plan

### Phase 1.5A: Foundation (Days 1-2)

| Task | TDD Test | Files |
|------|----------|-------|
| Create unified_insights table | `test_unified_insights_schema` | migrations/015_unified_insights.sql |
| Create ACMS_Insights_v1 collection | `test_insights_collection_exists` | src/storage/weaviate_schemas.py |
| Create InsightExtractor base class | `test_extractor_interface` | src/intelligence/insight_extractor.py |
| Create InsightStore CRUD | `test_insight_crud` | src/storage/insight_store.py |

### Phase 1.5B: Email Integration (Days 3-4)

| Task | TDD Test | Files |
|------|----------|-------|
| Create EmailInsightExtractor | `test_email_action_items_extracted` | src/intelligence/email_insight_extractor.py |
| Extract insights from existing emails | `test_batch_email_extraction` | src/jobs/insight_extraction_jobs.py |
| Vectorize email insights | `test_email_insights_vectorized` | src/storage/insight_vectorizer.py |
| Add email insights to chat context | `test_email_insights_in_context` | src/gateway/context_assembler.py |

### Phase 1.5C: Query Router (Days 5-6)

| Task | TDD Test | Files |
|------|----------|-------|
| Create QueryRouter class | `test_router_detects_sources` | src/gateway/query_router.py |
| Integrate with orchestrator | `test_orchestrator_uses_router` | src/gateway/orchestrator.py |
| Add source tags to responses | `test_response_has_source_tags` | src/gateway/response_formatter.py |
| Update chat UI for source display | Manual E2E | desktop-app/src/renderer/* |

### Phase 1.5D: Testing & Polish (Day 7)

| Task | TDD Test | Files |
|------|----------|-------|
| End-to-end cross-source query | `test_cross_source_query_e2e` | tests/e2e/test_unified_intelligence.py |
| Privacy filter verification | `test_financial_amounts_blocked` | tests/security/test_privacy_filters.py |
| Performance testing | `test_router_latency_acceptable` | tests/performance/test_query_router.py |

---

## 9. TDD Specifications

### 9.1 Unit Tests

```python
# tests/unit/intelligence/test_email_insight_extractor.py

class TestEmailInsightExtractor:

    def test_extracts_action_items_from_email(self):
        """Action items should be extracted from email content."""
        email = {
            "subject": "Project Update",
            "body_text": "Please review the attached document and send feedback by Friday.",
            "sender_email": "john@example.com"
        }

        extractor = EmailInsightExtractor()
        insights = extractor.extract(email)

        action_insights = [i for i in insights if i.insight_type == InsightType.ACTION_ITEM]
        assert len(action_insights) >= 1
        assert "review" in action_insights[0].content.lower()

    def test_extracts_deadlines_from_email(self):
        """Deadlines mentioned in email should be extracted."""
        email = {
            "subject": "Q4 Report Due",
            "body_text": "The quarterly report is due by December 31, 2025.",
            "sender_email": "manager@company.com"
        }

        extractor = EmailInsightExtractor()
        insights = extractor.extract(email)

        deadline_insights = [i for i in insights if i.insight_type == InsightType.DEADLINE]
        assert len(deadline_insights) >= 1
        assert "December 31" in deadline_insights[0].content

    def test_entities_extracted_from_email(self):
        """Entities (people, orgs) should be linked to insights."""
        email = {
            "subject": "AWS Cost Review",
            "body_text": "Let's discuss the AWS infrastructure costs with Sarah next week.",
            "sender_email": "team@company.com"
        }

        extractor = EmailInsightExtractor()
        insights = extractor.extract(email)

        # At least one insight should have entities
        insights_with_entities = [i for i in insights if len(i.entities) > 0]
        assert len(insights_with_entities) > 0

        # Should find AWS and Sarah as entities
        all_entities = [e['name'] for i in insights for e in i.entities]
        assert "AWS" in all_entities or "aws" in all_entities.lower()


# tests/unit/intelligence/test_finance_insight_extractor.py

class TestFinanceInsightExtractor:

    def test_spending_pattern_has_no_amounts(self):
        """Financial insights must NEVER contain actual dollar amounts."""
        transactions = [
            {"amount": 150.00, "category": "dining", "date": "2025-12-15"},
            {"amount": 75.50, "category": "dining", "date": "2025-12-16"},
        ]

        extractor = FinanceInsightExtractor()
        insights = extractor.extract_patterns(transactions)

        for insight in insights:
            # Check no dollar amounts in content
            assert not re.search(r'\$\d+', insight.content)
            assert not re.search(r'\d+\.\d{2}', insight.content)
            # Check no amounts in metadata
            assert 'amount' not in str(insight.source_metadata)

    def test_category_trends_use_percentages(self):
        """Trends should use relative terms, not absolute amounts."""
        # Implementation...


# tests/unit/gateway/test_query_router.py

class TestQueryRouter:

    def test_financial_query_routes_to_financial(self):
        """Spending queries should route to financial source."""
        router = QueryRouter(mock_db, mock_weaviate)
        result = router._determine_sources(
            intent=Intent(category="SPENDING_QUERY"),
            entities=[],
            context_filter=None
        )

        assert "financial" in result

    def test_person_query_routes_to_email_calendar(self):
        """Queries about people should search email and calendar."""
        router = QueryRouter(mock_db, mock_weaviate)
        result = router._determine_sources(
            intent=Intent(category="PERSON_CONTEXT"),
            entities=[Entity(name="Sarah", type="person")],
            context_filter=None
        )

        assert "email" in result
        assert "calendar" in result

    def test_context_filter_overrides_auto_detection(self):
        """Explicit context filter should limit sources."""
        router = QueryRouter(mock_db, mock_weaviate)
        result = router._determine_sources(
            intent=Intent(category="GENERAL"),
            entities=[],
            context_filter="email"
        )

        assert result == ["email"]
```

### 9.2 Integration Tests

```python
# tests/integration/test_unified_intelligence.py

class TestUnifiedIntelligence:

    @pytest.mark.asyncio
    async def test_email_insights_stored_in_postgres_and_weaviate(self):
        """Email insights should be stored in both PostgreSQL and Weaviate."""
        # Create test email
        email = create_test_email()

        # Extract and store
        extractor = EmailInsightExtractor(db_pool)
        insights = await extractor.extract(email)

        store = InsightStore(db_pool, weaviate_client)
        await store.store_insights(insights)

        # Verify PostgreSQL
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM unified_insights WHERE source_type = 'email'"
            )
            assert len(rows) >= 1

        # Verify Weaviate
        results = weaviate_client.query.get(
            "ACMS_Insights_v1",
            ["content", "source_type"]
        ).with_where({
            "path": ["source_type"],
            "operator": "Equal",
            "valueText": "email"
        }).do()

        assert len(results['data']['Get']['ACMS_Insights_v1']) >= 1

    @pytest.mark.asyncio
    async def test_cross_source_query_returns_tagged_results(self):
        """Cross-source query should return results with source tags."""
        # Setup: Insert test insights from multiple sources
        await insert_test_insights([
            ("email", "Email about AWS costs from Sarah"),
            ("ai_chat", "Discussed AWS optimization strategies"),
            ("calendar", "Meeting with Sarah about AWS review"),
        ])

        # Execute cross-source query
        router = QueryRouter(db_pool, weaviate_client)
        result = await router.route("What about AWS with Sarah?")

        # Verify results from multiple sources
        assert len(result.sources_searched) >= 2
        assert any(r.source == "email" for r in result.results)
        assert any(r.source == "ai_chat" for r in result.results)
```

---

## 10. Future: Pulse Integration

The Unified Intelligence Layer is the foundation for ACMS Pulse - proactive daily/weekly intelligence digests.

### Pulse Data Flow

```
Daily Pulse Generation (6 AM):
│
├── Query: "What needs my attention today?"
│   └── Route to: [email, calendar, financial]
│
├── Email Insights
│   ├── 3 action items pending
│   ├── 2 emails need response
│   └── 1 deadline today
│
├── Calendar Insights
│   ├── 4 meetings scheduled
│   ├── Meeting prep for "AWS Review" with Sarah
│   └── 2 hours of focus time blocked
│
├── Financial Insights
│   ├── Credit card payment due tomorrow
│   ├── Unusual activity in dining (up 30%)
│   └── AWS subscription renews next week
│
└── Compiled Pulse
    ├── Priority 1: Respond to urgent emails
    ├── Priority 2: Prepare for AWS meeting
    ├── Priority 3: Review dining spending
    └── FYI: Credit card due tomorrow
```

### Pulse Collection

```python
# Future: ACMS_Pulse_v1 collection for generated pulse items
ACMS_PULSE_V1_SCHEMA = {
    "class": "ACMS_Pulse_v1",
    "properties": [
        {"name": "pulse_date", "dataType": ["date"]},
        {"name": "item_type", "dataType": ["text"]},  # action, reminder, insight
        {"name": "priority", "dataType": ["int"]},
        {"name": "content", "dataType": ["text"]},
        {"name": "source_insights", "dataType": ["text[]"]},  # IDs of source insights
        {"name": "was_acted_on", "dataType": ["boolean"]},  # Learning signal
    ]
}
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 21, 2025 | Initial design specification |

---

**Next Steps:**
1. Review and approve this architecture
2. Update ACMS_3.0_UNIFIED_INTELLIGENCE_PLAN.md with Phase 1.5
3. Update TECHNOLOGY_STACK_REFRESHER.md with new components
4. Begin TDD implementation
