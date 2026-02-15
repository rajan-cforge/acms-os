# ACMS Debugging Guide - Tracing UI to Backend Flow

**Complete guide to test, debug, and trace code execution from desktop app UI all the way to backend services.**

---

## 🎯 Quick Start: Enable Full Debugging

### 1. Start Backend with Debug Logging

```bash
cd /path/to/acms

# Set debug logging
export LOG_LEVEL=DEBUG
export LOG_FORMAT=text  # or 'json' for structured logs

# Start API server
source venv/bin/activate
PYTHONPATH=/path/to/acms python3 src/api_server.py
```

### 2. Start Desktop App with DevTools

```bash
cd desktop-app

# Start with DevTools open
npm start -- --inspect
```

Or edit `main.js` line 27-29 to always open DevTools:
```javascript
// Always open DevTools (remove the if condition)
mainWindow.webContents.openDevTools();
```

---

## 📊 Complete Request Flow: UI → Backend

### Example: User sends "What is ACMS?" message

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: UI (Electron Renderer)                            │
│ File: desktop-app/src/renderer/app.js                       │
└─────────────────────────────────────────────────────────────┘
         │
         │ User clicks "Send" button
         ▼
┌─────────────────────────────────────────────────────────────┐
│ handleSendMessage()                                         │
│ - Line 173: Receives message and agent                      │
│ - Line 186: Calls handleStreamingMessage()                  │
└─────────────────────────────────────────────────────────────┘
         │
         │ streamChatMessage()
         ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: API Client (Streaming)                             │
│ File: desktop-app/src/renderer/utils/streaming.js          │
└─────────────────────────────────────────────────────────────┘
         │
         │ POST /gateway/ask
         │ Body: {query, manual_agent, conversation_id}
         ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: FastAPI Endpoint                                   │
│ File: src/api_server.py                                     │
│ Endpoint: POST /gateway/ask (line ~1844)                    │
└─────────────────────────────────────────────────────────────┘
         │
         │ gateway.execute(request)
         ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: Gateway Orchestrator                               │
│ File: src/gateway/orchestrator.py                           │
│ Method: execute() - Line 113                                │
└─────────────────────────────────────────────────────────────┘
         │
         │ 7-Step Pipeline:
         │ 1. Intent Detection
         │ 2. Cache Check
         │ 3. Agent Selection
         │ 4. Context Assembly
         │ 5. Compliance Check
         │ 6. Agent Execution
         │ 7. Storage
         ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 5: Backend Services                                   │
│ - Intent Classifier, Agent Selector, Context Assembler     │
│ - Memory CRUD, LLM Agents (Claude/GPT/Gemini)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Step-by-Step Debugging

### Step 1: Add Breakpoints in UI (Electron DevTools)

1. **Open DevTools** in desktop app:
   - View → Developer → Developer Tools
   - Or press `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows/Linux)

2. **Set Breakpoints**:
   - Go to Sources tab
   - Navigate to: `src/renderer/app.js`
   - Click line number to set breakpoint at:
     - **Line 173**: `handleSendMessage()` - Entry point
     - **Line 220**: `handleStreamingMessage()` - Streaming handler
     - **Line 260**: `streamChatMessage()` - API call

3. **Watch Variables**:
   - In DevTools, add to Watch:
     ```javascript
     message
     agent
     this.state.currentConversationId
     ```

### Step 2: Monitor Network Requests

1. **Open Network Tab** in DevTools
2. **Filter**: Select "Fetch/XHR"
3. **Look for**: `gateway/ask` request
4. **Inspect**:
   - Request Headers
   - Request Payload
   - Response (SSE stream)

### Step 3: Add Console Logging in UI

Edit `desktop-app/src/renderer/app.js`:

```javascript
async handleSendMessage(message, agent) {
    console.log('🔵 [UI] handleSendMessage called', { message, agent });
    console.trace('Call stack'); // Shows full call stack
    
    // ... existing code ...
    
    if (this.state.enableStreaming) {
        console.log('🔵 [UI] Using streaming mode');
        this.handleStreamingMessage(message, agent);
    }
}
```

Edit `desktop-app/src/renderer/utils/streaming.js`:

```javascript
async function streamWithFetch(baseUrl, params, callbacks) {
    console.log('🟢 [STREAMING] Starting fetch', { url: baseUrl, params });
    
    const response = await fetch(`${API_BASE_URL}/gateway/ask`, {
        // ... existing code ...
    });
    
    console.log('🟢 [STREAMING] Response received', response.status);
    // ... rest of code ...
}
```

### Step 4: Debug Backend API Server

#### Option A: Python Debugger (pdb)

Edit `src/api_server.py` at the endpoint:

```python
@app.post("/gateway/ask")
async def gateway_ask(request: GatewayAskRequest):
    import pdb; pdb.set_trace()  # Breakpoint here
    
    logger.info(f"[API] Gateway ask request: {request.query[:50]}...")
    # ... rest of code ...
```

Run with:
```bash
PYTHONPATH=/path/to/acms python3 -m pdb src/api_server.py
```

#### Option B: VS Code Python Debugger

1. Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: ACMS API Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/api_server.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "LOG_LEVEL": "DEBUG"
            },
            "justMyCode": false
        }
    ]
}
```

2. Set breakpoints in VS Code:
   - `src/api_server.py` line ~1844 (gateway_ask endpoint)
   - `src/gateway/orchestrator.py` line 113 (execute method)
   - `src/gateway/orchestrator.py` line 150+ (pipeline steps)

3. Press F5 to start debugging

### Step 5: Add Logging in Gateway Orchestrator

Edit `src/gateway/orchestrator.py`:

```python
async def execute(self, request: GatewayRequest) -> AsyncIterator[Dict[str, Any]]:
    start_time = time.time()
    query = request.query
    user_id = request.user_id

    # Add detailed logging
    logger.info(f"🔴 [GATEWAY] START | query='{query[:50]}...' | user={user_id}")
    logger.debug(f"[GATEWAY] Full request: {request.dict()}")

    try:
        # Step 1: Intent Detection
        logger.info("🔴 [GATEWAY] Step 1: Intent Detection")
        detected_intent = await self.intent_classifier.classify(query)
        logger.info(f"🔴 [GATEWAY] Intent: {detected_intent}")
        
        # Step 2: Cache Check
        logger.info("🔴 [GATEWAY] Step 2: Cache Check")
        # ... cache logic ...
        
        # Step 3: Agent Selection
        logger.info("🔴 [GATEWAY] Step 3: Agent Selection")
        selected_agent_type = await self.agent_selector.select_agent(
            query, detected_intent
        )
        logger.info(f"🔴 [GATEWAY] Selected agent: {selected_agent_type}")
        
        # ... continue for each step ...
        
    except Exception as e:
        logger.error(f"🔴 [GATEWAY] ERROR: {e}", exc_info=True)
        raise
```

### Step 6: Monitor Backend Logs

```bash
# Terminal 1: Watch API server logs
tail -f api_server.log | grep -E "\[GATEWAY\]|\[API\]|ERROR"

# Terminal 2: Watch all Python logs
tail -f api_server.log

# Terminal 3: Filter by correlation ID (if using structured logging)
tail -f api_server.log | grep "correlation_id:abc-123"
```

---

## 🛠️ Debugging Tools

### 1. Browser DevTools (Electron)

**Access**: View → Developer → Developer Tools

**Tabs to Use**:
- **Console**: JavaScript logs, errors
- **Sources**: Set breakpoints, step through code
- **Network**: Monitor API requests/responses
- **Application**: Local storage, session storage

**Keyboard Shortcuts**:
- `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows): Open DevTools
- `Cmd+Option+J` (Mac) / `Ctrl+Shift+J` (Windows): Console tab
- `Cmd+R` (Mac) / `Ctrl+R` (Windows): Reload

### 2. Python Debugger (pdb)

**Basic Commands**:
```python
# In pdb prompt:
n          # Next line
s          # Step into function
c          # Continue
l          # List code
p variable # Print variable
pp dict    # Pretty print
q          # Quit
```

**Example**:
```python
# In orchestrator.py
async def execute(self, request):
    import pdb; pdb.set_trace()
    # Now you can inspect: request, self, etc.
```

### 3. VS Code Debugger

**Setup**:
1. Install Python extension
2. Create `.vscode/launch.json` (see Step 4 above)
3. Set breakpoints by clicking line numbers
4. Press F5 to start debugging

**Features**:
- Step over (F10), Step into (F11), Step out (Shift+F11)
- Watch variables
- Call stack view
- Debug console

### 4. Logging with Correlation IDs

The codebase has structured logging with correlation IDs. Enable it:

```python
# In api_server.py startup
from src.utils.logging import setup_logging, set_correlation_id
import uuid

setup_logging(format='text', level='DEBUG')

# In each request handler:
correlation_id = str(uuid.uuid4())
set_correlation_id(correlation_id)
logger.info(f"Request started", extra={'correlation_id': correlation_id})
```

Then trace requests:
```bash
# Filter logs by correlation ID
tail -f api_server.log | grep "correlation_id:abc-123"
```

---

## 📝 Complete Debugging Checklist

### Before Starting

- [ ] Backend API server running (`python3 src/api_server.py`)
- [ ] Docker services running (`docker-compose ps`)
- [ ] Desktop app running (`npm start`)
- [ ] DevTools open in Electron
- [ ] Backend logs visible in terminal

### Tracing a Request

1. **UI Layer**:
   - [ ] Set breakpoint in `app.js` `handleSendMessage()`
   - [ ] Verify message and agent values
   - [ ] Check `this.state` object

2. **Streaming Layer**:
   - [ ] Set breakpoint in `streaming.js` `streamWithFetch()`
   - [ ] Verify request URL and body
   - [ ] Check fetch response status

3. **Network Layer**:
   - [ ] Open Network tab in DevTools
   - [ ] Find `gateway/ask` request
   - [ ] Inspect request headers and payload
   - [ ] Check response (SSE stream)

4. **API Endpoint**:
   - [ ] Set breakpoint in `api_server.py` `gateway_ask()`
   - [ ] Verify `request` object
   - [ ] Check `user_id` and `query`

5. **Gateway Orchestrator**:
   - [ ] Set breakpoint in `orchestrator.py` `execute()`
   - [ ] Step through 7-step pipeline
   - [ ] Verify each step's output

6. **Backend Services**:
   - [ ] Check intent classification result
   - [ ] Verify agent selection
   - [ ] Check context retrieval
   - [ ] Monitor LLM API calls

---

## 🎯 Common Debugging Scenarios

### Scenario 1: Message Not Sending

**Symptoms**: Click Send, nothing happens

**Debug Steps**:
1. **Check UI Console**:
   ```javascript
   // In DevTools Console
   window.acmsApp.state  // Check app state
   ```

2. **Check Event Handler**:
   - Set breakpoint in `input.js` `handleSend()`
   - Verify `onSend` callback is called

3. **Check API Connection**:
   ```javascript
   // In DevTools Console
   fetch('http://localhost:40080/health')
     .then(r => r.json())
     .then(console.log)
   ```

4. **Check Backend Logs**:
   ```bash
   # Should see request in logs
   tail -f api_server.log | grep "gateway/ask"
   ```

### Scenario 2: Streaming Not Working

**Symptoms**: Response appears all at once, not character-by-character

**Debug Steps**:
1. **Check Streaming Flag**:
   ```javascript
   // In DevTools Console
   window.acmsApp.state.enableStreaming  // Should be true
   ```

2. **Check SSE Events**:
   - Network tab → `gateway/ask` → Response
   - Should see `event: chunk`, `event: done` events

3. **Check Backend Streaming**:
   ```python
   # In orchestrator.py
   logger.info(f"Yielding chunk: {chunk[:50]}...")
   ```

4. **Check Browser Support**:
   ```javascript
   // In DevTools Console
   'ReadableStream' in window  // Should be true
   ```

### Scenario 3: Wrong Agent Selected

**Symptoms**: Selected "Claude" but GPT-4 responds

**Debug Steps**:
1. **Check UI Agent Value**:
   ```javascript
   // In DevTools Console, before sending
   document.getElementById('agent-selector').value
   ```

2. **Check Request Payload**:
   - Network tab → Request Payload
   - Verify `manual_agent` field

3. **Check Agent Selection Logic**:
   ```python
   # In orchestrator.py, add logging:
   logger.info(f"Manual agent requested: {request.manual_agent}")
   logger.info(f"Selected agent: {selected_agent_type}")
   ```

4. **Check Agent Mapping**:
   ```python
   # In streaming.js, verify agentMap:
   const agentMap = {
       'claude': 'claude_sonnet',
       'gpt': 'chatgpt',
       'gemini': 'gemini'
   };
   ```

### Scenario 4: Conversation Not Persisting

**Symptoms**: Messages disappear after closing app

**Debug Steps**:
1. **Check Conversation ID**:
   ```javascript
   // In DevTools Console
   window.acmsApp.state.currentConversationId
   ```

2. **Check API Call**:
   - Network tab → Look for `POST /chat/conversations/{id}/messages`
   - Verify request succeeds (200 status)

3. **Check Backend Storage**:
   ```python
   # In conversation_crud.py, add logging:
   logger.info(f"Saving message to conversation: {conversation_id}")
   ```

4. **Check Database**:
   ```bash
   # Connect to PostgreSQL
   docker exec -it acms_postgres psql -U acms -d acms
   
   # Query conversations
   SELECT * FROM conversations ORDER BY created_at DESC LIMIT 5;
   SELECT * FROM conversation_messages WHERE conversation_id = '...';
   ```

---

## 🔧 Advanced Debugging

### 1. Enable Verbose Logging

**Backend**:
```bash
export LOG_LEVEL=DEBUG
export LOG_FORMAT=text
python3 src/api_server.py
```

**Frontend**:
Edit `desktop-app/src/renderer/app.js`:
```javascript
// Add at top of file
const DEBUG = true;

// Then use throughout:
if (DEBUG) console.log('🔵 [DEBUG]', data);
```

### 2. Add Performance Timing

**Backend**:
```python
import time

async def execute(self, request):
    timings = {}
    
    # Step 1
    start = time.time()
    intent = await self.intent_classifier.classify(query)
    timings['intent'] = time.time() - start
    
    # Step 2
    start = time.time()
    # ... cache check ...
    timings['cache'] = time.time() - start
    
    logger.info(f"Timings: {timings}")
```

**Frontend**:
```javascript
const startTime = performance.now();
// ... operation ...
const endTime = performance.now();
console.log(`Operation took ${endTime - startTime}ms`);
```

### 3. Trace Database Queries

```python
# Enable SQLAlchemy query logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### 4. Monitor Weaviate Queries

```python
# In weaviate_client.py
logger.debug(f"Weaviate query: {query}")
logger.debug(f"Weaviate response: {response}")
```

### 5. Trace LLM API Calls

```python
# In agent files (claude_sonnet.py, chatgpt.py, etc.)
logger.info(f"Calling {agent_name} API with prompt: {prompt[:100]}...")
logger.info(f"{agent_name} response: {response[:100]}...")
```

---

## 📊 Logging Output Examples

### UI Console (DevTools)

```
🔵 [UI] handleSendMessage called { message: "What is ACMS?", agent: "auto" }
🔵 [UI] Using streaming mode
🟢 [STREAMING] Starting fetch { url: "http://localhost:40080/gateway/ask", params: {...} }
🟢 [STREAMING] Response received 200
🟢 [STREAMING] Chunk received: "ACMS is..."
✅ Stream complete: { answer: "...", cost: 0.0023, ... }
```

### Backend Logs

```
2025-11-15 10:30:15 - acms.api - INFO - [API] Gateway ask request: What is ACMS?...
2025-11-15 10:30:15 - src.gateway.orchestrator - INFO - 🔴 [GATEWAY] START | query='What is ACMS?' | user=...
2025-11-15 10:30:15 - src.gateway.orchestrator - INFO - 🔴 [GATEWAY] Step 1: Intent Detection
2025-11-15 10:30:15 - src.gateway.intent_classifier - INFO - Intent: factual
2025-11-15 10:30:15 - src.gateway.orchestrator - INFO - 🔴 [GATEWAY] Step 2: Cache Check
2025-11-15 10:30:15 - src.gateway.orchestrator - INFO - 🔴 [GATEWAY] Step 3: Agent Selection
2025-11-15 10:30:15 - src.gateway.agent_selector - INFO - Selected: claude_sonnet
2025-11-15 10:30:15 - src.gateway.orchestrator - INFO - 🔴 [GATEWAY] Step 4: Context Assembly
2025-11-15 10:30:16 - src.gateway.orchestrator - INFO - 🔴 [GATEWAY] Step 5: Compliance Check
2025-11-15 10:30:16 - src.gateway.orchestrator - INFO - 🔴 [GATEWAY] Step 6: Agent Execution
2025-11-15 10:30:18 - src.gateway.agents.claude_sonnet - INFO - Claude response received
2025-11-15 10:30:18 - src.gateway.orchestrator - INFO - 🔴 [GATEWAY] Step 7: Storage
2025-11-15 10:30:18 - src.gateway.orchestrator - INFO - 🔴 [GATEWAY] COMPLETE | latency=2.3s | cost=$0.0023
```

---

## 🚀 Quick Reference

### Start Everything with Debugging

```bash
# Terminal 1: Backend
cd /path/to/acms
export LOG_LEVEL=DEBUG
source venv/bin/activate
PYTHONPATH=/path/to/acms python3 src/api_server.py

# Terminal 2: Desktop App
cd desktop-app
npm start -- --inspect

# Terminal 3: Watch Logs
tail -f /path/to/acms/api_server.log
```

### Key Files to Debug

| Layer | File | Key Methods |
|-------|------|-------------|
| UI | `desktop-app/src/renderer/app.js` | `handleSendMessage()`, `handleStreamingMessage()` |
| Streaming | `desktop-app/src/renderer/utils/streaming.js` | `streamWithFetch()` |
| API | `src/api_server.py` | `gateway_ask()` |
| Orchestrator | `src/gateway/orchestrator.py` | `execute()` |
| Services | `src/gateway/*.py` | Various service methods |

### Useful Commands

```bash
# Check API health
curl http://localhost:40080/health

# Test gateway endpoint
curl -X POST http://localhost:40080/gateway/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "manual_agent": null}'

# Check Docker services
docker-compose ps

# View API logs
tail -f api_server.log

# Check PostgreSQL
docker exec -it acms_postgres psql -U acms -d acms
```

---

**Last Updated**: November 15, 2025
**Status**: Complete debugging guide for ACMS full-stack flow





