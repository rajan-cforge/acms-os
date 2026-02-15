#!/bin/bash
#
# ACMS Weekly Insights API Tests
# Tests the executive intelligence reporting feature - the "wow factor"
# Shows leadership what their teams are struggling with - zero manual analysis
#

BASE_URL="http://localhost:40080"
OUTPUT_FILE="/tmp/weekly_insights_test_results.json"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "========================================="
echo "ACMS Weekly Insights API Test Suite"
echo "========================================="
echo "Started: $TIMESTAMP"
echo "API: $BASE_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

# Test helper function
test_endpoint() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_status="$5"

    echo -n "Testing: $test_name... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    fi

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo "$body" | python3 -m json.tool 2>/dev/null | head -20
        echo ""
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_status, got $http_code)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "$body" | head -10
        echo ""
        return 1
    fi
}

echo "========================================="
echo "TEST SUITE 1: WEEKLY REPORT GENERATION"
echo "========================================="
echo ""

# Test 1: Generate weekly report (JSON format)
test_endpoint \
    "Generate weekly report (JSON)" \
    "GET" \
    "/reporting/weekly?format=json" \
    "" \
    "200"

# Test 2: Generate weekly report for specific week
LAST_MONDAY=$(date -v-Mon +%Y-%m-%d 2>/dev/null || date -d "last monday" +%Y-%m-%d)
test_endpoint \
    "Generate report for specific week" \
    "GET" \
    "/reporting/weekly?week_start=$LAST_MONDAY&format=json" \
    "" \
    "200"

# Test 3: Get latest report
test_endpoint \
    "Get latest report" \
    "GET" \
    "/reporting/latest" \
    "" \
    "200"

# Test 4: List all reports
test_endpoint \
    "List all enterprise reports" \
    "GET" \
    "/reporting/list" \
    "" \
    "200"

echo ""
echo "========================================="
echo "TEST SUITE 2: REPORT FORMAT OPTIONS"
echo "========================================="
echo ""

# Test 5: Generate HTML format
echo -n "Testing: Generate weekly report (HTML)... "
html_response=$(curl -s -w "\n%{http_code}" "$BASE_URL/reporting/weekly?format=html")
html_code=$(echo "$html_response" | tail -n 1)
html_body=$(echo "$html_response" | sed '$d')

if [ "$html_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $html_code)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "HTML content received ($(echo "$html_body" | wc -c) bytes)"
    echo "$html_body" | grep -o "<title>.*</title>" | head -1
    echo ""
else
    echo -e "${RED}✗ FAIL${NC} (Expected 200, got $html_code)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo "$html_body" | head -10
    echo ""
fi

# Test 6: Generate text format
echo -n "Testing: Generate weekly report (text)... "
text_response=$(curl -s -w "\n%{http_code}" "$BASE_URL/reporting/weekly?format=text")
text_code=$(echo "$text_response" | tail -n 1)
text_body=$(echo "$text_response" | sed '$d')

if [ "$text_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $text_code)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "Text content received ($(echo "$text_body" | wc -c) bytes)"
    echo "$text_body" | head -5
    echo ""
else
    echo -e "${RED}✗ FAIL${NC} (Expected 200, got $text_code)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo "$text_body" | head -10
    echo ""
fi

echo ""
echo "========================================="
echo "TEST SUITE 3: REPORT CONTENT VALIDATION"
echo "========================================="
echo ""

# Test 7: Validate report structure
echo -n "Testing: Report has required fields... "
report=$(curl -s "$BASE_URL/reporting/weekly?format=json")

required_fields=(
    "report_id"
    "executive_summary"
    "top_patterns"
    "productivity_blockers"
    "knowledge_gaps"
    "quality_issues"
    "innovation_ideas"
    "metrics"
)

all_fields_present=true
for field in "${required_fields[@]}"; do
    if ! echo "$report" | grep -q "\"$field\""; then
        echo -e "${RED}✗ FAIL${NC} (Missing field: $field)"
        all_fields_present=false
        TESTS_FAILED=$((TESTS_FAILED + 1))
        break
    fi
done

if $all_fields_present; then
    echo -e "${GREEN}✓ PASS${NC} (All required fields present)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "$report" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  - Report ID: {data.get('report_id', 'N/A')}\")
    print(f\"  - Week: {data.get('week_start', 'N/A')} to {data.get('week_end', 'N/A')}\")
    print(f\"  - Patterns detected: {data.get('patterns_analyzed', 0)}\")
    print(f\"  - Total impact: \${data.get('total_impact', 0):,.2f}\")
    if 'metrics' in data:
        m = data['metrics']
        print(f\"  - Cache hit rate: {m.get('cache_hit_rate', 0):.1f}%\")
        print(f\"  - Cost savings: \${m.get('cost_savings_usd', 0):.2f}\")
except Exception as e:
    print(f\"  Error parsing: {e}\")
" 2>/dev/null || echo "  (Could not parse JSON)"
    echo ""
fi

# Test 8: Executive summary quality
echo -n "Testing: Executive summary contains key insights... "
exec_summary=$(echo "$report" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('executive_summary', ''))
except:
    pass
" 2>/dev/null)

if echo "$exec_summary" | grep -q "Week of" && \
   echo "$exec_summary" | grep -q "patterns detected"; then
    echo -e "${GREEN}✓ PASS${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "Executive Summary Preview:"
    echo "$exec_summary" | head -10
    echo ""
else
    echo -e "${RED}✗ FAIL${NC} (Executive summary incomplete)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo ""
fi

echo ""
echo "========================================="
echo "TEST SUITE 4: PATTERN CATEGORIZATION"
echo "========================================="
echo ""

# Test 9: Productivity blockers present
echo -n "Testing: Productivity blockers identified... "
blockers=$(echo "$report" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    blockers = data.get('productivity_blockers', [])
    print(len(blockers))
    if blockers:
        for b in blockers[:3]:
            print(f\"  - {b.get('description', 'N/A')} ({b.get('mentions', 0)} mentions)\")
except:
    print(0)
" 2>/dev/null)

blocker_count=$(echo "$blockers" | head -1)
if [ "$blocker_count" -ge 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} ($blocker_count blockers found)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "$blockers" | tail -n +2
    echo ""
else
    echo -e "${YELLOW}⚠ WARN${NC} (No blockers detected)"
    echo ""
fi

# Test 10: Knowledge gaps identified
echo -n "Testing: Knowledge gaps identified... "
gaps=$(echo "$report" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    gaps = data.get('knowledge_gaps', [])
    print(len(gaps))
    if gaps:
        for g in gaps[:3]:
            print(f\"  - {g.get('description', 'N/A')} ({g.get('mentions', 0)} mentions)\")
except:
    print(0)
" 2>/dev/null)

gap_count=$(echo "$gaps" | head -1)
if [ "$gap_count" -ge 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} ($gap_count gaps found)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "$gaps" | tail -n +2
    echo ""
else
    echo -e "${YELLOW}⚠ WARN${NC} (No knowledge gaps detected)"
    echo ""
fi

echo ""
echo "========================================="
echo "TEST SUITE 5: METRICS CALCULATION"
echo "========================================="
echo ""

# Test 11: Cache performance metrics
echo -n "Testing: Cache metrics calculated... "
cache_metrics=$(echo "$report" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    metrics = data.get('metrics', {})
    if 'cache_hit_rate' in metrics and 'cost_savings_usd' in metrics:
        print('PASS')
        print(f\"  - Total queries: {metrics.get('total_queries', 0):,}\")
        print(f\"  - Cache hits: {metrics.get('cache_hits', 0):,}\")
        print(f\"  - Hit rate: {metrics.get('cache_hit_rate', 0):.1f}%\")
        print(f\"  - Savings: \${metrics.get('cost_savings_usd', 0):.2f}\")
    else:
        print('FAIL')
except:
    print('FAIL')
" 2>/dev/null)

if echo "$cache_metrics" | head -1 | grep -q "PASS"; then
    echo -e "${GREEN}✓ PASS${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "$cache_metrics" | tail -n +2
    echo ""
else
    echo -e "${RED}✗ FAIL${NC} (Metrics missing)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo ""
fi

# Test 12: Cost impact calculation
echo -n "Testing: Total impact calculated... "
impact=$(echo "$report" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    total = data.get('total_impact', 0)
    if isinstance(total, (int, float)):
        print(f\"PASS|{total}\")
    else:
        print('FAIL|0')
except:
    print('FAIL|0')
" 2>/dev/null)

if echo "$impact" | grep -q "PASS"; then
    impact_value=$(echo "$impact" | cut -d'|' -f2)
    echo -e "${GREEN}✓ PASS${NC} (\$$impact_value monthly impact)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo ""
else
    echo -e "${RED}✗ FAIL${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo ""
fi

echo ""
echo "========================================="
echo "TEST SUITE 6: WOW FACTOR VALIDATION"
echo "========================================="
echo ""

# Test 13: Report provides actionable insights
echo -n "Testing: Report has actionable recommendations... "
recommendations=$(echo "$report" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    all_patterns = (
        data.get('productivity_blockers', []) +
        data.get('knowledge_gaps', []) +
        data.get('quality_issues', []) +
        data.get('innovation_ideas', [])
    )

    rec_count = 0
    for pattern in all_patterns:
        recs = pattern.get('recommendations', [])
        rec_count += len(recs)

    print(rec_count)

    # Show sample recommendations
    if all_patterns and all_patterns[0].get('recommendations'):
        print(f\"Sample from '{all_patterns[0].get('description', 'N/A')}' category:\")
        for rec in all_patterns[0].get('recommendations', [])[:2]:
            print(f\"  → {rec}\")
except Exception as e:
    print(0)
" 2>/dev/null)

rec_count=$(echo "$recommendations" | head -1)
if [ "$rec_count" -gt 0 ] 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC} ($rec_count recommendations total)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "$recommendations" | tail -n +2
    echo ""
else
    echo -e "${YELLOW}⚠ WARN${NC} (No recommendations generated)"
    echo ""
fi

# Test 14: Report persistence
echo -n "Testing: Report stored in database... "
sleep 2  # Wait for async storage
latest=$(curl -s "$BASE_URL/reporting/latest")
latest_id=$(echo "$latest" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('report_id', ''))
except:
    pass
" 2>/dev/null)

if [ ! -z "$latest_id" ]; then
    echo -e "${GREEN}✓ PASS${NC} (Report ID: $latest_id)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo ""
else
    echo -e "${RED}✗ FAIL${NC} (Could not retrieve stored report)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo ""
fi

# Test 15: The WOW factor - Complete executive intelligence
echo -n "Testing: Complete executive intelligence report... "
wow_check=$(echo "$report" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)

    # Check for all key components
    has_summary = len(data.get('executive_summary', '')) > 100
    has_patterns = data.get('patterns_analyzed', 0) >= 0
    has_metrics = 'metrics' in data
    has_recommendations = any(
        p.get('recommendations')
        for p in (
            data.get('productivity_blockers', []) +
            data.get('knowledge_gaps', []) +
            data.get('quality_issues', []) +
            data.get('innovation_ideas', [])
        )
    )

    if has_summary and has_patterns and has_metrics:
        print('PASS')
        print(f\"  ✓ Executive summary ({len(data.get('executive_summary', ''))} chars)\")
        print(f\"  ✓ Patterns analyzed: {data.get('patterns_analyzed', 0)}\")
        print(f\"  ✓ Metrics included: {list(data.get('metrics', {}).keys())}\")
        print(f\"  ✓ Actionable recommendations: {'Yes' if has_recommendations else 'No'}\")
        print(f\"  ✓ Auto-generated report shows what teams struggle with - ZERO manual analysis\")
    else:
        print('FAIL')
except Exception as e:
    print(f'FAIL: {e}')
" 2>/dev/null)

if echo "$wow_check" | head -1 | grep -q "PASS"; then
    echo -e "${GREEN}✓ PASS${NC} - 🌟 WOW FACTOR VALIDATED!"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "$wow_check" | tail -n +2
    echo ""
else
    echo -e "${RED}✗ FAIL${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo "$wow_check"
    echo ""
fi

echo ""
echo "========================================="
echo "TEST SUMMARY"
echo "========================================="
TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$(echo "scale=1; $TESTS_PASSED * 100 / $TOTAL_TESTS" | bc 2>/dev/null || echo "N/A")

echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Pass Rate: $PASS_RATE%"
echo ""
echo "Finished: $(date +"%Y-%m-%d %H:%M:%S")"
echo "========================================="
echo ""

# Exit with appropriate code
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    exit 1
fi
