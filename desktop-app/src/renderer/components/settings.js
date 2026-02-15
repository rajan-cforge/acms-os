/**
 * Settings Component
 * Sprint 6: Polish & Integration
 *
 * User settings and preferences
 */

const { fetchWithAuth } = require('../api-client');

class Settings {
    constructor(container) {
        this.container = container;
        this.settings = {
            theme: 'dark',
            defaultAgent: 'Claude',
            cacheEnabled: true,
            notificationsEnabled: true,
            autoSync: true,
            privacyMode: false
        };
    }

    async init() {
        await this.loadSettings();
        this.render();
    }

    async loadSettings() {
        try {
            const stored = localStorage.getItem('acms_settings');
            if (stored) {
                this.settings = { ...this.settings, ...JSON.parse(stored) };
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    saveSettings() {
        try {
            localStorage.setItem('acms_settings', JSON.stringify(this.settings));
        } catch (error) {
            console.error('Failed to save settings:', error);
        }
    }

    render() {
        this.container.innerHTML = `
            <div class="settings-container">
                <div class="settings-header">
                    <h2>Settings</h2>
                </div>

                <div class="settings-sections">
                    <div class="settings-section">
                        <h3>Appearance</h3>
                        <div class="setting-item">
                            <div class="setting-info">
                                <div class="setting-label">Theme</div>
                                <div class="setting-description">Choose your preferred color scheme</div>
                            </div>
                            <select id="themeSetting" class="input setting-select" onchange="window.settingsView.updateSetting('theme', this.value)">
                                <option value="dark" ${this.settings.theme === 'dark' ? 'selected' : ''}>Dark</option>
                                <option value="light" ${this.settings.theme === 'light' ? 'selected' : ''}>Light</option>
                                <option value="system" ${this.settings.theme === 'system' ? 'selected' : ''}>System</option>
                            </select>
                        </div>
                    </div>

                    <div class="settings-section">
                        <h3>AI & Chat</h3>
                        <div class="setting-item">
                            <div class="setting-info">
                                <div class="setting-label">Default Agent</div>
                                <div class="setting-description">Preferred AI model for conversations</div>
                            </div>
                            <select id="agentSetting" class="input setting-select" onchange="window.settingsView.updateSetting('defaultAgent', this.value)">
                                <option value="Claude" ${this.settings.defaultAgent === 'Claude' ? 'selected' : ''}>Claude (Sonnet 4.5)</option>
                                <option value="GPT" ${this.settings.defaultAgent === 'GPT' ? 'selected' : ''}>GPT-5.1</option>
                                <option value="Gemini" ${this.settings.defaultAgent === 'Gemini' ? 'selected' : ''}>Gemini 3 Flash</option>
                                <option value="Ollama" ${this.settings.defaultAgent === 'Ollama' ? 'selected' : ''}>Ollama (Local)</option>
                            </select>
                        </div>
                        <div class="setting-item">
                            <div class="setting-info">
                                <div class="setting-label">Response Caching</div>
                                <div class="setting-description">Cache similar queries to improve speed</div>
                            </div>
                            <label class="toggle">
                                <input type="checkbox" ${this.settings.cacheEnabled ? 'checked' : ''} onchange="window.settingsView.updateSetting('cacheEnabled', this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>

                    <div class="settings-section">
                        <h3>Notifications</h3>
                        <div class="setting-item">
                            <div class="setting-info">
                                <div class="setting-label">Enable Notifications</div>
                                <div class="setting-description">Get nudges and insights from ACMS</div>
                            </div>
                            <label class="toggle">
                                <input type="checkbox" ${this.settings.notificationsEnabled ? 'checked' : ''} onchange="window.settingsView.updateSetting('notificationsEnabled', this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>

                    <div class="settings-section">
                        <h3>Data & Sync</h3>
                        <div class="setting-item">
                            <div class="setting-info">
                                <div class="setting-label">Auto Sync</div>
                                <div class="setting-description">Automatically sync with connected services</div>
                            </div>
                            <label class="toggle">
                                <input type="checkbox" ${this.settings.autoSync ? 'checked' : ''} onchange="window.settingsView.updateSetting('autoSync', this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>

                    <div class="settings-section">
                        <h3>Privacy</h3>
                        <div class="setting-item">
                            <div class="setting-info">
                                <div class="setting-label">Privacy Mode</div>
                                <div class="setting-description">Restrict sensitive data from external APIs</div>
                            </div>
                            <label class="toggle">
                                <input type="checkbox" ${this.settings.privacyMode ? 'checked' : ''} onchange="window.settingsView.updateSetting('privacyMode', this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>

                    <div class="settings-section">
                        <h3>Connections</h3>
                        <div class="connections-grid">
                            <div class="connection-card" id="gmailConnection">
                                <div class="connection-icon">📧</div>
                                <div class="connection-name">Gmail</div>
                                <div class="connection-status loading">Checking...</div>
                            </div>
                            <div class="connection-card" id="plaidConnection">
                                <div class="connection-icon">🏦</div>
                                <div class="connection-name">Plaid</div>
                                <div class="connection-status loading">Checking...</div>
                            </div>
                            <div class="connection-card" id="ollamaConnection">
                                <div class="connection-icon">🤖</div>
                                <div class="connection-name">Ollama</div>
                                <div class="connection-status loading">Checking...</div>
                            </div>
                        </div>
                    </div>

                    <div class="settings-section">
                        <h3>About</h3>
                        <div class="about-info">
                            <div class="about-row">
                                <span class="about-label">Version</span>
                                <span class="about-value">1.0.0</span>
                            </div>
                            <div class="about-row">
                                <span class="about-label">API Endpoint</span>
                                <span class="about-value">http://localhost:40080</span>
                            </div>
                            <div class="about-row">
                                <span class="about-label">Database</span>
                                <span class="about-value">PostgreSQL @ :40432</span>
                            </div>
                            <div class="about-row">
                                <span class="about-label">Vector DB</span>
                                <span class="about-value">Weaviate @ :40480</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.checkConnections();
    }

    updateSetting(key, value) {
        this.settings[key] = value;
        this.saveSettings();

        if (key === 'theme') {
            this.applyTheme(value);
        }
    }

    applyTheme(theme) {
        if (theme === 'system') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            document.body.classList.toggle('light-theme', !prefersDark);
        } else {
            document.body.classList.toggle('light-theme', theme === 'light');
        }
    }

    async checkConnections() {
        // Check Gmail
        try {
            const response = await fetchWithAuth('/api/gmail/status');
            const gmail = document.getElementById('gmailConnection');
            if (response.ok) {
                const data = await response.json();
                gmail.querySelector('.connection-status').textContent = data.connected ? 'Connected' : 'Not connected';
                gmail.querySelector('.connection-status').className = `connection-status ${data.connected ? 'connected' : 'disconnected'}`;
            }
        } catch (error) {
            const gmail = document.getElementById('gmailConnection');
            gmail.querySelector('.connection-status').textContent = 'Error';
            gmail.querySelector('.connection-status').className = 'connection-status error';
        }

        // Check Plaid
        try {
            const response = await fetchWithAuth('/api/plaid/status');
            const plaid = document.getElementById('plaidConnection');
            if (response.ok) {
                const data = await response.json();
                plaid.querySelector('.connection-status').textContent = data.connected ? `${data.active_connections} accounts` : 'Not connected';
                plaid.querySelector('.connection-status').className = `connection-status ${data.connected ? 'connected' : 'disconnected'}`;
            }
        } catch (error) {
            const plaid = document.getElementById('plaidConnection');
            plaid.querySelector('.connection-status').textContent = 'Error';
            plaid.querySelector('.connection-status').className = 'connection-status error';
        }

        // Check Ollama
        try {
            const response = await fetch('http://localhost:40434/api/tags');
            const ollama = document.getElementById('ollamaConnection');
            if (response.ok) {
                ollama.querySelector('.connection-status').textContent = 'Running';
                ollama.querySelector('.connection-status').className = 'connection-status connected';
            }
        } catch (error) {
            const ollama = document.getElementById('ollamaConnection');
            ollama.querySelector('.connection-status').textContent = 'Not running';
            ollama.querySelector('.connection-status').className = 'connection-status disconnected';
        }
    }
}

// Export for use in renderer
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Settings };
}
