#!/bin/bash
# =============================================================================
# ACMS - One-Command Installer
# =============================================================================
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/acms-ai/acms/main/install.sh | bash
#
# Or after cloning:
#   ./install.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                               ║${NC}"
echo -e "${BLUE}║   ${GREEN}🧠 ACMS - Adaptive Context Memory System${BLUE}                   ║${NC}"
echo -e "${BLUE}║   ${NC}Your private, local-first AI assistant${BLUE}                      ║${NC}"
echo -e "${BLUE}║                                                               ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# -----------------------------------------------------------------------------
# Check Prerequisites
# -----------------------------------------------------------------------------

echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check for Docker or Podman
CONTAINER_CMD=""
COMPOSE_CMD=""

if command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    fi
    echo -e "  ${GREEN}✓${NC} Docker found"
elif command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
    if command -v podman-compose &> /dev/null; then
        COMPOSE_CMD="podman-compose"
    fi
    echo -e "  ${GREEN}✓${NC} Podman found"
else
    echo -e "  ${RED}✗${NC} Docker or Podman not found"
    echo ""
    echo "Please install Docker Desktop or Podman first:"
    echo "  - Docker Desktop: https://www.docker.com/products/docker-desktop/"
    echo "  - Podman: https://podman.io/getting-started/installation"
    exit 1
fi

if [ -z "$COMPOSE_CMD" ]; then
    echo -e "  ${RED}✗${NC} Docker Compose not found"
    echo ""
    echo "Please install Docker Compose:"
    echo "  https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Compose found: $COMPOSE_CMD"

# Check if Docker is running
if ! $CONTAINER_CMD info &> /dev/null; then
    echo -e "  ${RED}✗${NC} Docker daemon not running"
    echo ""
    echo "Please start Docker Desktop or the Docker daemon."
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Docker daemon running"

# Check available memory (cross-platform)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS: use sysctl for total physical memory (in GB)
    TOTAL_MEM=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%d", $1/1073741824}')
else
    # Linux: use free
    TOTAL_MEM=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo "8")
fi
if [ "$TOTAL_MEM" -lt 8 ]; then
    echo -e "  ${YELLOW}⚠${NC} Low memory warning: ${TOTAL_MEM}GB total (8GB+ recommended)"
else
    echo -e "  ${GREEN}✓${NC} Memory: ${TOTAL_MEM}GB total"
fi

echo ""

# -----------------------------------------------------------------------------
# Clone Repository (if not already in repo)
# -----------------------------------------------------------------------------

if [ ! -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}Cloning ACMS repository...${NC}"

    if command -v git &> /dev/null; then
        git clone https://github.com/rajan-cforge/acms-os.git
        cd acms-os
        echo -e "  ${GREEN}✓${NC} Repository cloned"
    else
        echo -e "  ${RED}✗${NC} Git not found. Please install git or download manually."
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} Already in ACMS directory"
fi

echo ""

# -----------------------------------------------------------------------------
# Configure Environment
# -----------------------------------------------------------------------------

echo -e "${YELLOW}Configuring environment...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "  ${GREEN}✓${NC} Created .env from template"

    # Generate security keys (postgres password uses fixed default from .env.example)
    if command -v python3 &> /dev/null; then
        TOKEN_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

        # Update .env with generated keys
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^ACMS_TOKEN_SECRET=$/ACMS_TOKEN_SECRET=$TOKEN_SECRET/" .env
            sed -i '' "s/^ACMS_ENCRYPTION_KEY=$/ACMS_ENCRYPTION_KEY=$ENCRYPTION_KEY/" .env
        else
            sed -i "s/^ACMS_TOKEN_SECRET=$/ACMS_TOKEN_SECRET=$TOKEN_SECRET/" .env
            sed -i "s/^ACMS_ENCRYPTION_KEY=$/ACMS_ENCRYPTION_KEY=$ENCRYPTION_KEY/" .env
        fi
        echo -e "  ${GREEN}✓${NC} Generated security keys (token, encryption)"
    fi
else
    echo -e "  ${GREEN}✓${NC} .env already exists"
fi

echo ""

# -----------------------------------------------------------------------------
# Start Services
# -----------------------------------------------------------------------------

echo -e "${YELLOW}Starting ACMS services...${NC}"
echo "  This may take a few minutes on first run (downloading images)..."
echo ""

# Determine container name prefix (matches docker-compose.yml)
ACMS_PREFIX="${ACMS_PREFIX:-acms}"

$COMPOSE_CMD up -d

echo ""
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"

# Wait for API to be ready
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:40080/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} API server ready"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo -e "  Waiting for API... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "  ${YELLOW}⚠${NC} API not responding yet. Check logs with: $COMPOSE_CMD logs api"
fi

# Check other services
echo ""
echo -e "${YELLOW}Service Status:${NC}"
$COMPOSE_CMD ps --format "table {{.Name}}\t{{.Status}}"

echo ""

# -----------------------------------------------------------------------------
# Run Database Migrations
# -----------------------------------------------------------------------------

echo -e "${YELLOW}Running database migrations...${NC}"
$CONTAINER_CMD exec ${ACMS_PREFIX}_api alembic upgrade head 2>&1 | tail -5
echo -e "  ${GREEN}✓${NC} Database migrations complete"

# -----------------------------------------------------------------------------
# Create Weaviate Collections
# -----------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}Setting up Weaviate collections...${NC}"

# Wait for Weaviate to be ready
sleep 3

# Create ACMS_Raw_v1 collection (for raw Q&A storage)
curl -s -X POST "http://localhost:40480/v1/schema" -H "Content-Type: application/json" -d '{
  "class": "ACMS_Raw_v1",
  "description": "Raw Q&A pairs with 30-day retention",
  "vectorizer": "none",
  "vectorIndexConfig": {"distance": "cosine"},
  "properties": [
    {"name": "query_hash", "dataType": ["text"]},
    {"name": "query_text", "dataType": ["text"]},
    {"name": "answer_text", "dataType": ["text"]},
    {"name": "conversation_id", "dataType": ["text"]},
    {"name": "agent_used", "dataType": ["text"]},
    {"name": "cost_usd", "dataType": ["number"]},
    {"name": "latency_ms", "dataType": ["int"]},
    {"name": "user_feedback", "dataType": ["text"]},
    {"name": "created_at", "dataType": ["date"]},
    {"name": "user_id", "dataType": ["text"]}
  ]
}' > /dev/null 2>&1 && echo -e "  ${GREEN}✓${NC} ACMS_Raw_v1 collection ready" || echo -e "  ${YELLOW}⚠${NC} ACMS_Raw_v1 already exists or failed"

# Create ACMS_Knowledge_v2 collection (for knowledge extraction)
curl -s -X POST "http://localhost:40480/v1/schema" -H "Content-Type: application/json" -d '{
  "class": "ACMS_Knowledge_v2",
  "description": "Structured knowledge entries",
  "vectorizer": "none",
  "vectorIndexConfig": {"distance": "cosine"},
  "properties": [
    {"name": "canonical_query", "dataType": ["text"]},
    {"name": "answer_summary", "dataType": ["text"]},
    {"name": "full_answer", "dataType": ["text"]},
    {"name": "primary_intent", "dataType": ["text"]},
    {"name": "problem_domain", "dataType": ["text"]},
    {"name": "topic_cluster", "dataType": ["text"]},
    {"name": "key_facts", "dataType": ["text[]"]},
    {"name": "entities_json", "dataType": ["text"]},
    {"name": "user_id", "dataType": ["text"]},
    {"name": "source_query_id", "dataType": ["text"]},
    {"name": "created_at", "dataType": ["text"]},
    {"name": "extraction_confidence", "dataType": ["number"]}
  ]
}' > /dev/null 2>&1 && echo -e "  ${GREEN}✓${NC} ACMS_Knowledge_v2 collection ready" || echo -e "  ${YELLOW}⚠${NC} ACMS_Knowledge_v2 already exists or failed"

# Create ACMS_QualityCache_v1 collection (for quality cache)
curl -s -X POST "http://localhost:40480/v1/schema" -H "Content-Type: application/json" -d '{
  "class": "ACMS_QualityCache_v1",
  "description": "Quality-validated cache entries",
  "vectorizer": "none",
  "vectorIndexConfig": {"distance": "cosine"},
  "properties": [
    {"name": "query_hash", "dataType": ["text"]},
    {"name": "query_text", "dataType": ["text"]},
    {"name": "answer_text", "dataType": ["text"]},
    {"name": "quality_score", "dataType": ["number"]},
    {"name": "feedback_count", "dataType": ["int"]},
    {"name": "positive_feedback", "dataType": ["int"]},
    {"name": "ttl_hours", "dataType": ["int"]},
    {"name": "created_at", "dataType": ["date"]},
    {"name": "last_accessed", "dataType": ["date"]},
    {"name": "user_id", "dataType": ["text"]}
  ]
}' > /dev/null 2>&1 && echo -e "  ${GREEN}✓${NC} ACMS_QualityCache_v1 collection ready" || echo -e "  ${YELLOW}⚠${NC} ACMS_QualityCache_v1 already exists or failed"

# Create ACMS_Insights_v1 collection (for cross-source insights)
curl -s -X POST "http://localhost:40480/v1/schema" -H "Content-Type: application/json" -d '{
  "class": "ACMS_Insights_v1",
  "description": "Cross-source unified insights",
  "vectorizer": "none",
  "vectorIndexConfig": {"distance": "cosine"},
  "properties": [
    {"name": "insight_text", "dataType": ["text"]},
    {"name": "insight_type", "dataType": ["text"]},
    {"name": "source_type", "dataType": ["text"]},
    {"name": "confidence", "dataType": ["number"]},
    {"name": "topic", "dataType": ["text"]},
    {"name": "user_id", "dataType": ["text"]},
    {"name": "created_at", "dataType": ["date"]},
    {"name": "metadata_json", "dataType": ["text"]}
  ]
}' > /dev/null 2>&1 && echo -e "  ${GREEN}✓${NC} ACMS_Insights_v1 collection ready" || echo -e "  ${YELLOW}⚠${NC} ACMS_Insights_v1 already exists or failed"

echo ""

# -----------------------------------------------------------------------------
# Create Default User
# -----------------------------------------------------------------------------

echo -e "${YELLOW}Setting up default user...${NC}"
$CONTAINER_CMD exec ${ACMS_PREFIX}_postgres psql -U acms -d acms -c "INSERT INTO users (user_id, username, email, display_name, is_active, is_admin) VALUES (gen_random_uuid(), 'default', 'default@acms.local', 'Default User', true, true) ON CONFLICT (email) DO NOTHING;" > /dev/null 2>&1
echo -e "  ${GREEN}✓${NC} Default user ready (default@acms.local)"

echo ""

# -----------------------------------------------------------------------------
# Pull Ollama Models
# -----------------------------------------------------------------------------

echo -e "${YELLOW}Downloading Ollama models (this may take a few minutes)...${NC}"
echo "  Pulling llama3.2 for chat..."
$CONTAINER_CMD exec ${ACMS_PREFIX}_ollama ollama pull llama3.2:latest > /dev/null 2>&1 && echo -e "  ${GREEN}✓${NC} llama3.2 ready" || echo -e "  ${YELLOW}⚠${NC} llama3.2 download failed (can retry later)"

echo "  Pulling nomic-embed-text for embeddings..."
$CONTAINER_CMD exec ${ACMS_PREFIX}_ollama ollama pull nomic-embed-text > /dev/null 2>&1 && echo -e "  ${GREEN}✓${NC} nomic-embed-text ready" || echo -e "  ${YELLOW}⚠${NC} nomic-embed-text download failed (can retry later)"

echo ""

# -----------------------------------------------------------------------------
# Success Message
# -----------------------------------------------------------------------------

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                               ║${NC}"
echo -e "${GREEN}║   🎉 ACMS Installation Complete!                              ║${NC}"
echo -e "${GREEN}║                                                               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Access ACMS:${NC}"
echo "  • Web Interface: http://localhost:40080"
echo "  • Desktop App:   cd desktop-app && npm install && npm start"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  • Edit .env to add API keys (optional - Ollama works without keys)"
echo "  • After editing .env, restart: $COMPOSE_CMD restart"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  • View logs:     $COMPOSE_CMD logs -f"
echo "  • Stop ACMS:     $COMPOSE_CMD down"
echo "  • Restart ACMS:  $COMPOSE_CMD restart"
echo ""
echo -e "${YELLOW}Note:${NC} For cloud AI (Claude, GPT, Gemini), add your API keys to .env"
echo "      Or use Ollama for 100% local operation (no keys needed)!"
echo ""
