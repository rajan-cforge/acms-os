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

# Check available memory
AVAILABLE_MEM=$(free -g 2>/dev/null | awk '/^Mem:/{print $7}' || echo "8")
if [ "$AVAILABLE_MEM" -lt 4 ]; then
    echo -e "  ${YELLOW}⚠${NC} Low memory warning: ${AVAILABLE_MEM}GB available (8GB+ recommended)"
else
    echo -e "  ${GREEN}✓${NC} Memory: ${AVAILABLE_MEM}GB available"
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

    # Generate encryption keys
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
        echo -e "  ${GREEN}✓${NC} Generated encryption keys"
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
    echo -e "  ${YELLOW}⚠${NC} API not responding yet. Check logs with: $COMPOSE_CMD logs acms_api"
fi

# Check other services
echo ""
echo -e "${YELLOW}Service Status:${NC}"
$COMPOSE_CMD ps --format "table {{.Name}}\t{{.Status}}"

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
