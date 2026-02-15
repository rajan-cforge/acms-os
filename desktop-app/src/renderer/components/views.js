/**
 * ACMS Desktop - View Components
 *
 * Memory Browser, Search, and Analytics views
 *
 * Security: All DOM manipulation via createElement, no innerHTML with user data
 */

const API_BASE = 'http://localhost:40080';

// ============================================================================
// MEMORY BROWSER VIEW
// ============================================================================

/**
 * Render the Memory Browser view
 * Shows memories grouped by collection, with search and filtering
 */
async function renderMemoryBrowser(container) {
    container.innerHTML = ''; // Clear existing content

    // Header
    const header = document.createElement('div');
    header.className = 'view-header';
    header.innerHTML = `
        <h2>Memory Browser</h2>
        <p class="view-subtitle">Explore and manage your memories across collections</p>
    `;
    container.appendChild(header);

    // Stats section
    const statsSection = document.createElement('div');
    statsSection.className = 'memory-stats';
    statsSection.innerHTML = '<div class="loading">Loading memory statistics...</div>';
    container.appendChild(statsSection);

    // Load and display stats
    try {
        const stats = await fetch(`${API_BASE}/stats`).then(r => r.json());
        renderMemoryStats(statsSection, stats);
    } catch (error) {
        statsSection.innerHTML = `<div class="error">Failed to load stats: ${error.message}</div>`;
    }

    // Memory list section
    const listSection = document.createElement('div');
    listSection.className = 'memory-list-section';

    // Controls
    const controls = document.createElement('div');
    controls.className = 'memory-controls';
    controls.innerHTML = `
        <select id="memory-filter-privacy" class="memory-filter">
            <option value="">All Privacy Levels</option>
            <option value="PUBLIC">PUBLIC</option>
            <option value="INTERNAL">INTERNAL</option>
            <option value="CONFIDENTIAL">CONFIDENTIAL</option>
            <option value="LOCAL_ONLY">LOCAL_ONLY</option>
        </select>
        <select id="memory-filter-tier" class="memory-filter">
            <option value="">All Tiers</option>
            <option value="CORE">CORE</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="ARCHIVE">ARCHIVE</option>
        </select>
        <input type="text" id="memory-search" class="memory-search" placeholder="Search memories...">
        <button id="refresh-memories" class="btn-secondary">Refresh</button>
    `;
    listSection.appendChild(controls);

    // Memory list
    const memoryList = document.createElement('div');
    memoryList.id = 'memory-list';
    memoryList.className = 'memory-list';
    memoryList.innerHTML = '<div class="loading">Loading memories...</div>';
    listSection.appendChild(memoryList);

    container.appendChild(listSection);

    // Load memories
    await loadMemories(memoryList, {});

    // Setup event listeners
    document.getElementById('memory-filter-privacy').addEventListener('change', () => reloadMemories());
    document.getElementById('memory-filter-tier').addEventListener('change', () => reloadMemories());
    document.getElementById('memory-search').addEventListener('input', debounce(() => reloadMemories(), 300));
    document.getElementById('refresh-memories').addEventListener('click', () => reloadMemories());
}

function renderMemoryStats(container, stats) {
    container.innerHTML = '';

    // Total count card
    const totalCard = createStatCard('Total Memories', stats.total.toLocaleString(), '📚');
    container.appendChild(totalCard);

    // By privacy
    const privacyStats = Object.entries(stats.by_privacy || {})
        .map(([level, count]) => `${level}: ${count}`)
        .join(' | ');
    const privacyCard = createStatCard('By Privacy', privacyStats || 'N/A', '🔒');
    container.appendChild(privacyCard);

    // By tier
    const tierStats = Object.entries(stats.by_tier || {})
        .map(([tier, count]) => `${tier}: ${count}`)
        .join(' | ');
    const tierCard = createStatCard('By Tier', tierStats || 'N/A', '📊');
    container.appendChild(tierCard);

    // By source
    const sourceStats = Object.entries(stats.by_source || {})
        .slice(0, 5)
        .map(([source, count]) => `${source}: ${count}`)
        .join(' | ');
    const sourceCard = createStatCard('By Source', sourceStats || 'N/A', '🔗');
    container.appendChild(sourceCard);
}

async function loadMemories(container, filters) {
    try {
        const params = new URLSearchParams({ limit: '50' });
        if (filters.privacy) params.append('privacy_level', filters.privacy);
        if (filters.tier) params.append('tier', filters.tier);

        const response = await fetch(`${API_BASE}/memories?${params}`);
        const data = await response.json();

        // API returns { memories: [...], count, limit, offset }
        const memories = data.memories || data || [];

        container.innerHTML = '';

        if (!memories.length) {
            container.innerHTML = '<div class="empty-state">No memories found</div>';
            return;
        }

        // Filter by search if present
        let filtered = memories;
        const searchTerm = document.getElementById('memory-search')?.value?.toLowerCase();
        if (searchTerm) {
            filtered = memories.filter(m =>
                m.content?.toLowerCase().includes(searchTerm) ||
                m.tags?.some(t => t.toLowerCase().includes(searchTerm))
            );
        }

        filtered.forEach(memory => {
            const card = createMemoryCard(memory);
            container.appendChild(card);
        });

        // Show count
        const countEl = document.createElement('div');
        countEl.className = 'memory-count';
        countEl.textContent = `Showing ${filtered.length} of ${memories.length} memories`;
        container.insertBefore(countEl, container.firstChild);

    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load memories: ${error.message}</div>`;
    }
}

function reloadMemories() {
    const container = document.getElementById('memory-list');
    const privacy = document.getElementById('memory-filter-privacy')?.value;
    const tier = document.getElementById('memory-filter-tier')?.value;
    loadMemories(container, { privacy, tier });
}

function createMemoryCard(memory) {
    const card = document.createElement('div');
    card.className = 'memory-card';
    // API returns memory_id, not id
    const memoryId = memory.memory_id || memory.id;
    card.setAttribute('data-memory-id', memoryId);

    // Header with badges
    const header = document.createElement('div');
    header.className = 'memory-card-header';

    const privacy = document.createElement('span');
    privacy.className = `badge badge-privacy badge-${(memory.privacy_level || 'unknown').toLowerCase()}`;
    privacy.textContent = memory.privacy_level || 'Unknown';
    header.appendChild(privacy);

    const tier = document.createElement('span');
    tier.className = `badge badge-tier badge-${(memory.tier || 'unknown').toLowerCase()}`;
    tier.textContent = memory.tier || 'Unknown';
    header.appendChild(tier);

    // Use crs_score (from API) or importance
    const score = memory.crs_score || memory.importance;
    if (score) {
        const importance = document.createElement('span');
        importance.className = 'memory-importance';
        importance.textContent = `★ ${score.toFixed(2)}`;
        header.appendChild(importance);
    }

    card.appendChild(header);

    // Content
    const content = document.createElement('div');
    content.className = 'memory-content';
    content.textContent = truncateText(memory.content, 300);
    card.appendChild(content);

    // Tags
    if (memory.tags?.length) {
        const tags = document.createElement('div');
        tags.className = 'memory-tags';
        memory.tags.slice(0, 5).forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'memory-tag';
            tagEl.textContent = tag;
            tags.appendChild(tagEl);
        });
        card.appendChild(tags);
    }

    // Footer
    const footer = document.createElement('div');
    footer.className = 'memory-footer';
    footer.innerHTML = `<span class="memory-date">${formatDate(memory.created_at)}</span>`;
    if (memoryId) {
        const idSpan = document.createElement('span');
        idSpan.className = 'memory-id';
        idSpan.textContent = memoryId.slice(0, 8) + '...';
        idSpan.title = memoryId;
        footer.appendChild(idSpan);
    }
    card.appendChild(footer);

    return card;
}

// ============================================================================
// SEARCH VIEW
// ============================================================================

/**
 * Render the Search view
 * Semantic search across all collections
 */
async function renderSearchView(container) {
    container.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'view-header';
    header.innerHTML = `
        <h2>Semantic Search</h2>
        <p class="view-subtitle">Search across your memories using natural language</p>
    `;
    container.appendChild(header);

    // Search form
    const searchForm = document.createElement('div');
    searchForm.className = 'search-form';
    searchForm.innerHTML = `
        <div class="search-input-group">
            <input type="text" id="search-query" class="search-input" placeholder="Search for anything...">
            <button id="search-btn" class="btn-primary">Search</button>
        </div>
        <div class="search-options">
            <label>
                <input type="number" id="search-limit" value="10" min="1" max="50">
                Results
            </label>
            <label>
                <input type="number" id="search-threshold" value="0.5" min="0" max="1" step="0.1">
                Min Score
            </label>
        </div>
    `;
    container.appendChild(searchForm);

    // Results
    const results = document.createElement('div');
    results.id = 'search-results';
    results.className = 'search-results';
    results.innerHTML = '<div class="empty-state">Enter a search query above</div>';
    container.appendChild(results);

    // Event listeners
    document.getElementById('search-btn').addEventListener('click', () => performSearch());
    document.getElementById('search-query').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
}

async function performSearch() {
    const query = document.getElementById('search-query').value.trim();
    if (!query) return;

    const limit = parseInt(document.getElementById('search-limit').value) || 10;
    const threshold = parseFloat(document.getElementById('search-threshold').value) || 0.5;

    const results = document.getElementById('search-results');
    results.innerHTML = '<div class="loading">Searching...</div>';

    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                limit,
                threshold
            })
        });

        const data = await response.json();
        renderSearchResults(results, data, query);

    } catch (error) {
        results.innerHTML = `<div class="error">Search failed: ${error.message}</div>`;
    }
}

function renderSearchResults(container, data, query) {
    container.innerHTML = '';

    const memories = data.memories || data.results || data;

    if (!memories?.length) {
        container.innerHTML = '<div class="empty-state">No results found. Try a different query.</div>';
        return;
    }

    // Results header
    const header = document.createElement('div');
    header.className = 'search-results-header';
    header.innerHTML = `
        <span>Found ${memories.length} results for "<strong>${escapeHtml(query)}</strong>"</span>
        ${data.latency_ms ? `<span class="search-latency">${data.latency_ms}ms</span>` : ''}
    `;
    container.appendChild(header);

    // Results list
    memories.forEach((memory, index) => {
        const card = document.createElement('div');
        card.className = 'search-result-card';

        // Score badge
        const score = memory.score || memory.similarity || memory.relevance || 0;
        const scoreBadge = document.createElement('div');
        scoreBadge.className = `score-badge ${score >= 0.8 ? 'high' : score >= 0.5 ? 'medium' : 'low'}`;
        scoreBadge.textContent = `${(score * 100).toFixed(0)}%`;
        card.appendChild(scoreBadge);

        // Content
        const content = document.createElement('div');
        content.className = 'result-content';
        content.textContent = truncateText(memory.content, 400);
        card.appendChild(content);

        // Metadata
        const meta = document.createElement('div');
        meta.className = 'result-meta';
        meta.innerHTML = `
            <span class="badge badge-privacy">${memory.privacy_level || 'N/A'}</span>
            <span class="badge badge-tier">${memory.tier || 'N/A'}</span>
            <span class="result-date">${formatDate(memory.created_at)}</span>
        `;
        card.appendChild(meta);

        container.appendChild(card);
    });
}

// ============================================================================
// ANALYTICS VIEW
// ============================================================================

/**
 * Render the Analytics dashboard view
 * Shows cache stats, cost, API usage, and memory growth
 */
async function renderAnalyticsView(container) {
    container.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'view-header';
    header.innerHTML = `
        <h2>Analytics Dashboard</h2>
        <p class="view-subtitle">Track costs, agent performance, and memory statistics</p>
    `;
    container.appendChild(header);

    // Time period selector
    const controls = document.createElement('div');
    controls.className = 'analytics-controls';
    controls.innerHTML = `
        <select id="analytics-period">
            <option value="7">Last 7 days</option>
            <option value="30" selected>Last 30 days</option>
            <option value="90">Last 90 days</option>
        </select>
        <button id="refresh-analytics" class="btn-secondary">Refresh</button>
    `;
    container.appendChild(controls);

    // Dashboard grid
    const dashboard = document.createElement('div');
    dashboard.id = 'analytics-dashboard';
    dashboard.className = 'analytics-dashboard';
    dashboard.innerHTML = '<div class="loading">Loading analytics...</div>';
    container.appendChild(dashboard);

    // Load analytics
    await loadAnalytics(dashboard, 30);

    // Event listeners
    document.getElementById('analytics-period').addEventListener('change', (e) => {
        loadAnalytics(dashboard, parseInt(e.target.value));
    });
    document.getElementById('refresh-analytics').addEventListener('click', () => {
        const days = parseInt(document.getElementById('analytics-period').value);
        loadAnalytics(dashboard, days);
    });
}

async function loadAnalytics(container, days) {
    container.innerHTML = '<div class="loading">Loading analytics...</div>';

    try {
        // Fetch analytics data
        const [dashboardData, statsData] = await Promise.all([
            fetch(`${API_BASE}/analytics/dashboard?user_id=default&days=${days}`).then(r => r.json()).catch(() => ({})),
            fetch(`${API_BASE}/stats`).then(r => r.json()).catch(() => ({}))
        ]);

        container.innerHTML = '';

        // Cost Summary Section (NEW - moved from cache, shows actual spend)
        const costSection = document.createElement('div');
        costSection.className = 'analytics-section';
        costSection.innerHTML = '<h3>Cost & Usage Summary</h3>';
        renderCostSummary(costSection, dashboardData);
        container.appendChild(costSection);

        // Agent Performance Section
        const agentSection = document.createElement('div');
        agentSection.className = 'analytics-section';
        agentSection.innerHTML = '<h3>Agent Performance</h3>';
        renderAgentPerformance(agentSection, dashboardData.source_performance || []);
        container.appendChild(agentSection);

        // Memory Statistics Section
        const growthSection = document.createElement('div');
        growthSection.className = 'analytics-section';
        growthSection.innerHTML = '<h3>Memory Statistics</h3>';
        renderMemoryGrowth(growthSection, statsData);
        container.appendChild(growthSection);

    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load analytics: ${error.message}</div>`;
    }
}

function renderCachePerformance(container, data) {
    const grid = document.createElement('div');
    grid.className = 'stat-grid';

    grid.appendChild(createStatCard('Total Queries', (data.total_queries || 0).toLocaleString(), '📊'));
    grid.appendChild(createStatCard('Cache Hits', (data.cache_hits || 0).toLocaleString(), '⚡'));
    grid.appendChild(createStatCard('Hit Rate', `${(data.cache_hit_rate || 0).toFixed(1)}%`, '🎯'));
    grid.appendChild(createStatCard('Cost Savings', `$${(data.estimated_cost_savings_usd || 0).toFixed(2)}`, '💰'));
    grid.appendChild(createStatCard('Avg Latency (Hit)', `${(data.avg_latency_cache_hit_ms || 0).toFixed(0)}ms`, '⏱️'));
    grid.appendChild(createStatCard('Avg Latency (Miss)', `${(data.avg_latency_cache_miss_ms || 0).toFixed(0)}ms`, '⏱️'));

    container.appendChild(grid);
}

function renderCostSummary(container, data) {
    const grid = document.createElement('div');
    grid.className = 'stat-grid';

    // Calculate totals from agent performance if available
    const agents = data.source_performance || [];
    const totalQueries = agents.reduce((sum, a) => sum + (a.total_queries || 0), 0);

    // Estimated cost based on typical token usage (~500 tokens/query at ~$0.002/query average)
    const estimatedCost = totalQueries * 0.002;
    const ollamaQueries = agents.find(a => a.source_name === 'Ollama')?.total_queries || 0;
    const ollamaSavings = ollamaQueries * 0.002; // Free local queries

    grid.appendChild(createStatCard('Total Queries', totalQueries.toLocaleString(), '📊'));
    grid.appendChild(createStatCard('Est. API Cost', `$${estimatedCost.toFixed(2)}`, '💰'));
    grid.appendChild(createStatCard('Local (Free)', ollamaQueries.toLocaleString(), '🏠'));
    grid.appendChild(createStatCard('Savings', `$${ollamaSavings.toFixed(2)}`, '✨'));

    container.appendChild(grid);

    // Add explanation
    const note = document.createElement('p');
    note.className = 'analytics-note';
    note.textContent = 'Cost estimates based on typical token usage. Ollama queries are free (local inference).';
    container.appendChild(note);
}

function renderAgentPerformance(container, data) {
    if (!data.length) {
        container.innerHTML += '<div class="empty-state">No agent data available</div>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'analytics-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Agent</th>
                <th>Queries</th>
                <th>Avg Rating</th>
                <th>👍</th>
                <th>👎</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tbody = table.querySelector('tbody');
    data.forEach(agent => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><span class="badge badge-agent">${escapeHtml(agent.source_name || 'Unknown')}</span></td>
            <td>${agent.total_queries || 0}</td>
            <td>${(agent.avg_rating || 0).toFixed(2)}</td>
            <td class="positive">${agent.thumbs_up || 0}</td>
            <td class="negative">${agent.thumbs_down || 0}</td>
        `;
        tbody.appendChild(row);
    });

    container.appendChild(table);
}

function renderUserSatisfaction(container, data) {
    const grid = document.createElement('div');
    grid.className = 'stat-grid';

    grid.appendChild(createStatCard('Total Feedback', (data.total_feedback || 0).toLocaleString(), '📝'));
    grid.appendChild(createStatCard('Avg Rating', (data.avg_rating || 0).toFixed(2), '⭐'));
    grid.appendChild(createStatCard('Thumbs Up', `${(data.thumbs_up_percentage || 0).toFixed(1)}%`, '👍'));
    grid.appendChild(createStatCard('Thumbs Down', `${(data.thumbs_down_percentage || 0).toFixed(1)}%`, '👎'));

    container.appendChild(grid);
}

function renderMemoryGrowth(container, data) {
    const grid = document.createElement('div');
    grid.className = 'stat-grid';

    grid.appendChild(createStatCard('Total Memories', (data.total || 0).toLocaleString(), '📚'));

    // By source breakdown
    const sources = Object.entries(data.by_source || {}).slice(0, 4);
    sources.forEach(([source, count]) => {
        grid.appendChild(createStatCard(source, count.toLocaleString(), '🔗'));
    });

    container.appendChild(grid);

    // Privacy breakdown chart
    const privacyChart = document.createElement('div');
    privacyChart.className = 'privacy-chart';
    privacyChart.innerHTML = '<h4>By Privacy Level</h4>';

    const privacyData = data.by_privacy || {};
    const total = Object.values(privacyData).reduce((a, b) => a + b, 0) || 1;

    Object.entries(privacyData).forEach(([level, count]) => {
        const bar = document.createElement('div');
        bar.className = 'chart-bar';
        const pct = ((count / total) * 100).toFixed(1);
        bar.innerHTML = `
            <span class="bar-label">${level}</span>
            <div class="bar-track">
                <div class="bar-fill" style="width: ${pct}%"></div>
            </div>
            <span class="bar-value">${count} (${pct}%)</span>
        `;
        privacyChart.appendChild(bar);
    });

    container.appendChild(privacyChart);
}

function renderRecentQueries(container, queries) {
    if (!queries.length) {
        container.innerHTML += '<div class="empty-state">No recent queries</div>';
        return;
    }

    const list = document.createElement('div');
    list.className = 'recent-queries-list';

    queries.slice(0, 10).forEach(query => {
        const item = document.createElement('div');
        item.className = 'query-item';
        item.innerHTML = `
            <div class="query-text">${escapeHtml(truncateText(query.query || query.question, 100))}</div>
            <div class="query-meta">
                <span class="badge badge-agent">${escapeHtml(query.response_source || query.agent || 'N/A')}</span>
                ${query.from_cache ? '<span class="badge badge-cache">Cached</span>' : ''}
                <span class="query-time">${formatDate(query.created_at)}</span>
            </div>
        `;
        list.appendChild(item);
    });

    container.appendChild(list);
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function createStatCard(label, value, icon) {
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.innerHTML = `
        <div class="stat-icon">${icon}</div>
        <div class="stat-value">${escapeHtml(String(value))}</div>
        <div class="stat-label">${escapeHtml(label)}</div>
    `;
    return card;
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + '...';
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function debounce(fn, delay) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), delay);
    };
}

// ============================================================================
// INSIGHTS VIEW (Intelligence Hub)
// ============================================================================

/**
 * Render the Insights Dashboard view
 * Shows AI-extracted knowledge, patterns, and recommendations from your conversations
 */
async function renderInsightsView(container) {
    container.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'view-header';
    header.innerHTML = `
        <h2>Insights Dashboard</h2>
        <p class="view-subtitle">AI-extracted knowledge and patterns from your conversations</p>
    `;
    container.appendChild(header);

    // Analysis input
    const analyzeSection = document.createElement('div');
    analyzeSection.className = 'analyze-section';
    analyzeSection.innerHTML = `
        <div class="analyze-input-group">
            <input type="text" id="analyze-query" class="analyze-input"
                   placeholder="Ask about your knowledge: 'What have I learned about [topic]?'">
            <button id="analyze-btn" class="btn-primary">Analyze</button>
        </div>
    `;
    container.appendChild(analyzeSection);

    // Controls
    const controls = document.createElement('div');
    controls.className = 'insights-controls';
    controls.innerHTML = `
        <select id="insights-period">
            <option value="7" selected>Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
        </select>
        <button id="refresh-insights" class="btn-secondary">Refresh</button>
        <button id="generate-insights" class="btn-primary">Generate Insights</button>
    `;
    container.appendChild(controls);

    // Dashboard content
    const dashboard = document.createElement('div');
    dashboard.id = 'insights-dashboard';
    dashboard.className = 'insights-dashboard';
    dashboard.innerHTML = '<div class="loading">Loading insights...</div>';
    container.appendChild(dashboard);

    // Analysis results container (hidden initially)
    const analysisResults = document.createElement('div');
    analysisResults.id = 'analysis-results';
    analysisResults.className = 'analysis-results hidden';
    container.appendChild(analysisResults);

    // Load Knowledge Intelligence view
    await loadKnowledgePoweredInsights(dashboard, 30);

    // Event listeners
    document.getElementById('insights-period').addEventListener('change', (e) => {
        loadKnowledgePoweredInsights(dashboard, parseInt(e.target.value));
    });
    document.getElementById('refresh-insights').addEventListener('click', () => {
        const days = parseInt(document.getElementById('insights-period').value);
        loadKnowledgePoweredInsights(dashboard, days);
    });
    document.getElementById('generate-insights').addEventListener('click', () => {
        const days = parseInt(document.getElementById('insights-period').value);
        generateInsightsOnDemand(dashboard, days);
    });
    document.getElementById('analyze-btn').addEventListener('click', () => performAnalysis());
    document.getElementById('analyze-query').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performAnalysis();
    });
}

async function generateInsightsOnDemand(dashboard, days) {
    const generateBtn = document.getElementById('generate-insights');
    const originalText = generateBtn.textContent;

    generateBtn.textContent = 'Generating...';
    generateBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/v2/insights/generate?period_days=${days}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.status === 'success') {
            // Show success message
            const successMsg = document.createElement('div');
            successMsg.className = 'success-message';
            successMsg.innerHTML = `
                <strong>Insights Generated!</strong><br>
                ${result.data.insights_generated} insights from ${result.data.topics_analyzed} topics<br>
                Knowledge: ${result.data.key_stats?.knowledge_items || 0} items, ${result.data.key_stats?.facts_extracted || 0} facts
            `;
            dashboard.insertBefore(successMsg, dashboard.firstChild);

            // Remove after 5 seconds
            setTimeout(() => successMsg.remove(), 5000);

            // Reload the insights summary
            await loadInsightsSummary(dashboard, days);
        } else {
            throw new Error(result.detail || 'Generation failed');
        }

    } catch (error) {
        console.error('Failed to generate insights:', error);
        alert(`Failed to generate insights: ${error.message}`);
    } finally {
        generateBtn.textContent = originalText;
        generateBtn.disabled = false;
    }
}

async function loadInsightsSummary(container, days) {
    container.innerHTML = '<div class="loading">Loading insights...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/v2/insights/summary?period_days=${days}&scope=user`);
        const result = await response.json();
        const data = result.data || result;

        container.innerHTML = '';

        // Key Stats Section
        const statsSection = document.createElement('div');
        statsSection.className = 'insights-section';
        statsSection.innerHTML = '<h3>This Week at a Glance</h3>';
        renderInsightsStats(statsSection, data.key_stats || {});
        container.appendChild(statsSection);

        // Top Topics Section
        const topicsSection = document.createElement('div');
        topicsSection.className = 'insights-section';
        topicsSection.innerHTML = '<h3>Top Topics</h3>';
        renderTopTopics(topicsSection, data.top_topics || []);
        container.appendChild(topicsSection);

        // Insights Section
        const insightsSection = document.createElement('div');
        insightsSection.className = 'insights-section';
        insightsSection.innerHTML = '<h3>Key Insights</h3>';
        renderInsightsList(insightsSection, data.insights || []);
        container.appendChild(insightsSection);

        // Recommendations Section
        if (data.recommendations?.length) {
            const recsSection = document.createElement('div');
            recsSection.className = 'insights-section';
            recsSection.innerHTML = '<h3>Recommendations</h3>';
            renderRecommendations(recsSection, data.recommendations);
            container.appendChild(recsSection);
        }

    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load insights: ${error.message}</div>`;
    }
}

function renderInsightsStats(container, stats) {
    const grid = document.createElement('div');
    grid.className = 'stat-grid';

    grid.appendChild(createStatCard('Total Queries', (stats.total_queries || 0).toLocaleString(), '📊'));
    grid.appendChild(createStatCard('Unique Topics', (stats.unique_topics || 0).toLocaleString(), '🏷️'));
    grid.appendChild(createStatCard('Knowledge Items', (stats.knowledge_items || 0).toLocaleString(), '📚'));
    grid.appendChild(createStatCard('Facts Extracted', (stats.facts_extracted || 0).toLocaleString(), '💡'));
    grid.appendChild(createStatCard('Total Cost', `$${(stats.total_cost_usd || 0).toFixed(2)}`, '💰'));
    grid.appendChild(createStatCard('Top Agent', stats.top_agent || 'N/A', '🤖'));

    container.appendChild(grid);
}

function renderTopTopics(container, topics) {
    if (!topics.length) {
        container.innerHTML += '<div class="empty-state">No topics found for this period</div>';
        return;
    }

    const list = document.createElement('div');
    list.className = 'topics-list';

    topics.slice(0, 10).forEach((topic, index) => {
        const item = document.createElement('div');
        item.className = 'topic-item';

        const trendIcon = {
            'up': '↑',
            'down': '↓',
            'stable': '→',
            'new': '★'
        }[topic.trend] || '→';

        const trendClass = {
            'up': 'trend-up',
            'down': 'trend-down',
            'stable': 'trend-stable',
            'new': 'trend-new'
        }[topic.trend] || '';

        item.innerHTML = `
            <span class="topic-rank">#${index + 1}</span>
            <span class="topic-name">${escapeHtml(topic.topic)}</span>
            <span class="topic-count">${topic.count}</span>
            <span class="topic-trend ${trendClass}">${trendIcon} ${Math.abs(topic.trend_percent || 0).toFixed(0)}%</span>
        `;
        list.appendChild(item);
    });

    container.appendChild(list);
}

function renderInsightsList(container, insights) {
    if (!insights.length) {
        container.innerHTML += '<div class="empty-state">No insights detected yet. Keep using ACMS!</div>';
        return;
    }

    const list = document.createElement('div');
    list.className = 'insights-list';

    insights.forEach(insight => {
        const card = document.createElement('div');
        card.className = `insight-card insight-${insight.type || 'general'}`;

        const icon = {
            'emerging_theme': '🔥',
            'knowledge_gap': '⚠️',
            'cost_trend': '💰',
            'productivity_trend': '📈',
            'topic_shift': '🔄',
            'model_preference': '🤖'
        }[insight.type] || '💡';

        card.innerHTML = `
            <div class="insight-header">
                <span class="insight-icon">${icon}</span>
                <span class="insight-title">${escapeHtml(insight.title)}</span>
            </div>
            <div class="insight-description">${escapeHtml(insight.description)}</div>
            <div class="insight-confidence">Confidence: ${((insight.confidence || 0) * 100).toFixed(0)}%</div>
        `;
        list.appendChild(card);
    });

    container.appendChild(list);
}

function renderRecommendations(container, recommendations) {
    const list = document.createElement('div');
    list.className = 'recommendations-list';

    recommendations.forEach(rec => {
        const item = document.createElement('div');
        item.className = `recommendation-item priority-${rec.priority}`;

        const priorityIcon = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }[rec.priority] || '⚪';

        item.innerHTML = `
            <span class="rec-priority">${priorityIcon}</span>
            <div class="rec-content">
                <div class="rec-action">${escapeHtml(rec.action)}</div>
                <div class="rec-context">${escapeHtml(rec.context)}</div>
            </div>
        `;
        list.appendChild(item);
    });

    container.appendChild(list);
}

// ============================================================================
// KNOWLEDGE-POWERED INSIGHTS (Dec 2025)
// ============================================================================

/**
 * Load and render Knowledge-Powered Insights
 * Shows deep analysis: expertise centers, learning patterns, attention signals
 */
async function loadKnowledgePoweredInsights(container, days) {
    container.innerHTML = '<div class="loading">Loading knowledge intelligence...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/v2/insights/knowledge?period_days=${days}`);
        const result = await response.json();
        const data = result.data || result;

        container.innerHTML = '';

        // Executive Summary Section
        const summarySection = document.createElement('div');
        summarySection.className = 'insights-section executive-summary';
        summarySection.innerHTML = '<h3>Executive Summary</h3>';
        renderExecutiveSummary(summarySection, data.executive_summary || {});
        container.appendChild(summarySection);

        // Knowledge Velocity Section
        const velocitySection = document.createElement('div');
        velocitySection.className = 'insights-section';
        velocitySection.innerHTML = '<h3>Knowledge Velocity</h3>';
        renderKnowledgeVelocity(velocitySection, data.knowledge_velocity || {});
        container.appendChild(velocitySection);

        // Expertise Centers Section (top 6)
        if (data.expertise_centers?.length) {
            const expertiseSection = document.createElement('div');
            expertiseSection.className = 'insights-section';
            expertiseSection.innerHTML = '<h3>Expertise Centers</h3>';
            renderExpertiseCenters(expertiseSection, data.expertise_centers.slice(0, 6));
            container.appendChild(expertiseSection);
        }

        // Attention Signals Section
        if (data.attention_signals) {
            const signalsSection = document.createElement('div');
            signalsSection.className = 'insights-section';
            signalsSection.innerHTML = '<h3>Attention Signals</h3>';
            renderAttentionSignals(signalsSection, data.attention_signals);
            container.appendChild(signalsSection);
        }

        // Key Facts Sample Section
        if (data.key_facts && Object.keys(data.key_facts).length) {
            const factsSection = document.createElement('div');
            factsSection.className = 'insights-section';
            factsSection.innerHTML = '<h3>Key Facts by Domain</h3>';
            renderKeyFacts(factsSection, data.key_facts);
            container.appendChild(factsSection);
        }

        // Recommendations Section
        if (data.recommendations?.length) {
            const recsSection = document.createElement('div');
            recsSection.className = 'insights-section';
            recsSection.innerHTML = '<h3>Actionable Recommendations</h3>';
            renderKnowledgeRecommendations(recsSection, data.recommendations);
            container.appendChild(recsSection);
        }

    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load knowledge insights: ${error.message}</div>`;
    }
}

function renderExecutiveSummary(container, summary) {
    const card = document.createElement('div');
    card.className = 'executive-summary-card';

    card.innerHTML = `
        <div class="summary-headline">${escapeHtml(summary.headline || 'No data')}</div>
        <div class="summary-stats">
            <div class="summary-stat">
                <span class="stat-label">Top Expertise</span>
                <span class="stat-value">${escapeHtml(summary.top_expertise || 'N/A')}</span>
            </div>
            <div class="summary-stat">
                <span class="stat-label">Domains Covered</span>
                <span class="stat-value">${summary.domains_covered || 0}</span>
            </div>
            <div class="summary-stat">
                <span class="stat-label">Learning Focus</span>
                <span class="stat-value">${escapeHtml(summary.learning_focus || 'N/A')}</span>
            </div>
            <div class="summary-stat">
                <span class="stat-label">Needs Attention</span>
                <span class="stat-value ${summary.attention_needed > 0 ? 'warning' : ''}">${summary.attention_needed || 0}</span>
            </div>
        </div>
    `;
    container.appendChild(card);
}

function renderKnowledgeVelocity(container, velocity) {
    const grid = document.createElement('div');
    grid.className = 'stat-grid';

    grid.appendChild(createStatCard('Knowledge Items', velocity.total_items || 0, '📚'));
    grid.appendChild(createStatCard('Facts Extracted', velocity.total_facts || 0, '💡'));
    grid.appendChild(createStatCard('Domains', velocity.domains_covered || 0, '🏷️'));
    grid.appendChild(createStatCard('Facts/Item Avg', velocity.facts_per_item_avg || 0, '📊'));

    container.appendChild(grid);
}

function renderExpertiseCenters(container, centers) {
    const grid = document.createElement('div');
    grid.className = 'expertise-grid';

    centers.forEach(center => {
        const card = document.createElement('div');
        card.className = `expertise-card depth-${center.depth_level} clickable`;
        card.style.cursor = 'pointer';
        card.title = `Click to view knowledge in ${center.domain}`;

        const depthIcon = {
            'deep': '🟢',
            'growing': '🟡',
            'shallow': '🔴'
        }[center.depth_level] || '⚪';

        card.innerHTML = `
            <div class="expertise-header">
                <span class="depth-indicator">${depthIcon}</span>
                <span class="expertise-domain">${escapeHtml(center.domain)}</span>
                <span class="nav-hint">→</span>
            </div>
            <div class="expertise-stats">
                <span class="stat">${center.item_count} items</span>
                <span class="stat">${center.fact_count} facts</span>
                <span class="badge badge-depth">${center.depth_level}</span>
            </div>
            <div class="expertise-topics">
                ${center.topics.slice(0, 3).map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('')}
            </div>
            ${center.sample_insight ? `<div class="sample-insight">"${escapeHtml(truncateText(center.sample_insight, 100))}"</div>` : ''}
        `;

        // Click to navigate to Knowledge Base filtered by domain
        card.addEventListener('click', () => {
            if (typeof window.navigateToKnowledgeWithFilter === 'function') {
                window.navigateToKnowledgeWithFilter({ domain: center.domain });
            }
        });

        grid.appendChild(card);
    });

    container.appendChild(grid);
}

function renderLearningPatterns(container, patterns) {
    const chartContainer = document.createElement('div');
    chartContainer.className = 'learning-patterns-chart';

    const patternOrder = ['building', 'learning', 'debugging', 'configuring', 'investing'];
    const patternIcons = {
        'building': '🔨',
        'learning': '📖',
        'debugging': '🐛',
        'configuring': '⚙️',
        'investing': '📈'
    };
    const patternColors = {
        'building': '#4CAF50',
        'learning': '#2196F3',
        'debugging': '#FF9800',
        'configuring': '#9C27B0',
        'investing': '#00BCD4'
    };

    patternOrder.forEach(key => {
        const pattern = patterns[key];
        if (!pattern || pattern.count === 0) return;

        const bar = document.createElement('div');
        bar.className = 'pattern-bar';
        bar.innerHTML = `
            <div class="pattern-label">
                <span class="pattern-icon">${patternIcons[key] || '📊'}</span>
                <span class="pattern-name">${key.charAt(0).toUpperCase() + key.slice(1)}</span>
            </div>
            <div class="pattern-track">
                <div class="pattern-fill" style="width: ${pattern.percentage}%; background: ${patternColors[key] || '#666'}"></div>
            </div>
            <div class="pattern-value">${pattern.percentage}% (${pattern.count})</div>
        `;
        chartContainer.appendChild(bar);
    });

    container.appendChild(chartContainer);
}

function renderCrossDomainConnections(container, connections) {
    const list = document.createElement('div');
    list.className = 'connections-list';

    connections.forEach(conn => {
        const item = document.createElement('div');
        item.className = 'connection-item';
        item.innerHTML = `
            <div class="connection-topic">
                <span class="connection-icon">🔗</span>
                <span class="topic-name">${escapeHtml(conn.topic)}</span>
                <span class="connection-count">${conn.connection_count} domains</span>
            </div>
            <div class="connection-domains">
                ${conn.domains.slice(0, 4).map(d => `<span class="domain-tag">${escapeHtml(d)}</span>`).join('')}
            </div>
        `;
        list.appendChild(item);
    });

    container.appendChild(list);
}

function renderAttentionSignals(container, signals) {
    const grid = document.createElement('div');
    grid.className = 'attention-signals-grid';

    // Deep Expertise (green - good)
    if (signals.deep_expertise?.length) {
        const section = document.createElement('div');
        section.className = 'signal-section signal-deep';
        section.innerHTML = `
            <h4>Deep Expertise (${signals.deep_expertise.length})</h4>
            <div class="signal-list">
                ${signals.deep_expertise.slice(0, 3).map(s => `
                    <div class="signal-item">
                        <span class="signal-icon">🟢</span>
                        <span class="signal-domain">${escapeHtml(s.domain)}</span>
                        <span class="signal-reason">${escapeHtml(s.reason)}</span>
                    </div>
                `).join('')}
            </div>
        `;
        grid.appendChild(section);
    }

    // Growing Areas (yellow - progress)
    if (signals.growing_areas?.length) {
        const section = document.createElement('div');
        section.className = 'signal-section signal-growing';
        section.innerHTML = `
            <h4>Growing Areas (${signals.growing_areas.length})</h4>
            <div class="signal-list">
                ${signals.growing_areas.slice(0, 3).map(s => `
                    <div class="signal-item">
                        <span class="signal-icon">🟡</span>
                        <span class="signal-domain">${escapeHtml(s.domain)}</span>
                        <span class="signal-reason">${escapeHtml(s.reason)}</span>
                    </div>
                `).join('')}
            </div>
        `;
        grid.appendChild(section);
    }

    // Needs Attention (red - warning)
    if (signals.needs_attention?.length) {
        const section = document.createElement('div');
        section.className = 'signal-section signal-attention';
        section.innerHTML = `
            <h4>Needs Attention (${signals.needs_attention.length})</h4>
            <div class="signal-list">
                ${signals.needs_attention.map(s => `
                    <div class="signal-item">
                        <span class="signal-icon">🔴</span>
                        <span class="signal-domain">${escapeHtml(s.domain)}</span>
                        <span class="signal-reason">${escapeHtml(s.reason)}</span>
                    </div>
                `).join('')}
            </div>
        `;
        grid.appendChild(section);
    }

    container.appendChild(grid);
}

function renderKeyFacts(container, facts) {
    const grid = document.createElement('div');
    grid.className = 'key-facts-grid';

    // Show top 4 domains with most facts
    const sortedDomains = Object.entries(facts)
        .sort((a, b) => b[1].length - a[1].length)
        .slice(0, 4);

    sortedDomains.forEach(([domain, domainFacts]) => {
        const card = document.createElement('div');
        card.className = 'facts-card';
        card.innerHTML = `
            <div class="facts-domain">${escapeHtml(domain)}</div>
            <ul class="facts-list">
                ${domainFacts.slice(0, 2).map(f => `<li>${escapeHtml(truncateText(f, 80))}</li>`).join('')}
            </ul>
        `;
        grid.appendChild(card);
    });

    container.appendChild(grid);
}

function renderKnowledgeRecommendations(container, recommendations) {
    const list = document.createElement('div');
    list.className = 'knowledge-recommendations-list';

    recommendations.forEach(rec => {
        const item = document.createElement('div');
        item.className = `recommendation-item priority-${rec.priority}`;

        const priorityIcon = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }[rec.priority] || '⚪';

        item.innerHTML = `
            <span class="rec-priority">${priorityIcon}</span>
            <div class="rec-content">
                <div class="rec-action">${escapeHtml(rec.action)}</div>
                <div class="rec-context">${escapeHtml(rec.context)}</div>
                ${rec.domain ? `<span class="rec-domain badge">${escapeHtml(rec.domain)}</span>` : ''}
            </div>
        `;
        list.appendChild(item);
    });

    container.appendChild(list);
}

async function performAnalysis() {
    const query = document.getElementById('analyze-query').value.trim();
    if (!query) return;

    const resultsContainer = document.getElementById('analysis-results');
    resultsContainer.classList.remove('hidden');
    resultsContainer.innerHTML = '<div class="loading">Analyzing...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/v2/insights/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, period_days: 30 })
        });

        const result = await response.json();
        const data = result.data || result;

        resultsContainer.innerHTML = '';

        const analysisCard = document.createElement('div');
        analysisCard.className = 'analysis-card';

        analysisCard.innerHTML = `
            <div class="analysis-header">
                <h3>Analysis: ${escapeHtml(data.topic || data.query)}</h3>
                <span class="analysis-confidence">Confidence: ${((data.confidence || 0) * 100).toFixed(0)}%</span>
            </div>
            <div class="analysis-text">${escapeHtml(data.analysis || 'No analysis available')}</div>
        `;

        if (data.key_learnings?.length) {
            const learnings = document.createElement('div');
            learnings.className = 'analysis-section';
            learnings.innerHTML = `
                <h4>Key Learnings</h4>
                <ul>${data.key_learnings.map(l => `<li>${escapeHtml(l)}</li>`).join('')}</ul>
            `;
            analysisCard.appendChild(learnings);
        }

        if (data.knowledge_gaps?.length) {
            const gaps = document.createElement('div');
            gaps.className = 'analysis-section warning';
            gaps.innerHTML = `
                <h4>Knowledge Gaps</h4>
                <ul>${data.knowledge_gaps.map(g => `<li>${escapeHtml(g)}</li>`).join('')}</ul>
            `;
            analysisCard.appendChild(gaps);
        }

        if (data.related_topics?.length) {
            const related = document.createElement('div');
            related.className = 'analysis-section';
            related.innerHTML = `
                <h4>Related Topics</h4>
                <div class="related-topics">${data.related_topics.map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('')}</div>
            `;
            analysisCard.appendChild(related);
        }

        resultsContainer.appendChild(analysisCard);

    } catch (error) {
        resultsContainer.innerHTML = `<div class="error">Analysis failed: ${error.message}</div>`;
    }
}

// ============================================================================
// REPORTS VIEW (Intelligence Hub)
// ============================================================================

/**
 * Render the Reports view - Full Visual Redesign
 * Generate and view intelligence reports with modern UI
 */
async function renderReportsView(container) {
    container.innerHTML = '';

    // Create scrollable content wrapper
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'reports-container';

    // Header with gradient accent
    const header = document.createElement('div');
    header.className = 'view-header reports-header';
    header.innerHTML = `
        <div class="reports-header-content">
            <div class="reports-header-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
            </div>
            <div>
                <h2>Intelligence Reports</h2>
                <p class="view-subtitle">AI-powered executive summaries and insights from your knowledge base</p>
            </div>
        </div>
    `;
    contentWrapper.appendChild(header);

    // Hero Generate Section - Modern Card Design
    const generateSection = document.createElement('div');
    generateSection.className = 'report-hero-generate';
    generateSection.innerHTML = `
        <div class="report-hero-card">
            <div class="report-hero-left">
                <div class="report-hero-icon-wrapper">
                    <div class="report-hero-icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 4v16m8-8H4"/>
                        </svg>
                    </div>
                </div>
                <div class="report-hero-text">
                    <h3>Generate New Report</h3>
                    <p>Create a comprehensive analysis of your AI usage, topics explored, and knowledge accumulated</p>
                </div>
            </div>
            <div class="report-hero-form">
                <div class="report-form-row">
                    <div class="report-form-group">
                        <label for="report-type">Report Type</label>
                        <select id="report-type" class="report-select">
                            <option value="weekly" selected>Weekly Summary</option>
                            <option value="monthly">Monthly Overview</option>
                        </select>
                    </div>
                    <div class="report-form-group">
                        <label for="report-scope">Scope</label>
                        <select id="report-scope" class="report-select">
                            <option value="user" selected>Personal</option>
                            <option value="org">Organization</option>
                        </select>
                    </div>
                    <div class="report-form-group">
                        <label for="report-format">Format</label>
                        <select id="report-format" class="report-select">
                            <option value="json" selected>View Online</option>
                            <option value="markdown">Markdown</option>
                            <option value="html">HTML</option>
                        </select>
                    </div>
                </div>
                <button id="generate-report-btn" class="report-generate-btn">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    Generate Report
                </button>
            </div>
        </div>
    `;
    contentWrapper.appendChild(generateSection);

    // Generated Report Display (Modal-style)
    const reportDisplay = document.createElement('div');
    reportDisplay.id = 'report-display';
    reportDisplay.className = 'report-display-modern hidden';
    contentWrapper.appendChild(reportDisplay);

    // Previous Reports Section with visual cards
    const previousSection = document.createElement('div');
    previousSection.className = 'reports-history-section';
    previousSection.innerHTML = `
        <div class="reports-history-header">
            <h3>Report History</h3>
            <span class="reports-history-subtitle">Your previously generated intelligence reports</span>
        </div>
    `;

    const reportsList = document.createElement('div');
    reportsList.id = 'reports-list';
    reportsList.className = 'reports-grid';
    reportsList.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div></div>';
    previousSection.appendChild(reportsList);
    contentWrapper.appendChild(previousSection);

    container.appendChild(contentWrapper);

    // Load previous reports
    await loadReportsList(reportsList);

    // Event listeners
    document.getElementById('generate-report-btn').addEventListener('click', () => generateReport());
}

async function loadReportsList(container) {
    try {
        const response = await fetch(`${API_BASE}/api/v2/reports?limit=10`);
        const result = await response.json();
        const reports = result.data?.reports || [];

        container.innerHTML = '';

        if (!reports.length) {
            container.innerHTML = `
                <div class="reports-empty-state">
                    <div class="empty-state-icon">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                            <path d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                    </div>
                    <h4>No Reports Yet</h4>
                    <p>Generate your first intelligence report to see AI usage patterns, topic trends, and actionable insights.</p>
                </div>
            `;
            return;
        }

        reports.forEach((report, index) => {
            const card = document.createElement('div');
            card.className = 'report-history-card';
            card.setAttribute('data-report-id', report.report_id);

            // Determine type icon and color
            const isWeekly = report.report_type === 'weekly';
            const typeIcon = isWeekly
                ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
                : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';

            const typeClass = isWeekly ? 'type-weekly' : 'type-monthly';

            // Format date nicely
            const dateStr = report.created_at ? formatDateRelative(report.created_at) : 'Unknown date';
            const periodStr = report.period_start && report.period_end
                ? `${formatDateShort(report.period_start)} - ${formatDateShort(report.period_end)}`
                : 'Custom period';

            // Extract preview stats if available
            const stats = report.stats || {};
            const queriesCount = stats.total_queries || report.total_queries || '—';
            const topicsCount = stats.unique_topics || report.unique_topics || '—';

            card.innerHTML = `
                <div class="report-card-accent ${typeClass}"></div>
                <div class="report-card-content">
                    <div class="report-card-top">
                        <div class="report-card-type ${typeClass}">
                            ${typeIcon}
                            <span>${escapeHtml(report.report_type || 'Report')}</span>
                        </div>
                        <div class="report-card-date">${dateStr}</div>
                    </div>
                    <div class="report-card-title">${escapeHtml(report.title || 'Intelligence Report')}</div>
                    <div class="report-card-period">${periodStr}</div>
                    <div class="report-card-preview">
                        <div class="preview-stat">
                            <span class="preview-value">${queriesCount}</span>
                            <span class="preview-label">Queries</span>
                        </div>
                        <div class="preview-stat">
                            <span class="preview-value">${topicsCount}</span>
                            <span class="preview-label">Topics</span>
                        </div>
                    </div>
                    <button class="report-view-btn" data-id="${report.report_id}">
                        View Full Report
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M5 12h14M12 5l7 7-7 7"/>
                        </svg>
                    </button>
                </div>
            `;

            card.querySelector('.report-view-btn').addEventListener('click', () => {
                viewReport(report.report_id);
            });

            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load reports: ${error.message}</div>`;
    }
}

// Helper: Format date as relative (e.g., "2 days ago")
function formatDateRelative(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return formatDateShort(dateStr);
}

// Helper: Format date as short (e.g., "Dec 15")
function formatDateShort(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

async function generateReport() {
    const reportType = document.getElementById('report-type').value;
    const scope = document.getElementById('report-scope').value;
    const format = document.getElementById('report-format').value;

    const displayContainer = document.getElementById('report-display');
    displayContainer.classList.remove('hidden');

    // Show animated loading state
    displayContainer.innerHTML = `
        <div class="report-generating">
            <div class="generating-animation">
                <div class="generating-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
                        <circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="32"/>
                    </svg>
                </div>
                <div class="generating-bars">
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                </div>
            </div>
            <h3>Generating Your Report</h3>
            <p>Analyzing usage patterns, extracting insights, and compiling recommendations...</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/api/v2/reports/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                report_type: reportType,
                scope: scope,
                format: format,
                include_recommendations: true
            })
        });

        if (format === 'markdown' || format === 'html') {
            // Download file
            const content = await response.text();
            const blob = new Blob([content], { type: format === 'markdown' ? 'text/markdown' : 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `acms-report-${new Date().toISOString().split('T')[0]}.${format === 'markdown' ? 'md' : 'html'}`;
            a.click();
            URL.revokeObjectURL(url);
            displayContainer.innerHTML = `
                <div class="report-success">
                    <div class="success-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                            <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                    </div>
                    <h3>Report Downloaded!</h3>
                    <p>Your ${format.toUpperCase()} report has been saved to your downloads folder.</p>
                    <button class="btn-secondary" onclick="document.getElementById('report-display').classList.add('hidden')">Close</button>
                </div>
            `;
        } else {
            const result = await response.json();
            const data = result.data || result;
            renderReportDisplay(displayContainer, data);
        }

        // Refresh reports list
        await loadReportsList(document.getElementById('reports-list'));

    } catch (error) {
        displayContainer.innerHTML = `
            <div class="report-error">
                <div class="error-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="15" y1="9" x2="9" y2="15"/>
                        <line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                </div>
                <h3>Generation Failed</h3>
                <p>${escapeHtml(error.message)}</p>
                <button class="btn-secondary" onclick="document.getElementById('report-display').classList.add('hidden')">Close</button>
            </div>
        `;
    }
}

async function viewReport(reportId) {
    const displayContainer = document.getElementById('report-display');
    displayContainer.classList.remove('hidden');

    // Show loading state
    displayContainer.innerHTML = `
        <div class="report-loading">
            <div class="loading-spinner"></div>
            <p>Loading report...</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/api/v2/reports/${reportId}`);
        const result = await response.json();
        const data = result.data || result;

        renderReportDisplay(displayContainer, data);

    } catch (error) {
        displayContainer.innerHTML = `
            <div class="report-error">
                <div class="error-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="15" y1="9" x2="9" y2="15"/>
                        <line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                </div>
                <h3>Failed to Load Report</h3>
                <p>${escapeHtml(error.message)}</p>
                <button class="btn-secondary" onclick="document.getElementById('report-display').classList.add('hidden')">Close</button>
            </div>
        `;
    }
}

function renderReportDisplay(container, report) {
    container.innerHTML = '';

    const reportEl = document.createElement('div');
    reportEl.className = 'report-modern';

    // Close button (top right)
    const closeBtn = document.createElement('button');
    closeBtn.className = 'report-close-x';
    closeBtn.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
    `;
    closeBtn.addEventListener('click', () => container.classList.add('hidden'));
    reportEl.appendChild(closeBtn);

    // Hero Header
    const header = document.createElement('div');
    header.className = 'report-hero-header';
    const periodStart = report.period?.start ? formatDateShort(report.period.start) : 'N/A';
    const periodEnd = report.period?.end ? formatDateShort(report.period.end) : 'N/A';
    const typeLabel = report.type === 'weekly' ? 'Weekly Report' : report.type === 'monthly' ? 'Monthly Report' : 'Report';

    header.innerHTML = `
        <div class="report-hero-badge">${typeLabel}</div>
        <h1 class="report-hero-title">${escapeHtml(report.summary?.headline || 'Intelligence Report')}</h1>
        <div class="report-hero-period">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            ${periodStart} — ${periodEnd}
        </div>
    `;
    reportEl.appendChild(header);

    // Hero Stats Grid
    if (report.summary?.key_stats) {
        const stats = report.summary.key_stats;
        const heroStats = document.createElement('div');
        heroStats.className = 'report-hero-stats';

        const statItems = [];
        if (stats.total_queries !== undefined) {
            statItems.push({ value: stats.total_queries, label: 'Total Queries', icon: 'chat', color: '#4CAF50' });
        }
        if (stats.unique_topics !== undefined) {
            statItems.push({ value: stats.unique_topics, label: 'Unique Topics', icon: 'tag', color: '#2196F3' });
        }
        if (stats.knowledge_items !== undefined) {
            statItems.push({ value: stats.knowledge_items, label: 'Knowledge Items', icon: 'book', color: '#9C27B0' });
        }
        if (stats.facts_extracted !== undefined) {
            statItems.push({ value: stats.facts_extracted, label: 'Facts Extracted', icon: 'lightbulb', color: '#FF9800' });
        }
        if (stats.total_cost_usd !== undefined) {
            statItems.push({ value: `$${stats.total_cost_usd.toFixed(2)}`, label: 'Total Cost', icon: 'dollar', color: '#00BCD4' });
        }

        statItems.forEach(stat => {
            heroStats.appendChild(createHeroStatCard(stat.value, stat.label, stat.icon, stat.color));
        });

        reportEl.appendChild(heroStats);
    }

    // Two-column layout for charts
    const chartsRow = document.createElement('div');
    chartsRow.className = 'report-charts-row';

    // Top Topics - Bar Chart
    if (report.top_topics?.length) {
        const topicsSection = document.createElement('div');
        topicsSection.className = 'report-chart-section';
        topicsSection.innerHTML = `
            <div class="chart-header">
                <h3>Top Topics</h3>
                <span class="chart-subtitle">Most discussed subjects this period</span>
            </div>
        `;

        const chartContainer = document.createElement('div');
        chartContainer.className = 'topics-bar-chart';

        const maxCount = Math.max(...report.top_topics.map(t => t.count));
        const colors = ['#4CAF50', '#2196F3', '#9C27B0', '#FF9800', '#00BCD4', '#E91E63', '#795548', '#607D8B'];

        report.top_topics.slice(0, 8).forEach((topic, i) => {
            const percentage = (topic.count / maxCount) * 100;
            const trendIcon = topic.trend === 'up' ? '↑' : topic.trend === 'down' ? '↓' : '→';
            const trendClass = topic.trend === 'up' ? 'trend-up' : topic.trend === 'down' ? 'trend-down' : 'trend-stable';

            const bar = document.createElement('div');
            bar.className = 'topic-bar-item';
            bar.innerHTML = `
                <div class="topic-bar-label">
                    <span class="topic-rank">#${topic.rank || i + 1}</span>
                    <span class="topic-name">${escapeHtml(topic.topic)}</span>
                    <span class="topic-trend ${trendClass}">${trendIcon}</span>
                </div>
                <div class="topic-bar-track">
                    <div class="topic-bar-fill" style="width: ${percentage}%; background: ${colors[i % colors.length]}"></div>
                </div>
                <div class="topic-bar-value">${topic.count}</div>
            `;
            chartContainer.appendChild(bar);
        });

        topicsSection.appendChild(chartContainer);
        chartsRow.appendChild(topicsSection);
    }

    // Agent Breakdown - Donut Chart
    if (report.agent_breakdown && Object.keys(report.agent_breakdown).length) {
        const agentSection = document.createElement('div');
        agentSection.className = 'report-chart-section';
        agentSection.innerHTML = `
            <div class="chart-header">
                <h3>Agent Usage</h3>
                <span class="chart-subtitle">Distribution of AI model usage</span>
            </div>
        `;

        const chartContainer = document.createElement('div');
        chartContainer.className = 'agent-donut-container';

        // Create donut chart with CSS conic-gradient
        const agents = Object.entries(report.agent_breakdown);
        const total = agents.reduce((sum, [_, s]) => sum + (s.queries || 0), 0);
        const agentColors = {
            'claude': '#9C27B0',
            'chatgpt': '#10a37f',
            'gemini': '#4285f4',
            'default': '#607D8B'
        };

        let gradientStops = [];
        let currentPercent = 0;

        agents.forEach(([name, stats], i) => {
            const percent = total > 0 ? ((stats.queries || 0) / total) * 100 : 0;
            const color = agentColors[name.toLowerCase()] || agentColors.default;
            gradientStops.push(`${color} ${currentPercent}% ${currentPercent + percent}%`);
            currentPercent += percent;
        });

        const donutChart = document.createElement('div');
        donutChart.className = 'donut-chart';
        donutChart.style.background = `conic-gradient(${gradientStops.join(', ')})`;
        donutChart.innerHTML = `<div class="donut-hole"><span class="donut-total">${total}</span><span class="donut-label">queries</span></div>`;

        const legend = document.createElement('div');
        legend.className = 'donut-legend';

        agents.forEach(([name, stats]) => {
            const color = agentColors[name.toLowerCase()] || agentColors.default;
            const percent = total > 0 ? ((stats.queries || 0) / total * 100).toFixed(0) : 0;
            legend.innerHTML += `
                <div class="legend-item">
                    <span class="legend-color" style="background: ${color}"></span>
                    <span class="legend-name">${escapeHtml(name)}</span>
                    <span class="legend-value">${stats.queries || 0} (${percent}%)</span>
                </div>
            `;
        });

        chartContainer.appendChild(donutChart);
        chartContainer.appendChild(legend);
        agentSection.appendChild(chartContainer);
        chartsRow.appendChild(agentSection);
    }

    reportEl.appendChild(chartsRow);

    // Insights Section
    if (report.insights?.length) {
        const insightsSection = document.createElement('div');
        insightsSection.className = 'report-insights-section';
        insightsSection.innerHTML = `
            <div class="section-header">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="16" x2="12" y2="12"/>
                    <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
                <h3>Key Insights</h3>
            </div>
        `;

        const insightsGrid = document.createElement('div');
        insightsGrid.className = 'insights-grid';

        report.insights.forEach((insight, i) => {
            const card = document.createElement('div');
            card.className = 'insight-card-modern';
            card.innerHTML = `
                <div class="insight-number">${i + 1}</div>
                <div class="insight-content">
                    <h4>${escapeHtml(insight.title)}</h4>
                    <p>${escapeHtml(insight.description)}</p>
                </div>
            `;
            insightsGrid.appendChild(card);
        });

        insightsSection.appendChild(insightsGrid);
        reportEl.appendChild(insightsSection);
    }

    // Recommendations Section
    if (report.recommendations?.length) {
        const recsSection = document.createElement('div');
        recsSection.className = 'report-recommendations-section';
        recsSection.innerHTML = `
            <div class="section-header">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                <h3>Recommendations</h3>
            </div>
        `;

        const recsGrid = document.createElement('div');
        recsGrid.className = 'recommendations-list';

        const priorityIcons = {
            high: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
            medium: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
            low: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>'
        };

        report.recommendations.forEach(rec => {
            const priority = (rec.priority || 'medium').toLowerCase();
            const card = document.createElement('div');
            card.className = `recommendation-card priority-${priority}`;
            card.innerHTML = `
                <div class="rec-priority-badge priority-${priority}">
                    ${priorityIcons[priority] || priorityIcons.medium}
                    <span>${priority.toUpperCase()}</span>
                </div>
                <div class="rec-content">
                    <div class="rec-action">${escapeHtml(rec.action)}</div>
                    <div class="rec-context">${escapeHtml(rec.context)}</div>
                </div>
            `;
            recsGrid.appendChild(card);
        });

        recsSection.appendChild(recsGrid);
        reportEl.appendChild(recsSection);
    }

    container.appendChild(reportEl);
}

// Helper: Create hero stat card with icon
function createHeroStatCard(value, label, iconType, color) {
    const card = document.createElement('div');
    card.className = 'hero-stat-card';
    card.style.borderTopColor = color;

    const icons = {
        chat: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
        tag: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
        book: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
        lightbulb: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="9" y1="18" x2="15" y2="18"/><line x1="10" y1="22" x2="14" y2="22"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg>',
        dollar: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>'
    };

    card.innerHTML = `
        <div class="hero-stat-icon" style="color: ${color}">${icons[iconType] || icons.chat}</div>
        <div class="hero-stat-value">${value}</div>
        <div class="hero-stat-label">${label}</div>
    `;

    return card;
}

// ============================================================================
// KNOWLEDGE BASE VIEW (Dec 2025)
// ============================================================================

// Global filter state for cross-view navigation
let knowledgeViewFilters = {
    domain: null,
    topic: null,
    search: null
};

/**
 * Navigate to Knowledge view with filters
 * Call this from other views (like Insights) to filter Knowledge Base
 */
function navigateToKnowledgeWithFilter(filters = {}) {
    knowledgeViewFilters = { domain: null, topic: null, search: null, ...filters };

    // Trigger view switch via custom event
    const event = new CustomEvent('acms-navigate', {
        detail: { view: 'knowledge', filters: knowledgeViewFilters }
    });
    window.dispatchEvent(event);
}

// Make it available globally for cross-view navigation
if (typeof window !== 'undefined') {
    window.navigateToKnowledgeWithFilter = navigateToKnowledgeWithFilter;
}

/**
 * Render the Knowledge Base view
 * Shows extracted knowledge from ACMS_Knowledge_v2 (via Claude Desktop MCP)
 * @param {HTMLElement} container - Container element
 * @param {Object} initialFilters - Optional filters { domain, topic, search }
 */
async function renderKnowledgeBaseView(container, initialFilters = {}) {
    container.innerHTML = '';

    // Merge initial filters with global state
    const filters = { ...knowledgeViewFilters, ...initialFilters };

    // Header with optional filter indicator
    const header = document.createElement('div');
    header.className = 'view-header';

    let subtitle = 'Structured knowledge extracted from your Q&A history via Claude Desktop';
    let filterBadge = '';
    if (filters.domain) {
        subtitle = `Showing knowledge in domain:`;
        filterBadge = `<span class="filter-badge">${escapeHtml(filters.domain)}</span>
                       <button id="clear-domain-filter" class="btn-link">Clear filter</button>`;
    }

    header.innerHTML = `
        <h2>Knowledge Base</h2>
        <p class="view-subtitle">${subtitle} ${filterBadge}</p>
    `;
    container.appendChild(header);

    // Active Second Brain: Add tabs for All Knowledge vs Needs Review
    const tabsContainer = document.createElement('div');
    tabsContainer.className = 'knowledge-tabs';
    tabsContainer.innerHTML = `
        <button class="knowledge-tab active" data-tab="all">📚 All Knowledge</button>
        <button class="knowledge-tab" data-tab="review">⚠️ Needs Review</button>
        <button class="knowledge-tab" data-tab="verified">✓ Verified</button>
    `;
    container.appendChild(tabsContainer);

    // Tab click handlers
    tabsContainer.querySelectorAll('.knowledge-tab').forEach(tab => {
        tab.addEventListener('click', async () => {
            tabsContainer.querySelectorAll('.knowledge-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const tabType = tab.getAttribute('data-tab');
            const listSection = document.getElementById('knowledge-list');
            if (tabType === 'review') {
                await loadKnowledgeReviewQueue(listSection);
            } else if (tabType === 'verified') {
                await loadKnowledge(listSection, { ...filters, verified: true });
            } else {
                await loadKnowledge(listSection, filters);
            }
        });
    });

    // Content wrapper with padding
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'knowledge-content';

    // Stats section
    const statsSection = document.createElement('div');
    statsSection.className = 'knowledge-stats';
    statsSection.innerHTML = '<div class="loading">Loading knowledge statistics...</div>';
    contentWrapper.appendChild(statsSection);

    // Load stats
    let statsData = {};
    try {
        statsData = await fetch(`${API_BASE}/knowledge/stats`).then(r => r.json());
        renderKnowledgeStats(statsSection, statsData);
    } catch (error) {
        statsSection.innerHTML = `<div class="error">Failed to load stats: ${error.message}</div>`;
    }

    // Controls with domain filter
    const controls = document.createElement('div');
    controls.className = 'knowledge-controls';
    controls.innerHTML = `
        <input type="text" id="knowledge-search" class="knowledge-search" placeholder="Search knowledge..." value="${escapeHtml(filters.search || '')}">
        <select id="knowledge-filter-domain" class="knowledge-filter">
            <option value="">All Domains</option>
        </select>
        <select id="knowledge-filter-topic" class="knowledge-filter">
            <option value="">All Topics</option>
        </select>
        <button id="refresh-knowledge" class="btn-secondary">Refresh</button>
    `;
    contentWrapper.appendChild(controls);

    // Populate domain filter (use querySelector since element isn't in document yet)
    const domainSelect = controls.querySelector('#knowledge-filter-domain');
    if (domainSelect && statsData.top_domains) {
        statsData.top_domains.forEach(d => {
            const option = document.createElement('option');
            option.value = d.domain;
            option.textContent = `${d.domain} (${d.count})`;
            if (filters.domain === d.domain) option.selected = true;
            domainSelect.appendChild(option);
        });
    }

    // Knowledge list
    const listSection = document.createElement('div');
    listSection.id = 'knowledge-list';
    listSection.className = 'knowledge-list';
    listSection.innerHTML = '<div class="loading">Loading knowledge...</div>';
    contentWrapper.appendChild(listSection);

    container.appendChild(contentWrapper);

    // Load knowledge with filters
    await loadKnowledge(listSection, filters);

    // Setup event listeners
    document.getElementById('knowledge-search').addEventListener('input', debounce(() => reloadKnowledge(), 300));
    document.getElementById('knowledge-filter-domain')?.addEventListener('change', () => reloadKnowledge());
    document.getElementById('knowledge-filter-topic').addEventListener('change', () => reloadKnowledge());
    document.getElementById('refresh-knowledge').addEventListener('click', () => reloadKnowledge());

    // Clear filter button
    const clearBtn = document.getElementById('clear-domain-filter');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            knowledgeViewFilters = { domain: null, topic: null, search: null };
            renderKnowledgeBaseView(container, {});
        });
    }
}

function renderKnowledgeStats(container, data) {
    container.innerHTML = '';

    const grid = document.createElement('div');
    grid.className = 'stat-grid';

    grid.appendChild(createStatCard('Total Knowledge', (data.total_knowledge || 0).toLocaleString(), '📚'));
    grid.appendChild(createStatCard('Total Facts', (data.total_facts || 0).toLocaleString(), '💡'));

    // Top topics
    const topTopics = (data.top_topics || []).slice(0, 3).map(t => t.topic).join(', ');
    grid.appendChild(createStatCard('Top Topics', topTopics || 'N/A', '🏷️'));

    // Top domains
    const topDomains = (data.top_domains || []).slice(0, 3).map(d => d.domain).join(', ');
    grid.appendChild(createStatCard('Top Domains', topDomains || 'N/A', '📁'));

    container.appendChild(grid);

    // Populate topic filter
    const topicSelect = document.getElementById('knowledge-filter-topic');
    if (topicSelect && data.top_topics) {
        data.top_topics.forEach(t => {
            const option = document.createElement('option');
            option.value = t.topic;
            option.textContent = `${t.topic} (${t.count})`;
            topicSelect.appendChild(option);
        });
    }
}

async function loadKnowledge(container, filters) {
    try {
        const params = new URLSearchParams({ limit: '50' });
        if (filters.domain) params.append('domain', filters.domain);
        if (filters.topic) params.append('topic', filters.topic);
        if (filters.search) params.append('search', filters.search);

        const response = await fetch(`${API_BASE}/knowledge?${params}`);
        const data = await response.json();

        container.innerHTML = '';

        const items = data.knowledge || [];

        if (!items.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No knowledge extracted yet.</p>
                    <p>Use Claude Desktop with the MCP server to extract knowledge from your Q&A history.</p>
                </div>
            `;
            return;
        }

        // Count display
        const countEl = document.createElement('div');
        countEl.className = 'knowledge-count';
        countEl.textContent = `Showing ${items.length} of ${data.total} knowledge items`;
        container.appendChild(countEl);

        // Render each item
        items.forEach(item => {
            const card = createKnowledgeCard(item);
            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load knowledge: ${error.message}</div>`;
    }
}

function reloadKnowledge() {
    const container = document.getElementById('knowledge-list');
    const domain = document.getElementById('knowledge-filter-domain')?.value;
    const topic = document.getElementById('knowledge-filter-topic')?.value;
    const search = document.getElementById('knowledge-search')?.value;
    loadKnowledge(container, { domain, topic, search });
}

/**
 * Active Second Brain: Load items needing review (low confidence, unverified)
 */
async function loadKnowledgeReviewQueue(container) {
    container.innerHTML = '<div class="loading">Loading items needing review...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/knowledge/review?limit=20`);
        const data = await response.json();

        container.innerHTML = '';

        const items = data.items || [];

        if (!items.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>🎉 No items need review!</p>
                    <p>All knowledge has been verified or has high confidence.</p>
                </div>
            `;
            return;
        }

        // Header
        const header = document.createElement('div');
        header.className = 'review-queue-header';
        header.innerHTML = `
            <p>Found <strong>${items.length}</strong> items with low confidence that need your review.</p>
            <p class="hint">Click Edit to correct, or Verify to confirm the knowledge is accurate.</p>
        `;
        container.appendChild(header);

        // Render each item with review actions
        items.forEach(item => {
            const card = createKnowledgeCard(item, true); // true = show review actions
            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load review queue: ${error.message}</div>`;
    }
}

/**
 * Active Second Brain: Verify knowledge without editing
 */
async function verifyKnowledge(knowledgeId) {
    try {
        const response = await fetch(`${API_BASE}/api/knowledge/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ knowledge_id: knowledgeId })
        });

        if (response.ok) {
            showToast('Knowledge verified!', 'success');
            // Refresh the list
            const activeTab = document.querySelector('.knowledge-tab.active');
            if (activeTab) activeTab.click();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to verify', 'error');
        }
    } catch (error) {
        showToast('Failed to verify: ' + error.message, 'error');
    }
}

/**
 * Active Second Brain: Show correction modal
 */
function showCorrectionModal(knowledgeId, currentContent) {
    // Remove existing modal
    const existingModal = document.getElementById('correction-modal');
    if (existingModal) existingModal.remove();

    const modal = document.createElement('div');
    modal.id = 'correction-modal';
    modal.className = 'feedback-modal'; // Reuse feedback modal styles
    modal.innerHTML = `
        <div class="feedback-modal-overlay"></div>
        <div class="feedback-modal-dialog" style="max-width: 600px;">
            <div class="feedback-modal-header">
                <h3>✏️ Correct Knowledge</h3>
                <button class="feedback-modal-close" id="close-correction-modal">×</button>
            </div>
            <div class="feedback-modal-body">
                <label class="feedback-modal-label">Current Content:</label>
                <div style="background: #1a1a1a; padding: 12px; border-radius: 6px; margin-bottom: 16px; max-height: 150px; overflow-y: auto; font-size: 13px; color: #888;">
                    ${escapeHtml(currentContent || 'No content')}
                </div>

                <label class="feedback-modal-label">Corrected Content:</label>
                <textarea id="correction-content" class="feedback-comment-input" rows="6" placeholder="Enter the corrected content...">${escapeHtml(currentContent || '')}</textarea>

                <label class="feedback-modal-label">Correction Type:</label>
                <select id="correction-type" style="width: 100%; padding: 10px; background: #252525; border: 1px solid #444; border-radius: 6px; color: #fff; margin-bottom: 12px;">
                    <option value="factual_error">Factual Error</option>
                    <option value="outdated">Outdated Information</option>
                    <option value="incomplete">Incomplete</option>
                    <option value="wrong_context">Wrong Context</option>
                    <option value="typo">Typo/Grammar</option>
                    <option value="clarification">Needs Clarification</option>
                </select>

                <label class="feedback-modal-label">Reason (optional):</label>
                <input type="text" id="correction-reason" class="feedback-comment-input" placeholder="Why is this correction needed?">
            </div>
            <div class="feedback-modal-footer">
                <button class="feedback-btn-secondary" id="cancel-correction">Cancel</button>
                <button class="feedback-btn-primary" id="submit-correction">Save Correction</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Event handlers
    document.getElementById('close-correction-modal').addEventListener('click', () => modal.remove());
    document.getElementById('cancel-correction').addEventListener('click', () => modal.remove());
    modal.querySelector('.feedback-modal-overlay').addEventListener('click', () => modal.remove());

    document.getElementById('submit-correction').addEventListener('click', async () => {
        const correctedContent = document.getElementById('correction-content').value.trim();
        const correctionType = document.getElementById('correction-type').value;
        const reason = document.getElementById('correction-reason').value.trim();

        if (!correctedContent) {
            showToast('Please enter corrected content', 'error');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/knowledge/correct`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    knowledge_id: knowledgeId,
                    corrected_content: correctedContent,
                    correction_type: correctionType,
                    reason: reason || null
                })
            });

            if (response.ok) {
                modal.remove();
                showToast('Correction saved!', 'success');
                // Refresh the list
                const activeTab = document.querySelector('.knowledge-tab.active');
                if (activeTab) activeTab.click();
            } else {
                const error = await response.json();
                showToast(error.detail || 'Failed to save correction', 'error');
            }
        } catch (error) {
            showToast('Failed to save: ' + error.message, 'error');
        }
    });
}

/**
 * Simple toast notification
 */
function showToast(message, type = 'success') {
    const existing = document.getElementById('acms-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'acms-toast';
    toast.className = `feedback-toast feedback-toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

function createKnowledgeCard(item, showReviewActions = false) {
    const card = document.createElement('div');
    card.className = 'knowledge-card clickable';
    card.setAttribute('data-knowledge-id', item.id || '');

    // Make card clickable to show full article
    card.addEventListener('click', () => {
        showKnowledgeModal(item.id);
    });

    // Header with topic and domain
    const header = document.createElement('div');
    header.className = 'knowledge-card-header';

    const topic = document.createElement('span');
    topic.className = 'badge badge-topic';
    topic.textContent = item.topic_cluster || 'Unknown Topic';
    header.appendChild(topic);

    const domain = document.createElement('span');
    domain.className = 'badge badge-domain';
    domain.textContent = item.problem_domain || 'Unknown';
    header.appendChild(domain);

    const confidence = document.createElement('span');
    confidence.className = 'knowledge-confidence';
    confidence.textContent = `${((item.extraction_confidence || 0) * 100).toFixed(0)}%`;
    header.appendChild(confidence);

    card.appendChild(header);

    // Query
    const query = document.createElement('div');
    query.className = 'knowledge-query';
    query.textContent = item.canonical_query || 'No query';
    card.appendChild(query);

    // Intent
    const intent = document.createElement('div');
    intent.className = 'knowledge-intent';
    intent.innerHTML = `<strong>Intent:</strong> ${escapeHtml(item.primary_intent || 'Unknown')}`;
    card.appendChild(intent);

    // Summary
    const summary = document.createElement('div');
    summary.className = 'knowledge-summary';
    summary.textContent = truncateText(item.answer_summary || '', 200);
    card.appendChild(summary);

    // Key facts
    if (item.key_facts?.length) {
        const facts = document.createElement('div');
        facts.className = 'knowledge-facts';
        facts.innerHTML = '<strong>Key Facts:</strong>';
        const factsList = document.createElement('ul');
        item.key_facts.slice(0, 3).forEach(fact => {
            const li = document.createElement('li');
            li.textContent = truncateText(fact, 100);
            factsList.appendChild(li);
        });
        if (item.key_facts.length > 3) {
            const more = document.createElement('li');
            more.className = 'more-facts';
            more.textContent = `+${item.key_facts.length - 3} more facts`;
            factsList.appendChild(more);
        }
        facts.appendChild(factsList);
        card.appendChild(facts);
    }

    // Related topics
    if (item.related_topics?.length) {
        const related = document.createElement('div');
        related.className = 'knowledge-related';
        item.related_topics.slice(0, 5).forEach(t => {
            const tag = document.createElement('span');
            tag.className = 'related-tag';
            tag.textContent = t;
            related.appendChild(tag);
        });
        card.appendChild(related);
    }

    // Active Second Brain: Action buttons for review
    if (showReviewActions && item.id) {
        const actions = document.createElement('div');
        actions.className = 'knowledge-actions';
        actions.style.cssText = 'display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #333;';

        const editBtn = document.createElement('button');
        editBtn.className = 'btn-secondary';
        editBtn.innerHTML = '✏️ Edit';
        editBtn.style.cssText = 'padding: 6px 12px; font-size: 12px;';
        editBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            showCorrectionModal(item.id, item.answer_summary || item.content || '');
        });
        actions.appendChild(editBtn);

        const verifyBtn = document.createElement('button');
        verifyBtn.className = 'btn-primary';
        verifyBtn.innerHTML = '✓ Verify';
        verifyBtn.style.cssText = 'padding: 6px 12px; font-size: 12px; background: #4CAF50;';
        verifyBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            verifyKnowledge(item.id);
        });
        actions.appendChild(verifyBtn);

        // Show confidence indicator
        const confidence = item.extraction_confidence || item.confidence || 0;
        const confBadge = document.createElement('span');
        confBadge.style.cssText = 'margin-left: auto; font-size: 11px; color: #888;';
        confBadge.textContent = `Confidence: ${(confidence * 100).toFixed(0)}%`;
        actions.appendChild(confBadge);

        card.appendChild(actions);
    }

    // Footer
    const footer = document.createElement('div');
    footer.className = 'knowledge-footer';
    footer.innerHTML = `
        <span class="knowledge-date">${item.created_at ? formatDate(item.created_at) : 'N/A'}</span>
        <span class="knowledge-id">${item.id?.slice(0, 8) || ''}...</span>
    `;
    card.appendChild(footer);

    return card;
}

// ============================================================================
// KNOWLEDGE MODAL (Full Article View)
// ============================================================================

/**
 * Show modal with full knowledge article details
 */
async function showKnowledgeModal(knowledgeId) {
    if (!knowledgeId) return;

    // Create modal overlay if it doesn't exist
    let modal = document.getElementById('knowledge-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'knowledge-modal';
        modal.className = 'modal-overlay';
        document.body.appendChild(modal);
    }

    // Show loading state
    modal.innerHTML = `
        <div class="modal-content knowledge-modal-content">
            <button class="modal-close" id="knowledge-modal-close">&times;</button>
            <div class="modal-body">
                <div class="loading">Loading knowledge article...</div>
            </div>
        </div>
    `;
    modal.classList.add('active');

    // Close on close button click
    const closeBtn = document.getElementById('knowledge-modal-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeKnowledgeModal();
        });
    }

    // Close on overlay click
    modal.onclick = (e) => {
        if (e.target === modal) closeKnowledgeModal();
    };

    // Close on Escape key
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            closeKnowledgeModal();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);

    try {
        const response = await fetch(`${API_BASE}/knowledge/${knowledgeId}`);
        const result = await response.json();

        if (result.status === 'error') {
            throw new Error(result.message || 'Failed to load knowledge');
        }

        const item = result.knowledge || result.data || result;
        renderKnowledgeModalContent(modal, item);

        // Re-attach close button listener after content render
        const closeBtnRendered = document.getElementById('knowledge-modal-close-rendered');
        if (closeBtnRendered) {
            closeBtnRendered.addEventListener('click', (e) => {
                e.stopPropagation();
                closeKnowledgeModal();
            });
        }

    } catch (error) {
        modal.querySelector('.modal-body').innerHTML = `
            <div class="error">Failed to load knowledge article: ${error.message}</div>
        `;
    }
}

/**
 * Render full knowledge article in modal
 */
function renderKnowledgeModalContent(modal, item) {
    const modalContent = modal.querySelector('.modal-content');
    modalContent.innerHTML = `
        <button class="modal-close" id="knowledge-modal-close-rendered">&times;</button>
        <div class="modal-header">
            <div class="modal-badges">
                <span class="badge badge-domain">${escapeHtml(item.problem_domain || 'Unknown Domain')}</span>
                <span class="badge badge-topic">${escapeHtml(item.topic_cluster || 'Unknown Topic')}</span>
                <span class="badge badge-intent">${escapeHtml(item.primary_intent || 'Unknown Intent')}</span>
                <span class="badge badge-confidence">${((item.extraction_confidence || 0) * 100).toFixed(0)}% confidence</span>
            </div>
            <h2 class="modal-title">${escapeHtml(item.canonical_query || 'Knowledge Article')}</h2>
        </div>
        <div class="modal-body">
            <section class="knowledge-section">
                <h3>Summary</h3>
                <p class="knowledge-full-summary">${escapeHtml(item.full_answer || item.answer_summary || 'No summary available')}</p>
            </section>

            ${item.why_context ? `
            <section class="knowledge-section">
                <h3>Context (Why)</h3>
                <p class="knowledge-why-context">${escapeHtml(item.why_context)}</p>
            </section>
            ` : ''}

            ${item.key_facts?.length ? `
            <section class="knowledge-section">
                <h3>Key Facts (${item.key_facts.length})</h3>
                <ul class="knowledge-full-facts">
                    ${item.key_facts.map(fact => `<li>${escapeHtml(fact)}</li>`).join('')}
                </ul>
            </section>
            ` : ''}

            ${(item.entities?.length || item.entities_json) ? `
            <section class="knowledge-section">
                <h3>Entities</h3>
                <div class="entity-list">
                    ${(item.entities || (typeof item.entities_json === 'string' ? JSON.parse(item.entities_json || '[]') : item.entities_json) || []).map(e => `
                        <div class="entity-item">
                            <span class="entity-name">${escapeHtml(e.name || e)}</span>
                            ${e.type ? `<span class="entity-type">${escapeHtml(e.type)}</span>` : ''}
                        </div>
                    `).join('')}
                </div>
            </section>
            ` : ''}

            ${item.related_topics?.length ? `
            <section class="knowledge-section">
                <h3>Related Topics</h3>
                <div class="related-topics-list">
                    ${item.related_topics.map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('')}
                </div>
            </section>
            ` : ''}

            ${item.source_queries?.length ? `
            <section class="knowledge-section">
                <h3>Source Queries</h3>
                <ul class="source-queries-list">
                    ${item.source_queries.map(q => `<li>${escapeHtml(q)}</li>`).join('')}
                </ul>
            </section>
            ` : ''}

            <section class="knowledge-section knowledge-meta">
                <h3>Metadata</h3>
                <div class="meta-grid">
                    <div class="meta-item">
                        <span class="meta-label">ID</span>
                        <span class="meta-value">${escapeHtml(item.id || 'N/A')}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Created</span>
                        <span class="meta-value">${item.created_at ? formatDate(item.created_at) : 'N/A'}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Usage Count</span>
                        <span class="meta-value">${item.usage_count || 0}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Feedback Score</span>
                        <span class="meta-value">${item.feedback_score !== null && item.feedback_score !== undefined ? item.feedback_score.toFixed(1) : 'N/A'}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Extraction Model</span>
                        <span class="meta-value">${escapeHtml(item.extraction_model || 'N/A')}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Source Query ID</span>
                        <span class="meta-value">${escapeHtml(item.source_query_id?.slice(0, 8) || 'N/A')}...</span>
                    </div>
                </div>
            </section>
        </div>
    `;
}

/**
 * Close knowledge modal
 */
function closeKnowledgeModal() {
    const modal = document.getElementById('knowledge-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Make closeKnowledgeModal available globally for onclick
if (typeof window !== 'undefined') {
    window.closeKnowledgeModal = closeKnowledgeModal;
}

// ============================================================
// API ANALYTICS VIEW
// ============================================================

/**
 * Render API Analytics View with 3 tabs
 * - Usage Overview: API calls by provider, trends, cost breakdown
 * - Performance: Latency, cache hit rates, response quality
 * - Routing Insights: Intent→Agent mapping, effectiveness
 */
async function renderAPIAnalyticsView(container) {
    container.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'api-analytics-header';
    header.innerHTML = `
        <div class="api-analytics-title-section">
            <h2>API Analytics</h2>
            <p class="view-subtitle">AI provider usage, performance metrics, and routing intelligence</p>
        </div>
        <div class="api-analytics-controls">
            <select id="api-analytics-period" class="period-select">
                <option value="7">Last 7 days</option>
                <option value="14">Last 14 days</option>
                <option value="30" selected>Last 30 days</option>
                <option value="90">Last 90 days</option>
            </select>
        </div>
    `;
    container.appendChild(header);

    // Tab navigation
    const tabNav = document.createElement('div');
    tabNav.className = 'api-analytics-tabs';
    tabNav.innerHTML = `
        <button class="analytics-tab-btn active" data-tab="usage">Usage Overview</button>
        <button class="analytics-tab-btn" data-tab="performance">Performance</button>
        <button class="analytics-tab-btn" data-tab="routing">Routing Insights</button>
        <button class="analytics-tab-btn" data-tab="storage">Storage</button>
        <button class="analytics-tab-btn" data-tab="jobs">Background Jobs</button>
    `;
    container.appendChild(tabNav);

    // Dashboard container
    const dashboard = document.createElement('div');
    dashboard.id = 'api-analytics-dashboard';
    dashboard.className = 'api-analytics-dashboard';
    container.appendChild(dashboard);

    // Tab switching logic
    let currentTab = 'usage';
    const tabButtons = tabNav.querySelectorAll('.analytics-tab-btn');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTab = btn.getAttribute('data-tab');
            const days = parseInt(document.getElementById('api-analytics-period').value);
            loadTabContent(dashboard, currentTab, days);
        });
    });

    // Period change handler
    document.getElementById('api-analytics-period').addEventListener('change', (e) => {
        const days = parseInt(e.target.value);
        loadTabContent(dashboard, currentTab, days);
    });

    // Load default tab
    loadTabContent(dashboard, 'usage', 30);
}

/**
 * Load tab content based on selected tab
 */
async function loadTabContent(container, tab, days) {
    switch (tab) {
        case 'usage':
            await loadUsageOverview(container, days);
            break;
        case 'performance':
            await loadPerformanceMetrics(container, days);
            break;
        case 'routing':
            await loadRoutingInsights(container, days);
            break;
        case 'storage':
            await loadStorageMetrics(container);
            break;
        case 'jobs':
            await loadJobsMonitor(container, days);
            break;
    }
}

/**
 * Tab 1: Usage Overview
 * Shows API calls by provider, daily trends, cost breakdown
 */
async function loadUsageOverview(container, days) {
    container.innerHTML = `
        <div class="analytics-loading">
            <div class="loading-spinner"></div>
            <p>Loading usage data...</p>
        </div>
    `;

    try {
        // Fetch data from multiple endpoints in parallel
        const [dashboardData, queryHistory, trendsData] = await Promise.all([
            fetch(`${API_BASE}/analytics/dashboard?user_id=default&days=${days}`).then(r => r.json()).catch(() => ({})),
            fetch(`${API_BASE}/query-history?days=${days}&page_size=200`).then(r => r.json()).catch(() => ({ items: [] })),
            fetch(`${API_BASE}/api/v2/insights/trends?period_days=${days}&granularity=day`).then(r => r.json()).catch(() => ({}))
        ]);

        container.innerHTML = '';

        // Calculate LLM usage from query history (API returns 'items' not 'queries')
        const queries = queryHistory.items || [];
        const llmUsage = calculateLLMUsage(queries);

        // Hero stats row
        const heroStats = document.createElement('div');
        heroStats.className = 'usage-hero-stats';

        const totalQueries = dashboardData.cache_performance?.total_queries || queries.length || 0;
        const totalCost = llmUsage.totalCost;
        const cacheSavings = dashboardData.cache_performance?.estimated_cost_savings_usd || 0;

        heroStats.innerHTML = `
            <div class="hero-stat-card">
                <div class="hero-stat-icon">📊</div>
                <div class="hero-stat-value">${totalQueries.toLocaleString()}</div>
                <div class="hero-stat-label">Total Queries</div>
                <div class="hero-stat-period">Last ${days} days</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">💰</div>
                <div class="hero-stat-value">$${totalCost.toFixed(2)}</div>
                <div class="hero-stat-label">Estimated Cost</div>
                <div class="hero-stat-period">API spend</div>
            </div>
            <div class="hero-stat-card savings">
                <div class="hero-stat-icon">💎</div>
                <div class="hero-stat-value">$${cacheSavings.toFixed(2)}</div>
                <div class="hero-stat-label">Cache Savings</div>
                <div class="hero-stat-period">Cost avoided</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">📈</div>
                <div class="hero-stat-value">${Math.round(totalQueries / Math.max(days, 1))}</div>
                <div class="hero-stat-label">Queries/Day</div>
                <div class="hero-stat-period">Average</div>
            </div>
        `;
        container.appendChild(heroStats);

        // Two-column layout for charts
        const chartsRow = document.createElement('div');
        chartsRow.className = 'analytics-charts-row';

        // LLM Distribution (left column)
        const agentSection = document.createElement('div');
        agentSection.className = 'analytics-section';
        agentSection.innerHTML = '<h3>LLM Usage Distribution</h3>';

        if (llmUsage.agents.length > 0) {
            const agentChart = createAgentDistributionChart(llmUsage.agents);
            agentSection.appendChild(agentChart);

            // Add pie chart visualization
            const pieChart = createLLMPieChart(llmUsage.agents);
            agentSection.appendChild(pieChart);
        } else {
            agentSection.innerHTML += '<p class="no-data">No LLM usage data available</p>';
        }
        chartsRow.appendChild(agentSection);

        // Cost Breakdown (right column)
        const costSection = document.createElement('div');
        costSection.className = 'analytics-section';
        costSection.innerHTML = '<h3>Cost by Provider</h3>';

        if (llmUsage.agents.length > 0) {
            const costChart = createCostBreakdownChart(llmUsage.agents);
            costSection.appendChild(costChart);
        } else {
            costSection.innerHTML += '<p class="no-data">No cost data available</p>';
        }
        chartsRow.appendChild(costSection);

        container.appendChild(chartsRow);

        // Usage Trend Chart (full width)
        const trendSection = document.createElement('div');
        trendSection.className = 'analytics-section full-width';
        trendSection.innerHTML = '<h3>Daily Usage Trend</h3>';

        const trendData = trendsData?.data?.timeline || [];
        if (trendData.length > 0) {
            const trendChart = createUsageTrendChart(trendData);
            trendSection.appendChild(trendChart);
        } else {
            trendSection.innerHTML += '<p class="no-data">No trend data available for this period</p>';
        }
        container.appendChild(trendSection);

    } catch (error) {
        console.error('Failed to load usage overview:', error);
        container.innerHTML = `<div class="analytics-error">Failed to load usage data. Please try again.</div>`;
    }
}

/**
 * Tab 2: Performance Metrics
 * Shows latency, cache hit rates, response quality
 */
async function loadPerformanceMetrics(container, days) {
    container.innerHTML = `
        <div class="analytics-loading">
            <div class="loading-spinner"></div>
            <p>Loading performance data...</p>
        </div>
    `;

    try {
        const dashboardData = await fetch(`${API_BASE}/analytics/dashboard?user_id=default&days=${days}`)
            .then(r => r.json())
            .catch(() => ({}));

        container.innerHTML = '';

        const cache = dashboardData.cache_performance || {};
        const satisfaction = dashboardData.user_satisfaction || {};

        // Hero stats row
        const heroStats = document.createElement('div');
        heroStats.className = 'usage-hero-stats';

        const avgLatency = cache.avg_latency_cache_miss_ms || 0;
        const cacheHitRate = (cache.total_hit_rate || 0) * 100;
        const exactHits = cache.exact_cache_hits || 0;
        const semanticHits = cache.semantic_cache_hits || 0;

        heroStats.innerHTML = `
            <div class="hero-stat-card ${avgLatency < 500 ? 'good' : avgLatency < 1000 ? 'warning' : 'bad'}">
                <div class="hero-stat-icon">⚡</div>
                <div class="hero-stat-value">${Math.round(avgLatency)}ms</div>
                <div class="hero-stat-label">Avg Latency</div>
                <div class="hero-stat-period">LLM calls</div>
            </div>
            <div class="hero-stat-card ${cacheHitRate > 30 ? 'good' : 'neutral'}">
                <div class="hero-stat-icon">🎯</div>
                <div class="hero-stat-value">${cacheHitRate.toFixed(1)}%</div>
                <div class="hero-stat-label">Cache Hit Rate</div>
                <div class="hero-stat-period">Total</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">✅</div>
                <div class="hero-stat-value">${exactHits}</div>
                <div class="hero-stat-label">Exact Hits</div>
                <div class="hero-stat-period">Direct matches</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">🔍</div>
                <div class="hero-stat-value">${semanticHits}</div>
                <div class="hero-stat-label">Semantic Hits</div>
                <div class="hero-stat-period">Similar matches</div>
            </div>
        `;
        container.appendChild(heroStats);

        // Two-column layout
        const chartsRow = document.createElement('div');
        chartsRow.className = 'analytics-charts-row';

        // Latency Comparison
        const latencySection = document.createElement('div');
        latencySection.className = 'analytics-section';
        latencySection.innerHTML = '<h3>Latency Comparison</h3>';

        const latencyData = [
            { label: 'Cache Hit', value: cache.avg_latency_cache_hit_ms || 0, color: '#4CAF50' },
            { label: 'Cache Miss', value: cache.avg_latency_cache_miss_ms || 0, color: '#FF9800' }
        ];
        const latencyChart = createHorizontalBarChart(latencyData, 'ms');
        latencySection.appendChild(latencyChart);
        chartsRow.appendChild(latencySection);

        // Response Quality
        const qualitySection = document.createElement('div');
        qualitySection.className = 'analytics-section';
        qualitySection.innerHTML = '<h3>Response Quality</h3>';

        const thumbsUp = satisfaction.thumbs_up_percentage || 0;
        const thumbsDown = satisfaction.thumbs_down_percentage || 0;
        const avgRating = satisfaction.avg_rating || 0;

        qualitySection.innerHTML += `
            <div class="quality-metrics">
                <div class="quality-metric">
                    <span class="quality-icon good">👍</span>
                    <span class="quality-value">${thumbsUp.toFixed(1)}%</span>
                    <span class="quality-label">Thumbs Up</span>
                </div>
                <div class="quality-metric">
                    <span class="quality-icon bad">👎</span>
                    <span class="quality-value">${thumbsDown.toFixed(1)}%</span>
                    <span class="quality-label">Thumbs Down</span>
                </div>
                <div class="quality-metric">
                    <span class="quality-icon neutral">⭐</span>
                    <span class="quality-value">${avgRating.toFixed(1)}/5</span>
                    <span class="quality-label">Avg Rating</span>
                </div>
            </div>
        `;
        chartsRow.appendChild(qualitySection);

        container.appendChild(chartsRow);

        // Cache Performance Breakdown (full width)
        const cacheSection = document.createElement('div');
        cacheSection.className = 'analytics-section full-width';
        cacheSection.innerHTML = '<h3>Cache Performance Breakdown</h3>';

        const totalQueries = cache.total_queries || 1;
        const cacheData = [
            { label: 'Exact Cache Hits', value: exactHits, pct: (exactHits / totalQueries * 100).toFixed(1), color: '#4CAF50' },
            { label: 'Semantic Cache Hits', value: semanticHits, pct: (semanticHits / totalQueries * 100).toFixed(1), color: '#2196F3' },
            { label: 'LLM Calls (Misses)', value: totalQueries - exactHits - semanticHits, pct: ((totalQueries - exactHits - semanticHits) / totalQueries * 100).toFixed(1), color: '#FF9800' }
        ];

        const cacheChart = createStackedBarChart(cacheData);
        cacheSection.appendChild(cacheChart);
        container.appendChild(cacheSection);

    } catch (error) {
        console.error('Failed to load performance metrics:', error);
        container.innerHTML = `<div class="analytics-error">Failed to load performance data. Please try again.</div>`;
    }
}

/**
 * Tab 3: Routing Insights
 * Shows intent distribution, agent effectiveness, recent queries
 */
async function loadRoutingInsights(container, days) {
    container.innerHTML = `
        <div class="analytics-loading">
            <div class="loading-spinner"></div>
            <p>Loading routing data...</p>
        </div>
    `;

    try {
        const [dashboardData, queryHistory] = await Promise.all([
            fetch(`${API_BASE}/analytics/dashboard?user_id=default&days=${days}&recent_limit=10`).then(r => r.json()).catch(() => ({})),
            fetch(`${API_BASE}/query-history?days=${days}&page_size=50`).then(r => r.json()).catch(() => ({ items: [] }))
        ]);

        container.innerHTML = '';

        // Calculate routing stats from query history (API returns 'items' not 'queries')
        const queries = queryHistory.items || [];
        const routingStats = calculateRoutingStats(queries);

        // Hero stats row
        const heroStats = document.createElement('div');
        heroStats.className = 'usage-hero-stats';

        heroStats.innerHTML = `
            <div class="hero-stat-card">
                <div class="hero-stat-icon">🎯</div>
                <div class="hero-stat-value">${routingStats.uniqueSources}</div>
                <div class="hero-stat-label">Active Agents</div>
                <div class="hero-stat-period">In use</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">🏆</div>
                <div class="hero-stat-value">${routingStats.topAgent || 'N/A'}</div>
                <div class="hero-stat-label">Top Agent</div>
                <div class="hero-stat-period">Most used</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">⭐</div>
                <div class="hero-stat-value">${routingStats.bestRatedAgent || 'N/A'}</div>
                <div class="hero-stat-label">Best Rated</div>
                <div class="hero-stat-period">Highest quality</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">📊</div>
                <div class="hero-stat-value">${queries.length}</div>
                <div class="hero-stat-label">Sample Size</div>
                <div class="hero-stat-period">Queries analyzed</div>
            </div>
        `;
        container.appendChild(heroStats);

        // Agent Effectiveness Table
        const agentSection = document.createElement('div');
        agentSection.className = 'analytics-section full-width';
        agentSection.innerHTML = '<h3>Agent Effectiveness</h3>';

        if (routingStats.byAgent && Object.keys(routingStats.byAgent).length > 0) {
            const agentTable = createAgentEffectivenessTable(routingStats.byAgent);
            agentSection.appendChild(agentTable);
        } else {
            agentSection.innerHTML += '<p class="no-data">No agent data available</p>';
        }
        container.appendChild(agentSection);

        // Recent Queries
        const recentSection = document.createElement('div');
        recentSection.className = 'analytics-section full-width';
        recentSection.innerHTML = '<h3>Recent Queries</h3>';

        const recentQueries = dashboardData.recent_queries || [];
        if (recentQueries.length > 0) {
            const recentList = createRecentQueriesList(recentQueries);
            recentSection.appendChild(recentList);
        } else {
            recentSection.innerHTML += '<p class="no-data">No recent queries available</p>';
        }
        container.appendChild(recentSection);

    } catch (error) {
        console.error('Failed to load routing insights:', error);
        container.innerHTML = `<div class="analytics-error">Failed to load routing data. Please try again.</div>`;
    }
}

/**
 * Tab 4: Storage Metrics
 * Shows database storage, memory counts, disk locations
 */
async function loadStorageMetrics(container) {
    container.innerHTML = `
        <div class="analytics-loading">
            <div class="loading-spinner"></div>
            <p>Loading storage metrics...</p>
        </div>
    `;

    try {
        // Fetch data from multiple endpoints in parallel
        const [statsData, knowledgeStats, dbHealth, weaviateHealth, redisHealth] = await Promise.all([
            fetch(`${API_BASE}/stats`).then(r => r.json()).catch(() => ({})),
            fetch(`${API_BASE}/knowledge/stats`).then(r => r.json()).catch(() => ({})),
            fetch(`${API_BASE}/health/database`).then(r => r.json()).catch(() => ({ database: 'disconnected' })),
            fetch(`${API_BASE}/health/weaviate`).then(r => r.json()).catch(() => ({ weaviate: 'disconnected' })),
            fetch(`${API_BASE}/health/redis`).then(r => r.json()).catch(() => ({ redis: 'disconnected' }))
        ]);

        container.innerHTML = '';

        // Calculate storage estimates
        const totalMemories = statsData.total || 0;
        const totalKnowledge = knowledgeStats.total_knowledge || 0;
        const estimatedMemorySize = (totalMemories * 2.5).toFixed(1); // ~2.5KB avg per memory
        const estimatedVectorSize = (totalMemories * 6).toFixed(1); // ~6KB per vector (1536 dims)
        const estimatedKnowledgeSize = (totalKnowledge * 3).toFixed(1);

        // Database Health Status
        const healthSection = document.createElement('div');
        healthSection.className = 'storage-health-section';
        healthSection.innerHTML = `
            <h3>Database Status</h3>
            <div class="health-cards">
                <div class="health-card ${dbHealth.database === 'connected' ? 'healthy' : 'unhealthy'}">
                    <div class="health-icon">🐘</div>
                    <div class="health-name">PostgreSQL</div>
                    <div class="health-status">${dbHealth.database === 'connected' ? 'Connected' : 'Disconnected'}</div>
                    <div class="health-detail">Primary data store</div>
                </div>
                <div class="health-card ${weaviateHealth.weaviate === 'connected' ? 'healthy' : 'unhealthy'}">
                    <div class="health-icon">🔷</div>
                    <div class="health-name">Weaviate</div>
                    <div class="health-status">${weaviateHealth.weaviate === 'connected' ? 'Connected' : 'Disconnected'}</div>
                    <div class="health-detail">Vector database</div>
                </div>
                <div class="health-card ${redisHealth.redis === 'connected' ? 'healthy' : 'unhealthy'}">
                    <div class="health-icon">🔴</div>
                    <div class="health-name">Redis</div>
                    <div class="health-status">${redisHealth.redis === 'connected' ? 'Connected' : 'Disconnected'}</div>
                    <div class="health-detail">Cache layer</div>
                </div>
            </div>
        `;
        container.appendChild(healthSection);

        // Storage Overview Cards
        const storageCards = document.createElement('div');
        storageCards.className = 'usage-hero-stats';
        storageCards.innerHTML = `
            <div class="hero-stat-card">
                <div class="hero-stat-icon">🧠</div>
                <div class="hero-stat-value">${totalMemories.toLocaleString()}</div>
                <div class="hero-stat-label">Total Memories</div>
                <div class="hero-stat-period">~${estimatedMemorySize} KB</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">📐</div>
                <div class="hero-stat-value">${totalMemories.toLocaleString()}</div>
                <div class="hero-stat-label">Vector Embeddings</div>
                <div class="hero-stat-period">~${estimatedVectorSize} KB</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">📚</div>
                <div class="hero-stat-value">${totalKnowledge.toLocaleString()}</div>
                <div class="hero-stat-label">Knowledge Items</div>
                <div class="hero-stat-period">~${estimatedKnowledgeSize} KB</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">💾</div>
                <div class="hero-stat-value">${((parseFloat(estimatedMemorySize) + parseFloat(estimatedVectorSize) + parseFloat(estimatedKnowledgeSize)) / 1024).toFixed(1)} MB</div>
                <div class="hero-stat-label">Est. Total Size</div>
                <div class="hero-stat-period">All databases</div>
            </div>
        `;
        container.appendChild(storageCards);

        // Two-column layout for details
        const detailsRow = document.createElement('div');
        detailsRow.className = 'analytics-charts-row';

        // Memory Breakdown by Source
        const sourceSection = document.createElement('div');
        sourceSection.className = 'analytics-section';
        sourceSection.innerHTML = '<h3>Memories by Source</h3>';

        const bySource = statsData.by_source || {};
        const sourceData = Object.entries(bySource)
            .sort((a, b) => b[1] - a[1])
            .map(([name, count]) => ({
                name: name.charAt(0).toUpperCase() + name.slice(1),
                count,
                color: getSourceColor(name)
            }));

        if (sourceData.length > 0) {
            const sourceChart = createStorageBarChart(sourceData, totalMemories);
            sourceSection.appendChild(sourceChart);
        } else {
            sourceSection.innerHTML += '<p class="no-data">No source data available</p>';
        }
        detailsRow.appendChild(sourceSection);

        // Memory Breakdown by Privacy Level
        const privacySection = document.createElement('div');
        privacySection.className = 'analytics-section';
        privacySection.innerHTML = '<h3>Memories by Privacy Level</h3>';

        const byPrivacy = statsData.by_privacy || {};
        const privacyColors = {
            'PUBLIC': '#4CAF50',
            'INTERNAL': '#2196F3',
            'CONFIDENTIAL': '#FF9800',
            'LOCAL_ONLY': '#f44336'
        };
        const privacyData = Object.entries(byPrivacy)
            .sort((a, b) => b[1] - a[1])
            .map(([level, count]) => ({
                name: level,
                count,
                color: privacyColors[level] || '#888'
            }));

        if (privacyData.length > 0) {
            const privacyChart = createStorageBarChart(privacyData, totalMemories);
            privacySection.appendChild(privacyChart);
        } else {
            privacySection.innerHTML += '<p class="no-data">No privacy data available</p>';
        }
        detailsRow.appendChild(privacySection);

        container.appendChild(detailsRow);

        // Storage Locations Section
        const locationsSection = document.createElement('div');
        locationsSection.className = 'analytics-section full-width';
        locationsSection.innerHTML = `
            <h3>Storage Locations</h3>
            <div class="storage-locations">
                <div class="location-card">
                    <div class="location-icon">🐘</div>
                    <div class="location-info">
                        <div class="location-name">PostgreSQL Data</div>
                        <div class="location-path">/Volumes/Docker/acms-postgres-data</div>
                        <div class="location-tables">Tables: memory_items, query_history, conversations, users, feedback</div>
                    </div>
                </div>
                <div class="location-card">
                    <div class="location-icon">🔷</div>
                    <div class="location-info">
                        <div class="location-name">Weaviate Vectors</div>
                        <div class="location-path">/Volumes/Docker/acms-weaviate-data</div>
                        <div class="location-tables">Collections: ACMS_Raw_v1, ACMS_Knowledge_v2</div>
                    </div>
                </div>
                <div class="location-card">
                    <div class="location-icon">🔴</div>
                    <div class="location-info">
                        <div class="location-name">Redis Cache</div>
                        <div class="location-path">/Volumes/Docker/acms-redis-data</div>
                        <div class="location-tables">Keys: semantic_cache, session_data</div>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(locationsSection);

        // Knowledge Stats Section
        if (knowledgeStats.top_domains || knowledgeStats.by_intent) {
            const knowledgeSection = document.createElement('div');
            knowledgeSection.className = 'analytics-section full-width';
            knowledgeSection.innerHTML = '<h3>Knowledge Base Distribution</h3>';

            const kbRow = document.createElement('div');
            kbRow.className = 'kb-stats-row';

            // By Domain
            if (knowledgeStats.top_domains && knowledgeStats.top_domains.length > 0) {
                const domainDiv = document.createElement('div');
                domainDiv.className = 'kb-stat-group';
                domainDiv.innerHTML = '<h4>Top Domains</h4>';
                const domainList = document.createElement('div');
                domainList.className = 'tag-cloud';
                knowledgeStats.top_domains.slice(0, 8).forEach(d => {
                    domainList.innerHTML += `<span class="tag-item">${escapeHtml(d.domain || d.name)} <span class="tag-count">${d.count}</span></span>`;
                });
                domainDiv.appendChild(domainList);
                kbRow.appendChild(domainDiv);
            }

            // By Intent
            if (knowledgeStats.by_intent && Object.keys(knowledgeStats.by_intent).length > 0) {
                const intentDiv = document.createElement('div');
                intentDiv.className = 'kb-stat-group';
                intentDiv.innerHTML = '<h4>By Intent</h4>';
                const intentList = document.createElement('div');
                intentList.className = 'tag-cloud';
                Object.entries(knowledgeStats.by_intent)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 6)
                    .forEach(([intent, count]) => {
                        intentList.innerHTML += `<span class="tag-item">${escapeHtml(intent)} <span class="tag-count">${count}</span></span>`;
                    });
                intentDiv.appendChild(intentList);
                kbRow.appendChild(intentDiv);
            }

            knowledgeSection.appendChild(kbRow);
            container.appendChild(knowledgeSection);
        }

    } catch (error) {
        console.error('Failed to load storage metrics:', error);
        container.innerHTML = `<div class="analytics-error">Failed to load storage data. Please try again.</div>`;
    }
}

/**
 * Tab 5: Background Jobs Monitor
 * Shows scheduled jobs, recent runs, success/failure rates
 */
async function loadJobsMonitor(container, days) {
    container.innerHTML = `
        <div class="analytics-loading">
            <div class="loading-spinner"></div>
            <p>Loading job data...</p>
        </div>
    `;

    try {
        // Fetch job status and recent runs in parallel
        const [statusData, runsData] = await Promise.all([
            fetch(`${API_BASE}/api/v2/jobs/status`).then(r => r.json()).catch(() => ({ status: 'unknown', jobs: [] })),
            fetch(`${API_BASE}/api/v2/jobs/runs?days=${days}`).then(r => r.json()).catch(() => ({ runs: [] }))
        ]);

        container.innerHTML = '';

        const jobs = statusData.jobs || [];
        const runs = runsData.runs || [];

        // Calculate stats from runs
        const successCount = runs.filter(r => r.status === 'success').length;
        const failedCount = runs.filter(r => r.status === 'failed').length;
        const totalRuns = runs.length;
        const successRate = totalRuns > 0 ? ((successCount / totalRuns) * 100).toFixed(0) : 0;

        // Group runs by job for summary
        const jobStats = {};
        runs.forEach(run => {
            if (!jobStats[run.job_name]) {
                jobStats[run.job_name] = { runs: 0, success: 0, failed: 0, lastRun: null, totalOutput: 0 };
            }
            jobStats[run.job_name].runs++;
            if (run.status === 'success') jobStats[run.job_name].success++;
            if (run.status === 'failed') jobStats[run.job_name].failed++;
            if (!jobStats[run.job_name].lastRun || run.started_at > jobStats[run.job_name].lastRun) {
                jobStats[run.job_name].lastRun = run.started_at;
            }
            jobStats[run.job_name].totalOutput += (run.output_count || 0);
        });

        // Hero stats
        const heroStats = document.createElement('div');
        heroStats.className = 'usage-hero-stats';
        heroStats.innerHTML = `
            <div class="hero-stat-card">
                <div class="hero-stat-icon">${statusData.status === 'running' ? '🟢' : '🔴'}</div>
                <div class="hero-stat-value">${statusData.status === 'running' ? 'Running' : 'Stopped'}</div>
                <div class="hero-stat-label">Scheduler Status</div>
                <div class="hero-stat-period">${jobs.length} jobs registered</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">📊</div>
                <div class="hero-stat-value">${totalRuns}</div>
                <div class="hero-stat-label">Total Runs</div>
                <div class="hero-stat-period">Last ${days} days</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">${successRate >= 90 ? '✅' : successRate >= 70 ? '⚠️' : '❌'}</div>
                <div class="hero-stat-value">${successRate}%</div>
                <div class="hero-stat-label">Success Rate</div>
                <div class="hero-stat-period">${successCount} ok / ${failedCount} failed</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-icon">📤</div>
                <div class="hero-stat-value">${runs.reduce((sum, r) => sum + (r.output_count || 0), 0)}</div>
                <div class="hero-stat-label">Items Processed</div>
                <div class="hero-stat-period">Total output count</div>
            </div>
        `;
        container.appendChild(heroStats);

        // Two-column layout
        const chartsRow = document.createElement('div');
        chartsRow.className = 'analytics-charts-row';

        // Scheduled Jobs section
        const scheduledSection = document.createElement('div');
        scheduledSection.className = 'analytics-section';
        scheduledSection.innerHTML = '<h3>Scheduled Jobs</h3>';

        if (jobs.length > 0) {
            const jobsTable = document.createElement('div');
            jobsTable.className = 'jobs-schedule-table';
            jobsTable.innerHTML = `
                <div class="jobs-table-header">
                    <span>Job Name</span>
                    <span>Schedule</span>
                    <span>Next Run</span>
                </div>
            `;
            jobs.forEach(job => {
                const nextRun = job.next_run ? new Date(job.next_run) : null;
                const nextRunStr = nextRun ? formatTimeAgo(nextRun, true) : 'N/A';
                const scheduleStr = parseSchedule(job.trigger);

                jobsTable.innerHTML += `
                    <div class="jobs-table-row">
                        <span class="job-name">${escapeHtml(job.name)}</span>
                        <span class="job-schedule">${scheduleStr}</span>
                        <span class="job-next-run">${nextRunStr}</span>
                    </div>
                `;
            });
            scheduledSection.appendChild(jobsTable);
        } else {
            scheduledSection.innerHTML += '<p class="no-data">No jobs scheduled</p>';
        }
        chartsRow.appendChild(scheduledSection);

        // Job Performance Summary
        const perfSection = document.createElement('div');
        perfSection.className = 'analytics-section';
        perfSection.innerHTML = '<h3>Job Performance</h3>';

        const jobNames = Object.keys(jobStats);
        if (jobNames.length > 0) {
            const perfTable = document.createElement('div');
            perfTable.className = 'jobs-perf-table';
            perfTable.innerHTML = `
                <div class="jobs-table-header">
                    <span>Job</span>
                    <span>Runs</span>
                    <span>Success</span>
                    <span>Output</span>
                </div>
            `;
            jobNames.forEach(name => {
                const stats = jobStats[name];
                const rate = stats.runs > 0 ? ((stats.success / stats.runs) * 100).toFixed(0) : 0;
                const statusIcon = rate >= 90 ? '✅' : rate >= 70 ? '⚠️' : '❌';
                perfTable.innerHTML += `
                    <div class="jobs-table-row">
                        <span class="job-name">${formatJobName(name)}</span>
                        <span>${stats.runs}</span>
                        <span>${statusIcon} ${rate}%</span>
                        <span>${stats.totalOutput}</span>
                    </div>
                `;
            });
            perfSection.appendChild(perfTable);
        } else {
            perfSection.innerHTML += '<p class="no-data">No run history</p>';
        }
        chartsRow.appendChild(perfSection);
        container.appendChild(chartsRow);

        // Recent Runs section (full width)
        const recentSection = document.createElement('div');
        recentSection.className = 'analytics-section full-width';
        recentSection.innerHTML = '<h3>Recent Job Runs</h3>';

        if (runs.length > 0) {
            const runsTable = document.createElement('div');
            runsTable.className = 'jobs-runs-table';
            runsTable.innerHTML = `
                <div class="jobs-runs-header">
                    <span>Job</span>
                    <span>Started</span>
                    <span>Duration</span>
                    <span>Input</span>
                    <span>Output</span>
                    <span>Status</span>
                </div>
            `;

            // Show last 15 runs
            runs.slice(0, 15).forEach(run => {
                const started = new Date(run.started_at);
                const completed = run.completed_at ? new Date(run.completed_at) : null;
                const duration = completed ? ((completed - started) / 1000).toFixed(1) + 's' : '-';
                const statusClass = run.status === 'success' ? 'status-success' :
                                   run.status === 'failed' ? 'status-failed' : 'status-running';
                const statusIcon = run.status === 'success' ? '✅' :
                                  run.status === 'failed' ? '❌' : '🔄';

                runsTable.innerHTML += `
                    <div class="jobs-runs-row ${statusClass}">
                        <span class="job-name">${formatJobName(run.job_name)}</span>
                        <span>${formatDateTime(started)}</span>
                        <span>${duration}</span>
                        <span>${run.input_count || 0}</span>
                        <span>${run.output_count || 0}</span>
                        <span class="job-status">${statusIcon} ${run.status}${run.error_summary ? ` - ${escapeHtml(run.error_summary.substring(0, 50))}...` : ''}</span>
                    </div>
                `;
            });
            recentSection.appendChild(runsTable);
        } else {
            recentSection.innerHTML += '<p class="no-data">No recent runs</p>';
        }
        container.appendChild(recentSection);

    } catch (error) {
        console.error('Failed to load jobs data:', error);
        container.innerHTML = `<div class="analytics-error">Failed to load job data. Please try again.</div>`;
    }
}

/**
 * Parse cron trigger to human-readable schedule
 */
function parseSchedule(trigger) {
    if (!trigger) return 'Unknown';
    if (trigger.includes("minute='15'") && !trigger.includes('hour')) return 'Hourly at :15';
    if (trigger.includes("minute='45'") && !trigger.includes('hour')) return 'Hourly at :45';
    if (trigger.includes("hour='2'")) return 'Daily at 2 AM';
    if (trigger.includes("hour='3'")) return 'Daily at 3 AM';
    if (trigger.includes("day_of_week='sun'") && trigger.includes("hour='4'")) return 'Sunday 4 AM';
    if (trigger.includes("day_of_week='sun'") && trigger.includes("hour='5'")) return 'Sunday 5 AM';
    if (trigger.includes("day_of_week='mon'") && trigger.includes("hour='6'")) return 'Monday 6 AM';
    return trigger.replace('cron[', '').replace(']', '');
}

/**
 * Format job name for display
 */
function formatJobName(name) {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Format datetime for display
 */
function formatDateTime(date) {
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;

    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

/**
 * Format time ago or time until (for next run times)
 * @param {Date} date - The date to format
 * @param {boolean} future - If true, format as "in X minutes" for future dates
 */
function formatTimeAgo(date, future = false) {
    const now = new Date();
    const diff = future ? (date - now) : (now - date);
    const absDiff = Math.abs(diff);

    if (absDiff < 60000) {
        return future ? 'in < 1m' : 'just now';
    }
    if (absDiff < 3600000) {
        const mins = Math.floor(absDiff / 60000);
        return future ? `in ${mins}m` : `${mins}m ago`;
    }
    if (absDiff < 86400000) {
        const hours = Math.floor(absDiff / 3600000);
        return future ? `in ${hours}h` : `${hours}h ago`;
    }

    const days = Math.floor(absDiff / 86400000);
    if (days < 7) {
        return future ? `in ${days}d` : `${days}d ago`;
    }

    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

/**
 * Get color for data source
 */
function getSourceColor(source) {
    const colors = {
        'gemini': '#4285F4',
        'claude': '#CC785C',
        'chatgpt': '#10A37F',
        'github': '#333333',
        'slack': '#4A154B',
        'chrome': '#FFC107',
        'cache': '#888888',
        'unknown': '#666666'
    };
    return colors[source.toLowerCase()] || '#666666';
}

/**
 * Create storage bar chart
 */
function createStorageBarChart(data, total) {
    const chart = document.createElement('div');
    chart.className = 'storage-bar-chart';

    data.forEach(item => {
        const pct = total > 0 ? (item.count / total * 100).toFixed(1) : 0;
        const bar = document.createElement('div');
        bar.className = 'storage-bar';
        bar.innerHTML = `
            <span class="bar-label">${escapeHtml(item.name)}</span>
            <div class="bar-track">
                <div class="bar-fill" style="width: ${pct}%; background: ${item.color}"></div>
            </div>
            <span class="bar-value">${item.count.toLocaleString()} (${pct}%)</span>
        `;
        chart.appendChild(bar);
    });

    return chart;
}

// ============================================================
// HELPER FUNCTIONS FOR API ANALYTICS
// ============================================================

/**
 * Calculate LLM usage from query history
 * Uses REAL cost data from est_cost_usd field in query_history
 */
function calculateLLMUsage(queries) {
    const byAgent = {};

    // Fallback costs only used if est_cost_usd is null
    const fallbackCosts = {
        'gemini': 0.0001,
        'gemini_flash': 0.0001,
        'claude': 0.015,
        'claude_sonnet': 0.015,
        'chatgpt': 0.01,
        'gpt_4o': 0.01,
        'gpt4': 0.01,
        'ollama': 0,  // Free local inference
        'cache': 0,
        'semantic_cache': 0
    };

    const colors = {
        'gemini': '#4285F4',
        'gemini_flash': '#4285F4',
        'claude': '#CC785C',
        'claude_sonnet': '#CC785C',
        'chatgpt': '#10A37F',
        'gpt_4o': '#10A37F',
        'gpt4': '#10A37F',
        'ollama': '#FA8072',  // Salmon color for Ollama
        'cache': '#888888',
        'semantic_cache': '#666666'
    };

    const displayNames = {
        'gemini': 'Gemini Flash',
        'gemini_flash': 'Gemini Flash',
        'claude': 'Claude Sonnet',
        'claude_sonnet': 'Claude Sonnet',
        'chatgpt': 'GPT-4o',
        'gpt_4o': 'GPT-4o',
        'gpt4': 'GPT-4o',
        'ollama': 'Ollama Local',
        'cache': 'Cache Hit',
        'semantic_cache': 'Semantic Cache'
    };

    let totalCost = 0;
    let realCostCount = 0;  // Track how many have real cost data

    queries.forEach(q => {
        const source = (q.response_source || 'unknown').toLowerCase();
        const displayName = displayNames[source] || source.charAt(0).toUpperCase() + source.slice(1);

        if (!byAgent[displayName]) {
            byAgent[displayName] = {
                name: displayName,
                count: 0,
                cost: 0,
                color: colors[source] || '#666666'
            };
        }
        byAgent[displayName].count++;

        // Use REAL cost from database if available, otherwise fallback to estimate
        let queryCost = 0;
        if (q.est_cost_usd !== null && q.est_cost_usd !== undefined) {
            queryCost = parseFloat(q.est_cost_usd) || 0;
            realCostCount++;
        } else {
            queryCost = fallbackCosts[source] || 0.005;
        }

        byAgent[displayName].cost += queryCost;
        totalCost += queryCost;
    });

    // Convert to array and sort by count
    const agents = Object.values(byAgent).sort((a, b) => b.count - a.count);

    return {
        agents,
        totalCost,
        realCostData: realCostCount > 0,  // Flag if we have real cost data
        realCostPercentage: queries.length > 0 ? (realCostCount / queries.length * 100).toFixed(0) : 0
    };
}

/**
 * Create LLM pie chart
 */
function createLLMPieChart(agents) {
    const container = document.createElement('div');
    container.className = 'llm-pie-container';

    const total = agents.reduce((sum, a) => sum + a.count, 0);
    if (total === 0) return container;

    // Create pie chart using CSS conic-gradient
    let gradientParts = [];
    let currentAngle = 0;

    agents.forEach(agent => {
        const pct = agent.count / total * 100;
        const startAngle = currentAngle;
        currentAngle += pct * 3.6; // Convert to degrees
        gradientParts.push(`${agent.color} ${startAngle}deg ${currentAngle}deg`);
    });

    const pie = document.createElement('div');
    pie.className = 'llm-pie';
    pie.style.background = `conic-gradient(${gradientParts.join(', ')})`;
    container.appendChild(pie);

    // Legend
    const legend = document.createElement('div');
    legend.className = 'llm-pie-legend';
    agents.forEach(agent => {
        const pct = (agent.count / total * 100).toFixed(1);
        legend.innerHTML += `
            <div class="pie-legend-item">
                <span class="pie-legend-color" style="background: ${agent.color}"></span>
                <span class="pie-legend-name">${escapeHtml(agent.name)}</span>
                <span class="pie-legend-value">${pct}%</span>
            </div>
        `;
    });
    container.appendChild(legend);

    return container;
}

/**
 * Calculate total estimated cost from stats data (legacy - kept for compatibility)
 */
function calculateTotalCost(statsData) {
    // Estimate based on query counts and average costs per provider
    const bySrc = statsData.by_source || {};
    const costs = {
        gemini: 0.0001,   // Gemini Flash is cheap
        claude: 0.015,    // Claude Sonnet
        chatgpt: 0.01,    // GPT-4o
        ollama: 0,        // Free local inference
        cache: 0
    };

    let total = 0;
    for (const [source, count] of Object.entries(bySrc)) {
        const cost = costs[source.toLowerCase()] || 0.005;
        total += count * cost;
    }
    return total;
}

/**
 * Extract agent distribution from stats data
 */
function extractAgentDistribution(statsData) {
    const bySrc = statsData.by_source || {};
    const agents = [];
    const colors = {
        gemini: '#4285F4',
        claude: '#CC785C',
        chatgpt: '#10A37F',
        ollama: '#FA8072',
        cache: '#888888',
        github: '#333333',
        slack: '#4A154B',
        chrome: '#FFC107'
    };

    for (const [source, count] of Object.entries(bySrc)) {
        if (['gemini', 'claude', 'chatgpt', 'ollama', 'cache'].includes(source.toLowerCase())) {
            agents.push({
                name: source.charAt(0).toUpperCase() + source.slice(1),
                count: count,
                color: colors[source.toLowerCase()] || '#666666'
            });
        }
    }

    // Sort by count descending
    agents.sort((a, b) => b.count - a.count);
    return agents;
}

/**
 * Create agent distribution bar chart
 */
function createAgentDistributionChart(agents) {
    const chart = document.createElement('div');
    chart.className = 'agent-distribution-chart';

    const total = agents.reduce((sum, a) => sum + a.count, 0) || 1;

    agents.forEach(agent => {
        const pct = (agent.count / total * 100).toFixed(1);
        const bar = document.createElement('div');
        bar.className = 'distribution-bar';
        bar.innerHTML = `
            <span class="bar-label">${escapeHtml(agent.name)}</span>
            <div class="bar-track">
                <div class="bar-fill" style="width: ${pct}%; background: ${agent.color}"></div>
            </div>
            <span class="bar-value">${agent.count.toLocaleString()} (${pct}%)</span>
        `;
        chart.appendChild(bar);
    });

    if (agents.length === 0) {
        chart.innerHTML = '<p class="no-data">No agent usage data available</p>';
    }

    return chart;
}

/**
 * Create cost breakdown donut chart
 */
function createCostBreakdownChart(agents) {
    const container = document.createElement('div');
    container.className = 'cost-breakdown-container';

    const costs = {
        'Gemini': 0.0001,
        'Claude': 0.015,
        'Chatgpt': 0.01,
        'Cache': 0
    };

    const costData = agents.map(a => ({
        name: a.name,
        cost: a.count * (costs[a.name] || 0.005),
        color: a.color
    })).filter(c => c.cost > 0);

    const total = costData.reduce((sum, c) => sum + c.cost, 0);

    if (total === 0) {
        container.innerHTML = '<p class="no-data">No cost data available</p>';
        return container;
    }

    // Create donut chart using CSS conic-gradient
    let gradientParts = [];
    let currentAngle = 0;

    costData.forEach(item => {
        const pct = item.cost / total * 100;
        const startAngle = currentAngle;
        currentAngle += pct * 3.6; // Convert to degrees
        gradientParts.push(`${item.color} ${startAngle}deg ${currentAngle}deg`);
    });

    const donut = document.createElement('div');
    donut.className = 'cost-donut';
    donut.style.background = `conic-gradient(${gradientParts.join(', ')})`;
    donut.innerHTML = `<div class="donut-center"><span class="donut-total">$${total.toFixed(2)}</span><span class="donut-label">Total</span></div>`;
    container.appendChild(donut);

    // Legend
    const legend = document.createElement('div');
    legend.className = 'cost-legend';
    costData.forEach(item => {
        const pct = (item.cost / total * 100).toFixed(1);
        legend.innerHTML += `
            <div class="legend-item">
                <span class="legend-color" style="background: ${item.color}"></span>
                <span class="legend-name">${escapeHtml(item.name)}</span>
                <span class="legend-value">$${item.cost.toFixed(2)} (${pct}%)</span>
            </div>
        `;
    });
    container.appendChild(legend);

    return container;
}

/**
 * Create usage trend chart
 */
function createUsageTrendChart(trendData) {
    const chart = document.createElement('div');
    chart.className = 'usage-trend-chart';

    // Get last 14 data points
    const data = trendData.slice(-14);
    const maxQueries = Math.max(...data.map(d => d.queries || 0), 1);

    data.forEach(day => {
        const pct = ((day.queries || 0) / maxQueries * 100).toFixed(1);
        const bar = document.createElement('div');
        bar.className = 'trend-bar';
        bar.innerHTML = `
            <div class="trend-bar-fill" style="height: ${pct}%"></div>
            <span class="trend-bar-label">${formatTrendDate(day.date || day.period)}</span>
        `;
        bar.title = `${day.queries || 0} queries`;
        chart.appendChild(bar);
    });

    return chart;
}

/**
 * Format date for trend chart
 */
function formatTrendDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
}

/**
 * Create horizontal bar chart
 */
function createHorizontalBarChart(data, unit) {
    const chart = document.createElement('div');
    chart.className = 'horizontal-bar-chart';

    const maxVal = Math.max(...data.map(d => d.value), 1);

    data.forEach(item => {
        const pct = (item.value / maxVal * 100).toFixed(1);
        const bar = document.createElement('div');
        bar.className = 'h-bar';
        bar.innerHTML = `
            <span class="h-bar-label">${escapeHtml(item.label)}</span>
            <div class="h-bar-track">
                <div class="h-bar-fill" style="width: ${pct}%; background: ${item.color}"></div>
            </div>
            <span class="h-bar-value">${Math.round(item.value)}${unit}</span>
        `;
        chart.appendChild(bar);
    });

    return chart;
}

/**
 * Create stacked bar chart for cache breakdown
 */
function createStackedBarChart(data) {
    const container = document.createElement('div');
    container.className = 'stacked-bar-container';

    const bar = document.createElement('div');
    bar.className = 'stacked-bar';

    data.forEach(item => {
        const segment = document.createElement('div');
        segment.className = 'stacked-segment';
        segment.style.width = `${item.pct}%`;
        segment.style.background = item.color;
        segment.title = `${item.label}: ${item.value} (${item.pct}%)`;
        bar.appendChild(segment);
    });

    container.appendChild(bar);

    // Legend
    const legend = document.createElement('div');
    legend.className = 'stacked-legend';
    data.forEach(item => {
        legend.innerHTML += `
            <div class="legend-item">
                <span class="legend-color" style="background: ${item.color}"></span>
                <span class="legend-name">${escapeHtml(item.label)}</span>
                <span class="legend-value">${item.value.toLocaleString()} (${item.pct}%)</span>
            </div>
        `;
    });
    container.appendChild(legend);

    return container;
}

/**
 * Calculate routing stats from query history
 */
function calculateRoutingStats(queries) {
    const byAgent = {};
    const feedback = {};

    queries.forEach(q => {
        const source = q.response_source || 'unknown';
        if (!byAgent[source]) {
            byAgent[source] = { count: 0, ratings: [], latencies: [] };
        }
        byAgent[source].count++;

        if (q.rating) byAgent[source].ratings.push(q.rating);
        if (q.total_latency_ms) byAgent[source].latencies.push(q.total_latency_ms);
    });

    // Calculate averages
    for (const source of Object.keys(byAgent)) {
        const data = byAgent[source];
        data.avgRating = data.ratings.length > 0
            ? data.ratings.reduce((a, b) => a + b, 0) / data.ratings.length
            : null;
        data.avgLatency = data.latencies.length > 0
            ? data.latencies.reduce((a, b) => a + b, 0) / data.latencies.length
            : null;
    }

    // Find top and best rated
    const sortedByCount = Object.entries(byAgent).sort((a, b) => b[1].count - a[1].count);
    const sortedByRating = Object.entries(byAgent)
        .filter(([_, data]) => data.avgRating !== null)
        .sort((a, b) => (b[1].avgRating || 0) - (a[1].avgRating || 0));

    return {
        uniqueSources: Object.keys(byAgent).length,
        topAgent: sortedByCount[0]?.[0] || null,
        bestRatedAgent: sortedByRating[0]?.[0] || null,
        byAgent
    };
}

/**
 * Create agent effectiveness table
 */
function createAgentEffectivenessTable(byAgent) {
    const table = document.createElement('table');
    table.className = 'effectiveness-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Agent</th>
                <th>Queries</th>
                <th>Avg Rating</th>
                <th>Avg Latency</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tbody = table.querySelector('tbody');
    const sorted = Object.entries(byAgent).sort((a, b) => b[1].count - a[1].count);

    sorted.forEach(([agent, data]) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><span class="agent-badge agent-${agent.toLowerCase()}">${escapeHtml(agent)}</span></td>
            <td>${data.count.toLocaleString()}</td>
            <td>${data.avgRating !== null ? data.avgRating.toFixed(1) + '/5' : 'N/A'}</td>
            <td>${data.avgLatency !== null ? Math.round(data.avgLatency) + 'ms' : 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });

    return table;
}

/**
 * Create recent queries list
 */
function createRecentQueriesList(queries) {
    const list = document.createElement('div');
    list.className = 'recent-queries-list';

    queries.slice(0, 10).forEach(q => {
        const item = document.createElement('div');
        item.className = 'recent-query-item';

        const feedbackIcon = q.feedback_type === 'thumbs_up' ? '👍'
            : q.feedback_type === 'thumbs_down' ? '👎'
            : '';

        const questionPreview = (q.question || '').slice(0, 80) + ((q.question || '').length > 80 ? '...' : '');

        item.innerHTML = `
            <div class="query-preview">${escapeHtml(questionPreview)}</div>
            <div class="query-meta">
                <span class="agent-badge agent-${(q.response_source || '').toLowerCase()}">${escapeHtml(q.response_source || 'unknown')}</span>
                ${feedbackIcon ? `<span class="feedback-icon">${feedbackIcon}</span>` : ''}
                <span class="query-time">${formatRelativeTime(q.created_at)}</span>
            </div>
        `;
        list.appendChild(item);
    });

    return list;
}

/**
 * Format relative time for queries
 */
function formatRelativeTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

// ============================================================================
// DATA FLOW VIEW - Audit & Privacy Monitoring
// ============================================================================

/**
 * Render the Data Flow view
 * Shows data ingress/egress tracking, privacy status, and audit events
 */
async function renderDataFlowView(container) {
    container.innerHTML = '';

    // Create scrollable content wrapper
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'data-flow-container';

    // Header
    const header = document.createElement('div');
    header.className = 'view-header data-flow-header';
    header.innerHTML = `
        <div class="data-flow-header-content">
            <div class="data-flow-header-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 22V8m0 0l4 4m-4-4l-4 4"/>
                    <path d="M20 12V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2h4"/>
                    <circle cx="18" cy="18" r="3"/>
                    <path d="M18 15v6m-3-3h6"/>
                </svg>
            </div>
            <div>
                <h2>Data Flow Monitor</h2>
                <p class="view-subtitle">Track all data ingress, transforms, and egress with privacy enforcement</p>
            </div>
        </div>
        <div class="data-flow-period-selector">
            <button class="period-btn active" data-days="1">Today</button>
            <button class="period-btn" data-days="7">7 Days</button>
            <button class="period-btn" data-days="30">30 Days</button>
        </div>
    `;
    contentWrapper.appendChild(header);

    // Main dashboard
    const dashboard = document.createElement('div');
    dashboard.id = 'data-flow-dashboard';
    dashboard.className = 'data-flow-dashboard';
    dashboard.innerHTML = `
        <div class="loading-skeleton">
            <div class="skeleton-row"><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div></div>
            <div class="skeleton-row"><div class="skeleton-large"></div><div class="skeleton-large"></div></div>
        </div>
    `;
    contentWrapper.appendChild(dashboard);

    container.appendChild(contentWrapper);

    // Load dashboard data
    await loadDataFlowDashboard(dashboard);

    // Setup period selector
    const periodBtns = header.querySelectorAll('.period-btn');
    periodBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            periodBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            await loadDataFlowDashboard(dashboard, parseInt(btn.dataset.days));
        });
    });
}

/**
 * Load Data Flow dashboard data
 */
async function loadDataFlowDashboard(container, days = 1) {
    container.innerHTML = `
        <div class="loading-skeleton">
            <div class="skeleton-row"><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div></div>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/api/v2/audit/dashboard`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();

        container.innerHTML = '';

        // Privacy Status Hero
        const privacyHero = document.createElement('div');
        privacyHero.className = `privacy-status-hero ${data.today.privacy_status === 'SECURE' ? 'status-secure' : 'status-violation'}`;
        privacyHero.innerHTML = `
            <div class="privacy-status-icon">
                ${data.today.privacy_status === 'SECURE'
                    ? '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>'
                    : '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v4m0 4h.01"/></svg>'
                }
            </div>
            <div class="privacy-status-text">
                <h3>Privacy Status: ${data.today.privacy_status}</h3>
                <p>${data.today.privacy_status === 'SECURE'
                    ? 'All confidential data stayed local - no external leakage'
                    : 'WARNING: Confidential data may have been sent externally!'}</p>
            </div>
        `;
        container.appendChild(privacyHero);

        // Hero Stats Row
        const statsRow = document.createElement('div');
        statsRow.className = 'data-flow-stats-row';

        const today = data.today;
        const totalIngress = today.ingress.gmail_emails + today.ingress.calendar_events +
                            today.ingress.plaid_transactions + today.ingress.files_uploaded +
                            today.ingress.chat_messages;
        const totalEgress = today.egress.llm_calls_total + today.egress.browser_automations;

        statsRow.innerHTML = `
            <div class="stat-card stat-ingress">
                <div class="stat-icon">⬇️</div>
                <div class="stat-value">${totalIngress.toLocaleString()}</div>
                <div class="stat-label">Data Ingress</div>
                <div class="stat-detail">Items received today</div>
            </div>
            <div class="stat-card stat-transform">
                <div class="stat-icon">⚙️</div>
                <div class="stat-value">${(today.transforms.summaries + today.transforms.embeddings + today.transforms.memories).toLocaleString()}</div>
                <div class="stat-label">Transforms</div>
                <div class="stat-detail">Processing operations</div>
            </div>
            <div class="stat-card stat-egress">
                <div class="stat-icon">⬆️</div>
                <div class="stat-value">${totalEgress.toLocaleString()}</div>
                <div class="stat-label">Data Egress</div>
                <div class="stat-detail">External API calls</div>
            </div>
            <div class="stat-card stat-cost">
                <div class="stat-icon">💰</div>
                <div class="stat-value">$${today.egress.llm_cost_usd.toFixed(4)}</div>
                <div class="stat-label">LLM Cost</div>
                <div class="stat-detail">${today.egress.llm_tokens_total.toLocaleString()} tokens</div>
            </div>
        `;
        container.appendChild(statsRow);

        // Two-column layout for details
        const detailsGrid = document.createElement('div');
        detailsGrid.className = 'data-flow-details-grid';

        // Ingress Details
        const ingressSection = document.createElement('div');
        ingressSection.className = 'flow-section ingress-section';
        ingressSection.innerHTML = `
            <h3 class="section-title">📥 Data Ingress</h3>
            <div class="flow-items">
                <div class="flow-item">
                    <span class="flow-source">📧 Gmail</span>
                    <span class="flow-count">${today.ingress.gmail_emails}</span>
                </div>
                <div class="flow-item">
                    <span class="flow-source">📅 Calendar</span>
                    <span class="flow-count">${today.ingress.calendar_events}</span>
                </div>
                <div class="flow-item">
                    <span class="flow-source">🏦 Plaid</span>
                    <span class="flow-count">${today.ingress.plaid_transactions}</span>
                </div>
                <div class="flow-item">
                    <span class="flow-source">📁 Files</span>
                    <span class="flow-count">${today.ingress.files_uploaded}</span>
                </div>
                <div class="flow-item">
                    <span class="flow-source">💬 Chat</span>
                    <span class="flow-count">${today.ingress.chat_messages}</span>
                </div>
            </div>
        `;
        detailsGrid.appendChild(ingressSection);

        // Egress Details
        const egressSection = document.createElement('div');
        egressSection.className = 'flow-section egress-section';
        egressSection.innerHTML = `
            <h3 class="section-title">📤 Data Egress</h3>
            <div class="flow-items">
                <div class="flow-item">
                    <span class="flow-source">🟣 Claude API</span>
                    <span class="flow-count">${today.egress.llm_calls_claude}</span>
                </div>
                <div class="flow-item">
                    <span class="flow-source">🟢 OpenAI API</span>
                    <span class="flow-count">${today.egress.llm_calls_openai}</span>
                </div>
                <div class="flow-item">
                    <span class="flow-source">🔵 Gemini API</span>
                    <span class="flow-count">${today.egress.llm_calls_gemini}</span>
                </div>
                <div class="flow-item">
                    <span class="flow-source">🌐 Browser</span>
                    <span class="flow-count">${today.egress.browser_automations}</span>
                </div>
            </div>
        `;
        detailsGrid.appendChild(egressSection);

        container.appendChild(detailsGrid);

        // Transforms Section
        const transformsSection = document.createElement('div');
        transformsSection.className = 'flow-section transforms-section';
        transformsSection.innerHTML = `
            <h3 class="section-title">⚙️ Data Transformations</h3>
            <div class="transforms-grid">
                <div class="transform-item">
                    <span class="transform-icon">📝</span>
                    <span class="transform-count">${today.transforms.summaries}</span>
                    <span class="transform-label">Summaries</span>
                </div>
                <div class="transform-item">
                    <span class="transform-icon">🔢</span>
                    <span class="transform-count">${today.transforms.embeddings}</span>
                    <span class="transform-label">Embeddings</span>
                </div>
                <div class="transform-item">
                    <span class="transform-icon">📚</span>
                    <span class="transform-count">${today.transforms.learning_signals}</span>
                    <span class="transform-label">Learnings</span>
                </div>
                <div class="transform-item">
                    <span class="transform-icon">💡</span>
                    <span class="transform-count">${today.transforms.knowledge_facts}</span>
                    <span class="transform-label">Facts</span>
                </div>
                <div class="transform-item">
                    <span class="transform-icon">🧠</span>
                    <span class="transform-count">${today.transforms.memories}</span>
                    <span class="transform-label">Memories</span>
                </div>
            </div>
        `;
        container.appendChild(transformsSection);

        // Integration Status Section
        if (data.integrations && data.integrations.length > 0) {
            const integrationsSection = document.createElement('div');
            integrationsSection.className = 'flow-section integrations-section';
            integrationsSection.innerHTML = `
                <h3 class="section-title">🔌 Integration Status</h3>
                <div class="integrations-grid">
                    ${data.integrations.map(i => `
                        <div class="integration-item ${i.is_connected ? 'connected' : 'disconnected'}">
                            <div class="integration-header">
                                <span class="integration-name">${escapeHtml(i.id)}</span>
                                <span class="integration-status ${i.health_status}">${i.health_status}</span>
                            </div>
                            <div class="integration-details">
                                <span>Items: ${i.items_synced.toLocaleString()}</span>
                                ${i.last_sync_at ? `<span>Last: ${formatRelativeTime(i.last_sync_at)}</span>` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            container.appendChild(integrationsSection);
        }

        // Weekly Trend (if we have data)
        if (data.week_trend && data.week_trend.length > 0) {
            const trendSection = document.createElement('div');
            trendSection.className = 'flow-section trend-section';
            trendSection.innerHTML = `
                <h3 class="section-title">📈 Weekly Trend</h3>
                <div class="trend-chart">
                    ${data.week_trend.slice(0, 7).reverse().map(day => {
                        const maxOps = Math.max(...data.week_trend.map(d => d.total_operations)) || 1;
                        const height = (day.total_operations / maxOps) * 100;
                        const dateLabel = new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' });
                        return `
                            <div class="trend-bar-container">
                                <div class="trend-bar" style="height: ${height}%">
                                    <span class="trend-value">${day.total_operations}</span>
                                </div>
                                <span class="trend-label">${dateLabel}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
            container.appendChild(trendSection);
        }

        // Recent Events Table
        if (data.recent_events && data.recent_events.length > 0) {
            const eventsSection = document.createElement('div');
            eventsSection.className = 'flow-section events-section';
            eventsSection.innerHTML = `
                <h3 class="section-title">🕐 Recent Events</h3>
                <div class="events-table-container">
                    <table class="events-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Type</th>
                                <th>Source</th>
                                <th>Operation</th>
                                <th>Destination</th>
                                <th>Status</th>
                                <th>Duration</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.recent_events.slice(0, 15).map(e => `
                                <tr class="${e.success ? '' : 'event-failed'}">
                                    <td>${formatRelativeTime(e.timestamp)}</td>
                                    <td><span class="event-type event-${e.event_type}">${e.event_type}</span></td>
                                    <td>${escapeHtml(e.source || '-')}</td>
                                    <td>${escapeHtml(e.operation || '-')}</td>
                                    <td>${escapeHtml(e.destination || '-')}</td>
                                    <td>${e.success ? '✅' : '❌'}</td>
                                    <td>${e.duration_ms ? e.duration_ms + 'ms' : '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            container.appendChild(eventsSection);
        }

        // End of Day Report Button
        const reportSection = document.createElement('div');
        reportSection.className = 'flow-section eod-report-section';
        reportSection.innerHTML = `
            <div class="eod-report-card">
                <div class="eod-report-info">
                    <h3>📊 End of Day Report</h3>
                    <p>Generate a comprehensive daily summary of all data flows and operations</p>
                </div>
                <button id="generate-eod-btn" class="eod-report-btn">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                    View Today's Report
                </button>
            </div>
            <div id="eod-report-display" class="eod-report-display hidden"></div>
        `;
        container.appendChild(reportSection);

        // Setup EOD report button
        document.getElementById('generate-eod-btn').addEventListener('click', async () => {
            await loadEndOfDayReport();
        });

    } catch (error) {
        container.innerHTML = `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <h3>Unable to Load Data Flow</h3>
                <p>${escapeHtml(error.message)}</p>
                <p class="error-hint">Make sure the audit system is initialized and the database migration has been run.</p>
                <button onclick="loadDataFlowDashboard(this.closest('.data-flow-dashboard'))" class="retry-btn">Retry</button>
            </div>
        `;
    }
}

/**
 * Load and display End of Day Report
 */
async function loadEndOfDayReport() {
    const display = document.getElementById('eod-report-display');
    display.classList.remove('hidden');
    display.innerHTML = '<div class="loading">Generating End of Day Report...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/v2/audit/report/today`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();

        display.innerHTML = `
            <div class="eod-report-content">
                <div class="eod-report-header">
                    <h3>📊 Data Flow Report - ${new Date().toLocaleDateString()}</h3>
                    <button class="close-btn" onclick="document.getElementById('eod-report-display').classList.add('hidden')">✕</button>
                </div>
                <pre class="eod-report-text">${escapeHtml(data.text_report)}</pre>
            </div>
        `;
    } catch (error) {
        display.innerHTML = `
            <div class="error-state">
                <p>Failed to load report: ${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

// ============================================================================
// GMAIL INTELLIGENCE VIEW
// ============================================================================

/**
 * Render the Gmail Intelligence View
 * Restructured tabs: Today | Inbox | Patterns
 * - Today: Action-focused (deadlines, action items, VIP emails)
 * - Inbox: Clean email list with filters
 * - Patterns: Analytics, trends, and sender insights
 */
async function renderGmailView(container) {
    container.innerHTML = ''; // Clear existing content

    // Header
    const header = document.createElement('div');
    header.className = 'view-header';
    header.innerHTML = `
        <h2>📧 Email Intelligence</h2>
        <p class="view-subtitle">AI-powered insights and smart prioritization</p>
    `;
    container.appendChild(header);

    // Connection status section
    const statusSection = document.createElement('div');
    statusSection.className = 'gmail-status-section';
    statusSection.innerHTML = '<div class="loading">Checking Gmail connection...</div>';
    container.appendChild(statusSection);

    // Check connection status
    try {
        const status = await fetch(`${API_BASE}/api/gmail/status`).then(r => r.json());
        renderGmailStatus(statusSection, status);

        if (status.connected) {
            // Tab navigation - Restructured: Today | Inbox | Patterns
            const tabNav = document.createElement('div');
            tabNav.className = 'email-tabs';
            tabNav.innerHTML = `
                <button class="email-tab-btn active" data-tab="today">⚡ Today</button>
                <button class="email-tab-btn" data-tab="inbox">📬 Inbox</button>
                <button class="email-tab-btn" data-tab="patterns">📊 Patterns</button>
            `;
            container.appendChild(tabNav);

            // Tab content container
            const tabContent = document.createElement('div');
            tabContent.className = 'email-tab-content';
            container.appendChild(tabContent);

            // Tab switching logic
            let currentTab = 'today';
            const tabButtons = tabNav.querySelectorAll('.email-tab-btn');

            const loadTab = async (tab) => {
                currentTab = tab;
                tabContent.innerHTML = '<div class="loading">Loading...</div>';

                switch(tab) {
                    case 'today':
                        await loadTodayTab(tabContent, status.email);
                        break;
                    case 'inbox':
                        await loadInboxTab(tabContent, status.email);
                        break;
                    case 'patterns':
                        await loadPatternsTab(tabContent);
                        break;
                }
            };

            tabButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    tabButtons.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    loadTab(btn.dataset.tab);
                });
            });

            // Load default tab (Today - action focused)
            await loadTab('today');
        }
    } catch (error) {
        statusSection.innerHTML = `
            <div class="gmail-error">
                <p>⚠️ Failed to check Gmail status: ${escapeHtml(error.message)}</p>
                <p class="hint">Make sure the API server is running.</p>
            </div>
        `;
    }
}

/**
 * TODAY TAB - Action-focused unified view
 * "What do I need to do?"
 * Combines: Action items, deadlines, VIP/high-priority emails
 */
async function loadTodayTab(container, userEmail) {
    const state = {
        actionItems: [],
        deadlines: [],
        vipEmails: [],
        stats: {},
        loading: false,
        completedItems: new Set() // Track dismissed items
    };

    const render = () => {
        container.innerHTML = '';

        // Header with refresh
        const header = document.createElement('div');
        header.className = 'today-tab-header';
        header.innerHTML = `
            <div class="today-header-content">
                <h3>Today's Focus</h3>
                <p class="today-subtitle">Action items, deadlines, and priority emails</p>
            </div>
            <button class="refresh-btn" title="Refresh">
                <span class="refresh-icon ${state.loading ? 'spinning' : ''}">🔄</span>
            </button>
        `;
        header.querySelector('.refresh-btn').addEventListener('click', fetchAndRender);
        container.appendChild(header);

        // Quick stats row
        const statsRow = document.createElement('div');
        statsRow.className = 'today-stats-row';
        const actionCount = state.actionItems.filter(i => !state.completedItems.has(i.id)).length;
        const deadlineCount = state.deadlines.filter(i => !state.completedItems.has(i.id)).length;
        const vipCount = state.vipEmails.length;
        const totalAttention = actionCount + deadlineCount + vipCount;

        statsRow.innerHTML = `
            <div class="today-stat ${totalAttention === 0 ? 'success' : ''}">
                <span class="stat-value">${totalAttention}</span>
                <span class="stat-label">${totalAttention === 0 ? 'All clear!' : 'needs attention'}</span>
            </div>
            <div class="today-stat-pills">
                ${actionCount > 0 ? `<span class="stat-pill action">✅ ${actionCount} actions</span>` : ''}
                ${deadlineCount > 0 ? `<span class="stat-pill deadline">⏰ ${deadlineCount} deadlines</span>` : ''}
                ${vipCount > 0 ? `<span class="stat-pill vip">🔴 ${vipCount} VIP unread</span>` : ''}
            </div>
        `;
        container.appendChild(statsRow);

        // Main content sections
        const mainContent = document.createElement('div');
        mainContent.className = 'today-main-content';

        // Section: Urgent (Deadlines happening soon)
        if (state.deadlines.length > 0) {
            const urgentSection = createTodaySection('⏰ Deadlines', state.deadlines, 'deadline');
            mainContent.appendChild(urgentSection);
        }

        // Section: Action Items
        if (state.actionItems.length > 0) {
            const actionsSection = createTodaySection('✅ Action Required', state.actionItems, 'action');
            mainContent.appendChild(actionsSection);
        }

        // Section: VIP Emails (high priority unread)
        if (state.vipEmails.length > 0) {
            const vipSection = document.createElement('div');
            vipSection.className = 'today-section vip';
            vipSection.innerHTML = `
                <div class="today-section-header">
                    <h4>🔴 VIP Waiting</h4>
                    <span class="section-count">${state.vipEmails.length} unread</span>
                </div>
            `;

            const emailList = document.createElement('div');
            emailList.className = 'today-email-list';

            state.vipEmails.slice(0, 5).forEach(email => {
                const item = document.createElement('div');
                item.className = 'today-email-item';
                item.innerHTML = `
                    <div class="email-priority-indicator high"></div>
                    <div class="email-content">
                        <div class="email-sender">${escapeHtml(email.from)}</div>
                        <div class="email-subject">${escapeHtml(email.subject)}</div>
                        <div class="email-snippet">${escapeHtml(email.snippet || '').substring(0, 80)}...</div>
                    </div>
                    <div class="email-actions">
                        <button class="action-btn open" title="Open in Gmail">↗️</button>
                    </div>
                `;

                item.querySelector('.open').addEventListener('click', () => {
                    const gmailUrl = `https://mail.google.com/mail/u/0/#inbox/${email.id}`;
                    require('electron').shell.openExternal(gmailUrl);
                });

                emailList.appendChild(item);
            });

            if (state.vipEmails.length > 5) {
                const showMore = document.createElement('button');
                showMore.className = 'show-more-btn';
                showMore.textContent = `Show all ${state.vipEmails.length} VIP emails`;
                showMore.addEventListener('click', () => {
                    document.querySelector('.email-tab-btn[data-tab="inbox"]')?.click();
                });
                emailList.appendChild(showMore);
            }

            vipSection.appendChild(emailList);
            mainContent.appendChild(vipSection);
        }

        // Empty state
        if (totalAttention === 0 && !state.loading) {
            const emptyState = document.createElement('div');
            emptyState.className = 'today-empty-state';
            emptyState.innerHTML = `
                <div class="empty-icon">🎉</div>
                <h3>You're all caught up!</h3>
                <p>No action items, deadlines, or VIP emails waiting</p>
            `;
            mainContent.appendChild(emptyState);
        }

        container.appendChild(mainContent);
    };

    // Helper to create action/deadline sections
    const createTodaySection = (title, items, type) => {
        const section = document.createElement('div');
        section.className = `today-section ${type}`;

        const visibleItems = items.filter(i => !state.completedItems.has(i.id));

        section.innerHTML = `
            <div class="today-section-header">
                <h4>${title}</h4>
                <span class="section-count">${visibleItems.length} items</span>
            </div>
        `;

        const list = document.createElement('div');
        list.className = 'today-items-list';

        visibleItems.slice(0, 10).forEach(item => {
            const itemEl = document.createElement('div');
            itemEl.className = 'today-item';
            itemEl.innerHTML = `
                <div class="item-checkbox">
                    <button class="check-btn" title="Mark done">○</button>
                </div>
                <div class="item-content">
                    <div class="item-text">${escapeHtml(item.summary || item.insight_text || '')}</div>
                    ${item.sender ? `<div class="item-sender">From: ${escapeHtml(item.sender)}</div>` : ''}
                </div>
                ${item.source_id ? `
                    <button class="view-email-btn" data-id="${item.source_id}" title="View email">📧</button>
                ` : ''}
            `;

            // Mark done handler
            itemEl.querySelector('.check-btn').addEventListener('click', () => {
                state.completedItems.add(item.id);
                itemEl.classList.add('completed');
                setTimeout(() => render(), 300);
            });

            // View email handler
            const viewBtn = itemEl.querySelector('.view-email-btn');
            if (viewBtn) {
                viewBtn.addEventListener('click', () => {
                    const gmailUrl = `https://mail.google.com/mail/u/0/#inbox/${item.source_id}`;
                    require('electron').shell.openExternal(gmailUrl);
                });
            }

            list.appendChild(itemEl);
        });

        section.appendChild(list);
        return section;
    };

    // Fetch data
    const fetchAndRender = async () => {
        state.loading = true;
        render();

        try {
            // Fetch in parallel: insights (actions + deadlines) and VIP emails
            const [insightsResp, priorityResp] = await Promise.all([
                fetch(`${API_BASE}/email/insights?limit=100`).then(r => r.json()).catch(() => ({})),
                fetch(`${API_BASE}/email/priority?limit=20`).then(r => r.json()).catch(() => ({}))
            ]);

            // Extract action items and deadlines
            const allInsights = insightsResp.insights || [];
            state.actionItems = allInsights.filter(i => i.type === 'action_item');
            state.deadlines = allInsights.filter(i => i.type === 'deadline');

            // Get VIP emails (high priority tier)
            state.vipEmails = priorityResp.high_priority || [];

            state.stats = {
                unread: insightsResp.summary?.total || 0
            };

            state.loading = false;
            render();
        } catch (error) {
            state.loading = false;
            container.innerHTML = `
                <div class="email-error">
                    <p>⚠️ Failed to load: ${escapeHtml(error.message)}</p>
                    <button class="retry-btn">Retry</button>
                </div>
            `;
            container.querySelector('.retry-btn')?.addEventListener('click', fetchAndRender);
        }
    };

    await fetchAndRender();
}

/**
 * INBOX TAB - Clean email list with filters
 * "Browse my mail"
 * Simplified: Just the email list with filter options
 */
async function loadInboxTab(container, userEmail) {
    container.innerHTML = '';

    // Filter bar
    const filterBar = document.createElement('div');
    filterBar.className = 'inbox-filter-bar';
    filterBar.innerHTML = `
        <div class="filter-group">
            <button class="filter-btn active" data-filter="all">All Mail</button>
            <button class="filter-btn" data-filter="unread">Unread</button>
            <button class="filter-btn" data-filter="starred">Starred</button>
        </div>
        <div class="search-box">
            <input type="text" placeholder="Search by sender..." class="sender-search" />
        </div>
    `;
    container.appendChild(filterBar);

    // Inbox section
    const inboxSection = document.createElement('div');
    inboxSection.className = 'gmail-inbox-section';
    container.appendChild(inboxSection);

    // Current filter state
    let currentFilter = 'all';
    let searchQuery = '';

    // Filter handlers
    const filterBtns = filterBar.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            loadEmails();
        });
    });

    // Search handler
    const searchInput = filterBar.querySelector('.sender-search');
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchQuery = e.target.value;
            loadEmails();
        }, 300);
    });

    // Load emails with filters
    const loadEmails = async () => {
        inboxSection.innerHTML = '<div class="loading">Loading emails...</div>';

        try {
            let query = currentFilter === 'unread' ? 'is:unread'
                      : currentFilter === 'starred' ? 'is:starred'
                      : '';

            if (searchQuery) {
                query += (query ? ' ' : '') + `from:${searchQuery}`;
            }

            await renderGmailInbox(inboxSection, userEmail, query || null);
        } catch (error) {
            inboxSection.innerHTML = `<div class="email-error">Failed to load emails</div>`;
        }
    };

    // Initial load
    await loadEmails();
}

/**
 * Load Email Insights tab - Interactive filtering and source email linking
 * P0: Clickable hero cards, filter state, source email links
 * P2: Pagination, refresh button
 */
async function loadInsightsTab(container) {
    // State management for this tab
    const state = {
        allInsights: [],
        filteredInsights: [],
        summary: {},
        activeFilter: null,
        visibleCount: 20,
        loading: false
    };

    const typeIcons = {
        'topic': '📝',
        'action_item': '✅',
        'deadline': '⏰',
        'relationship': '👤',
        'decision': '⚖️',
        'fact': '💡'
    };

    const typeLabels = {
        'topic': 'Topics',
        'action_item': 'Action Items',
        'deadline': 'Deadlines',
        'relationship': 'Key Contacts',
        'decision': 'Decisions',
        'fact': 'Facts'
    };

    // Render function - can be called to refresh UI without fetching
    const render = () => {
        container.innerHTML = '';

        // Header with refresh button
        const header = document.createElement('div');
        header.className = 'insights-tab-header';
        header.innerHTML = `
            <h3>Email Insights</h3>
            <button class="refresh-btn" title="Refresh insights">
                <span class="refresh-icon ${state.loading ? 'spinning' : ''}">🔄</span>
            </button>
        `;
        header.querySelector('.refresh-btn').addEventListener('click', () => fetchAndRender());
        container.appendChild(header);

        // Hero stats row - CLICKABLE
        const heroStats = document.createElement('div');
        heroStats.className = 'email-insights-hero';

        // Total card (clears filter)
        const totalCard = document.createElement('div');
        totalCard.className = `hero-stat clickable ${!state.activeFilter ? 'active' : ''}`;
        totalCard.innerHTML = `
            <div class="hero-value">${state.filteredInsights.length.toLocaleString()}</div>
            <div class="hero-label">${state.activeFilter ? 'Showing' : 'Total'}</div>
        `;
        totalCard.addEventListener('click', () => {
            state.activeFilter = null;
            state.filteredInsights = state.allInsights;
            state.visibleCount = 20;
            render();
        });
        heroStats.appendChild(totalCard);

        // Type filter cards
        ['action_item', 'deadline', 'relationship'].forEach(type => {
            const count = state.summary[type] || 0;
            const card = document.createElement('div');
            card.className = `hero-stat clickable ${state.activeFilter === type ? 'active' : ''} ${count === 0 ? 'disabled' : ''}`;
            card.innerHTML = `
                <div class="hero-value">${count}</div>
                <div class="hero-label">${typeLabels[type] || type}</div>
            `;
            if (count > 0) {
                card.addEventListener('click', () => {
                    state.activeFilter = type;
                    state.filteredInsights = state.allInsights.filter(i => i.type === type);
                    state.visibleCount = 20;
                    render();
                });
            }
            heroStats.appendChild(card);
        });

        container.appendChild(heroStats);

        // Active filter indicator
        if (state.activeFilter) {
            const filterBar = document.createElement('div');
            filterBar.className = 'active-filter-bar';
            filterBar.innerHTML = `
                <span class="filter-label">Filtered by:</span>
                <span class="filter-chip">
                    ${typeIcons[state.activeFilter] || '📌'} ${typeLabels[state.activeFilter] || state.activeFilter}
                    <button class="clear-filter-btn" title="Clear filter">✕</button>
                </span>
                <span class="filter-count">${state.filteredInsights.length} results</span>
            `;
            filterBar.querySelector('.clear-filter-btn').addEventListener('click', () => {
                state.activeFilter = null;
                state.filteredInsights = state.allInsights;
                state.visibleCount = 20;
                render();
            });
            container.appendChild(filterBar);
        }

        // Quick type pills (all types)
        const typePills = document.createElement('div');
        typePills.className = 'insight-type-pills';
        Object.entries(state.summary).forEach(([type, count]) => {
            if (count === 0) return;
            const pill = document.createElement('button');
            pill.className = `type-pill ${state.activeFilter === type ? 'active' : ''}`;
            pill.innerHTML = `${typeIcons[type] || '📌'} ${type.replace('_', ' ')} <span class="pill-count">${count}</span>`;
            pill.addEventListener('click', () => {
                state.activeFilter = state.activeFilter === type ? null : type;
                state.filteredInsights = state.activeFilter
                    ? state.allInsights.filter(i => i.type === type)
                    : state.allInsights;
                state.visibleCount = 20;
                render();
            });
            typePills.appendChild(pill);
        });
        container.appendChild(typePills);

        // Insights list
        const listSection = document.createElement('div');
        listSection.className = 'insights-list-section';

        const insightsList = document.createElement('div');
        insightsList.className = 'insights-list';

        const visibleInsights = state.filteredInsights.slice(0, state.visibleCount);

        if (visibleInsights.length === 0) {
            insightsList.innerHTML = `
                <div class="empty-insights">
                    <p>No ${state.activeFilter ? typeLabels[state.activeFilter].toLowerCase() : 'insights'} found.</p>
                </div>
            `;
        } else {
            visibleInsights.forEach(insight => {
                const icon = typeIcons[insight.type] || '📌';
                const methodBadge = insight.extraction_method === 'llm'
                    ? '<span class="method-badge llm">AI</span>'
                    : '<span class="method-badge rule">Auto</span>';

                // Parse entities for sender info
                let senderEmail = '';
                let senderName = '';
                try {
                    const entities = typeof insight.entities === 'string'
                        ? JSON.parse(insight.entities)
                        : insight.entities;
                    if (entities?.people?.length > 0) {
                        senderEmail = entities.people[0];
                        senderName = senderEmail.split('@')[0];
                    }
                } catch (e) {}

                const item = document.createElement('div');
                item.className = 'insight-item clickable';
                item.innerHTML = `
                    <span class="insight-icon">${icon}</span>
                    <div class="insight-content">
                        <div class="insight-summary">${escapeHtml(insight.summary || '')}</div>
                        <div class="insight-meta">
                            <span class="insight-type-badge">${insight.type.replace('_', ' ')}</span>
                            ${methodBadge}
                            ${senderName ? `<span class="insight-sender">from ${escapeHtml(senderName)}</span>` : ''}
                            <span class="insight-date">${insight.date ? new Date(insight.date).toLocaleDateString() : ''}</span>
                        </div>
                    </div>
                    <div class="insight-actions">
                        ${senderEmail ? `<button class="insight-action-btn view-email" title="View emails from this sender" data-email="${escapeHtml(senderEmail)}">📧</button>` : ''}
                    </div>
                `;

                // Click on item to filter by sender
                if (senderEmail) {
                    item.querySelector('.view-email')?.addEventListener('click', (e) => {
                        e.stopPropagation();
                        // Switch to inbox tab and filter by sender
                        switchToInboxWithFilter(senderEmail, senderName);
                    });
                }

                insightsList.appendChild(item);
            });
        }

        listSection.appendChild(insightsList);

        // Load more button
        if (state.filteredInsights.length > state.visibleCount) {
            const loadMoreBtn = document.createElement('button');
            loadMoreBtn.className = 'load-more-btn';
            loadMoreBtn.innerHTML = `Show more (${state.filteredInsights.length - state.visibleCount} remaining)`;
            loadMoreBtn.addEventListener('click', () => {
                state.visibleCount += 20;
                render();
            });
            listSection.appendChild(loadMoreBtn);
        }

        container.appendChild(listSection);
    };

    // Fetch data and render
    const fetchAndRender = async () => {
        state.loading = true;
        render(); // Show loading state

        try {
            const response = await fetch(`${API_BASE}/email/insights?limit=200`);
            const data = await response.json();

            if (data.status !== 'success') {
                throw new Error(data.detail || 'Failed to load insights');
            }

            state.allInsights = data.insights || [];
            state.summary = data.summary || {};
            state.filteredInsights = state.activeFilter
                ? state.allInsights.filter(i => i.type === state.activeFilter)
                : state.allInsights;
            state.loading = false;

            render();
        } catch (error) {
            state.loading = false;
            container.innerHTML = `
                <div class="email-error">
                    <p>⚠️ Failed to load insights: ${escapeHtml(error.message)}</p>
                    <button class="retry-btn" onclick="this.parentElement.parentElement.querySelector('.refresh-btn')?.click()">Retry</button>
                </div>
            `;
        }
    };

    // Helper to switch to inbox tab with filter
    const switchToInboxWithFilter = (email, name) => {
        // Find the inbox tab button and click it
        const inboxTab = document.querySelector('.email-tab-btn[data-tab="inbox"]');
        if (inboxTab) {
            inboxTab.click();
            // After a short delay, trigger the sender filter
            setTimeout(() => {
                const senderChip = document.querySelector(`[data-sender-email="${email}"]`);
                if (senderChip) {
                    senderChip.click();
                } else {
                    // If chip doesn't exist, we need to manually filter
                    const inboxSection = document.querySelector('.gmail-inbox-section');
                    if (inboxSection && window.renderGmailInbox) {
                        // This would require exposing the function globally or via events
                        console.log('Filter inbox by:', email);
                    }
                }
            }, 300);
        }
    };

    // Initial load
    await fetchAndRender();
}

/**
 * PATTERNS TAB - Analytics and trends
 * "Teach me about my email habits"
 * Shows: Top senders, topics, insight types, sender priority distribution
 */
async function loadPatternsTab(container) {
    const state = {
        insights: {},
        priority: {},
        stats: {},
        loading: false
    };

    const render = () => {
        container.innerHTML = '';

        // Header with refresh
        const header = document.createElement('div');
        header.className = 'patterns-tab-header';
        header.innerHTML = `
            <div class="patterns-header-content">
                <h3>Email Patterns</h3>
                <p class="patterns-subtitle">Insights about your inbox and senders</p>
            </div>
            <button class="refresh-btn" title="Refresh">
                <span class="refresh-icon ${state.loading ? 'spinning' : ''}">🔄</span>
            </button>
        `;
        header.querySelector('.refresh-btn').addEventListener('click', fetchAndRender);
        container.appendChild(header);

        if (state.loading && !state.insights.summary) {
            container.innerHTML += '<div class="loading">Analyzing patterns...</div>';
            return;
        }

        const mainContent = document.createElement('div');
        mainContent.className = 'patterns-main-content';

        // Section 1: Top Senders
        if (state.insights.top_senders?.length > 0) {
            const sendersSection = document.createElement('div');
            sendersSection.className = 'patterns-section';
            sendersSection.innerHTML = `
                <div class="patterns-section-header">
                    <h4>📊 Top Senders</h4>
                    <span class="section-subtitle">Who emails you most</span>
                </div>
            `;

            const sendersList = document.createElement('div');
            sendersList.className = 'top-senders-list';

            state.insights.top_senders.slice(0, 8).forEach((sender, idx) => {
                const item = document.createElement('div');
                item.className = 'sender-item';
                const name = sender.email.split('@')[0];
                const domain = sender.email.split('@')[1];
                item.innerHTML = `
                    <span class="sender-rank">#${idx + 1}</span>
                    <div class="sender-info">
                        <span class="sender-name">${escapeHtml(name)}</span>
                        <span class="sender-domain">@${escapeHtml(domain)}</span>
                    </div>
                    <span class="sender-count">${sender.count} emails</span>
                `;
                sendersList.appendChild(item);
            });

            sendersSection.appendChild(sendersList);
            mainContent.appendChild(sendersSection);
        }

        // Section 2: Insight Types Distribution
        if (state.insights.summary) {
            const insightsSection = document.createElement('div');
            insightsSection.className = 'patterns-section';
            insightsSection.innerHTML = `
                <div class="patterns-section-header">
                    <h4>💡 What's In Your Emails</h4>
                    <span class="section-subtitle">Extracted insights by type</span>
                </div>
            `;

            const typeIcons = {
                'topic': '📝',
                'action_item': '✅',
                'deadline': '⏰',
                'relationship': '👤',
                'decision': '⚖️',
                'fact': '💡'
            };

            const insightTypes = document.createElement('div');
            insightTypes.className = 'insight-types-grid';

            const summary = state.insights.summary;
            const types = ['action_item', 'deadline', 'relationship', 'topic'];
            const total = types.reduce((sum, t) => sum + (summary[t] || 0), 0);

            types.forEach(type => {
                const count = summary[type] || 0;
                if (count === 0) return;

                const pct = total > 0 ? ((count / total) * 100).toFixed(0) : 0;
                const typeCard = document.createElement('div');
                typeCard.className = 'insight-type-stat';
                typeCard.innerHTML = `
                    <span class="type-icon">${typeIcons[type] || '📌'}</span>
                    <span class="type-count">${count}</span>
                    <span class="type-name">${type.replace('_', ' ')}</span>
                    <div class="type-bar">
                        <div class="type-bar-fill" style="width: ${pct}%"></div>
                    </div>
                `;
                insightTypes.appendChild(typeCard);
            });

            insightsSection.appendChild(insightTypes);
            mainContent.appendChild(insightsSection);
        }

        // Section 3: Sender Priority Distribution
        if (state.priority.counts) {
            const prioritySection = document.createElement('div');
            prioritySection.className = 'patterns-section';
            prioritySection.innerHTML = `
                <div class="patterns-section-header">
                    <h4>🎯 Sender Priority Breakdown</h4>
                    <span class="section-subtitle">How senders are ranked</span>
                </div>
            `;

            const tierConfig = {
                high: { icon: '🔴', label: 'VIP', color: '#f44336' },
                medium: { icon: '🟡', label: 'Regular', color: '#FF9800' },
                low: { icon: '🟢', label: 'Low Priority', color: '#4CAF50' },
                unscored: { icon: '⚪', label: 'Unknown', color: '#666' }
            };

            const priorityBars = document.createElement('div');
            priorityBars.className = 'priority-distribution';

            const counts = state.priority.counts || {};
            const totalUnread = Object.values(counts).reduce((s, c) => s + c, 0) || 1;

            ['high', 'medium', 'low', 'unscored'].forEach(tier => {
                const count = counts[tier] || 0;
                const pct = ((count / totalUnread) * 100).toFixed(0);
                const config = tierConfig[tier];

                const bar = document.createElement('div');
                bar.className = 'priority-bar-item';
                bar.innerHTML = `
                    <div class="priority-bar-label">
                        <span class="tier-icon">${config.icon}</span>
                        <span class="tier-name">${config.label}</span>
                    </div>
                    <div class="priority-bar-track">
                        <div class="priority-bar-fill" style="width: ${pct}%; background: ${config.color}"></div>
                    </div>
                    <span class="priority-bar-count">${count}</span>
                `;
                priorityBars.appendChild(bar);
            });

            prioritySection.appendChild(priorityBars);

            // Tip
            const tip = document.createElement('div');
            tip.className = 'patterns-tip';
            tip.innerHTML = `💡 <strong>Tip:</strong> Star emails or reply to senders to increase their priority score`;
            prioritySection.appendChild(tip);

            mainContent.appendChild(prioritySection);
        }

        // Section 4: Topics (if available)
        const topics = state.insights.insights?.filter(i => i.type === 'topic') || [];
        if (topics.length > 0) {
            const topicsSection = document.createElement('div');
            topicsSection.className = 'patterns-section';
            topicsSection.innerHTML = `
                <div class="patterns-section-header">
                    <h4>🏷️ Common Topics</h4>
                    <span class="section-subtitle">What you're discussing</span>
                </div>
            `;

            const topicsCloud = document.createElement('div');
            topicsCloud.className = 'topics-cloud';

            // Get unique topics (by summary text)
            const uniqueTopics = [...new Set(topics.map(t => t.summary || t.insight_text))].slice(0, 15);
            uniqueTopics.forEach(topic => {
                const tag = document.createElement('span');
                tag.className = 'topic-tag';
                tag.textContent = topic.length > 30 ? topic.substring(0, 30) + '...' : topic;
                topicsCloud.appendChild(tag);
            });

            topicsSection.appendChild(topicsCloud);
            mainContent.appendChild(topicsSection);
        }

        // Empty state
        if (!state.insights.summary && !state.priority.counts) {
            const emptyState = document.createElement('div');
            emptyState.className = 'patterns-empty-state';
            emptyState.innerHTML = `
                <div class="empty-icon">📊</div>
                <h3>No patterns yet</h3>
                <p>Connect Gmail and receive some emails to see patterns</p>
            `;
            mainContent.appendChild(emptyState);
        }

        container.appendChild(mainContent);
    };

    // Fetch data
    const fetchAndRender = async () => {
        state.loading = true;
        render();

        try {
            // Fetch insights and priority data in parallel
            const [insightsResp, priorityResp] = await Promise.all([
                fetch(`${API_BASE}/email/insights?limit=200`).then(r => r.json()).catch(() => ({})),
                fetch(`${API_BASE}/email/priority?limit=50`).then(r => r.json()).catch(() => ({}))
            ]);

            state.insights = insightsResp;
            state.priority = priorityResp;
            state.loading = false;
            render();
        } catch (error) {
            state.loading = false;
            container.innerHTML = `
                <div class="email-error">
                    <p>⚠️ Failed to load patterns: ${escapeHtml(error.message)}</p>
                    <button class="retry-btn">Retry</button>
                </div>
            `;
            container.querySelector('.retry-btn')?.addEventListener('click', fetchAndRender);
        }
    };

    await fetchAndRender();
}

/**
 * Render Daily Brief - Compact horizontal bar
 */
async function renderDailyBrief(container) {
    container.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE}/api/gmail/daily-brief`);
        const brief = await response.json();

        // Compact single-line format
        container.innerHTML = `
            <div class="daily-brief-bar">
                <span class="brief-headline-compact">${brief.headline || '📬 Inbox'}</span>
                <span class="brief-stats-compact">
                    <span>${brief.stats?.total || 0} total</span>
                    <span class="unread">${brief.stats?.unread || 0} unread</span>
                    ${brief.stats?.priority > 0 ? `<span class="priority">${brief.stats.priority} priority</span>` : ''}
                </span>
            </div>
        `;
    } catch (error) {
        container.innerHTML = '';
    }
}

/**
 * Render Inbox Insights - Clickable sender chips + learning signals
 * Clicking a sender chip filters the email list to show only from that sender
 */
async function renderInboxInsights(container, onSenderClick = null) {
    container.innerHTML = '<div class="loading-small">Loading insights...</div>';

    try {
        // Fetch both insights and learning signal stats
        const [insightsResp, actionsResp] = await Promise.all([
            fetch(`${API_BASE}/api/gmail/insights?limit=50`),
            fetch(`${API_BASE}/api/gmail/actions/stats?days=30`).catch(() => null)
        ]);

        const insights = await insightsResp.json();
        const actionStats = actionsResp ? await actionsResp.json().catch(() => ({})) : {};

        // Build insights panel
        container.innerHTML = '';

        const insightsPanel = document.createElement('div');
        insightsPanel.className = 'email-insights-panel';

        // Top Senders Section (Clickable)
        if (insights.top_senders && insights.top_senders.length > 0) {
            const sendersSection = document.createElement('div');
            sendersSection.className = 'insights-section-compact';
            sendersSection.innerHTML = '<span class="insights-label">📊 Top Senders</span>';

            const chipsContainer = document.createElement('div');
            chipsContainer.className = 'sender-chips';

            // Show up to 5 top senders as clickable chips
            insights.top_senders.slice(0, 5).forEach(sender => {
                const senderName = sender.email.split('@')[0];
                const chip = document.createElement('button');
                chip.className = 'sender-chip clickable';
                chip.innerHTML = `${escapeHtml(senderName)} <span class="chip-count">${sender.count}</span>`;
                chip.setAttribute('data-sender-email', sender.email);
                chip.title = `Filter emails from ${sender.email}`;

                chip.addEventListener('click', () => {
                    if (onSenderClick) {
                        onSenderClick(sender.email, senderName);
                    }
                });

                chipsContainer.appendChild(chip);
            });

            sendersSection.appendChild(chipsContainer);
            insightsPanel.appendChild(sendersSection);
        }

        // Inbox Stats Row
        const statsRow = document.createElement('div');
        statsRow.className = 'insights-stats-row';
        statsRow.innerHTML = `
            <span class="insight-stat">
                <span class="stat-value">${insights.unread_count || 0}</span>
                <span class="stat-label">unread</span>
            </span>
            <span class="insight-stat">
                <span class="stat-value">${insights.priority_count || 0}</span>
                <span class="stat-label">priority</span>
            </span>
            <span class="insight-stat">
                <span class="stat-value">${insights.external_count || 0}</span>
                <span class="stat-label">external</span>
            </span>
            <span class="insight-stat">
                <span class="stat-value">${insights.internal_count || 0}</span>
                <span class="stat-label">internal</span>
            </span>
        `;
        insightsPanel.appendChild(statsRow);

        // Learning Signals Section (if we have data)
        if (actionStats.total_signals > 0 || actionStats.action_counts) {
            const learningSection = document.createElement('div');
            learningSection.className = 'insights-section-compact learning';

            const openCount = actionStats.action_counts?.open_in_gmail || 0;
            const starCount = actionStats.action_counts?.star || 0;

            learningSection.innerHTML = `
                <span class="insights-label">🧠 Your Activity (30d)</span>
                <div class="learning-stats">
                    <span class="learning-stat" title="Emails opened in Gmail">
                        <span class="stat-icon">👆</span> ${openCount} opened
                    </span>
                    <span class="learning-stat" title="Emails starred">
                        <span class="stat-icon">⭐</span> ${starCount} starred
                    </span>
                    <span class="learning-stat subtle" title="Total learning signals captured">
                        ${actionStats.total_signals || 0} signals
                    </span>
                </div>
            `;
            insightsPanel.appendChild(learningSection);
        }

        // Any active insights/alerts
        if (insights.insights && insights.insights.length > 0) {
            const alertsSection = document.createElement('div');
            alertsSection.className = 'insights-alerts';

            insights.insights.forEach(insight => {
                const severityIcon = insight.severity === 'high' ? '🔴' :
                                    insight.severity === 'medium' ? '🟡' : '💡';
                const alert = document.createElement('div');
                alert.className = `insight-alert ${insight.severity || 'info'}`;
                alert.innerHTML = `${severityIcon} ${escapeHtml(insight.message)}`;
                alertsSection.appendChild(alert);
            });

            insightsPanel.appendChild(alertsSection);
        }

        container.appendChild(insightsPanel);

    } catch (error) {
        console.error('Failed to load insights:', error);
        container.innerHTML = '';
    }
}

/**
 * Render Gmail connection status
 */
function renderGmailStatus(container, status) {
    container.innerHTML = '';

    const statusCard = document.createElement('div');
    statusCard.className = `gmail-status-card ${status.connected ? 'connected' : 'disconnected'}`;

    if (status.connected) {
        statusCard.innerHTML = `
            <div class="gmail-status-header">
                <span class="status-icon">✅</span>
                <span class="status-text">Connected</span>
            </div>
            <div class="gmail-status-details">
                <p class="gmail-email">${escapeHtml(status.email)}</p>
                <p class="gmail-scopes">Scopes: ${status.scopes.length > 0 ? status.scopes.map(s => s.split('/').pop()).join(', ') : 'gmail.readonly'}</p>
            </div>
            <button id="gmail-disconnect-btn" class="btn-secondary gmail-disconnect-btn">Disconnect</button>
        `;
    } else {
        statusCard.innerHTML = `
            <div class="gmail-status-header">
                <span class="status-icon">🔗</span>
                <span class="status-text">Not Connected</span>
            </div>
            <div class="gmail-status-details">
                <p>Connect your Gmail account to see email insights.</p>
                <p class="hint">Read-only access - we never send or delete emails.</p>
            </div>
            <button id="gmail-connect-btn" class="btn-primary gmail-connect-btn">Connect Gmail</button>
        `;
    }

    container.appendChild(statusCard);

    // Setup event listeners
    setTimeout(() => {
        const connectBtn = document.getElementById('gmail-connect-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', handleGmailConnect);
        }

        const disconnectBtn = document.getElementById('gmail-disconnect-btn');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', handleGmailDisconnect);
        }
    }, 0);
}

/**
 * Track email action for learning signals
 * Non-blocking - fires and forgets to not slow down user actions
 *
 * @param {string} messageId - Gmail message ID
 * @param {string} senderEmail - Sender's email address
 * @param {string} actionType - Type of action: 'open_in_gmail', 'star', 'archive', etc.
 * @param {Object} metadata - Optional additional metadata
 */
function trackEmailAction(messageId, senderEmail, actionType, metadata = null) {
    // Fire and forget - don't await
    fetch(`${API_BASE}/api/gmail/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            gmail_message_id: messageId,
            sender_email: senderEmail || 'unknown',
            action_type: actionType,
            action_metadata: metadata,
        }),
    }).then(response => {
        if (!response.ok) {
            console.warn(`[Learning] Failed to track action: ${actionType}`);
        } else {
            console.log(`[Learning] Tracked: ${actionType} for ${senderEmail}`);
        }
    }).catch(err => {
        console.warn(`[Learning] Error tracking action: ${err.message}`);
    });
}

/**
 * Handle Gmail connect button click
 */
async function handleGmailConnect() {
    try {
        const response = await fetch(`${API_BASE}/api/gmail/connect`);
        const data = await response.json();

        if (data.auth_url) {
            // Open OAuth URL in browser
            window.open(data.auth_url, '_blank');

            // Show instructions
            const statusSection = document.querySelector('.gmail-status-section');
            if (statusSection) {
                statusSection.innerHTML += `
                    <div class="gmail-oauth-instructions">
                        <p>📋 Complete authorization in your browser, then click Refresh.</p>
                        <button id="gmail-refresh-status" class="btn-secondary">Refresh Status</button>
                    </div>
                `;
                document.getElementById('gmail-refresh-status').addEventListener('click', () => {
                    location.reload();
                });
            }
        }
    } catch (error) {
        alert('Failed to initiate Gmail connection: ' + error.message);
    }
}

/**
 * Handle Gmail disconnect button click
 */
async function handleGmailDisconnect() {
    if (!confirm('Disconnect Gmail? You can reconnect anytime.')) return;

    try {
        await fetch(`${API_BASE}/api/gmail/disconnect`, { method: 'POST' });
        location.reload();
    } catch (error) {
        alert('Failed to disconnect: ' + error.message);
    }
}

/**
 * Render Gmail inbox with priority scoring, timeline filter, and sender filter
 *
 * @param {HTMLElement} container - Container element
 * @param {string} userEmail - User's email address
 * @param {number|null} days - Timeline filter (7, 30, 90, 120 days)
 * @param {string|null} senderFilter - Filter by sender email
 * @param {string|null} senderName - Sender display name (for UI)
 */
async function renderGmailInbox(container, userEmail, days = null, senderFilter = null, senderName = null, categoryFilter = null) {
    container.innerHTML = '<div class="loading">Loading emails...</div>';

    try {
        // Get inbox summary for accurate unread count
        const summaryResp = await fetch(`${API_BASE}/api/gmail/summary`);
        const summary = await summaryResp.json();

        // Fetch emails with priority scoring and optional filters
        let url = `${API_BASE}/api/gmail/emails?limit=50&sort_by_priority=true`;
        if (days) {
            url += `&days=${days}`;
        }
        // Use Gmail search query for sender filter
        if (senderFilter) {
            url += `&query=from:${encodeURIComponent(senderFilter)}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        // Filter by category client-side (category detection happens server-side)
        let filteredEmails = data.emails || [];
        if (categoryFilter) {
            filteredEmails = filteredEmails.filter(e => e.category === categoryFilter);
        }

        container.innerHTML = '';

        // Active Filter Bar (show when filtering by sender or category)
        if (senderFilter || categoryFilter) {
            const filterBar = document.createElement('div');
            filterBar.className = 'gmail-active-filter';

            const categoryIcons = {
                'bills': '💳',
                'shipments': '📦',
                'purchases': '🛍️',
                'promotions': '🏷️',
                'social': '👥'
            };

            if (senderFilter) {
                filterBar.innerHTML = `
                    <span class="filter-label">📧 Showing emails from:</span>
                    <span class="filter-value">${escapeHtml(senderName || senderFilter)}</span>
                    <button id="clear-filter" class="btn-clear-filter" title="Clear filter">✕ Show all</button>
                `;
            } else if (categoryFilter) {
                filterBar.innerHTML = `
                    <span class="filter-label">${categoryIcons[categoryFilter] || '📂'} Showing:</span>
                    <span class="filter-value">${categoryFilter.charAt(0).toUpperCase() + categoryFilter.slice(1)}</span>
                    <button id="clear-filter" class="btn-clear-filter" title="Clear filter">✕ Show all</button>
                `;
            }
            container.appendChild(filterBar);

            // Clear filter handler
            setTimeout(() => {
                document.getElementById('clear-filter')?.addEventListener('click', () => {
                    renderGmailInbox(container, userEmail, days, null, null, null);
                });
            }, 0);
        }

        // Timeline selector + Summary bar
        const controlBar = document.createElement('div');
        controlBar.className = 'gmail-control-bar';
        const displayCount = categoryFilter ? filteredEmails.length : data.total_count;
        const filterLabel = senderFilter ? 'from sender' : (categoryFilter ? categoryFilter : 'shown');
        controlBar.innerHTML = `
            <div class="gmail-timeline-selector">
                <select id="gmail-days-filter" class="timeline-select">
                    <option value="" ${!days ? 'selected' : ''}>All time</option>
                    <option value="7" ${days == 7 ? 'selected' : ''}>Last 7 days</option>
                    <option value="30" ${days == 30 ? 'selected' : ''}>Last 30 days</option>
                    <option value="90" ${days == 90 ? 'selected' : ''}>Last 90 days</option>
                    <option value="120" ${days == 120 ? 'selected' : ''}>Last 120 days</option>
                </select>
            </div>
            <div class="gmail-stats-row">
                <span class="gmail-stat-inline">${displayCount} ${filterLabel}</span>
                <span class="gmail-stat-inline unread">${summary.unread_count} unread total</span>
                <span class="gmail-stat-inline priority">${data.priority_count || 0} priority</span>
            </div>
            <button id="gmail-refresh-inbox" class="btn-icon" title="Refresh">🔄</button>
        `;
        container.appendChild(controlBar);

        // Category Filter Chips (show when we have category counts and no active category filter)
        const categoryCounts = data.category_counts || {};
        if (Object.keys(categoryCounts).length > 0 && !categoryFilter) {
            const categorySection = document.createElement('div');
            categorySection.className = 'gmail-category-filters';

            const categoryIcons = {
                'bills': '💳',
                'shipments': '📦',
                'purchases': '🛍️',
                'promotions': '🏷️',
                'social': '👥'
            };

            const categoryLabels = {
                'bills': 'Bills & Payments',
                'shipments': 'Shipments',
                'purchases': 'Purchases',
                'promotions': 'Promotions',
                'social': 'Social'
            };

            // Sort by count descending
            const sortedCategories = Object.entries(categoryCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);

            sortedCategories.forEach(([cat, count]) => {
                const chip = document.createElement('button');
                chip.className = 'category-chip clickable';
                chip.innerHTML = `${categoryIcons[cat] || '📂'} ${categoryLabels[cat] || cat} <span class="chip-count">${count}</span>`;
                chip.setAttribute('data-category', cat);
                chip.title = `Filter ${categoryLabels[cat] || cat} emails`;

                chip.addEventListener('click', () => {
                    renderGmailInbox(container, userEmail, days, null, null, cat);
                });

                categorySection.appendChild(chip);
            });

            container.appendChild(categorySection);
        }

        // Email list
        const emailList = document.createElement('div');
        emailList.className = 'gmail-email-list';

        if (!filteredEmails || filteredEmails.length === 0) {
            emailList.innerHTML = '<div class="empty-state">No emails found</div>';
        } else {
            // Priority emails section
            const priorityEmails = filteredEmails.filter(e => e.is_priority);
            const normalEmails = filteredEmails.filter(e => !e.is_priority);

            if (priorityEmails.length > 0) {
                const priorityHeader = document.createElement('div');
                priorityHeader.className = 'gmail-section-header priority';
                priorityHeader.innerHTML = '⭐ Priority';
                emailList.appendChild(priorityHeader);

                priorityEmails.forEach(email => {
                    emailList.appendChild(createEmailCard(email));
                });
            }

            if (normalEmails.length > 0) {
                const normalHeader = document.createElement('div');
                normalHeader.className = 'gmail-section-header';
                normalHeader.innerHTML = '📬 Recent';
                emailList.appendChild(normalHeader);

                normalEmails.forEach(email => {
                    emailList.appendChild(createEmailCard(email));
                });
            }
        }

        container.appendChild(emailList);

        // Event handlers
        setTimeout(() => {
            // Timeline filter change (maintain sender and category filters)
            const daysFilter = document.getElementById('gmail-days-filter');
            if (daysFilter) {
                daysFilter.addEventListener('change', (e) => {
                    const selectedDays = e.target.value ? parseInt(e.target.value) : null;
                    renderGmailInbox(container, userEmail, selectedDays, senderFilter, senderName, categoryFilter);
                });
            }

            // Refresh button (maintain all filters)
            const refreshBtn = document.getElementById('gmail-refresh-inbox');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => {
                    const currentDays = document.getElementById('gmail-days-filter')?.value;
                    renderGmailInbox(container, userEmail, currentDays ? parseInt(currentDays) : null, senderFilter, senderName, categoryFilter);
                });
            }
        }, 0);

    } catch (error) {
        container.innerHTML = `
            <div class="gmail-error">
                <p>⚠️ Failed to load emails: ${escapeHtml(error.message)}</p>
                <button onclick="location.reload()" class="btn-secondary">Retry</button>
            </div>
        `;
    }
}

/**
 * Create email card element
 */
function createEmailCard(email) {
    const card = document.createElement('div');
    card.className = `gmail-email-card ${email.is_read ? 'read' : 'unread'} ${email.is_priority ? 'priority' : ''}`;
    card.setAttribute('data-message-id', email.message_id);

    // Parse sender display
    const senderDisplay = email.from.includes('<')
        ? email.from.split('<')[0].trim().replace(/"/g, '')
        : email.sender_email;

    // Format date
    const dateStr = email.date ? formatEmailDate(email.date) : '';

    // Importance badge
    const importanceBadge = email.importance_score !== undefined
        ? `<span class="importance-badge score-${getScoreClass(email.importance_score)}">${email.importance_score}</span>`
        : '';

    card.innerHTML = `
        <div class="email-header">
            <span class="email-sender">${escapeHtml(senderDisplay)}</span>
            <span class="email-date">${dateStr}</span>
            ${importanceBadge}
        </div>
        <div class="email-subject">${escapeHtml(email.subject)}</div>
        <div class="email-snippet">${escapeHtml(email.snippet)}</div>
        <div class="email-actions">
            <button class="btn-link open-gmail-btn" data-message-id="${email.message_id}">Open in Gmail ↗</button>
            ${email.is_priority ? '<span class="priority-indicator">⭐ Priority</span>' : ''}
        </div>
    `;

    // Click handler for opening in Gmail - captures learning signal
    card.querySelector('.open-gmail-btn').addEventListener('click', async (e) => {
        e.stopPropagation();

        // Track learning signal (non-blocking)
        trackEmailAction(email.message_id, email.sender_email, 'open_in_gmail');

        // Open Gmail
        window.open(`https://mail.google.com/mail/u/0/#inbox/${email.message_id}`, '_blank');
    });

    return card;
}

/**
 * Get score class for importance coloring
 */
function getScoreClass(score) {
    if (score >= 60) return 'high';
    if (score >= 30) return 'medium';
    return 'low';
}

/**
 * Format email date for display
 */
function formatEmailDate(dateStr) {
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffHours = diffMs / (1000 * 60 * 60);

        if (diffHours < 1) {
            const mins = Math.floor(diffMs / (1000 * 60));
            return `${mins}m ago`;
        } else if (diffHours < 24) {
            return `${Math.floor(diffHours)}h ago`;
        } else if (diffHours < 48) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }
    } catch (e) {
        return dateStr;
    }
}

// ============================================================================
// FINANCIAL VIEW - Plaid Integration (Phase 2: Financial Constitution)
// ============================================================================

/**
 * Render the Financial view
 * Shows connected investment accounts and allows linking new ones via Plaid
 */
async function renderFinancialView(container) {
    container.innerHTML = '';

    // Create scrollable content wrapper
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'financial-container';

    // Header
    const header = document.createElement('div');
    header.className = 'view-header financial-header';
    header.innerHTML = `
        <div class="financial-header-content">
            <div class="financial-header-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
                </svg>
            </div>
            <div>
                <h2>Financial Accounts</h2>
                <p class="view-subtitle">Connect and monitor your investment accounts</p>
            </div>
        </div>
    `;
    contentWrapper.appendChild(header);

    // Main content area
    const mainContent = document.createElement('div');
    mainContent.id = 'financial-content';
    mainContent.className = 'financial-content';
    mainContent.innerHTML = '<div class="loading">Loading financial status...</div>';
    contentWrapper.appendChild(mainContent);

    container.appendChild(contentWrapper);

    // Load financial status
    await loadFinancialStatus(mainContent);
}

/**
 * Load and display financial status (Plaid connections)
 */
async function loadFinancialStatus(container) {
    try {
        const response = await fetch(`${API_BASE}/api/plaid/status`);
        const data = await response.json();

        container.innerHTML = '';

        if (!data.connected) {
            // No accounts connected - show setup card
            renderPlaidSetupCard(container, data.environment);
        } else {
            // Show connected accounts
            renderConnectedAccounts(container, data);
        }
    } catch (error) {
        console.error('Failed to load financial status:', error);
        container.innerHTML = `
            <div class="error-state">
                <h3>Unable to Load Financial Status</h3>
                <p>${escapeHtml(error.message)}</p>
                <button onclick="location.reload()" class="btn-primary">Retry</button>
            </div>
        `;
    }
}

/**
 * Render Plaid setup card for first-time connection
 */
function renderPlaidSetupCard(container, environment) {
    const setupCard = document.createElement('div');
    setupCard.className = 'financial-setup-card';
    setupCard.innerHTML = `
        <div class="setup-card-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#4CAF50" stroke-width="1.5">
                <rect x="2" y="5" width="20" height="14" rx="2"/>
                <path d="M2 10h20"/>
            </svg>
        </div>
        <h3>Connect Your Investment Accounts</h3>
        <p class="setup-description">
            Link your brokerage and retirement accounts to get AI-powered portfolio insights,
            track performance, and receive intelligent financial recommendations.
        </p>
        <div class="setup-features">
            <div class="feature-item">
                <span class="feature-icon">🔒</span>
                <span>Bank-level security via Plaid</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">📊</span>
                <span>Real-time portfolio tracking</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">🤖</span>
                <span>AI-powered financial insights</span>
            </div>
        </div>
        ${environment === 'sandbox' ? `
            <div class="sandbox-notice">
                <span class="sandbox-badge">SANDBOX MODE</span>
                <span>Using test credentials for development</span>
            </div>
        ` : ''}
        <button id="connect-plaid-btn" class="btn-primary btn-large">
            <span class="btn-icon">🔗</span>
            Connect Account
        </button>
        <p class="setup-footer">
            Supported: Fidelity, Vanguard, Charles Schwab, TD Ameritrade, and 10,000+ more
        </p>
    `;
    container.appendChild(setupCard);

    // Setup connect button
    document.getElementById('connect-plaid-btn').addEventListener('click', () => {
        initiatePlaidLink();
    });
}

/**
 * Render connected accounts dashboard with portfolio view
 */
function renderConnectedAccounts(container, data) {
    const institutions = data.institutions || [];

    // Header with actions
    const headerSection = document.createElement('div');
    headerSection.className = 'portfolio-header';
    headerSection.innerHTML = `
        <div class="portfolio-header-left">
            <h3>Portfolio Dashboard</h3>
            <p>${institutions.length} institution${institutions.length !== 1 ? 's' : ''} linked</p>
        </div>
        <div class="portfolio-header-actions">
            <button id="sync-all-btn" class="btn-primary">
                <span class="btn-icon">🔄</span>
                Sync All
            </button>
            <button id="add-account-btn" class="btn-secondary">
                <span class="btn-icon">+</span>
                Add Account
            </button>
        </div>
    `;
    container.appendChild(headerSection);

    // Sync status area
    const syncStatus = document.createElement('div');
    syncStatus.id = 'sync-status';
    syncStatus.className = 'sync-status hidden';
    container.appendChild(syncStatus);

    // Tab navigation
    const tabNav = document.createElement('div');
    tabNav.className = 'portfolio-tabs';
    tabNav.innerHTML = `
        <button class="portfolio-tab-btn active" data-tab="holdings">Holdings</button>
        <button class="portfolio-tab-btn" data-tab="rules">Constitution</button>
        <button class="portfolio-tab-btn" data-tab="accounts">Accounts</button>
        <button class="portfolio-tab-btn" data-tab="transactions">Transactions</button>
    `;
    container.appendChild(tabNav);

    // Tab content container
    const tabContent = document.createElement('div');
    tabContent.id = 'portfolio-tab-content';
    tabContent.className = 'portfolio-tab-content';
    container.appendChild(tabContent);

    // Setup tab switching
    tabNav.querySelectorAll('.portfolio-tab-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            tabNav.querySelectorAll('.portfolio-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            await loadPortfolioTab(tabContent, btn.dataset.tab, institutions);
        });
    });

    // Setup action buttons
    document.getElementById('sync-all-btn').addEventListener('click', () => syncAllAccounts());
    document.getElementById('add-account-btn').addEventListener('click', () => initiatePlaidLink());

    // Load default tab (holdings)
    loadPortfolioTab(tabContent, 'holdings', institutions);
}

/**
 * Load portfolio tab content
 */
async function loadPortfolioTab(container, tab, institutions) {
    container.innerHTML = '<div class="loading">Loading...</div>';

    try {
        switch (tab) {
            case 'holdings':
                await loadHoldingsTab(container);
                break;
            case 'rules':
                await loadRulesTab(container);
                break;
            case 'accounts':
                loadAccountsTab(container, institutions);
                break;
            case 'transactions':
                await loadTransactionsTab(container);
                break;
        }
    } catch (error) {
        console.error(`Failed to load ${tab} tab:`, error);
        container.innerHTML = `<div class="tab-error">Failed to load ${tab}. Try syncing first.</div>`;
    }
}

/**
 * Load holdings tab with portfolio breakdown
 */
async function loadHoldingsTab(container) {
    const response = await fetch(`${API_BASE}/api/plaid/holdings`);
    const data = await response.json();

    if (!data.holdings || data.holdings.length === 0) {
        container.innerHTML = `
            <div class="empty-holdings">
                <h4>No Holdings Data</h4>
                <p>Click "Sync All" to fetch your portfolio data from connected accounts.</p>
            </div>
        `;
        return;
    }

    // Portfolio summary
    const summary = document.createElement('div');
    summary.className = 'portfolio-summary';
    const totalGainLoss = data.total_gain_loss || 0;
    const gainLossClass = totalGainLoss >= 0 ? 'positive' : 'negative';
    const gainLossSign = totalGainLoss >= 0 ? '+' : '';

    summary.innerHTML = `
        <div class="summary-stat large">
            <span class="stat-value">$${formatCurrency(data.total_value)}</span>
            <span class="stat-label">Total Value</span>
        </div>
        <div class="summary-stat">
            <span class="stat-value">$${formatCurrency(data.total_cost)}</span>
            <span class="stat-label">Cost Basis</span>
        </div>
        <div class="summary-stat ${gainLossClass}">
            <span class="stat-value">${gainLossSign}$${formatCurrency(Math.abs(totalGainLoss))}</span>
            <span class="stat-label">Total Gain/Loss</span>
        </div>
        <div class="summary-stat">
            <span class="stat-value">${data.count}</span>
            <span class="stat-label">Positions</span>
        </div>
    `;
    container.innerHTML = '';
    container.appendChild(summary);

    // Holdings table
    const table = document.createElement('div');
    table.className = 'holdings-table';
    table.innerHTML = `
        <div class="holdings-table-header">
            <span class="col-ticker">Symbol</span>
            <span class="col-name">Name</span>
            <span class="col-qty">Shares</span>
            <span class="col-price">Price</span>
            <span class="col-value">Value</span>
            <span class="col-gain">Gain/Loss</span>
            <span class="col-pct">% Port</span>
        </div>
    `;

    data.holdings.forEach(h => {
        const gainLoss = h.gain_loss || 0;
        const gainLossPct = h.gain_loss_pct || 0;
        const positionPct = data.total_value > 0 ? (h.market_value / data.total_value * 100) : 0;
        const glClass = gainLoss >= 0 ? 'positive' : 'negative';
        const glSign = gainLoss >= 0 ? '+' : '';

        const row = document.createElement('div');
        row.className = 'holdings-table-row';
        row.innerHTML = `
            <span class="col-ticker"><strong>${escapeHtml(h.ticker || 'CASH')}</strong></span>
            <span class="col-name">${escapeHtml(truncate(h.name, 25))}</span>
            <span class="col-qty">${h.quantity.toFixed(2)}</span>
            <span class="col-price">$${h.price ? h.price.toFixed(2) : '-'}</span>
            <span class="col-value">$${formatCurrency(h.market_value)}</span>
            <span class="col-gain ${glClass}">${glSign}$${formatCurrency(Math.abs(gainLoss))} (${glSign}${gainLossPct.toFixed(1)}%)</span>
            <span class="col-pct">${positionPct.toFixed(1)}%</span>
        `;
        table.appendChild(row);
    });

    container.appendChild(table);
}

/**
 * Load accounts tab
 */
async function loadAccountsTab(container, institutions) {
    container.innerHTML = '<div class="loading">Loading accounts...</div>';

    try {
        // Fetch actual accounts from API
        const response = await fetch(`${API_BASE}/api/plaid/accounts`);
        const data = await response.json();
        const accounts = data.accounts || [];

        container.innerHTML = '';

        const grid = document.createElement('div');
        grid.className = 'accounts-grid';

        // Group accounts by institution (item_id)
        const accountsByInstitution = {};
        accounts.forEach(acc => {
            if (!accountsByInstitution[acc.item_id]) {
                accountsByInstitution[acc.item_id] = [];
            }
            accountsByInstitution[acc.item_id].push(acc);
        });

        // Create a card for each institution with its accounts
        institutions.forEach(item => {
            const institutionAccounts = accountsByInstitution[item.item_id] || [];
            const card = createAccountCardWithDetails(item, institutionAccounts);
            grid.appendChild(card);
        });

        container.appendChild(grid);
    } catch (error) {
        console.error('Failed to load accounts:', error);
        container.innerHTML = `<div class="tab-error">Failed to load accounts. Try syncing first.</div>`;
    }
}

/**
 * Load transactions tab
 */
async function loadTransactionsTab(container) {
    const response = await fetch(`${API_BASE}/api/plaid/transactions?days=90`);
    const data = await response.json();

    if (!data.transactions || data.transactions.length === 0) {
        container.innerHTML = `
            <div class="empty-transactions">
                <h4>No Transaction History</h4>
                <p>Click "Sync All" to fetch your transaction history.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = '';

    const table = document.createElement('div');
    table.className = 'transactions-table';
    table.innerHTML = `
        <div class="transactions-table-header">
            <span class="col-date">Date</span>
            <span class="col-type">Type</span>
            <span class="col-ticker">Symbol</span>
            <span class="col-qty">Shares</span>
            <span class="col-amount">Amount</span>
            <span class="col-account">Account</span>
        </div>
    `;

    data.transactions.slice(0, 50).forEach(t => {
        const typeClass = t.type === 'buy' ? 'type-buy' : t.type === 'sell' ? 'type-sell' : 'type-other';
        const row = document.createElement('div');
        row.className = 'transactions-table-row';
        row.innerHTML = `
            <span class="col-date">${t.date}</span>
            <span class="col-type ${typeClass}">${t.type.toUpperCase()}</span>
            <span class="col-ticker">${escapeHtml(t.ticker || '-')}</span>
            <span class="col-qty">${t.quantity ? t.quantity.toFixed(2) : '-'}</span>
            <span class="col-amount">$${formatCurrency(Math.abs(t.amount))}</span>
            <span class="col-account">${escapeHtml(truncate(t.account, 20))}</span>
        `;
        table.appendChild(row);
    });

    container.appendChild(table);
}

/**
 * Load Constitution Rules tab - Advisor + Principles Layout
 */
async function loadRulesTab(container) {
    // Fetch holdings to calculate rule status
    let holdings = { holdings: [], total_value: 0 };
    try {
        const response = await fetch(`${API_BASE}/api/plaid/holdings`);
        holdings = await response.json();
    } catch (e) {
        console.log('No holdings data for rules evaluation');
    }

    container.innerHTML = '';

    // Calculate rule metrics from holdings
    const metrics = calculatePortfolioMetrics(holdings);

    // Define the 25 Constitution rules organized by principle
    const principles = getConstitutionPrinciples(metrics);

    // Calculate overall health score and get advisor commentary
    const healthScore = calculateHealthScore(principles);
    const advisorCommentary = generateAdvisorCommentary(principles, metrics, healthScore);
    const quickActions = generateQuickActions(principles, metrics);

    // Build the advisor dashboard
    const advisorSection = document.createElement('div');
    advisorSection.className = 'advisor-dashboard';

    const healthClass = healthScore >= 80 ? 'excellent' : healthScore >= 60 ? 'good' : healthScore >= 40 ? 'fair' : 'poor';
    const healthLabel = healthScore >= 80 ? 'Excellent' : healthScore >= 60 ? 'Good' : healthScore >= 40 ? 'Fair' : 'Needs Work';

    advisorSection.innerHTML = `
        <div class="advisor-header">
            <div class="advisor-icon">💼</div>
            <div class="advisor-title">
                <h3>Your Portfolio Advisor</h3>
                <p>Monitoring ${principles.reduce((sum, p) => sum + p.rules.length, 0)} rules across ${principles.length} principles</p>
            </div>
        </div>

        <div class="health-score-section">
            <div class="health-score-ring ${healthClass}">
                <div class="health-score-value">${healthScore}</div>
                <div class="health-score-label">${healthLabel}</div>
            </div>
            <div class="health-score-bar">
                <div class="health-bar-track">
                    <div class="health-bar-fill ${healthClass}" style="width: ${healthScore}%"></div>
                </div>
                <div class="health-bar-labels">
                    <span>Poor</span>
                    <span>Fair</span>
                    <span>Good</span>
                    <span>Excellent</span>
                </div>
            </div>
        </div>

        <div class="advisor-commentary">
            <div class="commentary-icon">${advisorCommentary.icon}</div>
            <div class="commentary-text">
                <p class="commentary-main">${advisorCommentary.main}</p>
                ${advisorCommentary.detail ? `<p class="commentary-detail">${advisorCommentary.detail}</p>` : ''}
            </div>
        </div>

        ${quickActions.length > 0 ? `
            <div class="quick-actions">
                <h4>Suggested Actions</h4>
                <div class="action-buttons">
                    ${quickActions.map(action => `
                        <button class="action-btn ${action.priority}" data-action="${action.id}">
                            <span class="action-icon">${action.icon}</span>
                            <span class="action-text">${action.text}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
        ` : ''}
    `;
    container.appendChild(advisorSection);

    // Build the principles section
    const principlesSection = document.createElement('div');
    principlesSection.className = 'principles-section';
    principlesSection.innerHTML = `
        <div class="principles-header">
            <h3>Your Investment Constitution</h3>
            <p>Core principles guiding your portfolio decisions</p>
        </div>
    `;

    const principlesGrid = document.createElement('div');
    principlesGrid.className = 'principles-grid';

    principles.forEach(principle => {
        const card = document.createElement('div');
        card.className = `principle-card ${principle.status}`;

        const passingCount = principle.rules.filter(r => getRuleStatus(r) === 'passing').length;
        const totalCount = principle.rules.length;
        const summary = getPrincipleSummary(principle, metrics);

        card.innerHTML = `
            <div class="principle-card-header">
                <div class="principle-icon">${principle.icon}</div>
                <div class="principle-status-badge ${principle.status}">
                    ${principle.status === 'passing' ? '✓' : principle.status === 'warning' ? '!' : '×'}
                </div>
            </div>
            <div class="principle-card-body">
                <h4 class="principle-name">${principle.displayName}</h4>
                <p class="principle-tagline">${principle.tagline}</p>
                <div class="principle-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${(passingCount / totalCount) * 100}%"></div>
                    </div>
                    <span class="progress-text">${passingCount}/${totalCount} rules</span>
                </div>
                <p class="principle-summary">${summary}</p>
            </div>
            <div class="principle-card-footer">
                <button class="expand-rules-btn" data-principle="${principle.id}">
                    View Details <span class="expand-icon">›</span>
                </button>
            </div>
        `;

        // Add expandable rules section (hidden by default)
        const rulesDetail = document.createElement('div');
        rulesDetail.className = 'principle-rules-detail hidden';
        rulesDetail.id = `rules-${principle.id}`;
        rulesDetail.innerHTML = `
            <div class="rules-detail-content">
                ${principle.rules.map(rule => renderRuleItem(rule)).join('')}
            </div>
        `;

        card.appendChild(rulesDetail);
        principlesGrid.appendChild(card);
    });

    principlesSection.appendChild(principlesGrid);
    container.appendChild(principlesSection);

    // Add event listeners for expand/collapse
    container.querySelectorAll('.expand-rules-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const principleId = btn.dataset.principle;
            const rulesDetail = document.getElementById(`rules-${principleId}`);
            const expandIcon = btn.querySelector('.expand-icon');

            if (rulesDetail.classList.contains('hidden')) {
                rulesDetail.classList.remove('hidden');
                expandIcon.textContent = '‹';
                btn.innerHTML = `Hide Details <span class="expand-icon">‹</span>`;
            } else {
                rulesDetail.classList.add('hidden');
                expandIcon.textContent = '›';
                btn.innerHTML = `View Details <span class="expand-icon">›</span>`;
            }
        });
    });

    // Add event listeners for quick actions
    container.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const actionId = btn.dataset.action;
            handleQuickAction(actionId, metrics);
        });
    });
}

/**
 * Get constitution principles with human-readable names and icons
 */
function getConstitutionPrinciples(metrics) {
    return [
        {
            id: 'capital-preservation',
            name: 'A1: Capital Preservation',
            displayName: 'Capital Preservation',
            icon: '🛡️',
            tagline: 'Protecting your wealth first',
            rules: [
                { id: 'R1', name: 'Max Position Size', desc: 'No single position > 10%', limit: 10, value: metrics.maxPositionPct, unit: '%' },
                { id: 'R2', name: 'Sector Concentration', desc: 'No sector > 30%', limit: 30, value: metrics.maxSectorPct, unit: '%' },
                { id: 'R3', name: 'Speculative Cap', desc: 'Speculative positions < 5%', limit: 5, value: metrics.speculativePct, unit: '%' },
                { id: 'R4', name: 'Cash Buffer', desc: 'Maintain 5%+ cash', limit: 5, value: metrics.cashPct, unit: '%', invert: true },
                { id: 'R5', name: 'Drawdown Alert', desc: 'Alert at 15% drawdown', limit: 15, value: metrics.drawdownPct, unit: '%' },
            ],
            get status() { return getCategoryStatus(this.rules).class; }
        },
        {
            id: 'long-term',
            name: 'A2: Long-Term Compounding',
            displayName: 'Long-Term Growth',
            icon: '🌱',
            tagline: 'Growing wealth steadily over decades',
            rules: [
                { id: 'R6', name: 'Annual Turnover', desc: 'Portfolio turnover < 50%/year', limit: 50, value: metrics.turnoverPct, unit: '%' },
                { id: 'R7', name: 'Holding Period', desc: 'Min 30 days before sell', limit: 30, value: metrics.minHoldingDays, unit: ' days', invert: true },
                { id: 'R8', name: 'Index Core Base', desc: 'INDEX_CORE >= 25%', limit: 25, value: metrics.indexCorePct, unit: '%', invert: true },
                { id: 'R9', name: 'Allocation Bands', desc: 'Stay within target bands', limit: 5, value: metrics.bandDrift, unit: '% drift' },
            ],
            get status() { return getCategoryStatus(this.rules).class; }
        },
        {
            id: 'quality-value',
            name: 'A3: Quality + Value Discipline',
            displayName: 'Quality & Value',
            icon: '💎',
            tagline: 'Investing in excellent businesses',
            rules: [
                { id: 'R10', name: 'Thesis Required', desc: 'Thesis for each position', limit: 100, value: metrics.thesisCoverage, unit: '%', invert: true },
                { id: 'R11', name: 'Quality Filter', desc: 'Quality score > 70', limit: 70, value: metrics.avgQualityScore, unit: '', invert: true },
                { id: 'R12', name: 'Moat Documentation', desc: 'Document competitive moat', limit: 100, value: metrics.moatCoverage, unit: '%', invert: true },
                { id: 'R13', name: 'Averaging Down', desc: 'Thesis review before add', limit: 0, value: metrics.avgDownReviews, unit: ' pending' },
            ],
            get status() { return getCategoryStatus(this.rules).class; }
        },
        {
            id: 'ai-thesis',
            name: 'A4: AI Infrastructure Thesis',
            displayName: 'AI Investments',
            icon: '🤖',
            tagline: 'Capturing the AI revolution responsibly',
            rules: [
                { id: 'R14', name: 'AI Theme Diversity', desc: 'Spread across sub-themes', limit: 4, value: metrics.aiThemeCount, unit: ' themes', invert: true },
                { id: 'R15', name: 'AI Basket Cap', desc: 'AI_INFRA_CORE < 50%', limit: 50, value: metrics.aiInfraPct, unit: '%' },
                { id: 'R16', name: 'AI Single Name', desc: 'No AI position > 15%', limit: 15, value: metrics.maxAiPositionPct, unit: '%' },
                { id: 'R17', name: 'Review Cadence', desc: 'AI thesis review < 45 days', limit: 45, value: metrics.aiThesisAge, unit: ' days' },
            ],
            get status() { return getCategoryStatus(this.rules).class; }
        },
        {
            id: 'tax-aware',
            name: 'A5: Tax-Aware Wealth Building',
            displayName: 'Tax Efficiency',
            icon: '📊',
            tagline: 'Keeping more of what you earn',
            rules: [
                { id: 'R18', name: 'Short-Term Gains', desc: 'Warn before ST gain', limit: 0, value: metrics.stGainRisk, unit: ' at risk' },
                { id: 'R19', name: 'Wash Sale Detection', desc: 'Prevent wash sales', limit: 0, value: metrics.washSaleRisk, unit: ' potential' },
                { id: 'R20', name: 'Tax Loss Harvest', desc: 'Identify TLH opportunities', limit: 0, value: metrics.tlhOpportunities, unit: ' available', invert: true, neutral: true },
                { id: 'R21', name: 'Employer Stock', desc: 'Employer stock < 10%', limit: 10, value: metrics.employerPct, unit: '%' },
                { id: 'R22', name: 'Asset Location', desc: 'Tax-efficient placement', limit: 100, value: metrics.assetLocationScore, unit: '%', invert: true, neutral: true },
            ],
            get status() { return getCategoryStatus(this.rules).class; }
        },
        {
            id: 'behavioral',
            name: 'A6: Behavioral & Process Integrity',
            displayName: 'Behavioral Guard',
            icon: '🧠',
            tagline: 'Avoiding emotional decisions',
            rules: [
                { id: 'R23', name: 'Panic Sell Detection', desc: 'No selling in downturns', limit: 0, value: metrics.panicSellRisk, unit: '' },
                { id: 'R24', name: 'Rapid Changes', desc: 'Max 3 changes/48hrs', limit: 3, value: metrics.recentChanges, unit: ' changes' },
                { id: 'R25', name: 'New Position Cap', desc: 'Max 2 new positions/month', limit: 2, value: metrics.newPositions, unit: ' this month' },
            ],
            get status() { return getCategoryStatus(this.rules).class; }
        }
    ];
}

/**
 * Calculate overall health score (0-100)
 */
function calculateHealthScore(principles) {
    let totalRules = 0;
    let passingRules = 0;
    let warningRules = 0;

    principles.forEach(p => {
        p.rules.forEach(rule => {
            totalRules++;
            const status = getRuleStatus(rule);
            if (status === 'passing') passingRules++;
            else if (status === 'warning') warningRules++;
        });
    });

    // Passing = 100%, Warning = 50%, Failing = 0%
    const score = Math.round(((passingRules + warningRules * 0.5) / totalRules) * 100);
    return Math.min(100, Math.max(0, score));
}

/**
 * Generate natural language advisor commentary
 */
function generateAdvisorCommentary(principles, metrics, healthScore) {
    const failingPrinciples = principles.filter(p => p.status === 'failing');
    const warningPrinciples = principles.filter(p => p.status === 'warning');

    // Excellent health
    if (healthScore >= 90) {
        return {
            icon: '✨',
            main: "Your portfolio is in excellent shape!",
            detail: "All your investment principles are being followed. Keep up the disciplined approach."
        };
    }

    // Good health with minor warnings
    if (healthScore >= 75) {
        if (warningPrinciples.length > 0) {
            const p = warningPrinciples[0];
            return {
                icon: '👍',
                main: "Your portfolio is well-balanced with minor areas to watch.",
                detail: `${p.displayName} has some metrics approaching limits. Consider reviewing when convenient.`
            };
        }
        return {
            icon: '👍',
            main: "Your portfolio is in good health.",
            detail: "Most principles are being followed. A few areas could use attention."
        };
    }

    // Fair health - needs attention
    if (healthScore >= 50) {
        if (failingPrinciples.length > 0) {
            const p = failingPrinciples[0];
            return {
                icon: '⚠️',
                main: `${p.displayName} needs your attention.`,
                detail: getPrincipleActionAdvice(p, metrics)
            };
        }
        return {
            icon: '⚠️',
            main: "Your portfolio needs some adjustments.",
            detail: "Several principles have rules outside recommended limits."
        };
    }

    // Poor health
    return {
        icon: '🚨',
        main: "Your portfolio requires immediate attention.",
        detail: `${failingPrinciples.length} principle${failingPrinciples.length > 1 ? 's are' : ' is'} outside safe limits. Review the suggestions below.`
    };
}

/**
 * Get specific advice for a principle
 */
function getPrincipleActionAdvice(principle, metrics) {
    switch(principle.id) {
        case 'capital-preservation':
            if (parseFloat(metrics.maxPositionPct) > 10) {
                return `Your largest position is ${metrics.maxPositionPct}% of portfolio. Consider trimming to reduce concentration risk.`;
            }
            if (parseFloat(metrics.cashPct) < 5) {
                return `Cash is at ${metrics.cashPct}% (target: 5%+). Consider adding to your cash buffer.`;
            }
            return "Review your position sizes and sector allocations.";

        case 'long-term':
            return "Focus on holding quality positions longer and reducing trading frequency.";

        case 'quality-value':
            return "Document your investment thesis for each position to maintain discipline.";

        case 'ai-thesis':
            if (parseFloat(metrics.aiInfraPct) > 50) {
                return `AI positions total ${metrics.aiInfraPct}% of portfolio. Consider diversifying into other sectors.`;
            }
            return "Review your AI investment allocation and thesis recency.";

        case 'tax-aware':
            return "Review positions for tax-loss harvesting opportunities and wash sale risks.";

        case 'behavioral':
            return "Your recent trading activity suggests emotional decision-making. Pause and review.";

        default:
            return "Review the detailed rules below for specific guidance.";
    }
}

/**
 * Generate quick action suggestions
 */
function generateQuickActions(principles, metrics) {
    const actions = [];

    // Check cash buffer
    const cashPct = parseFloat(metrics.cashPct) || 0;
    if (cashPct < 5) {
        const neededPct = (5 - cashPct).toFixed(1);
        actions.push({
            id: 'add-cash',
            icon: '💵',
            text: `Add ${neededPct}% to Cash`,
            priority: 'warning'
        });
    }

    // Check position concentration
    const maxPos = parseFloat(metrics.maxPositionPct) || 0;
    if (maxPos > 10) {
        actions.push({
            id: 'trim-position',
            icon: '✂️',
            text: 'Trim Largest Position',
            priority: 'warning'
        });
    }

    // Check sector concentration
    const maxSector = parseFloat(metrics.maxSectorPct) || 0;
    if (maxSector > 30) {
        actions.push({
            id: 'diversify-sector',
            icon: '🎯',
            text: 'Diversify Sectors',
            priority: 'warning'
        });
    }

    // Suggest review if all good
    if (actions.length === 0) {
        const hasWarnings = principles.some(p => p.status === 'warning');
        if (hasWarnings) {
            actions.push({
                id: 'review-warnings',
                icon: '👀',
                text: 'Review Warnings',
                priority: 'info'
            });
        }
    }

    return actions.slice(0, 3); // Max 3 actions
}

/**
 * Get one-line summary for a principle card
 */
function getPrincipleSummary(principle, metrics) {
    const status = principle.status;

    switch(principle.id) {
        case 'capital-preservation':
            if (status === 'passing') {
                return `Positions well-diversified. Largest at ${metrics.maxPositionPct}%.`;
            }
            if (parseFloat(metrics.cashPct) < 5) {
                return `Cash buffer low at ${metrics.cashPct}%. Add funds to reach 5%.`;
            }
            return `Position size at ${metrics.maxPositionPct}% (limit: 10%).`;

        case 'long-term':
            if (status === 'passing') {
                return "Trading discipline maintained. Low turnover detected.";
            }
            return "Trading activity higher than optimal for long-term growth.";

        case 'quality-value':
            if (status === 'passing') {
                return "Investment theses documented and quality standards met.";
            }
            return "Some positions missing documented investment thesis.";

        case 'ai-thesis':
            if (status === 'passing') {
                return "AI exposure balanced across themes and within limits.";
            }
            return `AI allocation at ${metrics.aiInfraPct}%. Review concentration.`;

        case 'tax-aware':
            if (status === 'passing') {
                return "Tax efficiency optimized. No wash sale risks detected.";
            }
            return "Tax optimization opportunities available.";

        case 'behavioral':
            if (status === 'passing') {
                return "No concerning trading patterns. Discipline maintained.";
            }
            return "Recent trading shows signs of reactive behavior.";

        default:
            return status === 'passing' ? "All checks passing." : "Some rules need attention.";
    }
}

/**
 * Handle quick action button clicks
 */
function handleQuickAction(actionId, metrics) {
    switch(actionId) {
        case 'add-cash':
            showToast('Consider transferring funds to increase your cash buffer to 5%+', 'info');
            break;
        case 'trim-position':
            showToast('Review your largest positions and consider trimming to reduce concentration', 'info');
            break;
        case 'diversify-sector':
            showToast('Your sector allocation is concentrated. Consider adding positions in other sectors', 'info');
            break;
        case 'review-warnings':
            // Scroll to principles section
            document.querySelector('.principles-section')?.scrollIntoView({ behavior: 'smooth' });
            break;
        default:
            console.log('Unknown action:', actionId);
    }
}

/**
 * Show toast notification (reuse from email tab)
 */
function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'success' ? '✓' : type === 'warning' ? '⚠️' : 'ℹ️'}</span>
        <span class="toast-message">${message}</span>
    `;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/**
 * Calculate portfolio metrics from holdings
 */
function calculatePortfolioMetrics(data) {
    const holdings = data.holdings || [];
    const totalValue = data.total_value || 0;

    // Calculate position percentages
    let maxPositionPct = 0;
    let cashPct = 0;
    const sectorTotals = {};

    holdings.forEach(h => {
        const pct = totalValue > 0 ? (h.market_value / totalValue * 100) : 0;
        if (pct > maxPositionPct) maxPositionPct = pct;

        if (h.security_type === 'cash' || h.ticker === 'CASH') {
            cashPct += pct;
        }

        const sector = h.sector || 'Unknown';
        sectorTotals[sector] = (sectorTotals[sector] || 0) + pct;
    });

    const maxSectorPct = Math.max(...Object.values(sectorTotals), 0);

    // Return metrics (many will be 0 until we implement full tracking)
    return {
        maxPositionPct: maxPositionPct.toFixed(1),
        maxSectorPct: maxSectorPct.toFixed(1),
        speculativePct: 0,
        cashPct: cashPct.toFixed(1),
        drawdownPct: 0,
        turnoverPct: 0,
        minHoldingDays: '-',
        indexCorePct: 0,
        bandDrift: 0,
        thesisCoverage: 0,
        avgQualityScore: '-',
        moatCoverage: 0,
        avgDownReviews: 0,
        aiThemeCount: 0,
        aiInfraPct: 0,
        maxAiPositionPct: 0,
        aiThesisAge: '-',
        stGainRisk: 0,
        washSaleRisk: 0,
        tlhOpportunities: 0,
        employerPct: 0,
        assetLocationScore: '-',
        panicSellRisk: 0,
        recentChanges: 0,
        newPositions: 0,
    };
}

/**
 * Render a single rule item
 */
function renderRuleItem(rule) {
    const status = getRuleStatus(rule);
    const icon = status === 'passing' ? '✅' : status === 'warning' ? '⚠️' : status === 'failing' ? '❌' : '◯';

    return `
        <div class="rule-item ${status}">
            <span class="rule-icon">${icon}</span>
            <div class="rule-content">
                <div class="rule-name">${rule.id}: ${rule.name}</div>
                <div class="rule-description">${rule.desc}</div>
            </div>
            <div class="rule-value">
                <div class="rule-current">${rule.value}${rule.unit}</div>
                <div class="rule-limit">${rule.invert ? 'Min' : 'Max'}: ${rule.limit}${rule.unit}</div>
            </div>
        </div>
    `;
}

/**
 * Get rule status (passing, warning, failing)
 */
function getRuleStatus(rule) {
    const value = parseFloat(rule.value) || 0;
    const limit = rule.limit;

    if (rule.neutral) return 'passing';
    if (rule.value === '-' || rule.value === 0) return 'passing'; // No data yet

    if (rule.invert) {
        // Higher is better (e.g., cash minimum, index core)
        if (value >= limit) return 'passing';
        if (value >= limit * 0.8) return 'warning';
        return 'failing';
    } else {
        // Lower is better (e.g., max position size)
        if (value <= limit) return 'passing';
        if (value <= limit * 1.2) return 'warning';
        return 'failing';
    }
}

/**
 * Get category status based on rules
 */
function getCategoryStatus(rules) {
    const statuses = rules.map(r => getRuleStatus(r));

    if (statuses.some(s => s === 'failing')) {
        return { class: 'failing', text: 'Needs Attention' };
    }
    if (statuses.some(s => s === 'warning')) {
        return { class: 'warning', text: 'Warning' };
    }
    return { class: 'passing', text: 'All Passing' };
}

/**
 * Sync all connected accounts
 */
async function syncAllAccounts() {
    const syncBtn = document.getElementById('sync-all-btn');
    const statusDiv = document.getElementById('sync-status');

    syncBtn.disabled = true;
    syncBtn.innerHTML = '<span class="btn-icon spinner-icon">⏳</span> Syncing...';
    statusDiv.className = 'sync-status';
    statusDiv.innerHTML = '<span class="spinner"></span> Syncing accounts with Plaid...';

    try {
        const response = await fetch(`${API_BASE}/api/plaid/sync-all`, { method: 'POST' });
        const result = await response.json();

        if (result.success) {
            statusDiv.className = 'sync-status success';
            statusDiv.innerHTML = `✅ ${result.message}`;

            // Reload holdings tab
            const tabContent = document.getElementById('portfolio-tab-content');
            if (tabContent) {
                await loadHoldingsTab(tabContent);
            }
        } else {
            statusDiv.className = 'sync-status warning';
            statusDiv.innerHTML = `⚠️ ${result.message}`;
        }

        // Show details
        if (result.synced && result.synced.length > 0) {
            let details = '<div class="sync-details">';
            result.synced.forEach(s => {
                const icon = s.success ? '✅' : '❌';
                details += `<div>${icon} ${escapeHtml(s.institution)}: `;
                if (s.success) {
                    details += `${s.securities} securities, ${s.positions} positions`;
                } else {
                    details += `${escapeHtml(s.error)}`;
                }
                details += '</div>';
            });
            details += '</div>';
            statusDiv.innerHTML += details;
        }

    } catch (error) {
        console.error('Sync failed:', error);
        statusDiv.className = 'sync-status error';
        statusDiv.innerHTML = `❌ Sync failed: ${escapeHtml(error.message)}`;
    } finally {
        syncBtn.disabled = false;
        syncBtn.innerHTML = '<span class="btn-icon">🔄</span> Sync All';
    }
}

/**
 * Format currency for display
 */
function formatCurrency(amount) {
    if (!amount && amount !== 0) return '0.00';
    return Math.abs(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Truncate string
 */
function truncate(str, maxLen) {
    if (!str) return '';
    return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
}

/**
 * Create account card element
 */
/**
 * Create account card with detailed account list
 */
function createAccountCardWithDetails(item, accounts) {
    const card = document.createElement('div');
    card.className = 'account-card expanded';

    const isActive = item.is_active !== false;
    const statusClass = isActive ? 'status-active' : 'status-error';
    const statusText = isActive ? 'Connected' : 'Needs Attention';
    const lastSync = item.last_sync || item.last_successful_update;

    // Build accounts list HTML
    const accountsListHtml = accounts.length > 0
        ? accounts.map(acc => `
            <div class="sub-account-item">
                <span class="sub-account-icon">${getAccountIcon(acc.type)}</span>
                <div class="sub-account-info">
                    <span class="sub-account-name">${escapeHtml(acc.name)}</span>
                    <span class="sub-account-type">${escapeHtml(acc.subtype || acc.type)}</span>
                </div>
            </div>
        `).join('')
        : '<div class="no-accounts">No accounts found</div>';

    card.innerHTML = `
        <div class="account-card-header">
            <div class="institution-info">
                <span class="institution-icon">🏦</span>
                <span class="institution-name">${escapeHtml(item.institution_name || 'Unknown Institution')}</span>
            </div>
            <span class="account-status ${statusClass}">${statusText}</span>
        </div>
        <div class="account-card-body">
            <div class="sub-accounts-section">
                <div class="sub-accounts-header">
                    <span class="sub-accounts-title">${accounts.length} Account${accounts.length !== 1 ? 's' : ''}</span>
                    <span class="last-sync-info">Last sync: ${formatLastSync(lastSync)}</span>
                </div>
                <div class="sub-accounts-list">
                    ${accountsListHtml}
                </div>
            </div>
        </div>
        <div class="account-card-actions">
            <button class="btn-text refresh-btn" data-item-id="${item.item_id}">Refresh</button>
            <button class="btn-text danger disconnect-btn" data-item-id="${item.item_id}">Disconnect</button>
        </div>
    `;

    // Setup action buttons
    setTimeout(() => {
        card.querySelector('.refresh-btn')?.addEventListener('click', () => {
            syncSingleItem(item.item_id);
        });
        card.querySelector('.disconnect-btn')?.addEventListener('click', () => {
            if (confirm(`Disconnect ${item.institution_name}? This will remove all synced data.`)) {
                disconnectItem(item.item_id);
            }
        });
    }, 0);

    return card;
}

/**
 * Get icon for account type
 */
function getAccountIcon(type) {
    const icons = {
        'investment': '📈',
        'brokerage': '📊',
        'depository': '🏦',
        'credit': '💳',
        'loan': '💰',
        'retirement': '🏖️',
    };
    return icons[type] || '📁';
}

function createAccountCard(item) {
    const card = document.createElement('div');
    card.className = 'account-card';

    // API returns is_active (boolean), not status string
    const isActive = item.is_active !== false;
    const statusClass = isActive ? 'status-active' : 'status-error';
    const statusText = isActive ? 'Connected' : 'Needs Attention';

    // API returns last_sync, not last_successful_update
    const lastSync = item.last_sync || item.last_successful_update;

    card.innerHTML = `
        <div class="account-card-header">
            <div class="institution-info">
                <span class="institution-icon">🏦</span>
                <span class="institution-name">${escapeHtml(item.institution_name || 'Unknown Institution')}</span>
            </div>
            <span class="account-status ${statusClass}">${statusText}</span>
        </div>
        <div class="account-card-body">
            <div class="account-details">
                <div class="account-detail">
                    <span class="detail-label">Products</span>
                    <span class="detail-value">${(item.products || []).length}</span>
                </div>
                <div class="account-detail">
                    <span class="detail-label">Last Sync</span>
                    <span class="detail-value">${formatLastSync(lastSync)}</span>
                </div>
            </div>
        </div>
        <div class="account-card-actions">
            <button class="btn-text refresh-btn" data-item-id="${item.item_id}">Refresh</button>
            <button class="btn-text danger disconnect-btn" data-item-id="${item.item_id}">Disconnect</button>
        </div>
    `;

    // Setup action buttons
    setTimeout(() => {
        card.querySelector('.refresh-btn')?.addEventListener('click', () => {
            refreshPlaidItem(item.item_id);
        });
        card.querySelector('.disconnect-btn')?.addEventListener('click', () => {
            disconnectPlaidItem(item.item_id);
        });
    }, 0);

    return card;
}

/**
 * Format last sync time
 */
function formatLastSync(timestamp) {
    if (!timestamp) return 'Never';
    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffHours = diffMs / (1000 * 60 * 60);

        if (diffHours < 1) {
            return 'Just now';
        } else if (diffHours < 24) {
            return `${Math.floor(diffHours)}h ago`;
        } else {
            return date.toLocaleDateString();
        }
    } catch (e) {
        return 'Unknown';
    }
}

/**
 * Format number with commas
 */
function formatNumber(num) {
    if (!num) return '0';
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Global Plaid handler reference for cleanup
let currentPlaidHandler = null;

/**
 * Initiate Plaid Link flow
 */
async function initiatePlaidLink() {
    const btn = document.getElementById('connect-plaid-btn') || document.getElementById('add-account-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="btn-icon">⏳</span> Connecting...';
    }

    try {
        // Destroy any existing Plaid handler to ensure fresh start
        if (currentPlaidHandler) {
            try {
                currentPlaidHandler.destroy();
            } catch (e) {
                console.log('Could not destroy previous handler:', e);
            }
            currentPlaidHandler = null;
        }

        // Clear any Plaid OAuth state from localStorage
        try {
            Object.keys(localStorage).forEach(key => {
                if (key.startsWith('plaid') || key.includes('oauth')) {
                    localStorage.removeItem(key);
                }
            });
        } catch (e) {
            console.log('Could not clear localStorage:', e);
        }

        // Step 1: Get fresh link token from backend
        const response = await fetch(`${API_BASE}/api/plaid/link-token?user_id=current_user&t=${Date.now()}`);

        if (!response.ok) {
            throw new Error('Failed to get link token');
        }

        const { link_token } = await response.json();
        console.log('Got fresh Plaid link token');

        // Step 2: Open Plaid Link with the token
        if (typeof Plaid === 'undefined') {
            throw new Error('Plaid SDK not loaded. Please refresh the page.');
        }

        currentPlaidHandler = Plaid.create({
            token: link_token,
            onSuccess: async (public_token, metadata) => {
                console.log('Plaid Link success:', metadata.institution?.name);
                await exchangePlaidToken(public_token, metadata);
            },
            onExit: (err, metadata) => {
                console.log('Plaid Link exited:', err?.error_message || 'User cancelled');
                resetConnectButton();
            },
            onEvent: (eventName, metadata) => {
                console.log('Plaid event:', eventName);
            }
        });

        currentPlaidHandler.open();

    } catch (error) {
        console.error('Plaid Link initiation failed:', error);
        alert('Failed to open account connection: ' + error.message);
        resetConnectButton();
    }
}

/**
 * Exchange Plaid public token for access token
 */
async function exchangePlaidToken(publicToken, metadata) {
    const statusDiv = document.createElement('div');
    statusDiv.className = 'plaid-exchange-status';
    statusDiv.innerHTML = `
        <div class="exchange-progress">
            <span class="spinner"></span>
            <span>Securing connection to ${escapeHtml(metadata.institution?.name || 'institution')}...</span>
        </div>
    `;
    document.getElementById('financial-content')?.appendChild(statusDiv);

    try {
        const response = await fetch(`${API_BASE}/api/plaid/exchange`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                public_token: publicToken,
                institution_id: metadata.institution?.institution_id,
                institution_name: metadata.institution?.name
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Token exchange failed');
        }

        const result = await response.json();
        console.log('Token exchange successful:', result.item_id);

        // Show success and reload
        statusDiv.innerHTML = `
            <div class="exchange-success">
                <span class="success-icon">✅</span>
                <span>Successfully connected to ${escapeHtml(metadata.institution?.name)}!</span>
            </div>
        `;

        // Reload the view after 1.5 seconds
        setTimeout(() => {
            const container = document.getElementById('financial-content');
            if (container) {
                loadFinancialStatus(container);
            }
        }, 1500);

    } catch (error) {
        console.error('Token exchange failed:', error);
        statusDiv.innerHTML = `
            <div class="exchange-error">
                <span class="error-icon">❌</span>
                <span>Failed to connect: ${escapeHtml(error.message)}</span>
                <button onclick="this.parentElement.parentElement.remove(); resetConnectButton();" class="btn-text">Dismiss</button>
            </div>
        `;
    }
}

/**
 * Reset connect button to initial state
 */
function resetConnectButton() {
    const connectBtn = document.getElementById('connect-plaid-btn');
    const addBtn = document.getElementById('add-account-btn');

    if (connectBtn) {
        connectBtn.disabled = false;
        connectBtn.innerHTML = '<span class="btn-icon">🔗</span> Connect Account';
    }
    if (addBtn) {
        addBtn.disabled = false;
        addBtn.innerHTML = '<span class="btn-icon">+</span> Add Account';
    }
}

/**
 * Refresh a Plaid item (sync latest data)
 */
async function refreshPlaidItem(itemId) {
    // For now, just reload the page to re-sync
    // TODO: Implement proper item refresh via backend
    alert('Refreshing account data...');
    location.reload();
}

/**
 * Disconnect a Plaid item
 */
async function disconnectPlaidItem(itemId) {
    if (!confirm('Are you sure you want to disconnect this account?')) return;

    try {
        const response = await fetch(`${API_BASE}/api/plaid/items/${itemId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to disconnect');
        }

        alert('Account disconnected successfully');
        location.reload();

    } catch (error) {
        console.error('Disconnect failed:', error);
        alert('Failed to disconnect: ' + error.message);
    }
}

// Export functions
// Note: renderAnalyticsView, renderReportsView, renderKnowledgeBaseView, renderInsightsView
// deprecated in favor of v2 components / Cognitive dashboard (Feb 2026)
module.exports = {
    renderMemoryBrowser,
    renderSearchView,
    renderAPIAnalyticsView,
    renderDataFlowView,
    renderGmailView,
    renderFinancialView
};
