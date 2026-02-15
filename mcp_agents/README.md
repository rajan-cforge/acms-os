# ACMS Multi-Agent Build System

## Overview

This directory contains internal MCP agents used to build ACMS faster through parallel development.

**IMPORTANT**: These are **build-time agents** (temporary), NOT the product MCP server (permanent in `src/mcp_server/`).

## Architecture

```
mcp_agents/              # Internal build system
├── shared/              # Shared utilities
│   ├── acms_lite_client.py   # Query/store in ACMS-Lite
│   ├── git_utils.py           # Branch management
│   └── logger.py              # Structured logging
├── frontend_agent/      # Builds Electron + React
├── backend_agent/       # Builds FastAPI + MCP server
├── testing_agent/       # Writes and runs tests
└── coordinator_agent/   # Integrates and merges
```

## Agents

### Frontend Agent
- **Responsibility**: Electron shell, React UI components
- **Branch**: `frontend-agent/active`
- **Queries ACMS-Lite for**: API contracts, data models

### Backend Agent
- **Responsibility**: FastAPI, MCP server, storage integration
- **Branch**: `backend-agent/active`
- **Queries ACMS-Lite for**: Frontend requirements, schemas

### Testing Agent
- **Responsibility**: TDD test generation, checkpoint validation
- **Branch**: `testing-agent/active`
- **Queries ACMS-Lite for**: Implementation details, test requirements

### Coordinator Agent
- **Responsibility**: Interface contracts, branch merging, integration
- **Branch**: `v2.0-desktop-build` (main development branch)
- **Queries ACMS-Lite for**: Project status, blockers

## Workflow

1. **Coordinator** defines interface contracts → stores in ACMS-Lite
2. **All agents** query ACMS-Lite for contracts
3. **Agents work in parallel** on separate branches
4. **Agents store progress** in ACMS-Lite
5. **Coordinator** merges branches after validation

## Usage

For this build, we're using a **pragmatic hybrid approach**:

- Agents share work via ACMS-Lite (interface contracts, decisions)
- Claude Code acts as all agents (switches context)
- Git branches track parallel work
- Coordination via ACMS-Lite queries

This gives us 80% of the benefit with 20% of the complexity.

## Future Enhancement

For true autonomous agents, implement full MCP servers per agent (see `multi-agent.md` for specifications).
