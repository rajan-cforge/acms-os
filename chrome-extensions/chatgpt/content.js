/**
 * ACMS ChatGPT Content Script
 *
 * Monitors ChatGPT DOM for new messages and captures conversations.
 * Sends captured data to background script for storage in ACMS.
 */

console.log('[ACMS ChatGPT] Content script loaded');

// State
let isCapturing = true;
let lastProcessedMessageCount = 0;
let conversationId = null;

// Configuration
const CHECK_INTERVAL = 2000; // Check for new messages every 2 seconds
const MIN_MESSAGE_LENGTH = 10; // Minimum message length to capture

/**
 * Extract conversation ID from URL
 * @returns {string|null}
 */
function extractConversationId() {
  const url = window.location.href;
  const match = url.match(/\/c\/([a-f0-9-]+)/);
  return match ? match[1] : null;
}

/**
 * Extract message text from a message element
 * @param {Element} messageEl - Message DOM element
 * @returns {string}
 */
function extractMessageText(messageEl) {
  // ChatGPT uses markdown-rendered divs for message content
  const contentDiv = messageEl.querySelector('[data-message-author-role]') || messageEl;

  // Try to get text content, fallback to innerText
  let text = contentDiv.textContent || contentDiv.innerText || '';

  // Clean up whitespace
  text = text.trim().replace(/\s+/g, ' ');

  return text;
}

/**
 * Determine message role (user or assistant)
 * @param {Element} messageEl - Message DOM element
 * @returns {string} 'user' or 'assistant'
 */
function getMessageRole(messageEl) {
  // Check for data attribute
  const roleDiv = messageEl.querySelector('[data-message-author-role]');
  if (roleDiv) {
    const role = roleDiv.getAttribute('data-message-author-role');
    return role === 'user' ? 'user' : 'assistant';
  }

  // Fallback: Check for common class patterns
  const classes = messageEl.className || '';
  if (classes.includes('user')) return 'user';
  if (classes.includes('assistant') || classes.includes('agent')) return 'assistant';

  return 'assistant'; // Default to assistant
}

/**
 * Extract all messages from current conversation
 * @returns {Array<{role: string, content: string}>}
 */
function extractMessages() {
  // ChatGPT message selectors (may need adjustment based on UI updates)
  const messageSelectors = [
    'div[data-testid^="conversation-turn"]',
    'div.group.w-full',
    'div[class*="Message"]',
    'article'
  ];

  let messages = [];

  for (const selector of messageSelectors) {
    const messageElements = document.querySelectorAll(selector);

    if (messageElements.length > 0) {
      messages = Array.from(messageElements).map(el => {
        const role = getMessageRole(el);
        const content = extractMessageText(el);
        return { role, content };
      }).filter(m => m.content.length >= MIN_MESSAGE_LENGTH);

      if (messages.length > 0) {
        console.log(`[ACMS ChatGPT] Found ${messages.length} messages using selector: ${selector}`);
        break;
      }
    }
  }

  return messages;
}

/**
 * Format messages into conversation text
 * @param {Array} messages - Array of {role, content}
 * @returns {string}
 */
function formatConversation(messages) {
  return messages.map(msg => {
    const label = msg.role === 'user' ? 'User' : 'Assistant';
    return `${label}: ${msg.content}`;
  }).join('\n\n');
}

/**
 * Extract topic/tags from conversation
 * @param {Array} messages - Array of messages
 * @returns {Array<string>}
 */
function extractTags(messages) {
  const tags = ['chatgpt', 'conversation', 'auto-captured'];

  // Get first user message to infer topic
  const firstUserMsg = messages.find(m => m.role === 'user');
  if (!firstUserMsg) return tags;

  const content = firstUserMsg.content.toLowerCase();

  // Topic detection
  if (content.match(/\b(code|coding|program|function|debug|error|bug)\b/)) {
    tags.push('coding');
  }
  if (content.match(/\b(write|create|generate|draft|compose)\b/)) {
    tags.push('writing');
  }
  if (content.match(/\b(explain|what is|how does|why|describe)\b/)) {
    tags.push('learning');
  }
  if (content.match(/\b(invest|stock|money|finance|portfolio)\b/)) {
    tags.push('investment');
  }
  if (content.match(/\b(health|medical|symptom|doctor)\b/)) {
    tags.push('health');
  }

  return tags;
}

/**
 * Capture and send conversation to background script
 */
function captureConversation() {
  if (!isCapturing) {
    console.log('[ACMS ChatGPT] Capturing is disabled');
    return;
  }

  const messages = extractMessages();

  if (messages.length === 0) {
    console.log('[ACMS ChatGPT] No messages found in conversation');
    return;
  }

  // Check if new messages since last capture
  if (messages.length === lastProcessedMessageCount) {
    console.log('[ACMS ChatGPT] No new messages since last capture');
    return;
  }

  lastProcessedMessageCount = messages.length;
  conversationId = extractConversationId();

  // Format conversation
  const conversationText = formatConversation(messages);
  const tags = extractTags(messages);

  console.log(`[ACMS ChatGPT] Capturing conversation with ${messages.length} messages`);

  // Send to background script for storage
  chrome.runtime.sendMessage({
    type: 'capture-conversation',
    data: {
      content: conversationText,
      tags: tags,
      tier: 'SHORT', // Conversations are SHORT by default
      phase: 'conversation',
      auto_detect_privacy: true,
      metadata: {
        source: 'chatgpt',
        conversation_id: conversationId,
        message_count: messages.length,
        url: window.location.href,
        timestamp: new Date().toISOString()
      }
    }
  }, (response) => {
    if (response && response.success) {
      console.log('[ACMS ChatGPT] Conversation captured successfully:', response.memory_id);
    } else {
      console.error('[ACMS ChatGPT] Failed to capture conversation:', response?.error);
    }
  });
}

/**
 * Start monitoring for new messages
 */
function startMonitoring() {
  console.log('[ACMS ChatGPT] Starting conversation monitoring');

  // Initial capture
  setTimeout(captureConversation, 3000);

  // Periodic checks for new messages
  setInterval(() => {
    if (isCapturing) {
      captureConversation();
    }
  }, CHECK_INTERVAL);
}

/**
 * Listen for messages from popup/background
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[ACMS ChatGPT] Received message:', message);

  if (message.type === 'toggle-capture') {
    isCapturing = message.enabled;
    console.log(`[ACMS ChatGPT] Capture ${isCapturing ? 'enabled' : 'disabled'}`);
    sendResponse({ success: true, isCapturing });
  } else if (message.type === 'get-status') {
    sendResponse({
      isCapturing,
      messageCount: lastProcessedMessageCount,
      conversationId
    });
  } else if (message.type === 'capture-now') {
    captureConversation();
    sendResponse({ success: true });
  }

  return true; // Keep channel open for async response
});

// Initialize
startMonitoring();

// Log loaded status
console.log('[ACMS ChatGPT] Content script initialized and monitoring started');
