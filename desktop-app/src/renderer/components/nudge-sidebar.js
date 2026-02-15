/**
 * Nudge Sidebar Component
 *
 * Active Second Brain (Jan 2026)
 *
 * Displays proactive nudges ("Tap on Shoulder"):
 * - New learning notifications
 * - Stale knowledge reminders
 * - Low confidence items needing review
 * - Insight availability alerts
 *
 * Features:
 * - Priority-sorted display (high first)
 * - Snooze and dismiss actions
 * - Click to navigate to related item
 * - Badge count in sidebar
 *
 * Security: No innerHTML, DOM-safe operations only.
 */

// Nudge state
let nudgeState = {
    nudges: [],
    isOpen: false,
    pollInterval: null
};

// API base URL
const API_BASE = 'http://localhost:40080';

// Nudge type icons
const NUDGE_ICONS = {
    new_learning: '📚',
    stale_knowledge: '⏰',
    low_confidence: '❓',
    correction_suggested: '✏️',
    review_reminder: '👀',
    insight_available: '💡'
};

// Nudge type colors
const NUDGE_COLORS = {
    new_learning: '#4CAF50',      // Green
    stale_knowledge: '#FF9800',   // Orange
    low_confidence: '#2196F3',    // Blue
    correction_suggested: '#9C27B0', // Purple
    review_reminder: '#607D8B',   // Gray
    insight_available: '#00BCD4'  // Cyan
};

/**
 * Create the nudge sidebar element
 * @returns {HTMLElement} Sidebar container
 */
function createNudgeSidebar() {
    const sidebar = document.createElement('div');
    sidebar.id = 'nudge-sidebar';
    sidebar.className = 'nudge-sidebar hidden';

    // Header
    const header = document.createElement('div');
    header.className = 'nudge-sidebar-header';

    const title = document.createElement('h3');
    title.textContent = '🔔 Notifications';
    header.appendChild(title);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'nudge-sidebar-close';
    closeBtn.textContent = '×';
    closeBtn.addEventListener('click', closeNudgeSidebar);
    header.appendChild(closeBtn);

    sidebar.appendChild(header);

    // Body (nudge list)
    const body = document.createElement('div');
    body.id = 'nudge-sidebar-body';
    body.className = 'nudge-sidebar-body';
    sidebar.appendChild(body);

    // Footer
    const footer = document.createElement('div');
    footer.className = 'nudge-sidebar-footer';

    const clearAllBtn = document.createElement('button');
    clearAllBtn.className = 'nudge-clear-all-btn';
    clearAllBtn.textContent = 'Clear All';
    clearAllBtn.addEventListener('click', clearAllNudges);
    footer.appendChild(clearAllBtn);

    sidebar.appendChild(footer);

    return sidebar;
}

/**
 * Create the nudge toggle button for main UI
 * @returns {HTMLElement} Toggle button
 */
function createNudgeToggleButton() {
    const btn = document.createElement('button');
    btn.id = 'nudge-toggle-btn';
    btn.className = 'nudge-toggle-btn';
    btn.title = 'Notifications';

    const icon = document.createElement('span');
    icon.className = 'nudge-toggle-icon';
    icon.textContent = '🔔';
    btn.appendChild(icon);

    const badge = document.createElement('span');
    badge.id = 'nudge-badge';
    badge.className = 'nudge-badge hidden';
    badge.textContent = '0';
    btn.appendChild(badge);

    btn.addEventListener('click', toggleNudgeSidebar);

    return btn;
}

/**
 * Render nudges in the sidebar
 */
function renderNudges() {
    const body = document.getElementById('nudge-sidebar-body');
    if (!body) return;

    // Clear existing
    body.innerHTML = '';

    if (nudgeState.nudges.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'nudge-empty';
        empty.textContent = 'No notifications';
        body.appendChild(empty);
        return;
    }

    nudgeState.nudges.forEach(nudge => {
        const card = createNudgeCard(nudge);
        body.appendChild(card);
    });
}

/**
 * Create a nudge card element
 * @param {Object} nudge - Nudge data
 * @returns {HTMLElement} Nudge card
 */
function createNudgeCard(nudge) {
    const card = document.createElement('div');
    card.className = `nudge-card nudge-priority-${nudge.priority}`;
    card.setAttribute('data-nudge-id', nudge.id);

    // Icon and type
    const header = document.createElement('div');
    header.className = 'nudge-card-header';

    const icon = document.createElement('span');
    icon.className = 'nudge-icon';
    icon.textContent = NUDGE_ICONS[nudge.nudge_type] || '📌';
    icon.style.color = NUDGE_COLORS[nudge.nudge_type] || '#607D8B';
    header.appendChild(icon);

    const typeLabel = document.createElement('span');
    typeLabel.className = 'nudge-type';
    typeLabel.textContent = formatNudgeType(nudge.nudge_type);
    header.appendChild(typeLabel);

    const priorityBadge = document.createElement('span');
    priorityBadge.className = `nudge-priority-badge nudge-priority-${nudge.priority}`;
    priorityBadge.textContent = nudge.priority;
    header.appendChild(priorityBadge);

    card.appendChild(header);

    // Title
    const title = document.createElement('div');
    title.className = 'nudge-title';
    title.textContent = nudge.title;
    card.appendChild(title);

    // Message
    const message = document.createElement('div');
    message.className = 'nudge-message';
    message.textContent = nudge.message;
    card.appendChild(message);

    // Timestamp
    const timestamp = document.createElement('div');
    timestamp.className = 'nudge-timestamp';
    timestamp.textContent = formatTimestamp(nudge.created_at);
    card.appendChild(timestamp);

    // Actions
    const actions = document.createElement('div');
    actions.className = 'nudge-actions';

    // View/Action button (if has related item)
    if (nudge.related_id) {
        const viewBtn = document.createElement('button');
        viewBtn.className = 'nudge-action-btn nudge-view-btn';
        viewBtn.textContent = 'View';
        viewBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleNudgeAction(nudge);
        });
        actions.appendChild(viewBtn);
    }

    // Snooze button
    const snoozeBtn = document.createElement('button');
    snoozeBtn.className = 'nudge-action-btn nudge-snooze-btn';
    snoozeBtn.textContent = '💤 Snooze';
    snoozeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        snoozeNudge(nudge.id);
    });
    actions.appendChild(snoozeBtn);

    // Dismiss button
    const dismissBtn = document.createElement('button');
    dismissBtn.className = 'nudge-action-btn nudge-dismiss-btn';
    dismissBtn.textContent = '✕';
    dismissBtn.title = 'Dismiss';
    dismissBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dismissNudge(nudge.id);
    });
    actions.appendChild(dismissBtn);

    card.appendChild(actions);

    // Click handler for whole card
    card.addEventListener('click', () => handleNudgeAction(nudge));

    return card;
}

/**
 * Format nudge type for display
 * @param {string} type - Raw nudge type
 * @returns {string} Formatted display text
 */
function formatNudgeType(type) {
    const formats = {
        new_learning: 'New Learning',
        stale_knowledge: 'Stale Knowledge',
        low_confidence: 'Needs Review',
        correction_suggested: 'Suggested Edit',
        review_reminder: 'Review Reminder',
        insight_available: 'New Insight'
    };
    return formats[type] || type.replace(/_/g, ' ');
}

/**
 * Format timestamp for display
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Human-readable time
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '';

    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

/**
 * Fetch nudges from API
 */
async function fetchNudges() {
    try {
        const response = await fetch(`${API_BASE}/api/nudges?limit=20`);
        if (!response.ok) throw new Error('Failed to fetch nudges');

        const nudges = await response.json();
        nudgeState.nudges = nudges;

        updateNudgeBadge();
        if (nudgeState.isOpen) {
            renderNudges();
        }

    } catch (error) {
        console.error('Failed to fetch nudges:', error);
    }
}

/**
 * Update badge count
 */
function updateNudgeBadge() {
    const badge = document.getElementById('nudge-badge');
    if (!badge) return;

    const count = nudgeState.nudges.length;

    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count.toString();
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

/**
 * Toggle nudge sidebar visibility
 */
function toggleNudgeSidebar() {
    if (nudgeState.isOpen) {
        closeNudgeSidebar();
    } else {
        openNudgeSidebar();
    }
}

/**
 * Open nudge sidebar
 */
function openNudgeSidebar() {
    const sidebar = document.getElementById('nudge-sidebar');
    if (sidebar) {
        sidebar.classList.remove('hidden');
        nudgeState.isOpen = true;
        renderNudges();
    }
}

/**
 * Close nudge sidebar
 */
function closeNudgeSidebar() {
    const sidebar = document.getElementById('nudge-sidebar');
    if (sidebar) {
        sidebar.classList.add('hidden');
        nudgeState.isOpen = false;
    }
}

/**
 * Handle nudge action (click/view)
 * @param {Object} nudge - Nudge data
 */
function handleNudgeAction(nudge) {
    console.log('Nudge action:', nudge);

    // Emit event for main app to handle navigation
    const event = new CustomEvent('nudge-action', {
        detail: {
            nudge_type: nudge.nudge_type,
            related_id: nudge.related_id,
            nudge_id: nudge.id
        }
    });
    document.dispatchEvent(event);

    // Close sidebar
    closeNudgeSidebar();
}

/**
 * Snooze a nudge
 * @param {string} nudgeId - Nudge ID
 * @param {number} minutes - Snooze duration (default 60)
 */
async function snoozeNudge(nudgeId, minutes = 60) {
    try {
        const response = await fetch(`${API_BASE}/api/nudges/snooze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nudge_id: nudgeId,
                duration_minutes: minutes
            })
        });

        if (response.ok) {
            // Remove from local state
            nudgeState.nudges = nudgeState.nudges.filter(n => n.id !== nudgeId);
            updateNudgeBadge();
            renderNudges();

            showNudgeToast(`Snoozed for ${minutes} minutes`);
        }

    } catch (error) {
        console.error('Snooze error:', error);
        showNudgeToast('Failed to snooze', 'error');
    }
}

/**
 * Dismiss a nudge
 * @param {string} nudgeId - Nudge ID
 */
async function dismissNudge(nudgeId) {
    try {
        const response = await fetch(`${API_BASE}/api/nudges/dismiss`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nudge_id: nudgeId })
        });

        if (response.ok) {
            // Remove from local state
            nudgeState.nudges = nudgeState.nudges.filter(n => n.id !== nudgeId);
            updateNudgeBadge();
            renderNudges();
        }

    } catch (error) {
        console.error('Dismiss error:', error);
        showNudgeToast('Failed to dismiss', 'error');
    }
}

/**
 * Clear all nudges
 */
async function clearAllNudges() {
    for (const nudge of nudgeState.nudges) {
        await dismissNudge(nudge.id);
    }
}

/**
 * Show toast notification
 * @param {string} message - Toast message
 * @param {string} type - 'success' or 'error'
 */
function showNudgeToast(message, type = 'success') {
    let toast = document.getElementById('nudge-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'nudge-toast';
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.className = `nudge-toast nudge-toast-${type}`;

    setTimeout(() => {
        toast.className = 'nudge-toast hidden';
    }, 3000);
}

/**
 * Start polling for new nudges
 * @param {number} intervalMs - Poll interval in milliseconds
 */
function startNudgePolling(intervalMs = 60000) {
    // Initial fetch
    fetchNudges();

    // Set up polling
    if (nudgeState.pollInterval) {
        clearInterval(nudgeState.pollInterval);
    }
    nudgeState.pollInterval = setInterval(fetchNudges, intervalMs);

    console.log(`Nudge polling started (every ${intervalMs / 1000}s)`);
}

/**
 * Stop polling
 */
function stopNudgePolling() {
    if (nudgeState.pollInterval) {
        clearInterval(nudgeState.pollInterval);
        nudgeState.pollInterval = null;
    }
}

/**
 * Initialize nudge sidebar
 * Call this on app startup
 */
function initNudgeSidebar() {
    // Create sidebar if not exists
    if (!document.getElementById('nudge-sidebar')) {
        const sidebar = createNudgeSidebar();
        document.body.appendChild(sidebar);
    }

    // Create toggle button if not exists
    if (!document.getElementById('nudge-toggle-btn')) {
        const btn = createNudgeToggleButton();
        // Add to header - find the user badge area or chat header
        const header = document.querySelector('.header-user-badge') ||
                      document.querySelector('#chat-header') ||
                      document.querySelector('.chat-header') ||
                      document.body;
        // Insert before logout button if in user badge, otherwise append
        const logoutBtn = header.querySelector('#logout-btn');
        if (logoutBtn) {
            header.insertBefore(btn, logoutBtn);
        } else {
            header.appendChild(btn);
        }
    }

    // Start polling
    startNudgePolling(60000); // Every 60 seconds

    console.log('Nudge sidebar initialized');
}

// Export functions (CommonJS for Electron)
module.exports = {
    initNudgeSidebar,
    openNudgeSidebar,
    closeNudgeSidebar,
    fetchNudges,
    startNudgePolling,
    stopNudgePolling
};
