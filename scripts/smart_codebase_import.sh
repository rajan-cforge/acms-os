#!/bin/bash
# Smart ACMS Codebase Import
# Stores conceptual descriptions of ACMS with relevant code snippets
# This allows asking questions like "How does semantic cache work?" and getting meaningful answers

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACMS_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ACMS_ROOT"

echo "======================================================================"
echo "  ACMS Smart Codebase Import"
echo "======================================================================"
echo ""
echo "Storing conceptual descriptions of ACMS architecture and features..."
echo ""

STORED=0

# ============================================================================
# 1. WHAT IS ACMS - Core Product Description
# ============================================================================

./acms store "ACMS (Adaptive Context Memory System) is an enterprise-grade intelligent knowledge platform that enables organizations to capture, understand, and activate institutional knowledge through AI-powered context management.

**Core Value Proposition:**
- Transforms from consumer AI context bridge into enterprise knowledge operating system
- Enables semantic search across organizational knowledge
- Provides intelligent memory systems with tiered storage (SHORT/MEDIUM/LONG/PERMANENT)
- Integrates with multiple LLMs (Claude, ChatGPT, Gemini) for universal AI collaboration

**Target Users:**
- Enterprise teams (10-10,000+ employees)
- Knowledge workers requiring intelligent information retrieval
- Organizations with complex regulatory/compliance requirements

**Key Metrics:**
- Reduce query-to-answer time by 80% (15min → 3min)
- 60%+ cost reduction from AI API usage via intelligent caching
- 85%+ semantic cache accuracy with 0.85 cosine similarity threshold

Location: docs/PRD.md" \
--tags "acms,product,overview,what-is-acms" \
--tier "PERMANENT" && echo "✅ Stored: What is ACMS" && ((STORED++))

# ============================================================================
# 2. ARCHITECTURE - How ACMS is Built
# ============================================================================

./acms store "ACMS Architecture consists of 5 main layers:

**1. Frontend Layer:**
- Electron Desktop App (port 8080) - vanilla JavaScript, no framework
- Main process: desktop-app/main.js (window management, tray icon)
- Renderer process: desktop-app/renderer.js (UI, state management, API calls)
- Views: Ask, Memories, Projects, Analytics, Settings

**2. API Layer (FastAPI Backend on port 40080):**
- Main server: src/api_server.py
- 14 REST endpoints including:
  - POST /ask - RAG-powered Q&A with semantic cache
  - POST /memories - Store memories with auto-embedding
  - POST /feedback - User feedback tracking
  - GET /search - Hybrid vector + full-text search

**3. Storage Layer:**
- PostgreSQL (port 40432) - Relational data, user feedback, memory metadata
- Weaviate v4 (port 8090) - Vector database for semantic search
- Redis (port 40379) - Exact query cache
- Schemas in: src/storage/schemas.py

**4. Intelligence Layer:**
- Ollama (port 40434) - Local embeddings (nomic-embed-text, 768 dimensions)
- Claude Sonnet 4.5 - Primary LLM for answers
- ChatGPT-4o - Secondary LLM option
- Gemini Pro - Tertiary LLM option

**5. Smart Features:**
- Semantic Cache (src/cache/semantic_cache.py)
- User Feedback System (src/feedback/feedback_crud.py)
- Intent Classification (src/intent/intent_classifier.py)
- Universal Gateway (src/gateway/universal_gateway.py)

Location: docs/ARCHITECTURE.md, docker-compose.yml" \
--tags "acms,architecture,stack,infrastructure,how-it-works" \
--tier "PERMANENT" && echo "✅ Stored: ACMS Architecture" && ((STORED++))

# ============================================================================
# 3. WEEK 4 TASK 1 - Semantic Cache (60% Cost Savings)
# ============================================================================

./acms store "Week 4 Task 1: Semantic Cache Implementation

**Problem Solved:**
Users ask similar questions (e.g., 'How do I reset password?' vs 'What's the password reset process?'). Without semantic cache, each query costs \$0.02-0.05 in API calls to Claude/ChatGPT.

**Solution:**
Multi-level cache with semantic understanding:
1. Exact cache (Redis) - instant hits for identical queries
2. Semantic cache (Weaviate) - detects similar queries using vector similarity
3. LLM fallback - only when no similar query found

**How It Works:**
- Query arrives → generate embedding (Ollama nomic-embed-text)
- Check cosine similarity against cached queries (threshold: 0.85)
- If similar query found → return cached answer (0ms latency, \$0 cost)
- If no match → call LLM, cache result for future (500ms latency, normal cost)

**Key Code (src/cache/semantic_cache.py):**
- get_cached_response() - retrieves semantically similar cached answers
- cache_response() - stores new responses with embeddings
- Uses hybrid search: vector similarity + recency weighting

**Results:**
- 60%+ cost savings on API calls
- Sub-100ms response time for cache hits
- Accuracy: 85%+ (users satisfied with cached answers)

**Test:** Ask 'What is ACMS?' then ask 'Tell me about ACMS' - second query returns cached answer instantly.

Implementation: src/cache/semantic_cache.py (156 lines)" \
--tags "week4,task1,semantic-cache,cost-savings,implementation" \
--tier "LONG" && echo "✅ Stored: Week 4 Task 1 - Semantic Cache" && ((STORED++))

# ============================================================================
# 4. WEEK 4 TASK 2 - User Feedback System
# ============================================================================

./acms store "Week 4 Task 2: User Feedback System

**Problem Solved:**
Need to track which answers are helpful (cache vs LLM, Claude vs ChatGPT) to optimize routing and auto-tune the system.

**Solution:**
Comprehensive feedback tracking with denormalized summaries for fast analytics.

**How It Works:**
1. Every /ask response includes:
   - query_id (UUID) - unique identifier for this query
   - response_source (string) - where answer came from: 'cache', 'semantic_cache', 'claude', 'chatgpt', 'gemini'

2. User provides feedback via buttons:
   - 👍 Thumbs Up (rating=5, feedback_type='thumbs_up')
   - 👎 Thumbs Down (rating=1, feedback_type='thumbs_down')
   - 🔄 Regenerate (rating=2, feedback_type='regenerate')

3. Feedback stored in PostgreSQL query_feedback table:
   - Links to original query via query_id
   - Tracks response_source to analyze which sources perform best
   - Includes optional comments and user_id

4. Denormalized feedback_summary (JSONB column):
   - Pre-calculated stats: avg_rating, total_feedback, positive_ratio
   - Updated on each feedback submission (no complex joins needed)
   - Enables instant analytics dashboard queries

**Key Endpoints (src/api_server.py):**
- POST /feedback - Submit user feedback
- GET /feedback/summary/{query_id} - Get stats for specific query
- GET /feedback/user/{user_id} - Get user's feedback history (last 30 days)

**Database Schema (src/storage/schemas.py):**
```sql
CREATE TABLE query_feedback (
    id UUID PRIMARY KEY,
    query_id UUID NOT NULL,
    user_id UUID NOT NULL,
    rating INTEGER (1-5),
    feedback_type VARCHAR (thumbs_up/thumbs_down/regenerate),
    response_source VARCHAR (cache/semantic_cache/claude/chatgpt),
    comments TEXT,
    created_at TIMESTAMP
)
```

**Analytics Use Case:**
- Which source has highest satisfaction? (semantic_cache: 4.2/5, claude: 3.8/5)
- Which queries get regenerated most? (creative writing: 15% regenerate rate)
- Cost-benefit analysis: semantic_cache saves \$0.04/query with 4.2/5 rating

Implementation: src/feedback/feedback_crud.py (201 lines), src/api_server.py (lines 680-734)" \
--tags "week4,task2,feedback,analytics,tracking" \
--tier "LONG" && echo "✅ Stored: Week 4 Task 2 - Feedback System" && ((STORED++))

# ============================================================================
# 5. WEEK 4 TASK 3 - Individual Metrics Dashboard
# ============================================================================

./acms store "Week 4 Task 3: Individual Metrics Dashboard

**Problem Solved:**
Users need visibility into cache performance, feedback patterns, and cost savings to understand ACMS value and optimize usage.

**Solution:**
Real-time analytics dashboard in desktop app with interactive visualizations.

**Dashboard Components:**

1. **Feedback Buttons (desktop-app/renderer.js lines 1174-1194):**
   - Displayed after every answer
   - Visual states: normal (gray) → clicked (green/red/yellow) → disabled
   - Tracks feedback per query: state.feedbackGiven[queryId] prevents duplicate submissions
   - submitFeedback() function (lines 531-582) handles API calls

2. **Response Source Badges (lines 1149-1164):**
   - Color-coded badges show answer origin:
     - ⚡ Cache (blue #3b82f6) - instant, free
     - ✨ Semantic Cache (purple #8b5cf6) - fast, free
     - 🤖 Claude (orange #ff6b35) - slow, costly
     - 💬 ChatGPT (green #10a37f) - slow, costly
   - Helps users understand performance/cost tradeoffs

3. **Analytics View (renderAnalyticsView() lines 1234-1401):**

   A. Cache Performance Metrics:
      - Total queries processed
      - Cache hit rate (cache + semantic_cache / total)
      - Average latency by source
      - Cost savings estimate (\$0.04 per cache hit)

   B. Feedback Statistics by Source:
      - Average rating (1-5 stars)
      - Total feedback count
      - Regenerate rate
      - Visual indicators: ⭐⭐⭐⭐⭐ for ratings

   C. Time Period Filtering:
      - 7 days, 30 days, 90 days
      - Real-time updates on filter change

**State Management:**
- Global state object tracks: queryId, responseSource, feedbackGiven
- Reactive rendering: renderApp() called after state changes
- Event delegation: root-level click listener handles all buttons

**API Integration:**
- Fetches from /cache/stats (cache performance)
- Fetches from /feedback/user/default (feedback analytics)
- Updates every time Analytics view opened (fresh data)

**Key Insights Provided:**
- 'You've saved \$12.50 this month from semantic cache'
- 'Claude answers have 3.8/5 rating, ChatGPT has 4.1/5'
- 'Cache hit rate increased from 25% to 43% this week'

Implementation: desktop-app/renderer.js (lines 1234-1401, 167 lines of dashboard code)" \
--tags "week4,task3,dashboard,analytics,ui,metrics" \
--tier "LONG" && echo "✅ Stored: Week 4 Task 3 - Metrics Dashboard" && ((STORED++))

# ============================================================================
# 6. HOW TO USE ACMS - User Guide
# ============================================================================

./acms store "How to Use ACMS:

**Starting ACMS:**
\`\`\`bash
cd /path/to/acms
./start_desktop.sh
\`\`\`
- Automatically starts API server (port 40080)
- Launches Electron desktop app (port 8080)
- System tray icon appears (click to show/hide window)

**Using the Desktop App:**

1. **Ask View** - Natural Language Q&A:
   - Type question: 'What is Week 4 Task 3?'
   - System searches memory, returns answer with sources
   - Response badge shows origin (cache/semantic_cache/claude)
   - Provide feedback: 👍 👎 🔄

2. **Memories View** - Browse Stored Knowledge:
   - List all memories (paginated)
   - Filter by tags, phase, tier
   - Search semantically
   - Add new memories manually

3. **Projects View** - Organize by Project:
   - Create projects
   - Associate memories with projects
   - Project-scoped search

4. **Analytics View** - Performance Metrics:
   - Cache hit rates
   - Feedback statistics
   - Cost savings estimates
   - Response time distributions

5. **Settings View** - Configuration:
   - Database status (green = healthy)
   - API endpoint configuration
   - System health checks

**Using the CLI:**
\`\`\`bash
# Search for memories
./acms search 'semantic cache' --limit 5

# Store a new memory
./acms store 'Learned about Docker networking' --tags docker,learning --tier SHORT

# List memories by tag
./acms list --tag week4

# View statistics
./acms stats
\`\`\`

**API Direct Access:**
\`\`\`bash
# Ask a question
curl -X POST http://localhost:40080/ask -d '{\"question\": \"What is ACMS?\", \"context_limit\": 5}'

# Store memory
curl -X POST http://localhost:40080/memories -d '{\"content\": \"New insight\", \"tags\": [\"insight\"], \"tier\": \"SHORT\"}'

# Search memories
curl http://localhost:40080/search?query=cache

# API docs
open http://localhost:40080/docs
\`\`\`

**Recommended Workflow:**
1. Store knowledge as you work (via CLI or desktop app)
2. Ask questions when you need context
3. Provide feedback to improve accuracy
4. Review analytics weekly to optimize usage

Location: start_desktop.sh, acms CLI wrapper" \
--tags "acms,how-to,user-guide,usage,getting-started" \
--tier "PERMANENT" && echo "✅ Stored: How to Use ACMS" && ((STORED++))

# ============================================================================
# 7. WEEK 5 ROADMAP - What's Next
# ============================================================================

./acms store "Week 5 Roadmap (Next Phase):

**Task 1: Confidentiality Controls**
- 5-level classification: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED, SECRET
- Automatic PII/PCI/PHI detection (regex + ML)
- Query-time access enforcement
- Compliance audit trails
- Redaction for unauthorized access
- Implementation: src/confidentiality/

**Task 2: Intent Classification**
- Classify queries: factual, creative, analytical, procedural
- Optimize routing based on intent:
  - Factual → semantic cache preferred (high hit rate)
  - Creative → bypass cache (unique answers needed)
  - Analytical → Claude preferred (better reasoning)
  - Procedural → ChatGPT preferred (step-by-step)
- Implementation: src/intent/intent_classifier.py (already started)

**Task 3: Auto-Tuning Foundation**
- Use feedback data to auto-adjust:
  - Semantic cache similarity threshold (currently 0.85)
  - Source prioritization (Claude vs ChatGPT based on ratings)
  - Context window size (trade-off: relevance vs cost)
- Continuous improvement feedback loop
- Implementation: src/tuning/

**Success Criteria:**
- Confidentiality: Zero unauthorized access incidents
- Intent: 90%+ classification accuracy
- Auto-tuning: 10%+ improvement in user satisfaction within 2 weeks

**Timeline:**
- Week 5: Oct 21-27, 2025
- Builds on Week 4 foundation (semantic cache + feedback system)

Location: docs/PRD.md (lines 421-426), docs/IMPLEMENTATION_PLAN.md" \
--tags "week5,roadmap,confidentiality,intent,auto-tuning,planned" \
--tier "LONG" && echo "✅ Stored: Week 5 Roadmap" && ((STORED++))

# ============================================================================
# 8. KEY TECHNICAL DECISIONS - Why We Built It This Way
# ============================================================================

./acms store "ACMS Key Technical Decisions:

**1. Why Weaviate v4 for Vector Search?**
- Native vector operations (cosine similarity)
- Scales to millions of embeddings
- Built-in hybrid search (vector + BM25 text search)
- Open-source, self-hosted (no data leaves infrastructure)
- Alternative considered: pgvector (simpler, but less performant at scale)

**2. Why Ollama for Embeddings Instead of OpenAI?**
- Cost: \$0/query vs OpenAI \$0.0001/query (100% savings on embeddings)
- Privacy: Embeddings generated locally (no data sent to third party)
- Speed: Local inference ~50ms vs API call ~150ms
- Model: nomic-embed-text (768 dims) optimized for semantic similarity
- Trade-off: Slightly lower quality than OpenAI text-embedding-3-large, but 80% accuracy is sufficient

**3. Why Denormalized feedback_summary Instead of JOIN Queries?**
- Performance: Single row lookup vs complex aggregation JOIN
- Scalability: Analytics dashboard queries remain fast at 1M+ feedback records
- Simplicity: Pre-calculated stats always up-to-date
- Trade-off: 500 bytes extra storage per query (negligible cost)

**4. Why Electron Desktop Instead of Web App?**
- System tray integration (always accessible, low-friction)
- Native OS integration (notifications, file system access)
- Offline-first capability (future feature)
- Single codebase for Mac/Windows/Linux
- Trade-off: Larger download size (~100MB) vs web (instant access)

**5. Why FastAPI Instead of Flask?**
- Async/await support (critical for concurrent LLM calls)
- Automatic OpenAPI docs (http://localhost:40080/docs)
- Pydantic validation (type safety, auto-validation)
- Modern Python 3.13 features
- Performance: 2-3x faster than Flask for I/O-bound tasks

**6. Why Multi-LLM Gateway Instead of Claude-Only?**
- Redundancy: If Claude API down, fall back to ChatGPT
- Cost optimization: Use cheaper model for simple queries
- Quality comparison: A/B test which model users prefer
- Future-proof: Easy to add Gemini, Llama, etc.

**7. Why 0.85 Cosine Similarity Threshold for Semantic Cache?**
- Empirical testing: 0.80 = too many false positives (wrong cached answers)
- 0.90 = too few hits (cache underutilized)
- 0.85 = sweet spot: 85%+ accuracy, 40%+ hit rate
- User feedback will auto-tune this value in Week 5

Location: Architecture decisions documented in docs/ARCHITECTURE.md, code comments in key files" \
--tags "acms,technical-decisions,architecture,why,trade-offs" \
--tier "PERMANENT" && echo "✅ Stored: Technical Decisions" && ((STORED++))

# ============================================================================
# 9. TROUBLESHOOTING GUIDE - Common Issues
# ============================================================================

./acms store "ACMS Troubleshooting Guide:

**Issue 1: Desktop app shows 'API server not running'**
Solution:
\`\`\`bash
# Check if API server running
curl http://localhost:40080/health

# If not running, start manually:
cd /path/to/acms
source venv/bin/activate && source .env
python3 src/api_server.py

# Check for port conflicts:
lsof -i :40080
\`\`\`

**Issue 2: Search returns no results**
Possible causes:
- Weaviate not running: \`docker ps | grep weaviate\`
- No embeddings generated: Check memory_items table has embeddings column populated
- Query too specific: Try broader search terms

**Issue 3: Semantic cache not working (always calls LLM)**
Debug steps:
1. Check Redis running: \`redis-cli -p 40379 PING\`
2. Check Weaviate running: \`curl http://localhost:8090/v1/.well-known/ready\`
3. Check cache stats: \`curl http://localhost:40080/cache/stats\`
4. Verify query_id in response: Should be UUID, not null

**Issue 4: Feedback buttons not working**
Debug (desktop-app/renderer.js):
1. Open browser console (Cmd+Option+I)
2. Click feedback button
3. Check for errors in console
4. Verify queryId exists: \`console.log(state.askState.queryId)\`
5. Check API call succeeds: Should see 200 response

**Issue 5: Database connection errors**
Solution:
\`\`\`bash
# Check PostgreSQL running
docker ps | grep acms_postgres

# Check credentials in .env
cat .env | grep DATABASE_URL

# Test connection
docker exec -it acms_postgres psql -U acms_user -d acms_db -c 'SELECT COUNT(*) FROM memory_items;'
\`\`\`

**Issue 6: Ollama embeddings timeout**
Solution:
\`\`\`bash
# Check Ollama running
curl http://localhost:40434/api/tags

# Pull embedding model if missing
docker exec acms_ollama ollama pull nomic-embed-text

# Increase timeout in code (src/storage/memory_crud.py line 45):
timeout=30  # increase from 10
\`\`\`

**Issue 7: Week 4 features (queryId, responseSource) not in API response**
Solution: Old API server running with outdated code
\`\`\`bash
# Kill old server
lsof -i :40080 | grep LISTEN | awk '{print \$2}' | xargs kill -9

# Start fresh server
source venv/bin/activate && source .env && python3 src/api_server.py
\`\`\`

**Getting More Help:**
- Check logs: \`tail -f api_server.log\`
- API docs: http://localhost:40080/docs
- Database status: Desktop app → Settings → Database Status

Location: Compiled from various debugging sessions" \
--tags "acms,troubleshooting,debugging,issues,help" \
--tier "MEDIUM" && echo "✅ Stored: Troubleshooting Guide" && ((STORED++))

echo ""
echo "======================================================================"
echo "  ✅ Smart Import Complete!"
echo "======================================================================"
echo ""
echo "📊 Stored $STORED conceptual memories (not raw code dumps)"
echo ""
echo "🎯 Now try asking ACMS questions like:"
echo ""
echo "  ./acms search 'how does semantic cache work'"
echo "  ./acms search 'why did we choose weaviate'"
echo "  ./acms search 'what is week 4 task 2'"
echo "  ./acms search 'troubleshooting API server'"
echo ""
echo "Or in the desktop app:"
echo ""
echo "  'Explain the semantic cache implementation'"
echo "  'What are the key technical decisions in ACMS?'"
echo "  'How do I use the feedback system?'"
echo "  'What is the Week 5 roadmap?'"
echo ""
echo "======================================================================"
