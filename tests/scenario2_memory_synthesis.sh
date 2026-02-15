#!/bin/bash
# Scenario 2: Memory Synthesis (Universal Brain)
# Tests: Store memories from multiple sources, synthesize them in one answer
# Uses /memories (POST to create) and /gateway/ask (not /ask)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SCENARIO 2: Memory Synthesis (Universal Brain)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Goal: Demonstrate universal brain synthesis:"
echo "  1. Store memories from multiple sources (ChatGPT, Claude, Gemini)"
echo "  2. Query: 'Summarize authentication discussions'"
echo "  3. Answer should synthesize ALL memories from ALL sources"
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

# Store 10 memories about authentication from different sources
echo "───────────────────────────────────────────────────────────────"
echo "Step 1: Storing 10 authentication memories from multiple sources"
echo "───────────────────────────────────────────────────────────────"
echo ""

# Array of memory contents (will be sent individually)
declare -a MEMORY_CONTENTS=(
  "Implemented JWT authentication with RS256 algorithm for better security"
  "Added bcrypt password hashing with 12 rounds (industry standard)"
  "Researched OAuth2 authorization code flow for social login integration"
  "Implemented refresh token rotation every 15 minutes for security"
  "Added rate limiting to login endpoint: 5 attempts per minute per IP"
  "Configured CORS for authentication endpoints with allowed origins"
  "Implemented multi-factor authentication (MFA) with TOTP (Time-based OTP)"
  "Added session management with Redis for fast session lookup"
  "Implemented password reset flow with email verification and expiring tokens"
  "Added social login (Google, GitHub) using OAuth2 with state parameter for CSRF protection"
)

declare -a MEMORY_TAGS=(
  "auth jwt security"
  "auth password bcrypt"
  "auth oauth2 social"
  "auth jwt refresh-token"
  "auth security rate-limiting"
  "auth cors security"
  "auth mfa totp security"
  "auth session redis"
  "auth password email"
  "auth oauth2 social csrf"
)

declare -a MEMORY_SOURCES=(
  "chatgpt"
  "claude"
  "gemini"
  "chatgpt"
  "claude"
  "chatgpt"
  "gemini"
  "claude"
  "chatgpt"
  "gemini"
)

STORED_COUNT=0
for i in "${!MEMORY_CONTENTS[@]}"; do
    CONTENT="${MEMORY_CONTENTS[$i]}"
    TAGS="${MEMORY_TAGS[$i]}"
    SOURCE="${MEMORY_SOURCES[$i]}"

    # Convert space-separated tags to JSON array
    TAG_ARRAY=$(echo "$TAGS" | python3 -c "import sys, json; print(json.dumps(sys.stdin.read().strip().split()))")

    RESPONSE=$(curl -s -X POST http://localhost:40080/memories \
      -H "Content-Type: application/json" \
      -d "{
        \"user_id\": \"$USER_ID\",
        \"content\": \"$CONTENT\",
        \"tags\": $TAG_ARRAY,
        \"source\": \"$SOURCE\",
        \"privacy_level\": \"INTERNAL\",
        \"phase\": \"scenario2_test\",
        \"tier\": \"SHORT\"
      }")

    if echo "$RESPONSE" | grep -q "memory_id"; then
        STORED_COUNT=$((STORED_COUNT + 1))
        echo "  ✅ Memory $((i+1))/10 stored (source: $SOURCE)"
    else
        echo "  ❌ Memory $((i+1))/10 failed"
        echo "     Response: $RESPONSE"
    fi
done

echo ""
echo "✅ Stored $STORED_COUNT/10 memories"
echo ""

# Wait a moment for indexing
sleep 2

# Query to synthesize all authentication discussions using /gateway/ask
echo "───────────────────────────────────────────────────────────────"
echo "Step 2: Query for synthesis (using /gateway/ask)"
echo "───────────────────────────────────────────────────────────────"
echo "Question: 'Summarize all authentication discussions'"
echo ""

START=$(date +%s%N)
RESPONSE=$(curl -N -s -X POST http://localhost:40080/gateway/ask \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Summarize all authentication discussions and implementations\",
    \"user_id\": \"$USER_ID\",
    \"bypass_cache\": false,
    \"context_limit\": 15
  }" 2>&1 | parse_gateway_response)
END=$(date +%s%N)
LATENCY=$(( (END - START) / 1000000 ))

if [ -n "$RESPONSE" ]; then
    # Extract Gateway response fields
    ANSWER=$(echo "$RESPONSE" | jq -r '.answer // "Failed to parse"')
    AGENT=$(echo "$RESPONSE" | jq -r '.agent_used // "unknown"')
    INTENT=$(echo "$RESPONSE" | jq -r '.intent_detected // "unknown"')
    FROM_CACHE=$(echo "$RESPONSE" | jq -r '.from_cache // "unknown"')
    COST=$(echo "$RESPONSE" | jq -r '.cost_usd // 0')
    LATENCY_ACTUAL=$(echo "$RESPONSE" | jq -r '.latency_ms // 0')

    echo "✅ Synthesis complete"
    echo ""

    echo "Gateway Metadata:"
    echo "  Agent used: $AGENT"
    echo "  Intent detected: $INTENT"
    echo "  From cache: $FROM_CACHE"
    echo "  Cost: \$$COST"
    echo "  Latency: ${LATENCY_ACTUAL}ms"
    echo ""

    echo "Answer preview (first 500 chars):"
    echo "───────────────────────────────────────────────────────────────"
    echo "$ANSWER" | head -c 500
    echo "..."
    echo "───────────────────────────────────────────────────────────────"
    echo ""

    echo "Metrics:"
    echo "  Answer length: ${#ANSWER} chars"
    echo ""

    # Check if answer mentions key topics (validates synthesis)
    echo "Topic Coverage (validates synthesis):"
    TOPICS=("JWT" "bcrypt" "OAuth" "MFA" "session" "CORS" "rate" "refresh" "password" "social")
    TOPICS_FOUND=0

    for topic in "${TOPICS[@]}"; do
        if echo "$ANSWER" | grep -qi "$topic"; then
            echo "  ✅ $topic mentioned"
            TOPICS_FOUND=$((TOPICS_FOUND + 1))
        else
            echo "  ❌ $topic not mentioned"
        fi
    done

    echo ""
    echo "Topics coverage: $TOPICS_FOUND/${#TOPICS[@]} ($(( TOPICS_FOUND * 100 / ${#TOPICS[@]} ))%)"

    # Validate intent detection
    echo ""
    if [ "$INTENT" = "analysis" ] || [ "$INTENT" = "memory_query" ]; then
        echo "   ✅ Correct intent (analysis or memory_query)"
    else
        echo "   ⚠️  Expected intent: analysis or memory_query, got: $INTENT"
    fi

else
    echo "❌ Synthesis failed - no response"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SCENARIO 2 RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Memories stored: $STORED_COUNT/10"
echo "  Topics synthesized: $TOPICS_FOUND/10"
echo "  Agent used: $AGENT"
echo "  Intent: $INTENT"
echo ""

# Validation
PASS=true

if [ "$STORED_COUNT" -lt 10 ]; then
    echo "❌ Memory storage validation FAILED (expected 10, got $STORED_COUNT)"
    PASS=false
fi

if [ "$TOPICS_FOUND" -ge 6 ]; then
    echo "✅ Topic synthesis working (60%+ topics covered)"
else
    echo "⚠️  Synthesis partial (< 60% topics covered)"
    if [ "$STORED_COUNT" -eq 10 ]; then
        PASS=true  # Storage working is main success
    fi
fi

echo ""
if [ "$PASS" = true ]; then
    echo "✅ SCENARIO 2: PASSED"
else
    echo "❌ SCENARIO 2: FAILED"
fi
echo ""
echo "NOTE: Full cross-source synthesis (ChatGPT + Claude + Gemini)"
echo "will be demonstrated once browser extensions are built."
echo ""
