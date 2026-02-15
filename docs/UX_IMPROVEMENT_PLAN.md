# ACMS UX Improvement Plan - Product-Grade Views

> **Generated:** February 6, 2026
> **Analysis Method:** Multi-agent SDLC review with 10 iterations per persona
> **Scope:** Memories, Knowledge, Financial, Reports/Insights views

---

## Executive Summary

After comprehensive analysis by PM, UX Designer, Architect, and QA agents, we've identified that the current ACMS views suffer from **three core problems**:

1. **Data Problem**: We're showing raw data (Q&A pairs) instead of synthesized understanding
2. **Display Problem**: Cards are data dumps without hierarchy, context, or interactivity
3. **Trust Problem**: Users can't verify, correct, or understand what the system "knows"

### Key Insight from Research

> "AI memory shouldn't feel like a secret diary the model keeps behind the scenes. It should feel like a collaborative notebook." - Industry best practice

**Best-in-class tools (Claude Desktop, Notion, Obsidian, Linear) succeed because they:**
- Show **synthesized understanding**, not raw data
- Provide **user control** (edit, delete, verify)
- Display **confidence and source** attribution
- Use **progressive disclosure** (expand to see more)
- Create **visual hierarchy** that guides attention

---

## Current vs. Desired State

### Memories View

| Current | Desired |
|---------|---------|
| Random Q&A pairs | Clustered conversations by topic |
| Truncated content, no expand | Click-to-expand full conversation |
| No source attribution | "This led to X knowledge items" |
| Static list | Timeline with related items |

**Rename:** "Memories" → "Conversation History"

### Knowledge View

| Current | Desired |
|---------|---------|
| Shallow Q&A responses | Synthesized statements with confidence |
| No depth hierarchy | Domain tree navigation |
| No click-to-expand | Full article with source conversations |
| No verification | Verify/Correct/Delete actions |

**Rename:** "Knowledge" → "What I Know About You"

### Financial View

| Current | Desired |
|---------|---------|
| Static account list | Interactive Constitution rules |
| No alerts | Graduated severity alerts |
| Dollar amounts always shown | Privacy mode (percentages only) |
| No AI recommendations | Contextual, actionable suggestions |

### Reports/Insights

| Current | Desired |
|---------|---------|
| Basic text output | Visual story with charts |
| Static data | Change-focused narrative |
| Generic recommendations | SCAR format (Situation, Cause, Action, Result) |
| No personalization | Learns from user behavior |

---

## Architecture Changes Required

### New Database Tables

| Table | Purpose |
|-------|---------|
| `memory_clusters` | Group related memories by topic |
| `memory_cluster_members` | Cluster membership |
| `consolidated_knowledge` | Merged authoritative facts (not duplicates) |
| `knowledge_provenance` | Source attribution chain |
| `memory_quality_metrics` | Quality scores per memory |
| `knowledge_domains` | Hierarchical taxonomy |
| `confidence_snapshots` | Trend tracking over time |

### New Background Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `cluster_discovery` | Weekly | Group 97K memories into topic clusters |
| `knowledge_consolidation` | Daily | Merge duplicate facts into single authoritative items |
| `confidence_decay` | Daily | Reduce confidence of stale items |
| `quality_assessment` | Daily | Score memory quality |
| `domain_classification` | Daily | Classify into taxonomy |

### New API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v2/clusters` | List memory clusters |
| `GET /api/v2/clusters/{id}/members` | Cluster details |
| `GET /api/v2/knowledge/{id}` | Knowledge with provenance |
| `GET /api/v2/graph/entity/{name}` | Entity relationship graph |
| `GET /api/v2/domains` | Domain taxonomy tree |
| `GET /api/v2/trends/confidence` | Confidence trends |

---

## UX Design Specifications

### Design System

```css
/* Typography Scale (8px grid) */
--text-hero: 32px;   /* Page titles */
--text-h1: 24px;     /* Section headers */
--text-h2: 18px;     /* Card titles */
--text-body: 15px;   /* Primary content */
--text-small: 13px;  /* Metadata */

/* Spacing Scale */
--space-2: 8px;   --space-3: 12px;  --space-4: 16px;
--space-5: 24px;  --space-6: 32px;  --space-7: 48px;

/* Colors - Dark Theme */
--bg-app: #0D0D0D;
--bg-surface: #141414;
--bg-elevated: #1A1A1A;
--accent-green: #4CAF50;
--accent-blue: #2196F3;
--accent-purple: #9333EA;
```

### Card Variants

1. **Standard Card** - Background with subtle border, 12px radius
2. **Expandable Card** - Collapsed preview + expand animation (300ms)
3. **Insight Card** - Left accent border colored by confidence
4. **Metric Card** - Large centered value with optional sparkline

### Confidence Visualization

```
●●●●○ 80-100% = Verified (Green)
●●●○○ 60-79%  = High (Blue)
●●○○○ 40-59%  = Medium (Yellow)
●○○○○ 20-39%  = Low (Orange)
○○○○○ 0-19%   = Unverified (Red)
```

---

## View Specifications

### 1. Conversation History (Memories)

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER: Conversation History                           [Filter] │
├─────────────────────────────────────────────────────────────────┤
│ FILTER PILLS: [All] [Today] [This Week] [By Topic ▾]           │
├─────────────────────────────────────────────────────────────────┤
│ TIMELINE VIEW                                                   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 📅 Jan 14, 2026 at 3:42 PM                                  │ │
│ │ Topic: Python Async Patterns                                │ │
│ │                                                             │ │
│ │ "How do I handle concurrent API calls in FastAPI?"          │ │
│ │                                                             │ │
│ │ 🏷️ #python #async #fastapi                                 │ │
│ │ 💡 Extracted: 2 knowledge items                            │ │
│ │                                                             │ │
│ │ [▼ Expand Conversation]  [View Knowledge]                   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Click anywhere to expand full Q&A
- Shows what knowledge was extracted
- Groups related memories visually
- Timeline organization (not random list)

### 2. What I Know About You (Knowledge)

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER: What I Know About You                   [+ Extract New] │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┬─────────────────────────────────────┤
│ │ DOMAIN TREE             │ KNOWLEDGE CARDS                     │
│ │                         │                                     │
│ │ ▼ Technology (45)       │ ┌─────────────────────────────────┐ │
│ │   ▸ Python (12)         │ │ ●●●●○ 82% Confidence           │ │
│ │   ▸ Databases (15)      │ │                                 │ │
│ │ ▼ Finance (23)          │ │ "You prefer async/await over    │ │
│ │   ▸ Investing (18)      │ │  callbacks for concurrent code" │ │
│ │                         │ │                                 │ │
│ │                         │ │ 📚 From 3 conversations         │ │
│ │                         │ │ 🕐 Updated Jan 14               │ │
│ │                         │ │                                 │ │
│ │                         │ │ [Edit] [View Sources] [Verify]  │ │
│ │                         │ └─────────────────────────────────┘ │
│ └─────────────────────────┴─────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Domain tree for navigation
- Confidence scores with visual indicators
- Source attribution (which conversations)
- Edit/Verify/Delete actions
- Synthesized statements (not Q&A format)

### 3. Financial Constitution

```
┌─────────────────────────────────────────────────────────────────┐
│ MY FINANCIAL CONSTITUTION                                       │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Rule #1: Target Allocation                          [Edit]  │ │
│ │ Stocks: 60% | Bonds: 30% | Cash: 10%                        │ │
│ │ Status: ✓ Within tolerance (62% stocks, +2%)               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Rule #2: Emergency Fund                             [Edit]  │ │
│ │ Maintain at least 6 months expenses                         │ │
│ │ Status: ⚠️ Currently at 4.2 months                          │ │
│ │                                                             │ │
│ │ 💡 AI Recommendation:                                       │ │
│ │ "At your current savings rate, you'll reach 6 months        │ │
│ │  by March 15th. Consider increasing by $X to hit it         │ │
│ │  by February."                                              │ │
│ │                                                             │ │
│ │ [Acknowledge] [Snooze] [Adjust Target] [Create Plan]        │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- User-defined rules with real-time status
- Graduated severity (green/yellow/red)
- AI recommendations with context
- Action buttons (not just alerts)
- Privacy mode (percentages only)

### 4. Intelligence Reports

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 Your Week in Review                      Jan 6-12, 2026     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 🎯 CONSTITUTION STATUS                                          │
│ 3 of 5 rules in good standing                                  │
│ 1 needs attention • 1 improving                                │
│                                                                 │
│ 📈 WHAT CHANGED                                                 │
│ • Stock allocation: 60% → 62% (market movement)                │
│ • Emergency fund: Now at 4.5 months (+0.3)                     │
│ • Python knowledge confidence: +8% (3 new verifications)       │
│                                                                 │
│ 💡 ONE THING TO CONSIDER                                        │
│ "Your emergency fund is 1.5 months from your goal.             │
│  You're on track to hit it by March 15th."                     │
│                                                                 │
│ [See Full Details]  [Ask Question]                             │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Leads with user-defined priorities (constitution status)
- Highlights CHANGES, not static state
- One clear "thing to consider"
- Charts for trends (confidence, allocation)

---

## User Stories

### P0 - Critical

| ID | Story | View |
|----|-------|------|
| US-M1 | Click any memory to see full conversation | Memories |
| US-K1 | View knowledge organized by domain | Knowledge |
| US-K2 | See confidence score on each knowledge item | Knowledge |
| US-K3 | Edit or delete incorrect knowledge | Knowledge |
| US-F1 | Define financial rules via guided conversation | Financial |
| US-F2 | See clear alerts when rules are violated | Financial |

### P1 - High

| ID | Story | View |
|----|-------|------|
| US-M2 | See what knowledge was extracted from each conversation | Memories |
| US-M3 | Search and filter conversations | Memories |
| US-K4 | Click knowledge to see source conversations | Knowledge |
| US-K5 | Verify knowledge items to boost confidence | Knowledge |
| US-F3 | Receive AI recommendations for rule violations | Financial |
| US-F4 | Toggle between dollar and percentage views | Financial |
| US-R1 | See weekly summary highlighting changes | Reports |

### P2 - Medium

| ID | Story | View |
|----|-------|------|
| US-M4 | See related memories grouped together | Memories |
| US-K6 | Browse entity relationship graph | Knowledge |
| US-K7 | See confidence trends over time | Knowledge |
| US-F5 | Snooze alerts with custom timeframe | Financial |
| US-R2 | Interactive trend charts | Reports |
| US-R3 | Cross-source insights (email + financial) | Reports |

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Add CSS design system variables
- [ ] Create expandable card component
- [ ] Add skeleton loading states
- [ ] Rename views (Memories → Conversation History, Knowledge → What I Know)

### Phase 2: Memories Overhaul (Week 3-4)
- [ ] Implement click-to-expand
- [ ] Add "knowledge extracted" indicator
- [ ] Timeline layout
- [ ] Search and filter

### Phase 3: Knowledge Overhaul (Week 5-6)
- [ ] Domain tree navigation
- [ ] Confidence visualization
- [ ] Source attribution (provenance)
- [ ] Edit/Verify/Delete actions
- [ ] Backend: consolidated_knowledge table + consolidation job

### Phase 4: Financial Constitution (Week 7-8)
- [ ] Rule builder wizard
- [ ] Rule cards with status
- [ ] Violation alerts with severity
- [ ] AI recommendations
- [ ] Privacy mode toggle

### Phase 5: Reports Polish (Week 9-10)
- [ ] Weekly summary redesign
- [ ] Trend charts
- [ ] SCAR format for insights
- [ ] Cross-source insights

### Phase 6: Backend Intelligence (Week 11-12)
- [ ] Memory clustering job
- [ ] Knowledge consolidation job
- [ ] Confidence decay job
- [ ] Quality assessment job

---

## Test Coverage

**QA has created 121 test cases across all views:**

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 28 | Critical - Must pass |
| P1 | 43 | High - Required for production |
| P2 | 42 | Medium - Quality release |
| P3 | 8 | Low - Nice to have |

Full test suite: `docs/UX_TEST_SUITE_VIEWS.md`

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Memory click-to-expand usage | 0% | >50% |
| Knowledge verification rate | 0% | >30% |
| Constitution setup completion | N/A | >80% |
| Report open rate | Unknown | >50% |
| Insight action rate | Unknown | >40% |
| User-reported trust score | Unknown | >4/5 |

---

## Next Steps

1. **PM Sign-off**: Review user stories and acceptance criteria
2. **Design Review**: Create Figma mockups from wireframes
3. **Architect Sign-off**: Review schema changes and migration plan
4. **Sprint Planning**: Break into 2-week sprints
5. **Begin Phase 1**: CSS foundation + expandable cards

---

*This document was generated through multi-agent analysis with 10 iterations per persona, following the ACMS Agent-Based TDD Workflow.*
