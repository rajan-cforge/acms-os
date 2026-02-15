/**
 * ACMS Desktop App - Main Application
 *
 * Week 5 Day 2: Production-Quality Chat-First Interface
 * Sprint 3 Day 11-12: Authentication + Role Badge UI
 * Sprint 3 Day 14: Stop Generation + Edit Messages
 *
 * Architecture:
 * - Modular components (message.js, input.js, sidebar.js, login.js)
 * - Clean state management
 * - Event delegation for dynamic content
 * - Security: No innerHTML, all DOM manipulation via createElement
 * - Authentication flow with role-based UI
 * - Stop generation capability
 * - Edit message and regenerate
 */

const { ipcRenderer } = require('electron');

// Import components
const { createMessageBubble, setupFeedbackListeners, setEditMessageCallback } = require('./components/message.js');
const { setupInputArea, focusInput } = require('./components/input.js');
const { setupSidebar } = require('./components/sidebar.js');
const { renderMemoryBrowser, renderSearchView, renderAPIAnalyticsView, renderDataFlowView, renderGmailView, renderFinancialView } = require('./components/views.js');
const { renderLoginScreen, checkExistingSession, renderUserInfo } = require('./components/login.js');
const { checkHealth, sendChatMessage, loadConversations } = require('./utils/api.js');
const { streamChatMessage, abortCurrentStream, isStreaming } = require('./utils/streaming.js');
const { getConversation } = require('./utils/conversations.js');
const { ensureConversation } = require('./utils/message-persistence.js');
const { getCurrentUser, clearAuth, isAuthenticated } = require('./utils/auth.js');
// Active Second Brain (Jan 2026)
const { initFeedbackModal, showFeedbackModal } = require('./components/feedback-modal.js');
const { initNudgeSidebar } = require('./components/nudge-sidebar.js');

// Cognitive Architecture (Feb 2026)
const cognitive = require('./components/cognitive');

// Sprint 3-6: New integrated components
const { KnowledgeBrowser } = require('./components/knowledge-browser.js');
const { PortfolioConstitution } = require('./components/portfolio-constitution.js');
const { ReportsDashboard } = require('./components/reports-dashboard.js');
const { Settings } = require('./components/settings.js');

class AcmsApp {
    constructor() {
        this.state = {
            currentView: 'chat', // Default to chat view
            featureFlagNewUI: true, // Production-ready
            enableStreaming: true, // Week 5 Day 3: Streaming responses
            currentConversationId: null,
            messages: [],
            conversations: [],
            loading: false,
            error: null,
            apiHealth: { status: 'checking' },
            currentStream: null, // Active stream abort function
            // Sprint 3 Day 11-12: Authentication state
            user: null,
            isAuthenticated: false,
            // Sprint 3 Day 15: File upload context (ChatGPT-style)
            pendingFileContext: null  // {filename, extracted_text, memory_id}
        };

        this.init();
    }

    async init() {
        console.log('🚀 ACMS Desktop starting...');

        // Check API health first
        await this.checkApiHealth();

        // Sprint 3 Day 11-12: Check for existing session
        const existingUser = await checkExistingSession();

        if (existingUser) {
            console.log('✅ Existing session found:', existingUser.email);
            this.state.user = existingUser;
            this.state.isAuthenticated = true;
            this.initMainApp();
        } else {
            console.log('🔐 No session found, showing login screen');
            this.showLoginScreen();
        }
    }

    /**
     * Show login screen
     */
    showLoginScreen() {
        const root = document.getElementById('root');
        renderLoginScreen(root, (user) => this.onLoginSuccess(user));
    }

    /**
     * Handle successful login
     * @param {Object} user - User data from login
     */
    onLoginSuccess(user) {
        console.log('✅ Login successful:', user.email);
        this.state.user = user;
        this.state.isAuthenticated = true;

        // Set role class on body for CSS-based visibility
        document.body.className = `role-${user.role}`;

        // Initialize main app
        this.initMainApp();
    }

    /**
     * Handle logout
     */
    onLogout() {
        console.log('🔐 User logged out');
        this.state.user = null;
        this.state.isAuthenticated = false;
        this.state.messages = [];
        this.state.currentConversationId = null;

        // Remove role class
        document.body.className = '';

        // Show login screen
        this.showLoginScreen();
    }

    /**
     * Initialize main application after authentication
     */
    async initMainApp() {
        // Set role class on body for CSS-based visibility
        if (this.state.user) {
            document.body.className = `role-${this.state.user.role}`;
        }

        // Setup layout
        this.setupLayout();

        // Setup components
        this.setupComponents();

        // Setup event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadInitialData();

        console.log('✅ ACMS Desktop ready!');
    }

    setupLayout() {
        const root = document.getElementById('root');

        // Get user info for header
        const user = this.state.user;
        const userDisplay = user ? `
            <div class="header-user-badge">
                <span class="user-email">${user.username || user.email}</span>
                <span class="role-badge role-${user.role}">${user.role.toUpperCase()}</span>
                <button id="logout-btn" class="logout-btn" title="Sign out">↗</button>
            </div>
        ` : '';

        // Main layout: Sidebar + Chat Area
        const layout = `
            <div class="app-container">
                <aside id="sidebar" class="sidebar">
                    <!-- Sidebar content will be rendered by sidebar.js -->
                </aside>
                <main class="chat-area">
                    <div id="chat-header" class="chat-header chat-header-with-user">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <h2>Chat</h2>
                            <div id="status-indicator" class="status-indicator"></div>
                        </div>
                        ${userDisplay}
                    </div>
                    <div id="messages-container" class="messages-container">
                        <!-- Messages will be rendered here -->
                    </div>
                    <div id="input-area" class="input-area">
                        <!-- Input area will be rendered by input.js -->
                    </div>
                </main>
            </div>
        `;

        root.innerHTML = layout;

        // Setup logout button handler
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.onLogout());
        }

        console.log('📐 Layout created');
    }

    setupComponents() {
        // Setup sidebar with conversation loading callback
        setupSidebar(
            this.state,
            (view) => this.switchView(view),
            (conversationId) => this.handleConversationLoad(conversationId)
        );

        // Setup input area with file upload callback (Sprint 3 Day 15: ChatGPT-style file context)
        setupInputArea(
            (message, agent) => this.handleSendMessage(message, agent),
            (file, uploadResult) => this.handleFileUploaded(file, uploadResult)
        );

        // Sprint 3 Day 14: Setup edit message callback
        setEditMessageCallback((messageId, newContent) => this.handleEditMessage(messageId, newContent));

        // Active Second Brain (Jan 2026): Initialize feedback modal and nudge sidebar
        initFeedbackModal();
        initNudgeSidebar();

        // Cognitive Architecture (Feb 2026): Initialize cognitive UI components
        try {
            cognitive.initAll();
            console.log('🧬 Cognitive components initialized');
        } catch (e) {
            console.warn('Cognitive components initialization failed:', e);
        }

        console.log('🧩 Components initialized');
    }

    /**
     * Handle message edit and regenerate response
     *
     * Sprint 3 Day 14: Edit Message capability
     *
     * @param {string} messageId - ID of the message that was edited
     * @param {string} newContent - New message content
     */
    async handleEditMessage(messageId, newContent) {
        console.log('✏️  Message edited:', { messageId, newContent });

        // Find the message index
        const messageIndex = this.state.messages.findIndex(m => m.id === messageId);
        if (messageIndex === -1) {
            console.error('❌ Message not found:', messageId);
            return;
        }

        // Remove all messages after this one (including assistant response)
        const removedMessages = this.state.messages.splice(messageIndex + 1);
        console.log(`🗑️  Removed ${removedMessages.length} messages after edit`);

        // Update the UI to remove those messages
        removedMessages.forEach(msg => {
            const element = document.querySelector(`[data-message-id="${msg.id}"]`);
            if (element) {
                element.remove();
            }
        });

        // Update the edited message content in state
        this.state.messages[messageIndex].content = newContent;

        // Get the agent from the previous response or use 'auto'
        const agent = removedMessages[0]?.metadata?.agent || 'auto';

        // Regenerate response with the edited message
        this.setLoading(true);

        if (this.state.enableStreaming) {
            this.handleStreamingMessage(newContent, agent);
        } else {
            await this.handleSyncMessage(newContent, agent);
        }
    }

    /**
     * Stop the current generation
     *
     * Sprint 3 Day 14: Stop Generation capability
     */
    handleStopGeneration() {
        console.log('🛑 Stopping generation...');

        if (abortCurrentStream()) {
            console.log('✅ Generation stopped');
            this.setLoading(false);
        } else {
            console.log('⚠️  No active stream to stop');
        }
    }

    setupEventListeners() {
        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + N: New chat
            if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
                e.preventDefault();
                this.createNewChat();
            }

            // Cmd/Ctrl + /: Focus input
            if ((e.metaKey || e.ctrlKey) && e.key === '/') {
                e.preventDefault();
                focusInput();
            }

            // Sprint 3 Day 14: Escape to stop generation
            if (e.key === 'Escape' && this.state.loading) {
                e.preventDefault();
                this.handleStopGeneration();
            }
        });

        // Cross-view navigation: Handle acms-navigate events
        // Used for Insights → Knowledge Base navigation with filters
        window.addEventListener('acms-navigate', (e) => {
            const { view, filters } = e.detail || {};
            if (view) {
                console.log('🔀 Cross-view navigation:', view, filters);
                this.switchView(view, filters);
            }
        });

        console.log('⌨️  Event listeners registered');
    }

    async checkApiHealth() {
        try {
            const health = await checkHealth();
            this.state.apiHealth = health;
            this.updateStatusIndicator(health.status);
            console.log('🏥 API Health:', health.status);
        } catch (error) {
            console.error('❌ Health check failed:', error);
            this.state.apiHealth = { status: 'disconnected' };
            this.updateStatusIndicator('disconnected');
        }
    }

    updateStatusIndicator(status) {
        const indicator = document.getElementById('status-indicator');
        if (indicator) {
            // Accept both 'connected' and 'healthy' as connected states
            const isConnected = status === 'connected' || status === 'healthy';
            indicator.className = `status-indicator ${isConnected ? 'connected' : 'disconnected'}`;
            indicator.title = isConnected ? 'API Connected' : 'API Disconnected';
        }
    }

    async loadInitialData() {
        // Check API health status (status can be 'healthy' or 'connected')
        if (this.state.apiHealth.status !== 'connected' && this.state.apiHealth.status !== 'healthy') {
            this.showError('Cannot connect to ACMS API. Please ensure Docker containers are running.');
            return;
        }

        try {
            // Load conversations
            const conversations = await loadConversations();
            this.state.conversations = conversations;
            console.log(`📚 Loaded ${conversations.length} conversations`);

            // Update sidebar with conversation loading callback
            setupSidebar(
                this.state,
                (view) => this.switchView(view),
                (conversationId) => this.handleConversationLoad(conversationId)
            );

        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            // Don't show error for conversations - it's not critical
        }
    }

    /**
     * Handle file upload completion (Sprint 3 Day 15: ChatGPT-style file context)
     *
     * When a file is uploaded, store its content so the next message
     * includes the file context - exactly like ChatGPT.
     *
     * @param {File} file - The uploaded file object
     * @param {Object} uploadResult - Result from /gateway/upload API
     */
    handleFileUploaded(file, uploadResult) {
        console.log('📎 File uploaded:', {
            filename: file.name,
            memory_id: uploadResult.memory_id,
            extracted_text_length: uploadResult.extracted_text?.length || 0
        });

        // Store file context for the next message
        this.state.pendingFileContext = {
            filename: file.name,
            extracted_text: uploadResult.extracted_text,
            memory_id: uploadResult.memory_id,
            content_type: uploadResult.content_type
        };

        console.log('📋 File context stored - will be included in next message');
    }

    async handleSendMessage(message, agent) {
        if (!message || !message.trim()) {
            return;
        }

        // Sprint 3 Day 15: Include file context if available (ChatGPT-style)
        const fileContext = this.state.pendingFileContext;
        if (fileContext) {
            console.log('📎 Including file context:', fileContext.filename);
        }

        console.log('📤 Sending message:', {
            message,
            agent,
            streaming: this.state.enableStreaming,
            hasFileContext: !!fileContext
        });

        // Add user message to UI immediately (show file attachment indicator)
        const displayMessage = fileContext
            ? `📎 ${fileContext.filename}\n\n${message}`
            : message;
        this.addUserMessage(displayMessage);

        // Clear file context after including it (one-time use like ChatGPT)
        this.state.pendingFileContext = null;

        // Show loading state
        this.setLoading(true);

        if (this.state.enableStreaming) {
            // Week 5 Day 3: Use streaming for real-time responses
            this.handleStreamingMessage(message, agent, fileContext);
        } else {
            // Use synchronous API
            await this.handleSyncMessage(message, agent, fileContext);
        }
    }

    async handleSyncMessage(message, agent, fileContext = null) {
        try {
            // Send to API (sync) - include file context if available
            const requestParams = {
                message: message,
                agent: agent,
                conversation_id: this.state.currentConversationId
            };

            // Sprint 3 Day 15: Include file context for ChatGPT-style file handling
            if (fileContext) {
                requestParams.file_context = {
                    filename: fileContext.filename,
                    content: fileContext.extracted_text
                };
            }

            const response = await sendChatMessage(requestParams);

            // Add assistant response to UI
            this.addAssistantMessage(response);

            // Update conversation ID if new
            if (response.conversation_id) {
                this.state.currentConversationId = response.conversation_id;
            }

        } catch (error) {
            console.error('❌ Send message failed:', error);
            this.addErrorMessage('Failed to send message. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }

    async handleStreamingMessage(message, agent, fileContext = null) {
        // Ensure conversation exists (create if first message)
        try {
            const conversationId = await ensureConversation(
                this.state.currentConversationId,
                message,
                agent
            );

            // Update state with conversation ID
            if (!this.state.currentConversationId) {
                this.state.currentConversationId = conversationId;
                console.log('📝 Using conversation:', conversationId);
            }
        } catch (error) {
            console.error('❌ Failed to ensure conversation:', error);
            // Continue anyway - user can still chat without persistence
        }

        // Create placeholder message for streaming updates
        const streamingMessageId = `streaming-${Date.now()}`;
        let currentText = '';
        let thinkingSteps = [];

        // Add empty assistant message
        const placeholderMessage = {
            id: streamingMessageId,
            role: 'assistant',
            content: '',
            metadata: {
                agent: agent,
                streaming: true,
                hasFileContext: !!fileContext
            },
            timestamp: new Date().toISOString()
        };

        this.state.messages.push(placeholderMessage);
        this.renderMessage(placeholderMessage);

        // Sprint 3 Day 15: Build request params with optional file context
        const crossSourceEnabled = localStorage.getItem('acms_cross_source_enabled') !== 'false';

        const streamParams = {
            message,
            agent,
            conversationId: this.state.currentConversationId,
            crossSourceEnabled  // Pass cross-source preference to API
        };

        // Include file context for ChatGPT-style file handling
        if (fileContext) {
            streamParams.fileContext = {
                filename: fileContext.filename,
                content: fileContext.extracted_text
            };
            console.log('📎 Streaming with file context:', fileContext.filename);
        }

        console.log('🔀 Cross-source search:', crossSourceEnabled ? 'enabled' : 'disabled');

        // Start streaming
        const abortFn = streamChatMessage(
            streamParams,
            {
                onChunk: (chunk, fullText) => {
                    // Update message content in real-time
                    currentText = fullText;
                    this.updateStreamingMessage(streamingMessageId, fullText, thinkingSteps);
                },

                onStatus: (status) => {
                    // Add thinking step
                    console.log('🤔 Status:', status);
                    if (status.step) {
                        thinkingSteps.push(status);
                        this.updateStreamingMessage(streamingMessageId, currentText, thinkingSteps);
                    }
                },

                onComplete: async (response) => {
                    // Finalize message with metadata
                    console.log('✅ Stream complete:', response);
                    this.finalizeStreamingMessage(streamingMessageId, response, currentText);

                    // No need to save Q&A here - backend now handles persistence when conversation_id is provided
                    console.log('💾 Messages automatically saved to conversation by backend');

                    this.setLoading(false);
                },

                onError: (error) => {
                    console.error('❌ Stream error:', error);
                    this.addErrorMessage('Streaming failed: ' + error.message);
                    this.setLoading(false);
                }
            }
        );

        // Save abort function
        this.state.currentStream = abortFn;
    }

    updateStreamingMessage(messageId, content, thinkingSteps) {
        // Find message in state
        const message = this.state.messages.find(m => m.id === messageId);
        if (!message) return;

        // Update content
        message.content = content;
        if (thinkingSteps.length > 0) {
            message.metadata.thinking_steps = thinkingSteps;
        }

        // Re-render message
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            // Update content only (don't re-render entire message to avoid flicker)
            const contentElement = messageElement.querySelector('.message-content');
            if (contentElement) {
                contentElement.textContent = content;
            }
        }
    }

    finalizeStreamingMessage(messageId, response, streamedText) {
        // Find message in state
        const message = this.state.messages.find(m => m.id === messageId);
        if (!message) return;

        // Update with final metadata
        message.id = response.query_id || messageId;
        message.content = streamedText || response.answer;
        message.metadata = {
            agent: response.agent_used || response.agent || 'auto',
            from_cache: response.from_cache || false,
            cost: response.cost_usd || response.cost,
            confidence: response.confidence ? response.confidence * 100 : null,
            mode: response.cache_status === 'fresh_generation' ? 'enriched' : 'cached',
            thinking_steps: message.metadata.thinking_steps || [],
            latency_ms: response.latency_ms,
            streaming: false, // Mark as completed
            // Cross-source insights (Dec 2025)
            sources: response.sources || [],
            cross_source_citations: response.cross_source_citations || []
        };

        // Re-render complete message with updated ID
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            const newElement = createMessageBubble(message);
            messageElement.replaceWith(newElement);

            // Setup feedback listeners with the real query_id (not the temporary streaming ID)
            setupFeedbackListeners(message.id, (type) => this.handleFeedback(message.id, type));
        }
    }

    addUserMessage(content) {
        const message = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: content,
            timestamp: new Date().toISOString()
        };

        this.state.messages.push(message);
        this.renderMessage(message);
    }

    addAssistantMessage(response) {
        const message = {
            id: response.query_id || response.id || `assistant-${Date.now()}`,
            role: 'assistant',
            content: response.answer || response.response || response.content,
            metadata: {
                agent: response.agent_used || response.agent || 'auto',
                from_cache: response.from_cache || false,
                cost: response.cost_usd || response.cost,
                confidence: response.confidence ? response.confidence * 100 : null,  // Convert 0.9 → 90
                mode: response.cache_status === 'fresh_generation' ? 'enriched' : 'cached',
                thinking_steps: response.thinking_steps || [],
                cache_similarity: response.cache_similarity,
                latency_ms: response.latency_ms,
                // Cross-source insights (Dec 2025)
                sources: response.sources || [],
                cross_source_citations: response.cross_source_citations || []
            },
            timestamp: new Date().toISOString()
        };

        this.state.messages.push(message);
        this.renderMessage(message);

        // Setup feedback listeners for this message
        setupFeedbackListeners(message.id, (type) => this.handleFeedback(message.id, type));
    }

    addErrorMessage(content) {
        const container = document.getElementById('messages-container');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message message-error';
        errorDiv.textContent = content;
        container.appendChild(errorDiv);
        container.scrollTop = container.scrollHeight;
    }

    renderMessage(message) {
        const container = document.getElementById('messages-container');
        const bubble = createMessageBubble(message);
        container.appendChild(bubble);

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    setLoading(loading) {
        this.state.loading = loading;

        const inputArea = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        const inputContainer = document.querySelector('.input-container');

        if (inputArea) inputArea.disabled = loading;

        if (sendBtn) {
            if (loading) {
                // Sprint 3 Day 14: Show stop button during generation
                sendBtn.textContent = '⏹ Stop';
                sendBtn.classList.add('stop-mode');
                sendBtn.disabled = false;  // Enable for stopping
                sendBtn.onclick = () => this.handleStopGeneration();
            } else {
                sendBtn.textContent = 'Send';
                sendBtn.classList.remove('stop-mode');
                sendBtn.disabled = false;
                sendBtn.onclick = null;  // Clear the stop handler
            }
        }

        if (inputContainer) {
            inputContainer.classList.toggle('disabled', loading);
        }
    }

    showError(message) {
        this.state.error = message;
        console.error('❌', message);
        // Could show a toast notification here
    }

    switchView(view, filters = {}) {
        console.log('🔄 Switching view to:', view, filters);
        this.state.currentView = view;

        // Update sidebar active state
        const navLinks = document.querySelectorAll('.sidebar-nav a');
        navLinks.forEach(link => {
            link.classList.toggle('active', link.getAttribute('href') === `#${view}`);
        });

        // Get the main content area
        const chatArea = document.querySelector('.chat-area');
        if (!chatArea) return;

        // Render the appropriate view
        switch (view) {
            case 'chat':
                this.renderChatView(chatArea);
                break;
            case 'gmail':
                renderGmailView(chatArea);
                break;
            case 'financial':
                renderFinancialView(chatArea);
                break;
            case 'memories':
                renderMemoryBrowser(chatArea);
                break;
            case 'knowledge':
                this.renderKnowledgeV2(chatArea);
                break;
            case 'search':
                renderSearchView(chatArea);
                break;
            case 'cognitive':
                this.renderCognitiveView(chatArea);
                break;
            case 'reports':
                this.renderReportsV2(chatArea);
                break;
            case 'constitution':
                this.renderConstitutionV2(chatArea);
                break;
            case 'api-analytics':
                renderAPIAnalyticsView(chatArea);
                break;
            case 'data-flow':
                renderDataFlowView(chatArea);
                break;
            case 'settings':
                this.renderSettingsV2(chatArea);
                break;
            default:
                console.warn('Unknown view:', view);
        }
    }

    renderChatView(container) {
        // Restore chat layout
        container.innerHTML = `
            <div id="chat-header" class="chat-header">
                <h2>Chat</h2>
                <div id="status-indicator" class="status-indicator"></div>
            </div>
            <div id="messages-container" class="messages-container">
                <!-- Messages will be rendered here -->
            </div>
            <div id="input-area" class="input-area">
                <!-- Input area will be rendered by input.js -->
            </div>
        `;

        // Re-setup input area with file upload callback
        setupInputArea(
            (message, agent) => this.handleSendMessage(message, agent),
            (file, uploadResult) => this.handleFileUploaded(file, uploadResult)
        );

        // Update status indicator
        const isConnected = this.state.apiHealth.status === 'connected' || this.state.apiHealth.status === 'healthy';
        this.updateStatusIndicator(isConnected ? 'connected' : 'disconnected');

        // Re-render messages
        const messagesContainer = document.getElementById('messages-container');
        this.state.messages.forEach(msg => {
            const bubble = createMessageBubble(msg);
            messagesContainer.appendChild(bubble);
            if (msg.role === 'assistant') {
                setupFeedbackListeners(msg.id, (type) => this.handleFeedback(msg.id, type));
            }
        });

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // =========================================================================
    // Cognitive Architecture Dashboard (Feb 2026) - Interactive Version
    // =========================================================================

    async renderCognitiveView(container) {
        // Store reference for event handlers
        window.cognitiveView = this;

        container.innerHTML = `
            <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h2>🧬 Cognitive Dashboard</h2>
                    <p class="view-subtitle">Click on topics to explore your knowledge profile and associations</p>
                </div>
                <button onclick="window.cognitiveView.showWeeklyDigest()"
                        style="padding: 10px 20px; background: linear-gradient(135deg, #5A8AD8, #9C27B0); border: none; border-radius: 8px; color: white; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                    📊 Weekly Digest
                </button>
            </div>
            <div id="cognitive-content" style="padding: 24px; overflow-y: auto; height: calc(100% - 100px);">
                <div style="text-align: center; color: #888;">Loading cognitive data...</div>
            </div>
            <div id="cognitive-modal" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 1000; justify-content: center; align-items: center;">
                <div id="cognitive-modal-content" style="background: #1A1721; border-radius: 12px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; padding: 24px; position: relative;">
                </div>
            </div>
        `;

        const content = document.getElementById('cognitive-content');
        const modal = document.getElementById('cognitive-modal');

        // Close modal on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });

        try {
            // Fetch all cognitive data in parallel
            const [expertiseRes, discoveriesRes, healthRes] = await Promise.all([
                fetch('http://localhost:40080/api/expertise'),
                fetch('http://localhost:40080/api/discoveries?limit=10'),
                fetch('http://localhost:40080/api/knowledge-health')
            ]);

            const expertise = await expertiseRes.json();
            const discoveries = await discoveriesRes.json();
            const health = await healthRes.json();

            // Store data for click handlers
            this.cognitiveData = { expertise, discoveries, health };

            // Clear loading message
            content.innerHTML = '';

            // Health overview section
            const healthSection = document.createElement('div');
            healthSection.className = 'analytics-section';
            healthSection.innerHTML = `
                <h3>📊 Knowledge Health</h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 16px;">
                    <div class="stat-card" style="background: #1E1B24; padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 28px; color: #5AA86B; font-weight: 600;">${expertise.total_queries.toLocaleString()}</div>
                        <div style="color: #888; font-size: 12px; margin-top: 4px;">Total Queries</div>
                    </div>
                    <div class="stat-card" style="background: #1E1B24; padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 28px; color: #5A8AD8; font-weight: 600;">${expertise.topic_count}</div>
                        <div style="color: #888; font-size: 12px; margin-top: 4px;">Topics Covered</div>
                    </div>
                    <div class="stat-card" style="background: #1E1B24; padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 28px; color: #E8A838; font-weight: 600;">${health.consistency_score}%</div>
                        <div style="color: #888; font-size: 12px; margin-top: 4px;">Consistency</div>
                    </div>
                    <div class="stat-card" style="background: #1E1B24; padding: 16px; border-radius: 8px; text-align: center; cursor: pointer;" onclick="window.cognitiveView.showAllDiscoveries()">
                        <div style="font-size: 28px; color: #9C27B0; font-weight: 600;">${discoveries.count}</div>
                        <div style="color: #888; font-size: 12px; margin-top: 4px;">Cross-Domain Insights</div>
                    </div>
                </div>
            `;
            content.appendChild(healthSection);

            // Expertise profile section - INTERACTIVE
            const expertiseSection = document.createElement('div');
            expertiseSection.className = 'analytics-section';
            expertiseSection.style.marginTop = '24px';

            const levelColors = {
                'expert': '#E8A838',
                'advanced': '#5AA86B',
                'intermediate': '#5A8AD8',
                'beginner': '#9B93A8',
                'first_encounter': '#6B6578'
            };

            const levelEmojis = {
                'expert': '🏗️',
                'advanced': '🔬',
                'intermediate': '🌿',
                'beginner': '🌱',
                'first_encounter': '👋'
            };

            const barsHtml = expertise.profile.slice(0, 15).map(t => {
                const width = Math.min(t.relative_share * 5, 100);
                const color = levelColors[t.level] || '#6B6578';
                const emoji = levelEmojis[t.level] || '📚';
                return `
                    <div class="topic-bar" style="display: flex; align-items: center; gap: 8px; margin: 8px 0; cursor: pointer; padding: 4px; border-radius: 6px; transition: background 0.2s;"
                         onclick="window.cognitiveView.showTopicDetail('${t.topic}')"
                         onmouseover="this.style.background='#2A2535'"
                         onmouseout="this.style.background='transparent'">
                        <span style="width: 24px; text-align: center;">${emoji}</span>
                        <span style="width: 120px; font-size: 12px; color: #C4BFD0; text-align: right;">${t.topic}</span>
                        <div style="flex: 1; height: 16px; background: #1E1B24; border-radius: 8px; overflow: hidden;">
                            <div style="width: ${width}%; height: 100%; background: ${color}; border-radius: 8px; transition: width 0.5s;"></div>
                        </div>
                        <span style="width: 50px; font-size: 11px; color: #6B6578; text-align: right;">${t.relative_share}%</span>
                        <span style="width: 80px; font-size: 11px; color: ${color}; text-align: left;">${t.level}</span>
                        <span style="color: #6B6578; font-size: 12px;">→</span>
                    </div>
                `;
            }).join('');

            expertiseSection.innerHTML = `
                <h3>🧠 Expertise Profile <span style="font-size: 12px; color: #6B6578; font-weight: normal;">(click to explore)</span></h3>
                <p style="color: #888; font-size: 12px; margin-bottom: 16px;">
                    Your knowledge distribution across ${expertise.topic_count} topics
                </p>
                <div style="margin-top: 16px;">
                    ${barsHtml}
                </div>
                ${expertise.profile.length > 15 ? `<button onclick="window.cognitiveView.showAllTopics()" style="margin-top: 12px; padding: 8px 16px; background: #2A2535; border: none; border-radius: 6px; color: #888; cursor: pointer;">Show all ${expertise.profile.length} topics →</button>` : ''}
            `;
            content.appendChild(expertiseSection);

            // Cross-domain discoveries section - INTERACTIVE
            const discoveriesSection = document.createElement('div');
            discoveriesSection.className = 'analytics-section';
            discoveriesSection.style.marginTop = '24px';

            const discoveriesHtml = discoveries.discoveries.slice(0, 5).map((d, idx) => `
                <div class="discovery-card" style="padding: 16px; margin: 12px 0; background: #1A1E2E; border: 1px solid #2A3548; border-radius: 8px; transition: border-color 0.2s;"
                     onmouseover="this.style.borderColor='#5A8AD8'"
                     onmouseout="this.style.borderColor='#2A3548'">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 14px; font-weight: 600; color: #5A8AD8;">⟐ ${d.bridge}</span>
                        <span style="font-size: 11px; color: #6B6578;">${d.session_count} sessions</span>
                    </div>
                    <div style="font-size: 12px; color: #9B93A8; line-height: 1.5;">${d.insight}</div>
                    <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px;">
                        ${d.topics_involved.slice(0, 6).map(t => `<span class="topic-chip" style="font-size: 10px; padding: 2px 8px; background: #2A3548; border-radius: 12px; color: #7B9BC0; cursor: pointer;" onclick="event.stopPropagation(); window.cognitiveView.showTopicDetail('${t}')">${t}</span>`).join('')}
                    </div>
                    <div style="display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #2A3548;">
                        <button onclick="window.cognitiveView.exploreDiscovery('${d.bridge}')" style="padding: 6px 12px; background: #2A3548; border: none; border-radius: 4px; color: #7B9BC0; cursor: pointer; font-size: 11px;">🔍 Explore Queries</button>
                        <button onclick="window.cognitiveView.rateDiscovery('${d.bridge}', 'useful')" style="padding: 6px 12px; background: #1E3A2F; border: none; border-radius: 4px; color: #5AA86B; cursor: pointer; font-size: 11px;">✓ Useful</button>
                        <button onclick="window.cognitiveView.rateDiscovery('${d.bridge}', 'not_useful')" style="padding: 6px 12px; background: #3A1E1E; border: none; border-radius: 4px; color: #D85A5A; cursor: pointer; font-size: 11px;">✕ Not Useful</button>
                    </div>
                </div>
            `).join('');

            discoveriesSection.innerHTML = `
                <h3>⟐ Cross-Domain Discoveries</h3>
                <p style="color: #888; font-size: 12px; margin-bottom: 16px;">
                    Insights generated by connecting knowledge across different domains
                </p>
                ${discoveriesHtml}
            `;
            content.appendChild(discoveriesSection);

        } catch (error) {
            content.innerHTML = `
                <div style="text-align: center; color: #f44336; padding: 48px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                    <div>Failed to load cognitive data</div>
                    <div style="font-size: 12px; color: #888; margin-top: 8px;">${error.message}</div>
                </div>
            `;
        }
    }

    // Show topic detail modal with associations
    async showTopicDetail(topic) {
        const modal = document.getElementById('cognitive-modal');
        const modalContent = document.getElementById('cognitive-modal-content');

        modal.style.display = 'flex';
        modalContent.innerHTML = `<div style="text-align: center; color: #888;">Loading ${topic}...</div>`;

        try {
            // Fetch topic detail and associations in parallel
            const [topicRes, assocRes] = await Promise.all([
                fetch(`http://localhost:40080/api/topic/${topic}`).catch(() => null),
                fetch(`http://localhost:40080/api/associations/${topic}?limit=10`)
            ]);

            const associations = await assocRes.json();
            let topicData = null;
            if (topicRes && topicRes.ok) {
                topicData = await topicRes.json();
            }

            // Find expertise data
            const expertiseItem = this.cognitiveData?.expertise?.profile?.find(t => t.topic === topic);

            const levelColors = {
                'expert': '#E8A838',
                'advanced': '#5AA86B',
                'intermediate': '#5A8AD8',
                'beginner': '#9B93A8',
                'first_encounter': '#6B6578'
            };

            modalContent.innerHTML = `
                <button onclick="document.getElementById('cognitive-modal').style.display='none'"
                        style="position: absolute; top: 12px; right: 12px; background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>

                <h2 style="color: #E0DCE8; margin-bottom: 8px;">${topic}</h2>

                ${expertiseItem ? `
                <div style="display: flex; gap: 16px; margin-bottom: 24px;">
                    <div style="background: #1E1B24; padding: 12px 20px; border-radius: 8px;">
                        <div style="font-size: 24px; color: ${levelColors[expertiseItem.level]}; font-weight: 600;">${expertiseItem.depth}</div>
                        <div style="color: #888; font-size: 11px;">queries</div>
                    </div>
                    <div style="background: #1E1B24; padding: 12px 20px; border-radius: 8px;">
                        <div style="font-size: 24px; color: ${levelColors[expertiseItem.level]}; font-weight: 600;">${expertiseItem.level}</div>
                        <div style="color: #888; font-size: 11px;">expertise level</div>
                    </div>
                    <div style="background: #1E1B24; padding: 12px 20px; border-radius: 8px;">
                        <div style="font-size: 24px; color: #5A8AD8; font-weight: 600;">${expertiseItem.relative_share}%</div>
                        <div style="color: #888; font-size: 11px;">of your knowledge</div>
                    </div>
                </div>
                ` : ''}

                ${topicData ? `
                <div style="margin-bottom: 24px;">
                    <h3 style="color: #C4BFD0; font-size: 14px; margin-bottom: 12px;">📝 Key Concepts</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                        ${topicData.key_concepts.map(c => `<span style="padding: 4px 12px; background: #2A3548; border-radius: 16px; color: #7B9BC0; font-size: 12px;">${c}</span>`).join('')}
                    </div>
                </div>

                ${topicData.sample_questions?.length ? `
                <div style="margin-bottom: 24px;">
                    <h3 style="color: #C4BFD0; font-size: 14px; margin-bottom: 12px;">💬 Sample Questions You've Asked</h3>
                    <ul style="color: #9B93A8; font-size: 12px; line-height: 1.8; padding-left: 20px;">
                        ${topicData.sample_questions.slice(0, 5).map(q => `<li>${q}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}

                ${topicData.knowledge_gaps?.length ? `
                <div style="margin-bottom: 24px;">
                    <h3 style="color: #C4BFD0; font-size: 14px; margin-bottom: 12px;">🔍 Knowledge Gaps</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                        ${topicData.knowledge_gaps.map(g => `<span style="padding: 4px 12px; background: #3A2E1E; border-radius: 16px; color: #E8A838; font-size: 12px;">${g}</span>`).join('')}
                    </div>
                </div>
                ` : ''}
                ` : ''}

                <div style="margin-bottom: 24px;">
                    <h3 style="color: #C4BFD0; font-size: 14px; margin-bottom: 12px;">🔗 Associated Topics (Co-Retrieved)</h3>
                    ${associations.associations.length ? `
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        ${associations.associations.map(a => `
                            <div class="assoc-item" style="display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: #1E1B24; border-radius: 6px; cursor: pointer;"
                                 onclick="window.cognitiveView.showTopicDetail('${a.topic}')"
                                 onmouseover="this.style.background='#2A2535'"
                                 onmouseout="this.style.background='#1E1B24'">
                                <span style="flex: 1; color: #C4BFD0;">${a.topic}</span>
                                <span style="color: #5AA86B; font-size: 12px;">${(a.strength * 100).toFixed(0)}% strength</span>
                                <span style="color: #6B6578; font-size: 11px;">${a.co_retrieval_count} co-retrievals</span>
                            </div>
                        `).join('')}
                    </div>
                    ` : `<div style="color: #6B6578; font-size: 12px;">No associations found yet. Keep asking questions!</div>`}
                </div>

                <div style="display: flex; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #2A3548;">
                    <button onclick="window.cognitiveView.searchTopic('${topic}')" style="flex: 1; padding: 10px; background: #2A3548; border: none; border-radius: 6px; color: #7B9BC0; cursor: pointer;">🔍 Search queries about ${topic}</button>
                </div>
            `;

        } catch (error) {
            modalContent.innerHTML = `
                <div style="text-align: center; color: #f44336; padding: 24px;">
                    <div>Failed to load topic data</div>
                    <div style="font-size: 12px; color: #888; margin-top: 8px;">${error.message}</div>
                </div>
            `;
        }
    }

    // Show all topics in modal
    showAllTopics() {
        const modal = document.getElementById('cognitive-modal');
        const modalContent = document.getElementById('cognitive-modal-content');
        const expertise = this.cognitiveData?.expertise;

        if (!expertise) return;

        modal.style.display = 'flex';

        const levelColors = {
            'expert': '#E8A838',
            'advanced': '#5AA86B',
            'intermediate': '#5A8AD8',
            'beginner': '#9B93A8',
            'first_encounter': '#6B6578'
        };

        modalContent.innerHTML = `
            <button onclick="document.getElementById('cognitive-modal').style.display='none'"
                    style="position: absolute; top: 12px; right: 12px; background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>

            <h2 style="color: #E0DCE8; margin-bottom: 16px;">All ${expertise.profile.length} Topics</h2>

            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                ${expertise.profile.map(t => `
                    <span class="topic-chip" style="padding: 6px 12px; background: ${levelColors[t.level]}22; border: 1px solid ${levelColors[t.level]}44; border-radius: 16px; color: ${levelColors[t.level]}; font-size: 12px; cursor: pointer;"
                          onclick="window.cognitiveView.showTopicDetail('${t.topic}')">
                        ${t.topic} (${t.depth})
                    </span>
                `).join('')}
            </div>
        `;
    }

    // Show all discoveries
    showAllDiscoveries() {
        const discoveries = this.cognitiveData?.discoveries;
        if (!discoveries) return;

        const modal = document.getElementById('cognitive-modal');
        const modalContent = document.getElementById('cognitive-modal-content');

        modal.style.display = 'flex';

        modalContent.innerHTML = `
            <button onclick="document.getElementById('cognitive-modal').style.display='none'"
                    style="position: absolute; top: 12px; right: 12px; background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>

            <h2 style="color: #E0DCE8; margin-bottom: 16px;">All ${discoveries.count} Cross-Domain Discoveries</h2>

            ${discoveries.discoveries.map(d => `
                <div style="padding: 12px; margin: 8px 0; background: #1A1E2E; border-radius: 8px;">
                    <div style="font-weight: 600; color: #5A8AD8; margin-bottom: 4px;">⟐ ${d.bridge}</div>
                    <div style="font-size: 12px; color: #9B93A8;">${d.insight}</div>
                    <div style="font-size: 11px; color: #6B6578; margin-top: 4px;">${d.session_count} sessions</div>
                </div>
            `).join('')}
        `;
    }

    // Explore discovery - show related queries
    async exploreDiscovery(bridge) {
        const modal = document.getElementById('cognitive-modal');
        const modalContent = document.getElementById('cognitive-modal-content');

        modal.style.display = 'flex';
        modalContent.innerHTML = `<div style="text-align: center; color: #888;">Loading queries for ${bridge}...</div>`;

        // Find the discovery data
        const discovery = this.cognitiveData?.discoveries?.discoveries?.find(d => d.bridge === bridge);

        if (!discovery) {
            modalContent.innerHTML = `<div style="color: #f44336;">Discovery not found</div>`;
            return;
        }

        modalContent.innerHTML = `
            <button onclick="document.getElementById('cognitive-modal').style.display='none'"
                    style="position: absolute; top: 12px; right: 12px; background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>

            <h2 style="color: #E0DCE8; margin-bottom: 8px;">⟐ ${bridge}</h2>
            <p style="color: #9B93A8; font-size: 13px; margin-bottom: 16px;">${discovery.insight}</p>

            <div style="background: #1E1B24; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                <div style="font-size: 12px; color: #888; margin-bottom: 8px;">This insight emerged from ${discovery.session_count} sessions where you explored topics from both domains:</div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${discovery.topics_involved.map(t => `
                        <span class="topic-chip" style="padding: 4px 10px; background: #2A3548; border-radius: 12px; color: #7B9BC0; font-size: 11px; cursor: pointer;"
                              onclick="window.cognitiveView.showTopicDetail('${t}')">${t}</span>
                    `).join('')}
                </div>
            </div>

            <div style="padding: 16px; background: #1A2E1E; border-radius: 8px; border-left: 3px solid #5AA86B;">
                <div style="font-size: 12px; color: #5AA86B; font-weight: 600; margin-bottom: 8px;">💡 What this means</div>
                <div style="font-size: 13px; color: #9B93A8; line-height: 1.6;">
                    Your questions naturally bridge these domains, suggesting you think about problems holistically.
                    This cross-domain thinking is a cognitive strength - it enables creative problem-solving that specialists might miss.
                </div>
            </div>
        `;
    }

    // Rate discovery as useful/not useful
    async rateDiscovery(bridge, rating) {
        console.log(`Rating discovery "${bridge}" as ${rating}`);

        // Visual feedback
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✓ Saved';
        btn.style.background = '#2A3548';

        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);

        // TODO: Save to backend when we add the endpoint
        // await fetch(`http://localhost:40080/api/discoveries/rate`, {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify({ bridge, rating })
        // });
    }

    // Search for topic in chat
    searchTopic(topic) {
        document.getElementById('cognitive-modal').style.display = 'none';
        this.switchView('search');
        // Pre-fill search with topic
        setTimeout(() => {
            const searchInput = document.querySelector('#search-input');
            if (searchInput) {
                searchInput.value = topic;
                searchInput.dispatchEvent(new Event('input'));
            }
        }, 100);
    }

    // Show Weekly Digest with LLM-generated insights
    async showWeeklyDigest() {
        const modal = document.getElementById('cognitive-modal');
        const modalContent = document.getElementById('cognitive-modal-content');

        modal.style.display = 'flex';
        modalContent.innerHTML = `
            <div style="text-align: center; padding: 48px;">
                <div style="font-size: 32px; margin-bottom: 16px;">📊</div>
                <div style="color: #888;">Generating your weekly digest...</div>
                <div style="color: #6B6578; font-size: 12px; margin-top: 8px;">Analyzing your learning patterns</div>
            </div>
        `;

        try {
            const response = await fetch('http://localhost:40080/api/digest/weekly');
            const digest = await response.json();

            const levelColors = {
                'expert': '#E8A838',
                'advanced': '#5AA86B',
                'intermediate': '#5A8AD8',
                'beginner': '#9B93A8',
                'first_encounter': '#6B6578'
            };

            // Format dates
            const startDate = new Date(digest.period_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            const endDate = new Date(digest.period_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

            modalContent.innerHTML = `
                <button onclick="document.getElementById('cognitive-modal').style.display='none'"
                        style="position: absolute; top: 12px; right: 12px; background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>

                <div style="text-align: center; margin-bottom: 24px;">
                    <h2 style="color: #E0DCE8; margin-bottom: 4px;">📊 Weekly Digest</h2>
                    <div style="color: #6B6578; font-size: 12px;">${startDate} - ${endDate}</div>
                </div>

                <!-- Stats Overview -->
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px;">
                    <div style="background: #1E1B24; padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 28px; color: #5AA86B; font-weight: 600;">${digest.stats.interactions}</div>
                        <div style="color: #888; font-size: 11px;">Interactions</div>
                    </div>
                    <div style="background: #1E1B24; padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 28px; color: #5A8AD8; font-weight: 600;">${digest.stats.topics_active}</div>
                        <div style="color: #888; font-size: 11px;">Active Topics</div>
                    </div>
                    <div style="background: #1E1B24; padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 28px; color: #9C27B0; font-weight: 600;">${digest.stats.new_topics.length}</div>
                        <div style="color: #888; font-size: 11px;">New Topics</div>
                    </div>
                </div>

                ${digest.stats.new_topics.length > 0 ? `
                <!-- New Topics This Week -->
                <div style="margin-bottom: 24px;">
                    <h3 style="color: #C4BFD0; font-size: 14px; margin-bottom: 12px;">🆕 New Topics This Week</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                        ${digest.stats.new_topics.map(t => `
                            <span style="padding: 6px 12px; background: #2E1E3A; border: 1px solid #9C27B044; border-radius: 16px; color: #9C27B0; font-size: 12px; cursor: pointer;"
                                  onclick="window.cognitiveView.showTopicDetail('${t}')">${t}</span>
                        `).join('')}
                    </div>
                </div>
                ` : ''}

                <!-- Top Topics This Week -->
                <div style="margin-bottom: 24px;">
                    <h3 style="color: #C4BFD0; font-size: 14px; margin-bottom: 12px;">🔥 Most Active Topics</h3>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        ${digest.top_topics.slice(0, 5).map(t => `
                            <div style="display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: #1E1B24; border-radius: 6px; cursor: pointer;"
                                 onclick="window.cognitiveView.showTopicDetail('${t.topic}')">
                                <span style="flex: 1; color: #C4BFD0;">${t.topic}</span>
                                <span style="color: ${levelColors[t.level]}; font-size: 12px;">${t.level}</span>
                                <span style="color: #6B6578; font-size: 11px;">${t.depth} queries</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                ${digest.discoveries.length > 0 ? `
                <!-- Cross-Domain Discoveries -->
                <div style="margin-bottom: 24px;">
                    <h3 style="color: #C4BFD0; font-size: 14px; margin-bottom: 12px;">⟐ Cross-Domain Insights</h3>
                    ${digest.discoveries.slice(0, 3).map(d => `
                        <div style="padding: 12px; margin: 8px 0; background: #1A1E2E; border-radius: 8px; border-left: 3px solid #5A8AD8;">
                            <div style="font-weight: 600; color: #5A8AD8; margin-bottom: 4px;">${d.bridge}</div>
                            <div style="font-size: 12px; color: #9B93A8;">${d.insight}</div>
                        </div>
                    `).join('')}
                </div>
                ` : ''}

                <!-- Knowledge Health -->
                <div style="padding: 16px; background: #1E2E1E; border-radius: 8px; border-left: 3px solid #5AA86B;">
                    <h3 style="color: #5AA86B; font-size: 14px; margin-bottom: 12px;">📈 Knowledge Health</h3>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                        <div>
                            <div style="font-size: 18px; color: #E0DCE8; font-weight: 600;">${digest.health.total_entries.toLocaleString()}</div>
                            <div style="color: #888; font-size: 11px;">Total Knowledge Entries</div>
                        </div>
                        <div>
                            <div style="font-size: 18px; color: #E0DCE8; font-weight: 600;">${digest.health.topics_covered}</div>
                            <div style="color: #888; font-size: 11px;">Topics Covered</div>
                        </div>
                        <div>
                            <div style="font-size: 18px; color: #E0DCE8; font-weight: 600;">${digest.health.consistency_score}%</div>
                            <div style="color: #888; font-size: 11px;">Consistency Score</div>
                        </div>
                        <div>
                            <div style="font-size: 18px; color: ${digest.health.needs_review > 0 ? '#E8A838' : '#5AA86B'}; font-weight: 600;">${digest.health.needs_review}</div>
                            <div style="color: #888; font-size: 11px;">Needs Review</div>
                        </div>
                    </div>
                </div>

                <!-- LLM Insight (synthesized) -->
                <div style="margin-top: 24px; padding: 20px; background: linear-gradient(135deg, #1A1E2E, #2A1E3A); border-radius: 12px; border: 1px solid #5A8AD844;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                        <span style="font-size: 20px;">💡</span>
                        <h3 style="color: #E0DCE8; font-size: 14px; margin: 0;">This Week's Insight</h3>
                    </div>
                    <div style="font-size: 13px; color: #C4BFD0; line-height: 1.7;">
                        ${this.generateWeeklyInsight(digest)}
                    </div>
                </div>
            `;

        } catch (error) {
            modalContent.innerHTML = `
                <div style="text-align: center; color: #f44336; padding: 48px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                    <div>Failed to load weekly digest</div>
                    <div style="font-size: 12px; color: #888; margin-top: 8px;">${error.message}</div>
                </div>
            `;
        }
    }

    // Generate synthesized insight from digest data
    generateWeeklyInsight(digest) {
        const insights = [];

        // Activity insight
        if (digest.stats.interactions > 50) {
            insights.push(`You had an active week with ${digest.stats.interactions} interactions across ${digest.stats.topics_active} topics.`);
        } else if (digest.stats.interactions > 20) {
            insights.push(`Moderate activity this week with ${digest.stats.interactions} interactions.`);
        } else {
            insights.push(`Light usage this week. Consider checking in more regularly to build your knowledge base.`);
        }

        // New topics insight
        if (digest.stats.new_topics.length > 0) {
            insights.push(`You explored ${digest.stats.new_topics.length} new topic${digest.stats.new_topics.length > 1 ? 's' : ''}: <strong>${digest.stats.new_topics.slice(0, 3).join(', ')}</strong>.`);
        }

        // Top topic insight
        if (digest.top_topics.length > 0) {
            const top = digest.top_topics[0];
            insights.push(`Your primary focus was <strong>${top.topic}</strong> (${top.depth} queries) - you're at ${top.level} level in this area.`);
        }

        // Cross-domain insight
        if (digest.discoveries.length > 0) {
            insights.push(`Your thinking bridges multiple domains - the <strong>${digest.discoveries[0].bridge}</strong> connection is particularly notable.`);
        }

        // Health insight
        if (digest.health.needs_review > 5) {
            insights.push(`<span style="color: #E8A838;">Note: ${digest.health.needs_review} items need review in your knowledge base.</span>`);
        }

        return insights.join(' ');
    }

    // =========================================================================
    // Sprint 3-6: New v2 Component Renders (for comparison with existing views)
    // =========================================================================

    renderKnowledgeV2(container) {
        container.innerHTML = '';
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'height: 100%; overflow-y: auto;';
        container.appendChild(wrapper);

        const knowledgeBrowser = new KnowledgeBrowser(wrapper);
        knowledgeBrowser.init();
        window.knowledgeBrowser = knowledgeBrowser;  // Component uses this name for onclick handlers
        console.log('📚 Knowledge v2 component loaded');
    }

    renderReportsV2(container) {
        container.innerHTML = '';
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'height: 100%; overflow-y: auto;';
        container.appendChild(wrapper);

        const reportsDashboard = new ReportsDashboard(wrapper);
        reportsDashboard.init();
        window.reportsDashboard = reportsDashboard;  // Component uses this name for onclick handlers
        console.log('📋 Reports v2 component loaded');
    }

    renderConstitutionV2(container) {
        container.innerHTML = '';
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'height: 100%; overflow-y: auto;';
        container.appendChild(wrapper);

        const portfolioConstitution = new PortfolioConstitution(wrapper);
        portfolioConstitution.init();
        window.portfolioConstitution = portfolioConstitution;
        console.log('📊 Constitution v2 component loaded');
    }

    renderSettingsV2(container) {
        container.innerHTML = '';
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'height: 100%; overflow-y: auto;';
        container.appendChild(wrapper);

        const settings = new Settings(wrapper);
        settings.init();
        window.settingsView = settings;
        console.log('⚙️ Settings v2 component loaded');
    }

    async handleConversationLoad(conversationId) {
        // If null, create new conversation
        if (!conversationId) {
            this.createNewChat();
            return;
        }

        console.log('📖 Loading conversation:', conversationId);

        try {
            // Load conversation from API
            const data = await getConversation(conversationId);

            // Extract conversation and messages from API response
            // API returns: {conversation: {...}, messages: [...]}
            const conversation = data.conversation || data;
            const messages = data.messages || conversation.messages || [];

            // Clear current messages
            this.state.messages = [];
            const container = document.getElementById('messages-container');
            container.innerHTML = '';

            // Update state
            this.state.currentConversationId = conversationId;

            // Render conversation messages
            if (messages && messages.length > 0) {
                messages.forEach(msg => {
                    // Convert API message format to UI format
                    const uiMessage = {
                        id: msg.id,
                        role: msg.role,
                        content: msg.content,
                        metadata: msg.metadata || {},
                        timestamp: msg.created_at
                    };

                    this.state.messages.push(uiMessage);
                    this.renderMessage(uiMessage);

                    // Setup feedback listeners for assistant messages
                    if (msg.role === 'assistant') {
                        setupFeedbackListeners(msg.id, (type) => this.handleFeedback(msg.id, type));
                    }
                });
            }

            // Update chat header
            const header = document.querySelector('#chat-header h2');
            if (header) {
                header.textContent = conversation.title || 'Chat';
            }

            console.log(`✅ Loaded conversation with ${messages.length} messages`);

        } catch (error) {
            console.error('❌ Failed to load conversation:', error);
            this.addErrorMessage('Failed to load conversation');
        }
    }

    async createNewChat() {
        console.log('➕ Creating new chat');

        // Save the current conversation ID before clearing
        const previousConversationId = this.state.currentConversationId;

        // Clear current chat state
        this.state.currentConversationId = null;
        this.state.messages = [];

        // Clear messages UI
        const container = document.getElementById('messages-container');
        container.innerHTML = '';

        // Reset chat header
        const header = document.querySelector('#chat-header h2');
        if (header) {
            header.textContent = 'Chat';
        }

        // Refresh sidebar to show the previous conversation if it exists
        if (previousConversationId) {
            console.log('🔄 Refreshing conversation list to show previous chat');
            try {
                const conversations = await loadConversations();
                this.state.conversations = conversations;

                // Update sidebar with refreshed list
                setupSidebar(
                    this.state,
                    (view) => this.switchView(view),
                    (conversationId) => this.handleConversationLoad(conversationId)
                );
            } catch (error) {
                console.error('❌ Failed to refresh conversations:', error);
            }
        }

        // Focus input
        focusInput();
    }

    async handleFeedback(messageId, type) {
        console.log('👍 Feedback:', { messageId, type });

        // Check if message has a valid query_id
        if (!messageId || messageId === 'null' || messageId.startsWith('streaming-') || messageId.startsWith('stream-')) {
            console.warn('⚠️  Cannot submit feedback - no valid query_id for this message');
            alert('Feedback not available for this message (no query ID from server)');
            return;
        }

        // Active Second Brain (Jan 2026): Use feedback modal for positive feedback
        if (type === 'upvote') {
            // Show modal asking if they want to save as verified
            showFeedbackModal(messageId, 'positive');
            return;
        }

        if (type === 'downvote') {
            // Show modal with reason selection
            showFeedbackModal(messageId, 'negative');
            return;
        }

        // Fallback for other feedback types
        try {
            const feedbackMap = {
                'upvote': { type: 'thumbs_up', rating: 5 },
                'downvote': { type: 'thumbs_down', rating: 1 }
            };

            const feedback = feedbackMap[type];
            if (!feedback) {
                console.error('❌ Invalid feedback type:', type);
                return;
            }

            const response = await fetch('http://localhost:40080/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query_id: messageId,
                    rating: feedback.rating,
                    feedback_type: feedback.type
                })
            });

            if (response.ok) {
                console.log('✅ Feedback recorded');
            } else {
                const error = await response.text();
                console.error('❌ Feedback failed:', response.status, error);
            }
        } catch (error) {
            console.error('❌ Feedback failed:', error);
        }
    }
}

// Export for use in renderer
module.exports = { AcmsApp };
