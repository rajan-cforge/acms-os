# ACMS MCP Server Setup for Claude Code

This guide will help you connect Claude Code to your ACMS system, allowing this conversation (and all future Claude Code sessions) to be stored in your Universal Brain.

## What is MCP?

**Model Context Protocol (MCP)** is a standardized way for AI assistants like Claude Code to interact with external tools and data sources. Think of it as a bridge that lets Claude Code read from and write to your ACMS memory system.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Claude Code (this session!)                                 │
│  ↓                                                           │
│  Uses MCP tools: acms_store_memory, acms_search_memories    │
└───────────────────────┬─────────────────────────────────────┘
                        ↓ (stdio JSON-RPC)
┌─────────────────────────────────────────────────────────────┐
│ ACMS MCP Server (src/mcp/server.py)                         │
│  ↓                                                           │
│  12 MCP Tools Available:                                     │
│  - acms_store_memory                                        │
│  - acms_search_memories                                     │
│  - acms_get_memory                                          │
│  - acms_update_memory                                       │
│  - acms_delete_memory                                       │
│  - acms_list_memories                                       │
│  - acms_search_by_tag                                       │
│  - acms_get_conversation_context                            │
│  - acms_store_conversation_turn                             │
│  - acms_get_memory_stats                                    │
│  - acms_tier_transition                                     │
│  - acms_semantic_search                                     │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ ACMS Storage Layer (MemoryCRUD)                             │
│  ↓                                                           │
│  - PostgreSQL (metadata + full text)                        │
│  - Weaviate (768d vectors)                                  │
│  - OpenAI (embeddings)                                      │
│  - Claude (synthesis)                                       │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Setup

### Step 1: Verify ACMS is Running

First, make sure all ACMS services are running:

```bash
# Check Docker containers
docker ps

# You should see:
# - acms_postgres (port 40432)
# - acms_weaviate (ports 40480, 40481)
# - acms_redis (port 40379)
# - acms_ollama (port 40434) - optional

# Check API server
curl http://localhost:40080/health
# Should return: {"status": "healthy", ...}
```

### Step 2: Test MCP Server

Test that the MCP server can start:

```bash
cd /path/to/acms
source venv/bin/activate
source .env
python3 -m src.mcp.server
```

You should see:
```
INFO - Starting ACMS MCP Server v0.1.0
INFO - Database: postgresql://...
INFO - Weaviate: http://localhost:40480
INFO - Registered 12 MCP tools: ...
```

Press `Ctrl+C` to stop the test.

###  Step 3: Configure Claude Code MCP Settings

Claude Code uses a configuration file to discover MCP servers. Create or update your Claude Code MCP config:

**File**: `~/.config/claude-code/mcp.json`

```json
{
  "mcpServers": {
    "acms": {
      "command": "/path/to/acms/venv/bin/python3",
      "args": [
        "-m",
        "src.mcp.server"
      ],
      "cwd": "/path/to/acms",
      "env": {
        "PYTHONPATH": "/path/to/acms",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "DATABASE_URL": "postgresql://localhost:40432/acms_db",
        "WEAVIATE_URL": "http://localhost:40480"
      }
    }
  }
}
```

**Note**: Replace `${OPENAI_API_KEY}` and `${ANTHROPIC_API_KEY}` with your actual API keys, or ensure they're in your environment.

### Step 4: Restart Claude Code

After updating the MCP configuration:

1. **Quit Claude Code completely** (Cmd+Q or File → Quit)
2. **Restart Claude Code**
3. Claude Code will automatically discover and connect to your ACMS MCP server

### Step 5: Verify MCP Connection

In a new Claude Code conversation, you can verify the connection:

1. Claude Code should automatically detect the ACMS MCP server
2. You'll see "acms" in the list of available tools
3. Claude Code can now use 12 ACMS tools:
   - `acms_store_memory` - Store conversations/code/decisions
   - `acms_search_memories` - Find relevant past discussions
   - `acms_get_memory` - Retrieve specific memories
   - And 9 more...

## Usage Examples

### Example 1: Store This Conversation

In Claude Code, you can ask:

```
"Store a summary of our Universal Brain implementation to ACMS"
```

Claude will use `acms_store_memory` to save the conversation with tags like:
- `["claude-code", "universal-brain", "phase-4e", "openai", "performance"]`

### Example 2: Search Past Conversations

```
"Search ACMS for previous discussions about privacy and data retention"
```

Claude will use `acms_search_memories` to find relevant past conversations, even from ChatGPT, Gemini, or other sources!

### Example 3: Get Context for Code Changes

```
"Check ACMS for our previous decisions about PostgreSQL schema design"
```

Claude will use `acms_get_conversation_context` to retrieve relevant memories and use them to inform code changes.

### Example 4: Multi-Turn Q&A with Conversation History (NEW!)

ACMS now supports **conversation history** for multi-turn Q&A! This allows Claude to maintain context across follow-up questions:

```
User: "What is the Universal Brain?"
Claude: [Uses acms_search_memories, gets answer from ACMS]

User: "How does it work?"  ← Follow-up question
Claude: [Maintains context from previous Q&A, provides coherent answer]

User: "What are the benefits?"  ← Another follow-up
Claude: [Still remembers the conversation context]
```

**How it works**:
- The `/ask` endpoint now accepts `conversation_history` parameter
- Automatically keeps last 3 Q&A pairs (6 messages) for context
- Claude Sonnet 4.5 synthesizes answers using both:
  - Retrieved memories from ACMS
  - Previous conversation turns for coherence

**API Usage** (Direct REST API):
```bash
curl -X POST http://localhost:40080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How does the embedding work?",
    "context_limit": 5,
    "conversation_history": [
      {"role": "user", "content": "What is ACMS?"},
      {"role": "assistant", "content": "ACMS is an AI context memory system..."}
    ]
  }'
```

**Benefits**:
- Natural follow-up questions without repeating context
- Claude understands pronouns ("it", "they", "that") from previous turns
- More human-like multi-turn conversations
- Better synthesis across conversation and stored memories

## Manual Testing

You can manually test MCP tools using the provided test script:

```bash
cd /path/to/acms
source venv/bin/activate
source .env
python3 scripts/test_mcp_tools.py
```

## Troubleshooting

### Issue 1: MCP Server Not Found

**Symptom**: Claude Code doesn't show ACMS tools

**Fix**:
1. Check `~/.config/claude-code/mcp.json` exists
2. Verify paths are absolute (not relative)
3. Restart Claude Code completely (Quit and relaunch)

### Issue 2: Connection Errors

**Symptom**: "Failed to connect to MCP server"

**Fix**:
1. Ensure Docker containers are running: `docker ps`
2. Check API server is running: `curl http://localhost:40080/health`
3. Test MCP server manually: `python3 -m src.mcp.server`

### Issue 3: Environment Variables Not Found

**Symptom**: "OPENAI_API_KEY not found"

**Fix**:
Edit `~/.config/claude-code/mcp.json` and replace `${OPENAI_API_KEY}` with actual key:

```json
"env": {
  "OPENAI_API_KEY": "sk-proj-...",
  "ANTHROPIC_API_KEY": "sk-ant-..."
}
```

### Issue 4: Import Errors

**Symptom**: "ModuleNotFoundError: No module named 'src'"

**Fix**:
1. Check `"PYTHONPATH": "/path/to/acms"` in mcp.json
2. Check `"cwd": "/path/to/acms"` in mcp.json

## What Gets Stored?

When you use `acms_store_memory` in Claude Code:

1. **Content**: Full conversation text (up to 50K chars per memory)
2. **Tags**: Auto-detected or manually specified
3. **Tier**: SHORT (default for conversations)
4. **Phase**: "claude-code" for source tracking
5. **Metadata**:
   - `source`: "claude-code"
   - `session_id`: (if available)
   - `timestamp`: Auto-added

6. **Embeddings**: OpenAI 768d vectors (for search)
7. **Storage**:
   - PostgreSQL: Full content + metadata
   - Weaviate: 768d vector + searchable properties

## Privacy Considerations

### What Leaves Your Machine:

1. **To OpenAI**: Memory content for embedding (30-day retention)
2. **To Claude API**: When using `/ask` endpoint for synthesis

### What NEVER Leaves Your Machine:

1. **LOCAL_ONLY memories**: Always blocked from APIs
2. **PostgreSQL data**: Stored locally only
3. **Weaviate vectors**: Stored locally only

### How to Control Privacy:

```python
# In Claude Code, when storing:
acms_store_memory(
    content="My SSN is 123-45-6789",
    tags=["personal", "sensitive"],
    # ACMS will auto-detect and mark as LOCAL_ONLY
)

# Later, when searching:
# LOCAL_ONLY memories are excluded from API calls automatically
```

## Benefits of MCP Integration

1. **Universal Brain**: All conversations (Claude Code, ChatGPT, Gemini, Claude, Slack) in one place
2. **Persistent Memory**: Claude Code can remember past sessions
3. **Cross-App Synthesis**: Find connections between coding sessions and research chats
4. **Timeline Tracking**: See how ideas evolved over time
5. **Smart Search**: Semantic search finds relevant context automatically

## Next Steps

After setup is complete:

1. **Test the connection** with a simple store/search
2. **Store this conversation** to ACMS for reference
3. **Use it naturally** - Claude Code will proactively use ACMS when helpful
4. **Check desktop app** - See your Claude Code conversations alongside others

## Support

If you encounter issues:

1. Check logs: `~/.config/claude-code/logs/mcp-acms.log`
2. Test manually: `python3 -m src.mcp.server`
3. Verify services: `docker ps && curl http://localhost:40080/health`
4. Review this guide's troubleshooting section

---

**Ready to test?** Let's store this conversation to ACMS! 🧠✨
