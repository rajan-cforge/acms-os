# ACMS-Lite: Operational Usage & Self-Correction Protocol for Claude Code

**🎯 PURPOSE**: Define exactly how Claude Code uses ACMS-Lite and implements self-correction  
**🧠 STRATEGY**: Continuous validation, automatic error detection, controlled rollback  
**🔄 RESULT**: Self-healing build system that catches and fixes issues immediately

---

## 🎬 OPERATIONAL USAGE: HOW CLAUDE CODE USES ACMS-LITE

### **Core Principle: Query Before Every Action**

```
┌─────────────────────────────────────────────────────────┐
│ DECISION FLOW FOR EVERY ACTION                          │
│                                                          │
│ 1. Query ACMS-Lite: "Has this been decided?"           │
│    └─ If YES: Use existing decision (consistency!)      │
│    └─ If NO: Proceed to step 2                          │
│                                                          │
│ 2. Analyze: What's the best approach?                  │
│    └─ Consider context from ACMS-Lite                   │
│    └─ Check for related decisions                       │
│                                                          │
│ 3. Decide: Make the decision                           │
│    └─ Document rationale                                │
│                                                          │
│ 4. Store: Save decision to ACMS-Lite                   │
│    └─ Include context and rationale                     │
│                                                          │
│ 5. Implement: Execute the decision                     │
│    └─ Write tests first (TDD)                          │
│    └─ Implement feature                                 │
│                                                          │
│ 6. Validate: Check it works                            │
│    └─ Run tests                                         │
│    └─ Store test results                                │
│                                                          │
│ 7. Store Result: Document outcome                      │
│    └─ Success or failure                                │
│    └─ Performance metrics                               │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 DETAILED USAGE SCENARIOS

### **Scenario 1: Choosing a Port Number**

```bash
# STEP 1: Query ACMS-Lite first
python acms_lite.py query "API port"

# If found: "API port: 30080"
# ACTION: Use 30080 (don't choose a different port!)

# If not found:
# STEP 2: Choose port (e.g., 30080)

# STEP 3: Store decision with rationale
python acms_lite.py store "API port: 30080 (30000+ range to avoid conflicts with user services)" --tag config --phase infra

# STEP 4: Implement
# Update docker-compose.yml, config files, etc.

# STEP 5: Store implementation
python acms_lite.py store "Updated docker-compose.yml with API port 30080" --tag implementation --phase infra
```

### **Scenario 2: Encountering an Error**

```bash
# ERROR OCCURS: Weaviate connection fails

# STEP 1: Query for similar errors
python acms_lite.py query "weaviate connection" --tag error

# If found: "ERROR: Weaviate timeout. SOLUTION: Retry logic 3x with exponential backoff"
# ACTION: Apply the same solution!

# If not found:
# STEP 2: Analyze and fix

# STEP 3: Store error AND solution
python acms_lite.py store "ERROR: Weaviate connection timeout on large batch. SOLUTION: Reduce batch size from 100 to 50, add retry logic with exponential backoff (1s, 2s, 4s). Tested and working." --tag error --phase storage

# STEP 4: Verify fix works
# Run tests

# STEP 5: Store verification
python acms_lite.py store "Verified: Weaviate batch insert now stable with batch_size=50" --tag test --phase storage
```

### **Scenario 3: Making an Architectural Decision**

```bash
# DECISION NEEDED: Where to store memory items?

# STEP 1: Query for related decisions
python acms_lite.py query "memory storage"
python acms_lite.py query "weaviate"
python acms_lite.py query "postgresql"

# STEP 2: Review context
python acms_lite.py list --tag architecture --phase infra
python acms_lite.py list --tag architecture --phase storage

# STEP 3: Make decision based on context
# Decision: Memory items in Weaviate (vectors + metadata), only query logs in PostgreSQL

# STEP 4: Store with detailed rationale
python acms_lite.py store "ARCHITECTURE: Memory items stored in Weaviate (vectors + metadata) because: (1) Weaviate optimized for vector search, (2) Reduces cross-system queries, (3) Simpler data model. PostgreSQL only for: query_logs, outcomes, audit_logs. This avoids dual-write consistency issues." --tag architecture --phase storage

# STEP 5: Store implications
python acms_lite.py store "IMPLICATION: No foreign keys between Weaviate and PostgreSQL. Use memory_id (UUID) for correlation." --tag architecture --phase storage
```

### **Scenario 4: Session Starts Mid-Build**

```bash
# NEW SESSION STARTS (e.g., next day, or after context loss)

# STEP 1: Restore complete context
echo "🧠 Restoring ACMS-Lite Context..."

# Show overall progress
python acms_lite.py stats

# Show last 20 actions
python acms_lite.py list --limit 20

# Identify current phase
LAST_CHECKPOINT=$(python acms_lite.py list --tag checkpoint --limit 1 | grep "Checkpoint" | awk '{print $2}')
echo "Last completed checkpoint: $LAST_CHECKPOINT"

# STEP 2: Check for unresolved errors
python acms_lite.py list --tag error --limit 10
# Review if any errors don't have "SOLUTION:" in them

# STEP 3: Check current phase memories
if [ "$LAST_CHECKPOINT" == "2" ]; then
  CURRENT_PHASE="core"
  python acms_lite.py list --phase core --limit 20
fi

# STEP 4: Query for specific context needed
python acms_lite.py query "CRS formula"  # If working on CRS
python acms_lite.py query "port configuration"  # If needed

# NOW: Fully restored context, can continue building!
```

### **Scenario 5: Before Writing Any Code**

```bash
# ABOUT TO: Write the CRS scoring function

# STEP 1: Query for design decisions
python acms_lite.py query "CRS weights"
python acms_lite.py query "CRS formula"
python acms_lite.py query "CRS decay"

# Result:
# - "CRS weights: semantic=0.35, recency=0.20, outcome=0.25..."
# - "CRS decay: exponential with λ=0.02 per day"

# STEP 2: Query for similar implementations
python acms_lite.py query "scoring"
python acms_lite.py query "calculation"

# STEP 3: Check for optimization notes
python acms_lite.py query "optimization" --phase core

# NOW: Have all context to write the function correctly!

# STEP 4: After writing, store implementation details
python acms_lite.py store "Implemented calculate_crs() in pkg/crs/scoring.go using stored formula. Used float64 for precision. Returns CRSScore struct with breakdown." --tag implementation --phase core
```

---

## 🔍 SELF-CORRECTION SYSTEM

### **Principle: Continuous Validation + Immediate Correction**

```
┌───────────────────────────────────────────────────────┐
│ QUALITY GATES (Stop Points)                          │
│                                                        │
│ 1. Test Failure → STOP, FIX, RETEST                  │
│ 2. Checkpoint Failure → STOP, ANALYZE, FIX           │
│ 3. Performance Miss → STOP, OPTIMIZE, RETEST         │
│ 4. Security Issue → STOP, SECURE, AUDIT              │
│ 5. Integration Break → STOP, ROLLBACK, FIX           │
│ 6. ACMS-Lite Inconsistency → STOP, RECONCILE         │
└───────────────────────────────────────────────────────┘
```

---

## 🚨 QUALITY GATE 1: TEST FAILURES

### **When Tests Fail:**

```bash
# Running tests
pytest tests/unit/test_crs_engine.py -v

# OUTPUT: FAILED - test_crs_calculation - AssertionError: expected 0.75, got 0.65

# ❌ STOP IMMEDIATELY - DO NOT PROCEED

# STEP 1: Store the failure
python acms_lite.py store "TEST FAILURE: test_crs_calculation failed. Expected 0.75, got 0.65. Investigation needed." --tag test_failure --phase core

# STEP 2: Analyze the failure
python acms_lite.py query "CRS calculation"
python acms_lite.py query "CRS formula"

# Review the stored formula:
# "CRS = 0.35*semantic + 0.20*recency + 0.25*outcome + 0.10*frequency + 0.10*corrections"

# STEP 3: Debug and identify root cause
# Check implementation vs. formula
# Found: Missing the 0.10*corrections component!

# STEP 4: Store root cause
python acms_lite.py store "ROOT CAUSE: test_crs_calculation failed because implementation missing corrections component (0.10*corrections). Formula has 5 components, implementation only had 4." --tag root_cause --phase core

# STEP 5: Fix the code
# Add corrections component to calculate_crs()

# STEP 6: Store the fix
python acms_lite.py store "FIX: Added corrections component to calculate_crs(). Now calculates all 5 components per stored formula." --tag fix --phase core

# STEP 7: Retest
pytest tests/unit/test_crs_engine.py -v
# OUTPUT: PASSED ✅

# STEP 8: Store successful retest
python acms_lite.py store "RETEST SUCCESS: test_crs_calculation now passes. CRS calculation correct." --tag test_success --phase core

# ✅ NOW SAFE TO PROCEED
```

### **Test Failure Protocol:**

```python
# Automated check after every test run
def handle_test_failure(test_name, error_message):
    """Protocol when tests fail."""
    
    # 1. Store failure immediately
    subprocess.run([
        "python", "acms_lite.py", "store",
        f"TEST FAILURE: {test_name} - {error_message}",
        "--tag", "test_failure",
        "--phase", get_current_phase()
    ])
    
    # 2. Query for similar failures
    similar_failures = subprocess.run([
        "python", "acms_lite.py", "query",
        test_name,
        "--tag", "test_failure"
    ], capture_output=True, text=True)
    
    if similar_failures.stdout:
        print("⚠️  Similar failures found:")
        print(similar_failures.stdout)
        print("\n🔍 Check if same root cause!")
    
    # 3. STOP - Do not proceed until fixed
    print("\n🚨 STOP: Fix test failure before proceeding")
    print(f"   Failed test: {test_name}")
    print(f"   Error: {error_message}")
    print("\nSteps:")
    print("1. Analyze root cause")
    print("2. Store root cause in ACMS-Lite")
    print("3. Fix the code")
    print("4. Store the fix in ACMS-Lite")
    print("5. Rerun tests")
    print("6. Only proceed if all tests pass")
    
    sys.exit(1)  # STOP execution
```

---

## 🚨 QUALITY GATE 2: CHECKPOINT FAILURES

### **When Checkpoint Fails:**

```bash
# Running Checkpoint 2
python tests/checkpoint_validation.py 2

# OUTPUT:
# ✅ Database schema created
# ✅ User CRUD working
# ❌ Weaviate collection not found
# ❌ Encryption test failed
# CHECKPOINT 2: FAILED

# 🚨 STOP IMMEDIATELY

# STEP 1: Store checkpoint failure
python acms_lite.py store "CHECKPOINT 2 FAILED: Weaviate collection missing, encryption test failed" --tag checkpoint_failure --checkpoint 2

# STEP 2: Analyze each failure

# Failure 1: Weaviate collection not found
python acms_lite.py query "weaviate collection"
# Found: "Weaviate collection: ACMS_MemoryItems_v1"

# Check if collection was actually created
# Found: Collection creation code missing!

# STEP 3: Store root causes
python acms_lite.py store "ROOT CAUSE 1: Weaviate collection ACMS_MemoryItems_v1 never created. Migration script missing collection creation step." --tag root_cause --phase storage

python acms_lite.py store "ROOT CAUSE 2: Encryption test failed because test key wasn't 32 bytes. Test setup incorrect." --tag root_cause --phase storage

# STEP 4: Fix in order of dependency
# Fix 1: Create Weaviate collection
# Add to migrations/002_create_weaviate_collection.py

python acms_lite.py store "FIX 1: Added migrations/002_create_weaviate_collection.py to create ACMS_MemoryItems_v1 with proper schema." --tag fix --phase storage

# Fix 2: Fix encryption test
# Update tests/unit/test_encryption.py with correct key size

python acms_lite.py store "FIX 2: Fixed test_encryption.py to use 32-byte keys. Was using 16-byte keys." --tag fix --phase storage

# STEP 5: Rerun checkpoint
python tests/checkpoint_validation.py 2
# OUTPUT:
# ✅ Database schema created
# ✅ User CRUD working
# ✅ Weaviate collection exists
# ✅ Encryption test passed
# CHECKPOINT 2: PASSED ✅

# STEP 6: Store success
python acms_lite.py store "CHECKPOINT 2 PASSED after fixes: Collection creation added, encryption test corrected" --tag checkpoint --checkpoint 2

# ✅ NOW SAFE TO PROCEED TO PHASE 3
```

### **Checkpoint Failure Protocol:**

```python
def handle_checkpoint_failure(checkpoint_num, failed_tests):
    """Protocol when checkpoint fails."""
    
    # 1. Store failure with details
    failure_details = ", ".join([t['name'] for t in failed_tests])
    subprocess.run([
        "python", "acms_lite.py", "store",
        f"CHECKPOINT {checkpoint_num} FAILED: {failure_details}",
        "--tag", "checkpoint_failure",
        "--checkpoint", str(checkpoint_num)
    ])
    
    # 2. Analyze each failed test
    print(f"\n🚨 CHECKPOINT {checkpoint_num} FAILED")
    print(f"   Failed tests: {len(failed_tests)}")
    print("\nAnalyzing failures...\n")
    
    for test in failed_tests:
        print(f"❌ {test['name']}")
        print(f"   Error: {test['error']}")
        
        # Query for related context
        result = subprocess.run([
            "python", "acms_lite.py", "query",
            test['name'].lower()
        ], capture_output=True, text=True)
        
        if result.stdout:
            print(f"   Context found: {result.stdout[:200]}...")
    
    # 3. STOP - Must fix all failures
    print("\n🚨 STOP: Fix all checkpoint failures before proceeding")
    print("\nRequired steps:")
    print("1. Analyze root cause for each failure")
    print("2. Store each root cause in ACMS-Lite")
    print("3. Fix issues in dependency order")
    print("4. Store each fix in ACMS-Lite")
    print("5. Rerun checkpoint")
    print("6. Repeat until checkpoint passes")
    
    sys.exit(1)  # STOP execution
```

---

## 🚨 QUALITY GATE 3: INTEGRATION BREAKS

### **When New Code Breaks Old Code:**

```bash
# Scenario: Adding Phase 4 (Rehydration) breaks Phase 3 (Core Logic)

# Running integration tests after implementing rehydration
pytest tests/integration/test_core_logic.py -v

# OUTPUT:
# ✅ test_end_to_end_memory_creation PASSED
# ❌ test_crs_calculation_on_real_data FAILED
# Error: KeyError: 'outcome_score'

# 🚨 STOP - Regression detected!

# STEP 1: Store regression
python acms_lite.py store "REGRESSION: Phase 4 changes broke test_crs_calculation_on_real_data in Phase 3. KeyError: 'outcome_score'" --tag regression --phase rehydration

# STEP 2: Query for what changed
python acms_lite.py list --phase rehydration --tag implementation --limit 10

# Found recent change: "Modified CRSScore struct to include intent_score"

# STEP 3: Identify root cause
# The struct change in rehydration phase modified a core data structure
# Broke existing code that expected old struct format

python acms_lite.py store "ROOT CAUSE: Modified CRSScore struct in Phase 4 without updating Phase 3 code. Breaking change to core data structure." --tag root_cause --phase rehydration

# STEP 4: Decide on fix strategy
# Option 1: Rollback Phase 4 changes
# Option 2: Update Phase 3 code (better - forward fix)
# Option 3: Make change backward compatible

python acms_lite.py store "DECISION: Make CRSScore struct change backward compatible by using optional fields with default values." --tag decision --phase rehydration

# STEP 5: Implement fix
# Make intent_score optional with default None
# Update all usages to handle None case

python acms_lite.py store "FIX: Made CRSScore.intent_score optional (default None). Updated all usage sites to handle None. Maintains backward compatibility." --tag fix --phase rehydration

# STEP 6: Retest both phases
pytest tests/integration/test_core_logic.py -v
# All tests PASSED ✅

pytest tests/integration/test_rehydration.py -v
# All tests PASSED ✅

# STEP 7: Store successful fix
python acms_lite.py store "REGRESSION FIXED: Both Phase 3 and Phase 4 tests passing. Backward compatibility maintained." --tag fix_verified --phase rehydration

# ✅ NOW SAFE TO PROCEED
```

### **Integration Break Protocol:**

```python
def handle_integration_break(new_phase, broken_phase, test_name):
    """Protocol when new code breaks old code."""
    
    # 1. Store regression
    subprocess.run([
        "python", "acms_lite.py", "store",
        f"REGRESSION: {new_phase} broke {broken_phase} test: {test_name}",
        "--tag", "regression",
        "--phase", new_phase
    ])
    
    # 2. Query for recent changes
    recent_changes = subprocess.run([
        "python", "acms_lite.py", "list",
        "--phase", new_phase,
        "--tag", "implementation",
        "--limit", "10"
    ], capture_output=True, text=True)
    
    print(f"\n🚨 REGRESSION DETECTED")
    print(f"   New phase: {new_phase}")
    print(f"   Broken phase: {broken_phase}")
    print(f"   Failed test: {test_name}")
    print("\nRecent changes in new phase:")
    print(recent_changes.stdout)
    
    # 3. STOP - Must fix regression
    print("\n🚨 STOP: Fix regression before proceeding")
    print("\nOptions:")
    print("1. Rollback breaking change (if not critical)")
    print("2. Forward fix (update broken code)")
    print("3. Make change backward compatible (preferred)")
    print("\nRequired steps:")
    print("1. Identify which recent change caused regression")
    print("2. Store root cause")
    print("3. Choose fix strategy")
    print("4. Store decision")
    print("5. Implement fix")
    print("6. Retest BOTH phases")
    print("7. Store fix verification")
    
    sys.exit(1)  # STOP execution
```

---

## 🚨 QUALITY GATE 4: PERFORMANCE MISSES

### **When Performance Targets Not Met:**

```bash
# Running performance tests for API
pytest tests/performance/test_api_performance.py -v

# OUTPUT:
# ✅ test_get_memory_latency: 45ms p95 (target: < 50ms) PASSED
# ❌ test_query_endpoint_latency: 3200ms p95 (target: < 2000ms) FAILED
# ✅ test_throughput: 120 req/sec (target: > 100) PASSED

# ⚠️ PERFORMANCE MISS - STOP AND OPTIMIZE

# STEP 1: Store performance miss
python acms_lite.py store "PERFORMANCE MISS: Query endpoint p95=3200ms, target=2000ms. 60% over target." --tag performance_issue --phase api

# STEP 2: Profile to find bottleneck
# Run profiler on query endpoint
python scripts/profile_query.py

# OUTPUT:
# Total: 3200ms
#   - Weaviate search: 150ms
#   - CRS calculation: 2800ms (BOTTLENECK!)
#   - Hybrid scoring: 200ms
#   - Token selection: 50ms

# STEP 3: Store root cause
python acms_lite.py store "ROOT CAUSE: Query endpoint slow because CRS calculation taking 2800ms. Calculating CRS for all 50 candidates serially." --tag root_cause --phase api

# STEP 4: Query for optimization strategies
python acms_lite.py query "CRS optimization"
python acms_lite.py query "batch calculation"

# Found from Phase 3: "OPTIMIZATION: Numpy vectorization for batch CRS, 10x speedup"

# STEP 5: Apply optimization
# Implement batch CRS calculation for query endpoint

python acms_lite.py store "OPTIMIZATION: Implemented batch CRS calculation for query endpoint using numpy vectorization. Calculate all 50 candidates in single batch." --tag optimization --phase api

# STEP 6: Retest performance
pytest tests/performance/test_api_performance.py::test_query_endpoint_latency -v

# OUTPUT:
# ✅ test_query_endpoint_latency: 1800ms p95 (target: < 2000ms) PASSED

# STEP 7: Store success
python acms_lite.py store "PERFORMANCE FIXED: Query endpoint now 1800ms p95, under 2000ms target. 44% improvement from batch CRS." --tag performance --phase api

# ✅ NOW SAFE TO PROCEED
```

### **Performance Miss Protocol:**

```python
def handle_performance_miss(test_name, actual, target, unit="ms"):
    """Protocol when performance targets not met."""
    
    # Calculate how far off
    percent_over = ((actual - target) / target) * 100
    
    # 1. Store performance issue
    subprocess.run([
        "python", "acms_lite.py", "store",
        f"PERFORMANCE MISS: {test_name} = {actual}{unit}, target < {target}{unit}. {percent_over:.0f}% over target.",
        "--tag", "performance_issue",
        "--phase", get_current_phase()
    ])
    
    # 2. STOP if significantly over target (>20%)
    if percent_over > 20:
        print(f"\n⚠️  PERFORMANCE MISS: {test_name}")
        print(f"   Actual: {actual}{unit}")
        print(f"   Target: < {target}{unit}")
        print(f"   Over by: {percent_over:.0f}%")
        
        # 3. Query for optimization strategies
        print("\n🔍 Checking for optimization strategies...")
        optimizations = subprocess.run([
            "python", "acms_lite.py", "query",
            "optimization",
            "--limit", "10"
        ], capture_output=True, text=True)
        
        if optimizations.stdout:
            print("Found previous optimizations:")
            print(optimizations.stdout)
        
        print("\n🚨 STOP: Optimize before proceeding")
        print("\nRequired steps:")
        print("1. Profile to identify bottleneck")
        print("2. Store root cause")
        print("3. Query for similar optimizations")
        print("4. Implement optimization")
        print("5. Store optimization details")
        print("6. Retest performance")
        print("7. Repeat until target met")
        
        sys.exit(1)  # STOP execution
    else:
        # Close enough (within 20%), but note for future optimization
        print(f"\n⚠️  Performance slightly over target ({percent_over:.0f}%), but acceptable")
        return True
```

---

## 🔄 ROLLBACK PROTOCOL

### **When to Rollback:**

1. **Multiple test failures** after implementing a feature
2. **Checkpoint fails** due to new phase
3. **Critical bug** discovered in new code
4. **Architecture decision** proves wrong

### **How to Rollback:**

```bash
# Scenario: Phase 4 implementation has fundamental issues
# Decision: Rollback Phase 4, fix design, re-implement

# STEP 1: Store rollback decision
python acms_lite.py store "ROLLBACK DECISION: Rolling back Phase 4 (Rehydration) due to fundamental architecture issue with intent classification. Will redesign and re-implement." --tag rollback --phase rehydration

# STEP 2: Identify what to rollback
python acms_lite.py list --phase rehydration --tag implementation --limit 50
# Lists all Phase 4 implementation changes

# STEP 3: Git rollback (if using version control)
git log --oneline --since="2 days ago"  # Find Phase 4 commits
git revert <commit-hash-range>  # Revert Phase 4 commits

# OR: Manual rollback
# Delete files created in Phase 4
# Restore modified files to Phase 3 state

# STEP 4: Verify Phase 3 still works
pytest tests/integration/test_core_logic.py -v
python tests/checkpoint_validation.py 3
# Both should PASS ✅

# STEP 5: Store rollback completion
python acms_lite.py store "ROLLBACK COMPLETE: Phase 4 rolled back. Phase 3 verified working. Ready to redesign Phase 4." --tag rollback_complete --phase rehydration

# STEP 6: Store new design decisions
python acms_lite.py store "NEW DESIGN: Intent classification will use simpler keyword-based approach instead of ML model. Rationale: ML model adds complexity and latency without clear benefit for MVP." --tag architecture --phase rehydration

# STEP 7: Re-implement Phase 4 with new design
# Follow normal Phase 4 workflow with new approach

# STEP 8: Store successful re-implementation
python acms_lite.py store "Phase 4 re-implemented successfully with keyword-based intent classification. All tests passing." --tag milestone --phase rehydration
```

---

## 🎯 DECISION TREE: WHEN TO STOP AND FIX

```
┌─────────────────────────────────────────────────────┐
│ AFTER EVERY CODE CHANGE                             │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
       ┌─────────────────────┐
       │  Run Unit Tests     │
       └──────────┬──────────┘
                  │
         ┌────────┴────────┐
         │  All Pass?      │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │                 │
         NO                YES
         │                 │
         ▼                 ▼
    ┌────────┐      ┌──────────┐
    │ STOP   │      │ Continue │
    │ FIX    │      └────┬─────┘
    │ RETEST │           │
    └────────┘           ▼
                  ┌─────────────────────┐
                  │ Run Integration     │
                  │ Tests               │
                  └──────────┬──────────┘
                             │
                    ┌────────┴────────┐
                    │  All Pass?      │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    NO                YES
                    │                 │
                    ▼                 ▼
               ┌────────┐      ┌──────────────┐
               │ STOP   │      │ At Phase End?│
               │ FIX    │      └──────┬───────┘
               │ RETEST │             │
               └────────┘    ┌────────┴────────┐
                             │                 │
                             YES               NO
                             │                 │
                             ▼                 ▼
                    ┌─────────────────┐  ┌──────────┐
                    │ Run Checkpoint  │  │ Continue │
                    └────────┬────────┘  │ Building │
                             │           └──────────┘
                    ┌────────┴────────┐
                    │  Pass?          │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    NO                YES
                    │                 │
                    ▼                 ▼
               ┌────────┐      ┌──────────────┐
               │ STOP   │      │ Generate     │
               │ FIX    │      │ Phase Summary│
               │ RETEST │      └──────┬───────┘
               └────────┘             │
                                      ▼
                              ┌───────────────┐
                              │ User Reviews  │
                              │ & Approves    │
                              └───────┬───────┘
                                      │
                                      ▼
                              ┌───────────────┐
                              │ Proceed to    │
                              │ Next Phase    │
                              └───────────────┘
```

---

## 🔍 CONTINUOUS VALIDATION CHECKS

### **Run After Every Significant Change:**

```bash
#!/bin/bash
# validate_change.sh - Run after every significant code change

echo "🔍 Validating recent changes..."

# 1. Run affected unit tests
echo "▶ Running unit tests..."
pytest tests/unit/ -v --tb=short

if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed - STOPPING"
    python acms_lite.py store "Unit tests failed after recent change" --tag test_failure
    exit 1
fi

# 2. Run integration tests
echo "▶ Running integration tests..."
pytest tests/integration/ -v --tb=short

if [ $? -ne 0 ]; then
    echo "❌ Integration tests failed - STOPPING"
    python acms_lite.py store "Integration tests failed - possible regression" --tag regression
    exit 1
fi

# 3. Check code quality
echo "▶ Checking code quality..."
pylint src/ --fail-under=8.0

if [ $? -ne 0 ]; then
    echo "⚠️  Code quality below threshold"
    python acms_lite.py store "Code quality check failed" --tag quality_issue
fi

# 4. Check ACMS-Lite health
echo "▶ Checking ACMS-Lite health..."
python acms_lite.py stats > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "🚨 ACMS-Lite unhealthy - CRITICAL"
    exit 1
fi

# 5. Check for inconsistencies
echo "▶ Checking for inconsistencies..."
python scripts/check_consistency.py

echo "✅ All validations passed"
python acms_lite.py store "Validation passed after recent change" --tag validation
```

---

## 📊 SELF-CORRECTION METRICS

### **Track These Metrics:**

```bash
# After each phase, generate metrics

# File: scripts/generate_metrics.py
"""Generate self-correction metrics."""

import subprocess
import json

def get_metrics():
    """Calculate self-correction metrics."""
    
    # Query ACMS-Lite for all events
    test_failures = count_memories("test_failure")
    fixes = count_memories("fix")
    regressions = count_memories("regression")
    optimizations = count_memories("optimization")
    rollbacks = count_memories("rollback")
    
    # Calculate metrics
    metrics = {
        "total_test_failures": test_failures,
        "total_fixes": fixes,
        "total_regressions": regressions,
        "total_optimizations": optimizations,
        "total_rollbacks": rollbacks,
        "fix_rate": fixes / test_failures if test_failures > 0 else 1.0,
        "regression_rate": regressions / fixes if fixes > 0 else 0.0,
    }
    
    return metrics

def count_memories(tag):
    """Count memories with specific tag."""
    result = subprocess.run([
        "python", "acms_lite.py", "list",
        "--tag", tag,
        "--limit", "1000"
    ], capture_output=True, text=True)
    
    return len([line for line in result.stdout.split('\n') if line.startswith('#')])

# Generate report
metrics = get_metrics()
print("\n📊 Self-Correction Metrics:")
print(f"   Test Failures: {metrics['total_test_failures']}")
print(f"   Fixes Applied: {metrics['total_fixes']}")
print(f"   Regressions: {metrics['total_regressions']}")
print(f"   Optimizations: {metrics['total_optimizations']}")
print(f"   Rollbacks: {metrics['total_rollbacks']}")
print(f"   Fix Rate: {metrics['fix_rate']:.1%}")
print(f"   Regression Rate: {metrics['regression_rate']:.1%}")
```

### **Quality Indicators:**

- **Fix Rate > 95%**: Good (most issues get fixed)
- **Regression Rate < 10%**: Good (fixes don't break things)
- **Rollbacks < 2**: Good (few major redesigns needed)
- **Test Failures trending down**: Good (learning from mistakes)

---

## ✅ SUMMARY: CLAUDE CODE BEHAVIOR

### **What Claude Code Does:**

1. **Query ACMS-Lite before every decision** - Maintain consistency
2. **Store every decision, implementation, error, fix** - Build complete history
3. **Run tests immediately after changes** - Catch issues early
4. **STOP when tests fail** - No proceeding with broken code
5. **STOP when checkpoints fail** - No skipping validation
6. **STOP when regressions occur** - Fix immediately
7. **STOP when performance misses** - Optimize before continuing
8. **Use rollback when needed** - Don't be afraid to backtrack
9. **Generate metrics** - Track self-correction effectiveness
10. **Generate phase summaries** - Keep user informed

### **What Claude Code Never Does:**

- ❌ Proceed with failing tests
- ❌ Skip checkpoints
- ❌ Ignore regressions
- ❌ Accept performance misses
- ❌ Make decisions without querying ACMS-Lite
- ❌ Implement without storing decisions
- ❌ Use workarounds instead of proper fixes

---

## 🎯 FINAL PROTOCOL

```
FOR EVERY ACTION:
  1. Query ACMS-Lite for context
  2. Make decision based on context
  3. Store decision in ACMS-Lite
  4. Implement with TDD
  5. Run tests
  6. IF tests fail:
       STOP
       Analyze root cause
       Store root cause
       Fix
       Store fix
       Retest
       GOTO 5
  7. Store successful implementation
  8. Continue

AT END OF PHASE:
  1. Run checkpoint
  2. IF checkpoint fails:
       STOP
       Analyze failures
       Fix all failures
       Store fixes
       Retest checkpoint
       GOTO 1
  3. Generate phase summary
  4. Wait for user approval
  5. Proceed to next phase
```

This creates a **self-healing build system** that catches and fixes issues immediately! 🎯

---

**With this protocol, Claude Code will build ACMS with minimal user intervention while maintaining the highest quality standards.** 🚀
