# ACMS UI Architecture - Complete Explanation

## Table of Contents
1. [Frontend Technology Primer](#frontend-technology-primer)
2. [Electron Framework Overview](#electron-framework-overview)
3. [ACMS Desktop App Architecture](#acms-desktop-app-architecture)
4. [How It All Works Together](#how-it-all-works-together)
5. [Component Deep Dive](#component-deep-dive)
6. [Data Flow](#data-flow)

---

## Frontend Technology Primer

### What is a Frontend/UI?

The **frontend** (or UI - User Interface) is everything the user sees and interacts with. Think of it like the dashboard of a car - it's what you look at and touch, while the engine (backend) does the actual work.

### Key Technologies Used in ACMS

#### 1. **HTML (HyperText Markup Language)**
- **What it is**: The structure/skeleton of a webpage
- **Like**: The frame of a house
- **In ACMS**: Defines where elements go (sidebar, chat area, buttons)

```html
<!-- Example: A button structure -->
<button id="send-btn">Send</button>
```

#### 2. **CSS (Cascading Style Sheets)**
- **What it is**: The styling/visual appearance
- **Like**: Paint, wallpaper, and decorations for the house
- **In ACMS**: Makes things look good (colors, spacing, animations)

```css
/* Example: Make button green */
.send-btn {
    background: #4CAF50;
    color: white;
    padding: 10px;
}
```

#### 3. **JavaScript (JS)**
- **What it is**: The behavior/logic - makes things interactive
- **Like**: The electrical system that makes lights turn on when you flip a switch
- **In ACMS**: Handles clicks, sends messages, updates the screen

```javascript
// Example: When button is clicked, do something
button.addEventListener('click', () => {
    sendMessage();
});
```

#### 4. **DOM (Document Object Model)**
- **What it is**: JavaScript's way of representing the HTML page as objects you can manipulate
- **Like**: A blueprint you can edit in real-time
- **In ACMS**: Used to add/remove messages, update UI dynamically

```javascript
// Example: Create a new message element
const messageDiv = document.createElement('div');
messageDiv.textContent = "Hello!";
container.appendChild(messageDiv);
```

### Frontend Layers (The Stack)

```
┌─────────────────────────────────────┐
│   User Interaction (Clicks, Typing)  │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   JavaScript (Event Handlers)      │  ← Logic layer
│   - Handles user actions            │
│   - Makes API calls                 │
│   - Updates the UI                  │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   DOM Manipulation                  │  ← Structure layer
│   - Creates/removes elements        │
│   - Updates text/content            │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   CSS Styling                       │  ← Presentation layer
│   - Colors, fonts, layout           │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   HTML Structure                    │  ← Content layer
│   - Buttons, divs, text areas       │
└─────────────────────────────────────┘
```

---

## Electron Framework Overview

### What is Electron?

**Electron** is a framework that lets you build desktop applications using web technologies (HTML, CSS, JavaScript) instead of native code (C++, Swift, etc.).

### Why Use Electron?

- ✅ Write once, run on Windows, Mac, and Linux
- ✅ Use familiar web technologies
- ✅ Access to native OS features (file system, notifications, etc.)
- ✅ Easier development than native apps

### How Electron Works

Electron has **two processes**:

#### 1. **Main Process** (`main.js`)
- **What it does**: Controls the application lifecycle
- **Responsibilities**:
  - Creates and manages windows
  - Handles system tray
  - Manages app menu
  - Can access Node.js APIs (file system, etc.)

```javascript
// main.js - Creates the app window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700
  });
  mainWindow.loadFile('index.html');
}
```

#### 2. **Renderer Process** (Your UI code)
- **What it does**: Renders the UI (like a web browser)
- **Responsibilities**:
  - Displays HTML/CSS/JS
  - Handles user interactions
  - Makes API calls
  - Updates the UI

```
┌─────────────────────────────────────┐
│   Main Process (main.js)            │
│   - Creates window                  │
│   - Manages app lifecycle           │
│   - System tray, menus             │
└─────────────────────────────────────┘
              ↓ loads
┌─────────────────────────────────────┐
│   Renderer Process                   │
│   ┌───────────────────────────────┐ │
│   │  index.html                   │ │
│   │  ┌─────────────────────────┐ │ │
│   │  │  JavaScript (app.js)    │ │ │
│   │  │  - UI logic             │ │ │
│   │  │  - API calls            │ │ │
│   │  └─────────────────────────┘ │ │
│   │  ┌─────────────────────────┐ │ │
│   │  │  CSS (chat.css)         │ │ │
│   │  │  - Styling              │ │ │
│   │  └─────────────────────────┘ │ │
│   └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Communication Between Processes

- **IPC (Inter-Process Communication)**: Main and renderer processes can send messages to each other
- **In ACMS**: Used for things like fetching memories, checking API health

---

## ACMS Desktop App Architecture

### High-Level Structure

```
desktop-app/
├── main.js                    # Electron main process
├── index.html                 # Entry point HTML
├── package.json               # Dependencies & config
└── src/
    └── renderer/              # All UI code (renderer process)
        ├── renderer.js        # Bootstrap/entry point
        ├── app.js             # Main application controller
        ├── components/         # Reusable UI components
        │   ├── message.js     # Message bubbles
        │   ├── input.js       # Input area
        │   ├── sidebar.js     # Navigation sidebar
        │   ├── login.js       # Authentication UI
        │   ├── file-upload.js # File upload handling
        │   └── views.js       # Different app views
        ├── utils/             # Helper functions
        │   ├── api.js         # API communication
        │   ├── streaming.js   # Real-time streaming
        │   ├── auth.js        # Authentication
        │   └── conversations.js # Conversation management
        └── styles/
            └── chat.css       # All styling
```

### Architecture Pattern: Component-Based

ACMS uses a **component-based architecture** - think of it like LEGO blocks:

- Each component is a self-contained piece of functionality
- Components can be reused
- Easy to test and maintain
- Clear separation of concerns

```
┌─────────────────────────────────────┐
│   App (app.js)                     │  ← Main controller
│   ┌─────────────────────────────┐ │
│   │  Sidebar Component          │ │  ← Navigation
│   └─────────────────────────────┘ │
│   ┌─────────────────────────────┐ │
│   │  Message Component           │ │  ← Displays messages
│   └─────────────────────────────┘ │
│   ┌─────────────────────────────┐ │
│   │  Input Component             │ │  ← User input
│   └─────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## How It All Works Together

### Application Startup Flow

```
1. User launches app
   ↓
2. Electron starts main process (main.js)
   ↓
3. main.js creates BrowserWindow
   ↓
4. Window loads index.html
   ↓
5. index.html loads renderer.js
   ↓
6. renderer.js creates AcmsApp instance
   ↓
7. AcmsApp.init() runs:
   - Checks API health
   - Checks authentication
   - Sets up layout
   - Initializes components
   - Loads initial data
   ↓
8. App is ready for user interaction
```

### Detailed Startup Sequence

#### Step 1: Main Process (`main.js`)

```javascript
// When app is ready, create window
app.whenReady().then(() => {
  createWindow();      // Creates the browser window
  createTray();        // Creates system tray icon
  checkAPIHealth();    // Checks if backend is running
});
```

#### Step 2: HTML Entry Point (`index.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="src/renderer/styles/chat.css">
</head>
<body>
    <div id="root">
        <!-- Loading message -->
    </div>
    <script>
        require('./src/renderer/renderer.js');
    </script>
</body>
</html>
```

#### Step 3: Bootstrap (`renderer.js`)

```javascript
// When page loads, create app
document.addEventListener('DOMContentLoaded', () => {
    const app = new AcmsApp();  // Create main app instance
    window.acmsApp = app;       // Make available globally
});
```

#### Step 4: App Initialization (`app.js`)

```javascript
class AcmsApp {
    async init() {
        // 1. Check API health
        await this.checkApiHealth();
        
        // 2. Check authentication
        const user = await checkExistingSession();
        
        if (user) {
            // 3. User is logged in - show main app
            this.initMainApp();
        } else {
            // 4. Show login screen
            this.showLoginScreen();
        }
    }
    
    initMainApp() {
        // 5. Create layout (sidebar + chat area)
        this.setupLayout();
        
        // 6. Initialize components
        this.setupComponents();
        
        // 7. Setup event listeners
        this.setupEventListeners();
        
        // 8. Load data
        await this.loadInitialData();
    }
}
```

---

## Component Deep Dive

### 1. Message Component (`components/message.js`)

**Purpose**: Renders chat messages (user and assistant)

**Key Functions**:
- `createMessageBubble()` - Creates a message element
- `createMetadataDisplay()` - Shows agent, cost, confidence
- `createThinkingSteps()` - Shows AI thinking process
- `createFeedbackButtons()` - Upvote/downvote buttons

**How it works**:
```javascript
// When a message needs to be displayed:
const message = {
    id: "msg-123",
    role: "assistant",
    content: "Hello! How can I help?",
    metadata: {
        agent: "claude",
        cost: 0.0025,
        confidence: 85
    }
};

// Create the visual element
const bubble = createMessageBubble(message);

// Add to page
container.appendChild(bubble);
```

**Security Note**: Uses `textContent` (safe) instead of `innerHTML` (dangerous) to prevent XSS attacks.

### 2. Input Component (`components/input.js`)

**Purpose**: Handles user input (typing, sending messages)

**Features**:
- Agent selector dropdown
- @ command parsing (`@claude`, `@gpt`, `@gemini`)
- Character counter
- File upload button
- Drag-and-drop support

**How it works**:
```javascript
// Setup input area
setupInputArea(
    (message, agent) => {
        // Called when user sends message
        handleSendMessage(message, agent);
    },
    (file, result) => {
        // Called when file is uploaded
        handleFileUploaded(file, result);
    }
);

// User types "@claude hello"
// → Automatically selects Claude agent
// → Removes "@claude" from message
// → Sends "hello" with Claude agent
```

### 3. Sidebar Component (`components/sidebar.js`)

**Purpose**: Navigation and conversation list

**Features**:
- App header with logo
- New chat button
- Navigation menu (Chat, Search, Analytics, etc.)
- Conversation history list

**How it works**:
```javascript
// Setup sidebar
setupSidebar(
    state,                    // App state
    (view) => {               // Called when view changes
        switchView(view);
    },
    (conversationId) => {     // Called when conversation clicked
        loadConversation(conversationId);
    }
);
```

### 4. API Utilities (`utils/api.js`)

**Purpose**: Communication with backend API

**Key Functions**:
- `checkHealth()` - Check if API is running
- `sendChatMessage()` - Send message (non-streaming)
- `loadConversations()` - Get conversation list

**How it works**:
```javascript
// Make API request
async function sendChatMessage(params) {
    const response = await fetch('http://localhost:40080/gateway/ask-sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: params.message,
            manual_agent: params.agent
        })
    });
    
    return await response.json();
}
```

### 5. Streaming Utilities (`utils/streaming.js`)

**Purpose**: Real-time streaming responses (like ChatGPT)

**How it works**:
```javascript
// Start streaming
streamChatMessage(
    { message: "Hello", agent: "claude" },
    {
        onChunk: (chunk, fullText) => {
            // Called for each piece of text
            updateMessage(fullText);
        },
        onComplete: (response) => {
            // Called when done
            finalizeMessage(response);
        }
    }
);
```

**Technical Details**:
- Uses `fetch()` with `ReadableStream` (not EventSource)
- Supports POST requests (EventSource only supports GET)
- Uses Server-Sent Events (SSE) format
- Can be aborted with `AbortController`

---

## Data Flow

### Sending a Message

```
User types message
    ↓
Input component captures text
    ↓
User clicks Send (or presses Enter)
    ↓
app.js.handleSendMessage() called
    ↓
Add user message to UI immediately
    ↓
Call streaming.js.streamChatMessage()
    ↓
Make POST request to /gateway/ask
    ↓
Backend streams response chunks
    ↓
For each chunk:
    - Update message in real-time
    - Show thinking steps
    ↓
When complete:
    - Finalize message with metadata
    - Save to conversation
    - Enable feedback buttons
```

### Loading a Conversation

```
User clicks conversation in sidebar
    ↓
sidebar.js calls onConversationLoad(conversationId)
    ↓
app.js.handleConversationLoad() called
    ↓
Make GET request to /conversations/{id}
    ↓
Backend returns conversation + messages
    ↓
Clear current messages
    ↓
For each message:
    - Create message bubble
    - Add to UI
    - Setup feedback listeners
    ↓
Scroll to bottom
```

### Authentication Flow

```
App starts
    ↓
Check localStorage for token
    ↓
If token exists:
    - Validate with backend
    - If valid: Show main app
    - If invalid: Show login
    ↓
If no token:
    - Show login screen
    ↓
User enters credentials
    ↓
POST to /auth/login
    ↓
Backend returns token + user data
    ↓
Store token in localStorage
    ↓
Show main app
```

---

## Key Concepts Explained

### State Management

**State** = The current data/status of the app

```javascript
// App state in app.js
this.state = {
    currentView: 'chat',
    messages: [],
    conversations: [],
    currentConversationId: null,
    loading: false,
    user: { email: 'user@example.com', role: 'member' }
};
```

When state changes, the UI updates to reflect it.

### Event Delegation

Instead of attaching listeners to every button, we listen on a parent element:

```javascript
// Instead of this (inefficient):
buttons.forEach(btn => {
    btn.addEventListener('click', handler);
});

// We do this (efficient):
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('feedback-btn')) {
        handleFeedback(e.target);
    }
});
```

**Why?**: Works for dynamically created elements (like new messages).

### Module System (CommonJS)

ACMS uses Node.js-style modules:

```javascript
// Export function
module.exports = { createMessageBubble };

// Import function
const { createMessageBubble } = require('./message.js');
```

**Why?**: Keeps code organized and reusable.

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Desktop Framework** | Electron | Runs web app as desktop app |
| **Structure** | HTML | Defines page structure |
| **Styling** | CSS | Makes it look good |
| **Logic** | JavaScript | Makes it interactive |
| **Module System** | CommonJS | Organizes code |
| **API Communication** | Fetch API | Talks to backend |
| **Streaming** | ReadableStream | Real-time responses |
| **Storage** | localStorage | Stores auth tokens |

---

## Security Features

1. **XSS Prevention**: Uses `textContent` instead of `innerHTML`
2. **CSP (Content Security Policy)**: Restricts what scripts can run
3. **Token Storage**: Auth tokens stored securely
4. **Input Validation**: Validates file types and sizes
5. **HTTPS**: API calls use secure connections (in production)

---

## Development Workflow

1. **Edit code** in `desktop-app/src/renderer/`
2. **Run app**: `npm start` (from desktop-app directory)
3. **See changes**: Electron auto-reloads (or restart app)
4. **Debug**: Open DevTools (Cmd+Shift+I or Ctrl+Shift+I)

---

## Common Patterns

### Creating UI Elements

```javascript
// 1. Create element
const div = document.createElement('div');

// 2. Set properties
div.className = 'message';
div.textContent = 'Hello!';

// 3. Add to page
container.appendChild(div);
```

### Making API Calls

```javascript
// 1. Make request
const response = await fetch('http://localhost:40080/endpoint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: 'value' })
});

// 2. Parse response
const data = await response.json();

// 3. Update UI
updateUI(data);
```

### Handling Events

```javascript
// 1. Get element
const button = document.getElementById('send-btn');

// 2. Add listener
button.addEventListener('click', () => {
    // Do something
    handleClick();
});
```

---

## Summary

The ACMS desktop app is built with:

1. **Electron** - Desktop framework
2. **Component-based architecture** - Modular, reusable code
3. **JavaScript** - Logic and interactivity
4. **CSS** - Styling and layout
5. **HTML** - Structure

**Key Flow**:
- User interacts → JavaScript handles → Updates DOM → CSS styles → User sees result

**Communication**:
- Frontend ↔ Backend via HTTP/SSE
- Main Process ↔ Renderer Process via IPC

The app is designed to be:
- ✅ Modular (easy to maintain)
- ✅ Secure (XSS prevention)
- ✅ Fast (streaming responses)
- ✅ User-friendly (modern UI)

---

## Next Steps for Learning

1. **HTML Basics**: Learn about elements, attributes
2. **CSS Basics**: Learn about selectors, properties
3. **JavaScript Basics**: Variables, functions, events
4. **DOM Manipulation**: Creating/updating elements
5. **Async/Await**: Handling API calls
6. **Electron Docs**: Understanding main vs renderer processes

---

*This document explains the ACMS UI architecture for someone new to frontend development. For more details, see the individual component files in `desktop-app/src/renderer/`.*



