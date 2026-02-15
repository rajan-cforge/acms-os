#!/bin/bash
# =============================================================================
# ACMS Open Source Release Preparation Script
# =============================================================================
# This script creates a CLEAN copy of ACMS for open-source release.
# It does NOT modify your working directory - it creates a new export.
#
# Usage: ./scripts/prepare_opensource_release.sh
# =============================================================================

set -e

# Configuration
SOURCE_DIR="/path/to/acms"
EXPORT_DIR="/path/to/acms-opensource"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=============================================="
echo "ACMS Open Source Release Preparation"
echo "=============================================="
echo ""
echo "Source:      $SOURCE_DIR"
echo "Export to:   $EXPORT_DIR"
echo ""

# Check if export dir exists
if [ -d "$EXPORT_DIR" ]; then
    echo "⚠️  Export directory already exists."
    read -p "Delete and recreate? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf "$EXPORT_DIR"
    else
        echo "Aborting."
        exit 1
    fi
fi

# Create export directory
mkdir -p "$EXPORT_DIR"

echo ""
echo "Step 1: Copying source files (excluding sensitive data)..."
echo "----------------------------------------------"

# Use rsync to copy, excluding sensitive files and directories
rsync -av --progress \
    --exclude='.git' \
    --exclude='.env' \
    --exclude='*.sql' \
    --exclude='backup_before_migration.sql' \
    --exclude='migration_backup/' \
    --exclude='node_modules/' \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache/' \
    --exclude='*.egg-info/' \
    --exclude='dist/' \
    --exclude='build/' \
    --exclude='archive/' \
    --exclude='downloaded-data/' \
    --exclude='rajan-feedback.md' \
    --exclude='*-feedback.md' \
    --exclude='.claude/' \
    --exclude='tests/latest.json' \
    --exclude='configs/claude_desktop_config.json' \
    --exclude='.DS_Store' \
    --exclude='*.log' \
    --exclude='logs/' \
    "$SOURCE_DIR/" "$EXPORT_DIR/"

echo ""
echo "Step 2: Replacing personal paths..."
echo "----------------------------------------------"

# Replace personal paths in all text files
find "$EXPORT_DIR" -type f \( -name "*.py" -o -name "*.js" -o -name "*.json" -o -name "*.md" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" \) -exec sed -i '' 's|/path/to/acms|/path/to/acms|g' {} \;
find "$EXPORT_DIR" -type f \( -name "*.py" -o -name "*.js" -o -name "*.json" -o -name "*.md" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" \) -exec sed -i '' 's|$HOME|$HOME|g' {} \;

echo "  ✓ Replaced personal paths"

echo ""
echo "Step 3: Creating .env.example..."
echo "----------------------------------------------"

cat > "$EXPORT_DIR/.env.example" << 'ENVEOF'
# =============================================================================
# ACMS Configuration
# =============================================================================
# Copy this file to .env and fill in your values:
#   cp .env.example .env
#
# MINIMUM REQUIREMENT: Configure at least ONE AI provider
# For 100% local/private setup, just enable Ollama (no API keys needed!)
# =============================================================================

# -----------------------------------------------------------------------------
# AI Providers (configure at least one)
# -----------------------------------------------------------------------------

# Option 1: Anthropic Claude (recommended for best quality)
# Get your key at: https://console.anthropic.com/
ANTHROPIC_API_KEY=

# Option 2: OpenAI GPT
# Get your key at: https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Option 3: Google Gemini (has free tier!)
# Get your key at: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=

# Option 4: Ollama (100% local, no API key needed!)
# Just make sure Ollama is running: ollama serve
OLLAMA_ENABLED=true
OLLAMA_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://localhost:11434

# -----------------------------------------------------------------------------
# Optional: Web Search
# -----------------------------------------------------------------------------

# Tavily API for web search capability
# Get your key at: https://tavily.com/
TAVILY_API_KEY=

# -----------------------------------------------------------------------------
# Optional: Gmail Integration
# -----------------------------------------------------------------------------
# Create OAuth credentials at: https://console.cloud.google.com/apis/credentials
# See docs/GMAIL_SETUP.md for detailed instructions

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:40080/api/gmail/callback

# -----------------------------------------------------------------------------
# Optional: Financial Integration (Plaid)
# -----------------------------------------------------------------------------
# Sign up at: https://dashboard.plaid.com/
# See docs/PLAID_SETUP.md for detailed instructions

PLAID_CLIENT_ID=
PLAID_SECRET=
PLAID_ENV=sandbox
PLAID_PRODUCTS=transactions,investments
PLAID_COUNTRY_CODES=US

# -----------------------------------------------------------------------------
# Security Keys (auto-generated if not provided)
# -----------------------------------------------------------------------------
# For production, generate secure keys:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"

# JWT token signing secret
ACMS_TOKEN_SECRET=

# Data encryption key (for OAuth tokens, etc.)
ACMS_ENCRYPTION_KEY=

# Plaid token encryption key
PLAID_ENCRYPTION_KEY=

# -----------------------------------------------------------------------------
# Infrastructure (Docker Compose handles these automatically)
# -----------------------------------------------------------------------------
# Only change these if running services outside Docker

# PostgreSQL
POSTGRES_HOST=acms_postgres
POSTGRES_PORT=5432
POSTGRES_USER=acms
POSTGRES_PASSWORD=acms_secure_password_change_me
POSTGRES_DB=acms
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# Redis
REDIS_HOST=acms_redis
REDIS_PORT=6379
REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}

# Weaviate
WEAVIATE_HOST=acms_weaviate
WEAVIATE_PORT=8080
WEAVIATE_URL=http://${WEAVIATE_HOST}:${WEAVIATE_PORT}

# Ollama (when running in Docker)
OLLAMA_HOST=acms_ollama
OLLAMA_PORT=11434

# -----------------------------------------------------------------------------
# Application Settings
# -----------------------------------------------------------------------------

# API server port
API_PORT=40080

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Enable debug mode (set to false in production)
DEBUG=false

# User ID (for single-user mode)
DEFAULT_USER_ID=default-user

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------

# Enable/disable specific features
FEATURE_GMAIL=true
FEATURE_FINANCIAL=true
FEATURE_WEB_SEARCH=true
FEATURE_COGNITIVE=true
ENVEOF

echo "  ✓ Created .env.example"

echo ""
echo "Step 4: Creating README.md..."
echo "----------------------------------------------"

cat > "$EXPORT_DIR/README.md" << 'READMEEOF'
# ACMS - Adaptive Context Memory System

> 🧠 Your private, local-first AI assistant that remembers everything

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

ACMS is a self-hosted AI memory system that turns your conversations, emails, and documents into a searchable, intelligent second brain.

## ✨ Features

- **🤖 Multi-Agent AI** - Use Claude, GPT, Gemini, or local Ollama
- **🧠 Persistent Memory** - Every conversation is remembered and searchable
- **🔒 Privacy-First** - All data stays on your machine
- **📧 Gmail Integration** - AI-powered email summaries and search
- **💰 Financial Tracking** - Portfolio analysis with Plaid
- **📊 Cognitive Dashboard** - Track your expertise and knowledge gaps
- **🔍 Semantic Search** - Find anything by meaning, not just keywords

## 🚀 Quick Start (5 minutes)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [Podman](https://podman.io/)
- 8GB RAM minimum (16GB recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/acms.git
cd acms

# Copy environment template
cp .env.example .env

# (Optional) Add your API keys to .env
# Or just use Ollama for 100% local operation!

# Start all services
docker compose up -d

# Wait for services to be healthy
docker compose ps
```

### Access ACMS

- **Web Interface**: http://localhost:40080
- **Desktop App**: `cd desktop-app && npm install && npm start`

## 🎯 Configuration Options

### Zero-Cost Setup (Ollama Only)

No API keys needed! ACMS works fully locally with Ollama:

```bash
# .env only needs:
OLLAMA_ENABLED=true
OLLAMA_MODEL=llama3.2:latest
```

### With Cloud AI Providers

Add any combination of API keys for better quality:

```bash
ANTHROPIC_API_KEY=sk-ant-...  # Claude (recommended)
OPENAI_API_KEY=sk-...         # GPT
GEMINI_API_KEY=AI...          # Gemini (has free tier)
```

### With Integrations

See the docs for setting up:
- [Gmail Integration](docs/GMAIL_SETUP.md)
- [Financial Tracking](docs/PLAID_SETUP.md)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ACMS Architecture                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Desktop   │     │   FastAPI   │     │   Weaviate  │   │
│  │   Electron  │────▶│   Backend   │────▶│  Vector DB  │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│                             │                               │
│                             ▼                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Claude    │     │  PostgreSQL │     │    Redis    │   │
│  │  GPT/Gemini │◀───▶│   Database  │     │    Cache    │   │
│  │   Ollama    │     └─────────────┘     └─────────────┘   │
│  └─────────────┘                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📖 Documentation

- [Quick Start Guide](docs/QUICK_START.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Contributing](CONTRIBUTING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Weaviate](https://weaviate.io/)
- [Electron](https://www.electronjs.org/)
- [Anthropic Claude](https://www.anthropic.com/)
- [OpenAI](https://openai.com/)
- [Ollama](https://ollama.ai/)
READMEEOF

echo "  ✓ Created README.md"

echo ""
echo "Step 5: Creating LICENSE (MIT)..."
echo "----------------------------------------------"

cat > "$EXPORT_DIR/LICENSE" << 'LICENSEEOF'
MIT License

Copyright (c) 2026 ACMS Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
LICENSEEOF

echo "  ✓ Created LICENSE"

echo ""
echo "Step 6: Creating CONTRIBUTING.md..."
echo "----------------------------------------------"

cat > "$EXPORT_DIR/CONTRIBUTING.md" << 'CONTRIBEOF'
# Contributing to ACMS

Thank you for your interest in contributing to ACMS! This document provides guidelines for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/acms.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `pytest tests/`
6. Commit: `git commit -m "Add your feature"`
7. Push: `git push origin feature/your-feature`
8. Open a Pull Request

## Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/acms.git
cd acms
cp .env.example .env

# Start services
docker compose up -d

# Install Python dependencies (for development)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v
```

## Code Style

- Python: Follow PEP 8, use Black for formatting
- JavaScript: Use ESLint with provided config
- Commits: Use conventional commits (feat:, fix:, docs:, etc.)

## Testing

- Write tests for new features
- Ensure existing tests pass
- Aim for >80% coverage on new code

## Pull Request Process

1. Update documentation for any new features
2. Add tests for new functionality
3. Ensure CI passes
4. Request review from maintainers

## Code of Conduct

Be respectful and inclusive. We welcome contributors of all backgrounds.

## Questions?

Open an issue or join our Discord community.
CONTRIBEOF

echo "  ✓ Created CONTRIBUTING.md"

echo ""
echo "Step 7: Creating .gitignore..."
echo "----------------------------------------------"

cat > "$EXPORT_DIR/.gitignore" << 'GITIGNOREEOF'
# Environment and secrets
.env
.env.local
.env.*.local
*.pem
*.key

# Database backups
*.sql
backup_before_migration.sql
migration_backup/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Personal files
*-feedback.md
downloaded-data/

# Claude Code
.claude/

# Test artifacts
tests/latest.json

# Docker
docker-compose.override.yml
GITIGNOREEOF

echo "  ✓ Created .gitignore"

echo ""
echo "Step 8: Initializing git repository..."
echo "----------------------------------------------"

cd "$EXPORT_DIR"
git init
git add .
git commit -m "Initial commit: ACMS open source release

Features:
- Multi-agent AI chat (Claude, GPT, Gemini, Ollama)
- Persistent memory with semantic search
- Knowledge extraction pipeline
- Gmail integration
- Financial tracking (Plaid)
- Cognitive dashboard
- Desktop app (Electron)

100% local-first, privacy-focused."

echo "  ✓ Git repository initialized"

echo ""
echo "=============================================="
echo "✅ EXPORT COMPLETE!"
echo "=============================================="
echo ""
echo "Clean export created at: $EXPORT_DIR"
echo ""
echo "Next steps:"
echo "  1. Review the exported files"
echo "  2. Create a new GitHub repository"
echo "  3. Push the clean code:"
echo ""
echo "     cd $EXPORT_DIR"
echo "     git remote add origin https://github.com/yourusername/acms.git"
echo "     git push -u origin main"
echo ""
echo "  4. IMPORTANT: Rotate all your API keys!"
echo "     Your current keys may be in git history."
echo ""
