# ACMS Desktop Testing Guide

**Week 5 Day 3**: Streaming Responses & Conversation History

## Prerequisites

1. **Backend running**:
   ```bash
   cd /path/to/acms
   docker-compose ps  # All services should be "Up"
   ```

2. **Desktop app running**:
   ```bash
   cd desktop-app
   npm start
   ```

---

## Feature 1: Streaming Responses ✨

### What to Test
Real-time message streaming with character-by-character display

### How to Test

1. **Open the desktop app**
2. **Select an agent** from dropdown (Auto/Claude/GPT-4)
3. **Type a message**: "Explain quantum computing in simple terms"
4. **Click Send**

### Expected Behavior
- ✅ Message appears immediately in chat (your message)
- ✅ Placeholder assistant message appears
- ✅ Response appears **character-by-character** (typewriter effect)
- ✅ Thinking steps update in real-time (if any)
- ✅ Final message shows metadata badges:
  - Agent used (e.g., "CLAUDE SONNET")
  - Cost (e.g., "$0.0023")
  - Confidence (if available)
  - Mode (ENRICHED or CACHED)

### What to Look For
- **No flicker** during streaming
- **Smooth character appearance**
- **Status indicator** shows "connected" (green dot)

### Known Issues
- ❌ **Gemini agent fails** with backend error (use Auto/Claude/GPT-4 instead)

---

## Feature 2: Conversation History 📚

### What to Test
Load and browse past conversations

### How to Test

1. **Check the sidebar** (left panel)
2. **Look for "Recent Conversations" section**
3. **Conversations should be grouped**:
   - TODAY
   - YESTERDAY
   - LAST 7 DAYS
   - OLDER

### Expected Behavior
- ✅ Conversations appear in time-based groups
- ✅ Each conversation shows:
  - Title (auto-generated from first message)
  - Message count (e.g., "4 messages")
  - Relative time (e.g., "2h ago", "Yesterday")

### How to Load a Conversation

1. **Click any conversation** in the sidebar
2. **Wait for loading**

### Expected Behavior
- ✅ All messages load and appear in order
- ✅ Chat header updates with conversation title
- ✅ You can continue the conversation
- ✅ New messages are added to the same conversation

---

## Feature 3: New Chat Creation ➕

### How to Test (3 ways)

**Method 1: Button**
- Click the **"+ New Chat"** button in sidebar

**Method 2: Keyboard shortcut**
- Press **Cmd+N** (Mac) or **Ctrl+N** (Windows/Linux)

**Method 3: After loading conversation**
- Load an old conversation
- Click "New Chat" to start fresh

### Expected Behavior
- ✅ Messages area clears
- ✅ Chat header resets to "Chat"
- ✅ Input field focuses automatically
- ✅ Next message starts a new conversation

---

## Feature 4: Agent Selection 🤖

### Available Agents

1. **Auto** (recommended)
   - System automatically selects best agent
   - Good for testing semantic cache

2. **Claude** (Claude Sonnet 4.5)
   - Best for complex reasoning
   - More expensive (~$0.003 per message)

3. **GPT-4** (ChatGPT 4o)
   - Good general-purpose agent
   - Medium cost (~$0.0025 per message)

4. **Gemini** ⚠️ (KNOWN ISSUE)
   - Currently has backend error
   - Avoid until fixed

### How to Test

1. **Select "Auto"** from dropdown
2. **Send**: "What is ACMS?"
3. **Wait for response**
4. **Check badge** - should show which agent was used

### Try Different Agents

1. **Select "Claude"**
2. **Send**: "Explain machine learning"
3. **Check cost badge** - should show cost

1. **Select "GPT-4"**
2. **Send**: "What is React?"
3. **Compare response style**

---

## Feature 5: Message Metadata 📊

### What to Look For

Every assistant message shows:

1. **Agent Badge** (blue)
   - Example: "CLAUDE SONNET", "CHATGPT", "AUTO"

2. **Cost Badge** (green)
   - Example: "$0.0023", "$0.0015"

3. **Confidence Badge** (if available)
   - High: 90%+ (green)
   - Medium: 70-89% (yellow)
   - Low: <70% (red)

4. **Mode Badge** (purple)
   - "ENRICHED" = Fresh generation
   - "CACHED" = Semantic cache hit

5. **Thinking Steps** (expandable)
   - Click to expand/collapse
   - Shows agent's reasoning process

---

## Feature 6: Feedback System 👍👎

### How to Test

1. **Send a message and get response**
2. **Look for feedback buttons** below assistant message
3. **Click thumbs up 👍** or **thumbs down 👎**

### Expected Behavior
- ✅ Button highlights when clicked
- ✅ Feedback sent to API
- ✅ Console shows: "✅ Feedback recorded"

---

## Testing Checklist

### Basic Flow
- [ ] Open desktop app
- [ ] API status shows "connected" (green dot)
- [ ] Sidebar loads conversations
- [ ] Send a message with Auto agent
- [ ] Response streams character-by-character
- [ ] Message shows all metadata badges

### Streaming
- [ ] Try Auto agent
- [ ] Try Claude agent
- [ ] Try GPT-4 agent
- [ ] Verify character-by-character streaming
- [ ] Verify no flicker during streaming

### Conversations
- [ ] Click an old conversation
- [ ] Verify all messages load
- [ ] Send a new message in that conversation
- [ ] Click "New Chat" button
- [ ] Verify messages clear
- [ ] Send message to start new conversation

### Keyboard Shortcuts
- [ ] Press Cmd/Ctrl+N → Creates new chat
- [ ] Press Cmd/Ctrl+/ → Focuses input field

### Edge Cases
- [ ] Send very long message (500+ chars)
- [ ] Send message with special characters
- [ ] Load conversation with 10+ messages
- [ ] Switch between conversations quickly

---

## Performance Testing

### Semantic Cache Test

**Goal**: Verify cache hit after asking same question

1. **Send**: "What is ACMS?" (agent: Auto)
2. **Wait for response** → Should show "ENRICHED"
3. **Wait 5 seconds**
4. **Send exact same question**: "What is ACMS?"
5. **Check badge** → Should show "CACHED"
6. **Check cost** → Should be $0 or very low

### Multi-Turn Conversation Test

**Goal**: Verify context retention

1. **Send**: "What is machine learning?"
2. **Wait for response**
3. **Send**: "Give me an example" (no context in message)
4. **Wait for response**
5. **Verify**: Response should provide ML example (context retained)

---

## Console Monitoring

Open **Developer Tools** (View → Developer → Developer Tools)

### Look for these logs:

**Startup**:
```
🚀 ACMS Desktop starting...
📐 Layout created
🧩 Components initialized
⌨️  Event listeners registered
🏥 API Health: connected
📚 Loaded N conversations
✅ ACMS Desktop ready!
```

**Sending Message**:
```
📤 Sending message: { message: "...", agent: "auto", streaming: true }
```

**Streaming**:
```
🤔 Status: { step: "..." }
✅ Stream complete: { answer: "...", cost: 0.0023, ... }
```

**Loading Conversation**:
```
📖 Loading conversation: <uuid>
✅ Loaded conversation with 5 messages
```

---

## Troubleshooting

### Issue: "Cannot connect to ACMS API"

**Fix**:
```bash
cd /path/to/acms
docker-compose ps  # Check all services are Up
docker-compose restart api  # Restart API if needed
```

### Issue: Conversations not loading

**Check**:
1. Open DevTools → Console
2. Look for error: "Failed to load conversations"
3. Check API endpoint: `http://localhost:40080/chat/conversations`

**Fix**:
```bash
curl "http://localhost:40080/chat/conversations?user_id=default_user"
# Should return JSON with conversations array
```

### Issue: Streaming not working

**Symptoms**: Full response appears at once (not character-by-character)

**Fix**:
1. Check console for streaming errors
2. Verify enableStreaming flag in app.js:28
3. Try sync mode temporarily:
   - Edit `app.js` line 28: `enableStreaming: false`
   - Restart app

### Issue: Gemini agent error

**Error**: `'GeminiAgent' object has no attribute 'cost_per_1m_input_tokens'`

**Fix**: Use Auto/Claude/GPT-4 agents instead (backend issue, see KNOWN_ISSUES.md)

---

## API Endpoints Reference

All endpoints run on `http://localhost:40080`

### Health Check
```bash
curl http://localhost:40080/health
# Returns: {"status": "healthy", "version": "1.0.0"}
```

### Send Message (Streaming)
```bash
curl -X POST http://localhost:40080/gateway/ask \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"query": "What is ACMS?", "conversation_id": null}'
# Returns: SSE stream
```

### List Conversations
```bash
curl "http://localhost:40080/chat/conversations?user_id=default_user&limit=20"
# Returns: {"conversations": [...], "total": N}
```

### Get Conversation
```bash
curl "http://localhost:40080/chat/conversations/<conversation-id>"
# Returns: {"id": "...", "messages": [...], "title": "..."}
```

---

## Success Criteria

Week 5 Day 3 features are working if:

- ✅ Responses stream character-by-character (not all at once)
- ✅ Conversations load and display in sidebar
- ✅ Time grouping works (Today/Yesterday/etc.)
- ✅ Clicking conversation loads all messages
- ✅ New chat button clears messages
- ✅ All metadata badges appear correctly
- ✅ Feedback buttons work
- ✅ No console errors (except Gemini agent)

---

## Next Steps (Week 5 Day 4)

Potential improvements to test:
- Conversation search
- Conversation deletion
- Title auto-generation
- Message search within conversation
- Export conversations

---

**Last Updated**: November 13, 2025
**Branch**: week5-production-quality-foundation
**Status**: Week 5 Day 3 Complete ✅
