#!/bin/bash
# Bulk Import ACMS Codebase to Memory System
# This script stores all important code files and documentation in ACMS memory
# so you can ask questions about the entire codebase

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACMS_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ACMS_ROOT"

echo "======================================================================"
echo "  ACMS Codebase Bulk Import"
echo "======================================================================"
echo ""
echo "This will store all code files and documentation in ACMS memory."
echo "You'll then be able to ask questions like:"
echo "  - 'How does the semantic cache work?'"
echo "  - 'What endpoints does the API have?'"
echo "  - 'How is the feedback system implemented?'"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

# Counter for stored files
STORED=0
FAILED=0

# Function to store a file in ACMS
store_file() {
    local file_path="$1"
    local tags="$2"
    local tier="${3:-LONG}"
    local category="$4"

    echo -n "  Storing: $file_path ... "

    # Read file content
    if [ ! -f "$file_path" ]; then
        echo "❌ NOT FOUND"
        ((FAILED++))
        return
    fi

    # Get file size
    file_size=$(wc -c < "$file_path")
    if [ "$file_size" -gt 50000 ]; then
        echo "⚠️  SKIPPED (too large: ${file_size} bytes)"
        return
    fi

    # Read content
    content=$(cat "$file_path")

    # Create description with file path and category
    description="$category: $file_path

$content"

    # Store using acms CLI
    if ./acms store "$description" --tags "$tags" --tier "$tier" > /dev/null 2>&1; then
        echo "✅"
        ((STORED++))
    else
        echo "❌ FAILED"
        ((FAILED++))
    fi
}

echo ""
echo "======================================================================"
echo "  Phase 1: Documentation"
echo "======================================================================"

store_file "docs/PRD.md" "documentation,prd,product" "PERMANENT" "Product Requirements Document"
store_file "docs/ARCHITECTURE.md" "documentation,architecture,technical" "PERMANENT" "Architecture Documentation"
store_file "docs/API.md" "documentation,api,endpoints" "PERMANENT" "API Reference"
store_file "docs/IMPLEMENTATION_PLAN.md" "documentation,implementation,plan" "PERMANENT" "Implementation Plan"
store_file "CLAUDE.md" "documentation,development,claude" "PERMANENT" "Development Guide"
store_file "README.md" "documentation,readme" "PERMANENT" "README"

echo ""
echo "======================================================================"
echo "  Phase 2: Core Backend Code"
echo "======================================================================"

store_file "src/api_server.py" "backend,api,fastapi,week4" "LONG" "Main API Server"
store_file "src/storage/memory_crud.py" "backend,storage,database,crud" "LONG" "Memory CRUD Operations"
store_file "src/storage/weaviate_client.py" "backend,storage,vector,weaviate" "LONG" "Weaviate Vector DB Client"
store_file "src/storage/schemas.py" "backend,storage,schemas,models" "LONG" "Database Schemas"
store_file "src/gateway/claude_direct.py" "backend,gateway,claude,llm" "LONG" "Claude Gateway"
store_file "src/gateway/universal_gateway.py" "backend,gateway,universal,routing" "LONG" "Universal LLM Gateway"
store_file "src/gateway/chatgpt_direct.py" "backend,gateway,chatgpt,llm" "LONG" "ChatGPT Gateway"

echo ""
echo "======================================================================"
echo "  Phase 3: Week 4 Features"
echo "======================================================================"

store_file "src/cache/semantic_cache.py" "backend,cache,semantic,week4,task1" "LONG" "Semantic Cache Implementation"
store_file "src/feedback/feedback_crud.py" "backend,feedback,database,week4,task2" "LONG" "Feedback System CRUD"
store_file "src/intent/intent_classifier.py" "backend,intent,classification,week5" "LONG" "Intent Classification System"

echo ""
echo "======================================================================"
echo "  Phase 4: Desktop App"
echo "======================================================================"

store_file "desktop-app/main.js" "frontend,electron,desktop,main" "LONG" "Electron Main Process"
store_file "desktop-app/renderer.js" "frontend,electron,desktop,ui,week4" "LONG" "Desktop App UI (Renderer)"
store_file "desktop-app/index.html" "frontend,electron,desktop,html" "LONG" "Desktop App HTML"
store_file "desktop-app/package.json" "frontend,electron,desktop,config" "LONG" "Desktop App Package Config"

echo ""
echo "======================================================================"
echo "  Phase 5: Database & Configuration"
echo "======================================================================"

store_file "src/storage/init_db.py" "backend,database,initialization,schema" "LONG" "Database Initialization"
store_file "docker-compose.yml" "infrastructure,docker,configuration" "LONG" "Docker Compose Configuration"
store_file ".env.example" "infrastructure,configuration,environment" "MEDIUM" "Environment Variables Example"

echo ""
echo "======================================================================"
echo "  Phase 6: Testing & Scripts"
echo "======================================================================"

store_file "tests/checkpoint_validation.py" "testing,checkpoint,validation" "MEDIUM" "Checkpoint Validation Tests"
store_file "scripts/setup_weaviate.sh" "scripts,infrastructure,weaviate,setup" "MEDIUM" "Weaviate Setup Script"
store_file "start_desktop.sh" "scripts,desktop,startup" "MEDIUM" "Desktop App Startup Script"

echo ""
echo "======================================================================"
echo "  Phase 7: Key Implementation Details"
echo "======================================================================"

# Store key implementation concepts as structured memories
./acms store "ACMS Week 4 Task 1: Semantic Cache uses vector similarity (cosine threshold 0.85) to detect semantically similar queries. Implements multi-level fallback: exact cache → semantic cache → LLM. Achieves 60%+ cost savings by avoiding redundant API calls to Claude/ChatGPT. Implementation in src/cache/semantic_cache.py" --tags "week4,task1,semantic-cache,implementation" --tier "LONG" > /dev/null 2>&1 && echo "  ✅ Stored Week 4 Task 1 concept" && ((STORED++))

./acms store "ACMS Week 4 Task 2: User Feedback System tracks user ratings (thumbs up/down/regenerate) with query_id and response_source fields. Stores feedback in PostgreSQL with denormalized feedback_summary JSONB column. Provides endpoints: POST /feedback, GET /feedback/summary/{query_id}, GET /feedback/user/{user_id}. Implementation in src/feedback/feedback_crud.py and src/api_server.py" --tags "week4,task2,feedback,implementation" --tier "LONG" > /dev/null 2>&1 && echo "  ✅ Stored Week 4 Task 2 concept" && ((STORED++))

./acms store "ACMS Week 4 Task 3: Individual Metrics Dashboard in desktop app (desktop-app/renderer.js). Shows feedback buttons (👍 👎 🔄), response source badges (cache/semantic_cache/claude), and analytics view with cache hit rates, feedback statistics, and cost savings. Uses state.askState.queryId and state.askState.responseSource for tracking." --tags "week4,task3,dashboard,analytics,implementation" --tier "LONG" > /dev/null 2>&1 && echo "  ✅ Stored Week 4 Task 3 concept" && ((STORED++))

./acms store "ACMS Architecture: FastAPI backend (port 40080), PostgreSQL database (port 40432), Weaviate v4 vector DB (port 8090), Redis cache (port 40379), Ollama embeddings (port 40434). Electron desktop app (port 8080). Uses hybrid search (vector + full-text), CRS algorithm for context ranking, and tiered memory storage (SHORT/MEDIUM/LONG/PERMANENT)." --tags "architecture,infrastructure,stack" --tier "PERMANENT" > /dev/null 2>&1 && echo "  ✅ Stored Architecture concept" && ((STORED++))

./acms store "ACMS Week 5 Features: Task 1 - Confidentiality Controls (5 levels: PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED/SECRET) with automatic PII/PCI/PHI detection. Task 2 - Intent Classification (factual/creative/analytical/procedural) for optimal query routing. Task 3 - Auto-tuning foundation using feedback data. Implementation in src/confidentiality/ and src/intent/" --tags "week5,confidentiality,intent,auto-tuning,planned" --tier "LONG" > /dev/null 2>&1 && echo "  ✅ Stored Week 5 roadmap" && ((STORED++))

echo ""
echo "======================================================================"
echo "  Import Complete!"
echo "======================================================================"
echo ""
echo "📊 Results:"
echo "  ✅ Successfully stored: $STORED files/concepts"
echo "  ❌ Failed: $FAILED files"
echo ""
echo "🎯 You can now ask ACMS questions like:"
echo "  - ./acms search 'semantic cache implementation'"
echo "  - ./acms search 'feedback system'"
echo "  - ./acms search 'desktop app UI'"
echo ""
echo "Or use the desktop app at http://localhost:8080 to ask:"
echo "  - 'How does the semantic cache work?'"
echo "  - 'What are the Week 4 features?'"
echo "  - 'Show me the API endpoints'"
echo ""
echo "======================================================================"
