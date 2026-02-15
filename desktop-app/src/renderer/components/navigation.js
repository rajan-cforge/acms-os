/**
 * Navigation Component
 * Sprint 6: Polish & Integration
 *
 * Unified navigation sidebar for all ACMS views
 */

class Navigation {
    constructor(container, onNavigate) {
        this.container = container;
        this.onNavigate = onNavigate;
        this.currentView = 'chat';
    }

    render() {
        this.container.innerHTML = `
            <nav class="main-nav">
                <div class="nav-brand">
                    <span class="brand-icon">🧠</span>
                    <span class="brand-text">ACMS</span>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">Main</div>
                    <button class="nav-item ${this.currentView === 'chat' ? 'active' : ''}" data-view="chat">
                        <span class="nav-icon">💬</span>
                        <span class="nav-label">Chat</span>
                    </button>
                    <button class="nav-item ${this.currentView === 'timeline' ? 'active' : ''}" data-view="timeline">
                        <span class="nav-icon">📅</span>
                        <span class="nav-label">Memory Timeline</span>
                    </button>
                    <button class="nav-item ${this.currentView === 'knowledge' ? 'active' : ''}" data-view="knowledge">
                        <span class="nav-icon">📚</span>
                        <span class="nav-label">Knowledge Base</span>
                    </button>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">Finance</div>
                    <button class="nav-item ${this.currentView === 'portfolio' ? 'active' : ''}" data-view="portfolio">
                        <span class="nav-icon">📊</span>
                        <span class="nav-label">Portfolio</span>
                    </button>
                    <button class="nav-item ${this.currentView === 'constitution' ? 'active' : ''}" data-view="constitution">
                        <span class="nav-icon">📋</span>
                        <span class="nav-label">Constitution</span>
                    </button>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">Insights</div>
                    <button class="nav-item ${this.currentView === 'reports' ? 'active' : ''}" data-view="reports">
                        <span class="nav-icon">📈</span>
                        <span class="nav-label">Reports</span>
                    </button>
                    <button class="nav-item ${this.currentView === 'clusters' ? 'active' : ''}" data-view="clusters">
                        <span class="nav-icon">🔗</span>
                        <span class="nav-label">Clusters</span>
                    </button>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">Integrations</div>
                    <button class="nav-item ${this.currentView === 'gmail' ? 'active' : ''}" data-view="gmail">
                        <span class="nav-icon">📧</span>
                        <span class="nav-label">Gmail</span>
                    </button>
                    <button class="nav-item ${this.currentView === 'plaid' ? 'active' : ''}" data-view="plaid">
                        <span class="nav-icon">🏦</span>
                        <span class="nav-label">Plaid</span>
                    </button>
                </div>

                <div class="nav-spacer"></div>

                <div class="nav-section">
                    <button class="nav-item ${this.currentView === 'settings' ? 'active' : ''}" data-view="settings">
                        <span class="nav-icon">⚙️</span>
                        <span class="nav-label">Settings</span>
                    </button>
                </div>
            </nav>
        `;

        this.bindEvents();
    }

    bindEvents() {
        this.container.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                this.navigate(view);
            });
        });
    }

    navigate(view) {
        this.currentView = view;
        this.render();
        if (this.onNavigate) {
            this.onNavigate(view);
        }
    }

    setActive(view) {
        this.currentView = view;
        this.render();
    }
}

// Export for use in renderer
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Navigation };
}
