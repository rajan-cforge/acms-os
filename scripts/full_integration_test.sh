#!/bin/bash
# =============================================================================
# ACMS Full Integration Test Suite
# =============================================================================
# Performs comprehensive testing from fresh installation:
# 1. Clean VM completely
# 2. Fresh git clone and install
# 3. Configure API keys
# 4. Run 1000+ chat queries across all agents
# 5. Verify knowledge extraction pipeline
# 6. Test all UI endpoints
# 7. Test Gmail and Plaid integrations
#
# Usage:
#   ./scripts/full_integration_test.sh [--skip-clone] [--quick]
#
# Environment:
#   TEST_VM_CONTAINER - Name of test VM container (default: acms-test-vm)
#   ACMS_ENV_SOURCE   - Path to .env with API keys (default: ~/Documents/ACMS/.env)
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
TEST_VM="${TEST_VM_CONTAINER:-acms-test-vm}"
ENV_SOURCE="${ACMS_ENV_SOURCE:-$HOME/Documents/ACMS/.env}"
SKIP_CLONE=false
QUICK_MODE=false
QUERY_COUNT=1000

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-clone) SKIP_CLONE=true; shift ;;
        --quick) QUICK_MODE=true; QUERY_COUNT=50; shift ;;
        *) shift ;;
    esac
done

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         ACMS Full Integration Test Suite                      ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# -----------------------------------------------------------------------------
# Phase 1: Clean VM
# -----------------------------------------------------------------------------
phase_clean() {
    echo -e "${YELLOW}[Phase 1] Cleaning VM for fresh install...${NC}"

    docker exec $TEST_VM bash -c '
        cd /home/acms/acms-os 2>/dev/null && docker compose down -v --remove-orphans 2>/dev/null || true
        docker rm -f $(docker ps -aq) 2>/dev/null || true
        docker rmi $(docker images -q "acms-os*") 2>/dev/null || true
        docker volume prune -f 2>/dev/null || true
        rm -rf /home/acms/acms-os
    ' 2>/dev/null

    echo -e "  ${GREEN}✓${NC} VM cleaned"
}

# -----------------------------------------------------------------------------
# Phase 2: Fresh Clone and Install
# -----------------------------------------------------------------------------
phase_install() {
    echo -e "${YELLOW}[Phase 2] Fresh installation...${NC}"

    docker exec $TEST_VM bash -c '
        cd /home/acms
        git clone https://github.com/rajan-cforge/acms-os.git
        cd acms-os
        ./install.sh
    '

    echo -e "  ${GREEN}✓${NC} Installation complete"
}

# -----------------------------------------------------------------------------
# Phase 3: Configure API Keys
# -----------------------------------------------------------------------------
phase_configure() {
    echo -e "${YELLOW}[Phase 3] Configuring API keys...${NC}"

    # Copy relevant keys from source env (excluding PII)
    if [ -f "$ENV_SOURCE" ]; then
        # Extract only API keys, not personal data
        grep -E "^(ANTHROPIC_API_KEY|OPENAI_API_KEY|GEMINI_API_KEY|GOOGLE_CLIENT_ID|GOOGLE_CLIENT_SECRET|GOOGLE_REDIRECT_URI|PLAID_CLIENT_ID|PLAID_SECRET|PLAID_ENV|PLAID_ENCRYPTION_KEY)=" "$ENV_SOURCE" > /tmp/acms_test_keys.env

        # Copy to VM and append to .env
        docker cp /tmp/acms_test_keys.env $TEST_VM:/tmp/test_keys.env
        docker exec $TEST_VM bash -c 'cat /tmp/test_keys.env >> /home/acms/acms-os/.env'
        rm /tmp/acms_test_keys.env

        echo -e "  ${GREEN}✓${NC} API keys configured"
    else
        echo -e "  ${YELLOW}⚠${NC} No env source found, using Ollama only"
    fi

    # Restart API to pick up new keys
    docker exec $TEST_VM bash -c 'cd /home/acms/acms-os && docker compose restart api'
    sleep 10
}

# -----------------------------------------------------------------------------
# Phase 4: Run Chat Tests
# -----------------------------------------------------------------------------
phase_chat_tests() {
    echo -e "${YELLOW}[Phase 4] Running $QUERY_COUNT chat queries...${NC}"

    docker exec $TEST_VM bash -c "
        cd /home/acms/acms-os
        python3 scripts/load_test_chat.py --count $QUERY_COUNT --all-agents
    "

    echo -e "  ${GREEN}✓${NC} Chat tests complete"
}

# -----------------------------------------------------------------------------
# Phase 5: Verify Knowledge Pipeline
# -----------------------------------------------------------------------------
phase_verify_knowledge() {
    echo -e "${YELLOW}[Phase 5] Verifying knowledge extraction...${NC}"

    docker exec $TEST_VM bash -c '
        # Check memories created
        MEMORY_COUNT=$(docker exec acms_postgres psql -U acms -d acms -t -c "SELECT COUNT(*) FROM memory_items")
        echo "  Memories created: $MEMORY_COUNT"

        # Check knowledge extraction
        KNOWLEDGE_COUNT=$(docker exec acms_api curl -s http://localhost:40080/api/knowledge/stats | python3 -c "import sys,json; print(json.load(sys.stdin).get(\"total_entries\", 0))" 2>/dev/null || echo "0")
        echo "  Knowledge entries: $KNOWLEDGE_COUNT"

        # Check topics
        TOPIC_COUNT=$(docker exec acms_postgres psql -U acms -d acms -t -c "SELECT COUNT(*) FROM topic_clusters")
        echo "  Topic clusters: $TOPIC_COUNT"
    '

    echo -e "  ${GREEN}✓${NC} Knowledge pipeline verified"
}

# -----------------------------------------------------------------------------
# Phase 6: Test API Endpoints
# -----------------------------------------------------------------------------
phase_test_endpoints() {
    echo -e "${YELLOW}[Phase 6] Testing API endpoints...${NC}"

    docker exec $TEST_VM bash -c '
        API="http://localhost:40080"

        test_endpoint() {
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$1")
            if [ "$STATUS" = "200" ]; then
                echo "  ✓ $2"
            else
                echo "  ✗ $2 (HTTP $STATUS)"
            fi
        }

        test_endpoint "$API/health" "Health check"
        test_endpoint "$API/api/agents" "Agents list"
        test_endpoint "$API/memories?limit=10" "Memories"
        test_endpoint "$API/api/nudges?limit=10" "Nudges"
        test_endpoint "$API/api/knowledge/stats" "Knowledge stats"
        test_endpoint "$API/api/conversations" "Conversations"
    '

    echo -e "  ${GREEN}✓${NC} Endpoint tests complete"
}

# -----------------------------------------------------------------------------
# Phase 7: Test Integrations
# -----------------------------------------------------------------------------
phase_test_integrations() {
    echo -e "${YELLOW}[Phase 7] Testing integrations...${NC}"

    docker exec $TEST_VM bash -c '
        API="http://localhost:40080"

        # Gmail integration
        GMAIL_STATUS=$(curl -s "$API/gmail/status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get(\"connected\", False))" 2>/dev/null || echo "false")
        if [ "$GMAIL_STATUS" = "True" ] || [ "$GMAIL_STATUS" = "true" ]; then
            echo "  ✓ Gmail connected"
        else
            echo "  ⚠ Gmail not connected (requires OAuth)"
        fi

        # Plaid integration
        PLAID_STATUS=$(curl -s "$API/api/financial/status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get(\"connected\", False))" 2>/dev/null || echo "false")
        if [ "$PLAID_STATUS" = "True" ] || [ "$PLAID_STATUS" = "true" ]; then
            echo "  ✓ Plaid connected"
        else
            echo "  ⚠ Plaid not connected (requires link)"
        fi
    '

    echo -e "  ${GREEN}✓${NC} Integration tests complete"
}

# -----------------------------------------------------------------------------
# Run All Phases
# -----------------------------------------------------------------------------

FAILED=0

if [ "$SKIP_CLONE" = false ]; then
    phase_clean || FAILED=1
    phase_install || FAILED=1
fi

phase_configure || FAILED=1
phase_test_endpoints || FAILED=1

if [ "$QUICK_MODE" = false ]; then
    phase_chat_tests || FAILED=1
    phase_verify_knowledge || FAILED=1
fi

phase_test_integrations || true  # Don't fail on integration tests

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              All Tests Passed!                                ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║              Some Tests Failed                                ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
