/**
 * Portfolio Constitution Component
 * Sprint 4: Financial Constitution - Frontend
 *
 * Displays:
 * - Allocation pie chart (target vs actual)
 * - Compliance status indicators
 * - Rebalancing recommendations
 * - Rule management
 */

const { fetchWithAuth } = require('../api-client');

class PortfolioConstitution {
    constructor(container) {
        this.container = container;
        this.buckets = [];
        this.rules = [];
        this.summary = null;
        this.recommendations = [];
        this.activeTab = 'overview';
    }

    async init() {
        this.render();
        await this.loadData();
    }

    render() {
        this.container.innerHTML = `
            <div class="constitution-container">
                <div class="constitution-header">
                    <div class="header-title">
                        <h2>Financial Constitution</h2>
                        <span class="compliance-badge" id="complianceBadge">Loading...</span>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-ghost" onclick="window.portfolioConstitution.syncData()">
                            Sync Data
                        </button>
                    </div>
                </div>

                <div class="constitution-tabs">
                    <button class="tab-btn active" data-tab="overview" onclick="window.portfolioConstitution.switchTab('overview')">
                        Overview
                    </button>
                    <button class="tab-btn" data-tab="buckets" onclick="window.portfolioConstitution.switchTab('buckets')">
                        Allocation Buckets
                    </button>
                    <button class="tab-btn" data-tab="rules" onclick="window.portfolioConstitution.switchTab('rules')">
                        Rules
                    </button>
                    <button class="tab-btn" data-tab="rebalance" onclick="window.portfolioConstitution.switchTab('rebalance')">
                        Rebalance
                    </button>
                </div>

                <div class="constitution-content" id="constitutionContent">
                    <div class="skeleton-loader">Loading...</div>
                </div>
            </div>
        `;
    }

    async loadData() {
        await Promise.all([
            this.loadBuckets(),
            this.loadRules(),
            this.loadSummary(),
            this.loadRecommendations()
        ]);
        this.renderTab();
    }

    async loadBuckets() {
        try {
            const response = await fetchWithAuth('/api/v2/constitution/buckets');
            if (response.ok) {
                this.buckets = await response.json();
            }
        } catch (error) {
            console.error('Failed to load buckets:', error);
        }
    }

    async loadRules() {
        try {
            const response = await fetchWithAuth('/api/v2/constitution/rules');
            if (response.ok) {
                this.rules = await response.json();
            }
        } catch (error) {
            console.error('Failed to load rules:', error);
        }
    }

    async loadSummary() {
        try {
            const response = await fetchWithAuth('/api/v2/constitution/portfolio/summary');
            if (response.ok) {
                this.summary = await response.json();
                this.updateComplianceBadge();
            }
        } catch (error) {
            console.error('Failed to load summary:', error);
        }
    }

    async loadRecommendations() {
        try {
            const response = await fetchWithAuth('/api/v2/constitution/portfolio/rebalance');
            if (response.ok) {
                this.recommendations = await response.json();
            }
        } catch (error) {
            console.error('Failed to load recommendations:', error);
        }
    }

    updateComplianceBadge() {
        const badge = document.getElementById('complianceBadge');
        if (!badge || !this.summary) return;

        const statusMap = {
            'compliant': { text: 'Compliant', class: 'badge-success' },
            'warning': { text: 'Warning', class: 'badge-warning' },
            'non_compliant': { text: 'Non-Compliant', class: 'badge-danger' },
            'unknown': { text: 'No Data', class: 'badge-neutral' }
        };

        const status = statusMap[this.summary.overall_status] || statusMap['unknown'];
        badge.textContent = status.text;
        badge.className = `compliance-badge ${status.class}`;
    }

    switchTab(tab) {
        this.activeTab = tab;

        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        this.renderTab();
    }

    renderTab() {
        const content = document.getElementById('constitutionContent');
        if (!content) return;

        switch (this.activeTab) {
            case 'overview':
                content.innerHTML = this.renderOverview();
                break;
            case 'buckets':
                content.innerHTML = this.renderBuckets();
                break;
            case 'rules':
                content.innerHTML = this.renderRules();
                break;
            case 'rebalance':
                content.innerHTML = this.renderRebalance();
                break;
        }
    }

    renderOverview() {
        if (!this.summary) {
            return '<div class="empty-state">No portfolio data available. Connect your accounts via Plaid.</div>';
        }

        const totalValue = this.formatCurrency(this.summary.total_value);

        return `
            <div class="overview-grid">
                <div class="overview-card total-value-card">
                    <div class="card-label">Total Portfolio Value</div>
                    <div class="card-value">${totalValue}</div>
                    <div class="card-meta">As of ${this.summary.snapshot_date}</div>
                </div>

                <div class="overview-card compliance-card">
                    <div class="card-label">Compliance Status</div>
                    <div class="compliance-stats">
                        <div class="stat passed">
                            <span class="stat-value">${this.summary.rules_passed}</span>
                            <span class="stat-label">Passed</span>
                        </div>
                        <div class="stat warned">
                            <span class="stat-value">${this.summary.rules_warned}</span>
                            <span class="stat-label">Warnings</span>
                        </div>
                        <div class="stat failed">
                            <span class="stat-value">${this.summary.rules_failed}</span>
                            <span class="stat-label">Failed</span>
                        </div>
                    </div>
                </div>

                <div class="overview-card allocation-chart-card">
                    <div class="card-label">Target vs Actual Allocation</div>
                    <div class="allocation-bars">
                        ${this.summary.allocations.map(a => this.renderAllocationBar(a)).join('')}
                    </div>
                </div>

                <div class="overview-card drift-card">
                    <div class="card-label">Allocation Drift</div>
                    <div class="drift-list">
                        ${this.summary.allocations
                            .filter(a => Math.abs(a.drift_percent) >= 2)
                            .sort((a, b) => Math.abs(b.drift_percent) - Math.abs(a.drift_percent))
                            .slice(0, 5)
                            .map(a => this.renderDriftItem(a))
                            .join('') || '<div class="empty-hint">All allocations within target range</div>'}
                    </div>
                </div>
            </div>
        `;
    }

    renderAllocationBar(alloc) {
        const targetWidth = Math.min(100, alloc.target_percent);
        const actualWidth = Math.min(100, alloc.actual_percent);

        return `
            <div class="allocation-bar-item">
                <div class="bar-label">
                    <span class="bucket-icon">${alloc.icon || '📊'}</span>
                    <span class="bucket-name">${alloc.display_name}</span>
                </div>
                <div class="bar-container">
                    <div class="bar-track">
                        <div class="bar-target" style="width: ${targetWidth}%; background: ${alloc.color || '#607D8B'}40"></div>
                        <div class="bar-actual" style="width: ${actualWidth}%; background: ${alloc.color || '#607D8B'}"></div>
                    </div>
                    <div class="bar-values">
                        <span class="actual-value">${alloc.actual_percent.toFixed(1)}%</span>
                        <span class="target-value">/ ${alloc.target_percent.toFixed(1)}%</span>
                    </div>
                </div>
            </div>
        `;
    }

    renderDriftItem(alloc) {
        const driftClass = alloc.drift_percent > 0 ? 'over' : 'under';
        const driftSign = alloc.drift_percent > 0 ? '+' : '';

        return `
            <div class="drift-item ${driftClass}">
                <span class="drift-name">${alloc.display_name}</span>
                <span class="drift-value">${driftSign}${alloc.drift_percent.toFixed(1)}%</span>
            </div>
        `;
    }

    renderBuckets() {
        if (this.buckets.length === 0) {
            return `
                <div class="empty-state">
                    <div class="empty-icon">📊</div>
                    <div class="empty-text">No allocation buckets defined</div>
                    <button class="btn btn-success" onclick="window.portfolioConstitution.showAddBucketModal()">
                        Add Bucket
                    </button>
                </div>
            `;
        }

        const totalTarget = this.buckets.reduce((sum, b) => sum + b.target_percent, 0);

        return `
            <div class="buckets-header">
                <div class="buckets-summary">
                    <span>Total Target: ${totalTarget.toFixed(1)}%</span>
                    ${totalTarget !== 100 ? `<span class="warning-text">(Should be 100%)</span>` : ''}
                </div>
                <button class="btn btn-success" onclick="window.portfolioConstitution.showAddBucketModal()">
                    Add Bucket
                </button>
            </div>
            <div class="buckets-grid">
                ${this.buckets.map(b => this.renderBucketCard(b)).join('')}
            </div>
        `;
    }

    renderBucketCard(bucket) {
        return `
            <div class="bucket-card" style="border-left-color: ${bucket.color || '#607D8B'}">
                <div class="bucket-header">
                    <span class="bucket-icon">${bucket.icon || '📊'}</span>
                    <span class="bucket-name">${bucket.display_name}</span>
                </div>
                <div class="bucket-target">
                    <span class="target-value">${bucket.target_percent}%</span>
                    <span class="target-label">Target</span>
                </div>
                <div class="bucket-range">
                    ${bucket.min_percent ? `Min: ${bucket.min_percent}%` : ''}
                    ${bucket.max_percent ? `Max: ${bucket.max_percent}%` : ''}
                </div>
                <div class="bucket-tags">
                    ${bucket.security_tags.map(t => `<span class="tag">${t}</span>`).join('')}
                </div>
                <div class="bucket-actions">
                    <button class="btn btn-ghost btn-sm" onclick="window.portfolioConstitution.editBucket('${bucket.bucket_id}')">
                        Edit
                    </button>
                    <button class="btn btn-ghost btn-sm btn-danger" onclick="window.portfolioConstitution.deleteBucket('${bucket.bucket_id}')">
                        Delete
                    </button>
                </div>
            </div>
        `;
    }

    renderRules() {
        if (this.rules.length === 0) {
            return `
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <div class="empty-text">No constitution rules defined</div>
                    <button class="btn btn-success" onclick="window.portfolioConstitution.showAddRuleModal()">
                        Add Rule
                    </button>
                </div>
            `;
        }

        return `
            <div class="rules-header">
                <button class="btn btn-success" onclick="window.portfolioConstitution.showAddRuleModal()">
                    Add Rule
                </button>
            </div>
            <div class="rules-list">
                ${this.rules.map(r => this.renderRuleCard(r)).join('')}
            </div>
        `;
    }

    renderRuleCard(rule) {
        const severityClass = {
            'info': 'severity-info',
            'warning': 'severity-warning',
            'critical': 'severity-critical'
        }[rule.severity] || 'severity-info';

        return `
            <div class="rule-card ${severityClass}">
                <div class="rule-header">
                    <span class="rule-name">${rule.name}</span>
                    <span class="rule-type">${rule.rule_type}</span>
                </div>
                ${rule.description ? `<div class="rule-description">${rule.description}</div>` : ''}
                <div class="rule-params">
                    ${this.formatRuleParams(rule.parameters)}
                </div>
                <div class="rule-actions">
                    <span class="severity-badge ${severityClass}">${rule.severity}</span>
                    <button class="btn btn-ghost btn-sm btn-danger" onclick="window.portfolioConstitution.deleteRule('${rule.rule_id}')">
                        Delete
                    </button>
                </div>
            </div>
        `;
    }

    formatRuleParams(params) {
        return Object.entries(params)
            .map(([key, value]) => `<span class="param">${key}: ${value}</span>`)
            .join(' ');
    }

    renderRebalance() {
        if (this.recommendations.length === 0) {
            return `
                <div class="empty-state">
                    <div class="empty-icon">Balanced</div>
                    <div class="empty-text">No rebalancing needed</div>
                    <div class="empty-hint">Your portfolio is within target allocations</div>
                </div>
            `;
        }

        return `
            <div class="rebalance-list">
                ${this.recommendations.map(r => this.renderRebalanceCard(r)).join('')}
            </div>
        `;
    }

    renderRebalanceCard(rec) {
        const actionClass = {
            'buy': 'action-buy',
            'sell': 'action-sell',
            'hold': 'action-hold'
        }[rec.action] || '';

        const changeValue = rec.change_value ? this.formatCurrency(Math.abs(rec.change_value)) : '';
        const changeSign = rec.change_percent > 0 ? '+' : '';

        return `
            <div class="rebalance-card ${actionClass}">
                <div class="rebalance-action">${rec.action.toUpperCase()}</div>
                <div class="rebalance-details">
                    <div class="rebalance-security">
                        ${rec.ticker ? `<span class="ticker">${rec.ticker}</span>` : ''}
                        <span class="security-name">${rec.security_name || rec.bucket_name}</span>
                    </div>
                    <div class="rebalance-amounts">
                        ${changeValue ? `<span class="change-value">${changeValue}</span>` : ''}
                        <span class="change-percent">${changeSign}${rec.change_percent.toFixed(1)}%</span>
                    </div>
                </div>
                <div class="rebalance-reason">${rec.reason}</div>
                <div class="rebalance-actions">
                    <button class="btn btn-ghost btn-sm" onclick="window.portfolioConstitution.dismissRecommendation('${rec.recommendation_id}')">
                        Dismiss
                    </button>
                </div>
            </div>
        `;
    }

    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
    }

    async syncData() {
        try {
            const response = await fetchWithAuth('/api/plaid/sync-all', { method: 'POST' });
            if (response.ok) {
                await this.loadData();
            }
        } catch (error) {
            console.error('Sync failed:', error);
        }
    }

    async deleteBucket(bucketId) {
        if (!confirm('Delete this allocation bucket?')) return;

        try {
            const response = await fetchWithAuth(`/api/v2/constitution/buckets/${bucketId}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                await this.loadBuckets();
                this.renderTab();
            }
        } catch (error) {
            console.error('Failed to delete bucket:', error);
        }
    }

    async deleteRule(ruleId) {
        if (!confirm('Delete this constitution rule?')) return;

        try {
            const response = await fetchWithAuth(`/api/v2/constitution/rules/${ruleId}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                await this.loadRules();
                this.renderTab();
            }
        } catch (error) {
            console.error('Failed to delete rule:', error);
        }
    }

    async dismissRecommendation(recId) {
        try {
            const response = await fetchWithAuth(
                `/api/v2/constitution/portfolio/rebalance/${recId}/dismiss`,
                { method: 'POST' }
            );
            if (response.ok) {
                await this.loadRecommendations();
                this.renderTab();
            }
        } catch (error) {
            console.error('Failed to dismiss recommendation:', error);
        }
    }

    showAddBucketModal() {
        // Simplified modal for adding bucket
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3>Add Allocation Bucket</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">x</button>
                </div>
                <div class="modal-content">
                    <div class="form-group">
                        <label>Name</label>
                        <input type="text" id="bucketName" class="input" placeholder="e.g., us_equity" />
                    </div>
                    <div class="form-group">
                        <label>Display Name</label>
                        <input type="text" id="bucketDisplayName" class="input" placeholder="e.g., US Equities" />
                    </div>
                    <div class="form-group">
                        <label>Target Percentage</label>
                        <input type="number" id="bucketTarget" class="input" min="0" max="100" value="20" />
                    </div>
                    <div class="form-group">
                        <label>Color (hex)</label>
                        <input type="text" id="bucketColor" class="input" placeholder="#2196F3" />
                    </div>
                    <div class="form-group">
                        <label>Icon (emoji)</label>
                        <input type="text" id="bucketIcon" class="input" placeholder="e.g., 🇺🇸" />
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    <button class="btn btn-success" onclick="window.portfolioConstitution.createBucket()">Create</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    async createBucket() {
        const name = document.getElementById('bucketName').value;
        const displayName = document.getElementById('bucketDisplayName').value;
        const target = parseFloat(document.getElementById('bucketTarget').value);
        const color = document.getElementById('bucketColor').value;
        const icon = document.getElementById('bucketIcon').value;

        if (!name || !displayName || isNaN(target)) {
            alert('Please fill in required fields');
            return;
        }

        try {
            const response = await fetchWithAuth('/api/v2/constitution/buckets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    display_name: displayName,
                    target_percent: target,
                    color: color || null,
                    icon: icon || null,
                    security_tags: [],
                    security_types: [],
                    sectors: []
                })
            });

            if (response.ok) {
                document.querySelector('.modal-overlay').remove();
                await this.loadBuckets();
                this.renderTab();
            }
        } catch (error) {
            console.error('Failed to create bucket:', error);
        }
    }

    showAddRuleModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3>Add Constitution Rule</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">x</button>
                </div>
                <div class="modal-content">
                    <div class="form-group">
                        <label>Name</label>
                        <input type="text" id="ruleName" class="input" placeholder="e.g., Cash Reserve Minimum" />
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="ruleDescription" class="input" rows="2"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Rule Type</label>
                        <select id="ruleType" class="input">
                            <option value="allocation">Allocation</option>
                            <option value="position_limit">Position Limit</option>
                            <option value="sector_limit">Sector Limit</option>
                            <option value="custom">Custom</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Severity</label>
                        <select id="ruleSeverity" class="input">
                            <option value="info">Info</option>
                            <option value="warning" selected>Warning</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    <button class="btn btn-success" onclick="window.portfolioConstitution.createRule()">Create</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    async createRule() {
        const name = document.getElementById('ruleName').value;
        const description = document.getElementById('ruleDescription').value;
        const ruleType = document.getElementById('ruleType').value;
        const severity = document.getElementById('ruleSeverity').value;

        if (!name) {
            alert('Please enter a rule name');
            return;
        }

        try {
            const response = await fetchWithAuth('/api/v2/constitution/rules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    description: description || null,
                    rule_type: ruleType,
                    severity,
                    parameters: {}
                })
            });

            if (response.ok) {
                document.querySelector('.modal-overlay').remove();
                await this.loadRules();
                this.renderTab();
            }
        } catch (error) {
            console.error('Failed to create rule:', error);
        }
    }
}

// Export for use in renderer
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PortfolioConstitution };
}
