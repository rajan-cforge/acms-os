# ACMS - Adaptive Context Memory System

> 🧠 Your private, local-first AI assistant that remembers everything

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Privacy](https://img.shields.io/badge/Privacy-First-green.svg)](#-why-acms)

## 🔐 Why ACMS?

**The Problem:** Cloud AI assistants like ChatGPT, Claude, and Gemini are powerful, but they have a fundamental issue: *they don't remember you*. Every conversation starts fresh. And when you give them context about your life, projects, or preferences, that data lives on someone else's servers.

**The Solution:** ACMS runs entirely on your machine. Your conversations, memories, and knowledge stay local. You get persistent memory across all your AI interactions, with zero data leaving your computer (unless you explicitly choose cloud AI providers).

### Privacy Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR MACHINE (localhost only)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │PostgreSQL│  │ Weaviate │  │  Redis   │  │  Ollama  │        │
│  │   :40432 │  │  :40480  │  │  :40379  │  │  :40434  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│       ▲              ▲             ▲             ▲              │
│       └──────────────┴─────────────┴─────────────┘              │
│                              │                                   │
│                       ┌──────┴──────┐                           │
│                       │  ACMS API   │                           │
│                       │   :40080    │                           │
│                       └─────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │ OPTIONAL: Cloud AI │  ← Only if YOU add API keys
                    │ Claude/GPT/Gemini  │  ← Only queries, not storage
                    └───────────────────┘
```

**Key Privacy Properties:**
- ✅ **Default: ZERO external connections** - Ollama runs 100% locally
- ✅ **All storage is local** - PostgreSQL, Weaviate, Redis in Docker
- ✅ **Cloud AI is optional** - Only enabled if you add API keys
- ✅ **You control your data** - Export, delete, or migrate anytime

## 🚀 Quick Start (2 minutes)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [Podman](https://podman.io/)
- 8GB RAM minimum (16GB recommended)

### One-Command Install

```bash
git clone https://github.com/rajan-cforge/acms-os.git && cd acms-os && ./install.sh
```

That's it! The installer will:
- ✅ Check prerequisites (Docker/Podman)
- ✅ Generate secure encryption keys
- ✅ Start all services (PostgreSQL, Weaviate, Redis, Ollama, API)
- ✅ Download Ollama models for local AI
- ✅ Create default user account

### Access ACMS

- **Desktop App**: `cd desktop-app && npm install && npm start`
- **API Docs**: http://localhost:40080/docs

## 🎯 Zero-Cost Local Setup (Recommended)

ACMS works **fully offline** with no API keys:

```bash
# That's it! Ollama is enabled by default.
# The installer downloads llama3.2 and nomic-embed-text automatically.
```

Your AI runs on your hardware. No API costs. No data leaves your machine.

## ☁️ Optional: Cloud AI Providers

Want higher quality responses? Add API keys to `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...  # Claude (best quality)
OPENAI_API_KEY=sk-...         # GPT
GEMINI_API_KEY=AI...          # Gemini (has free tier)
```

**Note:** When using cloud AI, only your *query* is sent to the provider. Your memories and knowledge base remain local.

## ✨ Features

- **🧠 Persistent Memory** - Every conversation is remembered and searchable
- **🤖 Multi-Agent AI** - Use Ollama (local), Claude, GPT, or Gemini
- **🔍 Semantic Search** - Find anything by meaning, not just keywords
- **📧 Gmail Integration** - AI-powered email summaries (optional)
- **💰 Financial Tracking** - Portfolio analysis with Plaid (optional)
- **📊 Knowledge Extraction** - Automatically extracts facts and topics
- **🔔 Proactive Nudges** - Get notified about stale or conflicting information

## 🏗️ Architecture

| Component | Purpose | Port | Data Location |
|-----------|---------|------|---------------|
| PostgreSQL | User data, memories, audit logs | 40432 | Local Docker volume |
| Weaviate | Vector search, knowledge base | 40480 | Local Docker volume |
| Redis | Caching, rate limiting | 40379 | Local Docker volume |
| Ollama | Local LLM inference | 40434 | Local Docker volume |
| FastAPI | Backend API | 40080 | Stateless |
| Electron | Desktop app | - | Local |

## 📖 Documentation

- [API Reference](API.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Privacy Policy](docs/PRIVACY_POLICY.md)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with [FastAPI](https://fastapi.tiangolo.com/), [Weaviate](https://weaviate.io/), [Electron](https://www.electronjs.org/), and [Ollama](https://ollama.ai/).
