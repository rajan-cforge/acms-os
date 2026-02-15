# Active Second Brain - Implementation Plan

**Version**: 1.0
**Created**: January 14, 2026
**Status**: Ready for Implementation

---

## Executive Summary

Transform ACMS from passive storage to an **Active Second Brain** that:
- Learns from user feedback (not just stores data)
- Surfaces knowledge proactively (not just when searched)
- Allows corrections (not just read-only display)
- Shows confidence levels (not just raw data)

**Key Principle**: No architectural changes. Close the feedback loop between existing components.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Architecture Overview](#architecture-overview)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [UX Scenarios & Acceptance Criteria](#ux-scenarios--acceptance-criteria)
6. [Multi-Hat Validation Framework](#multi-hat-validation-framework)
7. [Implementation Phases](#implementation-phases)
8. [Success Metrics](#success-metrics)

---

## Problem Statement

### Why Previous Caching Failed

| Issue | Root Cause | Impact |
|-------|------------|--------|
| Wrong agent responses | Cache didn't track which agent generated response | User selects Ollama, gets cached Claude answer |
| Stale web data | No flag for web search queries | "What happened today?" returns yesterday's news |
| Low-quality matches | 0.90 similarity too aggressive | "What is Python?" matched different context answers |
| No quality signal | Feedback existed but wasn't connected to cache | Bad responses kept being served |

### Current State vs. Active Second Brain

| Aspect | Current (Passive) | Target (Active) |
|--------|-------------------|-----------------|
| Knowledge storage | Store everything | Store + verify + score |
| User interaction | Search when needed | Nudge when relevant |
| Feedback | Collect but don't act | Feedback drives quality |
| Corrections | Not possible | Fix button on facts |
| Confidence | Hidden in backend | Visible in UI |

---

## Architecture Overview

### Data Flow: Closing the Feedback Loop

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ACTIVE SECOND BRAIN ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  USER QUERY                                                              │
│      │                                                                   │
│      ▼                                                                   │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │ Quality Cache   │────▶│ Gateway Pipeline │────▶│ AI Agent        │   │
│  │ (verified only) │     │ (7 steps)        │     │ (Claude/GPT/etc)│   │
│  └────────┬────────┘     └─────────────────┘     └────────┬────────┘   │
│           │                                               │             │
│           │  Cache HIT                                    │ Fresh       │
│           │  (high confidence)                            │ Response    │
│           │                                               │             │
│           ▼                                               ▼             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         RESPONSE TO USER                         │   │
│  │                    + Confidence Badge (87%)                      │   │
│  │                    + Source Attribution                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      FEEDBACK COLLECTION                         │   │
│  │   👍 Helpful    👎 Not Helpful    ✏️ Correct This    ⭐ Rate     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│           ┌────────────────────────┼────────────────────────┐          │
│           ▼                        ▼                        ▼          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │ PROMOTE to      │     │ DEMOTE from     │     │ CORRECT fact    │   │
│  │ Quality Cache   │     │ Quality Cache   │     │ in Knowledge DB │   │
│  │ (👍 + verified) │     │ (👎 feedback)   │     │ (user edit)     │   │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘   │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  PROACTIVE INTELLIGENCE                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Weekly Nudge: "You explored [topic] 5 times. View summary?"    │   │
│  │  Knowledge Review: "3 facts need verification"                   │   │
│  │  Learning Digest: "This week you learned about..."              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| QualityCache | `src/cache/quality_cache.py` (NEW) | Stores only verified responses |
| FeedbackPromoter | `src/feedback/promoter.py` (NEW) | Promotes 👍 responses to cache |
| KnowledgeCorrector | `src/intelligence/corrector.py` (NEW) | Handles user corrections |
| NudgeEngine | `src/intelligence/nudge_engine.py` (NEW) | Generates proactive insights |
| ConfidenceBadge | `desktop-app/.../confidence.js` (NEW) | UI component for confidence |

---

## Backend Implementation

### Phase B1: Quality-Gated Cache

**File**: `src/cache/quality_cache.py`

```python
"""
Quality-Gated Cache - Only stores verified, high-quality responses.

Key differences from old SemanticCache:
1. Tracks agent_used - prevents wrong-agent serving
2. Tracks contains_web_search - prevents stale data
3. Tiered TTL based on query type
4. Only caches after positive feedback
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

class QueryType(Enum):
    DEFINITION = "definition"      # "What is X?" - 7 day TTL
    FACTUAL = "factual"           # "How does X work?" - 24hr TTL
    TEMPORAL = "temporal"         # "What happened today?" - NO CACHE
    CREATIVE = "creative"         # "Write a poem" - NO CACHE
    CODE = "code"                 # "Write function" - 24hr TTL

@dataclass
class CacheEntry:
    """Enhanced cache entry with quality signals."""
    query_text: str
    response: str
    agent_used: str              # NEW: Which agent generated this
    contains_web_search: bool    # NEW: Did this use web search?
    query_type: QueryType        # NEW: For TTL calculation
    confidence: float            # Extraction confidence
    user_verified: bool          # NEW: Did user verify this?
    positive_feedback_count: int # NEW: How many 👍
    negative_feedback_count: int # NEW: How many 👎
    created_at: datetime
    last_served: datetime
    serve_count: int

    @property
    def quality_score(self) -> float:
        """Calculate quality score for cache ranking."""
        if self.negative_feedback_count > 2:
            return 0.0  # Too many downvotes, don't serve

        base = self.confidence
        if self.user_verified:
            base += 0.1
        if self.positive_feedback_count > 0:
            base += min(self.positive_feedback_count * 0.02, 0.1)

        return min(base, 1.0)

    @property
    def ttl_hours(self) -> int:
        """Get TTL based on query type."""
        if self.contains_web_search:
            return 1  # Web data goes stale fast

        ttl_map = {
            QueryType.DEFINITION: 168,  # 7 days
            QueryType.FACTUAL: 24,
            QueryType.CODE: 24,
            QueryType.TEMPORAL: 0,      # Never cache
            QueryType.CREATIVE: 0,      # Never cache
        }
        return ttl_map.get(self.query_type, 24)

    def is_valid_for_request(self, requested_agent: Optional[str]) -> bool:
        """Check if this cache entry is valid for the current request."""
        # Don't serve if too many downvotes
        if self.quality_score < 0.5:
            return False

        # Don't serve wrong agent's response
        if requested_agent and self.agent_used != requested_agent:
            return False

        # Don't serve expired entries
        age_hours = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        if age_hours > self.ttl_hours:
            return False

        return True


class QualityCache:
    """Quality-gated semantic cache."""

    SIMILARITY_THRESHOLD = 0.95  # Stricter than before (was 0.90)

    def __init__(self):
        self.weaviate = WeaviateClient()
        self.embeddings = OpenAIEmbeddings()
        self.collection_name = "ACMS_QualityCache_v1"

    async def get(
        self,
        query: str,
        user_id: str,
        requested_agent: Optional[str] = None
    ) -> Optional[CacheEntry]:
        """
        Get cached response if:
        1. Similarity >= 0.95 (strict matching)
        2. Same user (privacy)
        3. Agent matches request (or request is "auto")
        4. Quality score >= 0.5 (not too many downvotes)
        5. Not expired (TTL based on query type)
        """
        # Implementation...
        pass

    async def promote_to_cache(
        self,
        query_history_id: str,
        user_id: str
    ) -> bool:
        """
        Promote a query to cache after positive feedback.
        Called when user gives 👍 AND clicks "Save as verified".
        """
        # Get the query from history
        # Create CacheEntry with user_verified=True
        # Store in Weaviate
        pass

    async def demote_from_cache(
        self,
        cache_entry_id: str,
        reason: str
    ) -> bool:
        """
        Demote/remove entry after negative feedback.
        Called when user gives 👎.
        """
        # Increment negative_feedback_count
        # If count > 2, mark as invalid
        pass
```

**Schema for Weaviate** (`ACMS_QualityCache_v1`):

| Property | Type | Purpose |
|----------|------|---------|
| query_text | TEXT | Original query |
| response | TEXT | Cached response |
| agent_used | TEXT | claude/chatgpt/gemini/ollama |
| contains_web_search | BOOL | Did response use web search? |
| query_type | TEXT | definition/factual/temporal/creative/code |
| confidence | NUMBER | AI extraction confidence |
| user_verified | BOOL | User clicked "verify" |
| positive_feedback | INT | Count of 👍 |
| negative_feedback | INT | Count of 👎 |
| user_id | TEXT | Privacy isolation |
| created_at | DATE | When cached |
| last_served | DATE | Last time served |
| serve_count | INT | How many times served |

---

### Phase B2: Feedback-to-Cache Promoter

**File**: `src/feedback/promoter.py`

```python
"""
Feedback Promoter - Connects user feedback to cache quality.

When user gives 👍:
1. Record positive feedback (existing)
2. Offer to "Save as verified knowledge" (NEW)
3. If accepted, promote to QualityCache (NEW)

When user gives 👎:
1. Record negative feedback (existing)
2. Demote from QualityCache if cached (NEW)
3. Flag for review (NEW)
"""

class FeedbackPromoter:
    def __init__(self):
        self.quality_cache = QualityCache()
        self.knowledge_db = KnowledgeDB()

    async def handle_positive_feedback(
        self,
        query_history_id: str,
        user_id: str,
        save_as_knowledge: bool = False
    ) -> Dict[str, Any]:
        """
        Handle 👍 feedback with optional knowledge save.

        Returns:
            {
                "feedback_recorded": True,
                "promoted_to_cache": True/False,
                "knowledge_id": "uuid" or None
            }
        """
        result = {
            "feedback_recorded": True,
            "promoted_to_cache": False,
            "knowledge_id": None
        }

        # Always record the feedback
        await self._record_feedback(query_history_id, "positive")

        # If user wants to save as verified knowledge
        if save_as_knowledge:
            # Promote to quality cache
            promoted = await self.quality_cache.promote_to_cache(
                query_history_id, user_id
            )
            result["promoted_to_cache"] = promoted

            # Also save as verified knowledge
            knowledge_id = await self.knowledge_db.save_verified(
                query_history_id, user_id
            )
            result["knowledge_id"] = knowledge_id

        return result

    async def handle_negative_feedback(
        self,
        query_history_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle 👎 feedback with cache demotion.
        """
        # Record feedback
        await self._record_feedback(query_history_id, "negative", reason)

        # Check if this was served from cache
        cache_entry = await self._find_cache_entry(query_history_id)
        if cache_entry:
            await self.quality_cache.demote_from_cache(
                cache_entry.id,
                reason or "user_downvote"
            )

        return {
            "feedback_recorded": True,
            "demoted_from_cache": cache_entry is not None
        }
```

**New API Endpoints**:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/feedback/{id}/promote` | Promote to cache after 👍 |
| POST | `/api/feedback/{id}/demote` | Demote from cache after 👎 |
| GET | `/api/cache/quality/stats` | Quality cache statistics |

---

### Phase B3: Knowledge Corrector

**File**: `src/intelligence/corrector.py`

```python
"""
Knowledge Corrector - Allows users to fix extracted facts.

When AI extracts a fact like:
  "ACMS uses PostgreSQL for vector storage"

User can correct to:
  "ACMS uses Weaviate for vector storage, PostgreSQL for relational data"

Corrections:
1. Update the fact in ACMS_Knowledge_v2
2. Flag original as "corrected"
3. Track correction history for learning
"""

@dataclass
class Correction:
    knowledge_id: str
    original_content: str
    corrected_content: str
    corrected_by: str
    corrected_at: datetime
    correction_type: str  # "factual_error", "outdated", "incomplete", "wrong_context"

class KnowledgeCorrector:
    async def apply_correction(
        self,
        knowledge_id: str,
        corrected_content: str,
        user_id: str,
        correction_type: str
    ) -> Dict[str, Any]:
        """
        Apply user correction to a knowledge item.

        Steps:
        1. Load original knowledge item
        2. Create correction record (audit trail)
        3. Update knowledge item with corrected content
        4. Re-generate embedding for corrected content
        5. Mark as user_verified=True
        """
        pass

    async def get_items_needing_review(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get knowledge items that need user review.

        Criteria:
        - confidence < 0.8
        - user_verified = False
        - extracted_at > 7 days ago (give time for natural verification)
        """
        pass
```

**New API Endpoints**:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| PATCH | `/api/knowledge/{id}/correct` | Apply user correction |
| GET | `/api/knowledge/needs-review` | Get items needing verification |
| POST | `/api/knowledge/{id}/verify` | Mark as user-verified |

---

### Phase B4: Nudge Engine

**File**: `src/intelligence/nudge_engine.py`

```python
"""
Nudge Engine - Generates proactive insights for users.

Types of nudges:
1. Weekly Learning Digest - "This week you learned about..."
2. Topic Deep Dive - "You've asked about [topic] 5 times. View summary?"
3. Knowledge Review - "3 facts need your verification"
4. Expertise Growth - "Your knowledge in [area] grew 20%"
"""

class NudgeType(Enum):
    WEEKLY_DIGEST = "weekly_digest"
    TOPIC_DEEP_DIVE = "topic_deep_dive"
    KNOWLEDGE_REVIEW = "knowledge_review"
    EXPERTISE_GROWTH = "expertise_growth"

@dataclass
class Nudge:
    nudge_type: NudgeType
    title: str
    description: str
    action_label: str
    action_data: Dict[str, Any]
    priority: int  # 1-5, higher = more important
    dismissible: bool
    expires_at: Optional[datetime]

class NudgeEngine:
    async def generate_nudges(
        self,
        user_id: str,
        max_nudges: int = 3
    ) -> List[Nudge]:
        """
        Generate relevant nudges for user's current session.

        Rules:
        - Max 1 nudge per type per day
        - Respect user's dismiss preferences
        - Prioritize actionable over informational
        """
        nudges = []

        # Check for knowledge review nudge
        items_needing_review = await self._count_items_needing_review(user_id)
        if items_needing_review > 0:
            nudges.append(Nudge(
                nudge_type=NudgeType.KNOWLEDGE_REVIEW,
                title="Knowledge Review",
                description=f"{items_needing_review} facts need your verification",
                action_label="Review Now",
                action_data={"view": "knowledge", "filter": "needs_review"},
                priority=3,
                dismissible=True,
                expires_at=None
            ))

        # Check for topic deep dive
        hot_topic = await self._get_hot_topic(user_id, days=7)
        if hot_topic and hot_topic["query_count"] >= 5:
            nudges.append(Nudge(
                nudge_type=NudgeType.TOPIC_DEEP_DIVE,
                title=f"Deep Dive: {hot_topic['topic']}",
                description=f"You've explored this {hot_topic['query_count']} times this week",
                action_label="View Summary",
                action_data={"view": "insights", "topic": hot_topic["topic"]},
                priority=2,
                dismissible=True,
                expires_at=None
            ))

        # Weekly digest (only on Mondays or first session of week)
        if self._should_show_weekly_digest(user_id):
            digest = await self._generate_weekly_digest(user_id)
            nudges.append(Nudge(
                nudge_type=NudgeType.WEEKLY_DIGEST,
                title="Your Week in Review",
                description=digest["summary"],
                action_label="See Details",
                action_data={"view": "insights", "period": "week"},
                priority=1,
                dismissible=True,
                expires_at=datetime.utcnow() + timedelta(days=1)
            ))

        return sorted(nudges, key=lambda n: n.priority, reverse=True)[:max_nudges]

    async def dismiss_nudge(
        self,
        user_id: str,
        nudge_type: NudgeType,
        duration: str = "today"  # "today", "week", "forever"
    ):
        """Record user's dismiss preference."""
        pass
```

**New API Endpoints**:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/nudges` | Get current nudges for user |
| POST | `/api/nudges/{type}/dismiss` | Dismiss a nudge |
| GET | `/api/nudges/preferences` | Get user's nudge preferences |

---

## Frontend Implementation

### Phase F1: Enhanced Feedback with Verification Prompt

**File**: `desktop-app/src/renderer/components/message.js`

**Location**: After existing feedback buttons (line ~509)

```javascript
// After user clicks 👍, show verification prompt
async function handleFeedback(messageId, feedbackType) {
    // Existing: Send feedback to API
    const response = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query_history_id: messageId,
            feedback_type: feedbackType
        })
    });

    // NEW: If positive feedback, offer to save as verified
    if (feedbackType === 'upvote') {
        showVerificationPrompt(messageId);
    }

    // NEW: If negative feedback, show correction option
    if (feedbackType === 'downvote') {
        showCorrectionPrompt(messageId);
    }
}

function showVerificationPrompt(messageId) {
    const prompt = document.createElement('div');
    prompt.className = 'verification-prompt';
    prompt.innerHTML = `
        <div class="prompt-content">
            <span class="prompt-icon">✓</span>
            <span class="prompt-text">Save as verified knowledge?</span>
            <div class="prompt-actions">
                <button class="btn-small btn-primary" onclick="saveAsVerified('${messageId}')">
                    Yes, Save
                </button>
                <button class="btn-small btn-secondary" onclick="dismissPrompt(this)">
                    No Thanks
                </button>
            </div>
        </div>
    `;

    // Insert after the message
    const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
    messageEl.appendChild(prompt);

    // Auto-dismiss after 10 seconds
    setTimeout(() => prompt.remove(), 10000);
}

async function saveAsVerified(messageId) {
    await fetch(`${API_BASE}/api/feedback/${messageId}/promote`, {
        method: 'POST'
    });

    // Show success feedback
    showToast('Saved to verified knowledge!', 'success');

    // Remove prompt
    document.querySelector('.verification-prompt')?.remove();
}

function showCorrectionPrompt(messageId) {
    const prompt = document.createElement('div');
    prompt.className = 'correction-prompt';
    prompt.innerHTML = `
        <div class="prompt-content">
            <span class="prompt-icon">✏️</span>
            <span class="prompt-text">What was wrong?</span>
            <div class="prompt-options">
                <button onclick="reportIssue('${messageId}', 'incorrect')">Incorrect Info</button>
                <button onclick="reportIssue('${messageId}', 'outdated')">Outdated</button>
                <button onclick="reportIssue('${messageId}', 'incomplete')">Incomplete</button>
                <button onclick="reportIssue('${messageId}', 'wrong_agent')">Wrong Agent</button>
            </div>
        </div>
    `;

    const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
    messageEl.appendChild(prompt);
}
```

---

### Phase F2: Confidence Badges

**File**: `desktop-app/src/renderer/components/confidence.js` (NEW)

```javascript
/**
 * Confidence Badge Component
 * Shows verification status and confidence level on knowledge items
 */

const ConfidenceLevel = {
    VERIFIED: { icon: '✓', label: 'Verified', class: 'verified', minScore: 0.9 },
    HIGH: { icon: '●', label: 'High Confidence', class: 'high', minScore: 0.8 },
    MEDIUM: { icon: '○', label: 'Medium Confidence', class: 'medium', minScore: 0.6 },
    LOW: { icon: '?', label: 'Needs Review', class: 'low', minScore: 0 }
};

function createConfidenceBadge(item) {
    const badge = document.createElement('span');
    badge.className = 'confidence-badge';

    let level;
    if (item.user_verified) {
        level = ConfidenceLevel.VERIFIED;
    } else if (item.confidence >= 0.8) {
        level = ConfidenceLevel.HIGH;
    } else if (item.confidence >= 0.6) {
        level = ConfidenceLevel.MEDIUM;
    } else {
        level = ConfidenceLevel.LOW;
    }

    badge.classList.add(`confidence-${level.class}`);
    badge.innerHTML = `
        <span class="confidence-icon">${level.icon}</span>
        <span class="confidence-label">${level.label}</span>
        ${!item.user_verified ? `<span class="confidence-score">${(item.confidence * 100).toFixed(0)}%</span>` : ''}
    `;

    // Add tooltip with details
    badge.title = item.user_verified
        ? `Verified by you on ${formatDate(item.verified_at)}`
        : `AI confidence: ${(item.confidence * 100).toFixed(0)}%. Click to verify.`;

    // Click to verify (if not already verified)
    if (!item.user_verified) {
        badge.style.cursor = 'pointer';
        badge.onclick = () => showVerifyModal(item.id);
    }

    return badge;
}

function showVerifyModal(knowledgeId) {
    const modal = document.createElement('div');
    modal.className = 'modal verify-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Verify This Knowledge</h3>
            <div id="knowledge-content" class="knowledge-preview">Loading...</div>
            <div class="verify-actions">
                <button class="btn-primary" onclick="verifyKnowledge('${knowledgeId}', true)">
                    ✓ Confirm Correct
                </button>
                <button class="btn-secondary" onclick="showCorrectionEditor('${knowledgeId}')">
                    ✏️ Edit & Verify
                </button>
                <button class="btn-danger" onclick="markIncorrect('${knowledgeId}')">
                    ✗ Mark Incorrect
                </button>
            </div>
            <button class="modal-close" onclick="closeModal(this)">×</button>
        </div>
    `;

    document.body.appendChild(modal);
    loadKnowledgeContent(knowledgeId);
}
```

**CSS** (`desktop-app/src/renderer/styles/confidence.css`):

```css
/* Confidence Badges */
.confidence-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
}

.confidence-verified {
    background: rgba(34, 197, 94, 0.2);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
}

.confidence-high {
    background: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
    border: 1px solid rgba(59, 130, 246, 0.3);
}

.confidence-medium {
    background: rgba(234, 179, 8, 0.2);
    color: #eab308;
    border: 1px solid rgba(234, 179, 8, 0.3);
}

.confidence-low {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.confidence-icon {
    font-size: 10px;
}

.confidence-score {
    opacity: 0.7;
    font-size: 10px;
}
```

---

### Phase F3: Knowledge View with Filters

**File**: `desktop-app/src/renderer/components/views.js`

**Add to Knowledge/Insights view**:

```javascript
/**
 * Enhanced Knowledge View with verification filters
 */
async function renderKnowledgeView(container) {
    container.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'view-header';
    header.innerHTML = `
        <h2>Knowledge Base</h2>
        <p class="view-subtitle">Your verified facts, insights, and learnings</p>
    `;
    container.appendChild(header);

    // Filter controls
    const filters = document.createElement('div');
    filters.className = 'knowledge-filters';
    filters.innerHTML = `
        <div class="filter-group">
            <label>Status:</label>
            <select id="knowledge-status-filter">
                <option value="all">All Knowledge</option>
                <option value="verified">✓ Verified Only</option>
                <option value="needs_review">? Needs Review</option>
                <option value="high_confidence">● High Confidence</option>
            </select>
        </div>
        <div class="filter-group">
            <label>Source:</label>
            <select id="knowledge-source-filter">
                <option value="all">All Sources</option>
                <option value="chat">Chat Conversations</option>
                <option value="import">Imported Data</option>
                <option value="correction">User Corrections</option>
            </select>
        </div>
        <div class="filter-group">
            <label>Topic:</label>
            <input type="text" id="knowledge-topic-filter" placeholder="Filter by topic...">
        </div>
        <button id="refresh-knowledge" class="btn-secondary">Refresh</button>
    `;
    container.appendChild(filters);

    // Stats bar
    const statsBar = document.createElement('div');
    statsBar.className = 'knowledge-stats-bar';
    statsBar.id = 'knowledge-stats';
    container.appendChild(statsBar);

    // Knowledge list
    const list = document.createElement('div');
    list.className = 'knowledge-list';
    list.id = 'knowledge-list';
    list.innerHTML = '<div class="loading">Loading knowledge...</div>';
    container.appendChild(list);

    // Load initial data
    await loadKnowledgeItems(list, {});
    await loadKnowledgeStats(statsBar);

    // Event listeners
    document.getElementById('knowledge-status-filter').addEventListener('change', reloadKnowledge);
    document.getElementById('knowledge-source-filter').addEventListener('change', reloadKnowledge);
    document.getElementById('knowledge-topic-filter').addEventListener('input',
        debounce(reloadKnowledge, 300));
    document.getElementById('refresh-knowledge').addEventListener('click', reloadKnowledge);
}

async function loadKnowledgeStats(container) {
    try {
        const response = await fetch(`${API_BASE}/api/knowledge/stats`);
        const stats = await response.json();

        container.innerHTML = `
            <div class="stat-item">
                <span class="stat-value">${stats.total}</span>
                <span class="stat-label">Total Facts</span>
            </div>
            <div class="stat-item verified">
                <span class="stat-value">${stats.verified}</span>
                <span class="stat-label">✓ Verified</span>
            </div>
            <div class="stat-item needs-review">
                <span class="stat-value">${stats.needs_review}</span>
                <span class="stat-label">? Needs Review</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${stats.topics}</span>
                <span class="stat-label">Topics</span>
            </div>
        `;
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load stats</div>`;
    }
}

function renderKnowledgeItem(item) {
    const card = document.createElement('div');
    card.className = 'knowledge-card';
    card.setAttribute('data-knowledge-id', item.id);

    // Confidence badge
    const badge = createConfidenceBadge(item);

    // Content
    const content = document.createElement('div');
    content.className = 'knowledge-content';
    content.textContent = item.content;

    // Topics
    const topics = document.createElement('div');
    topics.className = 'knowledge-topics';
    (item.topics || []).forEach(topic => {
        const tag = document.createElement('span');
        tag.className = 'topic-tag';
        tag.textContent = topic;
        topics.appendChild(tag);
    });

    // Actions
    const actions = document.createElement('div');
    actions.className = 'knowledge-actions';
    actions.innerHTML = `
        <button class="btn-icon" onclick="verifyKnowledge('${item.id}')" title="Verify">✓</button>
        <button class="btn-icon" onclick="editKnowledge('${item.id}')" title="Edit">✏️</button>
        <button class="btn-icon" onclick="deleteKnowledge('${item.id}')" title="Delete">🗑️</button>
    `;

    // Metadata
    const meta = document.createElement('div');
    meta.className = 'knowledge-meta';
    meta.innerHTML = `
        <span class="source">${item.source || 'chat'}</span>
        <span class="date">${formatDate(item.created_at)}</span>
    `;

    card.appendChild(badge);
    card.appendChild(content);
    card.appendChild(topics);
    card.appendChild(actions);
    card.appendChild(meta);

    return card;
}
```

---

### Phase F4: Nudge Component

**File**: `desktop-app/src/renderer/components/nudge.js` (NEW)

```javascript
/**
 * Nudge Component - Shows proactive insights and suggestions
 */

class NudgeManager {
    constructor() {
        this.container = null;
        this.nudges = [];
        this.dismissedToday = new Set(
            JSON.parse(localStorage.getItem('dismissedNudges') || '[]')
        );
    }

    async init(container) {
        this.container = container;
        await this.loadNudges();
        this.render();
    }

    async loadNudges() {
        try {
            const response = await fetch(`${API_BASE}/api/nudges`);
            const data = await response.json();
            this.nudges = data.nudges || [];
        } catch (error) {
            console.error('Failed to load nudges:', error);
            this.nudges = [];
        }
    }

    render() {
        if (!this.container) return;

        // Filter out dismissed nudges
        const activeNudges = this.nudges.filter(
            n => !this.dismissedToday.has(n.nudge_type)
        );

        if (activeNudges.length === 0) {
            this.container.innerHTML = '';
            return;
        }

        this.container.innerHTML = '';
        this.container.className = 'nudge-container';

        activeNudges.forEach(nudge => {
            const card = this.createNudgeCard(nudge);
            this.container.appendChild(card);
        });
    }

    createNudgeCard(nudge) {
        const card = document.createElement('div');
        card.className = `nudge-card nudge-${nudge.nudge_type}`;

        const icons = {
            'weekly_digest': '📊',
            'topic_deep_dive': '🔍',
            'knowledge_review': '✓',
            'expertise_growth': '📈'
        };

        card.innerHTML = `
            <div class="nudge-icon">${icons[nudge.nudge_type] || '💡'}</div>
            <div class="nudge-content">
                <div class="nudge-title">${escapeHtml(nudge.title)}</div>
                <div class="nudge-description">${escapeHtml(nudge.description)}</div>
            </div>
            <div class="nudge-actions">
                <button class="nudge-action-btn" data-action="${JSON.stringify(nudge.action_data).replace(/"/g, '&quot;')}">
                    ${escapeHtml(nudge.action_label)}
                </button>
                ${nudge.dismissible ? `
                    <button class="nudge-dismiss-btn" data-type="${nudge.nudge_type}">
                        ✕
                    </button>
                ` : ''}
            </div>
        `;

        // Action button handler
        card.querySelector('.nudge-action-btn')?.addEventListener('click', (e) => {
            const actionData = JSON.parse(e.target.dataset.action);
            this.handleNudgeAction(actionData);
        });

        // Dismiss button handler
        card.querySelector('.nudge-dismiss-btn')?.addEventListener('click', (e) => {
            const nudgeType = e.target.dataset.type;
            this.dismissNudge(nudgeType, card);
        });

        return card;
    }

    handleNudgeAction(actionData) {
        // Navigate to the appropriate view
        if (actionData.view) {
            navigateToView(actionData.view, actionData);
        }
    }

    async dismissNudge(nudgeType, cardElement) {
        // Add to dismissed set
        this.dismissedToday.add(nudgeType);
        localStorage.setItem('dismissedNudges', JSON.stringify([...this.dismissedToday]));

        // Animate removal
        cardElement.classList.add('nudge-dismissing');
        setTimeout(() => cardElement.remove(), 300);

        // Tell server
        try {
            await fetch(`${API_BASE}/api/nudges/${nudgeType}/dismiss`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ duration: 'today' })
            });
        } catch (error) {
            console.error('Failed to record dismiss:', error);
        }
    }
}

// Initialize on page load
const nudgeManager = new NudgeManager();
```

**CSS** (`desktop-app/src/renderer/styles/nudge.css`):

```css
/* Nudge Cards */
.nudge-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
    border-radius: 8px;
    margin-bottom: 16px;
}

.nudge-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: rgba(30, 30, 30, 0.8);
    border-radius: 8px;
    border-left: 3px solid #3b82f6;
    transition: all 0.2s ease;
}

.nudge-card:hover {
    background: rgba(40, 40, 40, 0.9);
    transform: translateX(4px);
}

.nudge-card.nudge-dismissing {
    opacity: 0;
    transform: translateX(-100px);
}

.nudge-icon {
    font-size: 24px;
    flex-shrink: 0;
}

.nudge-content {
    flex: 1;
    min-width: 0;
}

.nudge-title {
    font-weight: 600;
    color: #e0e0e0;
    margin-bottom: 2px;
}

.nudge-description {
    font-size: 13px;
    color: #888;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.nudge-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
}

.nudge-action-btn {
    padding: 6px 12px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.2s;
}

.nudge-action-btn:hover {
    background: #2563eb;
}

.nudge-dismiss-btn {
    padding: 4px 8px;
    background: transparent;
    color: #666;
    border: none;
    cursor: pointer;
    font-size: 14px;
}

.nudge-dismiss-btn:hover {
    color: #ef4444;
}

/* Nudge type-specific colors */
.nudge-knowledge_review {
    border-left-color: #22c55e;
}

.nudge-topic_deep_dive {
    border-left-color: #8b5cf6;
}

.nudge-expertise_growth {
    border-left-color: #f59e0b;
}
```

---

## UX Scenarios & Acceptance Criteria

### Scenario 1: Feedback-Driven Learning

**User Story**: "When I give positive feedback, ACMS should learn from it"

**Steps**:
1. User asks: "What is the SOLID principle in software?"
2. Claude responds with explanation
3. User clicks 👍 (thumbs up)
4. **NEW**: Prompt appears: "Save as verified knowledge?"
5. User clicks "Yes, Save"
6. **Verification**: Toast shows "Saved to verified knowledge!"

**Acceptance Criteria**:
- [ ] Verification prompt appears within 500ms of clicking 👍
- [ ] Prompt auto-dismisses after 10 seconds if no action
- [ ] "Yes, Save" creates entry in ACMS_QualityCache_v1
- [ ] Entry has `user_verified: true`
- [ ] Toast notification confirms save

**Test Commands**:
```bash
# After saving as verified, check cache
curl http://localhost:40080/api/cache/quality/stats | jq '.verified_count'

# Should increase by 1
```

---

### Scenario 2: Correction Flow

**User Story**: "When I see wrong information, I should be able to fix it"

**Steps**:
1. User views Knowledge Base
2. Sees fact: "ACMS uses PostgreSQL for vector storage"
3. Clicks ✏️ (edit) button
4. Modal opens with current content
5. User corrects to: "ACMS uses Weaviate for vector storage, PostgreSQL for relational data"
6. Clicks "Save Correction"
7. **Verification**: Fact updated, marked as verified

**Acceptance Criteria**:
- [ ] Edit modal loads within 300ms
- [ ] Original content is pre-filled
- [ ] Save creates correction audit record
- [ ] Updated fact has `user_verified: true`
- [ ] Confidence badge changes to ✓ Verified

**Test Commands**:
```bash
# Check correction was recorded
curl http://localhost:40080/api/knowledge/{id}/history | jq '.'

# Should show correction record with original and corrected content
```

---

### Scenario 3: Proactive Knowledge Review

**User Story**: "ACMS should tell me when facts need my attention"

**Steps**:
1. User opens ACMS desktop app
2. **NEW**: Nudge appears at top: "3 facts need your verification"
3. User clicks "Review Now"
4. Navigates to Knowledge Base with filter set to "Needs Review"
5. Shows items with confidence < 0.8 and user_verified = false
6. User verifies or corrects each item

**Acceptance Criteria**:
- [ ] Nudge appears if `needs_review_count > 0`
- [ ] Click navigates to correct view with filter applied
- [ ] "Needs Review" items are sorted by oldest first
- [ ] After verifying all, nudge disappears
- [ ] Dismissing nudge hides it for 24 hours

**Test Commands**:
```bash
# Get nudges
curl http://localhost:40080/api/nudges | jq '.nudges[] | select(.nudge_type == "knowledge_review")'

# Should show nudge if there are unverified items
```

---

### Scenario 4: Quality Cache Hit

**User Story**: "When I ask a similar question, I should get my verified answer"

**Steps**:
1. User previously verified answer to "What is SOLID?"
2. Now asks: "Explain the SOLID principles"
3. **NEW**: Response comes from QualityCache (fast)
4. Response shows badge: "From your verified knowledge"
5. Response includes original answer with 98% similarity match

**Acceptance Criteria**:
- [ ] Cache hit within 100ms (vs 2-3s for fresh generation)
- [ ] Response shows "verified" badge
- [ ] Similarity score >= 0.95
- [ ] Original response is returned (not regenerated)
- [ ] Cache hit is logged for analytics

**Test Commands**:
```bash
# First, verify an answer (see Scenario 1)
# Then ask similar question
curl -X POST http://localhost:40080/gateway/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain the SOLID principles", "user_id": "test"}'

# Response should include: "from_cache": true, "cache_type": "quality"
```

---

### Scenario 5: Negative Feedback Demotion

**User Story**: "When I mark something as wrong, it shouldn't be served again"

**Steps**:
1. User receives response from cache
2. Response is incorrect
3. User clicks 👎 (thumbs down)
4. **NEW**: Prompt asks "What was wrong?" with options
5. User selects "Incorrect Info"
6. **Verification**: Entry demoted from cache

**Acceptance Criteria**:
- [ ] Prompt appears after 👎 click
- [ ] Options: Incorrect/Outdated/Incomplete/Wrong Agent
- [ ] Selected reason is recorded
- [ ] Cache entry's `negative_feedback_count` increments
- [ ] If count > 2, entry is no longer served
- [ ] Same query now gets fresh generation

**Test Commands**:
```bash
# After downvote, check cache entry
curl http://localhost:40080/api/cache/quality/entry/{id} | jq '.negative_feedback_count'

# Should be >= 1

# If count > 2, verify it's not served
curl -X POST http://localhost:40080/gateway/chat \
  -d '{"query": "same query", "user_id": "test"}'

# Should NOT have "from_cache": true
```

---

### Scenario 6: Weekly Learning Digest

**User Story**: "ACMS should summarize what I learned this week"

**Steps**:
1. It's Monday morning (or user's first session of the week)
2. **NEW**: Nudge appears: "Your Week in Review"
3. Description shows: "You explored 5 topics and learned 12 new facts"
4. User clicks "See Details"
5. Navigates to Insights view with weekly summary

**Acceptance Criteria**:
- [ ] Digest nudge only appears once per week
- [ ] Shows accurate count of topics and facts
- [ ] Details view shows week's top topics
- [ ] Shows which facts were added
- [ ] Dismissing hides until next week

---

### Scenario 7: Topic Deep Dive Suggestion

**User Story**: "When I explore a topic repeatedly, ACMS should notice"

**Steps**:
1. User has asked about "Python async" 5 times this week
2. On 6th query about async
3. **NEW**: Nudge appears: "Deep Dive: Python Async"
4. Description: "You've explored this 5 times this week. View summary?"
5. User clicks "View Summary"
6. Shows aggregated knowledge about Python async from all conversations

**Acceptance Criteria**:
- [ ] Nudge triggers after 5+ queries on same topic
- [ ] Topic detection uses semantic clustering (not exact match)
- [ ] Summary shows all related facts
- [ ] Summary shows timeline of exploration
- [ ] Can mark as "expertise area"

---

## Multi-Hat Validation Framework

### After Implementation: Testing with Different Perspectives

#### PM Perspective Questions

| Question | Expected Answer | How to Verify |
|----------|-----------------|---------------|
| "Does the system learn from my feedback?" | Yes, 👍 promotes to verified cache | Check cache after feedback |
| "Can I see what ACMS thinks it knows?" | Yes, Knowledge Base shows all facts | Browse Knowledge view |
| "How confident is this information?" | Badges show verified/high/medium/low | Visual inspection |
| "Can I correct mistakes?" | Yes, edit button on every fact | Edit and verify change |
| "Does ACMS remind me about things?" | Yes, nudges appear for review/digest | Check nudge appearance |

#### Architect Perspective Questions

| Question | Expected Answer | How to Verify |
|----------|-----------------|---------------|
| "Is the feedback loop closed?" | Yes, feedback → cache promotion | Trace data flow |
| "Is quality cache separate from raw storage?" | Yes, ACMS_QualityCache_v1 vs ACMS_Raw_v1 | Check Weaviate collections |
| "Does cache respect agent preference?" | Yes, agent_used field checked | Request different agents |
| "Is web search data handled specially?" | Yes, contains_web_search flag, 1hr TTL | Check cache entry |
| "Are corrections auditable?" | Yes, correction history stored | Check audit trail |

#### Developer Perspective Questions

| Question | Expected Answer | How to Verify |
|----------|-----------------|---------------|
| "What new endpoints exist?" | /promote, /demote, /correct, /verify, /nudges | Check API docs |
| "What new Weaviate collection?" | ACMS_QualityCache_v1 | List collections |
| "What new UI components?" | confidence.js, nudge.js | Check component files |
| "Are existing tests passing?" | Yes | Run pytest |
| "Is backward compatible?" | Yes, existing features unchanged | Run existing flows |

#### User Perspective Questions

| Question | Expected Answer | How to Verify |
|----------|-----------------|---------------|
| "Is the app faster for repeated questions?" | Yes, cache hit < 100ms | Time responses |
| "Do I trust the information more?" | Yes, verified badge visible | Check confidence display |
| "Can I fix wrong answers easily?" | Yes, one-click edit | Try correction flow |
| "Does it feel like it's learning?" | Yes, nudges acknowledge progress | Check nudge content |
| "Is it annoying with notifications?" | No, nudges dismissible and limited | Dismiss and check |

---

## Implementation Phases

### Phase 1: Backend Foundation (3 days)

| Task | File | Effort |
|------|------|--------|
| Create QualityCache class | `src/cache/quality_cache.py` | 4 hrs |
| Create ACMS_QualityCache_v1 schema | Weaviate migration | 1 hr |
| Create FeedbackPromoter | `src/feedback/promoter.py` | 3 hrs |
| Add /promote and /demote endpoints | `src/api_server.py` | 2 hrs |
| Create KnowledgeCorrector | `src/intelligence/corrector.py` | 3 hrs |
| Add /correct and /verify endpoints | `src/api_server.py` | 2 hrs |
| Write unit tests | `tests/unit/` | 4 hrs |

### Phase 2: Backend Intelligence (2 days)

| Task | File | Effort |
|------|------|--------|
| Create NudgeEngine | `src/intelligence/nudge_engine.py` | 4 hrs |
| Add /nudges endpoints | `src/api_server.py` | 2 hrs |
| Integrate QualityCache in orchestrator | `src/gateway/orchestrator.py` | 3 hrs |
| Add cache analytics endpoint | `src/api_server.py` | 2 hrs |
| Write integration tests | `tests/integration/` | 3 hrs |

### Phase 3: Frontend Components (3 days)

| Task | File | Effort |
|------|------|--------|
| Add verification prompt to feedback | `message.js` | 3 hrs |
| Create ConfidenceBadge component | `confidence.js` | 2 hrs |
| Create NudgeManager component | `nudge.js` | 4 hrs |
| Add nudge container to main layout | `app.js` | 1 hr |
| Update Knowledge view with filters | `views.js` | 4 hrs |
| Add correction modal | `views.js` | 3 hrs |
| Create CSS styles | `confidence.css`, `nudge.css` | 2 hrs |

### Phase 4: Integration & Testing (2 days)

| Task | Effort |
|------|--------|
| End-to-end testing of all scenarios | 4 hrs |
| Fix bugs from testing | 4 hrs |
| Performance testing (cache hit latency) | 2 hrs |
| User acceptance testing | 4 hrs |
| Documentation update | 2 hrs |

**Total Estimated Effort**: 10 working days

---

## Success Metrics

### Quantitative Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Cache hit rate | 0% (disabled) | 20-30% | `/api/cache/quality/stats` |
| Avg response time (cache hit) | N/A | < 200ms | Analytics dashboard |
| User verifications per week | 0 | 10+ | Track /verify calls |
| User corrections per week | 0 | 2+ | Track /correct calls |
| Nudge engagement rate | N/A | 30%+ | Click vs dismiss ratio |
| Knowledge items verified | 0 | 50+ in month 1 | DB count |

### Qualitative Metrics

| Aspect | Success Indicator |
|--------|-------------------|
| User trust | Users click verify instead of ignoring |
| Perceived learning | Users report "ACMS knows more about me" |
| Active engagement | Users check Knowledge Base regularly |
| Correction comfort | Users fix facts without hesitation |
| Nudge value | Users find nudges helpful, not annoying |

---

## Rollout Plan

### Week 1: Backend Only
- Deploy QualityCache, FeedbackPromoter, KnowledgeCorrector
- Enable for internal testing only
- Monitor for errors

### Week 2: Frontend Components
- Deploy confidence badges (read-only)
- Deploy nudge system (dismissible)
- No changes to feedback buttons yet

### Week 3: Full Integration
- Enable verification prompt on 👍
- Enable correction flow on edit
- Enable cache hit display

### Week 4: Monitoring & Tuning
- Monitor cache hit rate
- Adjust similarity threshold if needed
- Tune nudge frequency based on feedback

---

## Appendix: File Changes Summary

### New Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/cache/quality_cache.py` | Quality-gated semantic cache | ~200 |
| `src/feedback/promoter.py` | Feedback-to-cache promotion | ~100 |
| `src/intelligence/corrector.py` | User corrections handler | ~150 |
| `src/intelligence/nudge_engine.py` | Proactive nudge generation | ~200 |
| `desktop-app/.../confidence.js` | Confidence badge component | ~100 |
| `desktop-app/.../nudge.js` | Nudge display component | ~150 |
| `desktop-app/.../confidence.css` | Badge styles | ~50 |
| `desktop-app/.../nudge.css` | Nudge styles | ~80 |

### Modified Files

| File | Changes | Lines Changed |
|------|---------|---------------|
| `src/api_server.py` | Add new endpoints | ~100 |
| `src/gateway/orchestrator.py` | Integrate QualityCache | ~50 |
| `desktop-app/.../message.js` | Add verification prompt | ~50 |
| `desktop-app/.../views.js` | Add Knowledge filters, correction modal | ~150 |
| `desktop-app/.../app.js` | Add nudge container | ~20 |
| `desktop-app/.../sidebar.js` | Add notification indicator | ~20 |

**Total New Code**: ~1,420 lines
**Total Modified**: ~390 lines
