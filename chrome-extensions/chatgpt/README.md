# ACMS ChatGPT Capture Extension

Chrome extension for automatically capturing ChatGPT conversations to ACMS with privacy controls.

## Features

- **Automatic Conversation Capture**: Monitors ChatGPT for new messages and captures them automatically
- **Privacy Detection**: Uses ACMS privacy detection to classify conversations (PUBLIC/INTERNAL/CONFIDENTIAL/LOCAL_ONLY)
- **Smart Tagging**: Auto-tags conversations with topics (coding, writing, learning, investment, health)
- **Real-time Stats**: View capture statistics (total, successful, failed)
- **Manual Control**: Toggle auto-capture on/off, or trigger manual capture
- **Non-Intrusive**: Runs in the background with minimal performance impact

## Installation

### Prerequisites

1. ACMS API server must be running on `localhost:40080`
2. Docker containers for PostgreSQL, Weaviate, and Ollama must be running
3. Chrome browser

### Install Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Navigate to `/path/to/acms/chrome-extensions/chatgpt`
5. Click "Select Folder"

The extension should now appear in your extensions list with a green status indicator if ACMS is reachable.

## Usage

### Auto-Capture (Default)

1. Open ChatGPT (https://chatgpt.com)
2. Start a conversation
3. Extension automatically captures messages every 2 seconds
4. Check Desktop App to see captured conversations

### Manual Capture

1. Click the ACMS extension icon in Chrome toolbar
2. Click "Capture Now" button
3. Current conversation is captured immediately

### Toggle Capture

1. Click the ACMS extension icon
2. Click the "Auto-Capture" toggle
3. When disabled (gray), conversations are NOT captured
4. When enabled (green), conversations are auto-captured

## Privacy Controls

All captured conversations are automatically classified:

- **🔒 INTERNAL** (Default): Personal AI conversations, safe for your tools only
- **🔐 CONFIDENTIAL**: Investment/health discussions detected from keywords
- **⛔ LOCAL_ONLY**: API keys/passwords detected (rare in normal conversations)
- **🔓 PUBLIC**: Documentation/tutorials (if detected)

Privacy level is determined by:
- Content analysis (keywords, patterns)
- Auto-tagging (coding, investment, health, etc.)
- ACMS privacy detection engine

## Architecture

```
ChatGPT Page
     ↓
content.js (monitors DOM)
     ↓
background.js (API communication)
     ↓
ACMS API (localhost:40080)
     ↓
PostgreSQL + Weaviate
     ↓
Desktop App (view all captures)
```

## Files

- `manifest.json`: Extension configuration
- `content.js`: DOM monitoring and message extraction
- `background.js`: API communication with ACMS
- `popup.html`: Extension popup UI
- `popup.js`: Popup logic and controls
- `icons/`: Extension icons (16px, 48px, 128px)

## Configuration

Edit `content.js` to adjust:

```javascript
const CHECK_INTERVAL = 2000; // How often to check for new messages (ms)
const MIN_MESSAGE_LENGTH = 10; // Minimum message length to capture
```

Edit `background.js` to change API endpoint:

```javascript
const ACMS_API_BASE = 'http://localhost:40080';
```

## Troubleshooting

### Extension shows red indicator

- **Cause**: ACMS API not reachable
- **Fix**:
  1. Check if Docker containers are running: `docker ps`
  2. Check if API server is running: `curl http://localhost:40080/health`
  3. Start API if needed: `cd /path/to/acms && ./start_desktop.sh`

### No conversations captured

- **Cause**: Auto-capture is disabled or ChatGPT DOM changed
- **Fix**:
  1. Check extension popup - ensure toggle is green (enabled)
  2. Open Chrome DevTools (F12) and check Console for errors
  3. Look for messages starting with `[ACMS ChatGPT]`

### Conversations captured but not in Desktop App

- **Cause**: API error or database issue
- **Fix**:
  1. Check `api_server.log` for errors
  2. Check Desktop App refresh - click "Refresh" button
  3. Try manual capture and check Console for error messages

## Development

### Testing

1. Load extension in Chrome
2. Open `chrome://extensions/` and find "ACMS ChatGPT Capture"
3. Click "Inspect views: service worker" to see background console
4. Open ChatGPT and start a conversation
5. Check Console for capture messages
6. Verify conversation appears in ACMS Desktop App

### Debugging

**Content Script Logs**:
- Open ChatGPT page
- Press F12 to open DevTools
- Go to Console tab
- Look for `[ACMS ChatGPT]` messages

**Background Script Logs**:
- Go to `chrome://extensions/`
- Find "ACMS ChatGPT Capture"
- Click "Inspect views: service worker"
- Look for `[ACMS Background]` messages

**Popup Logs**:
- Click extension icon to open popup
- Right-click popup and select "Inspect"
- Look for `[ACMS Popup]` messages

## Privacy & Security

- **Local Only**: All data stored locally on your machine
- **No Cloud**: Extension does NOT send data to any external servers
- **API Endpoint**: Only communicates with `localhost:40080` (your local ACMS)
- **Privacy Detection**: Automatically detects and protects sensitive content
- **User Control**: Full control over what gets captured (toggle on/off)

## Limitations

- **ChatGPT Only**: Only works on chatgpt.com and chat.openai.com
- **DOM Dependent**: If ChatGPT UI changes, selectors may need updating
- **Local ACMS Required**: Requires running ACMS instance on localhost
- **Chrome Only**: Currently only works in Chrome (could be ported to Firefox)

## Next Steps

See parent README for:
- Phase 4c: Claude, Gemini, Cursor extensions
- Phase 5: Context injection (two-way sync)
- MCP integration

## Support

For issues or questions:
1. Check logs in `api_server.log`
2. Check extension console logs
3. Verify ACMS API health: `curl http://localhost:40080/health`
