/**
 * Sidebar Component
 *
 * Week 5 Day 2-3: Navigation and Conversation List
 *
 * Features:
 * - App header with logo
 * - New chat button
 * - Navigation (Chat, Search, Analytics, Settings)
 * - Conversation list with time grouping (Today, Yesterday, etc.)
 * - Real conversation loading from API
 */

const { listConversations, getConversation, createConversation } = require('../utils/conversations.js');

/**
 * Setup sidebar with navigation and conversation list
 *
 * @param {Object} state - App state
 * @param {Function} onViewChange - Callback(view) when view changes
 */
async function setupSidebar(state, onViewChange, onConversationLoad) {
    const sidebar = document.getElementById('sidebar');
    sidebar.innerHTML = ''; // Clear existing content

    // Sidebar header
    const header = document.createElement('div');
    header.className = 'sidebar-header';

    const logo = document.createElement('h1');
    logo.textContent = 'ACMS';
    logo.className = 'sidebar-logo';
    header.appendChild(logo);

    const newChatBtn = document.createElement('button');
    newChatBtn.id = 'new-chat-btn';
    newChatBtn.className = 'new-chat-btn';
    newChatBtn.textContent = '+ New Chat';
    newChatBtn.title = 'Start a new conversation (Cmd/Ctrl+N)';
    newChatBtn.addEventListener('click', () => {
        if (onConversationLoad) {
            onConversationLoad(null); // null = new conversation
        }
    });
    header.appendChild(newChatBtn);

    sidebar.appendChild(header);

    // Navigation
    const nav = document.createElement('nav');
    nav.className = 'sidebar-nav';

    const navItems = [
        { id: 'chat', label: 'Chat', icon: '💬' },
        { id: 'gmail', label: 'Email', icon: '📧' },
        { id: 'financial', label: 'Financial', icon: '💰' },
        { id: 'memories', label: 'Memories', icon: '🧠' },
        { id: 'knowledge', label: 'Knowledge', icon: '📚' },
        { id: 'search', label: 'Search', icon: '🔍' },
        { id: 'cognitive', label: 'Cognitive', icon: '🧬' },
        { id: 'reports', label: 'Reports', icon: '📋' },
        { id: 'constitution', label: 'Constitution', icon: '📜' },
        { id: 'api-analytics', label: 'API Analytics', icon: '📈' },
        { id: 'data-flow', label: 'Data Flow', icon: '🔄' },
        { id: 'settings', label: 'Settings', icon: '⚙️' }
    ];

    navItems.forEach(item => {
        const link = document.createElement('a');
        link.href = `#${item.id}`;
        link.className = state.currentView === item.id ? 'active' : '';
        link.innerHTML = ''; // Safe: we'll add text content separately

        const icon = document.createElement('span');
        icon.className = 'nav-icon';
        icon.textContent = item.icon;
        link.appendChild(icon);

        const label = document.createElement('span');
        label.textContent = item.label;
        link.appendChild(label);

        link.addEventListener('click', (e) => {
            e.preventDefault();
            onViewChange(item.id);
        });

        nav.appendChild(link);
    });

    sidebar.appendChild(nav);

    // Conversation list section
    const conversationsSection = document.createElement('div');
    conversationsSection.className = 'conversations-section';

    const conversationsHeader = document.createElement('h3');
    conversationsHeader.textContent = 'Recent Conversations';
    conversationsHeader.className = 'conversations-header';
    conversationsSection.appendChild(conversationsHeader);

    const conversationsList = document.createElement('div');
    conversationsList.id = 'conversation-list';
    conversationsList.className = 'conversation-list';

    conversationsSection.appendChild(conversationsList);
    sidebar.appendChild(conversationsSection);

    // Load conversations from API
    await loadConversationList(conversationsList, onConversationLoad);

    console.log('📑 Sidebar initialized');
}

/**
 * Load and render conversation list from API
 *
 * @param {HTMLElement} container - Container element
 * @param {Function} onConversationLoad - Callback(conversationId) when clicked
 */
async function loadConversationList(container, onConversationLoad) {
    // Show loading state
    container.innerHTML = '<div class="loading">Loading conversations...</div>';

    try {
        // Load conversations from API
        const data = await listConversations({
            limit: 50,
            offset: 0,
            groupByDate: true
        });

        // Clear loading
        container.innerHTML = '';

        if (!data.conversations || data.conversations.length === 0) {
            // Show empty state
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-state';
            emptyState.textContent = 'No conversations yet. Start chatting!';
            container.appendChild(emptyState);
            return;
        }

        // Always group manually from conversations array
        // (API's group format doesn't match our rendering expectations)
        const { groupConversationsByTime } = require('../utils/conversations.js');
        const grouped = groupConversationsByTime(data.conversations);
        renderGroupedConversations(container, grouped, onConversationLoad);

    } catch (error) {
        console.error('❌ Failed to load conversations:', error);

        // Show error state
        container.innerHTML = '';
        const errorState = document.createElement('div');
        errorState.className = 'empty-state error';
        errorState.textContent = 'Failed to load conversations';
        container.appendChild(errorState);
    }
}

/**
 * Render grouped conversations
 *
 * @param {HTMLElement} container - Container element
 * @param {Object} groups - Grouped conversations
 * @param {Function} onConversationLoad - Click callback
 */
function renderGroupedConversations(container, groups, onConversationLoad) {
    const groupTitles = {
        today: 'Today',
        yesterday: 'Yesterday',
        last7days: 'Last 7 Days',
        older: 'Older'
    };

    for (const [key, title] of Object.entries(groupTitles)) {
        const conversations = groups[key];
        if (!conversations || conversations.length === 0) continue;

        // Group header
        const groupHeader = document.createElement('div');
        groupHeader.className = 'conversation-group-header';
        groupHeader.textContent = title;
        container.appendChild(groupHeader);

        // Conversations in group
        conversations.forEach(conv => {
            const item = createConversationItem(conv, onConversationLoad);
            container.appendChild(item);
        });
    }
}

/**
 * Create conversation list item
 *
 * @param {Object} conversation - Conversation object
 * @param {Function} onConversationLoad - Click callback
 * @returns {HTMLElement} Conversation item element
 */
function createConversationItem(conversation, onConversationLoad) {
    const item = document.createElement('div');
    item.className = 'conversation-item';
    item.setAttribute('data-conversation-id', conversation.id);

    const title = document.createElement('div');
    title.className = 'conversation-title';
    title.textContent = conversation.title || 'Untitled Conversation';
    item.appendChild(title);

    const meta = document.createElement('div');
    meta.className = 'conversation-meta';

    const messageCount = document.createElement('span');
    messageCount.textContent = `${conversation.message_count || 0} messages`;
    meta.appendChild(messageCount);

    const timestamp = document.createElement('span');
    timestamp.textContent = formatRelativeTime(conversation.updated_at || conversation.created_at);
    meta.appendChild(timestamp);

    item.appendChild(meta);

    // Click handler
    item.addEventListener('click', () => {
        if (onConversationLoad) {
            // API returns conversation_id, not id
            onConversationLoad(conversation.conversation_id || conversation.id);
        }
    });

    return item;
}

/**
 * Format relative time
 *
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted time
 */
function formatRelativeTime(timestamp) {
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

// Export functions
module.exports = {
    setupSidebar,
    loadConversationList,
    createConversationItem,
    formatRelativeTime
};
