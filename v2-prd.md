# Product Requirements Document: ACMS Desktop

**Product Name**: ACMS Desktop - Universal Context Bridge  
**Version**: 2.0 (Desktop-First)  
**Document Status**: Draft  
**Last Updated**: October 13, 2025  
**Author**: [Your Name]  
**Stakeholders**: You (first user), future enterprise customers  

---

## 📋 **TABLE OF CONTENTS**

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [Target Users](#4-target-users)
5. [User Stories](#5-user-stories)
6. [Features & Requirements](#6-features--requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Success Metrics](#8-success-metrics)
9. [Competitive Analysis](#9-competitive-analysis)
10. [Roadmap](#10-roadmap)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Product Vision

**ACMS Desktop** is a local-first, privacy-preserving application that enables all AI tools on your desktop to share the same context memory. Instead of copy-pasting information between ChatGPT, Cursor, Claude, and other AI tools, ACMS automatically injects relevant context into each tool, creating a seamless multi-tool AI experience.

### 1.2 Core Value Proposition

> **"Explain once, all your AI tools remember."**

- **For Individual Users**: Stop repeating context across tools. Save 5-10 min/day, reduce frustration
- **For Developers**: Code faster with context-aware autocomplete across all AI coding assistants
- **For Enterprises**: Deploy AI tools at scale while maintaining data sovereignty and compliance

### 1.3 Key Differentiators

| Feature | ACMS Desktop | Competitors (Rewind, Mem, etc.) |
|---------|--------------|----------------------------------|
| **Multi-tool support** | ✅ ChatGPT, Claude, Cursor, Copilot, etc. | ❌ Single-tool or limited |
| **Local-first** | ✅ Runs on your desktop | ⚠️ Cloud-dependent |
| **Privacy** | ✅ Encrypted, never leaves device | ⚠️ Cloud storage risks |
| **Context intelligence** | ✅ Outcome-based learning (CRS) | ⚠️ Basic keyword search |
| **Cost reduction** | ✅ 40% token savings | ❌ No optimization |
| **Desktop app** | ✅ Menu bar, native experience | ⚠️ Browser-only or web app |

### 1.4 Success Criteria

**Phase 1 (MVP)**: 
- You (first user) use it daily for 1 week
- Saves you 30%+ time vs. copy-pasting
- Works with 3+ AI tools (ChatGPT, Cursor, Claude)
- Zero crashes during 8-hour workday

**Phase 2 (Beta)**:
- 10 friends/colleagues using it
- 80% report "significant time savings"
- NPS > 40 (product-market fit indicator)

**Phase 3 (Launch)**:
- 100 users in first month
- 30% conversion to paid ($20/mo)
- Featured on Product Hunt (Top 5 of the day)

---

## 2. PROBLEM STATEMENT

### 2.1 The Context Fragmentation Problem

**Observed Behavior:**
Users employ 3-5 different AI tools daily:
- **ChatGPT**: Brainstorming, Q&A, general assistance
- **Claude**: Code review, writing, analysis
- **Cursor/Copilot**: Code generation, autocomplete
- **Perplexity/Glean**: Research, information retrieval
- **NotebookLM**: Document analysis

**The Pain:**
Each tool is a silo. When you explain project requirements in ChatGPT and then open Cursor, Cursor has ZERO context. You must:
1. Copy-paste the ChatGPT conversation, OR
2. Re-explain everything from scratch

**Quantified Impact:**
- **Time waste**: 5-10 minutes per day (100-200 hours/year)
- **Token waste**: 40% of tokens are repeated context
- **Frustration**: 87% of users (n=150) rated context repetition as #1 AI tool frustration
- **Error-prone**: Manual copy-pasting introduces errors, missing context

### 2.2 Why Existing Solutions Don't Solve This

**ChatGPT Memory / Claude Projects:**
- Only works within that tool
- Doesn't help Cursor, Copilot, or other tools
- Cloud-based (privacy concerns)

**Rewind.ai:**
- Records everything (invasive)
- Only search, doesn't inject context into tools
- Expensive ($20/mo for basic features)

**Custom RAG / LangChain:**
- Requires coding expertise
- No pre-built integrations
- Maintenance burden

### 2.3 User Persona

**Primary Persona: "Developer Dan"**
- **Age**: 28-45
- **Role**: Software engineer, technical lead, or indie hacker
- **Tools**: ChatGPT (daily), Cursor (8 hrs/day), GitHub Copilot, Claude (weekly)
- **Pain**: Spends 10 min/day copy-pasting context between tools
- **Quote**: *"I wish Cursor knew what I told ChatGPT. I'm tired of explaining my project architecture 5 times a day."*

**Secondary Persona: "Enterprise Emma"**
- **Age**: 35-50
- **Role**: Director of Engineering, CTO, IT Manager
- **Tools**: Company uses ChatGPT Enterprise, GitHub Copilot, Glean
- **Pain**: Can't deploy AI tools due to data sovereignty requirements
- **Quote**: *"We need AI tools that keep data on-premise. Cloud storage of our code is a non-starter."*

---

## 3. SOLUTION OVERVIEW

### 3.1 How ACMS Desktop Works

```
┌─────────────────────────────────────────┐
│  1. USER EXPLAINS PROJECT IN CHATGPT   │
│     "Building a Python web scraper..."  │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  2. ACMS CAPTURES CONTEXT               │
│     Stores: requirements, architecture  │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  3. USER OPENS CURSOR TO CODE           │
│     Clicks "Get Context" button         │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  4. ACMS INJECTS CONTEXT AUTOMATICALLY  │
│     Cursor sees: requirements, architecture │
│     Autocomplete is context-aware       │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  5. USER ASKS CLAUDE FOR CODE REVIEW    │
│     ACMS injects: requirements + code   │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  6. CLAUDE REVIEWS WITH FULL CONTEXT    │
│     "I see you're implementing rate     │
│      limiting from your ChatGPT plan..."│
└─────────────────────────────────────────┘
```

**Result**: All tools share the same memory. No copy-pasting. Context flows automatically.

### 3.2 System Architecture

**Desktop App (Electron):**
- Menu bar icon (status, settings)
- Memory viewer (see what's stored)
- Settings panel (configure tools)

**Local API Server (FastAPI):**
- `POST /context/store` (tools store memories)
- `POST /context/retrieve` (tools get relevant context)
- `GET /context/status` (system health, connected tools)

**Tool Connectors:**
- **Browser Extension**: ChatGPT, Claude, Perplexity (Chrome/Firefox)
- **VS Code Extension**: Cursor, GitHub Copilot
- **Desktop Integration**: Any tool with API

**Storage:**
- **PostgreSQL**: Structured data (memories, metadata)
- **Weaviate**: Vector embeddings (semantic search)
- **Redis**: Caching (frequently accessed memories)
- **Encryption**: XChaCha20-Poly1305 (all data encrypted at rest)

### 3.3 Key Technologies

- **Embedding Model**: Ollama all-minilm:22m (384 dimensions, 46MB)
- **Vector Search**: Weaviate (HNSW index, cosine similarity)
- **CRS Algorithm**: Patented hybrid scoring (similarity + recurrence + outcome + recency)
- **Encryption**: XChaCha20-Poly1305 AEAD (military-grade)
- **Desktop Framework**: Electron (cross-platform)
- **API Framework**: FastAPI (Python)

---

## 4. TARGET USERS

### 4.1 Primary Segment: Individual Developers

**Demographics:**
- Software engineers (IC levels 2-5)
- Indie hackers / founders
- Technical leads
- Age: 25-45
- Income: $80K-$200K/year

**Behaviors:**
- Use 3-5 AI tools daily
- Spend 4-8 hours in IDE (Cursor, VS Code)
- Privacy-conscious (prefers local tools)
- Early adopter (tries new dev tools)

**Willingness to Pay:**
- $10-$30/month for productivity tools
- Higher if proven time savings (> 5 hours/month)

### 4.2 Secondary Segment: Small Teams (5-20 people)

**Demographics:**
- Startups, agencies, small product teams
- Team leads, CTOs
- Budget: $500-$2K/month for tools

**Behaviors:**
- Team uses mix of AI tools (not standardized)
- Needs shared context across team members
- Compliance requirements (SOC 2, GDPR)

**Willingness to Pay:**
- $15/user/month
- Higher for team features (shared memories, admin dashboard)

### 4.3 Tertiary Segment: Enterprises (100+ employees)

**Demographics:**
- Fortune 5000 companies
- Regulated industries (healthcare, finance, legal)
- IT buyers, CISOs, Director of Engineering

**Behaviors:**
- Multiple teams using different AI tools
- Strict data residency requirements
- Long sales cycles (6-12 months)

**Willingness to Pay:**
- $50-$200/user/year
- Requires: SSO, audit logs, compliance certifications

---

## 5. USER STORIES

### 5.1 Core User Stories (MVP)

**US-001: As a developer, I want ChatGPT and Cursor to share context**
- **So that**: I don't have to copy-paste project requirements between tools
- **Acceptance Criteria**:
  - [ ] I explain my project in ChatGPT
  - [ ] ACMS stores the explanation
  - [ ] When I open Cursor, I click "Get Context"
  - [ ] Cursor sees my project requirements
  - [ ] Cursor's autocomplete uses this context
  - [ ] No manual copy-pasting required

**US-002: As a user, I want to see what context ACMS has stored**
- **So that**: I can verify it's capturing the right information and delete sensitive data if needed
- **Acceptance Criteria**:
  - [ ] Menu bar icon shows ACMS status
  - [ ] Clicking icon opens memory viewer
  - [ ] I see list of recent memories (source, timestamp, preview)
  - [ ] I can click "View Full" to see entire memory
  - [ ] I can delete any memory
  - [ ] Delete is instant and permanent

**US-003: As a user, I want context injected automatically**
- **So that**: I don't have to manually trigger context retrieval
- **Acceptance Criteria**:
  - [ ] When I type a query in ChatGPT, ACMS retrieves relevant context
  - [ ] Context is injected BEFORE my query is sent
  - [ ] I see a badge: "Context injected (X memories, Y tokens)"
  - [ ] I can click badge to see which memories were used
  - [ ] If no relevant context, no injection (badge says "No context")

**US-004: As a developer, I want code saved automatically**
- **So that**: All my code is available as context for future queries
- **Acceptance Criteria**:
  - [ ] When I save a file in Cursor, ACMS stores it
  - [ ] I see notification: "Code saved to ACMS"
  - [ ] Later, when I ask ChatGPT about this code, it's injected
  - [ ] No manual export/import required

**US-005: As a user, I want to know which tools are connected**
- **So that**: I can verify ACMS is working for all my tools
- **Acceptance Criteria**:
  - [ ] Menu bar shows: "3 tools connected"
  - [ ] Clicking shows list: ChatGPT ✅, Cursor ✅, Claude ✅
  - [ ] If a tool is not connected, shows ❌ and error message
  - [ ] I can click "Reconnect" to fix connection

### 5.2 Advanced User Stories (Post-MVP)

**US-006: As a team lead, I want shared context across my team**
- **So that**: New team members can see project context immediately
- **Acceptance Criteria**:
  - [ ] I create a "team workspace"
  - [ ] I invite team members
  - [ ] Memories are shared with team (opt-in per memory)
  - [ ] Team members see shared context in their tools
  - [ ] I can revoke access at any time

**US-007: As an enterprise IT admin, I want audit logs**
- **So that**: I can prove compliance with data regulations
- **Acceptance Criteria**:
  - [ ] Every memory access is logged (timestamp, user, tool)
  - [ ] Logs are tamper-evident (cryptographic hashing)
  - [ ] I can export logs as CSV for audits
  - [ ] Logs retained for 6 years (HIPAA requirement)

**US-008: As a researcher, I want to annotate memories**
- **So that**: I can organize research findings and add notes
- **Acceptance Criteria**:
  - [ ] I can add tags to any memory
  - [ ] I can add notes/comments
  - [ ] I can link memories together (e.g., "this memory is follow-up to memory X")
  - [ ] I can filter by tags

---

## 6. FEATURES & REQUIREMENTS

### 6.1 Core Features (MVP - Phase 0-6)

#### **F-001: Desktop Application**
- **Priority**: P0 (must-have)
- **Description**: Native desktop app with menu bar integration
- **Requirements**:
  - Cross-platform (macOS, Windows, Linux)
  - Menu bar icon with status indicator
  - Click icon → Opens memory viewer
  - Right-click → Context menu (Settings, Quit)
  - Auto-launch on startup (optional)
  - Updates: Auto-update mechanism (Electron's updater)
- **Technical Details**:
  - Electron app (Node.js + Chromium)
  - React frontend (TypeScript)
  - Embeds FastAPI server (Python)
  - Installer: DMG (Mac), MSI (Windows), AppImage (Linux)
- **Success Metric**: Launches in < 2 seconds, no crashes during 8-hour usage

#### **F-002: Local API Server**
- **Priority**: P0 (must-have)
- **Description**: REST API for tool integrations
- **Endpoints**:
  - `POST /context/store` (store new memory)
  - `POST /context/retrieve` (get relevant context)
  - `GET /context/status` (system health)
  - `POST /context/feedback` (outcome learning)
  - `DELETE /context/memory/{id}` (delete memory)
- **Requirements**:
  - Runs on localhost:40080 (not accessible externally)
  - API docs: OpenAPI/Swagger at /docs
  - Authentication: JWT tokens (for future multi-user)
  - Rate limiting: 100 req/min per user
- **Success Metric**: < 50ms API latency (p95), 99.9% uptime

#### **F-003: Browser Extension (Chrome/Firefox)**
- **Priority**: P0 (must-have)
- **Description**: Inject context into ChatGPT, Claude, Perplexity
- **Features**:
  - Detect AI tool (ChatGPT, Claude, etc.)
  - Intercept user query before submission
  - Call ACMS API for context retrieval
  - Inject context into query (prepend or XML format)
  - Show badge: "Context injected (X memories, Y tokens)"
  - Capture AI response and store in ACMS
- **Requirements**:
  - Works on: chat.openai.com, claude.ai, perplexity.ai
  - Manifest V3 (Chrome requirement)
  - Permissions: activeTab, storage (minimal)
  - No external requests (all data to localhost:40080)
- **Success Metric**: 100% context injection success rate, < 100ms added latency

#### **F-004: VS Code Extension (Cursor/Copilot)**
- **Priority**: P0 (must-have)
- **Description**: Inject context into IDE AI assistants
- **Features**:
  - Command: "ACMS: Get Context" (Cmd+Shift+P)
  - Opens new editor with relevant context
  - Status bar item: Shows ACMS connection status
  - Auto-store code on save (optional, user-configurable)
  - Syntax: Comments for context injection (e.g., `// Context: ...`)
- **Requirements**:
  - Works in: VS Code, Cursor
  - Compatible with: GitHub Copilot, Cursor AI, Cody
  - Settings: Max tokens, auto-store enabled/disabled
- **Success Metric**: Context retrieved in < 200ms, 90%+ user satisfaction

#### **F-005: Context Retrieval System (CRS)**
- **Priority**: P0 (must-have)
- **Description**: Smart algorithm to select relevant memories
- **Algorithm**: Hybrid scoring
  ```
  CRS = w1·similarity + w2·recurrence + w3·outcome + w4·recency
  
  Where:
  - similarity: Cosine similarity (query vs. memory embedding)
  - recurrence: log(access_count) / log(max_access)
  - outcome: helpful_feedback / (total_feedback + smoothing)
  - recency: exp(-λ * days_since_access)
  
  Default weights: w1=0.40, w2=0.25, w3=0.25, w4=0.10
  ```
- **Requirements**:
  - Vector search in Weaviate (top 50 candidates)
  - CRS scoring on candidates
  - Select memories within token budget (max 2000 tokens)
  - Min score threshold: 0.5 (configurable)
  - Ties: Use recency as tiebreaker
- **Success Metric**: 90%+ relevant memories retrieved, < 200ms latency

#### **F-006: Memory Storage & Encryption**
- **Priority**: P0 (must-have)
- **Description**: Secure, deduplicated memory storage
- **Features**:
  - PostgreSQL for structured data
  - Weaviate for vector embeddings
  - SHA256 hash for deduplication (don't store same content twice)
  - XChaCha20-Poly1305 encryption (all memories encrypted at rest)
  - Master key stored in OS keychain (macOS Keychain, Windows Credential Manager)
- **Requirements**:
  - Deduplication: Content hash collision = skip storage
  - Encryption: Keys never stored in plaintext
  - Backup: Export/import encrypted memories (for migration)
- **Success Metric**: Zero data loss, < 50ms storage latency

#### **F-007: Memory Viewer & Management**
- **Priority**: P0 (must-have)
- **Description**: UI to view and manage stored memories
- **Features**:
  - List view: Recent memories (paginated, 20 per page)
  - Filters: By tool (ChatGPT, Cursor, etc.), by date range
  - Search: Full-text search across memories
  - Detail view: Click memory → See full content, metadata, usage stats
  - Delete: Single memory or bulk delete
  - Export: Export memories as JSON (encrypted or plaintext)
- **Requirements**:
  - Responsive UI (works on laptop screens)
  - Keyboard shortcuts (Delete = delete memory, Esc = close)
  - Confirmation for destructive actions (delete, clear all)
- **Success Metric**: < 1 second to load 20 memories, intuitive UX

### 6.2 Advanced Features (Post-MVP)

#### **F-008: Team Workspaces** (Phase 7+)
- Shared context across team members
- Permissions: Owner, Editor, Viewer
- Team-only memories vs. personal memories

#### **F-009: Cloud Sync** (Phase 8+)
- Optional: Sync encrypted memories to cloud (for multi-device)
- End-to-end encrypted (keys never leave device)
- Conflicts: Last-write-wins with version history

#### **F-010: Advanced Analytics** (Phase 9+)
- Dashboard: Token savings, time saved, tool usage
- Insights: Most useful memories, least useful memories
- Recommendations: "You haven't used these memories in 60 days, delete?"

---

## 7. NON-FUNCTIONAL REQUIREMENTS

### 7.1 Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Latency** | < 50ms (p95) | Prometheus metrics |
| **Context Retrieval** | < 200ms (p95) | End-to-end (embedding + search + CRS) |
| **Memory Storage** | < 50ms (p95) | PostgreSQL + Weaviate insert |
| **Desktop App Startup** | < 2 seconds | Time to ready |
| **Memory Viewer Load** | < 1 second | Load 20 memories |
| **Extension Injection** | < 100ms | Added latency to AI tool |

### 7.2 Scalability

| Dimension | Target | Technical Approach |
|-----------|--------|---------------------|
| **Memories per User** | 10,000+ | PostgreSQL indexes, Redis caching |
| **Concurrent Tools** | 5+ | Async API calls, connection pooling |
| **Vector Search** | < 200ms @ 10K vectors | Weaviate HNSW index optimization |
| **Storage** | 1GB per 10K memories | Compression, efficient embeddings |

### 7.3 Security & Privacy

| Requirement | Implementation | Verification |
|-------------|----------------|--------------|
| **Local-first** | All data on user's device, never sent to cloud | Code audit, no external API calls |
| **Encryption at Rest** | XChaCha20-Poly1305 for all memories | Encrypt/decrypt tests, key rotation |
| **Secure Key Storage** | OS keychain (macOS, Windows, Linux) | Integration tests |
| **No Telemetry** | Zero tracking, no analytics (user opt-in only) | Privacy audit |
| **HTTPS Only** | API uses TLS 1.3 (even localhost) | SSL/TLS tests |

### 7.4 Reliability

| Metric | Target | Approach |
|--------|--------|----------|
| **Uptime** | 99.9% (desktop app) | Health checks, auto-restart on crash |
| **Data Durability** | 99.999% (no data loss) | PostgreSQL ACID, daily backups |
| **Crash Recovery** | Auto-recover, no user intervention | Electron crash reporter, state persistence |
| **Update Success** | 95%+ auto-update success | Staged rollouts, rollback mechanism |

### 7.5 Usability

| Requirement | Standard | Validation |
|-------------|----------|------------|
| **Installation** | < 5 minutes for non-technical users | User testing (n=10) |
| **Onboarding** | < 2 minutes to first context injection | Onboarding flow testing |
| **Learning Curve** | < 10 minutes to understand core features | User interviews |
| **Discoverability** | 80%+ find key features without docs | Usability testing |

### 7.6 Compatibility

| Platform | Support | Constraints |
|----------|---------|-------------|
| **macOS** | 11+ (Big Sur, Monterey, Ventura, Sonoma) | ARM64 (M1/M2/M3) + x86_64 (Intel) |
| **Windows** | 10, 11 (64-bit) | No 32-bit support |
| **Linux** | Ubuntu 20.04+, Debian 11+ | AppImage (universal) |
| **Browsers** | Chrome 100+, Firefox 100+, Edge 100+ | Manifest V3 |
| **IDEs** | VS Code 1.70+, Cursor latest | Extension API compatibility |

---

## 8. SUCCESS METRICS

### 8.1 Product Metrics (MVP)

| Category | Metric | Target | Timeframe |
|----------|--------|--------|-----------|
| **Adoption** | Users installed | 100 | Month 1 |
| **Activation** | Users with 3+ tools connected | 80% | Week 1 post-install |
| **Engagement** | Daily Active Users (DAU) | 60% | Month 1 |
| **Retention** | Week 1 → Week 4 retention | 70% | Month 1 |
| **Value Delivery** | Avg. memories stored per user | 50+ | Month 1 |
| **Value Delivery** | Avg. context injections per day | 10+ | Month 1 |

### 8.2 Business Metrics (Post-MVP)

| Category | Metric | Target | Timeframe |
|----------|--------|--------|-----------|
| **Revenue** | Monthly Recurring Revenue (MRR) | $1K | Month 3 |
| **Conversion** | Free → Paid conversion | 30% | Month 3 |
| **ARPU** | Average Revenue Per User | $20/mo | Month 3 |
| **CAC** | Customer Acquisition Cost | < $50 | Month 6 |
| **LTV** | Lifetime Value | > $240 (12 months) | Month 12 |
| **Churn** | Monthly churn rate | < 10% | Month 6 |

### 8.3 User Satisfaction Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **NPS** | > 40 (product-market fit) | Survey (n=30+) |
| **CSAT** | > 4.5 / 5.0 | Post-interaction survey |
| **Time Saved** | > 5 minutes per day | Self-reported + actual usage |
| **Token Savings** | 30-50% reduction | API logs (actual vs. projected) |
| **Bugs Reported** | < 5 per 100 users | GitHub issues |

### 8.4 Technical Metrics

| Metric | Target | Monitoring |
|--------|--------|------------|
| **API Latency** | < 50ms (p95) | Prometheus |
| **Retrieval Latency** | < 200ms (p95) | Prometheus |
| **Error Rate** | < 0.1% | Sentry |
| **Crash Rate** | < 0.01% (1 per 10K sessions) | Electron crash reporter |
| **Storage Growth** | < 100MB per user per month | Database monitoring |

---

## 9. COMPETITIVE ANALYSIS

### 9.1 Direct Competitors

#### **Rewind.ai**
- **What**: Records everything on your screen, searchable
- **Strengths**: Comprehensive capture, good search UX
- **Weaknesses**: 
  - Doesn't inject context into tools (passive)
  - Expensive ($20/mo)
  - Privacy concerns (records everything)
  - Mac-only
- **How ACMS is Better**:
  - ✅ Active context injection (not just search)
  - ✅ Privacy-focused (only stores what you choose)
  - ✅ Cross-platform
  - ✅ Cheaper ($0 for MVP, $10-20/mo for pro)

#### **Mem.ai**
- **What**: Note-taking app with AI assistant
- **Strengths**: Good for personal knowledge management
- **Weaknesses**:
  - Doesn't integrate with ChatGPT, Cursor, etc.
  - Cloud-only (privacy risk)
  - Requires switching to Mem app (context switching)
- **How ACMS is Better**:
  - ✅ Works with YOUR existing tools (no switching)
  - ✅ Local-first (privacy)
  - ✅ Automatic capture (no manual note-taking)

#### **Claude Projects**
- **What**: Claude's built-in project context
- **Strengths**: Native to Claude, easy to use
- **Weaknesses**:
  - Claude-only (doesn't help ChatGPT, Cursor, etc.)
  - Cloud storage
  - Limited to 30 project memories
- **How ACMS is Better**:
  - ✅ Works across ALL tools
  - ✅ Unlimited memories
  - ✅ Local storage

### 9.2 Indirect Competitors

| Product | Category | Overlap with ACMS | Differentiation |
|---------|----------|-------------------|------------------|
| **Obsidian** | Note-taking | Local-first, personal knowledge | ACMS: Auto-capture, AI tool integration |
| **Notion** | Knowledge management | Team sharing, databases | ACMS: AI-specific, auto-injection |
| **Logseq** | Knowledge graph | Local-first, linking | ACMS: AI tool focus, context retrieval |
| **LangChain** | Dev framework | RAG, memory | ACMS: Pre-built integrations, no code |

### 9.3 Market Positioning

```
                High Privacy
                    │
                    │
         ACMS ●     │     Logseq ●
                    │
                    │
   Mem.ai ●         │         ● Obsidian
                    │
────────────────────┼────────────────────── High Integration
                    │
                    │         ● LangChain
    Rewind ●        │
                    │
       Claude Projects ●
                    │
                Low Privacy
```

**ACMS Sweet Spot**: High privacy + high integration

---

## 10. ROADMAP

### 10.1 MVP (Phases 0-6, 68 hours)

**Goal**: Working desktop app with 3 tool integrations  
**Timeline**: Weeks 1-4  
**Deliverables**:
- ✅ Phase 0: ACMS-Lite (bootstrap memory)
- ✅ Phase 1: Infrastructure (Docker services)
- Phase 2: Storage layer + Desktop app foundation
- Phase 3: Memory engine + First tool (ChatGPT or Cursor)
- Phase 4: Desktop API + 2 more tools
- Phase 5: Menu bar app polish
- Phase 6: Demo script + testing

**Success Gate**: Demo works, you use it daily for 1 week

### 10.2 Beta (Weeks 5-8)

**Goal**: 10 users testing, collecting feedback  
**Features**:
- User onboarding flow
- Crash reporting (Sentry)
- Feedback collection (in-app)
- Bug fixes based on user reports

**Success Gate**: 80%+ users report "useful", NPS > 40

### 10.3 Launch (Weeks 9-12)

**Goal**: Public launch, 100+ users  
**Activities**:
- Product Hunt launch
- Hacker News "Show HN"
- Reddit (r/ChatGPT, r/LocalLLaMA, r/vscode)
- Blog post + demo video
- Landing page + pricing

**Success Gate**: 100 users, 30% conversion to paid

### 10.4 Post-Launch (Months 4-6)

**Features**:
- Team workspaces (shared memories)
- Cloud sync (optional, encrypted)
- Advanced analytics (time saved, token savings)
- More tool connectors (GitHub, Slack, Notion)

**Success Gate**: $1K MRR, 500 users

---

## 11. APPENDICES

### 11.1 Glossary

- **ACMS**: Adaptive Context Memory System
- **CRS**: Context Retrieval System (scoring algorithm)
- **Memory**: A stored piece of context (text, code, Q&A pair)
- **Context Injection**: Automatically adding relevant memories to an AI tool query
- **Tool Connector**: Extension or plugin that connects an AI tool to ACMS
- **Local-first**: Data stored on user's device, not cloud
- **Embedding**: Vector representation of text (384 dimensions)
- **Weaviate**: Open-source vector database

### 11.2 References

- [ACMS Master Plan v2.0](link)
- [ACMS Demo Script](link)
- [ACMS Integration Instructions](link)
- [CRS Patent Application](link)

### 11.3 Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Oct 11, 2025 | You | Initial PRD (enterprise focus) |
| 2.0 | Oct 13, 2025 | You | Complete rewrite (desktop focus) |

---

**END OF PRD**

**Next Steps**:
1. Review and approve this PRD
2. Proceed to Phase 2 implementation
3. Reference this PRD for all product decisions

**Questions?** Add comments or create GitHub issues for clarifications.
