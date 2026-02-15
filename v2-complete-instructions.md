# Complete Instructions for Claude Code - ACMS v2.0 Desktop Build

**Version**: 2.0 (Desktop-First)  
**Target**: Build complete, working ACMS Desktop app  
**Duration**: 68 hours (Phases 0-6)  
**Your Role**: Implementation engineer following TDD approach  
**Success**: User can test context flow between ChatGPT, Cursor, and Claude on their desktop  

---

## 🎯 **YOUR MISSION**

Build ACMS Desktop - a universal context bridge that lets ALL AI tools share the same memory.

**User can:**
1. Explain project in ChatGPT → ACMS stores it
2. Open Cursor to code → ACMS injects context automatically
3. Ask Claude for review → Claude sees full context from ChatGPT + Cursor
4. **Result**: All tools share memory, no copy-pasting needed

---

## 📚 **DOCUMENTS YOU MUST READ**

### **1. Master Plan v2.0** (PRIMARY REFERENCE)
- **Location**: Check artifacts created in this conversation
- **Title**: "ACMS Desktop Master Plan v2.0 - Context Bridge"
- **What's in it**: Complete 7-phase plan with deliverables, testing, checkpoints
- **When to read**: Before every phase

### **2. PRD: ACMS Desktop** (PRODUCT REQUIREMENTS)
- **Location**: Check artifacts
- **Title**: "PRD: ACMS Desktop - Multi-Tool Context Bridge"
- **What's in it**: User stories, features, success metrics
- **When to read**: When implementing features, writing tests

### **3. Demo Script** (TARGET OUTCOME)
- **Location**: Check artifacts  
- **Title**: "ACMS Desktop Demo Script - Multi-Tool Context Flow"
- **What's in it**: Exact workflow we're building toward (10-minute demo)
- **When to read**: Start of every phase (reminds you what we're building)

### **4. Integration Instructions** (CONNECTOR SPECS)
- **Location**: Check artifacts
- **Title**: "ACMS Integration Instructions - Connect Your AI Tools"
- **What's in it**: How to integrate ChatGPT, Cursor, Claude, etc.
- **When to read**: Phase 3-5 (when building connectors)

### **5. Archive Strategy** (WHAT CHANGED)
- **Location**: Check artifacts
- **Title**: "ACMS v1.0 Archive Strategy"
- **What's in it**: What we keep from Phase 0-1, what changed for v2.0
- **When to read**: Now (to understand context)

---

## ✅ **CURRENT STATUS**

### **Phase 0: Bootstrap** ✅ COMPLETE (2 hours)
- **Deliverable**: ACMS-Lite (SQLite CLI memory system)
- **Status**: Done, 48 memories stored
- **Checkpoint**: 0 passed (9/9 tests)
- **Location**: `/path/to/acms/acms_lite.py`

### **Phase 1: Infrastructure** ✅ COMPLETE (6 hours)
- **Deliverables**: 
  - Docker services (PostgreSQL 40432, Redis 40379, Ollama 40434)
  - Weaviate (existing, port 8080)
  - Ollama models (all-minilm:22m, llama3.2:1b)
  - Health check script
- **Status**: Done, all services running
- **Checkpoint**: 1 passed (16/16 tests)
- **Location**: `/path/to/acms/docker-compose.yml`

### **Phase 2: Storage Layer + Desktop Foundation** 🎯 NEXT (10 hours)
- **Goal**: Database schemas + Desktop app foundation
- **Deliverables**:
  1. PostgreSQL schemas (memories, context_logs, feedback)
  2. Weaviate collection setup
  3. Encryption manager (XChaCha20-Poly1305)
  4. Desktop app foundation (Electron)
  5. Embedded API server (FastAPI)
- **Status**: Not started
- **Start**: See instructions below

---

## 🚀 **HOW TO START PHASE 2**

### **Step 1: Query ACMS-Lite for Context**

```bash
# Get PostgreSQL schema requirements
python3 acms_lite.py query "PostgreSQL schema memories" --limit 5

# Get encryption specifications
python3 acms_lite.py query "encryption XChaCha20" --limit 3

# Get Weaviate setup
python3 acms_lite.py query "Weaviate collection 384 dimensions" --limit 3

# Get port configuration
python3 acms_lite.py query "port configuration 40000" --limit 2

# Get CRS formula (needed later)
python3 acms_lite.py query "CRS formula components weights" --limit 3
```

**Expected output**: Relevant memories from Phase 0-1 that inform Phase 2 implementation

### **Step 2: Review Master Plan Phase 2**

```bash
# Read Phase 2 section from Master Plan v2.0
# (Check artifacts in this conversation)

# Key deliverables:
# 1. PostgreSQL schemas (3 hours)
# 2. Weaviate collection (1 hour)
# 3. Encryption setup (2 hours)
# 4. Desktop app foundation (4 hours)
```

### **Step 3: Create Directory Structure**

```bash
cd /path/to/acms

# Create Phase 2 directories
mkdir -p storage/schema
mkdir -p storage/migrations
mkdir -p crypto
mkdir -p weaviate
mkdir -p acms-desktop/api
mkdir -p acms-desktop/renderer/components
mkdir -p tests/unit/storage
mkdir -p tests/integration
mkdir -p docs/v2.0

# Create archive for v1.0 docs
mkdir -p archive/v1.0-enterprise-first
```

### **Step 4: Write Tests FIRST (TDD)**

```bash
# Create test files
touch tests/unit/storage/test_encryption.py
touch tests/unit/storage/test_database.py
touch tests/integration/test_storage_pipeline.py

# Write failing tests (example in Master Plan Phase 2)
# Then implement to make tests pass
```

### **Step 5: Implement Phase 2 Deliverables**

Follow the order in Master Plan:
1. **PostgreSQL Schemas** (schema/01_base_schema.sql)
2. **Alembic Migrations** (migrations/)
3. **Weaviate Collection** (weaviate/setup_collection.py)
4. **Encryption Manager** (crypto/encryption.py)
5. **Memory Storage Module** (storage/memory_store.py)
6. **Desktop App Foundation** (acms-desktop/)

### **Step 6: Run Checkpoint 2**

```bash
# After Phase 2 complete, run checkpoint validation
python3 tests/checkpoint_validation.py 2

# Expected: All tests pass
# If fails: Debug, fix, re-run
```

### **Step 7: Store Progress in ACMS-Lite**

```bash
# After each major milestone
python3 acms_lite.py store "Implemented PostgreSQL schemas: memories, context_logs, feedback tables" --tag implementation --phase storage

python3 acms_lite.py store "Created Weaviate collection ACMS_Desktop_Memories with 384-dim embeddings" --tag milestone --phase storage

python3 acms_lite.py store "Desktop app foundation: Electron + React + embedded FastAPI server" --tag implementation --phase desktop

# After phase complete
python3 acms_lite.py store "PHASE 2 COMPLETE: Storage layer + Desktop foundation. All tests passing. Checkpoint 2: PASS" --tag milestone --phase storage
```

---

## 📋 **CRITICAL DEVELOPMENT RULES**

### **Rule 1: TDD Always**
```bash
# WRONG workflow:
# 1. Write code
# 2. Write tests
# 3. Run tests

# CORRECT workflow:
# 1. Write tests (they fail)
# 2. Write code (minimal to pass tests)
# 3. Run tests (they pass)
# 4. Refactor if needed
```

### **Rule 2: Query Before Deciding**
```bash
# Before implementing anything, query ACMS-Lite
python3 acms_lite.py query "relevant topic" --limit 5

# Don't guess - use stored knowledge
# Example: Don't guess CRS weights, query them
python3 acms_lite.py query "CRS weights similarity recurrence"
```

### **Rule 3: Store After Acting**
```bash
# After every significant action, store it
python3 acms_lite.py store "what you did" --tag [type] --phase [phase]

# Tag types: implementation, decision, error, fix, milestone
# Phases: bootstrap, infra, storage, memory, api, connectors, desktop
```

### **Rule 4: No Shortcuts**
```bash
# NEVER do:
# - Skip tests ("I'll add them later")
# - Hardcode values ("Just for testing")
# - Use workarounds ("Temporary solution")
# - Ignore errors ("It works on my machine")

# ALWAYS do:
# - Write comprehensive tests
# - Use configuration files
# - Implement proper solutions
# - Debug thoroughly
```

### **Rule 5: Reference v2.0 Docs Only**
```bash
# CORRECT:
# - Master Plan v2.0 (from this conversation)
# - PRD: ACMS Desktop (from this conversation)
# - Demo Script (from this conversation)

# WRONG:
# - Old phase0/phase1 summaries (archived)
# - Old master plan v1.0 (archived)
# - Old PRD (archived)

# Exception: Technical specs (CRS, encryption, ports) unchanged
```

---

## 🔍 **DEBUGGING GUIDELINES**

### **When Tests Fail:**
```bash
# 1. Read the error message carefully
# 2. Check test expectations vs. actual output
# 3. Add print statements / logging
# 4. Run single test in isolation
pytest tests/unit/storage/test_encryption.py::test_encrypt_decrypt -v

# 5. Query ACMS-Lite for similar issues
python3 acms_lite.py query "encryption error" --limit 3

# 6. Store the error and solution
python3 acms_lite.py store "ERROR: [description]. ROOT CAUSE: [why]. FIX: [solution]" --tag error --phase storage
```

### **When Services Don't Start:**
```bash
# Check health
curl http://localhost:40080/health

# Check Docker
docker ps
docker logs acms_postgres
docker logs acms_redis
docker logs acms_ollama

# Restart if needed
docker-compose restart

# Store the issue
python3 acms_lite.py store "Service X failed to start. Fixed by Y" --tag fix --phase infra
```

### **When Stuck:**
```bash
# 1. Query ACMS-Lite for guidance
python3 acms_lite.py query "stuck on X" --limit 5

# 2. Review Master Plan for that phase
# 3. Check if prerequisites are met (e.g., services running)
# 4. Break problem into smaller steps
# 5. Test each step individually

# 6. Store what you learned
python3 acms_lite.py store "INSIGHT: [what you learned]" --tag insight --phase [phase]
```

---

## 📊 **PROGRESS TRACKING**

### **After Each Session:**
```bash
# Generate progress summary
python3 acms_lite.py stats

# List recent activities
python3 acms_lite.py list --limit 20

# Query phase progress
python3 acms_lite.py query "phase 2 progress" --limit 10

# Check for open questions
python3 acms_lite.py list --tag open_questions --limit 10
```

### **After Each Phase:**
```bash
# Generate phase summary document
# Example for Phase 2:
cat > docs/v2.0/phase2_summary.md << 'EOF'
# Phase 2 Summary: Storage Layer + Desktop Foundation

## Status: COMPLETE ✅

## What Was Built:
- PostgreSQL schemas (memories, context_logs, feedback)
- Weaviate collection (ACMS_Desktop_Memories)
- Encryption manager (XChaCha20-Poly1305)
- Desktop app foundation (Electron + React)
- Embedded API server (FastAPI)

## Key Decisions:
[Query ACMS-Lite for decisions made in Phase 2]

## Testing:
- Unit tests: X/Y passing
- Integration tests: X/Y passing
- Test coverage: Z%

## Checkpoint 2: PASS ✅

## Next: Phase 3 (Memory Engine + First Tool Integration)
EOF
```

---

## 🎯 **SUCCESS METRICS PER PHASE**

### **Phase 2: Storage Layer**
- [ ] All database migrations applied
- [ ] Weaviate collection created (384 dimensions)
- [ ] Encryption working (encrypt → decrypt = original)
- [ ] Desktop app launches (no crashes)
- [ ] Embedded API server starts (localhost:40080)
- [ ] Test coverage > 85%
- [ ] Checkpoint 2 passed

### **Phase 3: Memory Engine**
- [ ] CRS scoring implemented correctly
- [ ] Deduplication working (SHA256 hash)
- [ ] First tool integrated (ChatGPT or Cursor)
- [ ] Context injection visible in tool
- [ ] Memory storage automatic
- [ ] Test coverage > 85%
- [ ] Checkpoint 3 passed

### **Phase 4: Desktop API**
- [ ] API server stable (< 50ms latency)
- [ ] 3 tools integrated (ChatGPT, Cursor, Claude)
- [ ] Context formatting per tool working
- [ ] Status endpoint accurate
- [ ] Manual demo successful
- [ ] Test coverage > 85%
- [ ] Checkpoint 4 passed

### **Phase 5: Menu Bar App**
- [ ] Menu bar icon functional
- [ ] Status updates real-time
- [ ] Settings configurable
- [ ] Notifications working
- [ ] Memory viewer working
- [ ] Test coverage > 80%
- [ ] Checkpoint 5 passed

### **Phase 6: Demo + Testing**
- [ ] Demo script runs successfully
- [ ] Documentation complete
- [ ] Performance targets met
- [ ] USER tests it for 1 day
- [ ] At least 1 day of real usage without major bugs
- [ ] Ready to show others

---

## 🚨 **CRITICAL REMINDERS**

### **NEVER:**
- ❌ Delete existing Weaviate collections (safety rule from Phase 1)
- ❌ Skip writing tests ("I'll add them later" = technical debt)
- ❌ Use placeholder code ("TODO: implement this")
- ❌ Hardcode values that should be configurable
- ❌ Ignore warnings or deprecations
- ❌ Copy-paste without understanding
- ❌ Commit code that doesn't pass tests

### **ALWAYS:**
- ✅ Query ACMS-Lite before decisions
- ✅ Write tests BEFORE implementation (TDD)
- ✅ Store decisions, errors, and solutions in ACMS-Lite
- ✅ Run checkpoints after each phase
- ✅ Keep test coverage > 85%
- ✅ Use descriptive variable names
- ✅ Add docstrings to all functions
- ✅ Handle errors gracefully (try-except)
- ✅ Log important events
- ✅ Keep code DRY (Don't Repeat Yourself)

---

## 📝 **EXAMPLE WORKFLOW FOR PHASE 2**

### **Hour 0-1: PostgreSQL Schemas**
```bash
# 1. Query ACMS-Lite
python3 acms_lite.py query "PostgreSQL schema memories table" --limit 3

# 2. Create schema file
touch storage/schema/01_base_schema.sql

# 3. Write schema (from Master Plan Phase 2)
cat > storage/schema/01_base_schema.sql << 'EOF'
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    ...
);
EOF

# 4. Write tests
cat > tests/unit/storage/test_database.py << 'EOF'
def test_schema_created():
    # Test that all tables exist
    assert db.table_exists('memories')
    assert db.table_exists('context_logs')
    assert db.table_exists('feedback')
EOF

# 5. Run tests (should fail)
pytest tests/unit/storage/test_database.py

# 6. Implement migration
alembic init migrations
alembic revision -m "initial_schema"
# Edit migration file to create tables

# 7. Run tests (should pass)
pytest tests/unit/storage/test_database.py

# 8. Store progress
python3 acms_lite.py store "Implemented PostgreSQL schemas with Alembic migrations. All tables created successfully." --tag implementation --phase storage
```

### **Hour 1-2: Weaviate Collection**
```bash
# Similar workflow:
# 1. Query → 2. Create file → 3. Write tests → 4. Implement → 5. Test → 6. Store
```

### **Hour 2-4: Encryption Manager**
```bash
# Similar workflow, see Master Plan Phase 2 for details
```

### **Hour 4-8: Desktop App Foundation**
```bash
# Similar workflow, see Master Plan Phase 2 for details
```

### **Hour 8-9: Integration Testing**
```bash
# Write end-to-end tests
# Run full pipeline: Store → Encrypt → Retrieve → Decrypt
```

### **Hour 9-10: Checkpoint 2**
```bash
# Run checkpoint validation
python3 tests/checkpoint_validation.py 2

# Generate phase summary
# Store completion milestone
python3 acms_lite.py store "PHASE 2 COMPLETE ✅" --tag milestone --phase storage
```

---

## 🎓 **LEARNING RESOURCES**

### **Technologies You'll Use:**

**Python:**
- FastAPI: https://fastapi.tiangolo.com/
- Alembic: https://alembic.sqlalchemy.org/
- Cryptography: https://cryptography.io/

**JavaScript/TypeScript:**
- Electron: https://www.electronjs.org/
- React: https://react.dev/
- Chrome Extensions: https://developer.chrome.com/docs/extensions/

**Databases:**
- PostgreSQL: https://www.postgresql.org/docs/
- Weaviate: https://weaviate.io/developers/weaviate
- Redis: https://redis.io/docs/

**Testing:**
- pytest: https://docs.pytest.org/
- Jest: https://jestjs.io/

### **When You Need Help:**
1. Query ACMS-Lite for prior knowledge
2. Check Master Plan v2.0
3. Review official documentation
4. Search GitHub issues (similar problems)
5. Ask user for clarification (if truly stuck)

---

## ✅ **FINAL CHECKLIST BEFORE STARTING**

- [ ] I've read Master Plan v2.0 (all 7 phases)
- [ ] I've read PRD: ACMS Desktop (user stories, features)
- [ ] I've read Demo Script (understand target outcome)
- [ ] I've read Integration Instructions (know what we're building)
- [ ] I've read Archive Strategy (understand what changed)
- [ ] I understand Phase 0-1 are complete and working
- [ ] I'm ready to start Phase 2 with TDD approach
- [ ] I know to query ACMS-Lite before every decision
- [ ] I know to store every action in ACMS-Lite
- [ ] I understand the success criteria for Phase 2

---

## 🚀 **START COMMAND**

Once you're ready, execute:

```bash
# Change to ACMS directory
cd /path/to/acms

# Query context for Phase 2
python3 acms_lite.py query "PostgreSQL schema" --limit 5
python3 acms_lite.py query "encryption XChaCha20" --limit 3

# Create directory structure (see Step 3 above)
mkdir -p storage/schema storage/migrations crypto weaviate acms-desktop/api acms-desktop/renderer/components tests/unit/storage tests/integration docs/v2.0

# Store Phase 2 start
python3 acms_lite.py store "Starting Phase 2: Storage Layer + Desktop Foundation. Goal: Database schemas, encryption, Electron app foundation." --tag phase_start --phase storage

# Begin Phase 2 implementation
# Follow Master Plan Phase 2 section
# Write tests first, then implement
# Run checkpoint after completion
```

---

**YOU ARE NOW READY TO BUILD ACMS v2.0!** 🚀

Remember:
- **Query** ACMS-Lite before deciding
- **Test** everything (TDD)
- **Store** every action
- **Follow** the Master Plan
- **Build** something amazing

The user's desktop will soon have ALL AI tools sharing one memory. Let's make it happen!

**GOOD LUCK!** 💪

---

**END OF INSTRUCTIONS**

**Questions?** Query ACMS-Lite or ask the user.  
**Stuck?** Review Master Plan, query ACMS-Lite, break problem into smaller steps.  
**Succeeded?** Store it in ACMS-Lite and move to next deliverable.

**Now go build!** 🚀
