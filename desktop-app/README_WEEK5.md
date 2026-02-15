# ACMS Desktop - Week 5 Production Architecture

## 📁 New Modular Structure (Week 5 Day 2)

```
desktop-app/
├── index.html                     # Main HTML (minimal, loads renderer.js)
├── main.js                        # Electron main process (unchanged)
├── package.json                   # Dependencies
└── src/
    └── renderer/
        ├── renderer.js            # Bootstrap file (entry point)
        ├── app.js                 # Main application controller
        ├── components/
        │   ├── message.js         # Message bubble rendering
        │   ├── input.js           # Input area with agent selector
        │   └── sidebar.js         # Navigation & conversation list
        ├── utils/
        │   └── api.js             # API communication utilities
        └── styles/
            └── chat.css           # All UI styles
```

## 🎯 Key Features

### 1. **Component-Based Architecture**
- Each UI component is a separate, testable module
- Clean separation of concerns
- Easy to maintain and extend

### 2. **Message Rendering System** (`components/message.js`)
```javascript
createMessageBubble(message)     // Render user or assistant message
createMetadataDisplay(metadata)  // Show agent, cache, cost, confidence
createThinkingSteps(steps)       // Expandable thinking process
createFeedbackButtons(id)        // Upvote/downvote buttons
```

**Security**: All DOM manipulation uses `createElement()` and `textContent` - **no innerHTML** to prevent XSS attacks.

### 3. **Input Area with Agent Selector** (`components/input.js`)
```javascript
setupInputArea(onSend)           // Initialize input area
parseAtCommand(text)             // Parse @claude, @gpt, @gemini
```

**Features**:
- Agent selector dropdown (Auto, Claude, GPT-4, Gemini)
- @ command shortcuts: `@claude`, `@gpt`, `@gemini`
- Keyboard shortcuts: Enter to send, Shift+Enter for newline
- Auto-resize textarea
- Character counter (max 10,000)
- Input validation

### 4. **Sidebar Navigation** (`components/sidebar.js`)
```javascript
setupSidebar(state, onViewChange) // Render sidebar with nav
```

**Features**:
- New chat button (Cmd/Ctrl+N)
- Navigation: Chat, Search, Analytics, Settings
- Conversation list with timestamps
- Responsive design

### 5. **API Utilities** (`utils/api.js`)
```javascript
checkHealth()                     // API health check
sendChatMessage(params)           // Send message, get response
loadConversations(limit)          // Load conversation list
submitFeedback(id, type)          // Submit upvote/downvote
```

**Features**:
- 30-second timeout
- Error handling
- Request/response logging
- Consistent error messages

## 🚀 How to Run

```bash
# From ACMS root directory
cd desktop-app
npm start
```

## 🎨 UI Components

### Message Bubble Structure
```
┌─────────────────────────────────────┐
│ ASSISTANT                           │
│                                     │
│ Response text here...               │
│                                     │
│ ┌─────────────────────────────┐   │
│ │ 🟢 GPT-4  ⚡ Cached         │   │
│ │ $0.0025   85% confidence    │   │
│ └─────────────────────────────┘   │
│                                     │
│ 🤔 View thinking process (3 steps)│
│ ▼                                  │
│                                     │
│ 👍 👎                              │
│ 2 minutes ago                       │
└─────────────────────────────────────┘
```

### Input Area Structure
```
┌──────────────────────────────────────────────────┐
│ [🤖 Auto ▼] [Type message...                   ] │
│                                          0 / 10000│
│                                          [Send]   │
└──────────────────────────────────────────────────┘
```

## 🔧 Development

### Adding a New Component

1. Create component file in `src/renderer/components/`
2. Export functions via `module.exports`
3. Import in `app.js`
4. Call setup function in `AcmsApp.init()`

Example:
```javascript
// src/renderer/components/my-component.js
function setupMyComponent(state, callback) {
    // Component logic here
}

module.exports = { setupMyComponent };

// src/renderer/app.js
const { setupMyComponent } = require('./components/my-component.js');
```

### Adding API Endpoints

Add new function to `utils/api.js`:
```javascript
async function myNewEndpoint(params) {
    return await makeRequest('/my-endpoint', {
        method: 'POST',
        body: JSON.stringify(params)
    });
}

module.exports = { ...existing, myNewEndpoint };
```

## ✅ Week 5 Day 2 Completion

**Tasks Completed**:
- ✅ Task 1: App Structure Refactor (3 hours)
- ✅ Task 2: Message Rendering System (2 hours)
- ✅ Task 3: Input Area with Agent Selector (1 hour)

**Files Created** (7 new files):
1. `src/renderer/renderer.js` - Bootstrap
2. `src/renderer/app.js` - Main controller (10KB)
3. `src/renderer/components/message.js` - Message rendering (9KB)
4. `src/renderer/components/input.js` - Input area (6KB)
5. `src/renderer/components/sidebar.js` - Sidebar (4KB)
6. `src/renderer/utils/api.js` - API utilities (4KB)
7. `src/renderer/styles/chat.css` - Styles (12KB)

**Total Code**: ~45KB of clean, modular, production-quality code

**Backup Files**:
- `index.html.backup` - Original 138KB monolithic file
- `renderer.js.backup` - Original HTML with embedded CSS

## 🎯 Next Steps (Week 5 Day 3)

1. Test the new UI
2. Fix any loading/rendering issues
3. Add conversation history loading
4. Implement streaming responses
5. Add real-time pipeline visualization

## 🐛 Known Issues

None yet - this is the initial implementation!

## 📝 Notes

- Old monolithic files backed up as `.backup`
- All components use event delegation for dynamic content
- Security: No innerHTML, all DOM manipulation via createElement
- Follows Week 5 production-quality standards
