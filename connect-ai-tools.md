# ACMS Integration Instructions - Connect Your AI Tools

**Purpose**: Step-by-step instructions to connect ChatGPT, Claude, Cursor, GitHub Copilot, and any other AI tool to ACMS Desktop  
**Audience**: You (first user) and future users  
**Prerequisite**: ACMS Desktop installed and running  

---

## 📋 **TABLE OF CONTENTS**

1. [Prerequisites](#prerequisites)
2. [Integration 1: ChatGPT (Browser Extension)](#integration-1-chatgpt-browser-extension)
3. [Integration 2: Cursor (VS Code Extension)](#integration-2-cursor-vs-code-extension)
4. [Integration 3: Claude (Browser Extension)](#integration-3-claude-browser-extension)
5. [Integration 4: GitHub Copilot (VS Code Extension)](#integration-4-github-copilot-vs-code-extension)
6. [Integration 5: Perplexity (Browser Extension)](#integration-5-perplexity-browser-extension)
7. [Integration 6: Custom Tools (API)](#integration-6-custom-tools-api)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## PREREQUISITES

### Before You Start:

**1. ACMS Desktop Running**
```bash
# Check if ACMS Desktop is running
curl http://localhost:40080/context/status

# Expected response:
# {"total_memories": 0, "connected_tools": []}

# If not running:
# - macOS: Open Applications → ACMS Desktop
# - Windows: Start Menu → ACMS Desktop
# - Linux: ./acms-desktop
```

**2. Services Healthy**
```bash
# Check health
curl http://localhost:40080/health

# Expected response:
# {
#   "status": "healthy",
#   "services": {
#     "postgres": "up",
#     "weaviate": "up",
#     "redis": "up",
#     "ollama": "up"
#   }
# }
```

**3. Menu Bar Icon Visible**
- Look for ACMS icon in menu bar/system tray
- Icon should be GREEN (services healthy)
- RED = services down, click for diagnostics

---

## INTEGRATION 1: CHATGPT (Browser Extension)

### **What You're Installing:**
Browser extension that injects context into ChatGPT queries

### **Step-by-Step (Chrome):**

#### **1. Build the Extension** (First Time Only)
```bash
cd extensions/chrome-extension

# Install dependencies
npm install

# Build extension
npm run build

# Output: extensions/chrome-extension/dist/
```

#### **2. Load Extension in Chrome**
```bash
# 1. Open Chrome
# 2. Go to: chrome://extensions
# 3. Enable "Developer mode" (top right toggle)
# 4. Click "Load unpacked"
# 5. Select: extensions/chrome-extension/dist
# 6. Extension appears: "ACMS Context Bridge"
```

#### **3. Verify Installation**
```bash
# 1. Go to: https://chat.openai.com
# 2. Look for ACMS icon in extension bar (top right)
# 3. Icon should be GREEN = connected to localhost:40080
# 4. Icon should be RED = not connected, check ACMS Desktop
```

#### **4. Test Context Injection**
```bash
# 1. Open ChatGPT
# 2. Type a query: "What is machine learning?"
# 3. Before hitting Enter, look for ACMS badge in textarea
# 4. Badge says: "No context available" (first query)
# 5. Hit Enter, let ChatGPT respond
# 6. ACMS stores the Q&A pair
# 7. Type another query: "Give me an example"
# 8. Badge says: "Context injected (1 memory, 89 tokens)"
# 9. Hit Enter
# 10. ChatGPT responds with context from previous query
```

#### **5. Configure Settings** (Optional)
```bash
# 1. Right-click ACMS extension icon
# 2. Click "Options"
# 3. Settings:
#    - Max tokens: 1500 (default), adjust if needed
#    - Auto-inject: ON (default), turn OFF for manual control
#    - Show badge: ON (default)
# 4. Click "Save"
```

### **Step-by-Step (Firefox):**
```bash
# 1. Build extension (same as Chrome)
cd extensions/chrome-extension
npm run build

# 2. Load in Firefox
# - Go to: about:debugging#/runtime/this-firefox
# - Click "Load Temporary Add-on"
# - Select: extensions/chrome-extension/dist/manifest.json
# - Extension loaded (temporary, until Firefox restart)

# For permanent installation:
# - Package as .xpi file
# - Submit to Firefox Add-ons (or self-host)
```

### **What Gets Captured:**
- ✅ Your queries to ChatGPT
- ✅ ChatGPT's responses
- ✅ Timestamp, tool source ("chatgpt")
- ❌ Chat history (only current conversation)
- ❌ Your OpenAI account info

### **How to Disable:**
```bash
# Temporary (session only):
# - Right-click extension → "Disable for this site"

# Permanent:
# - chrome://extensions → ACMS Context Bridge → Remove
```

---

## INTEGRATION 2: CURSOR (VS Code Extension)

### **What You're Installing:**
VS Code extension that injects context into Cursor/Copilot

### **Step-by-Step:**

#### **1. Build the Extension** (First Time Only)
```bash
cd extensions/vscode

# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Package as VSIX
npx vsce package

# Output: acms-context-bridge-0.0.1.vsix
```

#### **2. Install in Cursor**
```bash
# Method 1: Command Palette
# 1. Open Cursor
# 2. Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows)
# 3. Type: "Extensions: Install from VSIX"
# 4. Select: extensions/vscode/acms-context-bridge-0.0.1.vsix
# 5. Reload Cursor

# Method 2: Terminal
code --install-extension acms-context-bridge-0.0.1.vsix
# (Replace 'code' with 'cursor' if Cursor has its own CLI)
```

#### **3. Verify Installation**
```bash
# 1. Open Cursor
# 2. Look at status bar (bottom right)
# 3. Should see: "ACMS ✓" (green checkmark)
# 4. Hover: "ACMS Context Bridge: Connected"
# 5. If RED: Click for diagnostics
```

#### **4. Test Context Injection**
```bash
# Test 1: Manual context retrieval
# 1. Open any file (e.g., main.py)
# 2. Cmd+Shift+P → "ACMS: Get Context"
# 3. New editor opens with relevant context
# 4. Context includes: project files, previous code, ChatGPT discussions

# Test 2: Auto-store on save
# 1. Edit a file (add comment: # Test ACMS)
# 2. Save file (Cmd+S)
# 3. Notification: "ACMS: Code saved"
# 4. Check Menu Bar → ACMS → Recent memories
# 5. Should see: "File: main.py" with your code
```

#### **5. Configure Settings**
```bash
# 1. Open Settings: Cmd+, (Mac) or Ctrl+, (Windows)
# 2. Search: "ACMS"
# 3. Settings:
#    - acms.maxTokens: 1500 (default)
#    - acms.autoStoreOnSave: true (default)
#    - acms.apiUrl: http://localhost:40080 (don't change)
# 4. Restart Cursor for changes
```

### **What Gets Captured:**
- ✅ Code files (on save)
- ✅ File path, language, timestamp
- ✅ Git branch (if in repo)
- ❌ Local environment variables
- ❌ Sensitive files (you can exclude via .acmsignore)

### **How to Exclude Files:**
```bash
# Create .acmsignore in project root
# (Similar to .gitignore)

# Example .acmsignore:
*.env
*.key
secrets/
node_modules/
.venv/
```

### **How to Disable:**
```bash
# Temporary (session only):
# - Status bar → Click "ACMS" → "Disable for this workspace"

# Permanent:
# - Cmd+Shift+X → Extensions → ACMS Context Bridge → Disable
```

---

## INTEGRATION 3: CLAUDE (Browser Extension)

### **What You're Installing:**
Same browser extension as ChatGPT, but configured for Claude

### **Step-by-Step:**
```bash
# Good news: You already installed this with ChatGPT!
# The browser extension works for BOTH ChatGPT and Claude.

# Just verify it's enabled for claude.ai:
# 1. Go to: chrome://extensions
# 2. Find: "ACMS Context Bridge"
# 3. Click "Details"
# 4. Under "Site access", ensure "On specific sites" includes:
#    - https://chat.openai.com/*
#    - https://claude.ai/*
# 5. If not, click "Add" → Type "https://claude.ai/*" → Add
```

### **Test Context Injection:**
```bash
# 1. Go to: https://claude.ai
# 2. Start a new conversation
# 3. Type: "Explain quantum computing"
# 4. Badge: "No context available" (first query)
# 5. Hit Cmd+Enter (or Ctrl+Enter) to send
# 6. Claude responds
# 7. Type: "Can you give an example?"
# 8. Badge: "Context injected (1 memory, 156 tokens)"
# 9. Claude responds with context from previous query
```

### **Claude-Specific Formatting:**
```xml
<!-- ACMS injects context in Claude's XML format -->
<context>
<memory source="chatgpt" timestamp="2025-10-13T10:30:00Z">
Previous discussion about quantum computing...
</memory>
<memory source="cursor" timestamp="2025-10-13T10:35:00Z">
Code: quantum_algorithm.py
</memory>
</context>

Your query: Can you give an example?
```

This helps Claude understand the context source and timestamp.

---

## INTEGRATION 4: GITHUB COPILOT (VS Code Extension)

### **What You're Installing:**
Same VS Code extension as Cursor (already installed!)

### **Step-by-Step:**
```bash
# Good news: You already installed this with Cursor!
# The VS Code extension works for BOTH Cursor and GitHub Copilot.

# Just verify Copilot is installed:
# 1. Cmd+Shift+X → Search "GitHub Copilot"
# 2. Should see "GitHub Copilot" extension installed
# 3. If not, install it first
# 4. ACMS will automatically work with Copilot
```

### **How It Works:**
```bash
# When Copilot suggests code, ACMS provides context:
# 1. You're coding in main.py
# 2. Copilot suggests a function
# 3. Behind the scenes:
#    - ACMS injects context: project files, ChatGPT discussions
#    - Copilot uses this context for better suggestions
# 4. Result: Suggestions are more relevant to YOUR project
```

### **Test It:**
```bash
# 1. Open a file
# 2. Start typing a function name (e.g., "def process_data")
# 3. Copilot suggests implementation
# 4. Notice: Suggestions align with your project (variable names, patterns)
# 5. This is because ACMS provided context
```

---

## INTEGRATION 5: PERPLEXITY (Browser Extension)

### **What You're Installing:**
Same browser extension (already installed!)

### **Step-by-Step:**
```bash
# Same extension works for Perplexity.ai

# Just add perplexity.ai to allowed sites:
# 1. chrome://extensions → ACMS Context Bridge → Details
# 2. Site access → Add: "https://perplexity.ai/*"
# 3. Go to perplexity.ai
# 4. Extension badge should show GREEN
```

### **Test Context Injection:**
```bash
# 1. Go to: https://perplexity.ai
# 2. Search: "Quantum computing" (first query)
# 3. Badge: "No context"
# 4. Perplexity responds with sources
# 5. Follow-up: "What are the applications?"
# 6. Badge: "Context injected (1 memory, 203 tokens)"
# 7. Perplexity gives applications WITH context from first query
```

---

## INTEGRATION 6: CUSTOM TOOLS (API)

### **What You're Building:**
Connect ANY AI tool using ACMS API

### **Example: Python Script**
```python
# my_ai_tool.py
import requests

ACMS_API = "http://localhost:40080"

def get_context(query: str):
    """Retrieve context from ACMS"""
    response = requests.post(f"{ACMS_API}/context/retrieve", json={
        "query": query,
        "source": "my_custom_tool",
        "max_tokens": 1500
    })
    return response.json()

def store_context(content: str):
    """Store content in ACMS"""
    response = requests.post(f"{ACMS_API}/context/store", json={
        "content": content,
        "source": "my_custom_tool",
        "metadata": {"type": "ai_response"}
    })
    return response.json()

# Usage
if __name__ == "__main__":
    # Get context
    context_data = get_context("What is machine learning?")
    print(f"Context: {context_data['context']}")
    print(f"Memories used: {len(context_data['memories_used'])}")
    print(f"Tokens: {context_data['token_count']}")
    
    # Store response
    ai_response = "Machine learning is a subset of AI..."
    store_context(f"Q: What is machine learning?\nA: {ai_response}")
```

### **Example: JavaScript (Node.js)**
```javascript
// my-ai-tool.js
const axios = require('axios');

const ACMS_API = 'http://localhost:40080';

async function getContext(query) {
  const response = await axios.post(`${ACMS_API}/context/retrieve`, {
    query,
    source: 'my_custom_tool',
    max_tokens: 1500
  });
  return response.data;
}

async function storeContext(content) {
  const response = await axios.post(`${ACMS_API}/context/store`, {
    content,
    source: 'my_custom_tool',
    metadata: { type: 'ai_response' }
  });
  return response.data;
}

// Usage
(async () => {
  // Get context
  const contextData = await getContext('What is machine learning?');
  console.log(`Context: ${contextData.context}`);
  console.log(`Memories: ${contextData.memories_used.length}`);
  
  // Store response
  const aiResponse = 'Machine learning is...';
  await storeContext(`Q: What is ML?\nA: ${aiResponse}`);
})();
```

### **API Documentation:**
```bash
# Full API docs available at:
http://localhost:40080/docs

# Key endpoints:
POST /context/store       # Store new memory
POST /context/retrieve    # Get relevant context
GET  /context/status      # Check system health
DELETE /context/memory/{id}  # Delete memory
POST /context/feedback    # Record feedback (outcome learning)
```

---

## TROUBLESHOOTING

### **Problem: Extension shows "Not Connected"**

**Symptoms:**
- Browser extension badge is RED
- Tooltip says "Not connected to ACMS"

**Solution:**
```bash
# 1. Check ACMS Desktop is running
curl http://localhost:40080/context/status
# If error: "Connection refused", ACMS Desktop is not running

# 2. Restart ACMS Desktop
# macOS: Applications → ACMS Desktop → Quit → Reopen
# Windows: Task Manager → End ACMS Desktop → Start Menu → ACMS Desktop

# 3. Check firewall
# Ensure localhost:40080 is not blocked
# macOS: System Settings → Privacy & Security → Firewall → Allow ACMS
# Windows: Windows Defender → Allow an app → Add ACMS Desktop

# 4. Reload extension
# chrome://extensions → ACMS Context Bridge → Reload
```

---

### **Problem: Context Not Injected**

**Symptoms:**
- Badge says "No context available" even when memories exist
- Context not appearing in AI tool

**Solution:**
```bash
# 1. Check memories exist
curl http://localhost:40080/context/status
# Should show: "total_memories": X (X > 0)

# 2. Test retrieval directly
curl -X POST http://localhost:40080/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "source": "test", "max_tokens": 1000}'
# Should return context

# 3. Check min_score threshold
# Menu Bar → Settings → Min CRS Score
# Default: 0.5 (lower = more permissive)
# Try: 0.3 for testing

# 4. Check extension logs
# Chrome: F12 (DevTools) → Console → Filter "ACMS"
# Look for errors

# 5. Manually trigger injection
# ChatGPT: Click extension icon → "Inject Context Manually"
```

---

### **Problem: VS Code Extension Not Working**

**Symptoms:**
- No "ACMS" in status bar
- "ACMS: Get Context" command not found

**Solution:**
```bash
# 1. Verify extension installed
# Cmd+Shift+X → Search "ACMS"
# Should see "ACMS Context Bridge" installed

# 2. Check extension logs
# View → Output → Select "ACMS Context Bridge"
# Look for errors

# 3. Reload VS Code window
# Cmd+Shift+P → "Developer: Reload Window"

# 4. Reinstall extension
# Uninstall → Restart VS Code → Reinstall from VSIX
```

---

### **Problem: Memories Not Stored**

**Symptoms:**
- Menu Bar shows "0 memories"
- API returns empty context

**Solution:**
```bash
# 1. Check database connection
curl http://localhost:40080/health
# All services should be "up"

# 2. Test storage directly
curl -X POST http://localhost:40080/context/store \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory", "source": "test"}'
# Should return: {"memory_id": "...", "status": "stored"}

# 3. Check database
# Menu Bar → Advanced → Open Database
# Run: SELECT COUNT(*) FROM memories;
# Should show count > 0

# 4. Check logs
# Menu Bar → View Logs
# Look for errors like "Database connection failed"

# 5. Restart services
# Menu Bar → Advanced → Restart Services
```

---

## FAQ

### **Q: Which browser extensions are supported?**
A: Chrome, Firefox, Edge, Brave (any Chromium-based browser)

### **Q: Does ACMS work with Safari?**
A: Not yet. Safari extension API is different. We may support it in future.

### **Q: Can I use ACMS with multiple browsers?**
A: Yes! Install extension in each browser. They all connect to same ACMS Desktop.

### **Q: Does ACMS work offline?**
A: Partially. ACMS Desktop works offline, but AI tools (ChatGPT, Claude) need internet. Context injection works offline if you have local LLMs (Ollama).

### **Q: How much storage does ACMS use?**
A: ~1MB per 100 memories. 10,000 memories = ~100MB. Very efficient!

### **Q: Can I export my memories?**
A: Yes. Menu Bar → Export → Select format (JSON, CSV, Markdown)

### **Q: Can I delete specific memories?**
A: Yes. Menu Bar → View Memories → Select memory → Delete

### **Q: Is my data encrypted?**
A: Yes. All memories encrypted with XChaCha20-Poly1305. Keys stored in OS keychain.

### **Q: Does ACMS send data to the cloud?**
A: No. 100% local. Data never leaves your device.

### **Q: Can I use ACMS on multiple computers?**
A: Currently no (single-device). Cloud sync coming in Phase 8+.

### **Q: What if I have more questions?**
A: Check full docs at: https://acms.io/docs (or file GitHub issue)

---

## NEXT STEPS

Now that you've connected your tools:

1. **Test the demo script** (see DEMO_SCRIPT.md)
2. **Use ACMS for 1 day** (real-world testing)
3. **Report any bugs** (GitHub issues)
4. **Share feedback** (what works, what doesn't)
5. **Show it to friends** (get more testers!)

**Happy context bridging!** 🚀
