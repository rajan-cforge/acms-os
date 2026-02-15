/**
 * Reports Dashboard Component
 * Sprint 5: Reports & Insights - Frontend
 *
 * Displays:
 * - Dashboard overview with key stats
 * - Weekly report with topics and agent usage
 * - Topic trends chart
 * - Insights feed
 */

const { fetchWithAuth } = require('../api-client');

class ReportsDashboard {
    constructor(container) {
        this.container = container;
        this.dashboardStats = null;
        this.weeklyReport = null;
        this.topicTrends = null;
        this.insights = [];
        this.activeTab = 'overview';
    }

    async init() {
        this.render();
        await this.loadData();
    }

    render() {
        this.container.innerHTML = `
            <div class="reports-container">
                <div class="reports-header">
                    <h2>Reports & Insights</h2>
                    <div class="header-actions">
                        <select id="weekSelector" class="input week-selector" onchange="window.reportsDashboard.loadWeek(this.value)">
                            ${this.generateWeekOptions()}
                        </select>
                    </div>
                </div>

                <div class="reports-tabs">
                    <button class="tab-btn active" data-tab="overview" onclick="window.reportsDashboard.switchTab('overview')">
                        Overview
                    </button>
                    <button class="tab-btn" data-tab="weekly" onclick="window.reportsDashboard.switchTab('weekly')">
                        Weekly Report
                    </button>
                    <button class="tab-btn" data-tab="topics" onclick="window.reportsDashboard.switchTab('topics')">
                        Topic Trends
                    </button>
                    <button class="tab-btn" data-tab="insights" onclick="window.reportsDashboard.switchTab('insights')">
                        Insights
                    </button>
                </div>

                <div class="reports-content" id="reportsContent">
                    <div class="skeleton-loader">Loading...</div>
                </div>
            </div>
        `;
    }

    generateWeekOptions() {
        const options = [];
        const today = new Date();
        const currentMonday = new Date(today);
        currentMonday.setDate(today.getDate() - today.getDay() + 1);

        for (let i = 0; i < 12; i++) {
            const weekStart = new Date(currentMonday);
            weekStart.setDate(currentMonday.getDate() - (i * 7));
            const weekEnd = new Date(weekStart);
            weekEnd.setDate(weekStart.getDate() + 6);

            const label = i === 0 ? 'This Week' : i === 1 ? 'Last Week' :
                `${weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;

            options.push(`<option value="${weekStart.toISOString().split('T')[0]}">${label}</option>`);
        }

        return options.join('');
    }

    async loadData() {
        await Promise.all([
            this.loadDashboard(),
            this.loadWeeklyReport(),
            this.loadTopicTrends(),
            this.loadInsights()
        ]);
        this.renderTab();
    }

    async loadDashboard() {
        try {
            const response = await fetchWithAuth('/api/v2/reports/dashboard');
            if (response.ok) {
                this.dashboardStats = await response.json();
            }
        } catch (error) {
            console.error('Failed to load dashboard:', error);
        }
    }

    async loadWeeklyReport(weekStart = null) {
        try {
            const url = weekStart
                ? `/api/v2/reports/weekly/${weekStart}`
                : '/api/v2/reports/weekly/current';
            const response = await fetchWithAuth(url);
            if (response.ok) {
                this.weeklyReport = await response.json();
            }
        } catch (error) {
            console.error('Failed to load weekly report:', error);
        }
    }

    async loadTopicTrends() {
        try {
            const response = await fetchWithAuth('/api/v2/reports/topics/trends?days=30');
            if (response.ok) {
                this.topicTrends = await response.json();
            }
        } catch (error) {
            console.error('Failed to load topic trends:', error);
        }
    }

    async loadInsights() {
        try {
            const response = await fetchWithAuth('/api/v2/reports/insights?days=30&limit=20');
            if (response.ok) {
                this.insights = await response.json();
            }
        } catch (error) {
            console.error('Failed to load insights:', error);
        }
    }

    async loadWeek(weekStart) {
        await this.loadWeeklyReport(weekStart);
        if (this.activeTab === 'weekly') {
            this.renderTab();
        }
    }

    switchTab(tab) {
        this.activeTab = tab;

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        this.renderTab();
    }

    renderTab() {
        const content = document.getElementById('reportsContent');
        if (!content) return;

        switch (this.activeTab) {
            case 'overview':
                content.innerHTML = this.renderOverview();
                break;
            case 'weekly':
                content.innerHTML = this.renderWeekly();
                break;
            case 'topics':
                content.innerHTML = this.renderTopics();
                break;
            case 'insights':
                content.innerHTML = this.renderInsights();
                break;
        }
    }

    renderOverview() {
        if (!this.dashboardStats) {
            return '<div class="empty-state">No data available</div>';
        }

        const stats = this.dashboardStats;

        return `
            <div class="dashboard-grid">
                <div class="stat-card primary">
                    <div class="stat-icon">💬</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.total_queries_today}</div>
                        <div class="stat-label">Queries Today</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.total_queries_week}</div>
                        <div class="stat-label">This Week</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon">🧠</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.total_memories}</div>
                        <div class="stat-label">Total Memories</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon">⚡</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.cache_hit_rate}%</div>
                        <div class="stat-label">Cache Hit Rate</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon">📚</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.knowledge_items}</div>
                        <div class="stat-label">Knowledge Items</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon">✓</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.verified_items}</div>
                        <div class="stat-label">Verified</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon">🤖</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.top_agent}</div>
                        <div class="stat-label">Top Agent</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon">🏷️</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.active_topics}</div>
                        <div class="stat-label">Active Topics</div>
                    </div>
                </div>
            </div>

            ${this.weeklyReport && this.weeklyReport.highlights.length > 0 ? `
                <div class="highlights-section">
                    <h3>This Week's Highlights</h3>
                    <div class="highlights-list">
                        ${this.weeklyReport.highlights.map(h => `
                            <div class="highlight-item">
                                <span class="highlight-icon">✨</span>
                                <span class="highlight-text">${h}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;
    }

    renderWeekly() {
        if (!this.weeklyReport) {
            return '<div class="empty-state">No report available</div>';
        }

        const report = this.weeklyReport;

        return `
            <div class="weekly-report">
                <div class="report-header-section">
                    <div class="report-period">
                        ${new Date(report.week_start).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })} -
                        ${new Date(report.week_end).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                    </div>
                    <div class="report-summary">
                        <span class="summary-item">
                            <strong>${report.total_queries}</strong> queries
                        </span>
                        <span class="summary-divider">•</span>
                        <span class="summary-item">
                            <strong>${report.unique_topics}</strong> topics
                        </span>
                    </div>
                </div>

                <div class="report-sections">
                    <div class="report-section">
                        <h3>Top Topics</h3>
                        <div class="topics-list">
                            ${report.top_topics.map((t, i) => `
                                <div class="topic-item">
                                    <span class="topic-rank">${i + 1}</span>
                                    <span class="topic-name">${t.topic}</span>
                                    <span class="topic-count">${t.count}</span>
                                    <span class="topic-trend ${t.trend}">
                                        ${t.trend === 'up' ? '↑' : t.trend === 'down' ? '↓' : '→'}
                                        ${t.trend_percent > 0 ? t.trend_percent.toFixed(0) + '%' : ''}
                                    </span>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <div class="report-section">
                        <h3>Agent Usage</h3>
                        <div class="agents-list">
                            ${report.agent_usage.map(a => `
                                <div class="agent-item">
                                    <div class="agent-name">${a.agent}</div>
                                    <div class="agent-bar">
                                        <div class="agent-bar-fill" style="width: ${a.percentage}%"></div>
                                    </div>
                                    <div class="agent-stats">
                                        <span class="agent-queries">${a.queries} queries</span>
                                        <span class="agent-percent">${a.percentage}%</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <div class="report-section">
                        <h3>Knowledge Growth</h3>
                        <div class="knowledge-metrics">
                            <div class="metric-item">
                                <span class="metric-value">${report.knowledge.new_memories}</span>
                                <span class="metric-label">New Memories</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-value">${report.knowledge.facts_extracted}</span>
                                <span class="metric-label">Facts Extracted</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-value">${report.knowledge.cache_hit_rate}%</span>
                                <span class="metric-label">Cache Hit Rate</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-value">${report.knowledge.knowledge_verified}</span>
                                <span class="metric-label">Verified</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderTopics() {
        if (!this.topicTrends) {
            return '<div class="empty-state">No topic data available</div>';
        }

        return `
            <div class="topics-trends">
                <div class="trends-header">
                    <h3>Top Topics (Last 30 Days)</h3>
                </div>

                <div class="top-topics-chart">
                    ${this.topicTrends.top_topics.map((t, i) => `
                        <div class="topic-bar-item">
                            <div class="topic-bar-label">
                                <span class="topic-rank">${i + 1}</span>
                                <span class="topic-name">${t.topic}</span>
                            </div>
                            <div class="topic-bar-container">
                                <div class="topic-bar-fill" style="width: ${this.getBarWidth(t.count)}%"></div>
                            </div>
                            <span class="topic-bar-value">${t.count}</span>
                        </div>
                    `).join('')}
                </div>

                <div class="trends-header" style="margin-top: var(--space-6);">
                    <h3>Daily Activity</h3>
                </div>

                <div class="daily-activity">
                    ${this.topicTrends.daily.slice(-14).map(d => `
                        <div class="day-column">
                            <div class="day-bar" style="height: ${this.getDayHeight(d.total)}%"></div>
                            <div class="day-label">${new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' })}</div>
                            <div class="day-value">${d.total}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    getBarWidth(count) {
        if (!this.topicTrends || this.topicTrends.top_topics.length === 0) return 0;
        const max = this.topicTrends.top_topics[0].count;
        return (count / max) * 100;
    }

    getDayHeight(total) {
        if (!this.topicTrends || this.topicTrends.daily.length === 0) return 0;
        const max = Math.max(...this.topicTrends.daily.map(d => d.total));
        return max > 0 ? (total / max) * 100 : 0;
    }

    renderInsights() {
        if (this.insights.length === 0) {
            return `
                <div class="empty-state">
                    <div class="empty-icon">💡</div>
                    <div class="empty-text">No insights yet</div>
                    <div class="empty-hint">Insights are generated as you use ACMS</div>
                </div>
            `;
        }

        return `
            <div class="insights-list">
                ${this.insights.map(i => `
                    <div class="insight-card ${i.insight_type}">
                        <div class="insight-header">
                            <span class="insight-type-badge">${this.getInsightIcon(i.insight_type)} ${i.insight_type}</span>
                            <span class="insight-date">${this.formatDate(i.created_at)}</span>
                        </div>
                        <div class="insight-title">${i.title}</div>
                        <div class="insight-description">${i.description}</div>
                        <div class="insight-footer">
                            <span class="insight-confidence">Confidence: ${(i.confidence * 100).toFixed(0)}%</span>
                            <span class="insight-sources">${i.source_count} source${i.source_count !== 1 ? 's' : ''}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    getInsightIcon(type) {
        const icons = {
            'pattern': '📊',
            'recommendation': '💡',
            'observation': '👁️'
        };
        return icons[type] || '📌';
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

// Export for use in renderer
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ReportsDashboard };
}
