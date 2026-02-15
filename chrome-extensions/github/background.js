/**
 * ACMS ChatGPT Background Script
 *
 * Service worker that handles API communication with ACMS.
 * Receives messages from content script and stores them in ACMS.
 */

console.log('[ACMS Background] Service worker started');

const ACMS_API_BASE = 'http://localhost:40080';

// State
let captureStats = {
  total: 0,
  successful: 0,
  failed: 0,
  lastCaptureTime: null
};

/**
 * Check ACMS API health
 * @returns {Promise<boolean>}
 */
async function checkACMSHealth() {
  try {
    const response = await fetch(`${ACMS_API_BASE}/health`);
    return response.ok;
  } catch (error) {
    console.error('[ACMS Background] Health check failed:', error);
    return false;
  }
}

/**
 * Store memory in ACMS
 * @param {Object} memoryData - Memory data to store
 * @returns {Promise<Object>} Result with memory_id or error
 */
async function storeMemory(memoryData) {
  try {
    console.log('[ACMS Background] Storing memory:', memoryData);

    const response = await fetch(`${ACMS_API_BASE}/memories`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(memoryData),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API returned ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    console.log('[ACMS Background] Memory stored successfully:', result.memory_id);

    // Update stats
    captureStats.total++;
    captureStats.successful++;
    captureStats.lastCaptureTime = new Date().toISOString();

    return { success: true, memory_id: result.memory_id };
  } catch (error) {
    console.error('[ACMS Background] Failed to store memory:', error);

    // Update stats
    captureStats.total++;
    captureStats.failed++;

    return { success: false, error: error.message };
  }
}

/**
 * Handle messages from content scripts and popup
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[ACMS Background] Received message:', message.type);

  if (message.type === 'capture-conversation') {
    // Store conversation in ACMS
    storeMemory(message.data)
      .then(result => {
        sendResponse(result);
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });

    return true; // Keep channel open for async response
  }

  if (message.type === 'check-health') {
    checkACMSHealth()
      .then(healthy => {
        sendResponse({ healthy });
      });

    return true;
  }

  if (message.type === 'get-stats') {
    sendResponse({ stats: captureStats });
    return true;
  }

  if (message.type === 'reset-stats') {
    captureStats = {
      total: 0,
      successful: 0,
      failed: 0,
      lastCaptureTime: null
    };
    sendResponse({ success: true });
    return true;
  }
});

/**
 * Handle extension installation
 */
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('[ACMS Background] Extension installed:', details.reason);

  // Check ACMS API health on install
  const healthy = await checkACMSHealth();
  if (healthy) {
    console.log('[ACMS Background] ✓ Connected to ACMS API');
  } else {
    console.warn('[ACMS Background] ⚠️ Cannot connect to ACMS API. Make sure it\'s running on localhost:40080');
  }

  // Set default storage values
  await chrome.storage.local.set({
    isCapturing: true,
    autoDetectPrivacy: true
  });
});

/**
 * Periodic health check
 */
setInterval(async () => {
  const healthy = await checkACMSHealth();
  console.log(`[ACMS Background] Health check: ${healthy ? '✓ Connected' : '✗ Disconnected'}`);
}, 60000); // Check every minute

console.log('[ACMS Background] Background script initialized');
