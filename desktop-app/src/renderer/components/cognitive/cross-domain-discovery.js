/**
 * Cross-Domain Discovery Component
 *
 * Cognitive Architecture Sprint 5 (Feb 2026)
 *
 * Displays creative cross-domain discoveries from the
 * CreativeRecombinator. These are "aha!" moments where
 * the system found unexpected connections between
 * distant knowledge domains.
 *
 * Cognitive Principle: REM Sleep Creative Discovery
 * - During REM sleep, brain makes novel associations
 * - Distant memories combine to form insights
 * - Prefrontal cortex relaxation allows unusual connections
 *
 * Features:
 * - Insight cards with domain connections
 * - Visual domain distance indicators
 * - User actions: confirm, dismiss, explore
 * - Weekly digest integration
 *
 * Security: No innerHTML, DOM-safe operations only.
 */

// Discovery state
let discoveryState = {
    discoveries: [],
    isLoading: false,
    lastFetch: null
};

// API base URL
const API_BASE = 'http://localhost:40080';

// Discovery type configurations
const DISCOVERY_TYPES = {
    cross_domain_entity: {
        icon: '🔗',
        label: 'Cross-Domain Connection',
        color: '#9C27B0'  // Purple
    },
    structural_analogy: {
        icon: '🔄',
        label: 'Pattern Match',
        color: '#00BCD4'  // Cyan
    },
    bridging_query: {
        icon: '🌉',
        label: 'Bridging Query',
        color: '#FF9800'  // Orange
    }
};

// Domain icons for visual representation
const DOMAIN_ICONS = {
    'machine-learning': '🤖',
    'devops': '⚙️',
    'kubernetes': '☸️',
    'docker': '🐳',
    'python': '🐍',
    'databases': '🗄️',
    'cooking': '🍳',
    'chemistry': '🧪',
    'biology': '🧬',
    'neuroscience': '🧠',
    'music': '🎵',
    'physics': '⚛️',
    'economics': '📈',
    'default': '📚'
};

/**
 * Create the discovery panel container
 * @returns {HTMLElement} Discovery panel
 */
function createDiscoveryPanel() {
    const panel = document.createElement('div');
    panel.id = 'cross-domain-discovery-panel';
    panel.className = 'discovery-panel';

    // Header
    const header = document.createElement('div');
    header.className = 'discovery-panel-header';

    const title = document.createElement('h3');
    title.className = 'discovery-panel-title';
    title.textContent = '💡 Cross-Domain Discoveries';
    header.appendChild(title);

    const subtitle = document.createElement('p');
    subtitle.className = 'discovery-panel-subtitle';
    subtitle.textContent = 'Creative connections found across your knowledge domains';
    header.appendChild(subtitle);

    const refreshBtn = document.createElement('button');
    refreshBtn.className = 'discovery-refresh-btn';
    refreshBtn.textContent = '🔄 Refresh';
    refreshBtn.addEventListener('click', fetchDiscoveries);
    header.appendChild(refreshBtn);

    panel.appendChild(header);

    // Body
    const body = document.createElement('div');
    body.id = 'discovery-panel-body';
    body.className = 'discovery-panel-body';
    panel.appendChild(body);

    return panel;
}

/**
 * Create a discovery card
 * @param {Object} discovery - Discovery data
 * @returns {HTMLElement} Discovery card
 */
function createDiscoveryCard(discovery) {
    const card = document.createElement('div');
    card.className = 'discovery-card';
    card.setAttribute('data-discovery-id', discovery.id || 'unknown');

    const type = discovery.discovery_type || discovery.type || 'cross_domain_entity';
    const typeConfig = DISCOVERY_TYPES[type] || DISCOVERY_TYPES.cross_domain_entity;

    // Card header with type badge
    const cardHeader = document.createElement('div');
    cardHeader.className = 'discovery-card-header';

    const typeBadge = document.createElement('span');
    typeBadge.className = 'discovery-type-badge';
    typeBadge.textContent = `${typeConfig.icon} ${typeConfig.label}`;
    typeBadge.style.borderColor = typeConfig.color;
    typeBadge.style.color = typeConfig.color;
    cardHeader.appendChild(typeBadge);

    // Novelty score
    if (discovery.novelty !== undefined) {
        const noveltyBadge = document.createElement('span');
        noveltyBadge.className = 'discovery-novelty-badge';
        noveltyBadge.textContent = `✨ ${Math.round(discovery.novelty * 100)}% novel`;
        cardHeader.appendChild(noveltyBadge);
    }

    card.appendChild(cardHeader);

    // Domain connection visualization
    const domains = discovery.domains || discovery.topics || [];
    if (domains.length >= 2) {
        const domainViz = createDomainVisualization(domains, discovery.distance);
        card.appendChild(domainViz);
    }

    // Entity or pattern
    if (discovery.entity) {
        const entitySection = document.createElement('div');
        entitySection.className = 'discovery-entity-section';

        const entityLabel = document.createElement('span');
        entityLabel.className = 'discovery-entity-label';
        entityLabel.textContent = 'Shared Concept:';
        entitySection.appendChild(entityLabel);

        const entityValue = document.createElement('span');
        entityValue.className = 'discovery-entity-value';
        entityValue.textContent = discovery.entity;
        entitySection.appendChild(entityValue);

        card.appendChild(entitySection);
    }

    // Insight text
    const insightText = discovery.insight_text || discovery.description || '';
    if (insightText) {
        const insight = document.createElement('p');
        insight.className = 'discovery-insight-text';
        insight.textContent = insightText;
        card.appendChild(insight);
    }

    // Actions
    const actions = document.createElement('div');
    actions.className = 'discovery-actions';

    const exploreBtn = document.createElement('button');
    exploreBtn.className = 'discovery-action-btn discovery-explore-btn';
    exploreBtn.textContent = '🔍 Explore';
    exploreBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        exploreDiscovery(discovery);
    });
    actions.appendChild(exploreBtn);

    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'discovery-action-btn discovery-confirm-btn';
    confirmBtn.textContent = '✓ Interesting';
    confirmBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        confirmDiscovery(discovery);
    });
    actions.appendChild(confirmBtn);

    const dismissBtn = document.createElement('button');
    dismissBtn.className = 'discovery-action-btn discovery-dismiss-btn';
    dismissBtn.textContent = '✕';
    dismissBtn.title = 'Not useful';
    dismissBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dismissDiscovery(discovery);
    });
    actions.appendChild(dismissBtn);

    card.appendChild(actions);

    return card;
}

/**
 * Create domain connection visualization
 * @param {string[]} domains - List of domains
 * @param {number} distance - Semantic distance (0-1)
 * @returns {HTMLElement} Domain visualization
 */
function createDomainVisualization(domains, distance = 0.5) {
    const viz = document.createElement('div');
    viz.className = 'discovery-domain-viz';

    // First domain
    const domain1 = document.createElement('div');
    domain1.className = 'discovery-domain-node';
    const icon1 = DOMAIN_ICONS[domains[0]] || DOMAIN_ICONS.default;
    domain1.textContent = `${icon1} ${formatDomainName(domains[0])}`;
    viz.appendChild(domain1);

    // Connection line with distance indicator
    const connection = document.createElement('div');
    connection.className = 'discovery-domain-connection';

    const connectionLine = document.createElement('div');
    connectionLine.className = 'discovery-connection-line';
    // Width based on distance (wider = more distant = more creative)
    connectionLine.style.width = `${50 + distance * 100}px`;
    connection.appendChild(connectionLine);

    const distanceLabel = document.createElement('span');
    distanceLabel.className = 'discovery-distance-label';
    distanceLabel.textContent = distance >= 0.7 ? '🌟 Creative' :
                                distance >= 0.5 ? '✨ Novel' : '🔹 Related';
    connection.appendChild(distanceLabel);

    viz.appendChild(connection);

    // Second domain
    const domain2 = document.createElement('div');
    domain2.className = 'discovery-domain-node';
    const icon2 = DOMAIN_ICONS[domains[1]] || DOMAIN_ICONS.default;
    domain2.textContent = `${icon2} ${formatDomainName(domains[1])}`;
    viz.appendChild(domain2);

    // Additional domains if present
    if (domains.length > 2) {
        const more = document.createElement('span');
        more.className = 'discovery-more-domains';
        more.textContent = `+${domains.length - 2} more`;
        viz.appendChild(more);
    }

    return viz;
}

/**
 * Format domain name for display
 * @param {string} domain - Raw domain name
 * @returns {string} Formatted name
 */
function formatDomainName(domain) {
    return domain
        .replace(/-/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Render discoveries in the panel
 */
function renderDiscoveries() {
    const body = document.getElementById('discovery-panel-body');
    if (!body) return;

    // Clear existing
    while (body.firstChild) {
        body.removeChild(body.firstChild);
    }

    if (discoveryState.isLoading) {
        const loading = document.createElement('div');
        loading.className = 'discovery-loading';
        loading.textContent = '🧠 Searching for creative connections...';
        body.appendChild(loading);
        return;
    }

    if (discoveryState.discoveries.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'discovery-empty';

        const emptyIcon = document.createElement('span');
        emptyIcon.className = 'discovery-empty-icon';
        emptyIcon.textContent = '💭';
        empty.appendChild(emptyIcon);

        const emptyText = document.createElement('p');
        emptyText.textContent = 'No cross-domain discoveries yet.';
        empty.appendChild(emptyText);

        const emptyHint = document.createElement('p');
        emptyHint.className = 'discovery-empty-hint';
        emptyHint.textContent = 'Keep learning across different topics - discoveries appear when you build knowledge in multiple areas.';
        empty.appendChild(emptyHint);

        body.appendChild(empty);
        return;
    }

    // Render each discovery
    discoveryState.discoveries.forEach(discovery => {
        const card = createDiscoveryCard(discovery);
        body.appendChild(card);
    });
}

/**
 * Fetch discoveries from API
 */
async function fetchDiscoveries() {
    discoveryState.isLoading = true;
    renderDiscoveries();

    try {
        const response = await fetch(`${API_BASE}/api/discoveries?limit=10`);
        if (!response.ok) throw new Error('Failed to fetch discoveries');

        const data = await response.json();
        discoveryState.discoveries = data.discoveries || data || [];
        discoveryState.lastFetch = new Date();

    } catch (error) {
        console.error('Failed to fetch discoveries:', error);
        discoveryState.discoveries = [];
    }

    discoveryState.isLoading = false;
    renderDiscoveries();
}

/**
 * Explore a discovery - navigate to related content
 * @param {Object} discovery - Discovery data
 */
function exploreDiscovery(discovery) {
    console.log('Exploring discovery:', discovery);

    // Emit event for main app to handle navigation
    const event = new CustomEvent('discovery-explore', {
        detail: {
            discovery_type: discovery.discovery_type || discovery.type,
            entity: discovery.entity,
            domains: discovery.domains || discovery.topics,
            discovery_id: discovery.id
        }
    });
    document.dispatchEvent(event);

    // Could also search for the entity or topic
    if (discovery.entity) {
        const searchEvent = new CustomEvent('search-query', {
            detail: { query: discovery.entity }
        });
        document.dispatchEvent(searchEvent);
    }
}

/**
 * Confirm a discovery as useful
 * @param {Object} discovery - Discovery data
 */
async function confirmDiscovery(discovery) {
    try {
        const response = await fetch(`${API_BASE}/api/discoveries/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                discovery_id: discovery.id,
                feedback: 'useful'
            })
        });

        if (response.ok) {
            showDiscoveryToast('Marked as interesting! Similar insights will be prioritized.');

            // Visual feedback on card
            const card = document.querySelector(`[data-discovery-id="${discovery.id}"]`);
            if (card) {
                card.classList.add('discovery-confirmed');
            }
        }

    } catch (error) {
        console.error('Confirm error:', error);
    }
}

/**
 * Dismiss a discovery
 * @param {Object} discovery - Discovery data
 */
async function dismissDiscovery(discovery) {
    try {
        const response = await fetch(`${API_BASE}/api/discoveries/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                discovery_id: discovery.id,
                feedback: 'not_useful'
            })
        });

        if (response.ok) {
            // Remove from local state
            discoveryState.discoveries = discoveryState.discoveries.filter(
                d => d.id !== discovery.id
            );
            renderDiscoveries();
        }

    } catch (error) {
        console.error('Dismiss error:', error);
    }
}

/**
 * Show toast notification
 * @param {string} message - Toast message
 */
function showDiscoveryToast(message) {
    let toast = document.getElementById('discovery-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'discovery-toast';
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.className = 'discovery-toast';

    setTimeout(() => {
        toast.className = 'discovery-toast hidden';
    }, 3000);
}

/**
 * Initialize the discovery component
 */
function initCrossDomainDiscovery() {
    // Create panel if not exists
    if (!document.getElementById('cross-domain-discovery-panel')) {
        const panel = createDiscoveryPanel();

        // Find a place to insert it - after main content or in sidebar
        const mainContent = document.querySelector('.main-content') ||
                           document.querySelector('#app') ||
                           document.body;
        mainContent.appendChild(panel);
    }

    // Initial fetch
    fetchDiscoveries();

    console.log('Cross-domain discovery component initialized');
}

/**
 * Get CSS styles for the discovery component
 * @returns {string} CSS styles
 */
function getDiscoveryStyles() {
    return `
        .discovery-panel {
            background: var(--bg-secondary, #1a1a2e);
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }

        .discovery-panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }

        .discovery-panel-title {
            font-size: 18px;
            margin: 0;
            color: var(--text-primary, #fff);
        }

        .discovery-panel-subtitle {
            font-size: 12px;
            color: var(--text-secondary, #888);
            margin: 4px 0 0 0;
            width: 100%;
        }

        .discovery-refresh-btn {
            background: transparent;
            border: 1px solid var(--border-color, #333);
            color: var(--text-secondary, #888);
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
        }

        .discovery-refresh-btn:hover {
            background: var(--bg-hover, #2a2a3e);
        }

        .discovery-card {
            background: var(--bg-tertiary, #2a2a3e);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            border: 1px solid var(--border-color, #333);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .discovery-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .discovery-card.discovery-confirmed {
            border-color: #4CAF50;
            background: rgba(76, 175, 80, 0.1);
        }

        .discovery-card-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }

        .discovery-type-badge {
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid;
            background: transparent;
        }

        .discovery-novelty-badge {
            font-size: 11px;
            color: var(--text-secondary, #888);
            margin-left: auto;
        }

        .discovery-domain-viz {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin: 16px 0;
            padding: 12px;
            background: var(--bg-secondary, #1a1a2e);
            border-radius: 8px;
        }

        .discovery-domain-node {
            padding: 8px 12px;
            background: var(--bg-tertiary, #2a2a3e);
            border-radius: 6px;
            font-size: 13px;
            color: var(--text-primary, #fff);
        }

        .discovery-domain-connection {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
        }

        .discovery-connection-line {
            height: 2px;
            background: linear-gradient(90deg, #9C27B0, #00BCD4);
            border-radius: 1px;
        }

        .discovery-distance-label {
            font-size: 10px;
            color: var(--text-secondary, #888);
        }

        .discovery-more-domains {
            font-size: 11px;
            color: var(--text-secondary, #888);
        }

        .discovery-entity-section {
            margin: 12px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .discovery-entity-label {
            font-size: 11px;
            color: var(--text-secondary, #888);
        }

        .discovery-entity-value {
            font-size: 14px;
            font-weight: 600;
            color: #9C27B0;
        }

        .discovery-insight-text {
            font-size: 13px;
            color: var(--text-primary, #fff);
            line-height: 1.5;
            margin: 12px 0;
        }

        .discovery-actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border-color, #333);
        }

        .discovery-action-btn {
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            border: none;
            transition: background 0.2s;
        }

        .discovery-explore-btn {
            background: #9C27B0;
            color: white;
        }

        .discovery-explore-btn:hover {
            background: #7B1FA2;
        }

        .discovery-confirm-btn {
            background: transparent;
            border: 1px solid #4CAF50;
            color: #4CAF50;
        }

        .discovery-confirm-btn:hover {
            background: rgba(76, 175, 80, 0.1);
        }

        .discovery-dismiss-btn {
            background: transparent;
            color: var(--text-secondary, #888);
            margin-left: auto;
        }

        .discovery-dismiss-btn:hover {
            color: #f44336;
        }

        .discovery-loading,
        .discovery-empty {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-secondary, #888);
        }

        .discovery-empty-icon {
            font-size: 48px;
            display: block;
            margin-bottom: 16px;
        }

        .discovery-empty-hint {
            font-size: 12px;
            opacity: 0.7;
            margin-top: 8px;
        }

        .discovery-toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #4CAF50;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 1000;
            transition: opacity 0.3s;
        }

        .discovery-toast.hidden {
            opacity: 0;
            pointer-events: none;
        }
    `;
}

// Export functions (CommonJS for Electron)
module.exports = {
    initCrossDomainDiscovery,
    fetchDiscoveries,
    createDiscoveryPanel,
    createDiscoveryCard,
    getDiscoveryStyles,
    exploreDiscovery,
    confirmDiscovery,
    dismissDiscovery
};
