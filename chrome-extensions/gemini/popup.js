/**
 * ACMS ChatGPT Popup Script
 *
 * Controls for the extension popup UI.
 * Manages capture toggle, displays stats, and triggers manual capture.
 */

console.log('[ACMS Popup] Popup script loaded');

// DOM elements
const statusIndicator = document.getElementById('status-indicator');
const statusMessage = document.getElementById('status-message');
const captureToggle = document.getElementById('capture-toggle');
const statTotal = document.getElementById('stat-total');
const statSuccess = document.getElementById('stat-success');
const statFailed = document.getElementById('stat-failed');
const lastCapture = document.getElementById('last-capture');
const captureNowBtn = document.getElementById('capture-now-btn');
const resetStatsBtn = document.getElementById('reset-stats-btn');

// State
let isCapturing = true;
let acmsHealthy = false;

/**
 * Show status message
 * @param {string} message - Message text
 * @param {string} type - Message type (success/error/info)
 */
function showStatus(message, type = 'info') {
  statusMessage.textContent = message;
  statusMessage.className = `status-message ${type}`;
  statusMessage.style.display = 'block';

  // Auto-hide after 3 seconds
  setTimeout(() => {
    statusMessage.style.display = 'none';
  }, 3000);
}

/**
 * Update capture toggle UI
 * @param {boolean} enabled - Whether capture is enabled
 */
function updateToggle(enabled) {
  isCapturing = enabled;
  if (enabled) {
    captureToggle.classList.add('active');
  } else {
    captureToggle.classList.remove('active');
  }

  // Update status indicator
  if (!acmsHealthy) {
    statusIndicator.className = 'status-indicator disconnected';
  } else if (!enabled) {
    statusIndicator.className = 'status-indicator disabled';
  } else {
    statusIndicator.className = 'status-indicator';
  }
}

/**
 * Update stats display
 * @param {Object} stats - Statistics object
 */
function updateStats(stats) {
  statTotal.textContent = stats.total || 0;
  statSuccess.textContent = stats.successful || 0;
  statFailed.textContent = stats.failed || 0;

  if (stats.lastCaptureTime) {
    const date = new Date(stats.lastCaptureTime);
    const timeAgo = getTimeAgo(date);
    lastCapture.textContent = `Last capture: ${timeAgo}`;
  } else {
    lastCapture.textContent = 'No captures yet';
  }
}

/**
 * Get human-readable time ago string
 * @param {Date} date - Date object
 * @returns {string}
 */
function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);

  if (seconds < 60) return `${seconds} seconds ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
  return `${Math.floor(seconds / 86400)} days ago`;
}

/**
 * Check ACMS API health
 */
async function checkHealth() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'check-health' });
    acmsHealthy = response.healthy;

    if (acmsHealthy) {
      console.log('[ACMS Popup] ✓ Connected to ACMS API');
    } else {
      console.warn('[ACMS Popup] ⚠️ Cannot connect to ACMS API');
      showStatus('⚠️ ACMS API not reachable. Is it running?', 'error');
    }

    updateToggle(isCapturing);
  } catch (error) {
    console.error('[ACMS Popup] Health check failed:', error);
    acmsHealthy = false;
    updateToggle(isCapturing);
  }
}

/**
 * Load capture stats from background
 */
async function loadStats() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'get-stats' });
    if (response && response.stats) {
      updateStats(response.stats);
    }
  } catch (error) {
    console.error('[ACMS Popup] Failed to load stats:', error);
  }
}

/**
 * Load capture state from storage
 */
async function loadCaptureState() {
  try {
    const result = await chrome.storage.local.get(['isCapturing']);
    isCapturing = result.isCapturing !== undefined ? result.isCapturing : true;
    updateToggle(isCapturing);
  } catch (error) {
    console.error('[ACMS Popup] Failed to load capture state:', error);
  }
}

/**
 * Toggle capture on/off
 */
async function toggleCapture() {
  isCapturing = !isCapturing;

  // Save to storage
  await chrome.storage.local.set({ isCapturing });

  // Update UI
  updateToggle(isCapturing);

  // Send message to content script
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url.includes('gemini.google.com')) {
      chrome.tabs.sendMessage(tab.id, {
        type: 'toggle-capture',
        enabled: isCapturing
      });

      showStatus(
        isCapturing ? '✓ Capture enabled' : '⏸ Capture paused',
        isCapturing ? 'success' : 'info'
      );
    }
  } catch (error) {
    console.error('[ACMS Popup] Failed to send toggle message:', error);
  }
}

/**
 * Trigger manual capture
 */
async function captureNow() {
  if (!acmsHealthy) {
    showStatus('⚠️ ACMS API not reachable', 'error');
    return;
  }

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab || !tab.url.includes('gemini.google.com')) {
      showStatus('⚠️ Open a Gemini conversation first', 'error');
      return;
    }

    // Send capture request to content script
    chrome.tabs.sendMessage(tab.id, { type: 'capture-now' }, (response) => {
      if (response && response.success) {
        showStatus('✓ Capturing conversation...', 'success');
        setTimeout(loadStats, 1000); // Reload stats after 1 second
      } else {
        showStatus('✗ Failed to capture', 'error');
      }
    });
  } catch (error) {
    console.error('[ACMS Popup] Manual capture failed:', error);
    showStatus('✗ Capture failed', 'error');
  }
}

/**
 * Reset statistics
 */
async function resetStats() {
  try {
    await chrome.runtime.sendMessage({ type: 'reset-stats' });
    updateStats({ total: 0, successful: 0, failed: 0, lastCaptureTime: null });
    showStatus('✓ Statistics reset', 'success');
  } catch (error) {
    console.error('[ACMS Popup] Failed to reset stats:', error);
    showStatus('✗ Failed to reset statistics', 'error');
  }
}

/**
 * Initialize popup
 */
async function init() {
  console.log('[ACMS Popup] Initializing popup');

  // Load initial state
  await loadCaptureState();
  await checkHealth();
  await loadStats();

  // Set up event listeners
  captureToggle.addEventListener('click', toggleCapture);
  captureNowBtn.addEventListener('click', captureNow);
  resetStatsBtn.addEventListener('click', resetStats);

  // Refresh stats every 5 seconds
  setInterval(loadStats, 5000);
}

// Start when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
