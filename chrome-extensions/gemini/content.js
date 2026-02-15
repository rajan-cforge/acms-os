/**
 * ACMS Google Gemini Content Script
 *
 * Monitors Gemini conversations and extracts messages for ACMS storage.
 *
 * Gemini DOM structure (as of 2025):
 * - Uses Material Design components
 * - Messages in structured chat containers
 * - User messages: typically in divs with user-related classes
 * - Model messages: responses with markdown and code blocks
 * - Uses Angular/Material with data attributes
 */

console.log('[ACMS Gemini] Content script loaded');

let captureEnabled = true;
let lastCapturedContent = '';
let captureStats = {
  totalCaptures: 0,
  lastCaptureTime: null,
  conversationId: null
};

// Load settings from storage
chrome.storage.local.get(['captureEnabled', 'captureStats'], (result) => {
  if (result.captureEnabled !== undefined) {
    captureEnabled = result.captureEnabled;
  }
  if (result.captureStats) {
    captureStats = result.captureStats;
  }
  console.log('[ACMS Gemini] Settings loaded:', { captureEnabled, captureStats });
});

// Listen for settings changes
chrome.storage.onChanged.addListener((changes) => {
  if (changes.captureEnabled) {
    captureEnabled = changes.captureEnabled.newValue;
    console.log('[ACMS Gemini] Capture enabled changed:', captureEnabled);
  }
});

/**
 * Extract messages from Gemini conversation
 *
 * Gemini uses Material Design with structured chat layout.
 * Look for:
 * 1. Chat container (main conversation area)
 * 2. Message bubbles or cards
 * 3. User vs Model message indicators
 */
function extractMessages() {
  const messages = [];

  // Strategy 1: Look for chat container
  // Gemini typically has a main chat area
  const chatContainer = document.querySelector('chat-window') ||
                        document.querySelector('[role="main"]') ||
                        document.querySelector('main') ||
                        document.querySelector('.chat-container') ||
                        document.body;

  if (!chatContainer) {
    console.log('[ACMS Gemini] Chat container not found');
    return messages;
  }

  console.log('[ACMS Gemini] Found chat container, searching for messages...');

  // Strategy 2: Find message containers
  // Gemini uses various selectors, try multiple approaches

  // Approach A: Look for message-content or similar classes
  const messageContentDivs = chatContainer.querySelectorAll(
    'message-content, .message-content, [class*="message"], [class*="response"]'
  );

  if (messageContentDivs.length > 0) {
    console.log('[ACMS Gemini] Found message divs (approach A):', messageContentDivs.length);

    messageContentDivs.forEach((div) => {
      const text = div.textContent?.trim() || '';
      if (text.length < 10) return;

      // Try to determine role from parent or sibling elements
      const isUser = div.closest('[class*="user"]') !== null ||
                     div.querySelector('[class*="user"]') !== null;
      const isModel = div.closest('[class*="model"]') !== null ||
                      div.querySelector('[class*="model"]') !== null;

      const role = isUser ? 'user' : (isModel ? 'assistant' : 'assistant');

      messages.push({ role, content: text });
    });
  }

  // Approach B: Look for structured chat messages by data attributes
  if (messages.length === 0) {
    const dataMessages = chatContainer.querySelectorAll('[data-message-author], [data-message-type]');

    console.log('[ACMS Gemini] Found data-attribute messages (approach B):', dataMessages.length);

    dataMessages.forEach((div) => {
      const text = div.textContent?.trim() || '';
      if (text.length < 10) return;

      const author = div.getAttribute('data-message-author') || '';
      const type = div.getAttribute('data-message-type') || '';

      const role = (author.toLowerCase().includes('user') || type === 'user') ? 'user' : 'assistant';

      messages.push({ role, content: text });
    });
  }

  // Approach C: Fallback - collect all text blocks
  if (messages.length === 0) {
    console.log('[ACMS Gemini] Using fallback text block collection');

    // Collect substantial text from paragraphs and divs
    const textElements = chatContainer.querySelectorAll('p, div[class*="text"], span[class*="text"]');
    const textBlocks = [];

    textElements.forEach(el => {
      const text = el.textContent?.trim() || '';
      if (text.length > 20 && !text.includes('Google') && !text.includes('Gemini')) {
        const isDuplicate = textBlocks.some(block => block.includes(text) || text.includes(block));
        if (!isDuplicate) {
          textBlocks.push(text);
        }
      }
    });

    console.log('[ACMS Gemini] Collected text blocks:', textBlocks.length);

    // Alternate between user and assistant
    textBlocks.forEach((text, index) => {
      messages.push({
        role: index % 2 === 0 ? 'user' : 'assistant',
        content: text
      });
    });
  }

  // Deduplicate messages
  const uniqueMessages = [];
  const seen = new Set();

  messages.forEach(msg => {
    const key = msg.role + ':' + msg.content.substring(0, 100);
    if (!seen.has(key)) {
      seen.add(key);
      uniqueMessages.push(msg);
    }
  });

  console.log('[ACMS Gemini] Extracted messages:', uniqueMessages.length);
  return uniqueMessages;
}

/**
 * Format conversation as readable text
 */
function formatConversation(messages) {
  if (messages.length === 0) return '';

  let formatted = '# Google Gemini Conversation\n\n';
  formatted += `Captured: ${new Date().toISOString()}\n`;
  formatted += `Messages: ${messages.length}\n\n`;
  formatted += '---\n\n';

  messages.forEach((msg, index) => {
    const roleLabel = msg.role === 'user' ? 'You' : 'Gemini';
    formatted += `## ${roleLabel} (${index + 1})\n\n`;
    formatted += msg.content + '\n\n';
    formatted += '---\n\n';
  });

  return formatted;
}

/**
 * Extract conversation ID from URL or generate one
 */
function getConversationId() {
  // Gemini URLs might be like: https://gemini.google.com/app/CONVERSATION_ID
  // or https://gemini.google.com/chat/CONVERSATION_ID
  const match = window.location.pathname.match(/\/(app|chat)\/([a-zA-Z0-9_-]+)/);
  if (match) {
    return match[2];
  }

  // Fallback: use or generate session ID
  if (captureStats.conversationId) {
    return captureStats.conversationId;
  }

  const newId = 'gemini_' + Date.now();
  captureStats.conversationId = newId;
  chrome.storage.local.set({ captureStats });
  return newId;
}

/**
 * Extract tags from conversation content
 */
function extractTags(messages) {
  const tags = ['gemini', 'conversation', 'auto-captured'];

  const fullText = messages.map(m => m.content).join(' ').toLowerCase();

  // Topic detection
  if (fullText.match(/\b(code|function|class|variable|debug|error|programming|python|javascript)\b/)) {
    tags.push('coding');
  }
  if (fullText.match(/\b(write|writing|essay|article|content|blog|story)\b/)) {
    tags.push('writing');
  }
  if (fullText.match(/\b(learn|learning|explain|understand|tutorial|teach)\b/)) {
    tags.push('learning');
  }
  if (fullText.match(/\b(research|analysis|data|study|paper|science)\b/)) {
    tags.push('research');
  }
  if (fullText.match(/\b(plan|planning|strategy|roadmap|schedule|organize)\b/)) {
    tags.push('planning');
  }
  if (fullText.match(/\b(creative|design|art|image|visual|draw)\b/)) {
    tags.push('creative');
  }

  return [...new Set(tags)]; // Remove duplicates
}

/**
 * Capture current conversation and send to ACMS
 */
async function captureConversation() {
  if (!captureEnabled) {
    console.log('[ACMS Gemini] Capture disabled, skipping');
    return;
  }

  const messages = extractMessages();

  if (messages.length === 0) {
    console.log('[ACMS Gemini] No messages found, skipping capture');
    return;
  }

  const content = formatConversation(messages);

  // Skip if content hasn't changed
  if (content === lastCapturedContent) {
    return;
  }

  lastCapturedContent = content;

  const conversationId = getConversationId();
  const tags = extractTags(messages);

  // Prepare memory data
  const memoryData = {
    content: content,
    tags: tags,
    phase: 'conversation',
    tier: 'SHORT',
    metadata: {
      source: 'gemini',
      conversation_id: conversationId,
      message_count: messages.length,
      url: window.location.href,
      captured_at: new Date().toISOString()
    }
  };

  console.log('[ACMS Gemini] Sending to background for storage:', {
    messageCount: messages.length,
    tags: tags,
    contentLength: content.length
  });

  // Send to background script
  chrome.runtime.sendMessage({
    type: 'capture-conversation',
    data: memoryData
  }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('[ACMS Gemini] Error sending message:', chrome.runtime.lastError);
      return;
    }

    if (response && response.success) {
      console.log('[ACMS Gemini] Capture successful:', response.memoryId);

      // Update stats
      captureStats.totalCaptures++;
      captureStats.lastCaptureTime = new Date().toISOString();
      chrome.storage.local.set({ captureStats });
    } else {
      console.error('[ACMS Gemini] Capture failed:', response?.error);
    }
  });
}

/**
 * Start monitoring conversation
 */
function startMonitoring() {
  console.log('[ACMS Gemini] Starting conversation monitoring');

  // Capture every 2 seconds when conversation changes
  setInterval(() => {
    captureConversation();
  }, 2000);

  // Also capture on page navigation (SPA)
  let lastUrl = window.location.href;
  setInterval(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      lastCapturedContent = ''; // Reset on navigation
      captureStats.conversationId = null; // Reset conversation ID
      console.log('[ACMS Gemini] Navigation detected, resetting capture');
    }
  }, 500);
}

// Listen for manual capture requests from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'capture-now') {
    console.log('[ACMS Gemini] Manual capture requested');
    lastCapturedContent = ''; // Force capture even if content same
    captureConversation();
    sendResponse({ success: true });
  }
  return true; // Keep channel open for async response
});

// Start monitoring when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startMonitoring);
} else {
  startMonitoring();
}

console.log('[ACMS Gemini] Content script initialized');
