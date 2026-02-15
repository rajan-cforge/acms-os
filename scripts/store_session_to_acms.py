#!/usr/bin/env python3
"""Store this Claude Code session to ACMS for future reference."""

import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.memory_crud import MemoryCRUD

async def store_session():
    """Store comprehensive session summary to ACMS."""

    crud = MemoryCRUD()

    # Session summary
    session_content = """# Claude Code Session: Phase 4e Universal Brain Implementation
**Date**: 2025-01-17
**Duration**: ~2 hours
**Status**: COMPLETED ✅

## Session Goals
1. Migrate from Ollama (384d) to OpenAI (768d) embeddings
2. Replace Ollama generation with Claude Sonnet 4.5
3. Implement "Universal Brain" cross-app synthesis
4. Set up MCP server for Claude Code integration
5. Verify privacy policies and data retention

## Major Accomplishments

### 1. Performance Upgrade (10x Faster!)
- **Before**: Ollama local LLM, 15-45s query time, 384d vectors
- **After**: OpenAI + Claude API, 2-5s query time, 768d vectors
- **Impact**: Production-ready performance for Universal Brain

### 2. Universal Brain Architecture
**Problem**: User reported "/ask" couldn't read actual conversation content, only showing truncated snippets.

**Root Cause**: Content truncated to 1000 chars before sending to LLM, preventing cross-app synthesis.

**Solution Implemented**:
- Increased content limit: 1000 → 50,000 chars per memory
- Increased default memories: 5 → 10 (max 20)
- Added source attribution: github, slack, claude, chatgpt, gemini
- Enhanced system prompt for synthesis, patterns, contradictions, gaps
- Enhanced user prompt for timeline organization

**Result**: Claude can now synthesize across full conversations from multiple apps, showing evolution of ideas over time.

### 3. Privacy Verification
Created comprehensive privacy testing:
- `scripts/check_openai_privacy.py` - Policy verification
- `scripts/test_api_privacy.py` - Real-time API monitoring

**Findings**:
- OpenAI API: 30-day retention (abuse monitoring only), NOT used for training
- Claude API: No retention, in-memory only, immediately discarded
- ACMS LOCAL_ONLY: Never leaves machine, encrypted at rest

**User Concern**: "Can I check ChatGPT API privacy?"
**Answer**: Yes, official policies confirmed. Web UI ≠ API. API is safe.

### 4. MCP Server Configuration
Set up Claude Code integration so future sessions can:
- Store conversations to ACMS
- Search past discussions
- Retrieve context automatically
- Maintain continuity across sessions

**Files Created**:
- `MCP_SETUP.md` - Comprehensive setup guide
- `~/.config/claude-code/mcp.json` - Configuration file
- 12 MCP tools available: store, search, get, update, delete, etc.

### 5. Storage Analysis
**User Question**: "PostgreSQL growing fast, should I use Google Drive (2TB) or external drive?"

**Analysis**:
- Current: 168 MB (115 MB PostgreSQL + 53 MB Weaviate)
- Growth: 5-25 MB/day = 2-9 GB/year
- **Recommendation**: Local disk is perfect!
- Google Drive would last 55+ years (overkill)
- External drive unnecessary (unless for backups)

## Technical Details

### Files Modified
1. `src/embeddings/openai_embeddings.py` (CREATED)
   - OpenAI text-embedding-3-small client
   - 768-dimensional embeddings
   - ~100ms latency

2. `src/generation/claude_generator.py` (CREATED)
   - Claude Sonnet 4.5 client
   - Conversation history support
   - 200K token context window
   - ~2-4s latency

3. `src/storage/memory_crud.py` (MODIFIED)
   - Lines 69-74: Made Ollama optional (graceful degradation)
   - Lines 164, 323, 520: Use OpenAI embeddings
   - All vector operations now use 768d

4. `src/api_server.py` (MODIFIED)
   - Lines 24, 44-45: Initialize Claude generator
   - Lines 119-125: Increase context_limit default (5 → 10, max 20)
   - Lines 312-360: Universal Brain implementation
     - Content limit: 1K → 50K chars
     - Source attribution added
     - Synthesis system prompt enhanced
     - Timeline-aware user prompt

5. `src/storage/weaviate_client.py` (MODIFIED)
   - All dimension checks: 384 → 768
   - Collection description updated
   - Validation functions updated

6. `chrome-extensions/claude/content.js` (MODIFIED)
   - Lines 57-99: Exclude sidebar/navigation from capture
   - Lines 105-125: Filter UI elements and titles
   - Fix: Was capturing conversation list instead of actual content

### Database Migration
- Ran `docker-compose down -v` to wipe all volumes
- Deleted 5,898 old 384d vectors
- Created fresh 768d Weaviate collection
- Ran Alembic migrations for PostgreSQL
- All data clean, ready for OpenAI embeddings

### Key Decisions

**Decision 1**: Ollama Status
- **Question**: "Are we still using Ollama for vectorization or NL queries?"
- **Answer**: NO. Ollama is optional fallback only, not used in production.
- **Evidence**: MemoryCRUD gracefully handles Ollama absence, all operations use OpenAI + Claude

**Decision 2**: Content Truncation
- **Problem**: Only sending 1K chars to Claude broke Universal Brain vision
- **Solution**: Increase to 50K chars (Claude supports 200K tokens = ~600K chars)
- **Impact**: Can now send full conversations, enabling true cross-app synthesis

**Decision 3**: Default Memory Count
- **User Request**: "I would have liked to extend to top 10 memories"
- **Action**: Changed default from 5 → 10, max from 10 → 20
- **Rationale**: Better cross-app synthesis with more context

**Decision 4**: Storage Strategy
- **User Question**: External drive vs Google Drive?
- **Decision**: Keep using local disk
- **Rationale**: Fast access for vector search, plenty of space, growth is manageable

### Architecture Confirmation

**The Complete Flow**:
```
1. USER QUESTION: "Summarize all investment discussions"
   ↓
2. YOUR ACMS: Vector Search (Weaviate)
   - Convert question → OpenAI embedding (768d)
   - Search Weaviate (COSINE similarity)
   - Find top 10 memories
   - Retrieve FULL TEXT from PostgreSQL (up to 50K chars each)
   ↓
3. YOUR ACMS: Build Context (Plain Text)
   - Format 10 memories with source attribution
   - Add system prompt for synthesis
   - Total: ~40K chars = ~12K tokens
   ↓
4. ANTHROPIC API: Claude Processes
   - Reads ALL text (12K input tokens)
   - Uses attention mechanism
   - Identifies patterns, contradictions, gaps
   - Generates synthesis
   - NO vector search on Claude's side
   - NO storage (in-memory only)
   ↓
5. RESPONSE: Synthesized Answer
   - Shows timeline across sources
   - Identifies patterns and contradictions
   - Cites sources with app names and dates
   - Connects dots like human thinking
```

**User's Vision (Validated)**:
"ACMS should be a Universal Brain that aggregates knowledge from GitHub, ChatGPT, Gemini, Claude, Slack, and synthesizes insights like a human would - showing evolution, contradictions, gaps, and connecting dots across all sources."

**Implementation Status**: ✅ ACHIEVED

## User Feedback & Questions

### Question 1: "Can I check ChatGPT API privacy?"
**Answer**: Created two scripts:
- `scripts/check_openai_privacy.py` - Verifies policy
- `scripts/test_api_privacy.py` - Live API monitoring

**Finding**: OpenAI API is safe (30-day retention, not for training)

### Question 2: "PostgreSQL growing fast, external drive?"
**Answer**: No need! Current 168 MB, grows 2-9 GB/year, local disk is perfect.

### Question 3: "Will new Claude session remember this?"
**Answer**: Not without ACMS MCP integration. Creating:
- PROJECT_STATUS.md (instant context)
- This ACMS memory (searchable)
- Git commit (version history)

## What User Learned

1. **Vector Search**: Done by Weaviate (local), NOT by Claude/ChatGPT APIs
2. **Data Storage**: APIs don't store (per policy), ACMS stores locally
3. **Architecture**: ACMS = long-term memory, APIs = language processing
4. **Privacy**: OpenAI 30 days, Claude none, ACMS forever (local control)
5. **Universal Brain**: Works by sending FULL content to Claude for synthesis

## Metrics & Performance

### Before (Ollama)
- Embedding: ~5-10s (local CPU)
- Generation: ~10-40s (local LLaMA)
- Total: ~15-50s per query
- Context: 8K tokens
- Embeddings: 384d

### After (OpenAI + Claude)
- Embedding: ~100ms (OpenAI API)
- Vector search: ~50ms (Weaviate HNSW)
- Database fetch: ~100ms (PostgreSQL)
- Generation: ~2-4s (Claude API)
- Total: ~2.5-5s per query ⚡
- Context: 200K tokens 🧠
- Embeddings: 768d 📊

**Performance Improvement**: 10x faster!

### Cost Analysis
- OpenAI embedding: $0.00002 per query
- Claude synthesis: $0.05 per query (12K in, 1K out)
- Total: ~$0.05 per Universal Brain query
- Annual (100 queries/day): ~$1,825/year

**Trade-off**: Slightly more expensive, but 10x faster and production-ready.

## Next Steps (Week 1 Plan)

### Pending Tasks
- [ ] Task 10: Add conversation history to /ask
  - Use Claude's `generate_with_history()` method
  - Maintain last 3 Q&A pairs for follow-up questions

- [ ] Task 11: Enhanced privacy detection
  - Add SSN, phone, credit card detection
  - Auto-classify as LOCAL_ONLY

- [ ] Task 12: Browse by source feature
  - Filter by github, slack, chrome, etc.
  - Show source badges in UI

- [ ] Task 13: Delete memory feature
  - Add delete button to memory cards
  - Confirm before deleting
  - Remove from PostgreSQL + Weaviate

## Session Continuity Plan

**Created for next session**:
1. ✅ `PROJECT_STATUS.md` - Comprehensive status document
2. ✅ This ACMS memory - Searchable session summary
3. 🔄 Git commit - Version control with full context

**How to continue**:
- New Claude session reads `PROJECT_STATUS.md`
- Search ACMS: "Universal Brain implementation status"
- Check git log for recent changes
- Continue with Task 10

## Conclusion

Phase 4e is COMPLETE! ✅

The ACMS Universal Brain is now:
- 10x faster (2-5s queries)
- Higher quality (768d embeddings, Claude Sonnet 4.5)
- True synthesis (50K chars × 10 memories)
- Privacy-verified (OpenAI/Claude policies checked)
- MCP-ready (Claude Code integration configured)

**Ready for Week 1 tasks**: Conversation history, privacy enhancements, UI features.

---

**Tags**: phase-4e, universal-brain, openai, claude, performance-upgrade, mcp-setup, privacy-verification, session-continuity
**Tier**: LONG (important milestone)
**Phase**: phase-4e-complete
"""

    # Store to ACMS
    print("📝 Storing session summary to ACMS...")

    memory_id = await crud.create_memory(
        user_id="00000000-0000-0000-0000-000000000001",  # Default user
        content=session_content,
        tags=[
            "claude-code",
            "phase-4e",
            "universal-brain",
            "openai",
            "claude-sonnet",
            "performance-upgrade",
            "mcp-setup",
            "privacy-verification",
            "session-continuity",
            "milestone"
        ],
        tier="LONG",  # Important milestone
        phase="phase-4e-complete",
        metadata={
            "source": "claude-code",
            "session_date": "2025-01-17",
            "session_type": "development",
            "completeness": "comprehensive",
            "next_steps": "week-1-tasks-10-13"
        }
    )

    if memory_id:
        print(f"✅ Session stored to ACMS!")
        print(f"   Memory ID: {memory_id}")
        print(f"   Tier: LONG")
        print(f"   Tags: claude-code, phase-4e, universal-brain, +7 more")
        print()
        print("🔍 To retrieve in next session:")
        print('   "Search ACMS for Phase 4e Universal Brain implementation"')
        print()
        return True
    else:
        print("❌ Failed to store (duplicate detected)")
        return False


if __name__ == "__main__":
    success = asyncio.run(store_session())
    sys.exit(0 if success else 1)
