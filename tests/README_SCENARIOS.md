# ACMS Gateway Test Scenarios

**Created**: October 19, 2025
**Purpose**: End-to-end validation of AI Gateway functionality

## 🎯 Overview

Three comprehensive test scenarios to validate your ACMS v2.0 Gateway:

1. **Scenario 1**: Multi-Agent Routing + Cost Savings (30-40% reduction)
2. **Scenario 2**: Memory Synthesis (Universal Brain across sources)
3. **Scenario 3**: Security Enforcement (blocks API keys, warns on dangerous commands)

---

## 📍 Test Script Locations

All scripts are in `/path/to/acms/tests/`:

```bash
tests/scenario1_cost_savings.sh          # Multi-agent routing + caching
tests/scenario2_memory_synthesis.sh      # Universal brain synthesis
tests/scenario3_security_enforcement.sh  # Security compliance
```

---

## 🚀 How to Run

### Prerequisites

1. **Start API Server** (if not already running):
   ```bash
   cd /path/to/acms
   source venv/bin/activate
   source .env
   python3 src/api_server.py
   ```

   Server should be running on http://localhost:40080

2. **Verify Services**:
   ```bash
   curl -s http://localhost:40080/health | python3 -m json.tool
   ```

   Expected: All services show "status": "healthy"

### Run Individual Scenarios

```bash
cd /path/to/acms

# Scenario 1: Cost savings test (5-10 minutes)
./tests/scenario1_cost_savings.sh

# Scenario 2: Memory synthesis test (3-5 minutes)
./tests/scenario2_memory_synthesis.sh

# Scenario 3: Security enforcement test (2-3 minutes)
./tests/scenario3_security_enforcement.sh
```

### Run All Scenarios

```bash
cd /path/to/acms

for script in tests/scenario*.sh; do
    echo ""
    echo "========================================"
    echo "Running: $script"
    echo "========================================"
    $script
    echo ""
done
```

---

## 📊 Scenario 1: Multi-Agent Routing + Cost Savings

**File**: `tests/scenario1_cost_savings.sh`

### What It Tests

1. **Creative Query** → Routes to ChatGPT ($10/1M input = 3x cheaper)
2. **Analysis Query** → Routes to Claude Sonnet ($3/1M input = quality)
3. **Repeat Query 1** → Cache hit (cost = $0)

### Expected Results

```
✅ Query 1 complete
   Intent detected: creative
   Agent used: chatgpt
   From cache: false
   Cost: $0.000XXX

✅ Query 2 complete
   Intent detected: analysis
   Agent used: claude_sonnet
   From cache: false
   Cost: $0.000XXX

✅ Query 3 complete (repeat of Query 1)
   Agent used: chatgpt
   From cache: true
   Cost: $0.000000
   Latency: <500ms

RESULTS:
  Cost saved: $0.000XXX
  Savings percentage: 30-40%

✅ SCENARIO 1: PASSED
```

### Success Criteria

- ✅ Query 1 uses ChatGPT (creative intent)
- ✅ Query 2 uses Claude Sonnet (analysis intent)
- ✅ Query 3 hits cache (from_cache=true)
- ✅ Cache hit cost = $0
- ✅ Cache hit latency < 500ms
- ✅ Overall savings > 20%

---

## 📊 Scenario 2: Memory Synthesis (Universal Brain)

**File**: `tests/scenario2_memory_synthesis.sh`

### What It Tests

1. **Store 10 memories** from different sources (ChatGPT, Claude, Gemini)
   - JWT authentication
   - bcrypt password hashing
   - OAuth2 flow
   - Refresh token rotation
   - Rate limiting
   - CORS configuration
   - MFA with TOTP
   - Session management
   - Password reset flow
   - Social login

2. **Query**: "Summarize all authentication discussions"

3. **Validation**: Answer should synthesize ALL 10 memories

### Expected Results

```
✅ Stored 10/10 memories

✅ Synthesis complete

Gateway Metadata:
  Agent used: claude_sonnet
  Intent detected: analysis
  From cache: false
  Cost: $0.000XXX

Answer preview:
─────────────────────────────────────────────────────────
Based on the authentication discussions, the system implements...
[mentions JWT, bcrypt, OAuth2, MFA, session, CORS, rate limiting, etc.]
...

Topic Coverage:
  ✅ JWT mentioned
  ✅ bcrypt mentioned
  ✅ OAuth mentioned
  ✅ MFA mentioned
  ✅ session mentioned
  ✅ CORS mentioned
  ✅ rate mentioned
  ✅ refresh mentioned
  ✅ password mentioned
  ✅ social mentioned

Topics coverage: 10/10 (100%)

✅ SCENARIO 2: PASSED
```

### Success Criteria

- ✅ All 10 memories stored successfully
- ✅ Query uses /gateway/ask (not /ask)
- ✅ Answer synthesizes 60%+ topics (6+ out of 10)
- ✅ Intent detected as analysis or memory_query
- ✅ Response shows Gateway metadata

---

## 📊 Scenario 3: Security Enforcement

**File**: `tests/scenario3_security_enforcement.sh`

### What It Tests

1. **Test 1**: Query with API key → BLOCKED (approved=false, cost=$0)
2. **Test 2**: Query with "rm -rf /" → WARNED (approved=true, issues present)
3. **Test 3**: Normal query → APPROVED (no issues)

### Expected Results

```
Test 1: API Key Detection
✅ Response received
   Event type: error
   Approved: false
   ✅ CORRECTLY BLOCKED
   ✅ Cost: $0 (query not executed)

Test 2: Dangerous Command Detection
✅ Response received (query executed with warning)
   Agent used: claude_sonnet
   Cost: $0.000XXX
   ✅ APPROVED (query executed despite dangerous pattern)
   ⚠️  Note: Compliance warnings may have been issued

Test 3: Normal Query
✅ Response received
   Agent used: claude_sonnet
   Intent detected: analysis
   Cost: $0.000XXX
   ✅ APPROVED (no issues, query executed successfully)

SCENARIO 3 RESULTS:
  ✅ Test 1: API key BLOCKED
  ✅ Test 2: Dangerous command handled
  ✅ Test 3: Normal query APPROVED

✅ SCENARIO 3: PASSED
```

### Success Criteria

- ✅ API key query blocked (approved=false)
- ✅ API key query cost = $0
- ✅ Dangerous command warned or blocked
- ✅ Normal query approved and executed

---

## 🔧 Troubleshooting

### Issue: "Connection refused" errors

**Fix**: Start API server
```bash
source venv/bin/activate
source .env
python3 src/api_server.py
```

### Issue: "jq: command not found"

**Fix**: Install jq
```bash
brew install jq
```

### Issue: Scripts show permission denied

**Fix**: Make scripts executable
```bash
chmod +x tests/scenario*.sh
```

### Issue: Memory storage fails

**Check**: PostgreSQL and Weaviate are running
```bash
docker ps | grep -E "postgres|weaviate"
```

### Issue: Gateway returns errors

**Check**: .env has API keys
```bash
grep -E "OPENAI_API_KEY|ANTHROPIC_API_KEY" .env
```

---

## 📈 What These Tests Validate

### ✅ Multi-Agent Routing (Scenario 1)
- Intent classification (7 types)
- Cost-optimized agent selection
- Query result caching (Redis)
- Cost savings measurement

### ✅ Universal Brain (Scenario 2)
- Memory storage across sources
- Cross-source context retrieval
- Semantic synthesis
- Context assembly

### ✅ Security Compliance (Scenario 3)
- API key detection and blocking
- Dangerous command warnings
- Query approval workflow
- Zero-cost blocking

---

## 🎯 Next Steps After Tests Pass

### Option A: Build Browser Extensions (8 hours)
Build ChatGPT extension to see the full "aha moment":
- Code in Claude Code
- Switch to ChatGPT
- ChatGPT ALREADY KNOWS your context 🤯

### Option B: Continue Gateway Development (12 hours)
Complete Week 3 tasks:
- Task 8: Agent execution optimization
- Task 9: Performance testing
- Task 10: Gateway metrics dashboard

### Option C: Start Week 4: MCP Integration (14 hours)
Connect Claude Code as MCP client:
- Claude Code ↔ ACMS MCP server
- Automatic context storage
- Context-aware responses

---

## 📝 Script Implementation Details

All scripts use the same patterns:

### SSE Stream Parsing
```bash
parse_gateway_response() {
    local temp_file=$(mktemp)
    cat > "$temp_file"

    grep "^data:" "$temp_file" | while IFS= read -r line; do
        data="${line#data: }"
        event_type=$(echo "$data" | jq -r '.type // empty')

        if [ "$event_type" = "done" ]; then
            echo "$data" | jq -r '.response'
            break
        fi
    done

    rm -f "$temp_file"
}
```

### Gateway Request Pattern
```bash
curl -N -s -X POST http://localhost:40080/gateway/ask \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"...\",
    \"user_id\": \"rajan\",
    \"bypass_cache\": false,
    \"context_limit\": 5
  }" 2>&1 | parse_gateway_response
```

### Response Validation
```bash
AGENT=$(echo "$RESPONSE" | jq -r '.agent_used // "unknown"')
INTENT=$(echo "$RESPONSE" | jq -r '.intent_detected // "unknown"')
FROM_CACHE=$(echo "$RESPONSE" | jq -r '.from_cache // "unknown"')
COST=$(echo "$RESPONSE" | jq -r '.cost_usd // 0')
```

---

**Ready to test?** Run the scenarios and see your AI Gateway in action! 🚀
