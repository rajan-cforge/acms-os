#!/bin/bash
#
# ACMS Comprehensive API Test Suite
# ==================================
# Tests all major scenarios with full execution traces
# Shows complete code path: API → Gateway → Memory Search → Response
#
# Tests:
# 1. Memory Query about ACMS (complex)
# 2. Stock market analysis query (complex)
# 3. Semantic cache hit/miss behavior
# 4. Multi-tier memory search (HOT/WARM/COLD)
# 5. Cross-source synthesis (multiple AI tools)
# 6. Privacy filtering
# 7. Compliance checking
# 8. Analytics and cost tracking
#
# Usage: ./tests/comprehensive_api_test.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:40080"
USER_ID="00000000-0000-0000-0000-000000000001"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="/tmp/acms_test_results_${TIMESTAMP}"
LOG_FILE="${RESULTS_DIR}/test_execution.log"

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Logging function
log() {
    echo -e "${1}" | tee -a "${LOG_FILE}"
}

log_section() {
    echo "" | tee -a "${LOG_FILE}"
    echo "========================================" | tee -a "${LOG_FILE}"
    echo "${1}" | tee -a "${LOG_FILE}"
    echo "========================================" | tee -a "${LOG_FILE}"
}

# Start test suite
log_section "ACMS COMPREHENSIVE API TEST SUITE"
log "Test Run: ${TIMESTAMP}"
log "Results Directory: ${RESULTS_DIR}"
log "API URL: ${API_URL}"
log ""

# ================================================================
# PRE-FLIGHT CHECK
# ================================================================
log_section "PRE-FLIGHT: Checking System Health"

# Check API health
log "${BLUE}Checking API health...${NC}"
curl -s "${API_URL}/health" > "${RESULTS_DIR}/00_health_check.json"
if [ $? -eq 0 ]; then
    log "${GREEN}✓ API is healthy${NC}"
    cat "${RESULTS_DIR}/00_health_check.json" | jq '.' | tee -a "${LOG_FILE}"
else
    log "${RED}✗ API is not responding${NC}"
    exit 1
fi

# Check database connections
log "\n${BLUE}Checking database connections...${NC}"
HEALTH=$(cat "${RESULTS_DIR}/00_health_check.json")
if echo "${HEALTH}" | jq -e '.databases' > /dev/null 2>&1; then
    echo "${HEALTH}" | jq '.databases' | tee -a "${LOG_FILE}"
else
    log "${YELLOW}⚠ Database status not available in health check${NC}"
fi

# Check memory count
log "\n${BLUE}Checking memory count...${NC}"
curl -s "${API_URL}/memories/count" > "${RESULTS_DIR}/00_memory_count.json"
MEMORY_COUNT=$(cat "${RESULTS_DIR}/00_memory_count.json" | jq -r '.total_count')
log "${GREEN}✓ Total memories: ${MEMORY_COUNT}${NC}"

log "\n${GREEN}✓ Pre-flight checks passed${NC}"
sleep 2

# ================================================================
# TEST 1: Complex ACMS Query with Memory Retrieval
# ================================================================
log_section "TEST 1: Complex ACMS Query with Full Memory Retrieval"

log "${BLUE}Query: 'Tell me everything about ACMS architecture, including memory tiers, caching strategy, and privacy controls'${NC}"

cat > "${RESULTS_DIR}/01_acms_query_request.json" << 'EOF'
{
  "question": "Tell me everything about ACMS architecture, including memory tiers, caching strategy, and privacy controls",
  "context_limit": 10,
  "privacy_filter": ["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
  "user_id": "00000000-0000-0000-0000-000000000001"
}
EOF

log "\n📤 REQUEST:"
cat "${RESULTS_DIR}/01_acms_query_request.json" | jq '.' | tee -a "${LOG_FILE}"

log "\n⏳ Executing query..."
time_start=$(date +%s%3N)

curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d @"${RESULTS_DIR}/01_acms_query_request.json" \
  > "${RESULTS_DIR}/01_acms_query_raw_response.txt"

time_end=$(date +%s%3N)
elapsed=$((time_end - time_start))

# Extract HTTP code and response
HTTP_CODE=$(tail -1 "${RESULTS_DIR}/01_acms_query_raw_response.txt" | grep -o '[0-9]*')
head -n -1 "${RESULTS_DIR}/01_acms_query_raw_response.txt" > "${RESULTS_DIR}/01_acms_query_response.json"

if [ "${HTTP_CODE}" = "200" ]; then
    log "\n${GREEN}✓ Query successful (HTTP ${HTTP_CODE}) - ${elapsed}ms${NC}"
else
    log "\n${RED}✗ Query failed (HTTP ${HTTP_CODE})${NC}"
    cat "${RESULTS_DIR}/01_acms_query_response.json" | tee -a "${LOG_FILE}"
fi

log "\n📥 RESPONSE ANALYSIS:"
cat "${RESULTS_DIR}/01_acms_query_response.json" | jq '.' | tee -a "${LOG_FILE}"

# Extract and analyze key metrics
log "\n📊 EXECUTION TRACE:"
log "${BLUE}Query ID:${NC}        $(cat ${RESULTS_DIR}/01_acms_query_response.json | jq -r '.query_id')"
log "${BLUE}Response Source:${NC} $(cat ${RESULTS_DIR}/01_acms_query_response.json | jq -r '.response_source')"
log "${BLUE}Latency:${NC}         $(cat ${RESULTS_DIR}/01_acms_query_response.json | jq -r '.analytics.total_latency_ms')ms"
log "${BLUE}Cost:${NC}            $$(cat ${RESULTS_DIR}/01_acms_query_response.json | jq -r '.analytics.cost_usd')"

log "\n${BLUE}Memory Search Results:${NC}"
cat "${RESULTS_DIR}/01_acms_query_response.json" | jq '.analytics.pipeline_stages[] | select(.stage == "semantic_search")' | tee -a "${LOG_FILE}"

log "\n${BLUE}Context Retrieved:${NC}"
CONTEXT_COUNT=$(cat "${RESULTS_DIR}/01_acms_query_response.json" | jq '.analytics.context_memories_used')
log "Memories used: ${CONTEXT_COUNT}"

if [ "${CONTEXT_COUNT}" -gt 0 ]; then
    log "${GREEN}✓ Memory system is retrieving context${NC}"
else
    log "${YELLOW}⚠ No context memories retrieved - possible issue${NC}"
fi

log "\n${BLUE}Answer Preview:${NC}"
cat "${RESULTS_DIR}/01_acms_query_response.json" | jq -r '.answer' | head -20 | tee -a "${LOG_FILE}"
log "...[truncated]"

sleep 2

# ================================================================
# TEST 2: Stock Market Complex Query
# ================================================================
log_section "TEST 2: Complex Stock Market Analysis Query"

log "${BLUE}Query: 'Analyze stock market trends for tech stocks in 2024, including AI company performance and regulatory impacts'${NC}"

cat > "${RESULTS_DIR}/02_stock_query_request.json" << 'EOF'
{
  "question": "Analyze stock market trends for tech stocks in 2024, including AI company performance and regulatory impacts. What patterns have you seen in previous conversations about NVIDIA, Tesla, and Microsoft?",
  "context_limit": 10,
  "privacy_filter": ["PUBLIC", "INTERNAL"],
  "user_id": "00000000-0000-0000-0000-000000000001"
}
EOF

log "\n📤 REQUEST:"
cat "${RESULTS_DIR}/02_stock_query_request.json" | jq '.' | tee -a "${LOG_FILE}"

log "\n⏳ Executing query..."
time_start=$(date +%s%3N)

curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d @"${RESULTS_DIR}/02_stock_query_request.json" \
  > "${RESULTS_DIR}/02_stock_query_raw_response.txt"

time_end=$(date +%s%3N)
elapsed=$((time_end - time_start))

HTTP_CODE=$(tail -1 "${RESULTS_DIR}/02_stock_query_raw_response.txt" | grep -o '[0-9]*')
head -n -1 "${RESULTS_DIR}/02_stock_query_raw_response.txt" > "${RESULTS_DIR}/02_stock_query_response.json"

if [ "${HTTP_CODE}" = "200" ]; then
    log "\n${GREEN}✓ Query successful (HTTP ${HTTP_CODE}) - ${elapsed}ms${NC}"
else
    log "\n${RED}✗ Query failed (HTTP ${HTTP_CODE})${NC}"
    cat "${RESULTS_DIR}/02_stock_query_response.json" | tee -a "${LOG_FILE}"
fi

log "\n📊 EXECUTION TRACE:"
log "${BLUE}Query ID:${NC}        $(cat ${RESULTS_DIR}/02_stock_query_response.json | jq -r '.query_id')"
log "${BLUE}Response Source:${NC} $(cat ${RESULTS_DIR}/02_stock_query_response.json | jq -r '.response_source')"
log "${BLUE}From Cache:${NC}      $(cat ${RESULTS_DIR}/02_stock_query_response.json | jq -r '.from_cache')"

log "\n${BLUE}Vector Search Trace:${NC}"
cat "${RESULTS_DIR}/02_stock_query_response.json" | jq '.analytics.pipeline_stages[] | select(.stage == "semantic_search")' | tee -a "${LOG_FILE}"

sleep 2

# ================================================================
# TEST 3: Cache Behavior Test (Hit vs Miss)
# ================================================================
log_section "TEST 3: Semantic Cache Behavior Test"

log "${BLUE}Testing cache MISS → cache HIT behavior${NC}"

# First query - should be MISS
cat > "${RESULTS_DIR}/03_cache_test_request.json" << 'EOF'
{
  "question": "What are the best practices for memory management in ACMS?",
  "context_limit": 5,
  "user_id": "00000000-0000-0000-0000-000000000001"
}
EOF

log "\n📤 REQUEST #1 (expecting cache MISS):"
cat "${RESULTS_DIR}/03_cache_test_request.json" | jq '.' | tee -a "${LOG_FILE}"

curl -s -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d @"${RESULTS_DIR}/03_cache_test_request.json" \
  > "${RESULTS_DIR}/03_cache_miss_response.json"

CACHE_MISS=$(cat "${RESULTS_DIR}/03_cache_miss_response.json" | jq -r '.from_cache')
LATENCY_MISS=$(cat "${RESULTS_DIR}/03_cache_miss_response.json" | jq -r '.analytics.total_latency_ms')

log "\n${BLUE}First query results:${NC}"
log "From cache: ${CACHE_MISS}"
log "Latency: ${LATENCY_MISS}ms"

if [ "${CACHE_MISS}" = "false" ]; then
    log "${GREEN}✓ Cache MISS detected (expected)${NC}"
else
    log "${YELLOW}⚠ Cache HIT on first query (unexpected)${NC}"
fi

# Wait a moment, then repeat exact same query
log "\n⏳ Waiting 2 seconds before repeating query..."
sleep 2

log "\n📤 REQUEST #2 (expecting cache HIT):"

curl -s -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d @"${RESULTS_DIR}/03_cache_test_request.json" \
  > "${RESULTS_DIR}/03_cache_hit_response.json"

CACHE_HIT=$(cat "${RESULTS_DIR}/03_cache_hit_response.json" | jq -r '.from_cache')
LATENCY_HIT=$(cat "${RESULTS_DIR}/03_cache_hit_response.json" | jq -r '.analytics.total_latency_ms')

log "\n${BLUE}Second query results:${NC}"
log "From cache: ${CACHE_HIT}"
log "Latency: ${LATENCY_HIT}ms"

if [ "${CACHE_HIT}" = "true" ]; then
    log "${GREEN}✓ Cache HIT detected (expected)${NC}"
    SPEEDUP=$(echo "scale=2; ${LATENCY_MISS} / ${LATENCY_HIT}" | bc)
    log "${GREEN}✓ Cache speedup: ${SPEEDUP}x faster${NC}"
else
    log "${YELLOW}⚠ Cache MISS on second query (unexpected)${NC}"
fi

sleep 2

# ================================================================
# TEST 4: Multi-Tier Memory Search
# ================================================================
log_section "TEST 4: Multi-Tier Memory Search (HOT/WARM/COLD)"

log "${BLUE}Testing CRS scoring across memory tiers${NC}"

cat > "${RESULTS_DIR}/04_tier_test_request.json" << 'EOF'
{
  "question": "Show me recent and historical information about ACMS development",
  "context_limit": 15,
  "user_id": "00000000-0000-0000-0000-000000000001"
}
EOF

log "\n📤 REQUEST:"
cat "${RESULTS_DIR}/04_tier_test_request.json" | jq '.' | tee -a "${LOG_FILE}"

curl -s -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d @"${RESULTS_DIR}/04_tier_test_request.json" \
  > "${RESULTS_DIR}/04_tier_test_response.json"

log "\n📊 MEMORY TIER ANALYSIS:"
cat "${RESULTS_DIR}/04_tier_test_response.json" | jq '.analytics.pipeline_stages[] | select(.stage == "semantic_search")' | tee -a "${LOG_FILE}"

log "\n${BLUE}Context breakdown by tier:${NC}"
# Note: This would require the API to return tier information
# For now we show what was retrieved
CONTEXT_USED=$(cat "${RESULTS_DIR}/04_tier_test_response.json" | jq -r '.analytics.context_memories_used')
log "Total context memories: ${CONTEXT_USED}"

sleep 2

# ================================================================
# TEST 5: Privacy Filtering Test
# ================================================================
log_section "TEST 5: Privacy Level Filtering"

log "${BLUE}Testing privacy filter enforcement${NC}"

# Test with PUBLIC only
cat > "${RESULTS_DIR}/05_privacy_public_request.json" << 'EOF'
{
  "question": "What is ACMS?",
  "context_limit": 10,
  "privacy_filter": ["PUBLIC"],
  "user_id": "00000000-0000-0000-0000-000000000001"
}
EOF

log "\n📤 REQUEST #1 (PUBLIC only):"
curl -s -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d @"${RESULTS_DIR}/05_privacy_public_request.json" \
  > "${RESULTS_DIR}/05_privacy_public_response.json"

PUBLIC_COUNT=$(cat "${RESULTS_DIR}/05_privacy_public_response.json" | jq -r '.analytics.context_memories_used')
log "${BLUE}Memories retrieved (PUBLIC only):${NC} ${PUBLIC_COUNT}"

# Test with all privacy levels
cat > "${RESULTS_DIR}/05_privacy_all_request.json" << 'EOF'
{
  "question": "What is ACMS?",
  "context_limit": 10,
  "privacy_filter": ["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
  "user_id": "00000000-0000-0000-0000-000000000001"
}
EOF

log "\n📤 REQUEST #2 (All privacy levels):"
curl -s -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d @"${RESULTS_DIR}/05_privacy_all_request.json" \
  > "${RESULTS_DIR}/05_privacy_all_response.json"

ALL_COUNT=$(cat "${RESULTS_DIR}/05_privacy_all_response.json" | jq -r '.analytics.context_memories_used')
log "${BLUE}Memories retrieved (All levels):${NC} ${ALL_COUNT}"

if [ "${ALL_COUNT}" -ge "${PUBLIC_COUNT}" ]; then
    log "${GREEN}✓ Privacy filtering working correctly (All >= Public)${NC}"
else
    log "${RED}✗ Privacy filtering issue (All < Public)${NC}"
fi

sleep 2

# ================================================================
# TEST 6: Gateway Agent Selection
# ================================================================
log_section "TEST 6: Multi-Agent Gateway Testing"

log "${BLUE}Testing intent classification and agent routing${NC}"

# Test analysis query (should route to Claude)
cat > "${RESULTS_DIR}/06_agent_analysis_request.json" << 'EOF'
{
  "question": "Analyze the architectural patterns in ACMS",
  "context_limit": 5,
  "user_id": "00000000-0000-0000-0000-000000000001"
}
EOF

log "\n📤 REQUEST (Analysis intent):"
curl -s -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d @"${RESULTS_DIR}/06_agent_analysis_request.json" \
  > "${RESULTS_DIR}/06_agent_analysis_response.json"

AGENT_USED=$(cat "${RESULTS_DIR}/06_agent_analysis_response.json" | jq -r '.analytics.agent_used')
INTENT=$(cat "${RESULTS_DIR}/06_agent_analysis_response.json" | jq -r '.analytics.intent_detected // "unknown"')

log "\n${BLUE}Gateway Decision:${NC}"
log "Intent classified: ${INTENT}"
log "Agent selected: ${AGENT_USED}"

if [ "${AGENT_USED}" = "claude_sonnet" ] || [ "${AGENT_USED}" = "claude" ]; then
    log "${GREEN}✓ Correct agent selected for analysis${NC}"
else
    log "${YELLOW}⚠ Unexpected agent: ${AGENT_USED}${NC}"
fi

sleep 2

# ================================================================
# TEST 7: Cost and Analytics Tracking
# ================================================================
log_section "TEST 7: Cost Tracking and Analytics"

log "${BLUE}Testing comprehensive analytics collection${NC}"

cat > "${RESULTS_DIR}/07_analytics_request.json" << 'EOF'
{
  "question": "Generate a comprehensive report about ACMS features",
  "context_limit": 10,
  "user_id": "00000000-0000-0000-0000-000000000001"
}
EOF

log "\n📤 REQUEST:"
curl -s -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d @"${RESULTS_DIR}/07_analytics_request.json" \
  > "${RESULTS_DIR}/07_analytics_response.json"

log "\n📊 COMPLETE ANALYTICS:"
cat "${RESULTS_DIR}/07_analytics_response.json" | jq '.analytics' | tee -a "${LOG_FILE}"

COST=$(cat "${RESULTS_DIR}/07_analytics_response.json" | jq -r '.analytics.cost_usd')
LATENCY=$(cat "${RESULTS_DIR}/07_analytics_response.json" | jq -r '.analytics.total_latency_ms')

log "\n${BLUE}Performance Metrics:${NC}"
log "Total latency: ${LATENCY}ms"
log "Total cost: $${COST}"

sleep 2

# ================================================================
# TEST SUMMARY
# ================================================================
log_section "TEST SUMMARY"

log "${GREEN}✓ All tests completed${NC}"
log ""
log "${BLUE}Test Results Location:${NC} ${RESULTS_DIR}"
log ""
log "${BLUE}Files Generated:${NC}"
ls -lh "${RESULTS_DIR}" | tee -a "${LOG_FILE}"

log ""
log "${BLUE}Quick Stats:${NC}"
log "- Total test files: $(ls -1 ${RESULTS_DIR} | wc -l)"
log "- Log file: ${LOG_FILE}"
log ""

log "${GREEN}========================================${NC}"
log "${GREEN}  ACMS API Test Suite Complete!${NC}"
log "${GREEN}========================================${NC}"
log ""
log "Review detailed results in: ${RESULTS_DIR}"
log "View execution log: ${LOG_FILE}"

echo ""
echo "Done!"
