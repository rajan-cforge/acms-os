# ACMS Google Gemini Extension

Chrome extension to automatically capture Google Gemini conversations into your local ACMS memory system.

## Features

- **Auto-Capture**: Monitors Gemini conversations in real-time, captures every 2 seconds
- **Privacy-Aware**: All data stored locally on your machine via ACMS API
- **Smart Tagging**: Auto-generates tags based on conversation topics (coding, writing, learning, research, planning, creative)
- **Manual Control**: Toggle auto-capture on/off, trigger manual captures
- **Conversation Tracking**: Maintains conversation IDs from Gemini URLs
- **Statistics**: Real-time stats showing total captures and last capture time
- **Material Design Compatible**: Works with Gemini's Angular/Material UI

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
5. Select directory: `/path/to/acms/chrome-extensions/gemini`
6. Extension should appear with green status indicator

## Usage

### Auto-Capture (Default)

1. Open https://gemini.google.com
2. Start or continue a conversation
3. Extension automatically captures messages every 2 seconds
4. Click extension icon to see statistics
5. Captured conversations appear in ACMS Desktop App with tags: `gemini`, `conversation`, `auto-captured`

### Manual Capture

1. Open Gemini conversation
2. Click ACMS extension icon
3. Click "Capture Now" button
4. Check Desktop App for new memory

### Toggle Capture

1. Click extension icon
2. Toggle "Auto-Capture" switch
3. Green = enabled, Gray = disabled

## What's Captured

Each capture includes:

- **Full conversation**: All user and Gemini messages
- **Auto-tags**: gemini, conversation, topic-based tags
- **Privacy level**: Auto-detected by ACMS privacy classifier
- **Metadata**:
  - `source`: "gemini"
  - `conversation_id`: Extracted from URL or generated
  - `message_count`: Total messages in conversation
  - `url`: Full gemini.google.com conversation URL
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

**Problem**: Gemini DOM structure may have changed or not loaded

**Solution**:
1. Wait a few seconds for page to fully load
2. Open Chrome DevTools (F12)
3. Go to Console tab
4. Look for `[ACMS Gemini]` log messages
5. Check which extraction approach is being used (A, B, or C)
6. If "Extracted messages: 0" appears repeatedly, DOM selectors may need update

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

1. Open Gemini page
2. Press F12 (DevTools)
3. Go to Console tab
4. Filter by `[ACMS Gemini]`
5. Check extraction approach and message count

### Background Script Console

1. Go to `chrome://extensions/`
2. Find "ACMS Gemini Capture"
3. Click "Inspect views: service worker"
4. Look for `[ACMS Background]` messages

## Architecture

### Content Script (`content.js`)

- Runs on all https://gemini.google.com/* pages
- Uses 3-tier extraction strategy:
  - **Approach A**: Class-based selectors (message-content, .message)
  - **Approach B**: Data attributes (data-message-author, data-message-type)
  - **Approach C**: Heuristic analysis (fallback)
- Formats as readable markdown
- Sends to background script every 2 seconds

### Extraction Strategy

Gemini uses Material Design with dynamic Angular components, requiring flexible extraction:

1. **Approach A - Class-based**: Look for message-content, .message, [class*="message"]
2. **Approach B - Data attributes**: Search for [data-message-author], [data-message-type]
3. **Approach C - Heuristic**: Analyze text blocks, detect user vs assistant by length/markdown presence

### Message Format

```markdown
# Google Gemini Conversation

Captured: 2025-01-15T10:30:00.000Z
Messages: 4

---

## You (1)

[User message content]

---

## Gemini (2)

[Assistant response with markdown/code]

---

...
```

## Background Script (`background.js`)

- Service worker (Manifest V3)
- Handles API communication with ACMS
- Stores conversations via POST /memories
- Maintains API health checks
- Manages extension state

## Popup (`popup.html`, `popup.js`)

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

### DOM Extraction Challenges

Gemini's Material Design presents unique challenges:

1. **Dynamic class names**: Angular generates random class names
2. **Component nesting**: Messages nested in multiple Material components
3. **Lazy loading**: Messages may load incrementally
4. **Shadow DOM**: Some components may use Shadow DOM (not common)

### Solution: Multi-Strategy Extraction

The extension tries 3 approaches in order, using the first that succeeds:
- Class-based → Data attributes → Heuristic analysis

This ensures robustness against UI updates.

## Comparison with ChatGPT/Claude Extensions

| Feature | ChatGPT | Claude | Gemini |
|---------|---------|--------|--------|
| Auto-capture | ✅ | ✅ | ✅ |
| Manual capture | ✅ | ✅ | ✅ |
| Privacy detection | ✅ | ✅ | ✅ |
| Topic tagging | 5 topics | 5 topics | 6 topics |
| Conversation ID | From URL | From URL | From URL |
| DOM complexity | Moderate | High (React) | High (Angular/Material) |
| Extraction method | Class-based | Heuristic | 3-tier fallback |
| Special features | - | - | Creative tag |

## Known Limitations

1. **DOM changes**: Gemini updates frequently, DOM structure may change
2. **Message extraction**: May occasionally miss messages if structure changes
3. **SPA navigation**: Captures reset on navigation (by design)
4. **No retry logic**: Failed captures are logged but not retried
5. **Material Design**: Complex component nesting may affect accuracy

## Future Enhancements

- **MutationObserver**: Real-time DOM change detection
- **Image capture**: Save Gemini-generated images to ACMS
- **Multi-modal support**: Handle image inputs and outputs
- **Conversation threading**: Link related conversations
- **Export/import**: Backup captured conversations
- **Search integration**: Search ACMS from extension popup

## Success Criteria

✅ Extension loads without errors
✅ Green status indicator when ACMS running
✅ Gemini conversations auto-captured
✅ Conversations appear in Desktop App
✅ Privacy badges show correct levels
✅ Tags include: gemini, conversation, topic tags

## Testing Checklist

- [ ] Install extension in Chrome
- [ ] Verify green status indicator
- [ ] Open Gemini and start conversation
- [ ] Send 3+ message exchanges
- [ ] Test with code blocks and markdown
- [ ] Click extension icon, verify statistics
- [ ] Open ACMS Desktop App
- [ ] Refresh memories list
- [ ] Find newest memory with `gemini` tag
- [ ] Click card to view full conversation
- [ ] Verify all messages captured correctly
- [ ] Verify privacy badge shows correct level

## Special Notes

### Gemini Multimodal

Gemini supports images and other modalities. Current version captures:
- ✅ Text messages (user and assistant)
- ❌ Image inputs (not captured)
- ❌ Image outputs (not captured)
- ❌ File uploads (not captured)

Future versions may support multimodal capture.

---

**Part of ACMS Phase 4c** - Web Extensions for AI Tools

Built with ❤️ for local-first AI memory management
