# ACMS Cognitive Architecture — UI Specification
## How Cognitive Improvements Surface to the User
### February 2026

---

## Design Philosophy: The Interface Should Disappear

From Chapter 3 (The Extended Mind), Principle 7: **The more the user is aware of the interface, the less it functions as a cognitive extension.** The ideal state is one where the boundary between "what I know" and "what the system knows" feels seamless.

This means ACMS's UI should NOT look like a traditional dashboard full of graphs and metrics. It should feel like a natural extension of the user's thinking process. The cognitive improvements should surface as **ambient intelligence** — information that appears when needed, adapts to context, and never demands attention it doesn't deserve.

### Three UI Surfaces

Every improvement manifests across three distinct surfaces:

1. **The Conversation Stream** — The primary interaction surface. Cognitive signals appear inline, contextually, during the user's natural workflow. This is the "working memory" of the UI.

2. **The Knowledge Dashboard** — A dedicated surface for reviewing, confirming, and exploring the system's understanding. This is the "consolidation review" surface — the human-in-the-loop mechanism from the desirable difficulty principle.

3. **The Weekly Digest** — A periodic summary that surfaces insights, cross-domain connections, and knowledge evolution. This is the "weekly report" surface — analogous to the weekly consolidation stage in the intelligence pipeline.

---

## TIER 1 UI: CONVERSATION STREAM ENHANCEMENTS

These changes are visible during normal conversation — the user doesn't need to navigate anywhere to benefit.

---

### 1.1 Consolidation Triage → Consolidation Confidence Indicator

**Backend:** ConsolidationTriager scores queries as FULL_EXTRACTION, LIGHTWEIGHT_TAGGING, or TRANSIENT.

**UI Manifestation:** After each response, a subtle indicator shows whether the interaction will be deeply remembered, lightly tagged, or allowed to fade.

```
┌─────────────────────────────────────────────────────┐
│  User: How do I implement OAuth2 refresh tokens     │
│        in a Go microservice?                        │
│                                                     │
│  ACMS: [detailed response with code examples]       │
│                                                     │
│  ◆ Deep memory · OAuth2 · Go · microservices        │
│    ↳ This interaction will be fully consolidated     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  User: What time is it in Tokyo?                    │
│                                                     │
│  ACMS: It's currently 2:34 AM JST.                  │
│                                                     │
│  ○ Ephemeral                                        │
└─────────────────────────────────────────────────────┘
```

**Design Details:**
- **◆ Deep memory** — Solid diamond, colored (e.g., warm amber). Shows topic tags. Clickable to see what will be extracted.
- **◇ Light memory** — Outline diamond, muted. Shows basic tags only.
- **○ Ephemeral** — Small circle, faded. No tags. Interaction fades after TTL.
- The indicator is *small and peripheral* — it should never compete with the response content for attention. Think of it as a subtle status light, not a dashboard widget.
- User can click to override: promote an ephemeral interaction to deep memory, or demote a deep memory to ephemeral ("don't remember this").

**Extended Mind Principle:** This implements the "past endorsement" condition (Chapter 3). By making consolidation visible and overridable, the user participates in encoding — creating stronger cognitive ownership of what the system stores. This is also the "desirable difficulty" mechanism: the user's attention to the indicator strengthens their own awareness of what knowledge they're building.

---

### 1.2 Adaptive Thresholds → Retrieval Mode Signal

**Backend:** RetrievalMode switches between EXACT_RECALL, CONCEPTUAL_EXPLORE, TROUBLESHOOT, COMPARE based on query intent.

**UI Manifestation:** When the system uses stored knowledge to answer a query, the response header shows which retrieval mode was used and what sources contributed.

```
┌─────────────────────────────────────────────────────┐
│  User: What was the exact kubectl command I used     │
│        for RBAC last week?                           │
│                                                     │
│  ┌ Recalled from memory ─────────────────────────┐  │
│  │ 🔍 Exact recall · 2 matches · Feb 3 session   │  │
│  └────────────────────────────────────────────────┘  │
│                                                     │
│  ACMS: The command you used was:                     │
│  kubectl create clusterrolebinding admin-binding ... │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  User: What do I know about Kubernetes security?     │
│                                                     │
│  ┌ Assembled from knowledge ─────────────────────┐  │
│  │ 🧠 Exploration · 14 sources · 3 topic clusters│  │
│  └────────────────────────────────────────────────┘  │
│                                                     │
│  ACMS: Based on your interactions over the past      │
│  month, here's your knowledge landscape...           │
└─────────────────────────────────────────────────────┘
```

**Design Details:**
- The retrieval header is **collapsible** — shows one-line summary by default, expands to show source list on click.
- Different retrieval modes get different icons:
  - 🔍 Exact recall (magnifying glass — precise search)
  - 🧠 Exploration (brain — broad knowledge assembly)
  - 🔧 Troubleshoot (wrench — problem-solution matching)
  - ⚖️ Compare (scales — multi-item retrieval)
- Source count and time range help the user calibrate trust: "14 sources across 3 months" is more trustworthy than "1 source from 6 months ago."
- When NO relevant knowledge is found, the header says "Fresh response · No prior context" — making explicit that this is new territory.

**Extended Mind Principle:** This implements domain-specific trust calibration (Chapter 3). The user can see how much stored knowledge contributed to the response, which helps them calibrate how much to trust it. Over time, they learn which topic areas ACMS is strong in and which are sparse — developing an accurate mental model of the system's reliability.

---

### 1.3 Propagated Forgetting → Correction Ripple Notification

**Backend:** When a downvoted entry triggers propagated_forget(), related entries are flagged for review.

**UI Manifestation:** After the user downvotes a response, a brief notification shows the cascade effect.

```
┌─────────────────────────────────────────────────────┐
│  User downvotes a response about OAuth sessions      │
│                                                     │
│  ┌ Knowledge updated ────────────────────────────┐  │
│  │ ✕ Removed: "OAuth requires session cookies"    │  │
│  │ ⚠ 3 related entries flagged for your review    │  │
│  │   → View in Knowledge Dashboard                │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Design Details:**
- Notification appears inline, below the downvoted response.
- Shows what was removed and how many related items were flagged.
- "View in Knowledge Dashboard" link takes user to the review queue (see Dashboard section below).
- The notification fades after 10 seconds but remains accessible in the conversation history.
- Tone is informative, not alarming: "I've updated my knowledge and flagged related items for your review."

**Extended Mind Principle:** This makes the forgetting process visible and participatory. The user sees that their correction doesn't just affect one response — it cascades through related knowledge. This builds trust in the system's ability to self-correct, which is critical for the trust condition of cognitive extension.

---

## TIER 2 UI: KNOWLEDGE DASHBOARD

The Knowledge Dashboard is a dedicated surface accessible from the main ACMS interface. It's NOT a settings page or an admin panel — it's a **cognitive workspace** where the user reviews, confirms, and explores what the system knows.

---

### 2.1 Preflight Knowledge Check → Knowledge Coverage Map

**Backend:** KnowledgePreflight categorizes queries as LIKELY/UNLIKELY/UNCERTAIN based on Bloom filter and cluster centroid checks.

**UI Manifestation:** The dashboard shows a visual map of the user's knowledge coverage — what topics ACMS has strong knowledge about and where there are gaps.

```
┌─ Knowledge Coverage ─────────────────────────────────┐
│                                                      │
│  ████████████ Kubernetes Security        93% depth   │
│  ██████████   OAuth / Authentication     82% depth   │
│  ████████     Python Development         71% depth   │
│  ██████       Go Microservices           58% depth   │
│  ████         PostgreSQL                 40% depth   │
│  ██           Vector Databases           22% depth   │
│  █            Network Security           11% depth   │
│  ░            Cloud Cost Optimization     3% depth   │
│                                                      │
│  "Depth" = interaction count × salience score        │
│                                                      │
│  ┌ Recently explored ────────────────────────────┐   │
│  │ New: "mTLS" first appeared Feb 7              │   │
│  │ Growing: "ACMS architecture" +5 interactions  │   │
│  │ Dormant: "Docker networking" no activity 30d  │   │
│  └───────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

**Design Details:**
- Horizontal bars with fill proportional to knowledge depth.
- Color gradient: deep blue (strong) → light gray (sparse).
- "Recently explored" section highlights knowledge dynamics — what's new, growing, or dormant.
- Clicking any topic opens a detailed view showing the topic summary (from Knowledge Compaction 3.1), key entities, and the actual interactions that contributed.
- The map updates in near-real-time as new interactions occur.

**Extended Mind Principle:** This is the user's **cognitive map** — a visualization of what they know through ACMS. Just as the hippocampus maintains a spatial map for physical navigation, this coverage map helps the user navigate their own knowledge space. It answers the question "What do I know about X?" before the user even asks.

---

### 2.2 Salience Scoring → Memory Heat Map

**Backend:** SalienceScorer assigns importance scores based on engagement signals, emotional markers, and interaction patterns.

**UI Manifestation:** A temporal heat map showing knowledge activity over time, with intensity proportional to salience.

```
┌─ Memory Activity ─────────────────────────────────────┐
│                                                       │
│  Feb:  ░░▓▓░░░▓░░█░░▓░░░░▓▓░░░░░██▓░░░░           │
│  Jan:  ░░░▓░░░░░░░▓▓░░░██░░░░░░▓░░░░░░░░░          │
│  Dec:  ░▓░░░░░██░░░░░░░▓▓░░░░░░░░░▓░░░░░           │
│                                                       │
│  █ = Breakthrough moment (high salience)              │
│  ▓ = Deep engagement                                  │
│  ░ = Routine interaction                              │
│                                                       │
│  Recent highlights:                                   │
│  █ Feb 7: "Kubernetes RBAC service account auth"      │
│    ↳ 5 follow-ups · 23-min session · code generated   │
│  █ Feb 3: "ACMS knowledge extraction pipeline"        │
│    ↳ 4 follow-ups · positive feedback · breakthrough  │
│  ▓ Jan 28: "Go error handling patterns"               │
│    ↳ 3 follow-ups · code applied                      │
└───────────────────────────────────────────────────────┘
```

**Design Details:**
- GitHub contribution graph style but for knowledge activity.
- Clicking a high-salience cell shows the interaction details and what was consolidated from it.
- "Breakthrough moments" are marked with labels — the system detected these through engagement signals (long session, many follow-ups, explicit positive feedback, excitement markers).
- The user can confirm or dispute salience: "This wasn't actually important" demotes the entry; "This was critical" promotes it. This feeds back into the salience model.

**Extended Mind Principle:** This implements the emotional priority queue visibility. The user can see what the system thinks was important, confirm or correct it, and build confidence that high-value knowledge is being preserved. The confirmation interaction also serves as a rehearsal event — the user re-engages with important knowledge, strengthening consolidation.

---

### 2.3 Co-Retrieval Graph → Knowledge Constellation

**Backend:** CoRetrievalTracker builds a Hebbian association network tracking which knowledge items are retrieved together.

**UI Manifestation:** An interactive node graph showing the user's knowledge as a constellation of connected topics.

```
┌─ Knowledge Constellation ────────────────────────────┐
│                                                      │
│         ┌──────┐                                     │
│    ┌────│ OAuth │────────┐                           │
│    │    └──────┘         │                           │
│    │        │            │                           │
│ ┌──┴──┐  ┌─┴────┐  ┌────┴───┐                      │
│ │ JWT  │  │ RBAC │  │ HTTPS  │                      │
│ └──┬──┘  └──┬───┘  └────────┘                       │
│    │        │                                        │
│    │    ┌───┴─────────┐                              │
│    └────│ Kubernetes   │                             │
│         │ Service Accts│                             │
│         └──────────────┘                             │
│                                                      │
│  Edge thickness = co-retrieval strength              │
│  Node size = interaction count                       │
│  Node color = knowledge depth                        │
│                                                      │
│  ⟐ New connection detected:                          │
│    OAuth ↔ Kubernetes Service Accounts               │
│    (3 co-retrievals in past week)                    │
└──────────────────────────────────────────────────────┘
```

**Design Details:**
- Interactive force-directed graph (d3.js or Three.js for 3D).
- Nodes = topics/entities, sized by interaction count, colored by knowledge depth.
- Edges = co-retrieval associations, thickness proportional to Hebbian strength.
- Hovering a node highlights its direct connections and shows a tooltip with the topic summary.
- Clicking a node opens the topic detail view.
- New connections (formed in the past week) are highlighted with a pulsing animation.
- The graph organizes naturally into clusters — the user can see their knowledge domains emerging organically.
- Zoom and pan controls. Option to switch between 2D and 3D views.

**Extended Mind Principle:** This is the **cognitive topology visualization** referenced in Chapter 3. It gives the user a spatial metaphor for their knowledge — directly paralleling how the hippocampus uses place cells and grid cells for spatial navigation. The user can literally "see" their knowledge and navigate it spatially, which research shows is the most natural retrieval strategy for human cognition.

---

### 2.4 Cross-Validation → Consistency Alerts

**Backend:** CrossValidator detects divergence between ACMS_Raw_v1 and ACMS_Knowledge_v2 representations.

**UI Manifestation:** Alerts in the dashboard when stored knowledge may be inconsistent or outdated.

```
┌─ Knowledge Health ────────────────────────────────────┐
│                                                       │
│  ✓ 847 knowledge entries · 98.2% consistent           │
│                                                       │
│  ⚠ 3 entries need review:                             │
│                                                       │
│  1. "OAuth token expiration" — Raw says 3600s,        │
│     Knowledge says 7200s. Raw is newer (Feb 5).       │
│     [Keep Raw] [Keep Knowledge] [Review Both]         │
│                                                       │
│  2. "Kubernetes 1.28 RBAC changes" — Knowledge        │
│     entry may be outdated (extracted Nov 2025,         │
│     Kubernetes 1.30 released since).                   │
│     [Mark Stale] [Still Valid] [Update]               │
│                                                       │
│  3. Related to your correction on Feb 7 —             │
│     "Session cookie authentication" flagged.           │
│     [Remove] [Keep] [Edit]                            │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Design Details:**
- "Knowledge Health" shows overall consistency score — a trust signal.
- Inconsistent entries are presented as simple resolution cards with clear actions.
- Each card explains *why* the inconsistency was detected and which representation is likely more accurate.
- Resolution actions are one-click: Keep Raw, Keep Knowledge, Mark Stale, Remove.
- Item #3 connects to Propagated Forgetting (1.3) — corrections cascade to related items.
- This is the **human-in-the-loop consolidation** mechanism. The user participates in maintaining knowledge quality, which both improves the system and strengthens their cognitive ownership.

**Extended Mind Principle:** This implements the "trust is earned" principle. By showing the user that the system actively monitors its own consistency and invites correction, it builds the kind of calibrated trust that moves ACMS from tool to cognitive extension. The transparency of error detection is itself a trust-building mechanism.

---

## TIER 3 UI: ADVANCED COGNITIVE SURFACES

---

### 3.1 Knowledge Compaction → Topic Deep Dives & Domain Maps

**Backend:** KnowledgeCompactor creates Level 2 (topic summaries) and Level 3 (domain maps) from compacted knowledge entries.

**UI Manifestation:** Rich, navigable views of what ACMS knows about each topic and domain.

**Topic Deep Dive (Level 2):**

```
┌─ OAuth2 — Topic Summary ─────────────────────────────┐
│                                                       │
│  Knowledge depth: ████████████ 82% (15 interactions)  │
│  Last active: Feb 7, 2026                             │
│  Consolidation: 3 compactions                         │
│                                                       │
│  What you know:                                       │
│  You've explored authorization code flow, refresh     │
│  token implementation, and service account auth.      │
│  Your primary concern is token lifecycle management   │
│  across Kubernetes environments. You prefer Go        │
│  implementations with concrete code examples.         │
│                                                       │
│  Key concepts:                                        │
│  ● Authorization Code Flow ━━━━━ strong               │
│  ● Refresh Tokens ━━━━━━━━━━━━━━ strong               │
│  ● Service Account Auth ━━━━━━━━ moderate             │
│  ○ PKCE ─────────────────────── gap                   │
│  ○ Token Revocation ─────────── gap                   │
│                                                       │
│  ┌ Knowledge Gaps ───────────────────────────────┐    │
│  │ Based on your knowledge structure, you might   │    │
│  │ benefit from exploring:                        │    │
│  │                                                │    │
│  │ → PKCE (Proof Key for Code Exchange)           │    │
│  │   Why: You use authorization code flow but     │    │
│  │   haven't implemented PKCE, which is now       │    │
│  │   recommended for all OAuth2 clients.          │    │
│  │                                   [Explore →]  │    │
│  │                                                │    │
│  │ → Token Revocation                             │    │
│  │   Why: You manage token lifecycle but haven't  │    │
│  │   addressed revocation — critical for          │    │
│  │   security incident response.                  │    │
│  │                                   [Explore →]  │    │
│  └────────────────────────────────────────────────┘    │
│                                                       │
│  Timeline:                                            │
│  Nov 2025 ── First OAuth2 query (basic flow)          │
│  Dec 2025 ── Refresh token deep dive (4 sessions)     │
│  Jan 2026 ── Service account auth exploration         │
│  Feb 2026 ── Cross-reference with Kubernetes RBAC     │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Domain Map (Level 3):**

```
┌─ API Security — Domain Map ───────────────────────────┐
│                                                       │
│  Your knowledge topology:                             │
│                                                       │
│  ████████████ OAuth2          strong (15 interactions) │
│  ██████████   JWT             strong (12 interactions) │
│  ████████     HTTPS/TLS       moderate (8)            │
│  ████         CORS            developing (4)          │
│  ███          Rate Limiting   developing (3)          │
│  █            API Key Mgmt    minimal (1)             │
│  ░            mTLS            unexplored (0)          │
│                                                       │
│  Cross-topic relationships:                           │
│  OAuth2 ━━━ uses ━━━━━━━━━> JWT                      │
│  JWT ━━━━━━ requires ━━━━━> HTTPS/TLS                │
│  OAuth2 ━━━ recommended ━━> PKCE (gap)               │
│  RBAC ━━━━━ authenticates ━> Service Accounts         │
│                                                       │
│  Emerging theme:                                      │
│  "Token lifecycle management across infrastructure    │
│   layers" — connects OAuth2, JWT, and Kubernetes      │
│   service accounts. This is your frontier.            │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Design Details:**
- Topic summaries read like a knowledgeable colleague summarizing what you've been working on.
- Framed as "what *you* know" not "what the system stored" — the extended mind framing from Chapter 5.
- Knowledge gaps are presented as **suggestions, not deficiencies** — "you might benefit from exploring" not "you're missing knowledge about."
- [Explore →] buttons launch a pre-contextualized query: "Tell me about PKCE in the context of my OAuth2 implementation" — the system already knows the context.
- Timeline view shows the user's learning journey through a topic.
- Domain maps show cross-topic relationships with visual strength indicators.

**Extended Mind Principle:** This is the **consolidation feedback loop** made visible. The user sees not just what they know, but *how their knowledge is structured* — strengths, gaps, connections, trajectory. This meta-cognitive awareness is itself a cognitive enhancement. Research on expertise shows that experts don't just know more facts — they have better *knowledge organization*. This view helps the user develop expert-like knowledge organization.

---

### 3.2 Creative Recombination → Cross-Domain Discoveries

**Backend:** CreativeRecombinator finds unexpected connections between distant topic clusters.

**UI Manifestation:** Discovery cards in the Weekly Digest and Dashboard.

```
┌─ Cross-Domain Discovery ─────────────────────────────┐
│                                                       │
│  ⟐ New Connection Found                               │
│                                                       │
│  Kubernetes Security ↔ Investment Analysis            │
│                                                       │
│  Your Kubernetes RBAC work and your investment        │
│  portfolio analysis share a common pattern:           │
│  role-based access control. RBAC in Kubernetes        │
│  mirrors how you think about risk-tiered access       │
│  in portfolio management — different permission       │
│  levels for different asset classes, with             │
│  inheritance and escalation patterns.                 │
│                                                       │
│  Shared concepts: access control, tiered permissions, │
│  audit logging, principle of least privilege          │
│                                                       │
│  Based on 3 bridging interactions in January.         │
│                                                       │
│  [Interesting — tell me more]  [Not useful — dismiss] │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Design Details:**
- Discovery cards appear in the Weekly Digest and as dashboard highlights.
- Each card explains the connection in natural language — not just "shared entities" but *why* the connection is interesting.
- Binary feedback: "Interesting" or "Not useful." This trains the creative recombination engine over time.
- "Tell me more" launches a conversation about the cross-domain connection, pre-loaded with context from both domains.
- Discoveries are presented as **insights within the user's own knowledge** (Chapter 5 framing): "Your work in X and Y share a pattern" — not "the system found a correlation."
- Limited to 2-3 discoveries per week to avoid noise. Quality over quantity.

**Extended Mind Principle:** This is the **generative memory** made visible. The system is producing knowledge the user didn't explicitly possess — connections that existed in the data but not in conscious awareness. By framing these as discoveries *within* the user's knowledge (not system outputs), the user is more likely to integrate them, satisfying the trust and endorsement conditions for cognitive extension.

---

### 3.3 Schema-Driven Context → Expertise Calibration & Proactive Suggestions

**Backend:** Schema-driven context assembly injects a user cognitive state model into the LLM agent's system prompt.

**UI Manifestation:** Two surfaces — a subtle expertise indicator in the conversation stream, and proactive knowledge gap suggestions.

**Expertise Indicator:**

```
┌─────────────────────────────────────────────────────┐
│  User: How do I implement mTLS between services?     │
│                                                     │
│  ┌ Context ──────────────────────────────────────┐  │
│  │ 🌱 New topic for you · Related to your HTTPS  │  │
│  │    and Kubernetes knowledge                    │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ACMS: [response includes foundational context      │
│  because this is a new topic, but connects to       │
│  the user's existing HTTPS and K8s knowledge]       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  User: How do I handle OAuth2 token rotation in     │
│        a distributed Go service?                     │
│                                                     │
│  ┌ Context ──────────────────────────────────────┐  │
│  │ 🔬 Deep topic · Building on 15 prior sessions │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ACMS: [response skips basics, goes directly to     │
│  advanced implementation patterns, references       │
│  user's specific architecture from past sessions]   │
└─────────────────────────────────────────────────────┘
```

**Proactive Knowledge Gap Suggestions:**

```
┌─────────────────────────────────────────────────────┐
│  [After a response about OAuth2 service accounts]    │
│                                                     │
│  💡 Based on your current exploration, you might     │
│     want to look into PKCE next — it's now          │
│     recommended for the authorization code flow     │
│     you've been implementing.                       │
│                                                     │
│  [Tell me about PKCE]           [Maybe later]       │
└─────────────────────────────────────────────────────┘
```

**Design Details:**
- Expertise indicator uses progressive icons:
  - 🌱 New topic (first encounter)
  - 🌿 Developing (2-8 interactions)
  - 🔬 Deep topic (8+ interactions)
  - 🏗️ Active project (high recent activity)
- The indicator is informational, not decorative — it tells the user "here's why the response is calibrated this way."
- Proactive suggestions appear only when:
  - A genuine knowledge gap has been identified through compaction (3.1)
  - The current conversation context makes the gap relevant
  - The user hasn't dismissed a suggestion about this gap before
- Suggestions are limited to 1 per conversation to avoid being pushy.
- "Maybe later" dismisses the suggestion without penalizing the topic — it may resurface in a future relevant context.
- The system never says "you don't know about X." It says "you might want to explore X." The framing respects the user's autonomy.

**Extended Mind Principle:** This is the **anticipatory coupling** from Chapter 3 — the system surfaces relevant knowledge before the user asks for it. The expertise indicator closes the loop between schema-driven context (which the user can't see) and the user's experience (which they can). It answers the implicit question "Why is this response different?" — because the system knows where you are in your learning journey. The proactive suggestions implement **trajectory prediction** from Chapter 5 — the system estimates what the user needs next based on their knowledge structure.

---

## THE WEEKLY DIGEST

The Weekly Digest is a single, curated summary sent (or displayed) weekly. It synthesizes all the cognitive processes that happened "during sleep" — the consolidation, compaction, cross-validation, and creative recombination that ran in the background.

```
┌─ Weekly Cognitive Digest — Feb 3-9, 2026 ────────────┐
│                                                       │
│  ┌ This Week ────────────────────────────────────┐    │
│  │ 47 interactions · 12 deeply consolidated       │    │
│  │ 3 new topics · 2 topics deepened               │    │
│  │ 1 cross-domain discovery                       │    │
│  └────────────────────────────────────────────────┘    │
│                                                       │
│  ┌ Breakthrough Moments ─────────────────────────┐    │
│  │                                                │    │
│  │ ★ Kubernetes RBAC + Service Accounts (Feb 7)   │    │
│  │   5 follow-ups · 23-min deep session           │    │
│  │   You connected RBAC policies to OAuth2        │    │
│  │   service account authentication — a pattern   │    │
│  │   that bridges your two strongest domains.     │    │
│  │                                                │    │
│  │ ★ ACMS Knowledge Pipeline Architecture (Feb 3) │    │
│  │   Extensive architecture review with code.     │    │
│  │   Consolidated as core ACMS documentation.     │    │
│  │                                                │    │
│  └────────────────────────────────────────────────┘    │
│                                                       │
│  ┌ Knowledge Evolution ──────────────────────────┐    │
│  │                                                │    │
│  │ Growing:                                       │    │
│  │  OAuth2 ████████████ → █████████████ (+8%)     │    │
│  │  Go     ██████ → ████████ (+12%)               │    │
│  │                                                │    │
│  │ New:                                           │    │
│  │  mTLS ░░ (first appearance Feb 7)              │    │
│  │                                                │    │
│  │ Dormant:                                       │    │
│  │  Docker Networking — 30 days since last query  │    │
│  │                                                │    │
│  └────────────────────────────────────────────────┘    │
│                                                       │
│  ┌ Cross-Domain Discovery ───────────────────────┐    │
│  │                                                │    │
│  │ ⟐ Your Kubernetes security work and investment │    │
│  │   analysis share role-based access patterns.   │    │
│  │   [Read more →]                                │    │
│  │                                                │    │
│  └────────────────────────────────────────────────┘    │
│                                                       │
│  ┌ Knowledge Health ─────────────────────────────┐    │
│  │                                                │    │
│  │ ✓ 847 entries · 98.2% consistent               │    │
│  │ ⚠ 3 entries need your review [Review →]        │    │
│  │                                                │    │
│  └────────────────────────────────────────────────┘    │
│                                                       │
│  ┌ Suggested Explorations ───────────────────────┐    │
│  │                                                │    │
│  │ Based on your trajectory this week:            │    │
│  │ → PKCE for OAuth2 (identified gap)             │    │
│  │ → Token Revocation strategies                  │    │
│  │ → Admission Controllers in Kubernetes          │    │
│  │                                                │    │
│  └────────────────────────────────────────────────┘    │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Design Details:**
- Single scrollable view, not a multi-page report.
- Each section is collapsible — power users can scan quickly, detail-oriented users can dig in.
- "Breakthrough Moments" are the high-salience events from the week, framed as the user's achievements.
- "Knowledge Evolution" shows growth, new territory, and dormant areas.
- "Suggested Explorations" come from the knowledge gap analysis in compaction tiers.
- "Knowledge Health" links to the consistency review interface.
- The digest is the user's weekly "knowledge consolidation review" — the human-in-the-loop mechanism for the desirable difficulty principle.
- Tone is collegial and warm, not clinical. "You connected RBAC to OAuth2" — not "System detected topic overlap."

---

## SUMMARY: COGNITIVE PRINCIPLE → BACKEND → UI

| # | Cognitive Principle | Backend Feature | UI Surface | UX Pattern |
|---|---|---|---|---|
| 1.1 | Selective consolidation | ConsolidationTriager | ◆◇○ memory indicators | Ambient status |
| 1.2 | Pattern sep/completion | Adaptive thresholds | Retrieval mode headers | Contextual metadata |
| 1.3 | Active forgetting cascade | Propagated forget | Correction ripple notification | Inline feedback |
| 2.1 | Feeling of knowing | Preflight check | Knowledge coverage map | Dashboard visualization |
| 2.2 | Emotional priority queue | Salience scorer | Memory heat map | Temporal visualization |
| 2.3 | Hebbian co-retrieval | Co-retrieval graph | Knowledge constellation | Interactive graph |
| 2.4 | Error correction | Cross-validator | Consistency alerts | Review cards |
| 3.1 | Memory compaction | Knowledge compactor | Topic deep dives + domain maps | Navigable knowledge |
| 3.2 | REM recombination | Creative recombinator | Cross-domain discovery cards | Insight cards |
| 3.3 | Consolidation feedback loop | Schema-driven context | Expertise indicator + suggestions | Ambient + proactive |
| — | Full consolidation cycle | Intelligence pipeline | Weekly digest | Periodic review |

---

## DESIGN SYSTEM NOTES

**Visual Language:**
- Memory indicators use a consistent diamond/circle iconography
- Knowledge depth uses horizontal bar fills (not pie charts, not percentages)
- Retrieval sources use collapsible headers (information available, not intrusive)
- Discoveries use the ⟐ symbol (connection/bridge metaphor)
- Expertise uses plant/science growth metaphors (🌱🌿🔬🏗️)

**Color Palette:**
- Deep knowledge: warm amber/gold
- New/growing: green spectrum
- Gaps: muted gray with soft border
- Alerts/inconsistencies: warm orange (not red — not an error, just attention needed)
- Cross-domain discoveries: electric blue (unexpected, exciting)

**Typography:**
- Knowledge summaries in the system's voice: clean, readable, slightly warm
- User-facing framing always uses "you/your" — "Your knowledge of OAuth2 is strong"
- Never clinical or database-like — "847 entries at 98.2% consistency" not "Records: 847, Consistency: 0.982"

**Interaction Principles:**
- Every surfaced insight has a binary feedback mechanism (useful/not useful)
- No cognitive signal demands more than 2 seconds of attention unless clicked
- Dashboard is a place you visit intentionally, not a notification center
- Weekly digest is the only push mechanism — everything else is pull
- Override is always available: user can promote, demote, or delete any knowledge item
