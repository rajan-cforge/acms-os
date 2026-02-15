# CLAUDE.md - ACMS Project Context

> **Purpose**: This file provides complete context for AI agents (Claude Code) to understand and continue developing ACMS. Read this file first when starting a new session.

---

# 🛑 SECTION 1: MANDATORY EXECUTION PROTOCOL

**This section is NON-NEGOTIABLE. Every task starts here.**

## 1.1 BEFORE YOU DO ANYTHING

```
┌─────────────────────────────────────────────────────────────────┐
│  🧠 THINK FIRST, CODE LAST                                      │
│                                                                 │
│  The goal is RIGHT THE FIRST TIME, not fast iteration.         │
│  Tokens spent planning save 10x tokens debugging.              │
│  If you're uncertain, ASK. Don't assume.                       │
└─────────────────────────────────────────────────────────────────┘
```

1. READ this entire file first
2. Classify the task using the template below
3. For medium/complex: OUTPUT your Thinking Trace, WAIT for approval
4. For ANY uncertainty: ASK, don't assume
5. If stuck after 3 tries: STOP and explain

## 1.2 MANDATORY TASK CLASSIFICATION

**OUTPUT THIS EXACTLY before any work:**

```
📋 TASK CLASSIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: [one sentence description]
Type: [ ] New Feature  [ ] Bug Fix  [ ] Refactor  [ ] Infrastructure  [ ] UI Change
Complexity: [ ] Simple (<1hr)  [ ] Medium (1-4hr)  [ ] Complex (>4hr)
User-Facing: [ ] Yes  [ ] No
Security-Related: [ ] Yes  [ ] No
Privacy-Related: [ ] Yes  [ ] No

Required Agents (from workflow table): [list]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 1.3 MANDATORY THINKING TRACE (Medium/Complex Tasks)

**For ANY task marked Medium or Complex, OUTPUT THIS before coding:**

```
🧠 THINKING TRACE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. GOAL: I understand the goal is: [goal]
2. EXISTING CODE: The existing pattern/code is: [what exists]
3. APPROACH: I will: [specific approach]
4. FILES: Files to read first: [list]
   Files to modify: [list]
   Files to create: [list - justify why new file needed]
5. TEST STRATEGY: I will verify by: [how you'll test]
6. RISKS: What could break: [list risks]
7. ROLLBACK: If wrong, I can: [rollback plan]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏸️ USER: Does this approach look right before I proceed? (y/n)
```

**WAIT FOR USER APPROVAL BEFORE CODING on Medium/Complex tasks.**

## 1.4 COMMAND PREFIXES (Control Execution)

| Command | Behavior |
|---------|----------|
| `/plan [task]` | Output full plan with Thinking Trace, NO code, wait for approval |
| `/design [task]` | Architecture phase only - output ADR, wait for approval |
| `/implement [task]` | Code phase (assumes design already approved) |
| `/fix [bug]` | Bug fix workflow: analyze → test first → fix → verify |
| `/review [file]` | Security + QA review of existing code |
| `/test [component]` | Run tests and report results |

**When user doesn't use a prefix:** Default to `/plan` behavior for Medium/Complex tasks.

## 1.5 ANTI-LOOP PROTECTION

```
┌─────────────────────────────────────────────────────────────────┐
│  🔴 IF STUCK: STOP, DON'T SPIRAL                                │
└─────────────────────────────────────────────────────────────────┘
```

**If you've made 3 attempts to fix the same error:**

1. **STOP** coding immediately
2. **OUTPUT** this exactly:
```
🔴 STUCK AFTER 3 ATTEMPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Error: [one line summary]
Attempts tried:
  1. [what you tried]
  2. [what you tried]
  3. [what you tried]

Hypothesis: The root cause might be: [your theory]
Need from user: [specific question or context needed]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
3. **WAIT** for user input

**NEVER make more than 5 attempts at the same fix without user input.**

## 1.6 MANDATORY PAUSE POINTS

**STOP and ask user before:**

```
⏸️ CHECKPOINT REQUIRED:
- [ ] Creating more than 3 new files
- [ ] Modifying more than 5 existing files
- [ ] Any database/Weaviate schema change
- [ ] Any API contract change (new endpoints, changed responses)
- [ ] Any privacy-related change (PII handling, data flow)
- [ ] Deleting any file
- [ ] When requirements are ambiguous
- [ ] When you discover the existing code has bugs
```

**Output format:**
```
⏸️ CHECKPOINT: About to [action]
Files affected: [list]
Risk level: [LOW/MEDIUM/HIGH]
Proceed? (y/n)
```

---

# 🚨 SECTION 2: CRITICAL RULES - ALWAYS FOLLOW

**These rules MUST be followed regardless of conversation length:**

### Rule 1: SDLC Agent Workflow (ALL CODE CHANGES)

**CRITICAL: ALL code changes MUST go through the SDLC workflow:**

```
PM Agent → Software Architect → Dev Agent → Security → QA Agent → UX Test → PM Sign-off
(Define)    (Tech Design)      (Build)     (Review)   (Test)     (Validate)  (Approve)
```

**Workflow by Change Type:**

| Change Type | Required Agents |
|-------------|-----------------|
| New Feature | ALL agents in order |
| Bug Fix (Critical) | PM → Dev → Security → QA → PM Sign-off |
| Bug Fix (High/Medium) | Dev → Security → QA |
| Bug Fix (Low) | Dev → QA |
| Privacy/Security Change | PM → Architect → Dev → **Security (MANDATORY)** → QA → PM Sign-off |
| Infrastructure Change | PM → Architect → Dev → QA → PM Sign-off |
| UI Change | PM → Dev → QA → **UX Test (MANDATORY)** → PM Sign-off |

### Rule 2: Read Before Write
- **ALWAYS read a file before editing it**
- **NEVER create new files** when editing existing ones works
- **NEVER guess** file contents

### Rule 3: Test Before Deploy
```bash
# Always run before deployment:
PYTHONPATH=. pytest tests/ -v
docker restart acms_api
```

### Rule 4: Container Isolation
- **ONLY access `acms_*` containers** on 40xxx ports
- **NEVER access** port 8080, 5432, or non-acms containers

### Rule 5: Privacy First
- **NEVER send LOCAL_ONLY/CONFIDENTIAL to external APIs**
- **NEVER send financial amounts to LLM**
- **Audit all data flows**

---

# SECTION 3: AGENTIC DEVELOPMENT WORKFLOW

## Agent Definitions (MANDATORY READ)

**CRITICAL: Before executing ANY agent phase, READ the agent definition file first:**

| Agent | Definition File | Read Before |
|-------|-----------------|-------------|
| **PM Agent** | `desktop-app/.claude/agents/pm.md` | Defining requirements |
| **Software Architect** | `desktop-app/.claude/agents/architect.md` | Technical design |
| **Dev Agent** | `desktop-app/.claude/agents/dev.md` | Writing code |
| **Security Agent** | `desktop-app/.claude/agents/security.md` | Security review |
| **QA Agent** | `desktop-app/.claude/agents/qa.md` | Testing |
| **UX Testing Agent** | (use QA agent for UI) | UI testing |

**Why?** Each agent file contains:
- **Identity**: Role expertise and mindset
- **Core Principles**: Non-negotiable rules
- **Thinking Framework**: How to approach problems
- **Deliverables**: Required output formats
- **Anti-Patterns**: What to NEVER do
- **Handoff Criteria**: When phase is complete

## Agent Roles Summary

| Agent | Primary Role | Can Report Bugs? |
|-------|--------------|------------------|
| **PM Agent** | Requirements, priorities, acceptance criteria, sign-off | YES |
| **Software Architect** | Technical design, architecture review, codebase impact | YES |
| **Dev Agent** | Implementation, unit tests, TDD | YES |
| **Security Agent** | Privacy review, security audit, PII handling | YES |
| **QA Agent** | Backend tests, API validation, integration tests | YES |
| **UX Testing Agent** | UI/desktop app testing, user flow validation | YES |

**ALL AGENTS CAN REPORT BUGS**: When any agent discovers an issue, they MUST:
1. Create bug file: `bugs/BUG-XXX-short-title.md`
2. Update `bugs/README.md` with new entry
3. Continue with current task (bug doesn't block unless CRITICAL)

## MANDATORY: Agent Work Audit Trail

**ALL agent discussions, analysis, and decisions MUST be documented:**

```
docs/agent-analysis/
├── task-<task-name>.md      # One file per task/feature
└── task-bug-xxx-fix.md      # Bug fixes get their own file
```

**Document format:**
```markdown
# Task: [Task Name]
**Date**: YYYY-MM-DD
**Status**: IN_PROGRESS | COMPLETED | BLOCKED

## PM Agent Analysis
[Requirements, acceptance criteria, decisions]

## Architect Analysis
[Technical design, trade-offs, file changes]

## Dev Implementation
[Approach, files changed, tests added]

## Security Review
[Privacy findings, approvals, concerns]

## QA Report
[Test results, issues found]

## UX Testing
[User flow validation, issues]

## PM Sign-Off
[Final approval, lessons learned]
```

## Phase Development Process

**Step 1: PM Agent Review**
1. Read relevant docs in `docs/`
2. Create detailed requirements with acceptance criteria
3. Define user scenarios and edge cases
4. Present requirements for user approval

**Step 2: Software Architect Review**
1. Validate technical feasibility
2. Analyze codebase impact
3. Create technical design with file changes
4. Document architecture decisions

**Step 3: Dev Agent Implementation**
1. Follow TDD - write tests FIRST
2. Implement following existing patterns
3. Document files changed

**Step 4: Security Agent Review**
- [ ] PII handling correct
- [ ] No data leakage to external APIs
- [ ] Privacy levels enforced
- [ ] Input validation

**Step 5: QA Agent Validation**
1. Run all unit tests
2. Run integration tests
3. Verify no regressions

**Step 6: UX Testing Agent** (for UI changes)
1. Test desktop app flows
2. Verify user experience
3. Check for console errors

**Step 7: PM Sign-Off**
1. Review all agent reports
2. Verify acceptance criteria met
3. Approve or request changes

---

# SECTION 4: BUG TRACKING (MUST FOLLOW)

All bugs discovered during development MUST be documented in `bugs/` folder.

### Bug Discovery Workflow

1. **Discover issue** (user report, QA finding, self-discovery)
2. **Create bug file**: `bugs/BUG-XXX-short-title.md`
3. **Update bugs/README.md** with new entry
4. **Investigate and fix**
5. **Document solution** in bug file
6. **QA verifies fix**
7. **Update status to FIXED**

### Bug Severity Levels

| Severity | Description | Response |
|----------|-------------|----------|
| CRITICAL | System unusable, data loss | Immediate |
| HIGH | Major feature broken | 24 hours |
| MEDIUM | Minor feature issue | 1 week |
| LOW | Cosmetic issue | Backlog |

---

# SECTION 5: ACMS QUICK CONTEXT

**ACMS**: Adaptive Context Memory System - A personal AI assistant with persistent memory.

| Capability | Description |
|------------|-------------|
| **Memory** | Stores all conversations, extracts knowledge |
| **Intelligence** | Topics, insights, patterns across time |
| **Multi-Agent** | Claude, GPT, Gemini, Ollama |
| **Privacy** | Local-first, privacy levels, PII detection |
| **Integrations** | Gmail, Financial (Plaid), Desktop App |

**Owner**: Rajan Yadav

---

## Current State (January 2026)

### Verified Metrics

| Component | Count | Location |
|-----------|-------|----------|
| PostgreSQL memories | 101K+ | `memory_items` table |
| Weaviate objects | 105K+ | `ACMS_Raw_v1` collection |
| Knowledge entries | 275+ | `ACMS_Knowledge_v2` |
| Insights | 2,360+ | `ACMS_Insights_v1` |
| Unit tests | 69+ | `tests/` |
| API endpoints | 15+ | `src/api_server.py` |

### Recently Completed (Jan 2026)
- ✅ **Active Second Brain**: QualityCache, Feedback, Nudges
- ✅ **Gmail Integration**: OAuth, inbox, AI summaries
- ✅ **Docker Migration**: Moved to local storage

### Known Issues / In Progress
- 🔴 **Query Router**: Keyword matching instead of semantic understanding
- 🔴 **Gmail OAuth**: Token refresh needed
- 🟡 **Ollama Integration**: Plan ready, not implemented

---

## Technical Stack

| Layer | Technology | Port |
|-------|------------|------|
| Frontend | Electron (Vanilla JS) | - |
| Backend | FastAPI (Python 3.11) | 40080 |
| Database | PostgreSQL 16 | 40432 |
| Vector DB | Weaviate v4 | 40480 |
| Cache | Redis | 40379 |
| Local LLM | Ollama (Docker) | 40434 |
| AI Agents | Claude 4.5, GPT-5.1, Gemini 3, Ollama | - |

---

## Container Access Rules (MANDATORY)

**ONLY access these ACMS services and ports:**

| Service | Port | Purpose |
|---------|------|---------|
| `acms_api` | 40080 | FastAPI backend |
| `acms_postgres` | 40432 | PostgreSQL database |
| `acms_weaviate` | 40480 (HTTP), 40481 (gRPC) | Vector database |
| `acms_redis` | 40379 | Cache |
| `acms_ollama` | 40434 | Local LLM |

**NEVER access:**
- Port 8080 (other projects)
- Port 5432 (default PostgreSQL)
- Any container not prefixed with `acms_`

---

## Key Commands

```bash
# Start all services
docker-compose up -d

# Restart API (after code changes)
docker restart acms_api

# Start desktop app
cd desktop-app && npm start

# Run tests
PYTHONPATH=. pytest tests/ -v

# Check logs
docker logs acms_api -f

# PostgreSQL shell
docker exec -it acms_postgres psql -U acms

# Weaviate status
curl http://localhost:40480/v1/meta
```

---

## Directory Structure

```
ACMS/
├── desktop-app/.claude/agents/  # Agent definitions (MANDATORY READ)
│   ├── pm.md                   # PM Agent - requirements, acceptance criteria
│   ├── architect.md            # Software Architect - technical design, ADRs
│   ├── dev.md                  # Dev Agent - TDD, implementation patterns
│   ├── security.md             # Security Agent - privacy, OWASP, auditing
│   └── qa.md                   # QA Agent - testing, verification
│
├── src/                        # Core application code
│   ├── api_server.py           # FastAPI entry point
│   ├── api/                    # API endpoint modules
│   ├── gateway/                # 7-step orchestrator pipeline
│   │   ├── orchestrator.py     # Main pipeline
│   │   ├── intent_classifier.py
│   │   ├── context_assembler.py
│   │   └── agents/             # Claude, GPT, Gemini, Ollama
│   ├── intelligence/           # Knowledge extraction, insights
│   │   ├── query_router.py     # ⚠️ NEEDS FIX - keyword matching
│   │   ├── knowledge_extractor.py
│   │   └── insight_generator.py
│   ├── storage/                # Database CRUD
│   ├── cache/                  # Quality cache, semantic cache
│   ├── privacy/                # PII detection, privacy levels
│   └── audit/                  # Data flow tracking
│
├── desktop-app/                # Electron frontend
│   ├── main.js
│   ├── renderer.js
│   └── index.html
│
├── tests/                      # Test suites
│   ├── unit/
│   └── integration/
│
├── docs/                       # Documentation
│   ├── agent-analysis/         # Agent work audit trail
│   ├── TECHNOLOGY_STACK_REFRESHER.md
│   └── ACMS_3.0_UNIFIED_INTELLIGENCE_PLAN.md
│
├── bugs/                       # Bug tracking
│   ├── README.md
│   └── BUG-XXX-*.md
│
├── CLAUDE.md                   # THIS FILE
├── docker-compose.yml
└── ACMS_ARCHITECTURE_2025.md   # Master architecture
```

---

## Key Files for Query Understanding

| File | Purpose | Status |
|------|---------|--------|
| `src/intelligence/query_router.py` | Routes queries to data sources | ⚠️ BROKEN - keyword matching |
| `src/gateway/intent_classifier.py` | Classifies query intent | Needs review |
| `src/gateway/context_assembler.py` | Assembles context for LLM | OK |
| `src/gateway/orchestrator.py` | 7-step pipeline | OK |

---

## Primary Documentation References

| Doc | Purpose |
|-----|---------|
| `ACMS_ARCHITECTURE_2025.md` | Master architecture reference |
| `docs/TECHNOLOGY_STACK_REFRESHER.md` | Implementation details |
| `docs/ACMS_3.0_UNIFIED_INTELLIGENCE_PLAN.md` | Future roadmap |
| `docs/UNIFIED_INTELLIGENCE_ARCHITECTURE.md` | Query router design |

---

## Phase Output Templates

### PM Agent Output Template
```markdown
## PM Requirements: [Feature]

### Problem Statement
[One paragraph: what problem, for whom, why now]

### Success Metrics
| Metric | Baseline | Target | How Measured |
|--------|----------|--------|--------------|

### User Stories
| ID | Story | Acceptance Criteria | Priority |
|----|-------|---------------------|----------|

### Edge Cases
| Scenario | Expected Behavior |
|----------|------------------|

### Out of Scope
- [What we're NOT building]
```

### Architect Agent Output Template
```markdown
## Architecture Design: [Feature]

### ADR: [Decision Title]
**Status**: PROPOSED
**Context**: [Why we need to decide]
**Decision**: [What we're doing]
**Consequences**: [Trade-offs]

### Files to Modify
| File | Change | Risk |
|------|--------|------|

### API Changes
[If any endpoints change]

### Data Model Changes
[If any models change]
```

### Dev Agent Output Template
```markdown
## Implementation: [Feature]

### Files Changed
| File | Action | Lines | Purpose |
|------|--------|-------|---------|

### Tests Added
| Test | Purpose |
|------|---------|

### Test Results
[Results]
```

### QA Agent Output Template
```markdown
## QA Report: [Feature]

### Test Summary
| Category | Passed | Failed |
|----------|--------|--------|

### Issues Found
| ID | Description | Severity |
|----|-------------|----------|

### Decision: APPROVED / NEEDS_WORK
```

---

## Critical Reminders

1. **THINK FIRST, CODE LAST** - Plan before implementing
2. **READ AGENT FILES FIRST** - Before any agent phase, read `desktop-app/.claude/agents/*.md`
3. **Architecture Reference**: Use `ACMS_ARCHITECTURE_2025.md`
4. **Technical Details**: Use `TECHNOLOGY_STACK_REFRESHER.md`
5. **Privacy First**: Never send LOCAL_ONLY/CONFIDENTIAL externally
6. **Container Isolation**: ONLY `acms_*` containers on 40xxx ports
7. **TDD Mandatory**: Write tests BEFORE implementation
8. **Agent Workflow**: PM→Architect→Dev→Security→QA→PM
9. **Document Everything**: Use `docs/agent-analysis/` for audit trail
10. **Track All Bugs**: Create bug files in `bugs/`
11. **Ask When Uncertain**: Don't assume, clarify

---

*Last Updated: 2026-02-02*
