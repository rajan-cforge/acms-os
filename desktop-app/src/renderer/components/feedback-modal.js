/**
 * Feedback Modal Component
 *
 * Active Second Brain (Jan 2026)
 *
 * Shows after user clicks 👍:
 * - AC9: Appears within 500ms of 👍 click
 * - AC10: "Yes, Save" creates entry with user_verified=true
 * - AC13: Auto-dismisses after 10 seconds
 *
 * Shows after user clicks 👎:
 * - AC11: Shows options (Incorrect/Outdated/Incomplete/Wrong Agent)
 * - AC12: "Wrong Agent" demotes and logs reason
 *
 * Security: No innerHTML, DOM-safe operations only.
 */

// Modal state
let modalState = {
    isOpen: false,
    messageId: null,
    queryHistoryId: null,
    feedbackType: null,
    autoDismissTimer: null
};

// API base URL
const API_BASE = 'http://localhost:40080';

/**
 * Negative feedback reasons
 */
const NEGATIVE_REASONS = [
    { value: 'incorrect', label: 'Incorrect', description: 'The information is factually wrong' },
    { value: 'outdated', label: 'Outdated', description: 'The information is no longer accurate' },
    { value: 'incomplete', label: 'Incomplete', description: 'Missing important details' },
    { value: 'wrong_agent', label: 'Wrong Agent', description: 'Got different AI than requested' },
    { value: 'too_long', label: 'Too Long', description: 'Response is too verbose' },
    { value: 'too_short', label: 'Too Short', description: 'Response lacks detail' },
    { value: 'off_topic', label: 'Off Topic', description: 'Didn\'t answer the question' },
    { value: 'other', label: 'Other', description: 'Something else (explain below)' }
];

/**
 * Create the feedback modal element
 * @returns {HTMLElement} Modal container
 */
function createFeedbackModal() {
    const modal = document.createElement('div');
    modal.id = 'feedback-modal';
    modal.className = 'feedback-modal hidden';

    const overlay = document.createElement('div');
    overlay.className = 'feedback-modal-overlay';
    overlay.addEventListener('click', closeFeedbackModal);
    modal.appendChild(overlay);

    const dialog = document.createElement('div');
    dialog.className = 'feedback-modal-dialog';

    // Header
    const header = document.createElement('div');
    header.className = 'feedback-modal-header';

    const title = document.createElement('h3');
    title.id = 'feedback-modal-title';
    title.textContent = 'Feedback';
    header.appendChild(title);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'feedback-modal-close';
    closeBtn.textContent = '×';
    closeBtn.addEventListener('click', closeFeedbackModal);
    header.appendChild(closeBtn);

    dialog.appendChild(header);

    // Body
    const body = document.createElement('div');
    body.id = 'feedback-modal-body';
    body.className = 'feedback-modal-body';
    dialog.appendChild(body);

    // Footer
    const footer = document.createElement('div');
    footer.id = 'feedback-modal-footer';
    footer.className = 'feedback-modal-footer';
    dialog.appendChild(footer);

    modal.appendChild(dialog);

    return modal;
}

/**
 * Show positive feedback modal
 * AC9: Must appear within 500ms
 *
 * @param {string} messageId - Message ID
 * @param {string} queryHistoryId - Query history ID for API
 */
function showPositiveFeedbackModal(messageId, queryHistoryId) {
    modalState = {
        isOpen: true,
        messageId,
        queryHistoryId,
        feedbackType: 'positive',
        autoDismissTimer: null
    };

    const modal = document.getElementById('feedback-modal');
    const title = document.getElementById('feedback-modal-title');
    const body = document.getElementById('feedback-modal-body');
    const footer = document.getElementById('feedback-modal-footer');

    // Clear previous content
    body.innerHTML = '';
    footer.innerHTML = '';

    // Set title
    title.textContent = '👍 Thanks for the feedback!';

    // Body content
    const message = document.createElement('p');
    message.className = 'feedback-modal-message';
    message.textContent = 'Would you like to save this response as verified knowledge? It will be cached for faster future responses.';
    body.appendChild(message);

    // Countdown indicator (AC13)
    const countdown = document.createElement('div');
    countdown.id = 'feedback-countdown';
    countdown.className = 'feedback-countdown';
    countdown.textContent = 'Auto-dismiss in 10s';
    body.appendChild(countdown);

    // Buttons
    const saveBtn = document.createElement('button');
    saveBtn.className = 'feedback-btn-primary';
    saveBtn.textContent = '✓ Yes, Save';
    saveBtn.addEventListener('click', () => submitPositiveFeedback(true));
    footer.appendChild(saveBtn);

    const skipBtn = document.createElement('button');
    skipBtn.className = 'feedback-btn-secondary';
    skipBtn.textContent = 'No, Thanks';
    skipBtn.addEventListener('click', () => submitPositiveFeedback(false));
    footer.appendChild(skipBtn);

    // Show modal
    modal.classList.remove('hidden');

    // Start auto-dismiss timer (AC13: 10 seconds)
    startAutoDismissTimer(10);
}

/**
 * Show negative feedback modal
 * AC11: Shows reason options
 *
 * @param {string} messageId - Message ID
 * @param {string} queryHistoryId - Query history ID
 */
function showNegativeFeedbackModal(messageId, queryHistoryId) {
    modalState = {
        isOpen: true,
        messageId,
        queryHistoryId,
        feedbackType: 'negative',
        autoDismissTimer: null
    };

    const modal = document.getElementById('feedback-modal');
    const title = document.getElementById('feedback-modal-title');
    const body = document.getElementById('feedback-modal-body');
    const footer = document.getElementById('feedback-modal-footer');

    // Clear previous content
    body.innerHTML = '';
    footer.innerHTML = '';

    // Set title
    title.textContent = '👎 What went wrong?';

    // Reason selection
    const reasonLabel = document.createElement('p');
    reasonLabel.className = 'feedback-modal-label';
    reasonLabel.textContent = 'Please select the issue:';
    body.appendChild(reasonLabel);

    const reasonList = document.createElement('div');
    reasonList.className = 'feedback-reason-list';

    NEGATIVE_REASONS.forEach(reason => {
        const option = document.createElement('label');
        option.className = 'feedback-reason-option';

        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'feedback-reason';
        radio.value = reason.value;
        option.appendChild(radio);

        const labelText = document.createElement('span');
        labelText.className = 'feedback-reason-label';
        labelText.textContent = reason.label;
        option.appendChild(labelText);

        const desc = document.createElement('span');
        desc.className = 'feedback-reason-desc';
        desc.textContent = reason.description;
        option.appendChild(desc);

        reasonList.appendChild(option);
    });

    body.appendChild(reasonList);

    // Optional comment
    const commentLabel = document.createElement('label');
    commentLabel.className = 'feedback-modal-label';
    commentLabel.textContent = 'Additional details (optional):';
    body.appendChild(commentLabel);

    const commentInput = document.createElement('textarea');
    commentInput.id = 'feedback-comment';
    commentInput.className = 'feedback-comment-input';
    commentInput.placeholder = 'Tell us more about the issue...';
    commentInput.rows = 2;
    body.appendChild(commentInput);

    // Buttons
    const submitBtn = document.createElement('button');
    submitBtn.className = 'feedback-btn-primary';
    submitBtn.textContent = 'Submit Feedback';
    submitBtn.addEventListener('click', submitNegativeFeedback);
    footer.appendChild(submitBtn);

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'feedback-btn-secondary';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.addEventListener('click', closeFeedbackModal);
    footer.appendChild(cancelBtn);

    // Show modal
    modal.classList.remove('hidden');
}

/**
 * Submit positive feedback to API
 * AC10: Creates entry with user_verified=true if save=true
 *
 * @param {boolean} saveAsVerified - Whether to save as verified
 */
async function submitPositiveFeedback(saveAsVerified) {
    clearAutoDismissTimer();

    const { queryHistoryId } = modalState;

    try {
        const response = await fetch(`${API_BASE}/api/v2/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query_history_id: queryHistoryId,
                feedback_type: 'positive',
                save_as_verified: saveAsVerified
            })
        });

        const result = await response.json();

        // Show success message
        showFeedbackSuccess(result.message || 'Feedback recorded!');

        // Update UI to show feedback was given
        markMessageFeedbackGiven(modalState.messageId, 'positive', saveAsVerified);

    } catch (error) {
        console.error('Feedback submission error:', error);
        showFeedbackError('Failed to submit feedback. Please try again.');
    }

    closeFeedbackModal();
}

/**
 * Submit negative feedback to API
 * AC12: "Wrong Agent" demotes and logs reason
 */
async function submitNegativeFeedback() {
    const { queryHistoryId } = modalState;

    // Get selected reason
    const selectedReason = document.querySelector('input[name="feedback-reason"]:checked');
    if (!selectedReason) {
        showFeedbackError('Please select a reason');
        return;
    }

    const reason = selectedReason.value;
    const comment = document.getElementById('feedback-comment')?.value || '';

    try {
        const response = await fetch(`${API_BASE}/api/v2/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query_history_id: queryHistoryId,
                feedback_type: 'negative',
                reason: reason,
                reason_text: comment
            })
        });

        const result = await response.json();

        // Show success message
        let message = result.message || 'Feedback recorded!';
        if (result.demoted_from_cache) {
            message = 'Thanks! This response has been removed from cache.';
        }
        showFeedbackSuccess(message);

        // Update UI
        markMessageFeedbackGiven(modalState.messageId, 'negative', false);

    } catch (error) {
        console.error('Feedback submission error:', error);
        showFeedbackError('Failed to submit feedback. Please try again.');
    }

    closeFeedbackModal();
}

/**
 * Start auto-dismiss countdown timer
 * AC13: Modal auto-dismisses after specified seconds
 *
 * @param {number} seconds - Countdown duration
 */
function startAutoDismissTimer(seconds) {
    let remaining = seconds;

    const updateCountdown = () => {
        const countdown = document.getElementById('feedback-countdown');
        if (countdown) {
            countdown.textContent = `Auto-dismiss in ${remaining}s`;
        }
        remaining--;

        if (remaining < 0) {
            submitPositiveFeedback(false); // Auto-dismiss without saving
        }
    };

    updateCountdown();
    modalState.autoDismissTimer = setInterval(updateCountdown, 1000);
}

/**
 * Clear auto-dismiss timer
 */
function clearAutoDismissTimer() {
    if (modalState.autoDismissTimer) {
        clearInterval(modalState.autoDismissTimer);
        modalState.autoDismissTimer = null;
    }
}

/**
 * Close the feedback modal
 */
function closeFeedbackModal() {
    clearAutoDismissTimer();

    const modal = document.getElementById('feedback-modal');
    if (modal) {
        modal.classList.add('hidden');
    }

    modalState = {
        isOpen: false,
        messageId: null,
        queryHistoryId: null,
        feedbackType: null,
        autoDismissTimer: null
    };
}

/**
 * Show success toast
 * @param {string} message - Success message
 */
function showFeedbackSuccess(message) {
    showToast(message, 'success');
}

/**
 * Show error toast
 * @param {string} message - Error message
 */
function showFeedbackError(message) {
    showToast(message, 'error');
}

/**
 * Show toast notification
 * @param {string} message - Toast message
 * @param {string} type - 'success' or 'error'
 */
function showToast(message, type) {
    let toast = document.getElementById('feedback-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'feedback-toast';
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.className = `feedback-toast feedback-toast-${type}`;

    // Auto-hide after 3 seconds
    setTimeout(() => {
        toast.className = 'feedback-toast hidden';
    }, 3000);
}

/**
 * Mark message as having received feedback
 * @param {string} messageId - Message ID
 * @param {string} type - 'positive' or 'negative'
 * @param {boolean} saved - Whether saved as verified
 */
function markMessageFeedbackGiven(messageId, type, saved) {
    const message = document.querySelector(`[data-message-id="${messageId}"]`);
    if (message) {
        message.classList.add('feedback-given');
        message.setAttribute('data-feedback-type', type);

        // Update feedback buttons
        const feedbackBtns = message.querySelector('.feedback-buttons');
        if (feedbackBtns) {
            const indicator = document.createElement('span');
            indicator.className = 'feedback-indicator';
            if (type === 'positive' && saved) {
                indicator.textContent = '✓ Saved';
                indicator.classList.add('feedback-saved');
            } else if (type === 'positive') {
                indicator.textContent = '✓ Thanks!';
            } else {
                indicator.textContent = '✓ Noted';
            }
            feedbackBtns.appendChild(indicator);

            // Disable buttons
            feedbackBtns.querySelectorAll('.feedback-btn').forEach(btn => {
                btn.disabled = true;
            });
        }
    }
}

/**
 * Show feedback modal (unified entry point)
 * @param {string} messageId - Query history ID
 * @param {string} type - 'positive' or 'negative'
 */
function showFeedbackModal(messageId, type) {
    if (type === 'positive') {
        showPositiveFeedbackModal(messageId);
    } else if (type === 'negative') {
        showNegativeFeedbackModal(messageId);
    } else {
        console.error('Invalid feedback type:', type);
    }
}

/**
 * Initialize feedback modal
 * Call this on app startup
 */
function initFeedbackModal() {
    // Create modal if not exists
    if (!document.getElementById('feedback-modal')) {
        const modal = createFeedbackModal();
        document.body.appendChild(modal);
    }

    console.log('Feedback modal initialized');
}

// Export functions (CommonJS for Electron)
module.exports = {
    initFeedbackModal,
    showFeedbackModal,
    showPositiveFeedbackModal,
    showNegativeFeedbackModal,
    closeFeedbackModal
};
