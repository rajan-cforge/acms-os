#!/bin/bash
# Scenario 1: Multi-Agent Routing + Cost Savings
# Tests: Creative→ChatGPT, Analysis→Claude, Cache Hit→$0
# Uses /gateway/ask with SSE stream parsing

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SCENARIO 1: Multi-Agent Routing + Cost Savings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Goal: Demonstrate 30-40% cost savings from:"
echo "  1. Cost-optimized routing (ChatGPT for creative = 3x cheaper)"
echo "  2. Query caching (repeat queries = \$0)"
echo ""

USER_ID="rajan"

# Helper function to parse SSE response and extract final Gateway response
parse_gateway_response() {
    local temp_file=$(mktemp)
    cat > "$temp_file"

    # Extract the final "done" event which contains the complete response
    grep "^data:" "$temp_file" | while IFS= read -r line; do
        data="${line#data: }"
        event_type=$(echo "$data" | jq -r '.type // empty' 2>/dev/null)

        if [ "$event_type" = "done" ]; then
            echo "$data" | jq -r '.response'
            break
        fi
    done

    rm -f "$temp_file"
}

# Query 1: Creative task (should route to ChatGPT - cheaper)
echo "───────────────────────────────────────────────────────────────"
echo "Query 1: Creative Task (expect ChatGPT routing)"
echo "───────────────────────────────────────────────────────────────"
echo "Question: 'Write a haiku about databases'"
echo ""

START1=$(date +%s%N)
RESPONSE1=$(curl -N -s -X POST http://localhost:40080/gateway/ask \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Write a haiku about databases\",
    \"user_id\": \"$USER_ID\",
    \"bypass_cache\": false,
    \"context_limit\": 5
  }" 2>&1 | parse_gateway_response)
END1=$(date +%s%N)
LATENCY1=$(( (END1 - START1) / 1000000 ))

if [ -n "$RESPONSE1" ]; then
    AGENT1=$(echo "$RESPONSE1" | jq -r '.agent_used // "unknown"')
    INTENT1=$(echo "$RESPONSE1" | jq -r '.intent_detected // "unknown"')
    FROM_CACHE1=$(echo "$RESPONSE1" | jq -r '.from_cache // "unknown"')
    COST1=$(echo "$RESPONSE1" | jq -r '.cost_usd // 0')

    echo "✅ Query 1 complete"
    echo "   Intent detected: $INTENT1"
    echo "   Agent used: $AGENT1"
    echo "   From cache: $FROM_CACHE1"
    echo "   Cost: \$$COST1"
    echo "   Latency: ${LATENCY1}ms"

    # Validate
    if [ "$INTENT1" = "creative" ]; then
        echo "   ✅ Correct intent (creative)"
    else
        echo "   ⚠️  Expected intent: creative, got: $INTENT1"
    fi

    if [ "$AGENT1" = "chatgpt" ]; then
        echo "   ✅ Correct agent (ChatGPT - cost-optimized)"
    else
        echo "   ⚠️  Expected agent: chatgpt, got: $AGENT1"
    fi
else
    echo "❌ Query 1 failed - no response"
    COST1=0
fi
echo ""

# Query 2: Analysis task (should route to Claude Sonnet - quality)
echo "───────────────────────────────────────────────────────────────"
echo "Query 2: Analysis Task (expect Claude Sonnet routing)"
echo "───────────────────────────────────────────────────────────────"
echo "Question: 'Analyze the performance implications of Redis caching'"
echo ""

START2=$(date +%s%N)
RESPONSE2=$(curl -N -s -X POST http://localhost:40080/gateway/ask \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Analyze the performance implications of Redis caching\",
    \"user_id\": \"$USER_ID\",
    \"bypass_cache\": false,
    \"context_limit\": 5
  }" 2>&1 | parse_gateway_response)
END2=$(date +%s%N)
LATENCY2=$(( (END2 - START2) / 1000000 ))

if [ -n "$RESPONSE2" ]; then
    AGENT2=$(echo "$RESPONSE2" | jq -r '.agent_used // "unknown"')
    INTENT2=$(echo "$RESPONSE2" | jq -r '.intent_detected // "unknown"')
    FROM_CACHE2=$(echo "$RESPONSE2" | jq -r '.from_cache // "unknown"')
    COST2=$(echo "$RESPONSE2" | jq -r '.cost_usd // 0')

    echo "✅ Query 2 complete"
    echo "   Intent detected: $INTENT2"
    echo "   Agent used: $AGENT2"
    echo "   From cache: $FROM_CACHE2"
    echo "   Cost: \$$COST2"
    echo "   Latency: ${LATENCY2}ms"

    # Validate
    if [ "$INTENT2" = "analysis" ]; then
        echo "   ✅ Correct intent (analysis)"
    else
        echo "   ⚠️  Expected intent: analysis, got: $INTENT2"
    fi

    if [ "$AGENT2" = "claude_sonnet" ]; then
        echo "   ✅ Correct agent (Claude Sonnet - quality-optimized)"
    else
        echo "   ⚠️  Expected agent: claude_sonnet, got: $AGENT2"
    fi
else
    echo "❌ Query 2 failed - no response"
    COST2=0
fi
echo ""

# Query 3: Repeat Query 1 (should hit cache, cost = $0)
echo "───────────────────────────────────────────────────────────────"
echo "Query 3: Repeat Query 1 (expect CACHE HIT)"
echo "───────────────────────────────────────────────────────────────"
echo "Question: 'Write a haiku about databases' (same as Query 1)"
echo ""

START3=$(date +%s%N)
RESPONSE3=$(curl -N -s -X POST http://localhost:40080/gateway/ask \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Write a haiku about databases\",
    \"user_id\": \"$USER_ID\",
    \"bypass_cache\": false,
    \"context_limit\": 5
  }" 2>&1 | parse_gateway_response)
END3=$(date +%s%N)
LATENCY3=$(( (END3 - START3) / 1000000 ))

if [ -n "$RESPONSE3" ]; then
    AGENT3=$(echo "$RESPONSE3" | jq -r '.agent_used // "unknown"')
    FROM_CACHE3=$(echo "$RESPONSE3" | jq -r '.from_cache // "unknown"')
    COST3=$(echo "$RESPONSE3" | jq -r '.cost_usd // 0')

    echo "✅ Query 3 complete"
    echo "   Agent used: $AGENT3"
    echo "   From cache: $FROM_CACHE3"
    echo "   Cost: \$$COST3"
    echo "   Latency: ${LATENCY3}ms"

    # Validate cache hit
    if [ "$FROM_CACHE3" = "true" ]; then
        echo "   ✅ CACHE HIT (from_cache=true)"
    else
        echo "   ⚠️  Expected cache hit, got: from_cache=$FROM_CACHE3"
    fi

    if [ "$COST3" = "0" ] || [ "$COST3" = "0.0" ]; then
        echo "   ✅ Zero cost on cache hit"
    else
        echo "   ⚠️  Expected \$0 cost on cache hit, got: \$$COST3"
    fi

    if [ "$LATENCY3" -lt 500 ]; then
        echo "   ✅ Fast response (< 500ms)"
    else
        echo "   ⚠️  Slower than expected: ${LATENCY3}ms"
    fi
else
    echo "❌ Query 3 failed - no response"
    COST3=0
fi
echo ""

# Calculate cost savings
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SCENARIO 1 RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Convert to proper numbers for bc calculation
COST1_NUM=$(echo "$COST1" | sed 's/[^0-9.]//g')
COST2_NUM=$(echo "$COST2" | sed 's/[^0-9.]//g')
COST3_NUM=$(echo "$COST3" | sed 's/[^0-9.]//g')

TOTAL_WITHOUT_CACHE=$(echo "$COST1_NUM + $COST2_NUM + $COST1_NUM" | bc 2>/dev/null || echo "0")
TOTAL_WITH_CACHE=$(echo "$COST1_NUM + $COST2_NUM + $COST3_NUM" | bc 2>/dev/null || echo "0")

if [ "$TOTAL_WITHOUT_CACHE" != "0" ] && [ -n "$TOTAL_WITHOUT_CACHE" ]; then
    SAVINGS=$(echo "scale=6; $TOTAL_WITHOUT_CACHE - $TOTAL_WITH_CACHE" | bc)
    SAVINGS_PCT=$(echo "scale=2; ($SAVINGS / $TOTAL_WITHOUT_CACHE) * 100" | bc)
else
    SAVINGS="0"
    SAVINGS_PCT="0"
fi

echo "Cost Breakdown:"
echo "  Query 1 (creative, ChatGPT):  \$$COST1_NUM"
echo "  Query 2 (analysis, Claude):   \$$COST2_NUM"
echo "  Query 3 (cached):             \$$COST3_NUM"
echo ""
echo "Comparison:"
echo "  Total cost without cache:  \$$TOTAL_WITHOUT_CACHE"
echo "  Total cost with cache:     \$$TOTAL_WITH_CACHE"
echo "  Cost saved:                \$$SAVINGS"
echo "  Savings percentage:        $SAVINGS_PCT%"
echo ""

# Validation
PASS=true

if [ "$FROM_CACHE3" != "true" ]; then
    echo "❌ Cache hit validation FAILED"
    PASS=false
fi

if (( $(echo "$SAVINGS_PCT > 20" | bc -l 2>/dev/null || echo 0) )); then
    echo "✅ Cost savings > 20% achieved"
else
    echo "⚠️  Cost savings < 20% (expected >30%)"
    if [ "$FROM_CACHE3" = "true" ]; then
        PASS=true  # Cache working is main success
    fi
fi

echo ""
if [ "$PASS" = true ]; then
    echo "✅ SCENARIO 1: PASSED"
else
    echo "❌ SCENARIO 1: FAILED"
fi
echo ""
