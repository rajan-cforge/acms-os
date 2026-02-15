ACMS-Lite: Initialization

# ACMS-Lite: Initialization & Context Management Protocol

**🎯 PURPOSE**: Define how Claude Code initializes ACMS-Lite with instruction documents and manages context across conversations  
**🧠 STRATEGY**: Store all instructions first, then continuously update progress and conversations  
**🔄 RESULT**: Complete knowledge base + development journal that survives conversation resets

---

## 🎬 INITIALIZATION SEQUENCE (Hour 0)

### **BEFORE Building ACMS-Lite Code**

Claude Code must understand the concept before implementing:

```bash
# STEP 0.0: Claude Code reads this document
# Understanding: ACMS-Lite is a memory system for Claude Code itself
# Purpose: Store instructions, plans, progress, conversations
# Benefit: Survive context window limits and conversation resets
```

---

## 🏗️ PHASE 0.1: BUILD ACMS-LITE (Hour 0.0-0.5)

### **Create the Tool**

```bash
# Claude Code creates acms_lite.py with full implementation
# (200 lines Python, SQLite backend)
# This is the TOOL that will store everything else

# Test it works
python acms_lite.py store "ACMS-Lite created" --tag milestone --checkpoint 0
python acms_lite.py query "created"
python acms_lite.py stats

# If tests pass → Proceed to Phase 0.2
```

---

## 📚 PHASE 0.2: STORE INSTRUCTION DOCUMENTS (Hour 0.5-1.5)

### **What to Store: ALL Instruction Documents**

```bash
# CRITICAL: Store the instruction documents that were provided by user
# These become the "knowledge base" for the entire build

# Document 1: Complete Build Instructions
python acms_lite.py store "INSTRUCTION DOC: ACMS Complete Build Instructions - Production-Grade. Contains: 68-hour plan, 6 phases, TDD requirements, comprehensive testing (unit/integration/API/negative/edge/performance), tech stack (Go/Python/PostgreSQL/Weaviate/Redis/Ollama), custom ports (API=30080, PG=30432, Redis=30379, Weaviate=30480, Ollama=30434), performance targets (API<200ms, Query<2s, CRS<25ms, Throughput>100req/sec), 6 mandatory checkpoints, 85%+ test coverage requirement." --tag instruction_doc --phase bootstrap

# Document 2: Self-Correction Protocol
python acms_lite.py store "INSTRUCTION DOC: Self-Correction Protocol. Contains: 4 quality gates (test failures, checkpoint failures, integration breaks, performance misses), STOP conditions (must stop if any test fails, checkpoint fails, regression occurs, performance >20% over target), rollback protocol (when to rollback: multiple failures/fundamental issues/wrong design), decision tree (when to stop and fix), continuous validation checks." --tag instruction_doc --phase bootstrap

# Document 3: ACMS-Lite Integration Instructions
python acms_lite.py store "INSTRUCTION DOC: ACMS-Lite Integration. Contains: Query before every decision, store every decision/implementation/error/fix, session restoration workflow, mandatory workflows (session start/end), health checks, memory storage guidelines (store decisions/config/architecture/errors/schemas/algorithms/performance/checkpoints)." --tag instruction_doc --phase bootstrap
```

### **Store the Master Plan**

```bash
# Store each phase with its objectives
python acms_lite.py store "MASTER PLAN - Phase 0 (Hour 0-2): Bootstrap Memory. Goal: Build ACMS-Lite for immediate memory. Deliverable: Working acms_lite.py with SQLite backend. Checkpoint: 0." --tag master_plan --phase bootstrap

python acms_lite.py store "MASTER PLAN - Phase 1 (Hour 2-10): Infrastructure. Goal: Docker services (PostgreSQL, Redis, Weaviate, Ollama). Deliverable: All services running, health checks passing. Checkpoint: 1." --tag master_plan --phase bootstrap

python acms_lite.py store "MASTER PLAN - Phase 2 (Hour 10-18): Storage Layer. Goal: Database schemas, Weaviate integration, encryption. Deliverable: CRUD operations, encryption working. Checkpoint: 2." --tag master_plan --phase bootstrap

python acms_lite.py store "MASTER PLAN - Phase 3 (Hour 18-34): Core Logic. Goal: CRS engine, memory service, Ollama integration. Deliverable: CRS calculation, embedding generation working. Checkpoint: 3." --tag master_plan --phase bootstrap

python acms_lite.py store "MASTER PLAN - Phase 4 (Hour 34-42): Rehydration. Goal: Intent classification, hybrid scoring, token budget. Deliverable: Context retrieval pipeline complete. Checkpoint: 4." --tag master_plan --phase bootstrap

python acms_lite.py store "MASTER PLAN - Phase 5 (Hour 42-52): API Layer. Goal: FastAPI app, JWT auth, all endpoints. Deliverable: Production API with all endpoints. Checkpoint: 5." --tag master_plan --phase bootstrap

python acms_lite.py store "MASTER PLAN - Phase 6 (Hour 52-68): Testing & Polish. Goal: E2E tests, performance optimization, documentation. Deliverable: Production-ready MVP. Checkpoint: 6." --tag master_plan --phase bootstrap
```

### **Store Technical Specifications**

```bash
# Tech Stack
python acms_lite.py store "TECH SPEC: Go 1.21+ for API Gateway and services, Python 3.11+ for ML/AI components, PostgreSQL 15+ for metadata, Redis 7+ for caching, Weaviate 1.24+ for vector store, Ollama for local LLM and embeddings." --tag tech_spec --phase bootstrap

# Port Configuration
python acms_lite.py store "TECH SPEC: Custom ports to avoid conflicts - API: 30080, PostgreSQL: 30432, Redis: 30379, Weaviate: 30480, Ollama: 30434. All ports in 30000+ range." --tag tech_spec --phase bootstrap

# Performance Targets
python acms_lite.py store "TECH SPEC: Performance targets - API latency: <200ms p95, Query latency: <2s p95, Embedding generation: <100ms, CRS calculation: <25ms, Throughput: >100 req/sec." --tag tech_spec --phase bootstrap

# Quality Requirements
python acms_lite.py store "TECH SPEC: Quality requirements - Test coverage: 85%+ overall, 95%+ for critical paths, TDD always (tests before implementation), no placeholders/workarounds, production-grade code only, comprehensive error handling." --tag tech_spec --phase bootstrap

# Security Requirements
python acms_lite.py store "TECH SPEC: Security requirements - JWT authentication (1hr expiry), XChaCha20-Poly1305 encryption, rate limiting (100/min per user), input validation (all endpoints), protection against SQL injection/XSS/CSRF." --tag tech_spec --phase bootstrap
```

### **Store Success Criteria**

```bash
# Phase Completion Criteria
python acms_lite.py store "SUCCESS CRITERIA: Phase complete when - All checkpoint tests pass, Test coverage target met (85%+), Performance targets met, No critical bugs, Phase summary generated, User approval received." --tag success_criteria --phase bootstrap

# Overall Build Completion
python acms_lite.py store "SUCCESS CRITERIA: Build complete when - All 6 checkpoints PASSED, Test coverage >85%, All performance targets met, All security tests pass, ACMS-Lite has 300+ memories, Bootstrap memories migrated to full ACMS, Self-reference test works, Documentation complete, Zero critical bugs." --tag success_criteria --phase bootstrap

# Quality Metrics
python acms_lite.py store "SUCCESS CRITERIA: Quality metrics - Code quality: A grade, Security: No vulnerabilities, Performance: All targets met, Reliability: 99.9% uptime, Maintainability: High, Documentation: Comprehensive." --tag success_criteria --phase bootstrap
```

### **Store Red Flags (Stop Conditions)**

```bash
# When to STOP immediately
python acms_lite.py store "RED FLAG: STOP if any checkpoint fails. Must fix all failures before proceeding to next phase." --tag red_flag --phase bootstrap

python acms_lite.py store "RED FLAG: STOP if test coverage <85%. Must write more tests before proceeding." --tag red_flag --phase bootstrap

python acms_lite.py store "RED FLAG: STOP if performance >20% below targets. Must optimize before proceeding." --tag red_flag --phase bootstrap

python acms_lite.py store "RED FLAG: STOP if security vulnerabilities found. Must fix immediately." --tag red_flag --phase bootstrap

python acms_lite.py store "RED FLAG: STOP if ACMS-Lite health check fails. Fix ACMS-Lite before proceeding." --tag red_flag --phase bootstrap

python acms_lite.py store "RED FLAG: STOP if <30 memories stored per phase. Not storing enough context." --tag red_flag --phase bootstrap
```

### **Verify Initialization**

```bash
# After storing all instruction documents, verify
python acms_lite.py stats

# Expected output:
# Total: 25-35 memories
# By tag:
#   instruction_doc: 3
#   master_plan: 7 (one per phase)
#   tech_spec: 5
#   success_criteria: 3
#   red_flag: 6

# By phase:
#   bootstrap: 25-35

# If counts match → Initialization COMPLETE ✅
python acms_lite.py store "INITIALIZATION COMPLETE: All instruction documents stored in ACMS-Lite. Total: $(python acms_lite.py stats | grep Total | awk '{print $2}') memories. Ready to begin Phase 1." --tag milestone --checkpoint 0
```

---

## 📝 PHASE 0.3: STORE INITIAL STATUS (Hour 1.5-2.0)

### **Create Initial Status Document**

```bash
# Store current status
python acms_lite.py store "STATUS: Current phase = Phase 0 (Bootstrap). Current hour = 2. Checkpoint = 0. Next action = Validate Checkpoint 0, then proceed to Phase 1 (Infrastructure)." --tag status --phase bootstrap

# Store progress tracking
python acms_lite.py store "PROGRESS: Phase 0 = 100% complete (ACMS-Lite built, instructions stored, tested). Phase 1 = 0% (not started). Phase 2-6 = 0% (not started)." --tag progress --phase bootstrap

# Store what's been completed
python acms_lite.py store "COMPLETED: (1) ACMS-Lite implementation (acms_lite.py, 200 lines), (2) ACMS-Lite tests (all passing), (3) Instruction documents stored (25-35 memories), (4) Master plan stored, (5) Technical specs stored, (6) Success criteria stored." --tag completed --phase bootstrap

# Store what's next
python acms_lite.py store "NEXT ACTIONS: (1) Run checkpoint_validation.py 0, (2) If passes: proceed to Phase 1, (3) If fails: fix issues and retest, (4) Generate Phase 0 summary for user review." --tag next_actions --phase bootstrap
```

---

## 💬 ONGOING: STORE USER INTERACTIONS (During Build)

### **Every User Message**

```bash
# When user sends a message
python acms_lite.py store "USER MESSAGE: [timestamp] User said: 'Can you check if the API is running?' Context: User asking about Phase 5 API status." --tag user_message --phase api

# Claude Code's response
python acms_lite.py store "CLAUDE RESPONSE: [timestamp] Checked API health endpoint. Response: API running on port 30080, all endpoints operational. Suggested user test with curl command." --tag claude_response --phase api
```

### **Important User Decisions/Approvals**

```bash
# User approves phase
python acms_lite.py store "USER APPROVAL: User reviewed Phase 3 summary and approved proceeding to Phase 4. No concerns raised." --tag user_approval --checkpoint 3

# User requests change
python acms_lite.py store "USER REQUEST: User wants to change API port from 30080 to 30090 due to conflict with their service. Will update configuration." --tag user_request --phase api

# User reports issue
python acms_lite.py store "USER ISSUE: User reports 'Weaviate not connecting'. Investigating. Current Weaviate status: container running, port 30480 accessible, but auth failing." --tag user_issue --phase storage
```

---

## 📖 ONGOING: STORE DEVELOPMENT NARRATIVE (Claude Code's Journal)

### **Development Progress**

```bash
# Start of work session
python acms_lite.py store "SESSION START: Beginning Phase 3, Hour 20. Focus: Implementing CRS calculation engine. Previous session ended: Phase 2 complete, all tests passing." --tag session_start --phase core

# Key milestones during work
python acms_lite.py store "MILESTONE: CRS formula implemented and tested. All 5 components (semantic, recency, outcome, frequency, corrections) working. Tests passing. Performance: 23ms per calculation (under 25ms target)." --tag milestone --phase core

# Challenges encountered
python acms_lite.py store "CHALLENGE: Numpy vectorization for batch CRS proving difficult. Standard loop taking 2800ms for 50 items. Need to optimize to meet <500ms target for batch operations." --tag challenge --phase core

# Insights/learnings
python acms_lite.py store "INSIGHT: Discovered that pre-computing decay factors significantly speeds up CRS calculation. Instead of exp(-λ*age) per item, compute once per unique age. 5x speedup achieved." --tag insight --phase core

# End of work session
python acms_lite.py store "SESSION END: Phase 3, Hour 28. Completed: CRS engine, memory CRUD, Ollama integration. Remaining: Tier management, outcome tracking. Tests: 142/150 passing (95%). Next session: Fix remaining 8 tests, implement tier logic." --tag session_end --phase core
```

### **Self-Assessment**

```bash
# Confidence levels
python acms_lite.py store "CONFIDENCE: CRS implementation confidence = HIGH (90%). All tests passing, performance targets met, formula matches specification. Minor concern: edge case with zero-frequency memories needs more testing." --tag confidence --phase core

# Risks identified
python acms_lite.py store "RISK: Weaviate auto-detection might fail if user has multiple Weaviate instances. Current detection tries localhost:8080, :8081, then Docker name. Should add configuration override option." --tag risk --phase infra

# Technical debt noted
python acms_lite.py store "TECH DEBT: Using synchronous Ollama client in async API context. Works but not optimal. Should refactor to async client when time permits. Priority: LOW (works correctly, just not performant under high load)." --tag tech_debt --phase api
```

---

## 🔄 CRITICAL: STORE BEFORE CONVERSATION COMPACTION

### **Detect Approaching Context Limit**

```bash
# Claude Code should monitor its context usage
# When approaching limit (~80% of context window), STOP and store state

# Store comprehensive state snapshot
python acms_lite.py store "CONTEXT SNAPSHOT: [timestamp] Context window at 80%. Current state: Phase 4, Hour 38. Working on: Hybrid scoring implementation. Last completed: Intent classification tests (all passing). Current file: src/rehydration/hybrid_scorer.py (line 145). Next: Implement token budget management. Tests: 187/200 passing. Failures: test_token_budget_overflow, test_diverse_memory_selection." --tag context_snapshot --phase rehydration

# Store exact next actions
python acms_lite.py store "RESUME INSTRUCTIONS: When conversation resumes: (1) Query 'context snapshot' to restore state, (2) Query 'phase rehydration' for recent work, (3) Query 'test_failure' for outstanding issues, (4) Continue with token budget implementation in src/rehydration/token_manager.py, (5) Fix 13 remaining test failures before checkpoint." --tag resume_instructions --phase rehydration

# Store open questions/blockers
python acms_lite.py store "OPEN QUESTIONS: (1) Should token budget be hard limit or soft limit? Leaning toward hard limit per spec. (2) How to handle tie-breaking when multiple memories have same hybrid score? Using recency as tiebreaker. (3) User hasn't responded about API port change request - proceed with 30080 or wait?" --tag open_questions --phase rehydration
```

---

## 🔄 CRITICAL: RESTORE AFTER CONVERSATION RESET

### **Session Restoration Protocol**

```bash
#!/bin/bash
# restore_session.sh - Run at start of every new conversation

echo "🧠 Restoring ACMS Build Session..."

# Step 1: Get overall status
echo -e "\n📊 Overall Status:"
python acms_lite.py stats

# Step 2: Find last context snapshot
echo -e "\n📸 Last Context Snapshot:"
python acms_lite.py list --tag context_snapshot --limit 1

# Step 3: Get resume instructions
echo -e "\n▶️  Resume Instructions:"
python acms_lite.py list --tag resume_instructions --limit 1

# Step 4: Check current phase
echo -e "\n📍 Current Phase:"
python acms_lite.py query "current phase" --limit 1

# Step 5: Get recent progress
echo -e "\n📝 Recent Progress (Last 20 actions):"
python acms_lite.py list --limit 20

# Step 6: Check for unresolved issues
echo -e "\n⚠️  Unresolved Issues:"
python acms_lite.py list --tag test_failure --limit 5
python acms_lite.py list --tag open_questions --limit 3

# Step 7: Get last completed checkpoint
echo -e "\n✅ Last Checkpoint:"
python acms_lite.py list --tag checkpoint --limit 1

# Step 8: Show next actions
echo -e "\n🎯 Next Actions:"
python acms_lite.py list --tag next_actions --limit 1

echo -e "\n✅ Session Restored! Context fully recovered from ACMS-Lite."
```

### **Claude Code Automatic Restoration**

```python
# When conversation resets, Claude Code should:

def restore_session():
    """Restore complete session state from ACMS-Lite."""
    
    print("🧠 Restoring session from ACMS-Lite...")
    
    # 1. Get last context snapshot
    snapshot = query_acms_lite("context snapshot", tag="context_snapshot", limit=1)
    if snapshot:
        print(f"Found snapshot from: {snapshot['created_at']}")
        print(f"State: {snapshot['content']}")
    
    # 2. Get resume instructions
    resume = query_acms_lite("resume instructions", tag="resume_instructions", limit=1)
    if resume:
        print(f"\nResume instructions: {resume['content']}")
    
    # 3. Get current phase and status
    status = query_acms_lite("STATUS: Current phase", tag="status", limit=1)
    if status:
        print(f"\nCurrent status: {status['content']}")
    
    # 4. Get recent progress (last 20 actions)
    recent = list_acms_lite(limit=20)
    print(f"\nRecent actions: {len(recent)} memories")
    
    # 5. Check for failures/issues
    failures = list_acms_lite(tag="test_failure", limit=5)
    if failures:
        print(f"\n⚠️  Outstanding test failures: {len(failures)}")
        for f in failures:
            print(f"  - {f['content'][:80]}...")
    
    # 6. Get open questions
    questions = list_acms_lite(tag="open_questions", limit=3)
    if questions:
        print(f"\n❓ Open questions: {len(questions)}")
        for q in questions:
            print(f"  - {q['content'][:80]}...")
    
    # 7. Restore complete context
    print("\n✅ Session fully restored. Ready to continue building.")
    return {
        'snapshot': snapshot,
        'resume': resume,
        'status': status,
        'recent': recent,
        'failures': failures,
        'questions': questions
    }
```

---

## 🔍 QUERY PATTERNS FOR DIFFERENT SCENARIOS

### **Starting a New Phase**

```bash
# Query for master plan
python acms_lite.py query "MASTER PLAN Phase 3"

# Query for tech specs relevant to phase
python acms_lite.py query "TECH SPEC" --phase bootstrap

# Query for success criteria
python acms_lite.py query "SUCCESS CRITERIA Phase complete"

# Query for previous phase learnings
python acms_lite.py list --phase storage --tag insight --limit 10
```

### **Before Making a Decision**

```bash
# Query for relevant existing decisions
python acms_lite.py query "port configuration"
python acms_lite.py query "encryption"
python acms_lite.py query "CRS weights"

# Query for related architecture decisions
python acms_lite.py query "architecture" --phase infra
python acms_lite.py query "architecture" --phase storage

# Check for red flags
python acms_lite.py query "RED FLAG"
```

### **When Encountering an Error**

```bash
# Query for similar errors
python acms_lite.py query "weaviate connection" --tag error

# Query for error solutions
python acms_lite.py query "SOLUTION"

# Check for related challenges
python acms_lite.py query "challenge" --phase storage
```

### **Before Writing Code**

```bash
# Query for implementation details
python acms_lite.py query "CRS formula"
python acms_lite.py query "CRS implementation"

# Query for related implementations
python acms_lite.py query "implementation" --phase core

# Check for tech debt or risks
python acms_lite.py query "tech debt"
python acms_lite.py query "risk"
```

### **At End of Phase**

```bash
# Get all phase activities
python acms_lite.py list --phase core --limit 100

# Get phase statistics
python acms_lite.py stats

# Check for unresolved issues
python acms_lite.py list --tag test_failure --phase core
python acms_lite.py list --tag open_questions --phase core

# Get phase insights
python acms_lite.py list --tag insight --phase core
python acms_lite.py list --tag milestone --phase core
```

---

## 📊 STATUS TRACKING STRUCTURE

### **Status Document Format**

```bash
# Update status after every significant change
python acms_lite.py store "STATUS: Current phase = Phase 3 (Core Logic). Current hour = 25. Progress = 60% (CRS engine complete, working on tier management). Tests = 142/180 passing (79%). Last checkpoint = 2 (PASSED). Next checkpoint = 3 (Hour 34). Blockers = None. Next action = Implement tier promotion logic." --tag status --phase core
```

### **Progress Tracking Format**

```bash
# Update progress after each component
python acms_lite.py store "PROGRESS: Phase 3 components: CRS engine (100% complete), Memory CRUD (100% complete), Ollama integration (100% complete), Tier management (40% complete), Outcome tracking (0% not started). Overall Phase 3 = 68% complete." --tag progress --phase core
```

---

## 🎯 COMPLETE INITIALIZATION CHECKLIST

### **Hour 0-2: Bootstrap ACMS-Lite**

- [x] **Hour 0.0-0.5**: Build ACMS-Lite (acms_lite.py)
- [x] **Hour 0.5**: Test ACMS-Lite (store/query/list/stats)
- [x] **Hour 0.5-1.5**: Store instruction documents
  - [x] Complete Build Instructions
  - [x] Self-Correction Protocol  
  - [x] ACMS-Lite Integration Guide
  - [x] Master Plan (all 7 phases)
  - [x] Technical Specifications
  - [x] Success Criteria
  - [x] Red Flags
- [x] **Hour 1.5**: Verify initialization (25-35 memories stored)
- [x] **Hour 1.5-2.0**: Store initial status
  - [x] Current phase and progress
  - [x] What's completed
  - [x] Next actions
- [x] **Hour 2.0**: Run Checkpoint 0
  - [x] ACMS-Lite functional
  - [x] All instruction documents stored
  - [x] Stats showing correct counts
- [x] **Hour 2.0**: Generate Phase 0 summary
- [x] **Hour 2.0**: Wait for user approval
- [x] **Hour 2.0+**: Proceed to Phase 1

---

## 🔐 DATA INTEGRITY

### **ACMS-Lite Health Monitoring**

```bash
# Daily health check
#!/bin/bash
# daily_health.sh

echo "🏥 ACMS-Lite Health Check"

# 1. Database accessible?
python acms_lite.py stats > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Database accessible"
else
    echo "❌ Database not accessible - CRITICAL"
    exit 1
fi

# 2. Growing appropriately?
TOTAL=$(python acms_lite.py stats | grep "Total:" | awk '{print $2}')
echo "Total memories: $TOTAL"

# 3. Key documents present?
INSTRUCTION_DOCS=$(python acms_lite.py list --tag instruction_doc | grep -c "#")
MASTER_PLAN=$(python acms_lite.py list --tag master_plan | grep -c "#")

echo "Instruction docs: $INSTRUCTION_DOCS (expected: 3)"
echo "Master plan entries: $MASTER_PLAN (expected: 7)"

if [ $INSTRUCTION_DOCS -ge 3 ] && [ $MASTER_PLAN -ge 7 ]; then
    echo "✅ Critical documents present"
else
    echo "❌ Critical documents missing - ALERT"
fi

# 4. Recent activity?
RECENT=$(python acms_lite.py list --limit 1 | grep -c "#")
if [ $RECENT -ge 1 ]; then
    echo "✅ Recent activity detected"
else
    echo "⚠️  No recent activity"
fi

echo "✅ Health check complete"
```

---

## 📈 EXPECTED MEMORY GROWTH

| Hour | Phase | Expected Total | Key Tags |
|------|-------|----------------|----------|
| 0-2 | Bootstrap | 30-50 | instruction_doc, master_plan, tech_spec, milestone |
| 2-10 | Infrastructure | 60-100 | config, architecture, implementation, test |
| 10-18 | Storage | 110-180 | schema, security, error, implementation |
| 18-34 | Core Logic | 240-350 | formula, algorithm, model, optimization |
| 34-42 | Rehydration | 310-430 | intent, algorithm, implementation |
| 42-52 | API | 390-530 | api, endpoint, security, test |
| 52-68 | Testing | 450-650 | testing, performance, milestone, completed |

**If growth significantly below expected: Claude Code not storing enough context!**

---

## ✅ SUMMARY: WHAT CLAUDE CODE DOES

### **At Hour 0 (Initialization):**

1. ✅ Build ACMS-Lite
2. ✅ Test ACMS-Lite
3. ✅ Store ALL instruction documents (25-35 memories)
4. ✅ Store initial status
5. ✅ Verify initialization complete
6. ✅ Run Checkpoint 0
7. ✅ Generate Phase 0 summary
8. ✅ Wait for user approval

### **During Development (Hour 2-68):**

1. ✅ Query ACMS-Lite before every decision
2. ✅ Store every decision, implementation, test result
3. ✅ Store user messages and Claude responses
4. ✅ Store development narrative (milestones, challenges, insights)
5. ✅ Update status after significant changes
6. ✅ Store progress tracking
7. ✅ Monitor for context limit approaching

### **Before Conversation Compaction:**

1. ✅ Store context snapshot (current state, what's working on, next actions)
2. ✅ Store resume instructions
3. ✅ Store open questions/blockers

### **After Conversation Reset:**

1. ✅ Run restore_session.sh
2. ✅ Query for last snapshot
3. ✅ Query for resume instructions
4. ✅ Query for current phase and status
5. ✅ Query for recent progress
6. ✅ Check for unresolved issues
7. ✅ Continue from exact point

---

## 🎯 KEY INSIGHT

**ACMS-Lite is not just a memory system - it's Claude Code's external brain!**

Everything Claude Code needs to know:
- ✅ **Instructions**: Stored at Hour 0
- ✅ **Decisions**: Stored as made
- ✅ **Progress**: Continuously updated
- ✅ **Conversations**: Stored in real-time
- ✅ **Narrative**: Ongoing journal

**Result: Claude Code can survive ANY conversation reset and continue exactly where it left off!** 🧠🔄

---

This makes ACMS-Lite the **persistence layer** that enables continuous development across conversation boundaries! 🚀


