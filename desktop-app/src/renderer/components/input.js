/**
 * Input Area Component
 *
 * Week 5 Day 2 Task 3: Input with Agent Selector
 * Sprint 3 Day 13: File Upload capability
 *
 * Features:
 * - Agent selector dropdown (Auto, Claude, GPT-4, Gemini)
 * - @ command parsing (@claude, @gpt, @gemini)
 * - Keyboard shortcuts (Enter to send, Shift+Enter for newline)
 * - Character count and max length enforcement
 * - Auto-resize textarea
 * - File upload button and drag-drop support
 */

const { createUploadButton, setupDragAndDrop, uploadFile, createFilePreview, createUploadProgress } = require('./file-upload.js');

const MAX_INPUT_LENGTH = 10000;

// State for pending file
let pendingFile = null;

/**
 * Setup input area with agent selector and event handlers
 *
 * @param {Function} onSend - Callback(message, agent) when user sends message
 * @param {Function} onFileUpload - Callback(file, uploadResult) when file is uploaded
 */
function setupInputArea(onSend, onFileUpload) {
    const container = document.getElementById('input-area');

    // Create file preview container (above input)
    const filePreviewContainer = document.createElement('div');
    filePreviewContainer.id = 'file-preview-container';
    filePreviewContainer.className = 'file-preview-container';
    container.appendChild(filePreviewContainer);

    // Create input structure
    const inputContainer = document.createElement('div');
    inputContainer.className = 'input-container';

    // Agent selector
    const agentSelect = document.createElement('select');
    agentSelect.id = 'agent-selector';
    agentSelect.className = 'agent-selector';
    agentSelect.title = 'Choose AI agent or let ACMS auto-route';

    const agents = [
        { value: 'auto', label: '🤖 Auto', title: 'ACMS will choose the best agent' },
        { value: 'claude', label: '🟣 Claude Sonnet 4', title: 'Anthropic Claude Sonnet 4' },
        { value: 'gpt', label: '🟢 GPT-5.1', title: 'OpenAI GPT-5.1' },
        { value: 'gemini', label: '🔵 Gemini 3 Flash', title: 'Google Gemini 3 Flash' },
        { value: 'ollama', label: '🦙 Ollama Local', title: 'Local LLM via Ollama (Free, Private)' }
    ];

    agents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.value;
        option.textContent = agent.label;
        option.title = agent.title;
        agentSelect.appendChild(option);
    });

    inputContainer.appendChild(agentSelect);

    // File upload button (Sprint 3 Day 13)
    const uploadBtn = createUploadButton((file) => handleFileSelected(file, filePreviewContainer, onFileUpload));
    inputContainer.appendChild(uploadBtn);

    // Textarea
    const textarea = document.createElement('textarea');
    textarea.id = 'user-input';
    textarea.className = 'user-input';
    textarea.placeholder = 'Ask anything... (drag files here or use @claude, @gpt, @gemini, @ollama)';
    textarea.rows = 3;
    textarea.maxLength = MAX_INPUT_LENGTH;
    textarea.setAttribute('aria-label', 'Message input');
    inputContainer.appendChild(textarea);

    // Character counter
    const charCounter = document.createElement('div');
    charCounter.id = 'char-counter';
    charCounter.className = 'char-counter';
    charCounter.textContent = `0 / ${MAX_INPUT_LENGTH}`;
    inputContainer.appendChild(charCounter);

    // Send button
    const sendBtn = document.createElement('button');
    sendBtn.id = 'send-btn';
    sendBtn.className = 'send-btn';
    sendBtn.textContent = 'Send';
    sendBtn.title = 'Send message (Enter)';
    sendBtn.setAttribute('aria-label', 'Send message');
    inputContainer.appendChild(sendBtn);

    container.appendChild(inputContainer);

    // Setup drag-and-drop on the entire input area (Sprint 3 Day 13)
    setupDragAndDrop(container, (file) => handleFileSelected(file, filePreviewContainer, onFileUpload));

    // Setup event handlers
    setupEventHandlers(textarea, agentSelect, sendBtn, charCounter, onSend);

    console.log('⌨️  Input area initialized (with file upload)');
}

/**
 * Handle file selection (from button or drag-drop)
 */
async function handleFileSelected(file, previewContainer, onFileUpload) {
    console.log('📎 File selected:', file.name);

    // Clear any existing preview
    previewContainer.innerHTML = '';
    pendingFile = file;

    // Show file preview
    const preview = createFilePreview(file, () => {
        previewContainer.innerHTML = '';
        pendingFile = null;
    });
    previewContainer.appendChild(preview);

    // Upload immediately
    const progress = createUploadProgress(file.name);
    previewContainer.appendChild(progress.element);

    try {
        progress.update(50); // Show progress

        const result = await uploadFile(file);

        progress.complete(true, `Uploaded: ${file.name}`);

        // Callback with result
        if (onFileUpload) {
            onFileUpload(file, result);
        }

        // Clear pending file after successful upload
        pendingFile = null;

        // Remove progress after delay
        setTimeout(() => {
            progress.element.remove();
        }, 3000);

    } catch (error) {
        console.error('Upload failed:', error);
        progress.complete(false, `Upload failed: ${error.message}`);
        pendingFile = null;
    }
}

/**
 * Setup all event handlers for input area
 */
function setupEventHandlers(textarea, agentSelect, sendBtn, charCounter, onSend) {
    // Send button click
    sendBtn.addEventListener('click', () => {
        handleSend(textarea, agentSelect, onSend);
    });

    // Keyboard shortcuts
    textarea.addEventListener('keydown', (e) => {
        // Enter to send (without Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend(textarea, agentSelect, onSend);
        }

        // Shift+Enter for newline (default behavior)
        if (e.key === 'Enter' && e.shiftKey) {
            // Allow default behavior
        }
    });

    // @ command parsing
    textarea.addEventListener('input', (e) => {
        const text = e.target.value;

        // Update character counter
        updateCharCounter(charCounter, text.length);

        // Parse @ commands
        parseAtCommand(text, agentSelect);

        // Auto-resize textarea
        autoResize(textarea);
    });

    // Auto-resize on initial load
    autoResize(textarea);
}

/**
 * Handle sending a message
 */
function handleSend(textarea, agentSelect, onSend) {
    const message = textarea.value.trim();

    if (!message) {
        return;
    }

    const agent = agentSelect.value;

    // Remove @ command from message if present
    const cleanMessage = removeAtCommand(message);

    // Call the onSend callback
    onSend(cleanMessage, agent);

    // Clear input
    textarea.value = '';
    textarea.style.height = 'auto'; // Reset height

    // Update character counter
    const charCounter = document.getElementById('char-counter');
    updateCharCounter(charCounter, 0);

    // Focus back on textarea
    textarea.focus();
}

/**
 * Parse @ commands and update agent selector
 *
 * Supported commands:
 * - @claude or @sonnet → Select Claude
 * - @gpt or @chatgpt or @openai → Select GPT-4
 * - @gemini or @google → Select Gemini
 * - @auto → Select Auto
 *
 * @param {string} text - Input text
 * @param {HTMLSelectElement} agentSelect - Agent selector element
 */
function parseAtCommand(text, agentSelect) {
    // Only parse if text starts with @
    if (!text.startsWith('@')) {
        return;
    }

    // Extract first word after @
    const match = text.match(/^@(\w+)/);
    if (!match) return;

    const command = match[1].toLowerCase();

    // Map commands to agents
    const commandMap = {
        'claude': 'claude',
        'sonnet': 'claude',
        'gpt': 'gpt',
        'gpt4': 'gpt',
        'chatgpt': 'gpt',
        'openai': 'gpt',
        'gemini': 'gemini',
        'google': 'gemini',
        'ollama': 'ollama',
        'llama': 'ollama',
        'local': 'ollama',
        'auto': 'auto'
    };

    const agent = commandMap[command];

    if (agent) {
        agentSelect.value = agent;

        // Visual feedback: Flash the selector
        agentSelect.style.background = '#4CAF50';
        setTimeout(() => {
            agentSelect.style.background = '';
        }, 300);
    }
}

/**
 * Remove @ command from message text
 *
 * @param {string} text - Input text
 * @returns {string} Text without @ command
 */
function removeAtCommand(text) {
    // Remove @command at start of message
    return text.replace(/^@\w+\s*/, '');
}

/**
 * Update character counter
 *
 * @param {HTMLElement} charCounter - Character counter element
 * @param {number} length - Current length
 */
function updateCharCounter(charCounter, length) {
    charCounter.textContent = `${length} / ${MAX_INPUT_LENGTH}`;

    // Color code based on usage
    if (length > MAX_INPUT_LENGTH * 0.9) {
        charCounter.style.color = '#f44336'; // Red
    } else if (length > MAX_INPUT_LENGTH * 0.7) {
        charCounter.style.color = '#FFC107'; // Amber
    } else {
        charCounter.style.color = '#999'; // Gray
    }
}

/**
 * Auto-resize textarea to fit content
 *
 * @param {HTMLTextAreaElement} textarea - Textarea element
 */
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
}

/**
 * Focus the input textarea
 */
function focusInput() {
    const textarea = document.getElementById('user-input');
    if (textarea) {
        textarea.focus();
    }
}

/**
 * Disable input (during loading)
 *
 * @param {boolean} disabled - True to disable
 */
function setInputDisabled(disabled) {
    const textarea = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const agentSelect = document.getElementById('agent-selector');

    if (textarea) textarea.disabled = disabled;
    if (sendBtn) {
        sendBtn.disabled = disabled;
        sendBtn.textContent = disabled ? 'Sending...' : 'Send';
    }
    if (agentSelect) agentSelect.disabled = disabled;
}

// Export functions
module.exports = {
    setupInputArea,
    focusInput,
    setInputDisabled,
    parseAtCommand,
    removeAtCommand
};
