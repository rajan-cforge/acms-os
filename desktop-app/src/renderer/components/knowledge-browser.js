/**
 * Knowledge Browser Component
 * Sprint 3: Knowledge Consolidation - Frontend
 *
 * Displays consolidated knowledge with:
 * - Domain tree navigation (sidebar)
 * - Confidence visualization (dots + colors)
 * - Knowledge cards with expand/collapse
 * - Verify/edit/delete actions
 */

const { fetchWithAuth } = require('../api-client');
const { ExpandableCard } = require('./expandable-card');

class KnowledgeBrowser {
    constructor(container) {
        this.container = container;
        this.knowledge = [];
        this.domains = [];
        this.selectedDomain = null;
        this.searchQuery = '';
        this.filters = {
            verifiedOnly: false,
            needsReview: false,
            minConfidence: 0
        };
        this.stats = null;
    }

    async init() {
        this.render();
        await this.loadData();
    }

    render() {
        this.container.innerHTML = `
            <div class="knowledge-browser">
                <div class="knowledge-sidebar">
                    <div class="sidebar-header">
                        <h3>Domains</h3>
                    </div>
                    <div class="domain-tree" id="domainTree">
                        <div class="skeleton-loader">Loading domains...</div>
                    </div>
                    <div class="sidebar-stats" id="sidebarStats"></div>
                </div>
                <div class="knowledge-main">
                    <div class="knowledge-header">
                        <div class="knowledge-title">
                            <h2>Knowledge Base</h2>
                            <span class="knowledge-count" id="knowledgeCount">0 items</span>
                        </div>
                        <div class="knowledge-actions">
                            <div class="search-container">
                                <input
                                    type="text"
                                    class="input"
                                    id="knowledgeSearch"
                                    placeholder="Search knowledge..."
                                />
                            </div>
                        </div>
                    </div>
                    <div class="knowledge-filters" id="knowledgeFilters">
                        <label class="filter-checkbox">
                            <input type="checkbox" id="filterVerified" />
                            <span>Verified only</span>
                        </label>
                        <label class="filter-checkbox">
                            <input type="checkbox" id="filterReview" />
                            <span>Needs review</span>
                        </label>
                        <div class="confidence-filter">
                            <label>Min confidence:</label>
                            <input
                                type="range"
                                id="filterConfidence"
                                min="0"
                                max="100"
                                value="0"
                            />
                            <span id="confidenceValue">0%</span>
                        </div>
                    </div>
                    <div class="knowledge-list" id="knowledgeList">
                        <div class="skeleton-loader">
                            <div class="skeleton-card"></div>
                            <div class="skeleton-card"></div>
                            <div class="skeleton-card"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        // Search
        const searchInput = document.getElementById('knowledgeSearch');
        if (searchInput) {
            let debounceTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimeout);
                debounceTimeout = setTimeout(() => {
                    this.searchQuery = e.target.value;
                    this.loadKnowledge();
                }, 300);
            });
        }

        // Filters
        const verifiedCheckbox = document.getElementById('filterVerified');
        if (verifiedCheckbox) {
            verifiedCheckbox.addEventListener('change', (e) => {
                this.filters.verifiedOnly = e.target.checked;
                this.loadKnowledge();
            });
        }

        const reviewCheckbox = document.getElementById('filterReview');
        if (reviewCheckbox) {
            reviewCheckbox.addEventListener('change', (e) => {
                this.filters.needsReview = e.target.checked;
                this.loadKnowledge();
            });
        }

        const confidenceSlider = document.getElementById('filterConfidence');
        if (confidenceSlider) {
            confidenceSlider.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                document.getElementById('confidenceValue').textContent = `${value}%`;
                this.filters.minConfidence = value / 100;
            });
            confidenceSlider.addEventListener('change', () => {
                this.loadKnowledge();
            });
        }
    }

    async loadData() {
        await Promise.all([
            this.loadDomains(),
            this.loadKnowledge(),
            this.loadStats()
        ]);
    }

    async loadDomains() {
        try {
            // Use existing /knowledge/stats to get domains
            const response = await fetchWithAuth('/knowledge/stats');
            if (response.ok) {
                const stats = await response.json();
                // Convert top_domains to tree structure
                this.domains = (stats.top_domains || []).map(d => ({
                    domain: {
                        domain_id: d.domain,
                        name: d.domain,
                        display_name: d.domain.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                        knowledge_count: d.count,
                        icon: '📁',
                        color: '#2196F3'
                    },
                    children: []
                }));
                this.renderDomainTree();
            }
        } catch (error) {
            console.error('Failed to load domains:', error);
        }
    }

    async loadKnowledge() {
        try {
            const params = new URLSearchParams({ limit: '50' });
            if (this.selectedDomain) {
                params.set('domain', this.selectedDomain);
            }
            if (this.searchQuery) {
                params.set('search', this.searchQuery);
            }

            // Use existing /knowledge endpoint
            const response = await fetchWithAuth(`/knowledge?${params.toString()}`);
            if (response.ok) {
                const data = await response.json();
                // Map to expected format for renderKnowledgeCard
                this.knowledge = (data.knowledge || []).map(k => ({
                    knowledge_id: k.id,
                    canonical_content: k.answer_summary || k.canonical_query || 'No content',
                    canonical_query: k.canonical_query,
                    answer_summary: k.answer_summary,
                    domain_path: k.problem_domain || 'general',
                    topic_cluster: k.topic_cluster,
                    primary_intent: k.primary_intent,
                    effective_confidence: k.extraction_confidence || 0.7,
                    knowledge_type: 'fact',
                    source_count: 1,
                    is_verified: k.is_verified || false,
                    key_facts: k.key_facts || [],
                    created_at: k.created_at
                }));
                this.renderKnowledgeList();
                this.updateCount(data.total || this.knowledge.length);
            }
        } catch (error) {
            console.error('Failed to load knowledge:', error);
        }
    }

    async loadStats() {
        try {
            // Use existing /knowledge/stats endpoint
            const response = await fetchWithAuth('/knowledge/stats');
            if (response.ok) {
                const data = await response.json();
                this.stats = {
                    total: data.total_knowledge || 0,
                    verified: 0,  // Not tracked in old system
                    avg_confidence: 0.75,  // Default average
                    total_facts: data.total_facts || 0,
                    top_domains: data.top_domains || [],
                    top_topics: data.top_topics || []
                };
                this.renderStats();
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    renderDomainTree() {
        const container = document.getElementById('domainTree');
        if (!container) return;

        if (this.domains.length === 0) {
            container.innerHTML = '<div class="empty-state">No domains yet</div>';
            return;
        }

        container.innerHTML = this.renderDomainNodes(this.domains);
    }

    renderDomainNodes(nodes, level = 0) {
        return nodes.map(node => {
            const isSelected = this.selectedDomain === node.domain.name;
            const hasChildren = node.children && node.children.length > 0;

            return `
                <div class="domain-node" style="padding-left: ${level * 16}px">
                    <div
                        class="domain-item ${isSelected ? 'selected' : ''}"
                        data-domain="${node.domain.name}"
                        onclick="window.knowledgeBrowser.selectDomain('${node.domain.name}')"
                    >
                        <span class="domain-icon">${node.domain.icon || '📁'}</span>
                        <span class="domain-name">${node.domain.display_name}</span>
                        <span class="domain-count">${node.domain.knowledge_count}</span>
                    </div>
                    ${hasChildren ? `
                        <div class="domain-children">
                            ${this.renderDomainNodes(node.children, level + 1)}
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    }

    selectDomain(domain) {
        if (this.selectedDomain === domain) {
            this.selectedDomain = null;
        } else {
            this.selectedDomain = domain;
        }
        this.renderDomainTree();
        this.loadKnowledge();
    }

    renderKnowledgeList() {
        const container = document.getElementById('knowledgeList');
        if (!container) return;

        if (this.knowledge.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📚</div>
                    <div class="empty-text">No knowledge items found</div>
                    <div class="empty-hint">Knowledge is extracted from your conversations</div>
                </div>
            `;
            return;
        }

        container.innerHTML = this.knowledge.map(item => this.renderKnowledgeCard(item)).join('');
    }

    renderKnowledgeCard(item) {
        const { dots, color } = this.getConfidenceIndicator(item.effective_confidence);

        return `
            <div class="knowledge-card" data-id="${item.knowledge_id}">
                <div class="knowledge-card-header">
                    <div class="knowledge-type-badge ${item.knowledge_type || 'fact'}">
                        ${this.getTypeIcon(item.knowledge_type)} ${item.knowledge_type || 'fact'}
                    </div>
                    <div class="confidence-indicator" style="color: var(--color-${color})">
                        <span class="confidence-dots">${dots}</span>
                        <span class="confidence-value">${Math.round(item.effective_confidence * 100)}%</span>
                    </div>
                </div>
                <div class="knowledge-content">
                    ${this.escapeHtml(item.canonical_content)}
                </div>
                <div class="knowledge-card-footer">
                    <div class="knowledge-meta">
                        <span class="domain-tag" style="background: ${this.getDomainColor(item.domain_path)}20; color: ${this.getDomainColor(item.domain_path)}">
                            ${item.domain_path || 'personal'}
                        </span>
                        <span class="source-count">${item.source_count} source${item.source_count !== 1 ? 's' : ''}</span>
                        ${item.is_verified ? '<span class="verified-badge">✓ Verified</span>' : ''}
                    </div>
                    <div class="knowledge-actions">
                        ${!item.is_verified ? `
                            <button class="btn btn-sm btn-success" onclick="window.knowledgeBrowser.verifyKnowledge('${item.knowledge_id}')">
                                Verify
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-ghost" onclick="window.knowledgeBrowser.unverifyKnowledge('${item.knowledge_id}')">
                                Unverify
                            </button>
                        `}
                        <button class="btn btn-sm btn-ghost" onclick="window.knowledgeBrowser.showDetails('${item.knowledge_id}')">
                            Details
                        </button>
                        <button class="btn btn-sm btn-ghost btn-danger" onclick="window.knowledgeBrowser.deleteKnowledge('${item.knowledge_id}')">
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    getConfidenceIndicator(confidence) {
        if (confidence >= 0.8) {
            return { dots: '●●●●○', color: 'green' };
        } else if (confidence >= 0.6) {
            return { dots: '●●●○○', color: 'blue' };
        } else if (confidence >= 0.4) {
            return { dots: '●●○○○', color: 'yellow' };
        } else if (confidence >= 0.2) {
            return { dots: '●○○○○', color: 'orange' };
        } else {
            return { dots: '○○○○○', color: 'red' };
        }
    }

    getTypeIcon(type) {
        const icons = {
            fact: '📋',
            preference: '⭐',
            definition: '📖',
            procedure: '📝'
        };
        return icons[type] || '📋';
    }

    getDomainColor(domain) {
        const colors = {
            'technology': '#2196F3',
            'technology/programming': '#4CAF50',
            'technology/databases': '#FF9800',
            'technology/devops': '#9C27B0',
            'personal': '#E91E63',
            'personal/preferences': '#FFC107',
            'work': '#795548',
            'finance': '#4CAF50'
        };
        return colors[domain] || '#607D8B';
    }

    renderStats() {
        const container = document.getElementById('sidebarStats');
        if (!container || !this.stats) return;

        container.innerHTML = `
            <div class="stats-section">
                <div class="stat-item">
                    <span class="stat-value">${this.stats.total}</span>
                    <span class="stat-label">Total items</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${this.stats.verified}</span>
                    <span class="stat-label">Verified</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${Math.round(this.stats.avg_confidence * 100)}%</span>
                    <span class="stat-label">Avg confidence</span>
                </div>
            </div>
        `;
    }

    updateCount(total) {
        const countEl = document.getElementById('knowledgeCount');
        if (countEl) {
            countEl.textContent = `${total} item${total !== 1 ? 's' : ''}`;
        }
    }

    async verifyKnowledge(id) {
        try {
            const response = await fetchWithAuth(`/api/v2/knowledge/${id}/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ verified_by: 'user' })
            });
            if (response.ok) {
                await this.loadKnowledge();
                await this.loadStats();
            }
        } catch (error) {
            console.error('Failed to verify knowledge:', error);
        }
    }

    async unverifyKnowledge(id) {
        try {
            const response = await fetchWithAuth(`/api/v2/knowledge/${id}/unverify`, {
                method: 'POST'
            });
            if (response.ok) {
                await this.loadKnowledge();
                await this.loadStats();
            }
        } catch (error) {
            console.error('Failed to unverify knowledge:', error);
        }
    }

    async deleteKnowledge(id) {
        if (!confirm('Are you sure you want to delete this knowledge item?')) {
            return;
        }
        try {
            const response = await fetchWithAuth(`/api/v2/knowledge/${id}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                await this.loadKnowledge();
                await this.loadStats();
            }
        } catch (error) {
            console.error('Failed to delete knowledge:', error);
        }
    }

    async showDetails(id) {
        try {
            const response = await fetchWithAuth(`/api/v2/knowledge/${id}`);
            if (response.ok) {
                const data = await response.json();
                this.renderDetailsModal(data);
            }
        } catch (error) {
            console.error('Failed to load knowledge details:', error);
        }
    }

    renderDetailsModal(data) {
        const { knowledge, provenance } = data;
        const { dots, color } = this.getConfidenceIndicator(knowledge.effective_confidence);

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal knowledge-details-modal">
                <div class="modal-header">
                    <h3>Knowledge Details</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-content">
                    <div class="detail-section">
                        <label>Content</label>
                        <div class="detail-content">${this.escapeHtml(knowledge.canonical_content)}</div>
                    </div>

                    <div class="detail-row">
                        <div class="detail-section">
                            <label>Type</label>
                            <div class="knowledge-type-badge ${knowledge.knowledge_type || 'fact'}">
                                ${this.getTypeIcon(knowledge.knowledge_type)} ${knowledge.knowledge_type || 'fact'}
                            </div>
                        </div>
                        <div class="detail-section">
                            <label>Domain</label>
                            <div class="domain-tag">${knowledge.domain_path || 'personal'}</div>
                        </div>
                    </div>

                    <div class="detail-section">
                        <label>Confidence Breakdown</label>
                        <div class="confidence-breakdown">
                            <div class="confidence-row">
                                <span>Base confidence:</span>
                                <span>${Math.round(knowledge.base_confidence * 100)}%</span>
                            </div>
                            <div class="confidence-row">
                                <span>Source boost (${knowledge.source_count} sources):</span>
                                <span>+${Math.round(knowledge.source_boost * 100)}%</span>
                            </div>
                            <div class="confidence-row">
                                <span>Verification boost:</span>
                                <span>+${Math.round(knowledge.verification_boost * 100)}%</span>
                            </div>
                            <div class="confidence-row total">
                                <span>Effective confidence:</span>
                                <span class="confidence-indicator" style="color: var(--color-${color})">
                                    ${dots} ${Math.round(knowledge.effective_confidence * 100)}%
                                </span>
                            </div>
                        </div>
                    </div>

                    <div class="detail-section">
                        <label>Source Provenance (${provenance.length})</label>
                        <div class="provenance-list">
                            ${provenance.map(p => `
                                <div class="provenance-item">
                                    <div class="provenance-type ${p.contribution_type}">
                                        ${p.contribution_type}
                                    </div>
                                    <div class="provenance-details">
                                        <div class="provenance-source">
                                            ${p.source_type} • ${new Date(p.created_at).toLocaleDateString()}
                                        </div>
                                        ${p.source_preview ? `
                                            <div class="provenance-preview">"${this.escapeHtml(p.source_preview)}"</div>
                                        ` : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in renderer
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { KnowledgeBrowser };
}
