/**
 * Message Rendering Component
 *
 * Week 5 Day 2 Task 2: Production-Quality Message System
 * Sprint 3 Day 14: Edit Message capability
 *
 * Features:
 * - User and assistant message bubbles
 * - Rich metadata display (agent, cache status, cost, confidence)
 * - Feedback buttons (upvote/downvote)
 * - Thinking steps visualization (expandable)
 * - Edit button for user messages (Sprint 3 Day 14)
 * - Security: No innerHTML, all DOM manipulation via createElement
 *
 * Security Note:
 * This component uses ONLY textContent and createElement to prevent XSS attacks.
 * Never use innerHTML with user-generated content.
 */

// Callback for edit message
let editMessageCallback = null;

/**
 * Create a complete message bubble with all metadata
 *
 * @param {Object} message - Message object
 * @param {string} message.id - Unique message ID
 * @param {string} message.role - 'user' or 'assistant'
 * @param {string} message.content - Message text content
 * @param {Object} message.metadata - Metadata for assistant messages
 * @param {string} message.timestamp - ISO timestamp
 * @returns {HTMLElement} Complete message bubble element
 */
function createMessageBubble(message) {
    const bubble = document.createElement('div');
    bubble.className = `message message-${message.role}`;
    bubble.setAttribute('data-message-id', message.id);

    // Role indicator with actions container
    const roleContainer = document.createElement('div');
    roleContainer.className = 'message-role-container';

    const roleLabel = document.createElement('div');
    roleLabel.className = 'message-role';
    roleLabel.textContent = message.role === 'user' ? 'You' : 'Assistant';
    roleContainer.appendChild(roleLabel);

    // Edit button for user messages (Sprint 3 Day 14)
    if (message.role === 'user') {
        const editBtn = document.createElement('button');
        editBtn.className = 'message-edit-btn';
        editBtn.title = 'Edit message';
        editBtn.textContent = '✏️';
        editBtn.setAttribute('data-message-id', message.id);
        roleContainer.appendChild(editBtn);
    }

    bubble.appendChild(roleContainer);

    // Content wrapper (for edit mode)
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'message-content-wrapper';

    // Content (sanitized - textContent only)
    const content = document.createElement('div');
    content.className = 'message-content';
    content.textContent = message.content; // Safe: textContent, not innerHTML
    contentWrapper.appendChild(content);

    // Edit textarea (hidden by default) - Sprint 3 Day 14
    if (message.role === 'user') {
        const editContainer = document.createElement('div');
        editContainer.className = 'message-edit-container hidden';

        const editTextarea = document.createElement('textarea');
        editTextarea.className = 'message-edit-textarea';
        editTextarea.value = message.content;
        editTextarea.rows = 3;
        editContainer.appendChild(editTextarea);

        const editActions = document.createElement('div');
        editActions.className = 'message-edit-actions';

        const saveBtn = document.createElement('button');
        saveBtn.className = 'edit-save-btn';
        saveBtn.textContent = 'Save & Resend';
        saveBtn.title = 'Save changes and regenerate response';
        editActions.appendChild(saveBtn);

        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'edit-cancel-btn';
        cancelBtn.textContent = 'Cancel';
        editActions.appendChild(cancelBtn);

        editContainer.appendChild(editActions);
        contentWrapper.appendChild(editContainer);

        // Setup edit event handlers
        setupEditHandlers(bubble, content, editContainer, editTextarea, message);
    }

    bubble.appendChild(contentWrapper);

    // Metadata (for assistant messages only)
    if (message.role === 'assistant' && message.metadata) {
        const metadataEl = createMetadataDisplay(message.metadata);
        bubble.appendChild(metadataEl);

        // Thinking steps (if available)
        if (message.metadata.thinking_steps && message.metadata.thinking_steps.length > 0) {
            const thinkingEl = createThinkingSteps(message.metadata.thinking_steps);
            bubble.appendChild(thinkingEl);
        }
    }

    // Feedback buttons (for assistant messages)
    if (message.role === 'assistant') {
        const feedbackEl = createFeedbackButtons(message.id);
        bubble.appendChild(feedbackEl);
    }

    // Timestamp
    const timestampEl = document.createElement('div');
    timestampEl.className = 'message-timestamp';
    timestampEl.textContent = formatTimestamp(message.timestamp);
    bubble.appendChild(timestampEl);

    return bubble;
}

/**
 * Setup edit handlers for a user message
 *
 * Sprint 3 Day 14: Edit Message capability
 *
 * @param {HTMLElement} bubble - Message bubble element
 * @param {HTMLElement} content - Content display element
 * @param {HTMLElement} editContainer - Edit container element
 * @param {HTMLTextAreaElement} editTextarea - Edit textarea element
 * @param {Object} message - Original message object
 */
function setupEditHandlers(bubble, content, editContainer, editTextarea, message) {
    const editBtn = bubble.querySelector('.message-edit-btn');
    const saveBtn = editContainer.querySelector('.edit-save-btn');
    const cancelBtn = editContainer.querySelector('.edit-cancel-btn');

    // Enter edit mode
    editBtn.addEventListener('click', () => {
        content.classList.add('hidden');
        editContainer.classList.remove('hidden');
        editTextarea.value = content.textContent;
        editTextarea.focus();
        bubble.classList.add('editing');
    });

    // Cancel edit
    cancelBtn.addEventListener('click', () => {
        content.classList.remove('hidden');
        editContainer.classList.add('hidden');
        editTextarea.value = content.textContent;
        bubble.classList.remove('editing');
    });

    // Save and resend
    saveBtn.addEventListener('click', () => {
        const newContent = editTextarea.value.trim();
        if (newContent && newContent !== content.textContent) {
            content.textContent = newContent;

            // Call the edit callback
            if (editMessageCallback) {
                editMessageCallback(message.id, newContent);
            }
        }

        content.classList.remove('hidden');
        editContainer.classList.add('hidden');
        bubble.classList.remove('editing');
    });

    // Keyboard shortcuts
    editTextarea.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + Enter to save
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            saveBtn.click();
        }
        // Escape to cancel
        if (e.key === 'Escape') {
            cancelBtn.click();
        }
    });
}

/**
 * Set the callback for message edits
 *
 * Sprint 3 Day 14: Edit Message capability
 *
 * @param {Function} callback - Callback(messageId, newContent)
 */
function setEditMessageCallback(callback) {
    editMessageCallback = callback;
}

/**
 * Create metadata display with badges and stats
 *
 * @param {Object} metadata - Message metadata
 * @returns {HTMLElement} Metadata container
 */
function createMetadataDisplay(metadata) {
    const container = document.createElement('div');
    container.className = 'message-metadata';

    // Agent badge
    if (metadata.agent) {
        const badge = document.createElement('span');
        badge.className = `badge badge-agent badge-${metadata.agent.toLowerCase()}`;
        badge.textContent = formatAgentName(metadata.agent);
        container.appendChild(badge);
    }

    // Cache status badge
    if (metadata.from_cache) {
        const badge = document.createElement('span');
        badge.className = 'badge badge-cache';
        badge.textContent = '⚡ Cached';
        badge.title = 'Response served from cache - instant and free!';
        container.appendChild(badge);
    }

    // Cost display
    if (metadata.cost !== undefined && metadata.cost !== null) {
        const cost = document.createElement('span');
        cost.className = 'metadata-cost';
        cost.textContent = `$${metadata.cost.toFixed(4)}`;
        cost.title = `API cost: $${metadata.cost.toFixed(6)}`;
        container.appendChild(cost);
    }

    // Confidence score
    if (metadata.confidence !== undefined && metadata.confidence !== null) {
        const confidence = document.createElement('span');
        confidence.className = 'metadata-confidence';
        const confidencePercent = Math.round(metadata.confidence);
        confidence.textContent = `${confidencePercent}% confidence`;
        confidence.title = 'Confidence in routing decision';

        // Color code by confidence level
        if (confidencePercent >= 90) {
            confidence.style.color = '#4CAF50'; // Green
        } else if (confidencePercent >= 60) {
            confidence.style.color = '#FFC107'; // Amber
        } else {
            confidence.style.color = '#FF5722'; // Red
        }

        container.appendChild(confidence);
    }

    // Mode display (local/enriched)
    if (metadata.mode) {
        const mode = document.createElement('span');
        mode.className = 'metadata-mode';
        mode.textContent = metadata.mode.toUpperCase();
        mode.title = metadata.mode === 'local'
            ? 'Answered from local memory only'
            : 'Enriched with LLM processing';
        container.appendChild(mode);
    }

    // Cross-source badges (Unified Intelligence)
    if (metadata.sources && Array.isArray(metadata.sources) && metadata.sources.length > 0) {
        const sourcesContainer = document.createElement('div');
        sourcesContainer.className = 'sources-badges';

        const sourceIcons = {
            'email': '📧',
            'calendar': '📅',
            'financial': '💰',
            'chat': '💬',
            'memory': '🧠'
        };

        const sourceColors = {
            'email': 'source-email',
            'calendar': 'source-calendar',
            'financial': 'source-financial',
            'chat': 'source-chat',
            'memory': 'source-memory'
        };

        metadata.sources.forEach(source => {
            const sourceName = source.toLowerCase();
            const badge = document.createElement('span');
            badge.className = `badge badge-source ${sourceColors[sourceName] || 'source-default'}`;
            badge.textContent = `${sourceIcons[sourceName] || '📄'} ${source}`;
            badge.title = `Insights from ${source}`;
            sourcesContainer.appendChild(badge);
        });

        container.appendChild(sourcesContainer);
    }

    return container;
}

/**
 * Create thinking steps visualization (expandable) with input/output details
 *
 * @param {Array} steps - Array of thinking step objects
 * @returns {HTMLElement} Thinking steps container
 */
function createThinkingSteps(steps) {
    const container = document.createElement('div');
    container.className = 'thinking-steps';

    // Header (clickable to expand/collapse)
    const header = document.createElement('div');
    header.className = 'thinking-header';
    header.innerHTML = '🤔 '; // Safe: no user content

    const headerText = document.createElement('span');
    headerText.textContent = `View thinking process (${steps.length} steps)`;
    header.appendChild(headerText);

    const chevron = document.createElement('span');
    chevron.className = 'chevron';
    chevron.textContent = '▼';
    header.appendChild(chevron);

    container.appendChild(header);

    // Steps content (hidden by default)
    const stepsContent = document.createElement('div');
    stepsContent.className = 'thinking-content hidden';

    steps.forEach((step, index) => {
        const stepEl = document.createElement('div');

        // Special handling for knowledge_understanding step (WHY context)
        const isKnowledgeStep = step.step === 'knowledge_understanding';
        stepEl.className = isKnowledgeStep ? 'thinking-step knowledge-understanding-step' : 'thinking-step';

        // Step number with icon
        const stepNumber = document.createElement('span');
        stepNumber.className = 'step-number';
        stepNumber.textContent = isKnowledgeStep ? '🧠' : `${index + 1}.`;
        stepEl.appendChild(stepNumber);

        // Main step content wrapper
        const stepContent = document.createElement('div');
        stepContent.className = 'step-content';

        // For knowledge_understanding, show WHY context prominently
        if (isKnowledgeStep && step.details?.output) {
            const output = step.details.output;

            // WHY Context (primary display)
            const whySection = document.createElement('div');
            whySection.className = 'knowledge-why-section';

            const whyLabel = document.createElement('span');
            whyLabel.className = 'knowledge-label';
            whyLabel.textContent = 'Understanding WHY: ';
            whySection.appendChild(whyLabel);

            const whyText = document.createElement('span');
            whyText.className = 'knowledge-why-text';
            whyText.textContent = output.why_context || 'Context analyzed';
            whySection.appendChild(whyText);
            stepContent.appendChild(whySection);

            // Topic and domain info
            const metaSection = document.createElement('div');
            metaSection.className = 'knowledge-meta';

            if (output.topic_cluster) {
                const topicBadge = document.createElement('span');
                topicBadge.className = 'knowledge-badge topic';
                topicBadge.textContent = `📚 ${output.topic_cluster}`;
                metaSection.appendChild(topicBadge);
            }

            if (output.problem_domain) {
                const domainBadge = document.createElement('span');
                domainBadge.className = 'knowledge-badge domain';
                domainBadge.textContent = `🎯 ${output.problem_domain}`;
                metaSection.appendChild(domainBadge);
            }

            if (output.confidence) {
                const confBadge = document.createElement('span');
                confBadge.className = 'knowledge-badge confidence';
                confBadge.textContent = `${Math.round(output.confidence * 100)}% confident`;
                metaSection.appendChild(confBadge);
            }

            stepContent.appendChild(metaSection);

            // Stats row
            if (output.entities_found || output.facts_extracted) {
                const statsRow = document.createElement('div');
                statsRow.className = 'knowledge-stats';
                statsRow.textContent = `Extracted ${output.entities_found || 0} entities, ${output.facts_extracted || 0} facts`;
                stepContent.appendChild(statsRow);
            }
        } else {
            // Standard step text (message)
            const stepText = document.createElement('span');
            stepText.className = 'step-text';
            const text = step.message || step.step || step.description || (typeof step === 'string' ? step : JSON.stringify(step));
            stepText.textContent = text;
            stepContent.appendChild(stepText);
        }

        // Add details toggle if details exist
        if (step.details && (step.details.input || step.details.output)) {
            const detailsToggle = document.createElement('button');
            detailsToggle.className = 'details-toggle';
            detailsToggle.textContent = '📋';
            detailsToggle.title = 'View input/output details';
            stepContent.appendChild(detailsToggle);

            // Details panel (hidden by default)
            const detailsPanel = document.createElement('div');
            detailsPanel.className = 'step-details hidden';

            // Input section
            if (step.details.input) {
                const inputSection = document.createElement('div');
                inputSection.className = 'detail-section input';
                const inputLabel = document.createElement('span');
                inputLabel.className = 'detail-label';
                inputLabel.textContent = 'Input:';
                inputSection.appendChild(inputLabel);
                const inputValue = document.createElement('pre');
                inputValue.className = 'detail-value';
                inputValue.textContent = JSON.stringify(step.details.input, null, 2);
                inputSection.appendChild(inputValue);
                detailsPanel.appendChild(inputSection);
            }

            // Output section
            if (step.details.output) {
                const outputSection = document.createElement('div');
                outputSection.className = 'detail-section output';
                const outputLabel = document.createElement('span');
                outputLabel.className = 'detail-label';
                outputLabel.textContent = 'Output:';
                outputSection.appendChild(outputLabel);
                const outputValue = document.createElement('pre');
                outputValue.className = 'detail-value';
                outputValue.textContent = JSON.stringify(step.details.output, null, 2);
                outputSection.appendChild(outputValue);
                detailsPanel.appendChild(outputSection);
            }

            stepContent.appendChild(detailsPanel);

            // Toggle details on button click
            detailsToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                detailsPanel.classList.toggle('hidden');
                detailsToggle.textContent = detailsPanel.classList.contains('hidden') ? '📋' : '📋✓';
            });
        }

        stepEl.appendChild(stepContent);
        stepsContent.appendChild(stepEl);
    });

    container.appendChild(stepsContent);

    // Toggle functionality
    header.addEventListener('click', () => {
        stepsContent.classList.toggle('hidden');
        chevron.textContent = stepsContent.classList.contains('hidden') ? '▼' : '▲';
    });

    return container;
}

/**
 * Create feedback buttons (upvote/downvote)
 *
 * @param {string} messageId - Message ID
 * @returns {HTMLElement} Feedback buttons container
 */
function createFeedbackButtons(messageId) {
    const container = document.createElement('div');
    container.className = 'feedback-buttons';

    // Upvote button
    const upvote = document.createElement('button');
    upvote.className = 'feedback-btn upvote';
    upvote.setAttribute('data-message-id', messageId);
    upvote.setAttribute('data-feedback-type', 'upvote');
    upvote.textContent = '👍';
    upvote.title = 'Good response';
    container.appendChild(upvote);

    // Downvote button
    const downvote = document.createElement('button');
    downvote.className = 'feedback-btn downvote';
    downvote.setAttribute('data-message-id', messageId);
    downvote.setAttribute('data-feedback-type', 'downvote');
    downvote.textContent = '👎';
    downvote.title = 'Poor response';
    container.appendChild(downvote);

    return container;
}

/**
 * Setup feedback button listeners using event delegation
 *
 * @param {string} messageId - Message ID to listen for
 * @param {Function} callback - Callback(feedbackType)
 */
function setupFeedbackListeners(messageId, callback) {
    // Use event delegation - listen on document
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('feedback-btn')) {
            const btnMessageId = e.target.getAttribute('data-message-id');
            const feedbackType = e.target.getAttribute('data-feedback-type');

            if (btnMessageId === messageId) {
                e.target.classList.add('active');
                callback(feedbackType);
            }
        }
    });
}

/**
 * Format agent name for display
 *
 * @param {string} agent - Agent identifier
 * @returns {string} Formatted name
 */
function formatAgentName(agent) {
    const names = {
        'claude': 'Claude Sonnet 4',
        'claude_sonnet': 'Claude Sonnet 4',
        'gpt': 'GPT-5.1',
        'gpt4': 'GPT-5.1',
        'gpt-5.1': 'GPT-5.1',
        'chatgpt': 'GPT-5.1',
        'gemini': 'Gemini 3 Flash',
        'gemini_flash': 'Gemini 3 Flash',
        'gemini-3-flash-preview': 'Gemini 3 Flash',
        'ollama': 'Ollama Local',
        'auto': 'Auto'
    };

    return names[agent.toLowerCase()] || agent;
}

/**
 * Format timestamp to relative time
 *
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted time (e.g., "2 minutes ago")
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

// Export functions
module.exports = {
    createMessageBubble,
    createMetadataDisplay,
    createFeedbackButtons,
    setupFeedbackListeners,
    setEditMessageCallback,
    formatAgentName,
    formatTimestamp
};
