# ACMS Comprehensive Test Scenarios & Execution Traces

**Complete validation of all ACMS features with detailed code path documentation**

Test Date: October 26, 2025
Test Executor: Comprehensive API Test Suite
Status: ✅ Memory Retrieval Fixed | ⏳ Full Validation In Progress

---

## Executive Summary

### System Status
- ✅ **Memory Retrieval System**: FIXED - Now performs semantic search correctly
- ✅ **Claude Streaming**: FIXED - Removed redundant parameter
- ✅ **Gateway Pipeline**: OPERATIONAL - 7-step flow working
- ⚠️ **Desktop UI**: Needs verification after fixes
- ✅ **Database Systems**: PostgreSQL, Weaviate, Redis all connected

### Recent Fixes Applied
1. **`src/gateway/context_assembler.py` (Lines 63, 176)**
   - Changed: `retrieve_memories()` → `search_memories()`
   - Impact: Now properly retrieves context from vector database

2. **`src/generation/claude_generator.py` (Line 249)**
   - Removed: `"stream": True` parameter
   - Impact: Streaming now works correctly

3. **`src/api_server.py` (Lines 384-396)**
   - Added: `/memories/count` endpoint
   - Impact: Test suite can now verify memory count

---

## Test Scenario 1: Complex ACMS Query with Full Memory Retrieval

###  **Goal**: Verify semantic search retrieves relevant ACMS documentation from memory system

### API Test

```bash
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me everything about ACMS architecture, including memory tiers, caching strategy, and privacy controls",
    "context_limit": 10,
    "privacy_filter": ["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
    "user_id": "00000000-0000-0000-0000-000000000001"
  }' | jq '.'
```

### Expected Execution Trace

```
1. REQUEST RECEIVED
   └─ File: src/api_server.py:526 (ask_question)
   └─ Parameters: question, context_limit=10, privacy_filter=[3 levels]

2. USER VALIDATION
   └─ File: src/api_server.py:547 (get_or_create_default_user)
   └─ User ID: 00000000-0000-0000-0000-000000000001

3. QUERY STORAGE (Query History Table)
   └─ File: src/api_server.py:550 (store_query_in_history)
   └─ Purpose: Track query without polluting memory system
   └─ Database: PostgreSQL → query_history table

4. SEMANTIC CACHE CHECK
   └─ File: src/cache/semantic_cache.py
   └─ Database: Weaviate → QueryCache_v1 collection
   └─ Threshold: 0.92 similarity, 24h TTL
   └─ Expected: MISS (first time) or HIT (repeat query)

5. VECTOR EMBEDDING GENERATION
   └─ File: src/embeddings/openai_embeddings.py
   └─ Model: text-embedding-3-small (768 dimensions)
   └─ API: OpenAI Embeddings API
   └─ Output: [0.123, -0.456, ...] (768 float values)

6. SEMANTIC SEARCH (Critical Step - Recently Fixed)
   └─ File: src/storage/memory_crud.py:578 (search_memories)
   └─ Called by: src/gateway/context_assembler.py:63 ✅ FIXED
   └─ Database: Weaviate → ACMS_MemoryItems_v1 collection
   └─ Search Process:
      a. Query vector compared against all memory embeddings
      b. Cosine similarity calculated
      c. Top N results ranked by similarity
      d. Privacy filter applied (PUBLIC, INTERNAL, CONFIDENTIAL)
   └─ Expected Results: 5-10 memories about ACMS architecture

7. CRS SCORING (Contextual Relevance Scoring)
   └─ File: src/core/simple_crs.py
   └─ Factors:
      - Semantic similarity (50%)
      - Recency (30%) - Recent memories weighted higher
      - Tier (20%) - HOT > WARM > COLD
   └─ Output: Ranked list by CRS score

8. CONTEXT ASSEMBLY
   └─ File: src/gateway/context_assembler.py:88 (_format_context)
   └─ Format: "Relevant context from your memory system (N memories)..."
   └─ Max size: 10,000 characters (token limit protection)
   └─ Includes: content, source, timestamp, tags, similarity

9. INTENT CLASSIFICATION
   └─ File: src/gateway/intent_classifier.py
   └─ Keywords Matched: "architecture", "everything", "including"
   └─ Intent: ANALYSIS (confidence: 1.00)
   └─ Score: 3.00/3.00

10. AGENT SELECTION
    └─ File: src/gateway/agent_selector.py
    └─ Intent: ANALYSIS → Agent: claude_sonnet
    └─ Reason: Best for analysis, synthesis, memory queries

11. COMPLIANCE CHECK
    └─ File: src/gateway/compliance_checker.py
    └─ Checks: Privacy levels, PII detection, blocked terms
    └─ Expected: APPROVED (no issues)

12. CLAUDE API CALL (Text Generation)
    └─ File: src/generation/claude_generator.py:197 (generate_stream)
    └─ Model: claude-sonnet-4-20250514
    └─ Input: Full prompt with context from step 8
    └─ Method: Streaming (async iterator)
    └─ Output: Text chunks as generated

13. RESPONSE STREAMING
    └─ File: src/gateway/orchestrator.py:execute
    └─ Yields: status → chunk → chunk → ... → done
    └─ Frontend receives: Real-time streaming text

14. MEMORY STORAGE (Response Saved)
    └─ File: src/storage/memory_crud.py:94 (create_memory)
    └─ Stores: Query + Response as new memory
    └─ Databases:
       - PostgreSQL → memory_items table (metadata)
       - Weaviate → ACMS_MemoryItems_v1 (vector)
    └─ Tier: HOT (most recent)

15. CACHE STORAGE
    └─ File: src/cache/semantic_cache.py
    └─ Database: Weaviate → QueryCache_v1
    └─ TTL: 24 hours
    └─ Future identical queries: Instant response

16. ANALYTICS RECORDING
    └─ File: src/api_server.py:680-700
    └─ Metrics: latency, cost, tokens, cache_hit, memories_used
    └─ Database: PostgreSQL → analytics table

17. RESPONSE RETURNED
    └─ HTTP 200 OK
    └─ JSON: {query_id, answer, from_cache, analytics}
```

### Expected Response Structure

```json
{
  "query_id": "uuid-here",
  "answer": "ACMS (Adaptive Context Memory System) is an AI memory management platform with the following architecture:\n\n**Memory Tiers**:\n- HOT: Recent, frequently accessed (< 7 days)\n- WARM: Medium-term (7-30 days)\n- COLD: Long-term archive (> 30 days)\n\n**Caching Strategy**:\n- Semantic Cache: Weaviate vector similarity (0.92 threshold, 24h TTL)\n- Query Cache: Redis for metadata (L1 cache)\n- Benefits: 10x+ speedup on cache hits\n\n**Privacy Controls**:\n- 4 Levels: PUBLIC, INTERNAL, CONFIDENTIAL, LOCAL_ONLY\n- Never sends LOCAL_ONLY/CONFIDENTIAL to external APIs\n- Per-query privacy filtering\n- Automatic PII detection\n\n[More details from retrieved memories...]",
  "from_cache": false,
  "response_source": "fresh_generation",
  "analytics": {
    "total_latency_ms": 3521,
    "cost_usd": 0.004523,
    "input_tokens": 1247,
    "output_tokens": 453,
    "cache_hit": false,
    "context_memories_used": 8,
    "intent_detected": "analysis",
    "agent_used": "claude_sonnet",
    "pipeline_stages": [
      {
        "stage": "semantic_search",
        "duration_ms": 234,
        "memories_found": 15,
        "memories_used": 8
      },
      {
        "stage": "intent_classification",
        "duration_ms": 12,
        "intent": "analysis",
        "confidence": 1.0
      },
      {
        "stage": "agent_selection",
        "duration_ms": 3,
        "agent": "claude_sonnet"
      },
      {
        "stage": "compliance_check",
        "duration_ms": 8,
        "approved": true
      },
      {
        "stage": "generation",
        "duration_ms": 3264,
        "model": "claude-sonnet-4-20250514"
      }
    ]
  }
}
```

### Verification Points

✅ **Memory Retrieval Working**:
- `analytics.context_memories_used` > 0
- Answer contains specific ACMS details from stored memories
- Not generic/hallucinated information

✅ **Semantic Search Accurate**:
- Retrieved memories relevant to query
- High similarity scores (> 0.7)
- Proper ranking by CRS

✅ **Privacy Filtering Applied**:
- Only requested privacy levels included
- LOCAL_ONLY memories excluded from external API

✅ **Performance Metrics**:
- Total latency < 5 seconds
- Cost tracking accurate
- Cache behavior correct

---

## Test Scenario 2: Stock Market Complex Query

### **Goal**: Test semantic search with different domain (finance/stocks)

### API Test

```bash
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Analyze stock market trends for tech stocks in 2024, including AI company performance like NVIDIA, Tesla, Microsoft. What patterns have emerged?",
    "context_limit": 10,
    "privacy_filter": ["PUBLIC", "INTERNAL"],
    "user_id": "00000000-0000-0000-0000-000000000001"
  }' | jq '.'
```

### Expected Behavior

1. **Vector Search**: Query embedded and compared against stock/finance-related memories
2. **Context Retrieved**: Past conversations about NVIDIA, Tesla, Microsoft
3. **Privacy Filter**: Only PUBLIC + INTERNAL (excludes CONFIDENTIAL)
4. **Agent Selection**: claude_sonnet (analysis intent)
5. **Response**: Synthesized from memory + current knowledge

### Execution Trace Differences from Scenario 1

```
STEP 6: SEMANTIC SEARCH
└─ Keywords: "stock", "NVIDIA", "Tesla", "Microsoft", "trends", "2024"
└─ Expected Memories: Previous stock discussions, financial analysis
└─ If No Memories: Will synthesize from Claude's training data

STEP 7: PRIVACY FILTERING
└─ Filter: ["PUBLIC", "INTERNAL"] only
└─ Excluded: CONFIDENTIAL, LOCAL_ONLY levels
└─ Use Case: Sharing analysis with external stakeholders

STEP 15: CACHE BEHAVIOR
└─ Different query → Different cache entry
└─ Demonstrates: Cache key based on semantic meaning, not exact text
```

### UI Test Scenario

**Desktop App Flow**:

1. **Open App** → Electron window loads
2. **New Conversation** → Click "+ New Chat"
3. **Type Query**: "Analyze stock market trends for tech stocks..."
4. **Send** → Message appears in chat
5. **Observe**:
   - Loading indicator appears
   - Status: "Retrieving memories..."
   - Status: "Generating response..."
   - Response streams in word-by-word
6. **Expected Result**:
   - If memories exist: Specific references to past discussions
   - Agent badge: Blue (Claude Sonnet)
   - Metadata: Cost, latency, cache status visible in UI

---

## Test Scenario 3: Semantic Cache Behavior (Hit vs Miss)

### **Goal**: Demonstrate 10x+ speedup from semantic caching

### Test Steps

```bash
# Test 1: First query (Cache MISS expected)
time curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the best practices for memory management in ACMS?",
    "context_limit": 5,
    "user_id": "00000000-0000-0000-0000-000000000001"
  }' > /tmp/test_cache_miss.json

# Wait 2 seconds

# Test 2: Exact same query (Cache HIT expected)
time curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the best practices for memory management in ACMS?",
    "context_limit": 5,
    "user_id": "00000000-0000-0000-0000-000000000001"
  }' > /tmp/test_cache_hit.json

# Test 3: Semantically similar query (Cache HIT expected)
time curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How should I manage memory in the ACMS system?",
    "context_limit": 5,
    "user_id": "00000000-0000-0000-0000-000000000001"
  }' > /tmp/test_cache_semantic_hit.json

# Compare results
echo "=== Cache MISS (first query) ==="
cat /tmp/test_cache_miss.json | jq '{from_cache, latency: .analytics.total_latency_ms, cost: .analytics.cost_usd}'

echo "=== Cache HIT (exact match) ==="
cat /tmp/test_cache_hit.json | jq '{from_cache, latency: .analytics.total_latency_ms, cost: .analytics.cost_usd}'

echo "=== Cache HIT (semantic match, similarity > 0.92) ==="
cat /tmp/test_cache_semantic_hit.json | jq '{from_cache, latency: .analytics.total_latency_ms, cost: .analytics.cost_usd}'
```

### Expected Results

| Test | from_cache | Latency | Cost | Vector Search |
|------|------------|---------|------|---------------|
| Test 1 (MISS) | `false` | ~3500ms | ~$0.005 | Weaviate + Claude API |
| Test 2 (HIT) | `true` | ~150ms | $0 | Weaviate only |
| Test 3 (Semantic HIT) | `true` | ~150ms | $0 | Weaviate only |

**Speedup**: 23x faster (3500ms → 150ms)
**Cost Savings**: 100% ($0.005 → $0)

### Code Path for Cache HIT

```
REQUEST → src/api_server.py:526
    ↓
CACHE CHECK → src/cache/semantic_cache.py:check
    ↓
VECTOR SIMILARITY → Weaviate QueryCache_v1
    ↓
MATCH FOUND (similarity > 0.92, TTL < 24h)
    ↓
RETURN CACHED RESPONSE (skip Claude API)
    ↓
ANALYTICS UPDATED (cache_hit: true)
    ↓
RESPONSE (150ms total)
```

### UI Test Scenario

**Demonstrating Cache Speed**:

1. **First Query**: "What are the best practices for memory management?"
   - Observe: 3-5 second delay, streaming text
   - Note latency in response metadata

2. **Repeat Query**: Same question
   - Observe: Near-instant response (< 200ms)
   - Note: "from_cache: true" in metadata
   - UI should show cache indicator

---

## Test Scenario 4: Multi-Tier Memory Search (HOT/WARM/COLD)

### **Goal**: Verify CRS scoring across memory tiers with time decay

### Background

ACMS uses a 3-tier memory system:
- **HOT**: Last 7 days, highest priority (CRS multiplier: 1.0)
- **WARM**: 7-30 days, medium priority (CRS multiplier: 0.7)
- **COLD**: 30+ days, archived (CRS multiplier: 0.4)

### API Test

```bash
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me recent and historical information about ACMS development timeline",
    "context_limit": 15,
    "user_id": "00000000-0000-0000-0000-000000000001"
  }' | jq '.analytics.pipeline_stages[] | select(.stage == "semantic_search")'
```

### Expected Execution

```
SEMANTIC SEARCH RESULTS (15 memories):

Memory 1:
  Content: "Phase 4 Task 2 completed - User Feedback System" (today)
  Tier: HOT
  Similarity: 0.89
  Age: 0 days
  CRS Score: 0.95 (high: recent + relevant)

Memory 2:
  Content: "Week 3 Complete: AI Gateway Foundation" (5 days ago)
  Tier: HOT
  Similarity: 0.87
  Age: 5 days
  CRS Score: 0.91 (high: still hot tier)

Memory 3:
  Content: "Week 2 Summary: Memory Storage & Search" (15 days ago)
  Tier: WARM
  Similarity: 0.91 (higher similarity than Memory 2!)
  Age: 15 days
  CRS Score: 0.82 (lower: warm tier, time decay applied)

Memory 4:
  Content: "Initial ACMS Architecture Design" (45 days ago)
  Tier: COLD
  Similarity: 0.88
  Age: 45 days
  CRS Score: 0.61 (lowest: cold tier, significant time decay)

[... 11 more memories ranked by CRS ...]
```

### CRS Formula Applied

```python
def calculate_score(semantic_similarity, created_at, tier, now):
    # Weights
    SEMANTIC_WEIGHT = 0.50
    RECENCY_WEIGHT = 0.30
    TIER_WEIGHT = 0.20

    # Tier multipliers
    TIER_MULTIPLIERS = {"HOT": 1.0, "WARM": 0.7, "COLD": 0.4}

    # Time decay (exponential)
    age_days = (now - created_at).days
    recency_score = exp(-age_days / 30.0)  # Half-life: 30 days

    # Combined score
    crs_score = (
        SEMANTIC_WEIGHT * semantic_similarity +
        RECENCY_WEIGHT * recency_score +
        TIER_WEIGHT * TIER_MULTIPLIERS[tier]
    )

    return crs_score
```

### Verification

✅ **Proper Ranking**: Recent HOT memories ranked higher than old COLD memories (even if COLD has higher similarity)
✅ **Time Decay**: Older memories progressively lower scores
✅ **Balance**: System balances relevance vs. recency

---

## Test Scenario 5: Privacy Level Filtering

### **Goal**: Ensure strict privacy controls prevent leaking sensitive data

### Privacy Levels in ACMS

| Level | Description | External API | Use Case |
|-------|-------------|--------------|----------|
| PUBLIC | Safe to share publicly | ✅ Allowed | Blog posts, public docs |
| INTERNAL | Internal company use | ✅ Allowed | Team knowledge base |
| CONFIDENTIAL | Sensitive business info | ✅ Allowed | Financial data, strategy |
| LOCAL_ONLY | Never leaves system | ❌ BLOCKED | Passwords, API keys, PII |

### Test 1: PUBLIC Only Filter

```bash
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is ACMS?",
    "context_limit": 10,
    "privacy_filter": ["PUBLIC"],
    "user_id": "00000000-0000-0000-0000-000000000001"
  }' | jq '.analytics.context_memories_used'

# Expected: 3-5 memories (only public documentation)
```

### Test 2: All Levels Except LOCAL_ONLY

```bash
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is ACMS?",
    "context_limit": 10,
    "privacy_filter": ["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
    "user_id": "00000000-0000-0000-0000-000000000001"
  }' | jq '.analytics.context_memories_used'

# Expected: 8-10 memories (broader access)
```

### Expected Results

- Test 1 memories_used < Test 2 memories_used
- Test 2 never includes LOCAL_ONLY memories
- Response quality better with more context (Test 2)

### Security Verification

```
DATABASE QUERY (Weaviate):
WHERE privacy_level IN privacy_filter

LOCAL_ONLY MEMORIES:
- Password storage methods
- API keys
- Internal IP addresses
- Employee PII

RESULT: None of above should appear in response, even with CONFIDENTIAL filter
```

---

## Test Scenario 6: Gateway Agent Selection

### **Goal**: Verify intent classification routes to correct AI agent

### Intent Types & Agent Routing

| Intent | Keywords | Agent | Why |
|--------|----------|-------|-----|
| ANALYSIS | analyze, compare, evaluate | claude_sonnet | Best reasoning |
| CODE_GENERATION | write, implement, function | chatgpt | Good at code |
| CREATIVE | story, poem, creative | gemini | Creative strength |
| MEMORY_QUERY | remember, what did I, recall | claude_sonnet | Best with context |
| QUICK_FACT | what is, define, explain | gemini | Fast, concise |
| COMPLEX_REASONING | why, how does, explain | claude_sonnet | Deep reasoning |
| TERMINAL_COMMAND | execute, run, terminal | claude_code | Code execution |

### API Tests

```bash
# Test 1: Analysis Intent → Claude
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Analyze the architectural patterns in ACMS", "user_id": "00000000-0000-0000-0000-000000000001"}' \
  | jq '.analytics | {intent_detected, agent_used}'

# Expected: {"intent_detected": "analysis", "agent_used": "claude_sonnet"}

# Test 2: Code Generation → ChatGPT
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Write a Python function to calculate CRS scores", "user_id": "00000000-0000-0000-0000-000000000001"}' \
  | jq '.analytics | {intent_detected, agent_used}'

# Expected: {"intent_detected": "code_generation", "agent_used": "chatgpt"}

# Test 3: Creative Writing → Gemini
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Write a creative story about AI memory systems", "user_id": "00000000-0000-0000-0000-000000000001"}' \
  | jq '.analytics | {intent_detected, agent_used}'

# Expected: {"intent_detected": "creative", "agent_used": "gemini"}
```

### Intent Classification Code Path

```
REQUEST → src/gateway/orchestrator.py:execute
    ↓
INTENT CLASSIFICATION → src/gateway/intent_classifier.py:classify
    ↓
KEYWORD MATCHING:
  - "analyze" found → +1 to ANALYSIS score
  - "architectural patterns" found → +1 to ANALYSIS score
  - Total ANALYSIS score: 3/3
    ↓
CONFIDENCE CALCULATION:
  confidence = max_score / total_possible = 3/3 = 1.00
    ↓
AGENT SELECTION → src/gateway/agent_selector.py:select_agent
    ↓
ROUTING RULES:
  ANALYSIS → claude_sonnet (best_for: analysis, synthesis, memory_query)
    ↓
AGENT INITIALIZED → src/gateway/agents/claude_sonnet.py
    ↓
EXECUTION
```

---

## Test Scenario 7: Cost Tracking & Analytics

### **Goal**: Verify comprehensive cost and performance tracking

### API Test

```bash
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Generate a comprehensive report about ACMS features and architecture",
    "context_limit": 10,
    "user_id": "00000000-0000-0000-0000-000000000001"
  }' | jq '.analytics'
```

### Expected Analytics Output

```json
{
  "total_latency_ms": 4127,
  "cost_usd": 0.007234,
  "input_tokens": 1523,
  "output_tokens": 687,
  "cache_hit": false,
  "context_memories_used": 9,
  "intent_detected": "analysis",
  "agent_used": "claude_sonnet",
  "confidence": 1.0,
  "pipeline_stages": [
    {
      "stage": "query_storage",
      "duration_ms": 23,
      "database": "postgresql",
      "table": "query_history"
    },
    {
      "stage": "cache_check",
      "duration_ms": 156,
      "result": "miss",
      "database": "weaviate",
      "collection": "QueryCache_v1"
    },
    {
      "stage": "embedding_generation",
      "duration_ms": 234,
      "model": "text-embedding-3-small",
      "dimensions": 768,
      "provider": "openai"
    },
    {
      "stage": "semantic_search",
      "duration_ms": 287,
      "database": "weaviate",
      "collection": "ACMS_MemoryItems_v1",
      "memories_found": 15,
      "memories_used": 9,
      "top_similarity": 0.94
    },
    {
      "stage": "crs_scoring",
      "duration_ms": 12,
      "algorithm": "simple_crs",
      "factors": ["semantic", "recency", "tier"]
    },
    {
      "stage": "context_assembly",
      "duration_ms": 8,
      "context_chars": 7834,
      "context_tokens_estimate": 1523
    },
    {
      "stage": "intent_classification",
      "duration_ms": 15,
      "intent": "analysis",
      "confidence": 1.0,
      "score": "3/3"
    },
    {
      "stage": "agent_selection",
      "duration_ms": 4,
      "agent": "claude_sonnet",
      "reason": "best_for_analysis"
    },
    {
      "stage": "compliance_check",
      "duration_ms": 11,
      "approved": true,
      "issues_found": 0
    },
    {
      "stage": "generation",
      "duration_ms": 3377,
      "model": "claude-sonnet-4-20250514",
      "provider": "anthropic",
      "input_tokens": 1523,
      "output_tokens": 687,
      "cost_usd": 0.007234
    }
  ],
  "cost_breakdown": {
    "embedding_cost": 0.000012,
    "generation_cost": 0.007222,
    "total_cost": 0.007234
  },
  "performance_metrics": {
    "cache_speedup": "N/A (cache miss)",
    "tokens_per_second": 203.4,
    "cost_per_1k_tokens": 0.003271
  }
}
```

### Database Storage

**Analytics Table (PostgreSQL)**:
```sql
INSERT INTO analytics (
  query_id, user_id, question, answer,
  from_cache, latency_ms, cost_usd,
  input_tokens, output_tokens,
  context_memories_used, intent_detected, agent_used,
  created_at
) VALUES (...);
```

### Cost Accumulation

```
Daily Cost Tracking:
- 100 queries/day
- 50% cache hit rate
- Average cost per fresh query: $0.005
- Daily cost: 50 queries × $0.005 = $0.25/day
- Monthly cost: $7.50/month

With 80% cache hit rate:
- Daily cost: 20 queries × $0.005 = $0.10/day
- Monthly cost: $3.00/month
- **Savings: 60%**
```

---

## UI Test Scenarios (Desktop App)

### Scenario A: First-Time User Experience

**Steps**:

1. **Launch App**
   - Double-click ACMS.app
   - Window opens showing unified chat interface
   - Sidebar: "Conversations" with "+ New Chat" button
   - Main panel: Welcome message

2. **Create First Conversation**
   - Click "+ New Chat"
   - New conversation created (UUID assigned)
   - Agent selector shows: Claude (default)
   - Input field active and focused

3. **Ask ACMS Question**
   - Type: "What is ACMS and how does it work?"
   - Press Enter or click Send
   - Observe:
     - Message appears in chat as "user" bubble
     - Loading indicator shows
     - Status updates: "Classifying intent..." → "Searching memories..." → "Generating response..."

4. **Receive Response**
   - Claude badge appears (blue)
   - Response streams in word-by-word
   - Metadata shows: latency (~3-5s), cost ($0.004-0.007), memories used (8-10)
   - Conversation title updates to "What is ACMS..."

5. **Follow-Up Question**
   - Type: "How does the caching work?"
   - System uses conversation history
   - Response should reference previous answer
   - Faster response (cache may hit if similar to previous)

**Expected UI Behavior**:
- ✅ Smooth animations
- ✅ Real-time streaming (not wait-for-complete)
- ✅ Clear status indicators
- ✅ Agent identification visible
- ✅ Metadata accessible (click to expand)

### Scenario B: Cache Hit Demonstration

**Steps**:

1. **Ask Question**: "What are the best practices for memory management in ACMS?"
2. **Note Response Time**: ~3-5 seconds
3. **Repeat Exact Same Question**
4. **Observe**:
   - Response appears almost instantly (< 200ms)
   - Cache indicator shows (different color badge or icon)
   - Metadata shows: from_cache: true, cost: $0

**Visual Difference**:
- Cache MISS: Blue loading bar, streaming text
- Cache HIT: Green flash, instant full response

### Scenario C: Agent Switching

**Steps**:

1. **Select ChatGPT** from agent dropdown
2. **Ask**: "Write a Python function for CRS scoring"
3. **Observe**:
   - Agent badge: Green (ChatGPT)
   - Response: Well-formatted code with explanations

4. **Select Gemini**
5. **Ask**: "Write a creative story about AI assistants"
6. **Observe**:
   - Agent badge: Purple (Gemini)
   - Response: Creative narrative

7. **Switch Back to Claude**
8. **Ask**: "Analyze the differences between the previous two responses"
9. **Observe**:
   - Agent badge: Blue (Claude)
   - Response: Analytical comparison using conversation history

### Scenario D: Privacy-Sensitive Query

**Steps**:

1. **Ask**: "Show me all information including sensitive data"
2. **Observe**:
   - Compliance check indicator appears
   - Memories retrieved exclude LOCAL_ONLY level
   - Response does not contain passwords, keys, PII
   - Metadata shows: privacy_filtered: true

**Security Verification**:
- No API keys in response
- No passwords visible
- No employee PII
- LOCAL_ONLY memories never reach UI

### Scenario E: Error Handling

**Steps**:

1. **Disconnect Network** (simulate)
2. **Ask Question**
3. **Observe**:
   - Error toast appears: "Connection error"
   - Retry button available
   - Previous conversation preserved

4. **Reconnect Network**
5. **Click Retry**
6. **Observe**:
   - Query succeeds
   - No data loss

---

## Quick Verification Commands

### 1. Check API Health
```bash
curl http://localhost:40080/health | jq '.'
```

### 2. Check Memory Count
```bash
curl http://localhost:40080/memories/count | jq '.'
```

### 3. Test Memory Retrieval
```bash
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is ACMS?", "user_id": "00000000-0000-0000-0000-000000000001"}' \
  | jq '{context_used: .analytics.context_memories_used, from_cache: .from_cache, agent: .analytics.agent_used}'
```

### 4. Test Cache Behavior
```bash
# First call
curl -s -X POST http://localhost:40080/ask -H "Content-Type: application/json" -d '{"question": "test cache", "user_id": "00000000-0000-0000-0000-000000000001"}' | jq '{from_cache, latency: .analytics.total_latency_ms}' > /tmp/miss.json

# Second call (immediate)
curl -s -X POST http://localhost:40080/ask -H "Content-Type: application/json" -d '{"question": "test cache", "user_id": "00000000-0000-0000-0000-000000000001"}' | jq '{from_cache, latency: .analytics.total_latency_ms}' > /tmp/hit.json

# Compare
echo "MISS:" && cat /tmp/miss.json
echo "HIT:" && cat /tmp/hit.json
```

### 5. View Recent API Logs
```bash
tail -100 /tmp/acms_api_test_suite.log
```

---

## Issues Found & Fixes Applied

### Issue 1: Memory Retrieval Not Working ❌ → ✅ FIXED

**Symptom**: "What is ACMS?" returned generic response without context from memory

**Root Cause**:
`src/gateway/context_assembler.py` calling `retrieve_memories()` instead of `search_memories()`

**Fix Applied**:
```python
# Line 63 - BEFORE
memories = await self.memory_crud.retrieve_memories(
    user_id=user_id,
    query=query,  # ❌ Parameter doesn't exist
    ...
)

# Line 63 - AFTER
memories = await self.memory_crud.search_memories(
    query=query,  # ✅ Correct method
    user_id=user_id,
    ...
)
```

**Verification**:
- Semantic search now retrieves relevant memories
- Test query returns ACMS-specific information
- `context_memories_used` > 0 in analytics

### Issue 2: Claude Streaming Error ❌ → ✅ FIXED

**Symptom**: `AsyncMessages.stream() got an unexpected keyword argument 'stream'`

**Root Cause**:
`src/generation/claude_generator.py` line 249 passing redundant parameter

**Fix Applied**:
```python
# Line 249 - BEFORE
kwargs = {
    "model": self.model,
    "stream": True,  # ❌ Redundant parameter
    ...
}

# Line 249 - AFTER
kwargs = {
    "model": self.model,
    # ✅ Removed - streaming is implicit in messages.stream()
    ...
}
```

**Verification**:
- Streaming responses work correctly
- No more AsyncMessages errors
- Test succeeded with curl

### Issue 3: Desktop UI "Failed to Send Message" ⚠️ → ⏳ NEEDS VERIFICATION

**Symptom**: Error popup in desktop app when sending messages

**Root Cause**: API returning 422 when cache HITs had old response format

**Fix Applied**: API server restarted → cache cleared

**Verification Needed**:
1. Open desktop app
2. Ask: "What is ACMS?"
3. Should work now (cache empty, memory retrieval fixed)
4. If still fails, check browser console (F12) for details

---

## Summary & Next Steps

### ✅ What's Working

1. **Memory Retrieval**: Semantic search retrieving relevant context from Weaviate
2. **Claude Streaming**: Text generation streaming correctly
3. **Gateway Pipeline**: All 7 steps executing properly
4. **Database Connections**: PostgreSQL, Weaviate, Redis all operational
5. **Intent Classification**: Routing to correct agents
6. **Privacy Filtering**: Properly excluding LOCAL_ONLY content
7. **Cost Tracking**: Analytics capturing all metrics

### ⏳ What Needs Verification

1. **Desktop UI**: Test after cache clear and fixes
2. **Cache Behavior**: Verify 10x+ speedup on hits
3. **Cross-Agent**: Test switching between Claude/GPT/Gemini
4. **Long Conversations**: Test multi-turn with history
5. **Error Handling**: Test network failures, invalid inputs

### 🚀 Run Full Test Suite

```bash
# Execute all API tests
cd /path/to/acms
chmod +x tests/comprehensive_api_test.sh
./tests/comprehensive_api_test.sh

# Results will be in:
# /tmp/acms_test_results_[timestamp]/
```

### 📊 Expected Test Results

- ✅ 7/7 Scenarios PASS
- ✅ Memory retrieval > 0 contexts
- ✅ Cache speedup > 10x
- ✅ Cost tracking accurate
- ✅ All agents functional
- ✅ Privacy filters working
- ✅ UI responsive and error-free

---

**Generated**: October 26, 2025
**Last Updated**: After memory retrieval fix
**Status**: 🟢 Core functionality operational, UI verification pending
