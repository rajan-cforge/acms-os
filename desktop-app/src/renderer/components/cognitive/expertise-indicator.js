/**
 * Expertise Indicator Component
 *
 * Cognitive Architecture Sprint 4-5 (Feb 2026)
 *
 * Displays the user's expertise level for current topic,
 * enabling schema-driven context calibration.
 *
 * Cognitive Principle: Schema-Driven Comprehension
 * - Experts process information differently than novices
 * - They have rich mental schemas organizing knowledge
 * - AI responses should calibrate to user's expertise
 *
 * Expertise Levels:
 * - 🌱 Beginner: Explain concepts, avoid jargon
 * - 🌿 Intermediate: Some assumed knowledge
 * - 🔬 Advanced: Technical depth, familiarity assumed
 * - 🏗️ Expert: Peer-level discussion
 *
 * Security: No innerHTML, DOM-safe operations only.
 */

// Expertise state
let expertiseState = {
    currentTopic: null,
    level: 'beginner',
    depth: 0,
    isLoading: false
};

// API base URL
const API_BASE = 'http://localhost:40080';

// Expertise level configurations
const EXPERTISE_LEVELS = {
    beginner: {
        emoji: '🌱',
        label: 'Beginner',
        color: '#4CAF50',
        description: 'New to this topic - explanations welcome'
    },
    intermediate: {
        emoji: '🌿',
        label: 'Intermediate',
        color: '#8BC34A',
        description: 'Familiar with basics - some assumed knowledge'
    },
    advanced: {
        emoji: '🔬',
        label: 'Advanced',
        color: '#2196F3',
        description: 'Deep knowledge - technical depth appreciated'
    },
    expert: {
        emoji: '🏗️',
        label: 'Expert',
        color: '#9C27B0',
        description: 'Peer-level expertise - challenge me!'
    }
};

// Depth thresholds (matching backend configuration)
const DEPTH_THRESHOLDS = {
    beginner: 3,
    intermediate: 10,
    advanced: 25,
    expert: 100
};

/**
 * Create the expertise indicator element
 * @returns {HTMLElement} Expertise indicator
 */
function createExpertiseIndicator() {
    const container = document.createElement('div');
    container.id = 'expertise-indicator';
    container.className = 'expertise-indicator';

    // Badge showing current level
    const badge = document.createElement('div');
    badge.id = 'expertise-badge';
    badge.className = 'expertise-badge';
    badge.title = 'Your expertise level for current topic';
    container.appendChild(badge);

    // Tooltip with details
    const tooltip = document.createElement('div');
    tooltip.id = 'expertise-tooltip';
    tooltip.className = 'expertise-tooltip hidden';
    container.appendChild(tooltip);

    // Show/hide tooltip on hover
    container.addEventListener('mouseenter', showExpertiseTooltip);
    container.addEventListener('mouseleave', hideExpertiseTooltip);

    return container;
}

/**
 * Update the expertise indicator display
 * @param {string} level - Expertise level
 * @param {string} topic - Current topic
 * @param {number} depth - Knowledge depth
 */
function updateExpertiseIndicator(level, topic, depth = 0) {
    const config = EXPERTISE_LEVELS[level] || EXPERTISE_LEVELS.beginner;

    expertiseState.level = level;
    expertiseState.currentTopic = topic;
    expertiseState.depth = depth;

    // Update badge
    const badge = document.getElementById('expertise-badge');
    if (badge) {
        // Clear existing content
        while (badge.firstChild) {
            badge.removeChild(badge.firstChild);
        }

        const emoji = document.createElement('span');
        emoji.className = 'expertise-emoji';
        emoji.textContent = config.emoji;
        badge.appendChild(emoji);

        const label = document.createElement('span');
        label.className = 'expertise-label';
        label.textContent = config.label;
        badge.appendChild(label);

        badge.style.borderColor = config.color;
        badge.style.color = config.color;
    }

    // Update tooltip
    updateExpertiseTooltip(config, topic, depth);
}

/**
 * Update tooltip content
 * @param {Object} config - Level configuration
 * @param {string} topic - Current topic
 * @param {number} depth - Knowledge depth
 */
function updateExpertiseTooltip(config, topic, depth) {
    const tooltip = document.getElementById('expertise-tooltip');
    if (!tooltip) return;

    // Clear existing content
    while (tooltip.firstChild) {
        tooltip.removeChild(tooltip.firstChild);
    }

    // Topic header
    const topicHeader = document.createElement('div');
    topicHeader.className = 'expertise-tooltip-topic';

    const topicLabel = document.createElement('span');
    topicLabel.textContent = 'Topic: ';
    topicHeader.appendChild(topicLabel);

    const topicValue = document.createElement('strong');
    topicValue.textContent = formatTopicName(topic || 'General');
    topicHeader.appendChild(topicValue);

    tooltip.appendChild(topicHeader);

    // Level indicator
    const levelSection = document.createElement('div');
    levelSection.className = 'expertise-tooltip-level';

    const levelEmoji = document.createElement('span');
    levelEmoji.className = 'expertise-tooltip-emoji';
    levelEmoji.textContent = config.emoji;
    levelSection.appendChild(levelEmoji);

    const levelText = document.createElement('div');
    levelText.className = 'expertise-tooltip-text';

    const levelName = document.createElement('strong');
    levelName.textContent = config.label;
    levelText.appendChild(levelName);

    const levelDesc = document.createElement('p');
    levelDesc.textContent = config.description;
    levelText.appendChild(levelDesc);

    levelSection.appendChild(levelText);
    tooltip.appendChild(levelSection);

    // Depth progress bar
    const progressSection = document.createElement('div');
    progressSection.className = 'expertise-tooltip-progress';

    const progressLabel = document.createElement('span');
    progressLabel.textContent = `Knowledge Depth: ${depth} items`;
    progressSection.appendChild(progressLabel);

    const progressBar = createProgressBar(depth);
    progressSection.appendChild(progressBar);

    tooltip.appendChild(progressSection);

    // Next level hint
    const nextLevel = getNextLevel(expertiseState.level);
    if (nextLevel) {
        const nextHint = document.createElement('div');
        nextHint.className = 'expertise-tooltip-hint';

        const nextConfig = EXPERTISE_LEVELS[nextLevel];
        const nextThreshold = DEPTH_THRESHOLDS[nextLevel];
        const remaining = nextThreshold - depth;

        nextHint.textContent = `${remaining} more items to reach ${nextConfig.emoji} ${nextConfig.label}`;
        tooltip.appendChild(nextHint);
    }
}

/**
 * Create a progress bar showing depth toward next level
 * @param {number} depth - Current depth
 * @returns {HTMLElement} Progress bar element
 */
function createProgressBar(depth) {
    const container = document.createElement('div');
    container.className = 'expertise-progress-container';

    const bar = document.createElement('div');
    bar.className = 'expertise-progress-bar';

    // Calculate progress toward next level
    const currentLevel = expertiseState.level;
    const currentThreshold = DEPTH_THRESHOLDS[currentLevel] || 0;
    const nextLevel = getNextLevel(currentLevel);
    const nextThreshold = nextLevel ? DEPTH_THRESHOLDS[nextLevel] : DEPTH_THRESHOLDS.expert;

    let progress;
    if (currentLevel === 'expert') {
        progress = 100;
    } else {
        progress = Math.min(100, ((depth - currentThreshold) / (nextThreshold - currentThreshold)) * 100);
    }

    const fill = document.createElement('div');
    fill.className = 'expertise-progress-fill';
    fill.style.width = `${progress}%`;
    bar.appendChild(fill);

    container.appendChild(bar);

    // Markers for thresholds
    const markers = document.createElement('div');
    markers.className = 'expertise-progress-markers';

    Object.entries(DEPTH_THRESHOLDS).forEach(([level, threshold]) => {
        const marker = document.createElement('span');
        marker.className = 'expertise-progress-marker';
        marker.textContent = EXPERTISE_LEVELS[level].emoji;
        marker.style.left = `${Math.min(95, (threshold / DEPTH_THRESHOLDS.expert) * 100)}%`;
        markers.appendChild(marker);
    });

    container.appendChild(markers);

    return container;
}

/**
 * Get the next expertise level
 * @param {string} currentLevel - Current level
 * @returns {string|null} Next level or null if at expert
 */
function getNextLevel(currentLevel) {
    const levels = ['beginner', 'intermediate', 'advanced', 'expert'];
    const currentIndex = levels.indexOf(currentLevel);
    return currentIndex < levels.length - 1 ? levels[currentIndex + 1] : null;
}

/**
 * Format topic name for display
 * @param {string} topic - Raw topic name
 * @returns {string} Formatted name
 */
function formatTopicName(topic) {
    return topic
        .replace(/-/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Show expertise tooltip
 */
function showExpertiseTooltip() {
    const tooltip = document.getElementById('expertise-tooltip');
    if (tooltip) {
        tooltip.classList.remove('hidden');
    }
}

/**
 * Hide expertise tooltip
 */
function hideExpertiseTooltip() {
    const tooltip = document.getElementById('expertise-tooltip');
    if (tooltip) {
        tooltip.classList.add('hidden');
    }
}

/**
 * Fetch expertise level for a topic
 * @param {string} topic - Topic to check
 */
async function fetchExpertiseLevel(topic) {
    expertiseState.isLoading = true;

    try {
        const response = await fetch(
            `${API_BASE}/api/schema-context?topic=${encodeURIComponent(topic)}`
        );
        if (!response.ok) throw new Error('Failed to fetch expertise');

        const data = await response.json();
        updateExpertiseIndicator(
            data.level || 'beginner',
            topic,
            data.depth || 0
        );

    } catch (error) {
        console.error('Failed to fetch expertise:', error);
        updateExpertiseIndicator('beginner', topic, 0);
    }

    expertiseState.isLoading = false;
}

/**
 * Initialize the expertise indicator
 */
function initExpertiseIndicator() {
    // Create indicator if not exists
    if (!document.getElementById('expertise-indicator')) {
        const indicator = createExpertiseIndicator();

        // Add to header or input area
        const header = document.querySelector('.chat-header') ||
                      document.querySelector('#chat-header') ||
                      document.querySelector('.header-user-badge');
        if (header) {
            header.appendChild(indicator);
        }
    }

    // Set default state
    updateExpertiseIndicator('beginner', null, 0);

    // Listen for topic changes
    document.addEventListener('topic-detected', (event) => {
        if (event.detail && event.detail.topic) {
            fetchExpertiseLevel(event.detail.topic);
        }
    });

    console.log('Expertise indicator initialized');
}

/**
 * Get CSS styles for the expertise indicator
 * @returns {string} CSS styles
 */
function getExpertiseStyles() {
    return `
        .expertise-indicator {
            position: relative;
            display: inline-flex;
            align-items: center;
            margin-left: 12px;
        }

        .expertise-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border: 1px solid;
            border-radius: 16px;
            font-size: 12px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .expertise-badge:hover {
            background: var(--bg-hover, rgba(255, 255, 255, 0.1));
        }

        .expertise-emoji {
            font-size: 14px;
        }

        .expertise-label {
            font-weight: 500;
        }

        .expertise-tooltip {
            position: absolute;
            top: 100%;
            right: 0;
            margin-top: 8px;
            background: var(--bg-secondary, #1a1a2e);
            border: 1px solid var(--border-color, #333);
            border-radius: 8px;
            padding: 16px;
            min-width: 280px;
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .expertise-tooltip.hidden {
            display: none;
        }

        .expertise-tooltip-topic {
            font-size: 12px;
            color: var(--text-secondary, #888);
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-color, #333);
        }

        .expertise-tooltip-level {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 16px;
        }

        .expertise-tooltip-emoji {
            font-size: 32px;
        }

        .expertise-tooltip-text {
            flex: 1;
        }

        .expertise-tooltip-text strong {
            font-size: 14px;
            color: var(--text-primary, #fff);
        }

        .expertise-tooltip-text p {
            font-size: 12px;
            color: var(--text-secondary, #888);
            margin: 4px 0 0 0;
        }

        .expertise-tooltip-progress {
            margin-bottom: 12px;
        }

        .expertise-tooltip-progress > span {
            font-size: 11px;
            color: var(--text-secondary, #888);
            display: block;
            margin-bottom: 6px;
        }

        .expertise-progress-container {
            position: relative;
        }

        .expertise-progress-bar {
            height: 6px;
            background: var(--bg-tertiary, #2a2a3e);
            border-radius: 3px;
            overflow: hidden;
        }

        .expertise-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A, #2196F3, #9C27B0);
            border-radius: 3px;
            transition: width 0.3s;
        }

        .expertise-progress-markers {
            position: relative;
            height: 20px;
            margin-top: 4px;
        }

        .expertise-progress-marker {
            position: absolute;
            font-size: 12px;
            transform: translateX(-50%);
        }

        .expertise-tooltip-hint {
            font-size: 11px;
            color: var(--text-secondary, #888);
            font-style: italic;
            padding-top: 8px;
            border-top: 1px solid var(--border-color, #333);
        }
    `;
}

// Export functions (CommonJS for Electron)
module.exports = {
    initExpertiseIndicator,
    updateExpertiseIndicator,
    fetchExpertiseLevel,
    createExpertiseIndicator,
    getExpertiseStyles,
    EXPERTISE_LEVELS
};
