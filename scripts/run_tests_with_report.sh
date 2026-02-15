#!/bin/bash
# Comprehensive Test Runner with Detailed Reporting

set -e

echo "🧪 Running ACMS Test Suite with Full Reporting..."
echo ""

# Create timestamped backup
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH=.

# Run all tests with reporting
pytest tests/ \
    --json-report \
    --json-report-file=.ai/test-results/latest.json \
    --html=.ai/test-results/latest.html \
    --cov=src \
    --cov-report=term \
    --cov-report=json:.ai/test-results/coverage.json \
    --cov-report=html:.ai/test-results/coverage_html \
    -v

# Copy to timestamped archive
if [ -f ".ai/test-results/latest.json" ]; then
    cp .ai/test-results/latest.json \
       .ai/test-results/history/${TIMESTAMP}.json
    echo ""
    echo "✅ Test report archived: .ai/test-results/history/${TIMESTAMP}.json"
fi

# Generate summary
echo ""
echo "📊 Test Report Summary:"
echo "  - Latest JSON: .ai/test-results/latest.json"
echo "  - Latest HTML: .ai/test-results/latest.html"
echo "  - Coverage JSON: .ai/test-results/coverage.json"
echo "  - Coverage HTML: .ai/test-results/coverage_html/index.html"
echo ""

# Extract key metrics
if command -v jq &> /dev/null; then
    TOTAL=$(jq -r '.summary.total' .ai/test-results/latest.json 2>/dev/null || echo "N/A")
    PASSED=$(jq -r '.summary.passed' .ai/test-results/latest.json 2>/dev/null || echo "N/A")
    FAILED=$(jq -r '.summary.failed' .ai/test-results/latest.json 2>/dev/null || echo "N/A")
    DURATION=$(jq -r '.duration' .ai/test-results/latest.json 2>/dev/null || echo "N/A")

    echo "Results: ${PASSED}/${TOTAL} passed, ${FAILED} failed"
    echo "Duration: ${DURATION}s"
fi

echo ""
echo "✅ Full test report generated!"
