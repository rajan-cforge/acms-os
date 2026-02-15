/**
 * ACMS Claude.ai Content Script
 *
 * Monitors Claude.ai conversations and extracts messages for ACMS storage.
 *
 * Claude.ai DOM structure (as of 2025):
 * - Conversations are in main content area
 * - User messages: div[data-test-render-count] or similar containing prompt text
 * - Assistant messages: div containing markdown rendered responses
 * - Uses React with dynamic class names
 */

console.log('[ACMS Claude] Content script loaded');

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
  console.log('[ACMS Claude] Settings loaded:', { captureEnabled, captureStats });
});

// Listen for settings changes
chrome.storage.onChanged.addListener((changes) => {
  if (changes.captureEnabled) {
    captureEnabled = changes.captureEnabled.newValue;
    console.log('[ACMS Claude] Capture enabled changed:', captureEnabled);
  }
});

/**
 * Extract messages from Claude.ai conversation
 *
 * Claude uses a dynamic React structure. We look for:
 * 1. Message containers with alternating user/assistant patterns
 * 2. User messages typically in simpler divs
 * 3. Assistant messages with markdown rendering
 */
function extractMessages() {
  const messages = [];

  // Strategy 1: Look for main conversation container
  // IMPORTANT: Exclude sidebar navigation from search
  // Claude.ai structure: sidebar on left, conversation on right

  // First, find the main element
  const mainElement = document.querySelector('main') || document.body;

  // Exclude elements from the sidebar navigation
  // Sidebar typically contains: conversation list, settings, profile
  const sidebarSelectors = [
    'nav',  // Navigation menu
    '[class*="sidebar"]',
    '[class*="menu"]',
    'aside',  // Sidebar element
    '[role="navigation"]',
    '[class*="conversations"]',  // Conversation list
    '[class*="chat-list"]'
  ];

  // Get all text elements but filter out sidebar content
  let allElements = Array.from(mainElement.querySelectorAll('p, div[class*="text"], div[class*="prose"], div[data-testid]'));

  // Filter out elements that are inside sidebar/navigation
  allElements = allElements.filter(el => {
    // Check if element or any parent is in sidebar
    let current = el;
    while (current && current !== mainElement) {
      // Check if this element matches any sidebar selector
      for (const selector of sidebarSelectors) {
        if (current.matches && current.matches(selector)) {
          return false;  // Skip this element
        }
      }
      // Check class names for sidebar indicators
      const className = current.className || '';
      if (typeof className === 'string' && (
          className.includes('sidebar') ||
          className.includes('navigation') ||
          className.includes('menu') ||
          className.includes('chat-list')
      )) {
        return false;
      }
      current = current.parentElement;
    }
    return true;  // Keep this element
  });

  console.log('[ACMS Claude] Found text elements (excluding sidebar):', allElements.length);

  // Additional filter: Skip elements that look like conversation titles/list items
  // Conversation titles are typically short (< 100 chars) and appear in lists
  allElements = allElements.filter(el => {
    const text = el.textContent?.trim() || '';

    // Skip very short text (likely titles/buttons)
    if (text.length < 30) return false;

    // Skip if text looks like a conversation title (short, no punctuation)
    const hasEndPunctuation = /[.!?]/.test(text);
    const isShort = text.length < 100;
    if (isShort && !hasEndPunctuation) {
      return false;  // Likely a title, not conversation content
    }

    // Skip common UI elements
    const uiKeywords = ['New chat', 'Upgrade', 'Settings', 'Profile', 'Sign out', 'Claude'];
    if (uiKeywords.some(keyword => text === keyword || text.startsWith(keyword))) {
      return false;
    }

    return true;
  });

  console.log('[ACMS Claude] Text elements after filtering UI:', allElements.length);

  // Collect all substantial text blocks
  const textBlocks = [];
  allElements.forEach(el => {
    const text = el.textContent?.trim() || '';
    if (text.length > 20) {
      // Skip if already contained in a previous block
      const isDuplicate = textBlocks.some(block => block.includes(text) || text.includes(block));
      if (!isDuplicate) {
        textBlocks.push(text);
      }
    }
  });

  console.log('[ACMS Claude] Collected text blocks:', textBlocks.length);

  // Now try the div-based approach as fallback
  const allDivs = mainContent.querySelectorAll('div');
  let currentRole = null;
  let currentText = '';

  allDivs.forEach((div) => {
    const text = div.textContent?.trim() || '';

    // Skip empty or very short divs
    if (text.length < 20) return;

    // Skip if this text is already captured in parent
    const isNested = Array.from(div.querySelectorAll('div')).some(child =>
      child.textContent?.trim() === text
    );
    if (isNested && div.children.length > 3) return;

    // Heuristic: Detect role based on context
    // User messages are typically shorter, at top of conversation blocks
    // Assistant messages are longer, follow user messages

    // Check if this looks like a new message block
    const hasCodeBlock = div.querySelector('pre, code');
    const hasMarkdown = div.querySelector('p, ul, ol, h1, h2, h3');
    const isLongText = text.length > 100;

    // If has markdown or code, likely assistant
    if (hasCodeBlock || hasMarkdown || isLongText) {
      if (currentRole === 'assistant' && currentText.length > 0) {
        // Continue existing assistant message
        if (!currentText.includes(text)) {
          currentText += '\n\n' + text;
        }
      } else {
        // New assistant message
        if (currentRole === 'user' && currentText.length > 0) {
          messages.push({ role: 'user', content: currentText });
        }
        currentRole = 'assistant';
        currentText = text;
      }
    } else {
      // Likely user message
      if (currentRole === 'assistant' && currentText.length > 0) {
        messages.push({ role: 'assistant', content: currentText });
        currentRole = 'user';
        currentText = text;
      } else if (currentRole === 'user') {
        // Continue user message or start new one
        if (!currentText.includes(text) && text.length > 20) {
          if (currentText.length > 0) {
            messages.push({ role: 'user', content: currentText });
          }
          currentText = text;
        }
      } else {
        // Start new user message
        currentRole = 'user';
        currentText = text;
      }
    }
  });

  // Push final message
  if (currentRole && currentText.length > 0) {
    messages.push({ role: currentRole, content: currentText });
  }

  // If we collected text blocks but no messages, use them
  if (messages.length === 0 && textBlocks.length > 0) {
    console.log('[ACMS Claude] Using text blocks as fallback');
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

  console.log('[ACMS Claude] Final extracted messages:', uniqueMessages.length);
  if (uniqueMessages.length > 0) {
    console.log('[ACMS Claude] Sample message:', uniqueMessages[0].content.substring(0, 100));
  }
  return uniqueMessages;
}

/**
 * Format conversation as readable text
 */
function formatConversation(messages) {
  if (messages.length === 0) return '';

  let formatted = '# Claude.ai Conversation\n\n';
  formatted += `Captured: ${new Date().toISOString()}\n`;
  formatted += `Messages: ${messages.length}\n\n`;
  formatted += '---\n\n';

  messages.forEach((msg, index) => {
    const roleLabel = msg.role === 'user' ? 'Human' : 'Claude';
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
  // Claude URLs are like: https://claude.ai/chat/uuid
  const match = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
  if (match) {
    return match[1];
  }

  // Fallback: use or generate session ID
  if (captureStats.conversationId) {
    return captureStats.conversationId;
  }

  const newId = 'claude_' + Date.now();
  captureStats.conversationId = newId;
  chrome.storage.local.set({ captureStats });
  return newId;
}

/**
 * Extract tags from conversation content
 */
function extractTags(messages) {
  const tags = ['claude', 'conversation', 'auto-captured'];

  const fullText = messages.map(m => m.content).join(' ').toLowerCase();

  // Topic detection
  if (fullText.match(/\b(code|function|class|variable|debug|error|programming)\b/)) {
    tags.push('coding');
  }
  if (fullText.match(/\b(write|writing|essay|article|content|blog)\b/)) {
    tags.push('writing');
  }
  if (fullText.match(/\b(learn|learning|explain|understand|tutorial)\b/)) {
    tags.push('learning');
  }
  if (fullText.match(/\b(research|analysis|data|study|paper)\b/)) {
    tags.push('research');
  }
  if (fullText.match(/\b(plan|planning|strategy|roadmap|schedule)\b/)) {
    tags.push('planning');
  }

  return [...new Set(tags)]; // Remove duplicates
}

/**
 * Capture current conversation and send to ACMS
 */
async function captureConversation() {
  if (!captureEnabled) {
    console.log('[ACMS Claude] Capture disabled, skipping');
    return;
  }

  const messages = extractMessages();

  if (messages.length === 0) {
    console.log('[ACMS Claude] No messages found, skipping capture');
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
      source: 'claude.ai',
      conversation_id: conversationId,
      message_count: messages.length,
      url: window.location.href,
      captured_at: new Date().toISOString()
    }
  };

  console.log('[ACMS Claude] Sending to background for storage:', {
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
      console.error('[ACMS Claude] Error sending message:', chrome.runtime.lastError);
      return;
    }

    if (response && response.success) {
      console.log('[ACMS Claude] Capture successful:', response.memoryId);

      // Update stats
      captureStats.totalCaptures++;
      captureStats.lastCaptureTime = new Date().toISOString();
      chrome.storage.local.set({ captureStats });
    } else {
      console.error('[ACMS Claude] Capture failed:', response?.error);
    }
  });
}

/**
 * Start monitoring conversation
 */
function startMonitoring() {
  console.log('[ACMS Claude] Starting conversation monitoring');

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
      console.log('[ACMS Claude] Navigation detected, resetting capture');
    }
  }, 500);
}

// Listen for manual capture requests from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'capture-now') {
    console.log('[ACMS Claude] Manual capture requested');
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

console.log('[ACMS Claude] Content script initialized');
