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
