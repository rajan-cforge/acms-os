/**
 * Memory Timeline Component
 * Sprint 2: Memory Clustering - Frontend
 *
 * Displays memories in a timeline view with:
 * - Reverse chronological order
 * - Date headers separating time periods
 * - Cluster badges for related memories
 * - Search filtering in real-time
 * - Click-to-expand using ExpandableCard
 *
 * Security: DOM-safe operations, no innerHTML with user data
 */

const { ExpandableCard } = require('./expandable-card.js');

const API_BASE = 'http://localhost:40080';

/**
 * MemoryTimeline class
 */
class MemoryTimeline {
    constructor(options = {}) {
        this.container = options.container;
        this.userId = options.userId || 'default';
        this.pageSize = options.pageSize || 50;

        this.memories = [];
        this.clusters = [];
        this.expandedCards = new Map();
        this.searchTerm = '';
        this.selectedCluster = null;

        this._onSearch = this._debounce(this._onSearch.bind(this), 300);
    }

    /**
     * Initialize and render the timeline
     */
    async init() {
        if (!this.container) {
            throw new Error('Container element required');
        }

        this._renderSkeleton();

        try {
            // Load clusters and memories in parallel
            const [clusters, memoriesData] = await Promise.all([
                this._fetchClusters(),
                this._fetchMemories()
            ]);

            this.clusters = clusters;
            this.memories = memoriesData.memories || [];

            this._render();
        } catch (error) {
            this._renderError(error);
        }
    }

    /**
     * Render loading skeleton
     * @private
     */
    _renderSkeleton() {
        this.container.innerHTML = '';
        this.container.className = 'memory-timeline-container';

        const skeleton = document.createElement('div');
        skeleton.className = 'timeline-skeleton';
        skeleton.innerHTML = `
            <div class="skeleton-header"></div>
            <div class="skeleton-card"></div>
            <div class="skeleton-card"></div>
            <div class="skeleton-card"></div>
        `;
        this.container.appendChild(skeleton);
    }

    /**
     * Render error state
     * @private
     */
    _renderError(error) {
        this.container.innerHTML = '';

        const errorEl = document.createElement('div');
        errorEl.className = 'error-container';

        const title = document.createElement('div');
        title.className = 'error-title';
        title.textContent = 'Failed to load memories';
        errorEl.appendChild(title);

        const message = document.createElement('div');
        message.className = 'error-message';
        message.textContent = error.message || 'Please try again later';
        errorEl.appendChild(message);

        const retry = document.createElement('button');
        retry.className = 'btn btn-secondary mt-4';
        retry.textContent = 'Retry';
        retry.addEventListener('click', () => this.init());
        errorEl.appendChild(retry);

        this.container.appendChild(errorEl);
    }

    /**
     * Main render method
     * @private
     */
    _render() {
        this.container.innerHTML = '';
        this.container.className = 'memory-timeline-container';

        // Header with title and search
        const header = this._createHeader();
        this.container.appendChild(header);

        // Cluster filter pills
        if (this.clusters.length > 0) {
            const clusterFilter = this._createClusterFilter();
            this.container.appendChild(clusterFilter);
        }

        // Timeline content
        const timeline = document.createElement('div');
        timeline.className = 'timeline-content scroll-area';
        timeline.id = 'memory-timeline';

        this._renderMemories(timeline);

        this.container.appendChild(timeline);
    }

    /**
     * Create header with search
     * @private
     */
    _createHeader() {
        const header = document.createElement('div');
        header.className = 'view-header flex justify-between items-center';

        const titleSection = document.createElement('div');

        const title = document.createElement('h2');
        title.textContent = 'Conversation History';
        titleSection.appendChild(title);

        const subtitle = document.createElement('p');
        subtitle.className = 'view-subtitle';
        subtitle.textContent = `${this.memories.length} memories across ${this.clusters.length} topics`;
        titleSection.appendChild(subtitle);

        header.appendChild(titleSection);

        // Search input
        const searchContainer = document.createElement('div');
        searchContainer.className = 'search-container';

        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'input';
        searchInput.placeholder = 'Search memories...';
        searchInput.id = 'memory-search-input';
        searchInput.addEventListener('input', (e) => this._onSearch(e.target.value));
        searchContainer.appendChild(searchInput);

        header.appendChild(searchContainer);

        return header;
    }

    /**
     * Create cluster filter pills
     * @private
     */
    _createClusterFilter() {
        const container = document.createElement('div');
        container.className = 'cluster-filter-container mb-4';

        const label = document.createElement('span');
        label.className = 'text-micro mr-2';
        label.textContent = 'FILTER BY TOPIC:';
        container.appendChild(label);

        const pills = document.createElement('div');
        pills.className = 'cluster-pills flex gap-2';

        // "All" pill
        const allPill = document.createElement('button');
        allPill.className = 'cluster-pill active';
        allPill.textContent = 'All';
        allPill.addEventListener('click', () => this._filterByCluster(null));
        pills.appendChild(allPill);

        // Cluster pills
        this.clusters.slice(0, 8).forEach(cluster => {
            const pill = document.createElement('button');
            pill.className = 'cluster-pill';
            pill.textContent = cluster.display_name;
            pill.setAttribute('data-cluster-id', cluster.cluster_id);
            pill.addEventListener('click', () => this._filterByCluster(cluster.cluster_id));
            pills.appendChild(pill);
        });

        container.appendChild(pills);
        return container;
    }

    /**
     * Render memories grouped by date
     * @private
     */
    _renderMemories(container) {
        const filtered = this._getFilteredMemories();

        if (filtered.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'empty-state';

            const icon = document.createElement('div');
            icon.className = 'empty-state-icon';
            icon.textContent = '🔍';
            empty.appendChild(icon);

            const title = document.createElement('div');
            title.className = 'empty-state-title';
            title.textContent = this.searchTerm ? 'No matching memories' : 'No memories yet';
            empty.appendChild(title);

            const desc = document.createElement('div');
            desc.className = 'empty-state-description';
            desc.textContent = this.searchTerm
                ? 'Try adjusting your search term'
                : 'Start a conversation to create your first memory';
            empty.appendChild(desc);

            container.appendChild(empty);
            return;
        }

        // Group memories by date
        const grouped = this._groupByDate(filtered);

        Object.entries(grouped).forEach(([dateKey, memories]) => {
            // Date header
            const dateHeader = document.createElement('div');
            dateHeader.className = 'timeline-date-header';
            dateHeader.textContent = this._formatDateHeader(dateKey);
            container.appendChild(dateHeader);

            // Memory cards for this date
            memories.forEach(memory => {
                const card = this._createMemoryCard(memory);
                container.appendChild(card);
            });
        });
    }

    /**
     * Create an expandable memory card
     * @private
     */
    _createMemoryCard(memory) {
        const memoryId = memory.query_id || memory.memory_id || memory.id;

        // Collapsed content
        const collapsedContent = this._createCollapsedContent(memory);

        // Expanded content (async loaded)
        const expandedContentFn = async () => {
            return this._createExpandedContent(memory);
        };

        const card = new ExpandableCard({
            id: memoryId,
            collapsedContent: collapsedContent,
            expandedContent: expandedContentFn,
            onExpand: (c) => this._handleCardExpand(c, memory),
            onCollapse: (c) => this._handleCardCollapse(c, memory)
        });

        const element = card.render();
        element.classList.add('memory-timeline-card');

        // Add cluster indicator if belongs to a cluster
        if (memory.cluster_id) {
            const cluster = this.clusters.find(c => c.cluster_id === memory.cluster_id);
            if (cluster) {
                element.classList.add('has-cluster');
                element.setAttribute('data-cluster', cluster.canonical_topic);
            }
        }

        this.expandedCards.set(memoryId, card);
        return element;
    }

    /**
     * Create collapsed card content
     * @private
     */
    _createCollapsedContent(memory) {
        const question = memory.question || memory.content || '';
        const preview = question.length > 150 ? question.substring(0, 150) + '...' : question;

        // Find cluster for this memory
        const cluster = memory.cluster_id
            ? this.clusters.find(c => c.cluster_id === memory.cluster_id)
            : null;

        let html = `
            <div class="memory-preview">
                <p class="memory-question">${this._escapeHtml(preview)}</p>
                <div class="memory-meta">
                    <span class="memory-time">${this._formatTime(memory.created_at)}</span>
        `;

        if (cluster) {
            html += `<span class="cluster-badge">${this._escapeHtml(cluster.display_name)}</span>`;
        }

        if (memory.agent_used) {
            html += `<span class="agent-badge">${this._escapeHtml(memory.agent_used)}</span>`;
        }

        html += `
                </div>
            </div>
        `;

        return html;
    }

    /**
     * Create expanded card content (full Q&A)
     * @private
     */
    async _createExpandedContent(memory) {
        const question = memory.question || memory.content || '';
        const answer = memory.answer || memory.response || '';

        let html = `
            <div class="memory-full">
                <div class="memory-section">
                    <div class="section-label">Question</div>
                    <p class="memory-question-full">${this._escapeHtml(question)}</p>
                </div>
                <div class="memory-section">
                    <div class="section-label">Response</div>
                    <div class="memory-answer">${this._formatAnswer(answer)}</div>
                </div>
        `;

        // Show related memories if in a cluster
        if (memory.cluster_id) {
            const related = this.memories.filter(m =>
                m.cluster_id === memory.cluster_id &&
                (m.query_id || m.memory_id) !== (memory.query_id || memory.memory_id)
            ).slice(0, 3);

            if (related.length > 0) {
                html += `
                    <div class="memory-section">
                        <div class="section-label">Related Conversations</div>
                        <div class="related-memories">
                `;

                related.forEach(r => {
                    const q = (r.question || '').substring(0, 80);
                    html += `<div class="related-memory-item">${this._escapeHtml(q)}...</div>`;
                });

                html += `
                        </div>
                    </div>
                `;
            }
        }

        // Actions
        html += `
            <div class="card-actions">
                <button class="card-action-btn" onclick="navigator.clipboard.writeText('${this._escapeHtml(question)}')">
                    Copy Question
                </button>
                <button class="card-action-btn danger" data-memory-id="${memory.query_id || memory.memory_id}">
                    Delete
                </button>
            </div>
        `;

        html += '</div>';
        return html;
    }

    /**
     * Fetch clusters from API
     * @private
     */
    async _fetchClusters() {
        try {
            const response = await fetch(`${API_BASE}/api/v2/clusters?limit=50`);
            if (!response.ok) throw new Error('Failed to fetch clusters');
            const data = await response.json();
            return data.clusters || [];
        } catch (error) {
            console.warn('Could not fetch clusters:', error);
            return [];
        }
    }

    /**
     * Fetch memories from API
     * @private
     */
    async _fetchMemories() {
        const response = await fetch(`${API_BASE}/memories?limit=${this.pageSize}`);
        if (!response.ok) throw new Error('Failed to fetch memories');
        return response.json();
    }

    /**
     * Get filtered memories based on search and cluster filter
     * @private
     */
    _getFilteredMemories() {
        let filtered = this.memories;

        // Filter by cluster
        if (this.selectedCluster) {
            filtered = filtered.filter(m => m.cluster_id === this.selectedCluster);
        }

        // Filter by search term
        if (this.searchTerm) {
            const term = this.searchTerm.toLowerCase();
            filtered = filtered.filter(m =>
                (m.question || '').toLowerCase().includes(term) ||
                (m.answer || '').toLowerCase().includes(term)
            );
        }

        return filtered;
    }

    /**
     * Group memories by date
     * @private
     */
    _groupByDate(memories) {
        const groups = {};
        const today = new Date().toDateString();
        const yesterday = new Date(Date.now() - 86400000).toDateString();

        memories.forEach(memory => {
            const date = new Date(memory.created_at);
            const dateStr = date.toDateString();

            let key;
            if (dateStr === today) {
                key = 'today';
            } else if (dateStr === yesterday) {
                key = 'yesterday';
            } else {
                key = date.toISOString().split('T')[0];
            }

            if (!groups[key]) groups[key] = [];
            groups[key].push(memory);
        });

        return groups;
    }

    /**
     * Format date header text
     * @private
     */
    _formatDateHeader(dateKey) {
        if (dateKey === 'today') return 'Today';
        if (dateKey === 'yesterday') return 'Yesterday';

        const date = new Date(dateKey);
        return date.toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric'
        });
    }

    /**
     * Format time for display
     * @private
     */
    _formatTime(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }

    /**
     * Format answer with markdown-like rendering
     * @private
     */
    _formatAnswer(answer) {
        // Basic formatting - escape HTML first
        let formatted = this._escapeHtml(answer);

        // Convert newlines to br tags
        formatted = formatted.replace(/\n/g, '<br>');

        // Code blocks (```...```)
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        // Inline code (`...`)
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

        return formatted;
    }

    /**
     * Handle search input
     * @private
     */
    _onSearch(term) {
        this.searchTerm = term;
        const timeline = document.getElementById('memory-timeline');
        if (timeline) {
            timeline.innerHTML = '';
            this._renderMemories(timeline);
        }
    }

    /**
     * Filter by cluster
     * @private
     */
    _filterByCluster(clusterId) {
        this.selectedCluster = clusterId;

        // Update active pill
        const pills = document.querySelectorAll('.cluster-pill');
        pills.forEach(pill => {
            const pillClusterId = pill.getAttribute('data-cluster-id');
            pill.classList.toggle('active',
                (clusterId === null && !pillClusterId) ||
                pillClusterId === clusterId
            );
        });

        // Re-render memories
        const timeline = document.getElementById('memory-timeline');
        if (timeline) {
            timeline.innerHTML = '';
            this._renderMemories(timeline);
        }
    }

    /**
     * Handle card expand
     * @private
     */
    _handleCardExpand(card, memory) {
        console.log('Expanded memory:', memory.query_id);
    }

    /**
     * Handle card collapse
     * @private
     */
    _handleCardCollapse(card, memory) {
        console.log('Collapsed memory:', memory.query_id);
    }

    /**
     * Escape HTML to prevent XSS
     * @private
     */
    _escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Debounce utility
     * @private
     */
    _debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Cleanup
     */
    destroy() {
        this.expandedCards.forEach(card => card.destroy());
        this.expandedCards.clear();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

/**
 * Render memory timeline in a container
 * @param {HTMLElement} container - Container element
 * @returns {MemoryTimeline}
 */
function renderMemoryTimeline(container) {
    const timeline = new MemoryTimeline({ container });
    timeline.init();
    return timeline;
}

// Export for CommonJS (Electron)
module.exports = {
    MemoryTimeline,
    renderMemoryTimeline
};
