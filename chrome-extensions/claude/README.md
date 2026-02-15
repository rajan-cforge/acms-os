# ACMS Claude.ai Extension

Chrome extension to automatically capture Claude.ai conversations into your local ACMS memory system.

## Features

- **Auto-Capture**: Monitors Claude.ai conversations in real-time, captures every 2 seconds
- **Privacy-Aware**: All data stored locally on your machine via ACMS API
- **Smart Tagging**: Auto-generates tags based on conversation topics (coding, writing, learning, research, planning)
- **Manual Control**: Toggle auto-capture on/off, trigger manual captures
- **Conversation Tracking**: Maintains conversation IDs from Claude.ai URLs
- **Statistics**: Real-time stats showing total captures and last capture time

## Installation

### Prerequisites

1. ACMS API must be running on `http://localhost:40080`

```bash
# Start ACMS
cd /path/to/acms
./start_desktop.sh
```

2. Verify API health:

```bash
curl http://localhost:40080/health
# Should return: {"status":"healthy",...}
```

### Load Extension

1. Open Chrome browser
2. Navigate to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top-right)
4. Click "Load unpacked"
5. Select directory: `/path/to/acms/chrome-extensions/claude`
6. Extension should appear with green status indicator

## Usage

### Auto-Capture (Default)

1. Open https://claude.ai
2. Start or continue a conversation
3. Extension automatically captures messages every 2 seconds
4. Click extension icon to see statistics
5. Captured conversations appear in ACMS Desktop App with tags: `claude`, `conversation`, `auto-captured`

### Manual Capture

1. Open Claude.ai conversation
2. Click ACMS extension icon
3. Click "Capture Now" button
4. Check Desktop App for new memory

### Toggle Capture

1. Click extension icon
2. Toggle "Auto-Capture" switch
3. Green = enabled, Gray = disabled

## What's Captured

Each capture includes:

- **Full conversation**: All user and assistant messages
- **Auto-tags**: claude, conversation, topic-based tags
- **Privacy level**: Auto-detected by ACMS privacy classifier
- **Metadata**:
  - `source`: "claude.ai"
  - `conversation_id`: Extracted from URL or generated
  - `message_count`: Total messages in conversation
  - `url`: Full claude.ai conversation URL
  - `captured_at`: ISO timestamp
- **Tier**: SHORT (default for conversations)
- **Phase**: "conversation"

## Troubleshooting

### Red Status Indicator

**Problem**: Extension can't connect to ACMS API

**Solution**:
```bash
# Check if API is running
curl http://localhost:40080/health

# If not, start ACMS
cd /path/to/acms
./start_desktop.sh
```

### No Messages Extracted

**Problem**: Claude.ai DOM structure may have changed

**Solution**:
1. Open Chrome DevTools (F12)
2. Go to Console tab
3. Look for `[ACMS Claude]` log messages
4. Check if "Extracted messages: 0" appears repeatedly
5. If yes, report issue (DOM selectors may need update)

### Conversations Not in Desktop App

**Problem**: API error or database issue

**Solution**:
```bash
# Check API logs
tail -f /path/to/acms/api_server.log

# Look for errors related to POST /memories
```

## Debugging

### Content Script Console

1. Open Claude.ai page
2. Press F12 (DevTools)
3. Go to Console tab
4. Filter by `[ACMS Claude]`
5. Check for extraction and capture logs

### Background Script Console

1. Go to `chrome://extensions/`
2. Find "ACMS Claude Capture"
3. Click "Inspect views: service worker"
4. Look for `[ACMS Background]` messages

## Architecture

### Content Script (`content.js`)

- Runs on all https://claude.ai/* pages
- Monitors DOM for conversation messages
- Extracts user/assistant message pairs
- Formats as readable markdown
- Sends to background script every 2 seconds

### Background Script (`background.js`)

- Service worker (Manifest V3)
- Handles API communication with ACMS
- Stores conversations via POST /memories
- Maintains API health checks
- Manages extension state

### Popup (`popup.html`, `popup.js`)

- Extension UI for user control
- Auto-capture toggle
- Manual capture button
- Real-time statistics
- ACMS health indicator

## Privacy

- All data stored locally on your machine
- No external servers contacted
- Only communicates with `localhost:40080` (your local ACMS)
- Privacy classification handled by ACMS API
- Toggle capture on/off anytime

## Technical Details

### DOM Extraction Strategy

Claude.ai uses React with dynamic class names, so extraction uses:

1. **Main content detection**: Finds `<main>` or `[role="main"]`
2. **Message heuristics**:
   - User messages: Shorter text, simpler structure
   - Assistant messages: Longer text, markdown/code blocks
3. **Deduplication**: Removes nested/duplicate content
4. **Role alternation**: Expects user → assistant → user pattern

### Message Format

```markdown
# Claude.ai Conversation

Captured: 2025-01-15T10:30:00.000Z
Messages: 4

---

## Human (1)

[User message content]

---

## Claude (2)

[Assistant response]

---

...
```

## Comparison with ChatGPT Extension

| Feature | ChatGPT | Claude |
|---------|---------|--------|
| Auto-capture | ✅ | ✅ |
| Manual capture | ✅ | ✅ |
| Privacy detection | ✅ | ✅ |
| Topic tagging | ✅ | ✅ |
| Conversation ID | From URL | From URL |
| DOM complexity | Moderate | High (React) |
| Extraction method | Class-based | Heuristic-based |

## Known Limitations

1. **DOM changes**: Claude.ai updates frequently, DOM structure may change
2. **Message extraction**: Heuristic-based, may occasionally miss messages
3. **SPA navigation**: Captures reset on navigation (by design)
4. **No retry logic**: Failed captures are logged but not retried

## Future Enhancements

- **Smarter DOM detection**: Use MutationObserver for real-time updates
- **Conversation threading**: Link related conversations
- **Export/import**: Backup captured conversations
- **Privacy presets**: User-defined privacy rules
- **Search integration**: Search ACMS from extension popup

## Success Criteria

✅ Extension loads without errors
✅ Green status indicator when ACMS running
✅ Claude.ai conversations auto-captured
✅ Conversations appear in Desktop App
✅ Privacy badges show correct levels
✅ Tags include: claude, conversation, topic tags

## Testing Checklist

- [ ] Install extension in Chrome
- [ ] Verify green status indicator
- [ ] Open Claude.ai and start conversation
- [ ] Send 3+ message exchanges
- [ ] Click extension icon, verify statistics
- [ ] Open ACMS Desktop App
- [ ] Refresh memories list
- [ ] Find newest memory with `claude` tag
- [ ] Click card to view full conversation
- [ ] Verify all messages captured correctly
- [ ] Verify privacy badge shows correct level

---

**Part of ACMS Phase 4c** - Web Extensions for AI Tools

Built with ❤️ for local-first AI memory management
