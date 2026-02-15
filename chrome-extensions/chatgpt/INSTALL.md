# Quick Installation Guide - ACMS ChatGPT Extension

## Step 1: Verify ACMS is Running

```bash
# Check API health
curl http://localhost:40080/health

# Should return: {"status":"healthy","service":"acms-api","version":"1.0.0",...}
```

If ACMS is not running:
```bash
cd /path/to/acms
./start_desktop.sh
```

## Step 2: Load Extension in Chrome

1. Open Chrome browser
2. Go to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top-right corner)
4. Click "Load unpacked" button
5. Navigate to: `/path/to/acms/chrome-extensions/chatgpt`
6. Click "Select Folder"

## Step 3: Verify Extension Loaded

You should see:
- ✅ "ACMS ChatGPT Capture" in extensions list
- ✅ Extension icon in Chrome toolbar (puzzle piece → pin it for easy access)
- ✅ Green status indicator (if ACMS API is reachable)

## Step 4: Test Capture

1. Open https://chatgpt.com
2. Start a new conversation (or continue existing one)
3. Send a message and get a response
4. Click the ACMS extension icon
5. Check statistics - should show "1" capture after ~2 seconds

## Step 5: View in Desktop App

1. Open ACMS Desktop App (should already be running)
2. Click "Refresh" button
3. Look for newest memory with tags: `chatgpt`, `conversation`, `auto-captured`
4. Click the memory card to see full conversation
5. Verify privacy badge shows 🔒 INTERNAL

## Troubleshooting

### Extension shows red indicator

**Problem**: Can't connect to ACMS API

**Solution**:
```bash
# Check if API is running
curl http://localhost:40080/health

# If not, start it
cd /path/to/acms
./start_desktop.sh
```

### No captures appearing

**Problem**: Auto-capture might be disabled

**Solution**:
1. Click extension icon
2. Check "Auto-Capture" toggle is green (enabled)
3. If gray, click it to enable

### Conversations not in Desktop App

**Problem**: API error or database issue

**Solution**:
```bash
# Check API logs
tail -f /path/to/acms/api_server.log

# Look for errors related to POST /memories
```

## Manual Testing

To manually trigger a capture:

1. Open ChatGPT conversation
2. Click ACMS extension icon
3. Click "Capture Now" button
4. Check Desktop App after 2 seconds

## Debugging

**Content Script Console**:
1. Open ChatGPT page
2. Press F12 (DevTools)
3. Go to Console tab
4. Look for messages starting with `[ACMS ChatGPT]`

**Background Script Console**:
1. Go to `chrome://extensions/`
2. Find "ACMS ChatGPT Capture"
3. Click "Inspect views: service worker"
4. Look for messages starting with `[ACMS Background]`

## Success Criteria

✅ Extension loads without errors
✅ Green status indicator in popup
✅ ChatGPT conversation auto-captured
✅ Conversation appears in Desktop App
✅ Privacy badge shows correct level
✅ Tags include: chatgpt, conversation, auto-captured

## What's Captured

Each capture includes:

- **Full conversation** (User + Assistant messages)
- **Auto-tags**: chatgpt, conversation, topic tags (coding/writing/learning/etc.)
- **Privacy level**: Auto-detected (usually INTERNAL for normal conversations)
- **Metadata**: conversation_id, message_count, url, timestamp
- **Tier**: SHORT (default for conversations)
- **Phase**: "conversation"

## Next Steps

Once ChatGPT extension is working:

1. **Phase 4c**: Build extensions for Claude, Gemini, Cursor (6 hours)
2. **Phase 5**: Context injection - retrieval from ACMS → AI tools (8 hours)
3. **MCP Integration**: Bidirectional sync with Claude Desktop

## Privacy Notes

- All data stored locally on your machine
- No external servers contacted
- Only communicates with `localhost:40080` (your local ACMS)
- Privacy detection protects sensitive content automatically
- Toggle capture on/off anytime via extension popup

---

**Ready to test? Follow steps 1-5 above and verify all ✅ criteria pass!**
