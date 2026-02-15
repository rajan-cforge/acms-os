# ACMS Build Plan - Memory-First Approach

**🧠 META-RECURSIVE STRATEGY:** Build memory system first, use it to build better memory system

**Timeline:** 68 hours  
**Innovation:** ACMS-Lite provides memory from Hour 0  
**Result:** Full ACMS remembers its own creation

---

## 🎯 THE META-RECURSIVE CONCEPT

```
┌─────────────────────────────────────────────────────────┐
│ Phase 0 (Hour 0-2): Build ACMS-Lite                     │
│ ↓                                                        │
│ Phase 1-6 (Hour 2-68): Build Full ACMS                  │
│   → Claude Code stores ALL context in ACMS-Lite         │
│   → Queries ACMS-Lite before decisions                  │
│   → Never forgets context                               │
│ ↓                                                        │
│ Hour 68: Migrate ACMS-Lite → Full ACMS                  │
│ ↓                                                        │
│ Result: ACMS contains complete memory of its own build! │
└─────────────────────────────────────────────────────────┘
```

**Why This Works:**
- ✅ Memory available from Day 1
- ✅ Zero context loss across sessions
- ✅ Claude Code can query decisions
- ✅ Full build history preserved
- ✅ Dogfooding (using ACMS to build ACMS!)

---

## 📋 REVISED BUILD PHASES

### **PHASE 0: Bootstrap Memory System (Hours 0-2)** ⭐ NEW

**Goal:** Build ACMS-Lite so Claude Code has memory immediately

**Deliverable:** Working `acms_lite.py` script with SQLite backend

**Tasks:**
1. Create `acms_lite.py` (the script I provided earlier)
2. Initialize SQLite database
3. Test store/query/list commands
4. Create workflow commands for Claude Code

**Testing:**
```bash
# Test ACMS-Lite works
python acms_lite.py store "ACMS-Lite initialized successfully" --tag milestone --checkpoint 0
python acms_lite.py query "initialized"
# Should return the stored memory ✅
```

**Checkpoint 0 (Hour 2):**
```bash
# Validate ACMS-Lite
python tests/checkpoint_validation.py 0

# Tests:
✅ acms_lite.py script exists
✅ SQLite database created
✅ Store command works
✅ Query command works
✅ List command works
✅ Stats command works
```

**From this point forward, ALL decisions stored in ACMS-Lite!**

---

### **PHASE 1: Infrastructure (Hours 2-10)** ← Uses ACMS-Lite

**Before starting phase, Claude Code does:**
```bash
# Review what we've done so far
python acms_lite.py list --limit 5

# Check for any prior decisions about infrastructure
python acms_lite.py query "infrastructure decision"
```

**During phase, Claude Code stores:**
```bash
# Store every decision
python acms_lite.py store "Using PostgreSQL on port 30432" --tag config --phase infrastructure
python acms_lite.py store "Redis on port 30379" --tag config --phase infrastructure  
python acms_lite.py store "Ollama on port 30434" --tag config --phase infrastructure
python acms_lite.py store "API will run on port 30080" --tag config --phase infrastructure

# Store architectural decisions
python acms_lite.py store "Decided NOT to use pgvector, using Weaviate instead for existing instance compatibility" --tag architecture --phase infrastructure

# Store Weaviate auto-detection strategy
python acms_lite.py store "Weaviate auto-detection: try localhost:8080, then :8081, then Docker name 'weaviate', then fallback to in-memory" --tag architecture --phase infrastructure
```

**Checkpoint 1 (Hour 10):**
```bash
# Before validation, check what we built
python acms_lite.py list --phase infrastructure

# Store checkpoint results
python tests/checkpoint_validation.py 1
python acms_lite.py store "Checkpoint 1 PASSED: All infrastructure healthy" --tag checkpoint --checkpoint 1
```

---

### **PHASE 2: Storage Layer (Hours 10-18)** ← Uses ACMS-Lite

**Session starts:**
```bash
# Claude Code queries context
python acms_lite.py query "postgres port"  # → 30432
python acms_lite.py query "weaviate detection"  # → Returns detection strategy
python acms_lite.py list --phase infrastructure --limit 10  # Review previous phase
```

**During phase:**
```bash
# Store database schema decisions
python acms_lite.py store "Users table: id, email, password_hash, created_at, updated_at" --tag schema --phase storage

python acms_lite.py store "Memory items ONLY in Weaviate, PostgreSQL stores query logs and outcomes" --tag architecture --phase storage

# Store Weaviate schema
python acms_lite.py store "Weaviate collection: ACMS_MemoryItems_v1 with 384-dim vectors (all-minilm model)" --tag schema --phase storage

# Store encryption decisions  
python acms_lite.py store "Using XChaCha20-Poly1305 for encryption, nonce stored separately in Weaviate" --tag security --phase storage

# Store any errors and resolutions
python acms_lite.py store "ERROR: Weaviate connection failed initially. SOLUTION: Added retry logic with 3 attempts" --tag error --phase storage
```

**Checkpoint 2 (Hour 18):**
```bash
python acms_lite.py store "Checkpoint 2 PASSED: Auth working, database CRUD functional" --tag checkpoint --checkpoint 2
```

---

### **PHASE 3: Core Logic (Hours 18-34)** ← Uses ACMS-Lite

**Session starts:**
```bash
python acms_lite.py query "encryption"  # Check how encryption was implemented
python acms_lite.py query "weaviate schema"  # Review vector store structure
```

**During phase:**
```bash
# CRS formula decisions
python acms_lite.py store "CRS weights: semantic=0.35, recency=0.20, outcome=0.25, frequency=0.10, corrections=0.10" --tag formula --phase core

python acms_lite.py store "CRS decay rate: 0.02 per day (exponential)" --tag formula --phase core

python acms_lite.py store "Tier thresholds: LONG if CRS>0.80 AND age>=7d, MID if CRS>0.65 AND usage>=3, else SHORT" --tag algorithm --phase core

# Ollama model decisions
python acms_lite.py store "Embedding model: all-minilm:22m (384-dim vectors)" --tag model --phase core
python acms_lite.py store "LLM model: llama3.2:1b (smallest, fastest)" --tag model --phase core

# Store any optimizations
python acms_lite.py store "OPTIMIZATION: Batch CRS calculation using numpy vectorization for 10x speedup" --tag performance --phase core
```

**Checkpoint 3 (Hour 34):**
```bash
python acms_lite.py store "Checkpoint 3 PASSED: CRS computation working, memory CRUD functional" --tag checkpoint --checkpoint 3
```

---

### **PHASE 4: Rehydration (Hours 34-42)** ← Uses ACMS-Lite

**Session starts:**
```bash
python acms_lite.py query "CRS formula"  # Review scoring logic
python acms_lite.py query "tier threshold"  # Check tier rules
```

**During phase:**
```bash
# Intent classification decisions
python acms_lite.py store "Intent categories: code_assist, research, meeting_prep, writing, analysis, threat_hunt, general" --tag intent --phase rehydration

# Hybrid scoring
python acms_lite.py store "Hybrid score = 0.5*vector_sim + 0.2*recency + 0.2*outcome + 0.1*CRS (default weights, vary by intent)" --tag algorithm --phase rehydration

# Token budget
python acms_lite.py store "Default token budget: 1000 tokens, reserve 10% for prompt overhead" --tag config --phase rehydration

# Store retrieval strategy
python acms_lite.py store "Retrieval: Weaviate top-50 → CRS filter → Hybrid rank → Token budget select" --tag algorithm --phase rehydration
```

**Checkpoint 4 (Hour 42):**
```bash
python acms_lite.py store "Checkpoint 4 PASSED: Rehydration working, context bundles under token budget" --tag checkpoint --checkpoint 4
```

---

### **PHASE 5: API Layer (Hours 42-52)** ← Uses ACMS-Lite

**Session starts:**
```bash
python acms_lite.py query "port configuration"  # Check all ports
python acms_lite.py query "JWT"  # Check auth decisions
```

**During phase:**
```bash
# API design decisions
python acms_lite.py store "JWT expiry: 1 hour (3600s)" --tag api --phase api
python acms_lite.py store "Rate limit: 100 requests/min per user" --tag api --phase api

# Store all endpoints created
python acms_lite.py store "POST /v1/memory/ingest - creates memory item, auto-generates embedding, returns CRS" --tag endpoint --phase api

# Store any API issues and fixes
python acms_lite.py store "ISSUE: Async/await not working in Ollama client. FIX: Used httpx.AsyncClient properly" --tag error --phase api
```

**Checkpoint 5 (Hour 52):**
```bash
python acms_lite.py store "Checkpoint 5 PASSED: All API endpoints functional" --tag checkpoint --checkpoint 5
```

---

### **PHASE 6: Testing & Polish (Hours 52-68)** ← Uses ACMS-Lite

**During phase:**
```bash
# Store test results
python acms_lite.py store "Test coverage achieved: 82%" --tag testing --phase testing

# Store performance results
python acms_lite.py store "PERFORMANCE: API latency p95=145ms, Rehydration p95=1.8s, CRS computation=23ms" --tag performance --phase testing

# Store any optimizations made
python acms_lite.py store "OPTIMIZATION: Added connection pooling to PostgreSQL, reduced query time by 40%" --tag performance --phase testing
```

**Final Checkpoint (Hour 68):**
```bash
python acms_lite.py store "MILESTONE: ACMS MVP complete, all tests passing" --tag milestone --checkpoint 6

# Get final stats
python acms_lite.py stats
```

---

## 🔄 MIGRATION TO FULL ACMS (Hour 68+)

Once ACMS is built, migrate bootstrap memories:

```bash
# Export from ACMS-Lite
python acms_lite.py export
# Creates: bootstrap_memories.json with ~200-500 memories

# Start ACMS API
uvicorn src.api.main:app --host 0.0.0.0 --port 30080

# Register admin user
curl -X POST http://localhost:30080/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acms.local","password":"admin123"}'

# Login and get token
TOKEN=$(curl -X POST http://localhost:30080/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acms.local","password":"admin123"}' \
  | jq -r '.token')

# Import each memory
cat bootstrap_memories.json | jq -c '.[]' | while read memory; do
  CONTENT=$(echo $memory | jq -r '.content')
  TAG=$(echo $memory | jq -r '.tag')
  
  curl -X POST http://localhost:30080/v1/memory/ingest \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"content\":\"$CONTENT\",\"metadata\":{\"source\":\"bootstrap\",\"tag\":\"$TAG\"}}"
done

echo "✅ Migrated all bootstrap memories to full ACMS"

# Now query full ACMS
curl -X POST http://localhost:30080/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"How was the CRS formula designed?","max_tokens":1000}'

# ACMS returns complete context from its own build process! 🤯
```

---

## 🎯 CLAUDE CODE WORKFLOW INTEGRATION

### **Every Session Starts With:**

```bash
#!/bin/bash
# session_start.sh

echo "🧠 Reviewing ACMS-Lite context..."

# Check current phase
PHASE=$(ls -d src/* 2>/dev/null | wc -l)
if [ $PHASE -eq 0 ]; then
  echo "📍 Phase: Bootstrap (building ACMS-Lite)"
elif [ $PHASE -lt 3 ]; then
  echo "📍 Phase: Infrastructure"
else
  echo "📍 Phase: In progress"
fi

# Show recent memories
echo -e "\n📝 Last 5 memories:"
python acms_lite.py list --limit 5

# Show phase summary
if [ ! -z "$1" ]; then
  echo -e "\n📂 Memories from current phase:"
  python acms_lite.py list --phase "$1" --limit 10
fi

# Show any errors that need attention
echo -e "\n⚠️  Unresolved errors:"
python acms_lite.py list --tag error --limit 3

echo -e "\n✅ Ready to continue building!"
```

### **Before Making ANY Decision:**

```bash
# Query ACMS-Lite first
python acms_lite.py query "relevant keywords"

# If no results, proceed and STORE the decision
# If results found, use that context
```

### **After Implementing Something:**

```bash
# Store what was done
python acms_lite.py store "Implemented X using approach Y because Z" --tag implementation --phase current_phase
```

### **After Fixing An Error:**

```bash
# Store the solution
python acms_lite.py store "ERROR: [description]. SOLUTION: [fix]" --tag error --phase current_phase
```

### **At End of Session:**

```bash
#!/bin/bash
# session_end.sh

echo "💾 Session summary..."

# Show what was done this session
python acms_lite.py list --limit 10

# Show stats
python acms_lite.py stats

echo "✅ Session context preserved in ACMS-Lite"
```

---

## 📊 EXPECTED ACMS-LITE CONTENT BY PHASE

| Phase | Memories Stored | Example Tags |
|-------|-----------------|--------------|
| Phase 0 | 5-10 | milestone, test |
| Phase 1 | 30-50 | config, architecture, decision |
| Phase 2 | 50-80 | schema, security, error |
| Phase 3 | 60-100 | formula, algorithm, model, performance |
| Phase 4 | 40-70 | intent, algorithm, config |
| Phase 5 | 50-80 | api, endpoint, error |
| Phase 6 | 30-60 | testing, performance, milestone |
| **Total** | **265-450** | Complete build history |

---

## 🏆 BENEFITS OF MEMORY-FIRST APPROACH

### **For Claude Code:**
- ✅ **Zero context loss** across sessions
- ✅ **Query before asking** user
- ✅ **Reference past decisions** instantly
- ✅ **Learn from errors** (stored solutions)
- ✅ **Consistent implementation** (check previous patterns)

### **For User:**
- ✅ **Fewer interruptions** (Claude Code self-serves from memory)
- ✅ **Better decisions** (based on complete context)
- ✅ **Audit trail** (see every decision made)
- ✅ **Faster builds** (no repeated work)

### **For ACMS Itself:**
- ✅ **Dogfooding** (using ACMS to build ACMS)
- ✅ **Complete provenance** (knows its own creation story)
- ✅ **Instant onboarding** (new contributors query build history)
- ✅ **Living documentation** (decisions stored as memories)

---

## 🎯 SUCCESS CRITERIA (UPDATED)

ACMS MVP is complete when:

- ✅ **Phase 0:** ACMS-Lite working and tested
- ✅ **Phases 1-6:** All checkpoints passed
- ✅ **ACMS-Lite:** Contains 250+ memories from build process
- ✅ **Migration:** Bootstrap memories imported to full ACMS
- ✅ **Self-reference:** Full ACMS can answer "How was I built?"

---

## 🚀 FINAL BUILD COMMAND

```bash
#!/bin/bash
# start_build.sh

echo "🚀 Starting ACMS Build - Memory-First Approach"
echo "=============================================="
echo ""

# Phase 0: Build ACMS-Lite FIRST
echo "📍 Phase 0: Building bootstrap memory system..."
python acms_lite.py store "ACMS build initiated" --tag milestone

# Initialize ACMS-Lite
python acms_lite.py store "ACMS-Lite provides memory from Hour 0" --tag architecture --phase bootstrap

# Run checkpoint 0
python tests/checkpoint_validation.py 0

# Start main build
echo "✅ ACMS-Lite ready! Proceeding with full ACMS build..."
echo "💡 All decisions will be stored in ACMS-Lite"
echo ""

# Continue with phases 1-6
# (Claude Code now has memory for everything!)
```

---

## 💎 THE META BEAUTY

**At Hour 68, you can ask ACMS:**

```bash
curl -X POST http://localhost:30080/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"Why did we choose XChaCha20-Poly1305 for encryption?"}'

# ACMS responds with its own memory:
# "Decided to use XChaCha20-Poly1305 because it provides authenticated 
#  encryption, is faster than AES-GCM, and has better resistance to 
#  nonce reuse. Stored during Phase 2 (Hour 12) when implementing 
#  encryption module."
```

**🤯 ACMS remembers its own creation!**

---

## ✅ RECOMMENDATION

**YES, build ACMS-Lite first!**

**Why this is genius:**
1. Solves Claude Code's memory problem from Day 1
2. Creates complete audit trail of build
3. Demonstrates ACMS concept immediately
4. Provides migration path to full system
5. Results in self-aware ACMS that knows its own history

**This is not just building ACMS, it's building ACMS using ACMS principles from the start!** 🎯



# ACMS-Lite Integration Instructions for Claude Code

**🎯 GOAL:** Use simple memory system while building advanced memory system  
**💡 BENEFIT:** Immediate validation of ACMS concept + zero context loss  
**📊 OUTCOME:** Full ACMS learns from ACMS-Lite's usage patterns

---

## 🚨 CRITICAL MANDATE FOR CLAUDE CODE

### **YOU MUST:**

1. **Build ACMS-Lite FIRST** (Hour 0-2, before anything else)
2. **Use ACMS-Lite CONSTANTLY** (every session, every decision)
3. **Query before asking user** (check memory first)
4. **Store everything important** (decisions, errors, configs)
5. **Validate at checkpoints** (prove memory works)
6. **Learn from usage** (note what works/doesn't for full ACMS)

### **NEVER:**
- ❌ Skip building ACMS-Lite
- ❌ Forget to query before decisions
- ❌ Ask user for info that's in ACMS-Lite
- ❌ Make decisions without storing them
- ❌ Continue if ACMS-Lite tests fail

---

## 📋 PHASE 0: BUILD ACMS-LITE (Hours 0-2)

### **Step 1: Create acms_lite.py (Hour 0-1)**

Create file `acms_lite.py` with this exact content:

```python
#!/usr/bin/env python3
"""ACMS-Lite: Bootstrap memory for Claude Code during ACMS build."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import hashlib
import argparse
import sys


class ACMSLite:
    """Ultra-simple memory for Claude Code - uses SQLite, no dependencies."""
    
    def __init__(self, db_path: str = ".acms_lite.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create tables if not exist."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_hash TEXT UNIQUE NOT NULL,
                tag TEXT,
                phase TEXT,
                checkpoint INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tag ON memories(tag)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_phase ON memories(phase)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_checkpoint ON memories(checkpoint)")
        conn.commit()
        conn.close()
    
    def store(self, content: str, tag: Optional[str] = None,
              phase: Optional[str] = None, checkpoint: Optional[int] = None) -> int:
        """Store a memory. Returns memory ID."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO memories (content, content_hash, tag, phase, checkpoint)
                VALUES (?, ?, ?, ?, ?)
            """, (content, content_hash, tag, phase, checkpoint))
            conn.commit()
            memory_id = cursor.lastrowid
            print(f"✅ Stored #{memory_id}: {content[:60]}...")
            return memory_id
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM memories WHERE content_hash = ?", (content_hash,))
            memory_id = cursor.fetchone()[0]
            print(f"ℹ️  Already exists: #{memory_id}")
            return memory_id
        finally:
            conn.close()
    
    def query(self, search_term: str, tag: Optional[str] = None,
              phase: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Query memories by keyword search."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        where_clauses = ["content LIKE ?"]
        params = [f"%{search_term}%"]
        
        if tag:
            where_clauses.append("tag = ?")
            params.append(tag)
        if phase:
            where_clauses.append("phase = ?")
            params.append(phase)
        
        params.append(limit)
        
        query = f"""
            SELECT id, content, tag, phase, checkpoint, created_at, access_count
            FROM memories WHERE {' AND '.join(where_clauses)}
            ORDER BY access_count DESC, created_at DESC LIMIT ?
        """
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        if results:
            ids = [r['id'] for r in results]
            cursor.execute(f"""
                UPDATE memories SET access_count = access_count + 1,
                    last_accessed_at = CURRENT_TIMESTAMP
                WHERE id IN ({','.join('?' * len(ids))})
            """, ids)
            conn.commit()
        
        conn.close()
        return results
    
    def list_all(self, tag: Optional[str] = None, phase: Optional[str] = None,
                 checkpoint: Optional[int] = None, limit: int = 50) -> List[Dict]:
        """List all memories with optional filters."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        where_clauses = []
        params = []
        
        if tag:
            where_clauses.append("tag = ?")
            params.append(tag)
        if phase:
            where_clauses.append("phase = ?")
            params.append(phase)
        if checkpoint:
            where_clauses.append("checkpoint = ?")
            params.append(checkpoint)
        
        params.append(limit)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = f"""
            SELECT id, content, tag, phase, checkpoint, created_at, access_count
            FROM memories {where_sql}
            ORDER BY created_at DESC LIMIT ?
        """
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def export(self, output_file: str = "bootstrap_memories.json"):
        """Export all memories for ingestion into full ACMS."""
        memories = self.list_all(limit=10000)
        with open(output_file, 'w') as f:
            json.dump(memories, f, indent=2, default=str)
        print(f"✅ Exported {len(memories)} memories to {output_file}")
        return output_file
    
    def stats(self) -> Dict:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT tag, COUNT(*) FROM memories WHERE tag IS NOT NULL GROUP BY tag")
        by_tag = dict(cursor.fetchall())
        
        cursor.execute("SELECT phase, COUNT(*) FROM memories WHERE phase IS NOT NULL GROUP BY phase")
        by_phase = dict(cursor.fetchall())
        
        conn.close()
        return {'total': total, 'by_tag': by_tag, 'by_phase': by_phase}


def main():
    parser = argparse.ArgumentParser(description="ACMS-Lite: Memory for Claude Code")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    store_parser = subparsers.add_parser('store', help='Store a memory')
    store_parser.add_argument('content', help='Content to remember')
    store_parser.add_argument('--tag', help='Tag (decision/error/architecture/etc)')
    store_parser.add_argument('--phase', help='Build phase')
    store_parser.add_argument('--checkpoint', type=int, help='Checkpoint number')
    
    query_parser = subparsers.add_parser('query', help='Query memories')
    query_parser.add_argument('search', help='Search term')
    query_parser.add_argument('--tag', help='Filter by tag')
    query_parser.add_argument('--phase', help='Filter by phase')
    query_parser.add_argument('--limit', type=int, default=5, help='Max results')
    
    list_parser = subparsers.add_parser('list', help='List all memories')
    list_parser.add_argument('--tag', help='Filter by tag')
    list_parser.add_argument('--phase', help='Filter by phase')
    list_parser.add_argument('--checkpoint', type=int, help='Filter by checkpoint')
    list_parser.add_argument('--limit', type=int, default=50, help='Max results')
    
    subparsers.add_parser('export', help='Export for full ACMS')
    subparsers.add_parser('stats', help='Show statistics')
    
    args = parser.parse_args()
    acms = ACMSLite()
    
    if args.command == 'store':
        acms.store(args.content, args.tag, args.phase, args.checkpoint)
    elif args.command == 'query':
        results = acms.query(args.search, args.tag, args.phase, args.limit)
        if results:
            print(f"\n🔍 Found {len(results)} result(s):\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. [{r['tag'] or 'untagged'}] {r['content']}")
                print(f"   Phase: {r['phase'] or 'N/A'} | Checkpoint: {r['checkpoint'] or 'N/A'} | Used: {r['access_count']}x\n")
        else:
            print("❌ No matching memories found")
    elif args.command == 'list':
        results = acms.list_all(args.tag, args.phase, args.checkpoint, args.limit)
        print(f"\n📋 {len(results)} memories:\n")
        for r in results:
            tag = f"[{r['tag']}]" if r['tag'] else "[untagged]"
            print(f"#{r['id']} {tag} {r['content'][:80]}")
    elif args.command == 'export':
        acms.export()
    elif args.command == 'stats':
        stats = acms.stats()
        print(f"\n📊 ACMS-Lite Statistics:")
        print(f"   Total: {stats['total']}")
        if stats['by_tag']:
            print(f"\n   By tag:")
            for tag, count in stats['by_tag'].items():
                print(f"     {tag}: {count}")
        if stats['by_phase']:
            print(f"\n   By phase:")
            for phase, count in stats['by_phase'].items():
                print(f"     {phase}: {count}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
```

**Make executable:**
```bash
chmod +x acms_lite.py
```

### **Step 2: Test ACMS-Lite (Hour 1)**

Run these tests to verify it works:

```bash
# Test 1: Store a memory
python acms_lite.py store "ACMS-Lite initialized successfully" --tag milestone --checkpoint 0
# Expected: ✅ Stored #1: ACMS-Lite initialized successfully...

# Test 2: Query that memory
python acms_lite.py query "initialized"
# Expected: Should return the memory you just stored

# Test 3: List all memories
python acms_lite.py list
# Expected: Should show 1 memory

# Test 4: Check stats
python acms_lite.py stats
# Expected: Should show total=1, by_tag={'milestone': 1}
```

**If ALL tests pass: ✅ Continue**  
**If ANY test fails: 🛑 STOP and fix before proceeding**

### **Step 3: Create Checkpoint 0 Test (Hour 1-2)**

Create `tests/checkpoint_validation.py` and add Checkpoint 0:

```python
def validate_checkpoint_0(self) -> Dict[str, bool]:
    """Checkpoint 0: ACMS-Lite Working"""
    tests = {}
    
    # Test 1: Script exists
    tests['acms_lite_exists'] = os.path.exists('acms_lite.py')
    
    # Test 2: Can execute
    try:
        result = subprocess.run(
            ['python', 'acms_lite.py', 'stats'],
            capture_output=True,
            text=True,
            timeout=5
        )
        tests['acms_lite_executable'] = result.returncode == 0
    except:
        tests['acms_lite_executable'] = False
    
    # Test 3: Store works
    try:
        result = subprocess.run(
            ['python', 'acms_lite.py', 'store', 'Test memory', '--tag', 'test'],
            capture_output=True,
            text=True,
            timeout=5
        )
        tests['store_works'] = result.returncode == 0
    except:
        tests['store_works'] = False
    
    # Test 4: Query works
    try:
        result = subprocess.run(
            ['python', 'acms_lite.py', 'query', 'Test'],
            capture_output=True,
            text=True,
            timeout=5
        )
        tests['query_works'] = result.returncode == 0 and 'Test memory' in result.stdout
    except:
        tests['query_works'] = False
    
    return tests
```

**Run Checkpoint 0:**
```bash
python tests/checkpoint_validation.py 0
# Expected: All tests PASS ✅
```

### **Step 4: Document Initial State (Hour 2)**

Store the starting context:

```bash
python acms_lite.py store "ACMS build starts with ACMS-Lite for context persistence" --tag architecture --phase bootstrap

python acms_lite.py store "Project structure: src/ for code, tests/ for tests, docs/ for documentation" --tag architecture --phase bootstrap

python acms_lite.py store "Tech stack: Python 3.11+, FastAPI, SQLAlchemy, Weaviate, Ollama" --tag decision --phase bootstrap

python acms_lite.py store "Goal: Build production-ready ACMS MVP in 68 hours with 5 checkpoints" --tag goal --phase bootstrap
```

**✅ PHASE 0 COMPLETE - Ready to build main ACMS!**

---

## 🔄 MANDATORY WORKFLOW FOR EVERY SESSION

### **At START of Every Session:**

```bash
#!/bin/bash
# run_at_session_start.sh

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 ACMS-Lite Context Restoration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Show statistics
echo -e "\n📊 Memory Statistics:"
python acms_lite.py stats

# 2. Show last 10 memories
echo -e "\n📝 Last 10 Memories:"
python acms_lite.py list --limit 10

# 3. Show any unresolved errors
echo -e "\n⚠️  Recent Errors (if any):"
python acms_lite.py list --tag error --limit 5

# 4. Show current phase memories
CURRENT_PHASE="$1"  # Pass phase as argument
if [ ! -z "$CURRENT_PHASE" ]; then
    echo -e "\n📂 Memories from current phase ($CURRENT_PHASE):"
    python acms_lite.py list --phase "$CURRENT_PHASE" --limit 15
fi

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Context loaded. Ready to continue building!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
```

**Run it:**
```bash
bash run_at_session_start.sh infrastructure  # or current phase name
```

### **BEFORE Making ANY Decision:**

**MANDATORY QUERY FLOW:**

```bash
# Step 1: Query ACMS-Lite for relevant context
python acms_lite.py query "keywords about decision"

# Step 2: Check results
# - If FOUND: Use that decision (don't repeat work!)
# - If NOT FOUND: Make decision, then store it (Step 3)

# Step 3: Store the new decision
python acms_lite.py store "Decision: X because Y" --tag decision --phase current_phase
```

**Examples:**

```bash
# Example 1: Port selection
python acms_lite.py query "API port"
# If found: Use that port
# If not found: Choose port, then store it

# Example 2: Encryption choice
python acms_lite.py query "encryption"
# If found: Use that encryption method
# If not found: Research, choose, then store decision

# Example 3: Model selection
python acms_lite.py query "embedding model"
# If found: Use that model
# If not found: Choose model, then store it
```

### **AFTER Implementing Something:**

```bash
# Store what was implemented
python acms_lite.py store "Implemented [component]: [description]" --tag implementation --phase [phase]

# Example:
python acms_lite.py store "Implemented Weaviate client with auto-detection: tries localhost:8080, 8081, then fallback" --tag implementation --phase storage
```

### **AFTER Fixing an Error:**

```bash
# Store the error AND solution
python acms_lite.py store "ERROR: [problem description]. SOLUTION: [what fixed it]" --tag error --phase [phase]

# Example:
python acms_lite.py store "ERROR: Weaviate connection timeout. SOLUTION: Added retry logic with exponential backoff (3 attempts)" --tag error --phase storage
```

### **AFTER Each Checkpoint:**

```bash
# Store checkpoint results
python acms_lite.py store "Checkpoint [N] [PASSED/FAILED]: [summary]" --tag checkpoint --checkpoint [N]

# Example:
python acms_lite.py store "Checkpoint 1 PASSED: All infrastructure services healthy, ports configured correctly" --tag checkpoint --checkpoint 1
```

### **At END of Every Session:**

```bash
#!/bin/bash
# run_at_session_end.sh

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 Session Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show what was stored this session (last hour)
echo -e "\n📝 Memories stored this session:"
python acms_lite.py list --limit 20

# Show updated statistics
echo -e "\n📊 Updated Statistics:"
python acms_lite.py stats

# Verify ACMS-Lite is healthy
echo -e "\n🏥 Health Check:"
if python acms_lite.py stats > /dev/null 2>&1; then
    echo "   ✅ ACMS-Lite is healthy"
else
    echo "   ❌ ACMS-Lite has issues - FIX BEFORE NEXT SESSION"
fi

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Session context preserved!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
```

---

## 📊 WHAT TO STORE (Comprehensive List)

### **ALWAYS Store:**

| Event Type | When | Tag | Example |
|------------|------|-----|---------|
| **Decisions** | Made any choice | `decision` | "Chose PostgreSQL over MongoDB because..." |
| **Configuration** | Set any value | `config` | "API port: 30080" |
| **Architecture** | Design choice | `architecture` | "Using Weaviate for vectors, Postgres for metadata" |
| **Errors** | Fixed a bug | `error` | "ERROR: X. SOLUTION: Y" |
| **Performance** | Measured speed | `performance` | "API latency: 145ms p95" |
| **Security** | Security decision | `security` | "Using XChaCha20-Poly1305 for encryption" |
| **Schema** | Database design | `schema` | "Users table has email, password_hash, created_at" |
| **Algorithm** | Logic design | `algorithm` | "CRS formula: weighted sum with exponential decay" |
| **Model** | AI model choice | `model` | "Using all-minilm:22m for embeddings (384-dim)" |
| **API** | Endpoint design | `api` | "POST /v1/memory/ingest creates memory with auto-embedding" |
| **Test** | Test result | `test` | "Unit test coverage: 82%" |
| **Optimization** | Performance fix | `optimization` | "Added connection pooling, 40% faster queries" |
| **Checkpoint** | Milestone reached | `checkpoint` | "Checkpoint 3 PASSED: All core features working" |

### **Examples of Good Memory Entries:**

```bash
# Good ✅
python acms_lite.py store "Weaviate auto-detection order: localhost:8080, then :8081, then Docker name 'weaviate', then in-memory fallback" --tag architecture --phase storage

# Bad ❌
python acms_lite.py store "Fixed Weaviate stuff" --tag error --phase storage
# (Too vague, no details about what or how)

# Good ✅
python acms_lite.py store "CRS weights: semantic=0.35, recency=0.20, outcome=0.25, frequency=0.10, corrections=0.10. Weights must sum to 1.0" --tag formula --phase core

# Bad ❌
python acms_lite.py store "Set weights" --tag formula --phase core
# (Missing the actual values)

# Good ✅
python acms_lite.py store "ERROR: Async/await in Ollama client caused runtime error. SOLUTION: Used httpx.AsyncClient() context manager properly with async with" --tag error --phase api

# Bad ❌
python acms_lite.py store "Fixed async issue" --tag error --phase api
# (No details on what the issue was or how it was fixed)
```

---

## 🎯 LEARNING FROM ACMS-LITE USAGE

### **Meta-Observations to Track:**

As you use ACMS-Lite, notice and store these insights:

```bash
# When ACMS-Lite proves useful
python acms_lite.py store "INSIGHT: Querying 'encryption' saved 10 minutes - found previous decision instantly" --tag insight --phase meta

# When you wish ACMS-Lite had a feature
python acms_lite.py store "WISH: Would be nice to search by date range" --tag feature_request --phase meta

# When storage structure helps/hurts
python acms_lite.py store "OBSERVATION: Tags are super useful for filtering. Should emphasize tags in full ACMS" --tag insight --phase meta

# When retrieval is good/bad
python acms_lite.py store "INSIGHT: Keyword search works great for technical terms, less good for concepts" --tag insight --phase meta
```

**These insights will improve full ACMS design!**

---

## ✅ VALIDATION THAT ACMS-LITE IS WORKING

### **Daily Health Check:**

```bash
#!/bin/bash
# daily_acms_lite_check.sh

echo "🏥 ACMS-Lite Health Check"

# Test 1: Can query
if python acms_lite.py query "test" > /dev/null 2>&1; then
    echo "✅ Query works"
else
    echo "❌ Query broken - CRITICAL"
    exit 1
fi

# Test 2: Can store
if python acms_lite.py store "Health check $(date)" --tag test > /dev/null 2>&1; then
    echo "✅ Store works"
else
    echo "❌ Store broken - CRITICAL"
    exit 1
fi

# Test 3: Database not corrupted
if python acms_lite.py stats > /dev/null 2>&1; then
    echo "✅ Database healthy"
else
    echo "❌ Database corrupted - CRITICAL"
    exit 1
fi

# Test 4: Growing appropriately
TOTAL=$(python acms_lite.py stats 2>/dev/null | grep "Total:" | awk '{print $2}')
if [ "$TOTAL" -gt 10 ]; then
    echo "✅ Memories accumulating ($TOTAL total)"
else
    echo "⚠️  Only $TOTAL memories - are you storing enough?"
fi

echo "✅ ACMS-Lite is healthy!"
```

**Run daily:** `bash daily_acms_lite_check.sh`

### **Usage Metrics to Track:**

```bash
# After each phase, check usage
python acms_lite.py stats

# Expected growth:
# After Phase 0: 5-10 memories
# After Phase 1: 30-60 memories
# After Phase 2: 80-150 memories
# After Phase 3: 150-250 memories
# After Phase 4: 200-320 memories
# After Phase 5: 250-400 memories
# After Phase 6: 300-500 memories

# If numbers are low, you're not storing enough!
```

---

## 🔄 MIGRATION TO FULL ACMS (Hour 68)

### **Step 1: Export Bootstrap Memories**

```bash
# Export all ACMS-Lite memories
python acms_lite.py export

# Creates: bootstrap_memories.json
# Check file size
ls -lh bootstrap_memories.json
# Should be 50-200 KB depending on memory count
```

### **Step 2: Validate Export**

```bash
# Verify JSON is valid
python -m json.tool bootstrap_memories.json > /dev/null && echo "✅ Valid JSON" || echo "❌ Invalid JSON"

# Check memory count
cat bootstrap_memories.json | jq '. | length'
# Should match: python acms_lite.py stats (total)
```

### **Step 3: Import to Full ACMS**

```bash
# Create import script
cat > scripts/import_bootstrap.py << 'EOF'
#!/usr/bin/env python3
"""Import ACMS-Lite memories into full ACMS."""

import json
import sys
import requests
from datetime import datetime

def import_memories(json_file: str, base_url: str, token: str):
    """Import bootstrap memories into ACMS."""
    
    with open(json_file) as f:
        memories = json.load(f)
    
    print(f"Importing {len(memories)} memories...")
    
    success_count = 0
    fail_count = 0
    
    for memory in memories:
        content = memory['content']
        tag = memory.get('tag', 'bootstrap')
        phase = memory.get('phase', 'unknown')
        created_at = memory.get('created_at')
        
        # Add metadata about bootstrap origin
        metadata = {
            'source': 'acms_lite_bootstrap',
            'original_tag': tag,
            'original_phase': phase,
            'original_created_at': created_at,
            'bootstrap_memory_id': memory['id']
        }
        
        try:
            response = requests.post(
                f"{base_url}/v1/memory/ingest",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "content": content,
                    "metadata": metadata
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                success_count += 1
                if success_count % 10 == 0:
                    print(f"  Imported {success_count}/{len(memories)}...")
            else:
                fail_count += 1
                print(f"  Failed: {memory['id']} - {response.status_code}")
        
        except Exception as e:
            fail_count += 1
            print(f"  Error: {memory['id']} - {e}")
    
    print(f"\n✅ Import complete!")
    print(f"   Success: {success_count}")
    print(f"   Failed: {fail_count}")
    
    return success_count, fail_count

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python import_bootstrap.py <json_file> <api_url> <token>")
        sys.exit(1)
    
    import_memories(sys.argv[1], sys.argv[2], sys.argv[3])
EOF

chmod +x scripts/import_bootstrap.py

# Run import
python scripts/import_bootstrap.py \
    bootstrap_memories.json \
    http://localhost:30080 \
    $YOUR_JWT_TOKEN
```

### **Step 4: Verify Import**

```bash
# Query full ACMS for bootstrap memories
curl -X POST http://localhost:30080/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What was the CRS formula decision?","max_tokens":500}'

# Should return the memory you stored during Phase 3! ✅
```

### **Step 5: Self-Reference Test 🤯**

```bash
# Ask ACMS about its own creation
curl -X POST http://localhost:30080/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"How was I built? What were the key decisions during my creation?","max_tokens":2000}'

# ACMS should return comprehensive context about its own build process!
# This is PROOF that the memory system works! 🎉
```

---

## 🏆 SUCCESS CRITERIA

### **ACMS-Lite Usage is Successful When:**

- ✅ **Checkpoint 0 passes** (ACMS-Lite functional)
- ✅ **250+ memories stored** by end of build
- ✅ **Query used before every decision** (no repeated questions)
- ✅ **All errors have solutions stored** (knowledge preserved)
- ✅ **Migration to full ACMS works** (all memories imported)
- ✅ **Full ACMS can answer "How was I built?"** (self-aware!)

### **Red Flags (Fix Immediately):**

- 🚨 ACMS-Lite health check fails
- 🚨 Less than 10 memories per phase
- 🚨 Claude Code repeats previous questions
- 🚨 Decisions made without querying first
- 🚨 Export produces invalid JSON
- 🚨 Import to full ACMS fails

---

## 💡 PRO TIPS FOR CLAUDE CODE

1. **Query is Fast** - Don't hesitate to query before every decision
2. **Over-Store** - Better to store too much than too little
3. **Tag Everything** - Tags make retrieval much easier
4. **Be Specific** - "API port: 30080" not "set port"
5. **Include Context** - "Decision: X because Y" not just "X"
6. **Store Solutions** - Every error should have a solution stored
7. **Review Regularly** - Run `python acms_lite.py stats` often
8. **Use Phases** - Phase tags help organize memories
9. **Track Insights** - Note what works/doesn't for full ACMS
10. **Validate Daily** - Run health check daily

---

## 🎯 CRITICAL REMINDER

**ACMS-Lite is not optional!**

This is the **only way** to:
- Maintain context across 68-hour build
- Avoid repeating work
- Learn from errors
- Test memory concept iteratively
- Create self-aware ACMS

**If you skip ACMS-Lite, the build will:**
- Lose context frequently
- Repeat decisions
- Forget solutions
- Miss design insights
- Result in ACMS with no memory of its creation

**Build ACMS-Lite first. Use it constantly. Your future self will thank you.** 🙏

# ACMS: Complete Build Instructions for Claude Code [PRODUCTION-GRADE]

**🎯 MISSION**: Build production-ready ACMS MVP in 68 hours using memory-first TDD approach  
**🧠 STRATEGY**: Build ACMS-Lite first (Hour 0-2), use it to build Full ACMS (Hour 2-68)  
**📊 RESULT**: Self-aware ACMS with 100% test coverage, production-ready code  
**⚡ QUALITY**: Perfect code first time - comprehensive tests, no workarounds, high performance

---

## 🚨 CRITICAL MANDATES FOR CLAUDE CODE

### **CODE QUALITY REQUIREMENTS:**

1. ✅ **Production-Grade Only** - No placeholders, no TODOs, no shortcuts
2. ✅ **Test-Driven Development** - Write tests FIRST, then implementation
3. ✅ **Comprehensive Testing** - Unit (80%+), integration, API, negative, edge cases
4. ✅ **Performance Optimized** - Meet or exceed all latency targets
5. ✅ **Error Handling** - Every error path handled, logged, tested
6. ✅ **Type Safety** - Full type hints (Python), proper types (Go)
7. ✅ **Documentation** - Every function, class, API endpoint documented
8. ✅ **Security First** - Input validation, auth checks, encryption everywhere

### **DEVELOPMENT WORKFLOW:**

1. ✅ **Build ACMS-Lite FIRST** (Hours 0-2)
2. ✅ **Query ACMS-Lite before every decision** (avoid duplicates)
3. ✅ **Store every decision in ACMS-Lite** (build complete history)
4. ✅ **Write tests BEFORE implementation** (TDD always)
5. ✅ **Validate at checkpoints** (6 mandatory checkpoints)
6. ✅ **Generate phase summary** (claude.md after each phase)
7. ✅ **Never proceed if tests fail** (fix immediately)

### **NEVER:**

- ❌ Skip ACMS-Lite or tests
- ❌ Use placeholder code or workarounds
- ❌ Make untested changes
- ❌ Proceed if checkpoints fail
- ❌ Ask user for info in ACMS-Lite
- ❌ Skip documentation or type hints

---

## 🧠 META-RECURSIVE CONCEPT

```
┌──────────────────────────────────────────────────────────┐
│ Hour 0-2: Build ACMS-Lite (SQLite + CLI)                │
│   → Simple memory system operational in 2 hours          │
│   → Store/query/list commands working                    │
│   → Zero infrastructure dependencies                      │
│   → Checkpoint 0: Validate ACMS-Lite functional          │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ Hour 2-68: Build Full ACMS (using ACMS-Lite constantly) │
│   → Claude Code queries ACMS-Lite before decisions       │
│   → Stores every decision, error, solution               │
│   → Zero context loss across sessions                     │
│   → Complete audit trail of build process                │
│   → 6 checkpoints validate progress                      │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ Hour 68+: Migrate ACMS-Lite → Full ACMS                 │
│   → Export 300-500 bootstrap memories                    │
│   → Import into production ACMS                          │
│   → Result: ACMS remembers its own creation! 🤯         │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 BUILD PHASES (68 Hours)

### **PHASE 0: Bootstrap Memory (Hours 0-2)** ⭐

**Goal**: Build ACMS-Lite for immediate memory capability

**Implementation**:
```python
# File: acms_lite.py (~200 lines)
# - SQLite backend (no dependencies)
# - CLI: store, query, list, export, stats
# - Tags, phases, checkpoints
# - Keyword search (no embeddings)
```

**Testing Requirements**:
```bash
# Unit Tests (Hour 1)
tests/test_acms_lite.py:
  ✅ test_store_memory
  ✅ test_query_by_keyword
  ✅ test_list_with_filters
  ✅ test_export_json
  ✅ test_stats_calculation
  ✅ test_duplicate_detection
  ✅ test_empty_database
  ✅ test_special_characters
  
# Coverage: 100% (it's only 200 lines!)
```

**Checkpoint 0 (Hour 2)**:
```bash
python tests/checkpoint_validation.py 0

Required Tests:
  ✅ ACMS-Lite executable
  ✅ SQLite database created
  ✅ Store command works
  ✅ Query returns correct results
  ✅ List command functional
  ✅ Stats accurate
  ✅ Export produces valid JSON
  ✅ No errors in health check
```

**Store Initial Context**:
```bash
python acms_lite.py store "Phase 0 complete: ACMS-Lite operational" --tag milestone --checkpoint 0
python acms_lite.py store "Tech stack: Go (APIs), Python (ML), PostgreSQL, Weaviate, Redis, Ollama" --tag architecture --phase bootstrap
python acms_lite.py store "Ports: API=30080, PG=30432, Redis=30379, Weaviate=30480, Ollama=30434" --tag config --phase bootstrap
python acms_lite.py store "Quality: TDD always, 80%+ coverage, production-grade code only" --tag requirement --phase bootstrap
```

**Deliverable**: Working `acms_lite.py` + passing Checkpoint 0

---

### **PHASE 1: Infrastructure (Hours 2-10)**

**Session Start Workflow**:
```bash
# 1. Restore context
python acms_lite.py stats
python acms_lite.py list --limit 10
python acms_lite.py query "port configuration"
python acms_lite.py list --phase bootstrap --limit 5

# 2. Proceed with phase
```

**Implementation**:
- Docker Compose configuration
- PostgreSQL (port 30432) with migrations
- Redis (port 30379) with config
- Weaviate (port 30480) with auto-detection
- Ollama (port 30434) with model setup
- Makefile with all commands
- Health check scripts

**Testing Requirements**:
```bash
# Unit Tests
tests/unit/test_docker_config.py:
  ✅ test_docker_compose_valid_yaml
  ✅ test_all_ports_available
  ✅ test_volume_mounts_correct
  ✅ test_environment_variables
  
tests/unit/test_weaviate_detection.py:
  ✅ test_localhost_8080_detection
  ✅ test_localhost_8081_fallback
  ✅ test_docker_name_detection
  ✅ test_in_memory_final_fallback
  ✅ test_connection_retry_logic

# Integration Tests
tests/integration/test_infrastructure.py:
  ✅ test_postgres_connection
  ✅ test_postgres_authentication
  ✅ test_redis_connection
  ✅ test_redis_set_get
  ✅ test_weaviate_health_check
  ✅ test_weaviate_collection_list
  ✅ test_ollama_model_list
  ✅ test_ollama_embedding_test
  
# Negative Tests
tests/negative/test_infrastructure_failures.py:
  ✅ test_postgres_wrong_password
  ✅ test_postgres_wrong_port
  ✅ test_redis_connection_timeout
  ✅ test_weaviate_all_endpoints_fail
  ✅ test_ollama_model_not_found
  
# Coverage: 85%+
```

**Store Decisions**:
```bash
python acms_lite.py store "PostgreSQL: port 30432, database 'acms', user 'acms_user'" --tag config --phase infra
python acms_lite.py store "Redis: port 30379, max memory 256MB, eviction policy allkeys-lru" --tag config --phase infra
python acms_lite.py store "Weaviate auto-detect: localhost:8080 → :8081 → docker 'weaviate' → in-memory" --tag architecture --phase infra
python acms_lite.py store "CRITICAL: NEVER delete existing Weaviate collections - check exists first" --tag safety --phase infra
python acms_lite.py store "Ollama models: llama3.2:1b (LLM), all-minilm:22m (embeddings)" --tag model --phase infra
```

**Checkpoint 1 (Hour 10)**:
```bash
python tests/checkpoint_validation.py 1

Required Tests:
  ✅ All containers running
  ✅ PostgreSQL accessible on 30432
  ✅ Redis accessible on 30379
  ✅ Weaviate accessible on 30480
  ✅ Ollama accessible on 30434
  ✅ Database 'acms' created
  ✅ Health checks pass for all services
  ✅ No port conflicts
  
python acms_lite.py store "Checkpoint 1 PASSED: Infrastructure healthy" --tag checkpoint --checkpoint 1
```

**Generate Phase Summary**:
```bash
# Claude Code creates: docs/phase1_summary.md
# Contains:
# - What was built
# - Key decisions made
# - Test coverage achieved
# - Known issues (if any)
# - Next phase preview
```

---

### **PHASE 2: Storage Layer (Hours 10-18)**

**Session Start**:
```bash
python acms_lite.py query "postgres port"      # Check configuration
python acms_lite.py query "weaviate"           # Check Weaviate setup
python acms_lite.py list --phase infra --limit 10
```

**Implementation**:
- PostgreSQL schemas + Alembic migrations
- Weaviate schema and collection setup
- Encryption module (XChaCha20-Poly1305)
- Database connection pooling
- ORM models (SQLAlchemy)
- CRUD operations

**Testing Requirements**:
```bash
# Unit Tests
tests/unit/test_models.py:
  ✅ test_user_model_creation
  ✅ test_memory_item_validation
  ✅ test_query_log_model
  ✅ test_outcome_model
  ✅ test_audit_log_model
  
tests/unit/test_encryption.py:
  ✅ test_encrypt_decrypt_cycle
  ✅ test_nonce_uniqueness
  ✅ test_tamper_detection
  ✅ test_different_keys_fail
  ✅ test_empty_plaintext
  ✅ test_large_data (10MB)
  ✅ test_encryption_performance (< 1ms per KB)
  
tests/unit/test_weaviate_client.py:
  ✅ test_create_collection
  ✅ test_insert_object
  ✅ test_vector_search
  ✅ test_batch_insert (100 items)
  ✅ test_delete_object
  ✅ test_update_object

# Integration Tests
tests/integration/test_storage.py:
  ✅ test_end_to_end_memory_storage
  ✅ test_postgres_weaviate_sync
  ✅ test_encrypted_storage_retrieval
  ✅ test_concurrent_writes (10 threads)
  ✅ test_transaction_rollback
  ✅ test_connection_pool_exhaustion
  
# Negative Tests
tests/negative/test_storage_failures.py:
  ✅ test_invalid_user_data
  ✅ test_sql_injection_attempts
  ✅ test_oversized_memory_item (> 1MB)
  ✅ test_invalid_encryption_key
  ✅ test_corrupted_nonce
  ✅ test_weaviate_collection_not_found
  ✅ test_postgres_connection_lost
  
# Edge Cases
tests/edge_cases/test_storage_edge_cases.py:
  ✅ test_empty_content
  ✅ test_unicode_emoji_content
  ✅ test_very_long_content (100KB)
  ✅ test_special_chars_in_metadata
  ✅ test_null_metadata_fields
  ✅ test_duplicate_memory_detection
  
# Performance Tests
tests/performance/test_storage_performance.py:
  ✅ test_insert_latency (< 50ms p95)
  ✅ test_search_latency (< 100ms p95)
  ✅ test_batch_insert_throughput (> 100 items/sec)
  
# Coverage: 85%+
```

**Store Decisions**:
```bash
python acms_lite.py store "PostgreSQL schema: users, memory_metadata, query_logs, outcomes, audit_logs" --tag schema --phase storage
python acms_lite.py store "Weaviate collection: ACMS_MemoryItems_v1, 384-dim vectors (all-minilm)" --tag schema --phase storage
python acms_lite.py store "Memory items stored in Weaviate with embeddings, metadata in PostgreSQL" --tag architecture --phase storage
python acms_lite.py store "Encryption: XChaCha20-Poly1305, 256-bit keys, nonce stored with ciphertext" --tag security --phase storage
python acms_lite.py store "Connection pool: PostgreSQL max 20 connections, Redis max 10" --tag config --phase storage
python acms_lite.py store "ERROR: Weaviate timeout on large batch. SOLUTION: Batch size 50, retry 3x with exponential backoff" --tag error --phase storage
```

**Checkpoint 2 (Hour 18)**:
```bash
python tests/checkpoint_validation.py 2

Required Tests:
  ✅ All migrations applied
  ✅ All tables created correctly
  ✅ User CRUD operations work
  ✅ Memory storage and retrieval work
  ✅ Encryption/decryption functional
  ✅ Weaviate collection exists
  ✅ Vector search returns results
  ✅ Test coverage > 85%
  
python acms_lite.py store "Checkpoint 2 PASSED: Storage layer functional" --tag checkpoint --checkpoint 2
```

**Generate Phase Summary**: `docs/phase2_summary.md`

---

### **PHASE 3: Core Logic (Hours 18-34)**

**Session Start**:
```bash
python acms_lite.py query "encryption"
python acms_lite.py query "schema"
python acms_lite.py list --phase storage --limit 15
```

**Implementation**:
- Context Retrieval System (CRS) scoring engine
- Memory CRUD service
- Ollama client integration
- Embedding generation
- Tier management (LONG/MID/SHORT)
- Outcome tracking
- CRS weight management

**Testing Requirements**:
```bash
# Unit Tests
tests/unit/test_crs_engine.py:
  ✅ test_calculate_semantic_score
  ✅ test_calculate_recency_score
  ✅ test_calculate_outcome_score
  ✅ test_calculate_frequency_score
  ✅ test_calculate_correction_score
  ✅ test_weighted_sum_calculation
  ✅ test_exponential_decay
  ✅ test_tier_classification_long
  ✅ test_tier_classification_mid
  ✅ test_tier_classification_short
  ✅ test_crs_weights_sum_to_one
  ✅ test_zero_weights_handling
  
tests/unit/test_memory_service.py:
  ✅ test_create_memory
  ✅ test_get_memory_by_id
  ✅ test_update_memory
  ✅ test_delete_memory
  ✅ test_list_memories_paginated
  ✅ test_memory_not_found
  ✅ test_unauthorized_access
  
tests/unit/test_ollama_client.py:
  ✅ test_generate_embedding
  ✅ test_embedding_dimensions (384)
  ✅ test_batch_embeddings (10 texts)
  ✅ test_ollama_connection_error
  ✅ test_model_not_loaded
  ✅ test_embedding_cache
  
# Integration Tests
tests/integration/test_core_logic.py:
  ✅ test_end_to_end_memory_creation
  ✅ test_crs_calculation_on_real_data
  ✅ test_tier_promotion_over_time
  ✅ test_tier_demotion_low_usage
  ✅ test_outcome_tracking_updates_crs
  ✅ test_correction_tracking
  ✅ test_concurrent_crs_calculations
  
# Negative Tests
tests/negative/test_core_failures.py:
  ✅ test_invalid_crs_weights
  ✅ test_negative_scores
  ✅ test_ollama_timeout
  ✅ test_embedding_wrong_dimensions
  ✅ test_memory_id_not_found
  ✅ test_unauthorized_memory_access
  ✅ test_invalid_tier_value
  
# Edge Cases
tests/edge_cases/test_core_edge_cases.py:
  ✅ test_crs_all_zeros
  ✅ test_crs_all_ones
  ✅ test_very_old_memory (365+ days)
  ✅ test_very_new_memory (< 1 hour)
  ✅ test_high_frequency_memory (1000+ accesses)
  ✅ test_zero_frequency_memory
  ✅ test_embedding_identical_texts
  
# Performance Tests
tests/performance/test_core_performance.py:
  ✅ test_crs_calculation_speed (< 25ms)
  ✅ test_embedding_generation (< 100ms)
  ✅ test_batch_crs_calculation (100 items < 500ms)
  ✅ test_tier_update_performance (< 10ms)
  
# Coverage: 85%+
```

**Store Decisions**:
```bash
python acms_lite.py store "CRS weights: semantic=0.35, recency=0.20, outcome=0.25, frequency=0.10, corrections=0.10 (sum=1.0)" --tag formula --phase core
python acms_lite.py store "CRS decay: exponential with λ=0.02 per day" --tag formula --phase core
python acms_lite.py store "Tier logic: LONG if CRS>0.80 AND age>=7d, MID if CRS>0.65 AND uses>=3, else SHORT" --tag algorithm --phase core
python acms_lite.py store "Embedding model: all-minilm:22m (384 dimensions, fast)" --tag model --phase core
python acms_lite.py store "LLM model: llama3.2:1b (smallest, fastest for MVP)" --tag model --phase core
python acms_lite.py store "OPTIMIZATION: Numpy vectorization for batch CRS, 10x speedup" --tag performance --phase core
python acms_lite.py store "ERROR: Outcome score NaN for new memories. SOLUTION: Default to 0.5 if no outcomes" --tag error --phase core
```

**Checkpoint 3 (Hour 34)**:
```bash
python tests/checkpoint_validation.py 3

Required Tests:
  ✅ CRS calculation works correctly
  ✅ All CRS components tested
  ✅ Memory CRUD operations functional
  ✅ Ollama embedding generation works
  ✅ Tier classification accurate
  ✅ Outcome tracking functional
  ✅ Performance targets met
  ✅ Test coverage > 85%
  
python acms_lite.py store "Checkpoint 3 PASSED: Core logic complete" --tag checkpoint --checkpoint 3
```

**Generate Phase Summary**: `docs/phase3_summary.md`

---

### **PHASE 4: Rehydration (Hours 34-42)**

**Session Start**:
```bash
python acms_lite.py query "CRS formula"
python acms_lite.py query "tier logic"
python acms_lite.py list --phase core --limit 15
```

**Implementation**:
- Intent classification engine
- Hybrid scoring algorithm
- Token budget management
- Context selection algorithm
- Retrieval pipeline
- Response formatting

**Testing Requirements**:
```bash
# Unit Tests
tests/unit/test_intent_classifier.py:
  ✅ test_classify_code_assist
  ✅ test_classify_research
  ✅ test_classify_meeting_prep
  ✅ test_classify_writing
  ✅ test_classify_analysis
  ✅ test_classify_threat_hunt
  ✅ test_classify_general
  ✅ test_ambiguous_intent
  ✅ test_multi_intent_query
  
tests/unit/test_hybrid_scoring.py:
  ✅ test_default_weights
  ✅ test_intent_specific_weights
  ✅ test_vector_similarity_component
  ✅ test_recency_component
  ✅ test_outcome_component
  ✅ test_crs_component
  ✅ test_score_normalization
  
tests/unit/test_token_budget.py:
  ✅ test_calculate_token_count
  ✅ test_respect_max_budget
  ✅ test_reserve_overhead
  ✅ test_select_within_budget
  ✅ test_priority_ordering
  ✅ test_empty_budget
  
tests/unit/test_context_selection.py:
  ✅ test_select_top_k_memories
  ✅ test_diversity_enforcement
  ✅ test_recency_bias
  ✅ test_tier_preference
  ✅ test_deduplication
  
# Integration Tests
tests/integration/test_rehydration.py:
  ✅ test_end_to_end_rehydration
  ✅ test_retrieval_pipeline_complete
  ✅ test_intent_affects_scoring
  ✅ test_token_budget_respected
  ✅ test_context_formatting
  ✅ test_empty_query_handling
  ✅ test_no_relevant_memories
  
# Negative Tests
tests/negative/test_rehydration_failures.py:
  ✅ test_invalid_intent
  ✅ test_negative_token_budget
  ✅ test_empty_query_string
  ✅ test_weaviate_search_fails
  ✅ test_crs_calculation_error
  ✅ test_malformed_hybrid_scores
  
# Edge Cases
tests/edge_cases/test_rehydration_edge_cases.py:
  ✅ test_very_short_query (1 word)
  ✅ test_very_long_query (500 words)
  ✅ test_special_characters_query
  ✅ test_unicode_emoji_query
  ✅ test_all_memories_below_threshold
  ✅ test_all_memories_above_threshold
  ✅ test_exact_token_budget_match
  
# Performance Tests
tests/performance/test_rehydration_performance.py:
  ✅ test_full_pipeline_latency (< 2s p95)
  ✅ test_intent_classification_speed (< 50ms)
  ✅ test_hybrid_scoring_speed (< 100ms)
  ✅ test_context_selection_speed (< 50ms)
  
# Coverage: 85%+
```

**Store Decisions**:
```bash
python acms_lite.py store "Intent categories: code_assist, research, meeting_prep, writing, analysis, threat_hunt, general" --tag intent --phase rehydration
python acms_lite.py store "Hybrid score = 0.5*vector_sim + 0.2*recency + 0.2*outcome + 0.1*CRS (default, varies by intent)" --tag algorithm --phase rehydration
python acms_lite.py store "Token budget: 1000 default, reserve 10% for prompt overhead" --tag config --phase rehydration
python acms_lite.py store "Retrieval pipeline: Weaviate top-50 → CRS filter → Hybrid rank → Token select" --tag algorithm --phase rehydration
python acms_lite.py store "Context formatting: Markdown with headers, metadata, and sources" --tag format --phase rehydration
python acms_lite.py store "ERROR: Token count exceeded budget. SOLUTION: Truncate by priority, not by position" --tag error --phase rehydration
```

**Checkpoint 4 (Hour 42)**:
```bash
python tests/checkpoint_validation.py 4

Required Tests:
  ✅ Intent classification accurate
  ✅ Hybrid scoring functional
  ✅ Token budget respected
  ✅ Context selection working
  ✅ Retrieval pipeline complete
  ✅ Performance targets met
  ✅ Test coverage > 85%
  
python acms_lite.py store "Checkpoint 4 PASSED: Rehydration functional" --tag checkpoint --checkpoint 4
```

**Generate Phase Summary**: `docs/phase4_summary.md`

---

### **PHASE 5: API Layer (Hours 42-52)**

**Session Start**:
```bash
python acms_lite.py query "port"
python acms_lite.py query "JWT"
python acms_lite.py list --phase rehydration --limit 10
```

**Implementation**:
- FastAPI application setup
- JWT authentication
- Rate limiting middleware
- All REST endpoints
- Request validation
- Error handling
- API documentation (OpenAPI)
- CORS configuration

**API Endpoints to Implement**:
```
POST   /v1/auth/register      - Register new user
POST   /v1/auth/login         - Login and get JWT
POST   /v1/auth/refresh       - Refresh JWT token
POST   /v1/memory/ingest      - Create memory item
GET    /v1/memory/{id}        - Get memory by ID
PUT    /v1/memory/{id}        - Update memory
DELETE /v1/memory/{id}        - Delete memory
GET    /v1/memory             - List memories (paginated)
POST   /v1/query              - Query with rehydration
POST   /v1/outcome            - Record outcome
GET    /v1/stats              - Get statistics
GET    /v1/health             - Health check
```

**Testing Requirements**:
```bash
# Unit Tests
tests/unit/test_auth.py:
  ✅ test_jwt_generation
  ✅ test_jwt_validation
  ✅ test_jwt_expiration
  ✅ test_password_hashing
  ✅ test_password_verification
  ✅ test_invalid_token
  
tests/unit/test_rate_limiting.py:
  ✅ test_rate_limit_enforcement
  ✅ test_rate_limit_reset
  ✅ test_rate_limit_headers
  ✅ test_different_users_separate_limits
  
tests/unit/test_request_validation.py:
  ✅ test_valid_ingest_request
  ✅ test_invalid_ingest_request
  ✅ test_missing_required_fields
  ✅ test_invalid_field_types
  ✅ test_oversized_content
  
# API Tests
tests/api/test_auth_endpoints.py:
  ✅ test_register_success
  ✅ test_register_duplicate_email
  ✅ test_login_success
  ✅ test_login_wrong_password
  ✅ test_login_nonexistent_user
  ✅ test_refresh_token
  ✅ test_expired_token
  
tests/api/test_memory_endpoints.py:
  ✅ test_ingest_memory_success
  ✅ test_ingest_unauthorized
  ✅ test_get_memory_success
  ✅ test_get_memory_not_found
  ✅ test_update_memory_success
  ✅ test_update_unauthorized
  ✅ test_delete_memory_success
  ✅ test_list_memories_paginated
  ✅ test_list_memories_filtered
  
tests/api/test_query_endpoint.py:
  ✅ test_query_success
  ✅ test_query_with_intent
  ✅ test_query_with_token_budget
  ✅ test_query_empty_results
  ✅ test_query_unauthorized
  ✅ test_query_malformed_request
  
tests/api/test_outcome_endpoint.py:
  ✅ test_record_outcome_success
  ✅ test_record_outcome_invalid_memory
  ✅ test_record_outcome_updates_crs
  
# Integration Tests
tests/integration/test_api_integration.py:
  ✅ test_full_user_journey
  ✅ test_register_login_ingest_query
  ✅ test_concurrent_api_requests (50 concurrent)
  ✅ test_rate_limit_across_endpoints
  ✅ test_auth_token_across_requests
  
# Negative Tests
tests/negative/test_api_security.py:
  ✅ test_sql_injection_attempts
  ✅ test_xss_in_content
  ✅ test_csrf_protection
  ✅ test_invalid_jwt_signature
  ✅ test_jwt_token_reuse
  ✅ test_privilege_escalation
  ✅ test_unauthorized_memory_access
  
# Edge Cases
tests/edge_cases/test_api_edge_cases.py:
  ✅ test_empty_request_body
  ✅ test_null_values
  ✅ test_very_long_query (10000 chars)
  ✅ test_special_characters_in_fields
  ✅ test_unicode_in_all_fields
  ✅ test_concurrent_updates_same_memory
  
# Performance Tests
tests/performance/test_api_performance.py:
  ✅ test_ingest_endpoint_latency (< 200ms p95)
  ✅ test_query_endpoint_latency (< 2000ms p95)
  ✅ test_get_memory_latency (< 50ms p95)
  ✅ test_throughput (> 100 req/sec)
  
# Load Tests
tests/load/test_api_load.py:
  ✅ test_1000_concurrent_users
  ✅ test_sustained_load_5min
  ✅ test_spike_load_recovery
  
# Coverage: 85%+
```

**Store Decisions**:
```bash
python acms_lite.py store "API port: 30080 (HTTP), future: 30443 (HTTPS)" --tag config --phase api
python acms_lite.py store "JWT expiry: 1 hour (3600s), refresh token: 7 days" --tag config --phase api
python acms_lite.py store "Rate limit: 100 req/min per user, 1000 req/hour total" --tag config --phase api
python acms_lite.py store "CORS: Allow localhost:3000 for dev, configure for production" --tag config --phase api
python acms_lite.py store "Request validation: Pydantic models for all endpoints" --tag architecture --phase api
python acms_lite.py store "POST /v1/memory/ingest: Creates memory, auto-generates embedding, returns CRS" --tag endpoint --phase api
python acms_lite.py store "ERROR: Async/await syntax error with Ollama client. SOLUTION: Use httpx.AsyncClient() with async context manager" --tag error --phase api
python acms_lite.py store "SECURITY: All endpoints except /health require JWT authentication" --tag security --phase api
```

**Checkpoint 5 (Hour 52)**:
```bash
python tests/checkpoint_validation.py 5

Required Tests:
  ✅ All endpoints functional
  ✅ JWT authentication working
  ✅ Rate limiting enforced
  ✅ Request validation working
  ✅ Error handling comprehensive
  ✅ OpenAPI docs generated
  ✅ Performance targets met
  ✅ Security tests pass
  ✅ Test coverage > 85%
  
python acms_lite.py store "Checkpoint 5 PASSED: API layer complete" --tag checkpoint --checkpoint 5
```

**Generate Phase Summary**: `docs/phase5_summary.md`

---

### **PHASE 6: Testing & Polish (Hours 52-68)**

**Session Start**:
```bash
python acms_lite.py query "performance"
python acms_lite.py list --tag error --limit 10
python acms_lite.py stats
```

**Implementation**:
- End-to-end integration tests
- Performance optimization
- Security hardening
- Documentation completion
- Deployment scripts
- Monitoring setup
- Error logging
- Final polish

**Testing Requirements**:
```bash
# E2E Tests
tests/e2e/test_complete_workflows.py:
  ✅ test_new_user_complete_journey
  ✅ test_multi_session_memory_persistence
  ✅ test_learning_from_outcomes
  ✅ test_memory_evolution_over_time
  ✅ test_tier_transitions
  ✅ test_cross_session_context
  
# Stress Tests
tests/stress/test_system_limits.py:
  ✅ test_10000_memories_storage
  ✅ test_1000_concurrent_queries
  ✅ test_memory_leak_detection
  ✅ test_database_connection_exhaustion
  ✅ test_high_frequency_ingestion
  
# Security Tests
tests/security/test_comprehensive_security.py:
  ✅ test_penetration_scenarios
  ✅ test_encryption_strength
  ✅ test_authentication_bypass_attempts
  ✅ test_data_leakage_scenarios
  ✅ test_input_sanitization
  
# Performance Regression Tests
tests/regression/test_performance_regression.py:
  ✅ test_api_latency_regression
  ✅ test_memory_usage_regression
  ✅ test_database_query_performance
  ✅ test_embedding_generation_speed
  
# Documentation Tests
tests/docs/test_documentation.py:
  ✅ test_all_functions_documented
  ✅ test_all_endpoints_in_openapi
  ✅ test_readme_examples_work
  ✅ test_api_docs_accessible
  
# Final Coverage
✅ Overall test coverage: 85%+
✅ Critical paths coverage: 95%+
✅ Security code coverage: 90%+
```

**Store Decisions**:
```bash
python acms_lite.py store "FINAL: Test coverage achieved 87%" --tag testing --phase testing
python acms_lite.py store "PERFORMANCE: API p95=145ms, Rehydration p95=1.8s, CRS=23ms - ALL TARGETS MET" --tag performance --phase testing
python acms_lite.py store "OPTIMIZATION: PostgreSQL connection pooling reduced query time 40%" --tag optimization --phase testing
python acms_lite.py store "OPTIMIZATION: Redis caching for frequent queries, 60% cache hit rate" --tag optimization --phase testing
python acms_lite.py store "SECURITY: All OWASP Top 10 vulnerabilities addressed" --tag security --phase testing
python acms_lite.py store "DOCUMENTATION: All functions documented, API docs complete, README comprehensive" --tag docs --phase testing
```

**Checkpoint 6 (Hour 68)**:
```bash
python tests/checkpoint_validation.py 6

Required Tests:
  ✅ All E2E tests pass
  ✅ Performance targets met
  ✅ Security audit clean
  ✅ Test coverage > 85%
  ✅ Documentation complete
  ✅ No critical bugs
  ✅ Deployment scripts work
  ✅ Ready for production
  
python acms_lite.py store "MILESTONE: ACMS MVP COMPLETE - Production Ready!" --tag milestone --checkpoint 6
python acms_lite.py stats  # Final statistics
```

**Generate Final Summary**: `docs/phase6_summary.md` + `docs/BUILD_COMPLETE.md`

---

## 🔄 MIGRATION: ACMS-Lite → Full ACMS (Hour 68+)

### **Export Bootstrap Memories**:
```bash
python acms_lite.py export
# Creates: bootstrap_memories.json
# Expected: 300-500 memories

# Validate export
cat bootstrap_memories.json | jq '. | length'
python -m json.tool bootstrap_memories.json > /dev/null && echo "✅ Valid JSON"
```

### **Import to Full ACMS**:
```bash
# Start ACMS
docker-compose up -d
uvicorn src.api.main:app --host 0.0.0.0 --port 30080

# Register admin
curl -X POST http://localhost:30080/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acms.local","password":"SecurePassword123!"}'

# Login
TOKEN=$(curl -X POST http://localhost:30080/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acms.local","password":"SecurePassword123!"}' \
  | jq -r '.token')

# Import memories (use script from Phase 6)
python scripts/import_bootstrap.py bootstrap_memories.json http://localhost:30080 $TOKEN

# Verify import
curl -X GET "http://localhost:30080/v1/stats" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.total_memories'
# Should show 300-500 memories
```

### **Self-Reference Test** 🤯:
```bash
# Ask ACMS about its own creation
curl -X POST http://localhost:30080/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How was the CRS formula designed? What were the key architectural decisions during your creation?",
    "max_tokens": 2000
  }' | jq '.context'

# Expected: Detailed response with bootstrap memories about CRS design, 
# architectural decisions, error resolutions, and complete build history!
```

**✅ ACMS NOW REMEMBERS ITS OWN CREATION!**

---

## 📊 PHASE SUMMARY GENERATION

**After EACH phase, Claude Code must generate**: `docs/phase{N}_summary.md`

**Template**:
```markdown
# Phase {N} Summary: {Phase Name}

## Overview
- **Phase**: {N}
- **Duration**: {Hours}
- **Status**: COMPLETE ✅
- **Checkpoint**: {N} PASSED

## What Was Built
- {Component 1}
- {Component 2}
- ...

## Key Decisions Made
1. {Decision 1 with rationale}
2. {Decision 2 with rationale}
...

## Test Coverage Achieved
- **Unit Tests**: {N} tests, {%} coverage
- **Integration Tests**: {N} tests
- **API Tests**: {N} tests
- **Performance Tests**: {N} tests
- **Total Coverage**: {%}

## Performance Metrics
- {Metric 1}: {Value} (Target: {Target})
- {Metric 2}: {Value} (Target: {Target})
...

## Errors Encountered & Resolved
1. **ERROR**: {Description}
   **SOLUTION**: {Solution}
2. ...

## Files Created/Modified
- {File 1}
- {File 2}
...

## ACMS-Lite Memories Stored
- Total memories this phase: {N}
- Key memories:
  - {Memory 1}
  - {Memory 2}

## Known Issues (If Any)
- None / {Issue description}

## Next Phase Preview
{Brief description of Phase {N+1}}

## Sign-Off
- All tests passing: ✅
- Checkpoint {N} validated: ✅
- Ready for Phase {N+1}: ✅
```

**User Reviews**: After each phase, review `docs/phase{N}_summary.md` before proceeding.

---

## 🎯 SUCCESS CRITERIA

### **Build Complete When:**
- ✅ All 6 checkpoints PASS
- ✅ Test coverage > 85% overall
- ✅ All performance targets met
- ✅ All security tests pass
- ✅ ACMS-Lite has 300+ memories
- ✅ Bootstrap memories migrated
- ✅ Self-reference test works
- ✅ Documentation complete
- ✅ Zero critical bugs
- ✅ Production-ready code

### **Quality Metrics**:
- ✅ Code quality: A grade (no warnings)
- ✅ Security: No vulnerabilities
- ✅ Performance: All targets met
- ✅ Reliability: 99.9% uptime
- ✅ Maintainability: High
- ✅ Documentation: Comprehensive

---

## 🚨 RED FLAGS (Fix Immediately)

- 🚨 Any checkpoint fails
- 🚨 Test coverage < 85%
- 🚨 Performance below targets
- 🚨 Security vulnerabilities found
- 🚨 ACMS-Lite health check fails
- 🚨 < 30 memories per phase
- 🚨 Critical bugs present
- 🚨 Documentation incomplete

**If any red flag appears: STOP and FIX before proceeding!**

---

## 📚 TECHNICAL SPECIFICATIONS

### **Tech Stack**:
- **Go 1.21+**: API Gateway, services
- **Python 3.11+**: ML/AI, ACMS-Lite
- **PostgreSQL 15+**: Metadata, logs
- **Redis 7+**: Caching
- **Weaviate 1.24+**: Vector store
- **Ollama**: Local LLM + embeddings

### **Custom Ports**:
- API: 30080
- PostgreSQL: 30432
- Redis: 30379
- Weaviate: 30480
- Ollama: 30434

### **Performance Targets**:
- API latency: < 200ms p95
- Query latency: < 2s p95
- Embedding: < 100ms
- CRS calculation: < 25ms
- Throughput: > 100 req/sec

### **Security Requirements**:
- JWT authentication (1hr expiry)
- XChaCha20-Poly1305 encryption
- Rate limiting (100/min per user)
- Input validation (all endpoints)
- SQL injection protection
- XSS protection
- CSRF protection

---

## 🔧 MANDATORY WORKFLOWS

### **Session Start**:
```bash
#!/bin/bash
python acms_lite.py stats
python acms_lite.py list --limit 10
python acms_lite.py list --tag error --limit 5
python acms_lite.py list --phase {current_phase} --limit 15
```

### **Before Any Decision**:
```bash
python acms_lite.py query "{relevant keywords}"
# If found → Use that decision
# If not found → Make decision, then store it
```

### **After Implementation**:
```bash
python acms_lite.py store "Implemented {X}: {description}" --tag implementation --phase {phase}
```

### **After Test**:
```bash
python acms_lite.py store "Test: {name} - {result}" --tag test --phase {phase}
```

### **After Error Fix**:
```bash
python acms_lite.py store "ERROR: {problem}. SOLUTION: {fix}" --tag error --phase {phase}
```

### **Session End**:
```bash
#!/bin/bash
python acms_lite.py list --limit 20
python acms_lite.py stats
python acms_lite.py query "test" > /dev/null 2>&1 && echo "✅ ACMS-Lite healthy"
```

---

## 🚀 START COMMAND

```bash
#!/bin/bash
# start_acms_build.sh

echo "🚀 ACMS Build - Production-Grade TDD Approach"
echo "=============================================="
echo ""
echo "Phase 0: Building ACMS-Lite (Hour 0-2)"
echo ""

# Create ACMS-Lite (full code from reference docs)
cat > acms_lite.py << 'EOF'
[Full ACMS-Lite code here - see acms-lite.md]
EOF

chmod +x acms_lite.py

# Test ACMS-Lite
python acms_lite.py store "ACMS build initiated with TDD approach" --tag milestone --checkpoint 0

# Validate Checkpoint 0
python tests/checkpoint_validation.py 0

if [ $? -eq 0 ]; then
    python acms_lite.py store "Checkpoint 0 PASSED: ACMS-Lite operational" --tag checkpoint --checkpoint 0
    echo "✅ ACMS-Lite ready! Proceeding to Phase 1..."
else
    echo "❌ Checkpoint 0 failed. Fix before continuing."
    exit 1
fi
```

---

## 💡 FINAL REMINDERS

1. **TDD Always** - Tests before implementation
2. **Query Before Deciding** - Check ACMS-Lite first
3. **Store Everything** - Build complete history
4. **Production-Grade Only** - No shortcuts
5. **Validate at Checkpoints** - Don't skip
6. **Generate Phase Summaries** - For user review
7. **Fix Red Flags Immediately** - Never proceed with issues
8. **Document Everything** - Code, APIs, decisions

---

**YOU ARE NOW READY TO BUILD PRODUCTION-GRADE ACMS!**

**Execute**: `bash start_acms_build.sh`

**Result**: Self-aware ACMS with 85%+ test coverage, production-ready code, and complete memory of its own creation! 🎯🚀
