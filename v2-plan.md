# ACMS Desktop Master Plan v2.0 - Universal Context Bridge

**Version**: 2.0 (Complete Rebuild for Desktop Testing)  
**Focus**: Multi-tool context sharing on your desktop  
**Build Time**: 68 hours (7 phases × ~10 hours)  
**Primary Use Case**: YOU testing context flow between YOUR AI tools  
**Architecture**: Desktop-first, self-contained, easy to demo  

---

## 🎯 **THE VISION**

### **What You're Building:**
A desktop app that sits in the background and gives ALL your AI tools access to the same context memory.

**Imagine This Workflow:**
```
1. You explain your project architecture in ChatGPT
   → ACMS captures it

2. You open Cursor to write code
   → ACMS automatically injects that architecture context
   → Cursor's suggestions are now context-aware

3. You ask Claude for code review
   → ACMS gives Claude the same architecture + your Cursor code
   → Claude reviews with full context

4. You use GitHub Copilot
   → Copilot sees everything: architecture, prior code, reviews
   → Suggestions are perfectly aligned

ALL TOOLS SHARE THE SAME MEMORY. No more copy-pasting context.
```

### **Core Value Props:**
1. **Universal Memory**: All AI tools share the same brain
2. **Desktop-First**: Runs locally, no cloud required (privacy!)
3. **Zero Switching**: Keep using your favorite tools, we enhance them
4. **Smart Learning**: Remembers what was useful, forgets what wasn't
5. **Cost Savings**: 40% token reduction (no repeated context)

---

## 📊 **WHAT'S DIFFERENT FROM v1.0**

### **v1.0 (Archived):**
- Generic "memory system for enterprises"
- Cloud-first architecture
- Design partners TBD
- Abstract use case

### **v2.0 (This Plan):**
- **Concrete**: Test on YOUR desktop with YOUR tools
- **Desktop-first**: Menu bar app + local API
- **Your tools**: ChatGPT, Claude, Cursor, Copilot (whatever you use)
- **Immediate validation**: You ARE the first user

### **What We Keep from Phase 0-1:**
✅ ACMS-Lite (48 memories stored) - KEEP  
✅ Infrastructure (Docker services) - KEEP  
✅ Checkpoint framework - KEEP  
✅ Meta-recursive memory strategy - KEEP  

Everything Phase 0-1 built is PERFECT for this new direction.

### **What Changes in Phase 2-6:**
🔄 Phase 2: Add "Desktop App" component  
🔄 Phase 3: Focus on "your tools" integrations  
🔄 Phase 4: Desktop-first API (not cloud API)  
🔄 Phase 5: Menu bar app + tool connectors  
🔄 Phase 6: Demo script + testing YOUR workflow  

---

## 🏗️ **ARCHITECTURE OVERVIEW**

### **System Layers**

```
┌─────────────────────────────────────────────────────┐
│  Menu Bar App (Phase 5)                             │
│  • Show status (3 tools connected)                  │
│  • View memories (recent context)                   │
│  • Configure tools                                  │
└─────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────┐
│  Your AI Tools (Phase 3-5)                          │
│  ChatGPT │ Claude │ Cursor │ Copilot │ [Your tools] │
└─────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────┐
│  Tool Connectors (Phase 3-5)                        │
│  • Browser Extension (ChatGPT, Claude, Perplexity)  │
│  • VS Code Extension (Cursor, Copilot)              │
│  • Desktop Integration (any tool with API)          │
└─────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────┐
│  ACMS Desktop API (Phase 4)                         │
│  • POST /context/store    (tools store context)     │
│  • POST /context/retrieve (tools get context)       │
│  • GET  /context/status   (what's in memory)        │
│  • Runs on: http://localhost:40080                  │
└─────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────┐
│  Memory Engine (Phase 3)                            │
│  • Smart retrieval (CRS scoring)                    │
│  • Deduplication (don't store same thing twice)    │
│  • Learning (remember what was useful)              │
└─────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────┐
│  Storage Layer (Phase 2)                            │
│  • PostgreSQL (structured data)                     │
│  • Weaviate (vector search)                         │
│  • Redis (caching)                                  │
│  • Encrypted (local-first privacy)                  │
└─────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────┐
│  Infrastructure (Phase 1) ✅ DONE                   │
│  • Docker Compose                                   │
│  • Health checks                                    │
└─────────────────────────────────────────────────────┘
```

---

## 📅 **PHASE-BY-PHASE PLAN**

### **Phase 0: Bootstrap** ✅ COMPLETE (2 hours)
**Status**: DONE  
**What You Built**: ACMS-Lite (SQLite CLI for storing memories)  
**What We Keep**: Everything - this is the meta-memory that tracks the build itself  

**No changes needed.**

---

### **Phase 1: Infrastructure** ✅ COMPLETE (6 hours)
**Status**: DONE  
**What You Built**: 
- Docker services (PostgreSQL, Redis, Ollama)
- Weaviate (existing instance)
- Health checks

**No changes needed.**

---

### **Phase 2: Storage Layer + Desktop Foundation** (10 hours)
**Duration**: Hour 8-18  
**Goal**: Database schemas + desktop app foundation

#### **What We're Building:**

**1. PostgreSQL Schemas** (3 hours)
```sql
-- memories table
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) UNIQUE,  -- Deduplication
    source VARCHAR(50) NOT NULL,       -- 'chatgpt', 'cursor', etc.
    tool_context JSONB,                -- Tool-specific metadata
    created_at TIMESTAMP,
    last_used TIMESTAMP,
    use_count INT DEFAULT 0,
    crs_score FLOAT DEFAULT 0.0,       -- Context Retrieval Score
    embedding_id VARCHAR(100)          -- Weaviate UUID
);

-- context_logs table (track what context was retrieved)
CREATE TABLE context_logs (
    id UUID PRIMARY KEY,
    query TEXT NOT NULL,
    source_tool VARCHAR(50),           -- Which tool requested
    memories_used UUID[],              -- Array of memory IDs
    token_count INT,
    created_at TIMESTAMP
);

-- feedback table (outcome learning)
CREATE TABLE feedback (
    id UUID PRIMARY KEY,
    memory_id UUID REFERENCES memories(id),
    feedback_type VARCHAR(20),         -- 'helpful', 'not_helpful'
    created_at TIMESTAMP
);
```

**2. Weaviate Collection** (1 hour)
```python
# Collection: ACMS_Desktop_Memories
# Dimensions: 384 (all-minilm:22m)
# Properties: memory_id, content, source, created_at
```

**3. Encryption Setup** (2 hours)
```python
# XChaCha20-Poly1305 for content encryption
# Keys stored in macOS Keychain (or equivalent)
```

**4. Desktop App Foundation** (4 hours)
```
acms-desktop/
├── package.json           # Electron app
├── main.js                # Main process (API server)
├── preload.js             # Security bridge
├── renderer/              # UI (React)
│   ├── components/
│   │   ├── MenuBar.tsx    # Menu bar status
│   │   ├── MemoryView.tsx # View stored memories
│   │   └── Settings.tsx   # Configure tools
│   └── App.tsx
└── api/                   # Local API server
    ├── server.py          # FastAPI server
    └── routes/
        ├── store.py       # POST /context/store
        ├── retrieve.py    # POST /context/retrieve
        └── status.py      # GET /context/status
```

**Key Decision**: Use Electron for desktop app
- **Why**: Cross-platform (Mac, Windows, Linux)
- **Why**: Can embed API server (Python)
- **Why**: Easy menu bar integration
- **Alternative considered**: Native Swift/Objective-C (Mac-only)

#### **Testing (Phase 2):**
```python
# Unit tests
test_database_schemas()           # All tables created
test_encryption_decrypt()         # Encrypt → Decrypt works
test_weaviate_collection()        # Collection exists

# Integration tests
test_store_and_retrieve_memory()  # Full pipeline
test_duplicate_detection()        # SHA256 hash prevents dupes

# Desktop app tests
test_electron_starts()            # App launches
test_api_server_embedded()        # API runs inside Electron
test_menu_bar_visible()           # Menu bar icon shows
```

**Checkpoint 2 Criteria:**
- ✅ All database migrations applied
- ✅ Encryption working (encrypt/decrypt)
- ✅ Weaviate collection created
- ✅ Desktop app launches
- ✅ Embedded API server starts (http://localhost:40080)
- ✅ Menu bar icon visible
- ✅ Test coverage > 85%

---

### **Phase 3: Memory Engine + Your First Tool** (10 hours)
**Duration**: Hour 18-28  
**Goal**: Smart context retrieval + integrate YOUR first AI tool

#### **What We're Building:**

**1. Context Retrieval System (CRS)** (4 hours)
```python
# CRS Formula (from patent):
# score = w1·similarity + w2·recurrence + w3·outcome + w4·recency

class ContextRetriever:
    def retrieve(self, query: str, max_tokens: int = 2000):
        # 1. Generate query embedding
        query_emb = self.embedder.generate(query)
        
        # 2. Vector search (top 50 candidates)
        candidates = self.weaviate.search(query_emb, limit=50)
        
        # 3. Score with CRS
        for mem in candidates:
            mem['crs_score'] = (
                0.40 * mem['similarity'] +       # Semantic match
                0.25 * mem['recurrence'] +       # How often used
                0.25 * mem['outcome'] +          # Was it helpful?
                0.10 * mem['recency']            # Recent > old
            )
        
        # 4. Sort by CRS, select until token budget
        sorted_mems = sorted(candidates, key=lambda m: m['crs_score'], reverse=True)
        selected = []
        tokens = 0
        for mem in sorted_mems:
            mem_tokens = len(mem['content']) // 4  # Rough estimate
            if tokens + mem_tokens > max_tokens:
                break
            selected.append(mem)
            tokens += mem_tokens
        
        return selected, tokens
```

**2. Memory Ingestion Pipeline** (2 hours)
```python
class MemoryIngester:
    def ingest(self, content: str, source: str, metadata: dict = None):
        # 1. Check for duplicates (SHA256 hash)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if self.db.exists(content_hash):
            print(f"⚠️  Duplicate memory, skipping")
            return existing_id
        
        # 2. Store in PostgreSQL
        memory_id = self.db.store(content, source, metadata)
        
        # 3. Generate embedding
        embedding = self.embedder.generate(content)
        
        # 4. Store in Weaviate
        weaviate_id = self.weaviate.store(memory_id, embedding)
        
        # 5. Update PostgreSQL with weaviate_id
        self.db.update_embedding_id(memory_id, weaviate_id)
        
        print(f"✅ Stored memory {memory_id[:8]}... from {source}")
        return memory_id
```

**3. YOUR FIRST TOOL INTEGRATION** (4 hours)

**Question for you:** Which tool do you use MOST?
- [ ] ChatGPT (web)
- [ ] Claude (web)
- [ ] Cursor (IDE)
- [ ] GitHub Copilot (VS Code)
- [ ] Other: __________

**Let's say it's ChatGPT. Here's the integration:**

```javascript
// extensions/chrome-extension/
// manifest.json
{
  "name": "ACMS Context Bridge",
  "version": "1.0",
  "manifest_version": 3,
  "permissions": ["storage", "activeTab"],
  "host_permissions": ["https://chat.openai.com/*"],
  "content_scripts": [{
    "matches": ["https://chat.openai.com/*"],
    "js": ["content.js"]
  }],
  "background": {
    "service_worker": "background.js"
  }
}

// content.js (injected into ChatGPT)
const ACMS_API = 'http://localhost:40080';

// Intercept query submission
document.addEventListener('keydown', async (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    const textarea = document.querySelector('textarea');
    if (!textarea) return;
    
    const userQuery = textarea.value;
    
    // Get context from ACMS
    const response = await fetch(`${ACMS_API}/context/retrieve`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        query: userQuery,
        source: 'chatgpt',
        max_tokens: 1500
      })
    });
    
    const data = await response.json();
    
    if (data.context && data.context.length > 0) {
      // Inject context BEFORE user query
      const enhancedQuery = `${data.context}\n\n---\n\nUser query: ${userQuery}`;
      textarea.value = enhancedQuery;
      
      // Show badge: "Context injected (3 memories, 847 tokens)"
      showACMSBadge(data.memories_used.length, data.token_count);
    }
  }
});

// Capture ChatGPT's response
const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    if (mutation.addedNodes.length > 0) {
      const responseElement = document.querySelector('[data-message-author-role="assistant"]');
      if (responseElement) {
        const responseText = responseElement.innerText;
        
        // Store Q&A pair in ACMS
        fetch(`${ACMS_API}/context/store`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            content: `Q: ${userQuery}\nA: ${responseText}`,
            source: 'chatgpt',
            metadata: {type: 'qa_pair'}
          })
        });
      }
    }
  }
});

observer.observe(document.body, {childList: true, subtree: true});
```

**How to install on YOUR browser:**
```bash
# 1. Build extension
cd extensions/chrome-extension
npm install
npm run build

# 2. Load in Chrome
# - Go to chrome://extensions
# - Enable "Developer mode"
# - Click "Load unpacked"
# - Select extensions/chrome-extension/dist
# - Extension now active on chat.openai.com
```

#### **Testing (Phase 3):**
```python
# Unit tests
test_crs_scoring()                # CRS formula correct
test_deduplication()              # Duplicate detection works
test_token_budget()               # Retrieval respects token limit

# Integration tests
test_end_to_end_flow()            # Store → Retrieve → Use
test_chatgpt_extension()          # Extension injects context

# Manual tests (YOU do these)
test_chatgpt_context_injection()  # Explain architecture in ChatGPT
                                  # Ask related question
                                  # Verify context injected
```

**Checkpoint 3 Criteria:**
- ✅ CRS retrieval working (scores calculated correctly)
- ✅ Deduplication preventing duplicate memories
- ✅ First tool integrated (ChatGPT extension installed)
- ✅ Context injection visible in tool (badge shown)
- ✅ Memory storage working (Q&A pairs captured)
- ✅ Test coverage > 85%

---

### **Phase 4: Desktop API + Multi-Tool Support** (12 hours)
**Duration**: Hour 28-40  
**Goal**: Polish API + add 2-3 more tools

#### **What We're Building:**

**1. Complete Desktop API** (4 hours)
```python
# api/server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="ACMS Desktop API")

class StoreRequest(BaseModel):
    content: str
    source: str  # 'chatgpt', 'cursor', 'claude', etc.
    metadata: Optional[dict] = None

class RetrieveRequest(BaseModel):
    query: str
    source: str
    max_tokens: int = 2000

class RetrieveResponse(BaseModel):
    context: str           # Formatted context string
    memories_used: List[str]  # Memory IDs
    token_count: int
    latency_ms: int

@app.post("/context/store")
async def store_context(req: StoreRequest):
    memory_id = ingester.ingest(req.content, req.source, req.metadata)
    return {"memory_id": str(memory_id), "status": "stored"}

@app.post("/context/retrieve", response_model=RetrieveResponse)
async def retrieve_context(req: RetrieveRequest):
    import time
    start = time.time()
    
    memories, token_count = retriever.retrieve(req.query, req.max_tokens)
    
    # Format context for specific tool
    formatted = format_for_tool(memories, req.source)
    
    latency = int((time.time() - start) * 1000)
    
    return RetrieveResponse(
        context=formatted,
        memories_used=[m['id'] for m in memories],
        token_count=token_count,
        latency_ms=latency
    )

@app.get("/context/status")
async def get_status():
    return {
        "total_memories": db.count_memories(),
        "connected_tools": ["chatgpt", "cursor", "claude"],  # Auto-detect
        "last_update": db.get_last_memory_timestamp(),
        "storage_mb": db.get_storage_size()
    }

@app.post("/context/feedback")
async def record_feedback(memory_id: str, helpful: bool):
    db.record_feedback(memory_id, "helpful" if helpful else "not_helpful")
    return {"status": "recorded"}

def format_for_tool(memories: List[dict], source: str) -> str:
    """Format context for specific tool"""
    if source == "chatgpt":
        # ChatGPT format
        context = "# Relevant Context\n\n"
        for i, mem in enumerate(memories, 1):
            context += f"## Memory {i}\n{mem['content']}\n\n"
        return context
    
    elif source == "claude":
        # Claude XML format
        context = "<context>\n"
        for mem in memories:
            context += f"<memory>{mem['content']}</memory>\n"
        context += "</context>"
        return context
    
    elif source == "cursor":
        # Cursor code comment format
        context = "// Context from ACMS:\n"
        for mem in memories:
            context += f"// {mem['content']}\n"
        return context
    
    else:
        # Generic format
        return "\n\n---\n\n".join(m['content'] for m in memories)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=40080)
```

**2. Second Tool: Cursor** (4 hours)

**VS Code Extension for Cursor:**
```typescript
// extensions/vscode/src/extension.ts
import * as vscode from 'vscode';
import axios from 'axios';

const ACMS_API = 'http://localhost:40080';

export function activate(context: vscode.ExtensionContext) {
  
  // Command: Get context for current file
  let getContext = vscode.commands.registerCommand('acms.getContext', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    
    const filePath = editor.document.fileName;
    const currentCode = editor.document.getText();
    
    // Build query from file context
    const query = `Context for file: ${filePath}\n\nCurrent code:\n${currentCode.slice(0, 500)}`;
    
    // Get context from ACMS
    const response = await axios.post(`${ACMS_API}/context/retrieve`, {
      query,
      source: 'cursor',
      max_tokens: 1500
    });
    
    // Show context in new editor
    const doc = await vscode.workspace.openTextDocument({
      content: response.data.context,
      language: 'markdown'
    });
    await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    
    vscode.window.showInformationMessage(
      `ACMS: Loaded ${response.data.memories_used.length} memories (${response.data.token_count} tokens)`
    );
  });
  
  // Auto-store code on save
  vscode.workspace.onDidSaveTextDocument(async (document) => {
    const code = document.getText();
    
    await axios.post(`${ACMS_API}/context/store`, {
      content: `File: ${document.fileName}\n\`\`\`\n${code}\n\`\`\``,
      source: 'cursor',
      metadata: {
        type: 'code',
        language: document.languageId,
        file: document.fileName
      }
    });
  });
  
  // Status bar item
  const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBar.text = "$(database) ACMS";
  statusBar.tooltip = "ACMS Context Bridge Active";
  statusBar.command = 'acms.getContext';
  statusBar.show();
  
  context.subscriptions.push(getContext, statusBar);
}

export function deactivate() {}
```

**How to install in Cursor:**
```bash
# 1. Build extension
cd extensions/vscode
npm install
npm run compile

# 2. Install in Cursor
# - Open Cursor
# - Cmd+Shift+P → "Extensions: Install from VSIX"
# - Select extensions/vscode/acms-context-bridge-0.0.1.vsix
# - Reload Cursor
# - See "ACMS" in status bar
```

**3. Third Tool: Claude (web)** (4 hours)

**Browser extension update (add Claude support):**
```javascript
// extensions/chrome-extension/content.js
const detectTool = () => {
  if (window.location.hostname.includes('chat.openai.com')) return 'chatgpt';
  if (window.location.hostname.includes('claude.ai')) return 'claude';
  return null;
};

// Claude-specific injection
if (detectTool() === 'claude') {
  const textarea = document.querySelector('[contenteditable="true"]');
  
  textarea.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      const userQuery = textarea.innerText;
      
      // Get context
      const response = await fetch(`${ACMS_API}/context/retrieve`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          query: userQuery,
          source: 'claude',
          max_tokens: 1500
        })
      });
      
      const data = await response.json();
      
      if (data.context && data.context.length > 0) {
        // Claude XML format
        const enhancedQuery = `${data.context}\n\n${userQuery}`;
        textarea.innerText = enhancedQuery;
        
        showACMSBadge(data.memories_used.length, data.token_count);
      }
    }
  });
}
```

#### **Testing (Phase 4):**
```python
# API tests
test_store_endpoint()             # POST /context/store works
test_retrieve_endpoint()          # POST /context/retrieve works
test_status_endpoint()            # GET /context/status works
test_context_formatting()         # Different tools get different formats

# Integration tests
test_multi_tool_flow()            # ChatGPT → Cursor → Claude flow
test_context_consistency()        # Same memory retrieved by all tools

# Manual tests (YOU do these)
test_three_tool_demo()            # Your demo script (below)
```

**Checkpoint 4 Criteria:**
- ✅ API server stable (no crashes under load)
- ✅ 3 tools integrated (ChatGPT, Cursor, Claude)
- ✅ Context formatting correct for each tool
- ✅ Status endpoint shows connected tools
- ✅ Manual demo script successful (see Phase 6)
- ✅ Test coverage > 85%

---

### **Phase 5: Menu Bar App + Polish** (14 hours)
**Duration**: Hour 40-54  
**Goal**: Complete desktop experience

#### **What We're Building:**

**1. Menu Bar App** (8 hours)

```typescript
// acms-desktop/renderer/components/MenuBar.tsx
import { useState, useEffect } from 'react';

export function MenuBar() {
  const [status, setStatus] = useState(null);
  const [memories, setMemories] = useState([]);
  
  useEffect(() => {
    // Poll status every 5 seconds
    const interval = setInterval(async () => {
      const res = await fetch('http://localhost:40080/context/status');
      setStatus(await res.json());
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="menu-bar">
      <div className="status">
        <h3>ACMS Context Bridge</h3>
        <div className="stats">
          <div>📚 {status?.total_memories || 0} memories</div>
          <div>🔗 {status?.connected_tools?.length || 0} tools connected</div>
          <div>💾 {status?.storage_mb || 0} MB used</div>
        </div>
      </div>
      
      <div className="tools">
        <h4>Connected Tools</h4>
        {status?.connected_tools?.map(tool => (
          <div key={tool} className="tool-status">
            ✅ {tool}
          </div>
        ))}
      </div>
      
      <div className="recent-memories">
        <h4>Recent Memories</h4>
        {memories.slice(0, 5).map(mem => (
          <div key={mem.id} className="memory-item">
            <div className="memory-source">{mem.source}</div>
            <div className="memory-content">{mem.content.slice(0, 100)}...</div>
            <div className="memory-time">{formatTime(mem.created_at)}</div>
          </div>
        ))}
      </div>
      
      <button onClick={() => window.electron.openSettings()}>
        Settings
      </button>
    </div>
  );
}
```

**2. Settings Panel** (3 hours)
```typescript
// Settings to configure:
// - Which tools to monitor
// - Token budget per tool
// - CRS weight customization
// - Memory retention (auto-delete old memories)
// - Privacy: view/delete any memory
```

**3. Notifications** (3 hours)
```typescript
// Show desktop notifications:
// - "Context injected into ChatGPT (3 memories, 847 tokens)"
// - "New memory stored from Cursor"
// - "Warning: 90% memory capacity"
```

#### **Testing (Phase 5):**
```python
# UI tests
test_menu_bar_displays()          # Menu bar icon shows
test_status_updates()             # Status refreshes every 5s
test_memory_list_displays()       # Recent memories shown
test_settings_save()              # Settings persist

# Integration tests
test_notification_on_inject()     # Notification when context injected
test_manual_memory_delete()       # User can delete memories
```

**Checkpoint 5 Criteria:**
- ✅ Menu bar app functional
- ✅ Status updates in real-time
- ✅ Settings configurable
- ✅ Notifications working
- ✅ Memory viewer working
- ✅ Test coverage > 80%

---

### **Phase 6: Demo Script + YOUR Testing** (14 hours)
**Duration**: Hour 54-68  
**Goal**: Complete demo + thorough testing by YOU

#### **What We're Building:**

**1. Complete Demo Script** (2 hours)
See separate artifact below for full demo script.

**2. Documentation** (4 hours)
- README.md: Quick start guide
- USER_GUIDE.md: How to use ACMS
- INTEGRATION_GUIDE.md: How to connect new tools
- TROUBLESHOOTING.md: Common issues

**3. Performance Optimization** (4 hours)
- Cache frequently accessed memories in Redis
- Optimize CRS scoring (pre-compute some components)
- Reduce API latency to < 50ms (p95)

**4. YOUR Testing** (4 hours)
You test the complete flow:
- Install ACMS Desktop
- Connect ChatGPT, Cursor, Claude (or your tools)
- Run through demo script
- Use it naturally for 1 day
- Report bugs/issues
- Verify it actually saves you time

#### **Testing (Phase 6):**
```python
# Performance tests
test_api_latency()                # < 50ms p95
test_retrieval_latency()          # < 200ms p95
test_memory_load()                # 10K memories no slowdown

# End-to-end tests
test_complete_demo_script()       # Full demo runs without errors

# User acceptance tests (YOU)
test_real_world_usage()           # Use it for actual work
test_time_savings()               # Measure time saved vs. copy-pasting
```

**Checkpoint 6 Criteria:**
- ✅ Demo script runs successfully
- ✅ Documentation complete
- ✅ Performance targets met (< 50ms API, < 200ms retrieval)
- ✅ YOU can use it productively
- ✅ At least 1 day of real usage without major bugs
- ✅ Ready to show others

---

## 📊 **SUCCESS METRICS**

### **Phase 2-3: Foundation Success**
- ✅ Desktop app launches without errors
- ✅ API server runs stably
- ✅ First tool integrated (ChatGPT or Cursor)
- ✅ Context injection visible and working

### **Phase 4-5: Multi-Tool Success**
- ✅ 3+ tools connected
- ✅ Context flows between tools
- ✅ Menu bar app shows status
- ✅ No crashes during 1-hour usage

### **Phase 6: Real-World Success**
- ✅ YOU use it daily for 1 week
- ✅ Saves you time (vs. copy-pasting context)
- ✅ Friends/colleagues can install and use it
- ✅ Demo script impresses technical audience

### **Quantitative Metrics:**
- **API Latency**: < 50ms (p95)
- **Context Retrieval**: < 200ms (p95)
- **Token Reduction**: 30-50% (measured in demo)
- **Memory Accuracy**: 90%+ relevant memories retrieved
- **Uptime**: No crashes during 8-hour workday

---

## 🔧 **TECH STACK**

### **Desktop App:**
- Electron (cross-platform desktop app)
- React + TypeScript (UI)
- Tailwind CSS (styling)

### **Extensions:**
- Chrome Extension (JavaScript)
- VS Code Extension (TypeScript)

### **Backend:**
- FastAPI (Python)
- PostgreSQL 16
- Redis 7
- Weaviate 1.32.2
- Ollama (all-minilm:22m)

### **Infrastructure:**
- Docker Compose
- Already running from Phase 1 ✅

---

## 📦 **FILE STRUCTURE**

```
acms/
├── acms-lite/                  # Phase 0 ✅
│   ├── acms_lite.py
│   └── .acms_lite.db
│
├── infrastructure/             # Phase 1 ✅
│   ├── docker-compose.yml
│   ├── infra/health_check.sh
│   └── tests/test_infrastructure.py
│
├── storage/                    # Phase 2
│   ├── schema/
│   │   └── 01_base_schema.sql
│   ├── migrations/
│   ├── encryption.py
│   └── database.py
│
├── memory-engine/              # Phase 3
│   ├── retriever.py            # CRS implementation
│   ├── ingester.py
│   ├── embeddings.py
│   └── deduplicator.py
│
├── api/                        # Phase 4
│   ├── server.py               # FastAPI server
│   ├── routes/
│   │   ├── store.py
│   │   ├── retrieve.py
│   │   └── status.py
│   └── formatting.py           # Tool-specific context formatting
│
├── acms-desktop/               # Phase 5
│   ├── package.json
│   ├── main.js                 # Electron main process
│   ├── preload.js
│   └── renderer/
│       ├── components/
│       │   ├── MenuBar.tsx
│       │   ├── MemoryView.tsx
│       │   └── Settings.tsx
│       └── App.tsx
│
├── extensions/                 # Phase 3-5
│   ├── chrome-extension/
│   │   ├── manifest.json
│   │   ├── content.js
│   │   └── background.js
│   └── vscode/
│       ├── package.json
│       ├── src/extension.ts
│       └── test/
│
├── tests/                      # All phases
│   ├── unit/
│   ├── integration/
│   └── checkpoint_validation.py
│
├── docs/                       # Phase 6
│   ├── README.md
│   ├── USER_GUIDE.md
│   ├── INTEGRATION_GUIDE.md
│   ├── DEMO_SCRIPT.md
│   └── phase<N>_summary.md
│
└── scripts/
    ├── start_desktop.sh
    ├── install_extensions.sh
    └── run_demo.sh
```

---

## 🎯 **WHAT TO TELL CLAUDE CODE**

### **Overview:**
"We're building ACMS Desktop - a universal context bridge that gives ALL your AI tools access to the same memory. You test it on your own desktop with YOUR tools (ChatGPT, Cursor, Claude, etc.)."

### **Key Points:**
1. **Phases 0-1 are DONE** ✅ (ACMS-Lite + Infrastructure)
2. **Start Phase 2**: Database schemas + Desktop app foundation
3. **Desktop-first**: Electron app with embedded API server
4. **YOUR tools**: Integrate whatever YOU use most
5. **Demo-driven**: Build toward a working demo YOU can show

### **Development Approach:**
- TDD always (write tests first)
- Query ACMS-Lite before decisions
- Store everything in ACMS-Lite
- Run checkpoints after each phase
- Build for YOUR desktop (macOS/Windows/Linux)

### **Critical Success Factor:**
At the end of Phase 6, YOU should be using ACMS Desktop daily and showing it to friends. If you're not, we failed.

---

## 📋 **NEXT STEPS**

1. **Review this plan** - Does this match your vision?
2. **Confirm your tools** - ChatGPT? Cursor? Claude? Others?
3. **Start Phase 2** - Database schemas + Desktop app foundation
4. **Follow the demo script** - Build toward that working demo

---

**Ready to build the future of AI context management?** 🚀

Let's make YOUR desktop the first place where ALL AI tools share the same brain.

**PROCEED TO PHASE 2 →**
