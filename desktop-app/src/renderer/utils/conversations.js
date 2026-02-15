/**
 * Conversation Management Utilities
 *
 * Week 5 Day 3 Task 2: Conversation History
 *
 * Features:
 * - List conversations with grouping (Today, Yesterday, Last 7 Days, Older)
 * - Load conversation messages
 * - Create new conversations
 * - Update conversation metadata
 */

const API_BASE_URL = 'http://localhost:40080';
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'; // Default MCP user UUID

/**
 * List user's conversations
 *
 * @param {Object} options - Query options
 * @param {number} options.limit - Max conversations to return
 * @param {number} options.offset - Skip N conversations
 * @param {boolean} options.groupByDate - Group by date
 * @returns {Promise<Object>} Response with conversations array
 */
async function listConversations(options = {}) {
    const {
        limit = 20,
        offset = 0,
        groupByDate = true
    } = options;

    const queryParams = new URLSearchParams({
        user_id: DEFAULT_USER_ID,
        limit: limit.toString(),
        offset: offset.toString(),
        group_by_date: groupByDate.toString()
    });

    try {
        const response = await fetch(`${API_BASE_URL}/chat/conversations?${queryParams}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('📚 Conversations loaded:', data);

        return data;

    } catch (error) {
        console.error('❌ Failed to load conversations:', error);
        // Return empty structure on error
        return {
            conversations: [],
            total: 0,
            groups: null
        };
    }
}

/**
 * Get specific conversation with all messages
 *
 * @param {string} conversationId - Conversation UUID
 * @returns {Promise<Object>} Conversation with messages array
 */
async function getConversation(conversationId) {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/conversations/${conversationId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const conversation = await response.json();
        console.log('📖 Conversation loaded:', conversation);

        return conversation;

    } catch (error) {
        console.error('❌ Failed to load conversation:', error);
        throw error;
    }
}

/**
 * Create new conversation
 *
 * @param {Object} params - Conversation params
 * @param {string} params.agent - Agent to use (claude_sonnet, chatgpt, gemini)
 * @param {string} params.title - Optional title
 * @returns {Promise<Object>} Created conversation
 */
async function createConversation(params = {}) {
    const {
        agent = 'claude_sonnet',
        title = null
    } = params;

    // Map agent names to backend format
    const agentMap = {
        'claude_sonnet': 'claude',
        'chatgpt': 'gpt',
        'gemini': 'gemini',
        'claude_code': 'claude-code',
        'ollama': 'ollama'
    };

    const mappedAgent = agentMap[agent] || 'claude'; // Default to claude

    try {
        const response = await fetch(`${API_BASE_URL}/chat/conversations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: DEFAULT_USER_ID,
                agent: mappedAgent,  // Use mapped agent name
                title: title
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const conversation = await response.json();
        console.log('➕ Conversation created:', conversation);

        return conversation;

    } catch (error) {
        console.error('❌ Failed to create conversation:', error);
        throw error;
    }
}

/**
 * Update conversation metadata
 *
 * @param {string} conversationId - Conversation UUID
 * @param {Object} updates - Fields to update
 * @param {string} updates.title - New title
 * @returns {Promise<Object>} Updated conversation
 */
async function updateConversation(conversationId, updates) {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/conversations/${conversationId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const conversation = await response.json();
        console.log('✏️  Conversation updated:', conversation);

        return conversation;

    } catch (error) {
        console.error('❌ Failed to update conversation:', error);
        throw error;
    }
}

/**
 * Delete conversation
 *
 * @param {string} conversationId - Conversation UUID
 * @returns {Promise<void>}
 */
async function deleteConversation(conversationId) {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/conversations/${conversationId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        console.log('🗑️  Conversation deleted:', conversationId);

    } catch (error) {
        console.error('❌ Failed to delete conversation:', error);
        throw error;
    }
}

/**
 * Group conversations by time period
 *
 * @param {Array} conversations - Array of conversation objects
 * @returns {Object} Grouped conversations {today, yesterday, last7days, older}
 */
function groupConversationsByTime(conversations) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const last7days = new Date(today);
    last7days.setDate(last7days.getDate() - 7);

    const grouped = {
        today: [],
        yesterday: [],
        last7days: [],
        older: []
    };

    for (const conv of conversations) {
        const date = new Date(conv.updated_at || conv.created_at);

        if (date >= today) {
            grouped.today.push(conv);
        } else if (date >= yesterday) {
            grouped.yesterday.push(conv);
        } else if (date >= last7days) {
            grouped.last7days.push(conv);
        } else {
            grouped.older.push(conv);
        }
    }

    return grouped;
}

/**
 * Generate conversation title from first message
 *
 * @param {string} firstMessage - First user message
 * @returns {string} Generated title (max 50 chars)
 */
function generateConversationTitle(firstMessage) {
    if (!firstMessage || !firstMessage.trim()) {
        return 'New Conversation';
    }

    // Take first 50 chars, truncate at word boundary
    let title = firstMessage.substring(0, 50).trim();

    if (firstMessage.length > 50) {
        const lastSpace = title.lastIndexOf(' ');
        if (lastSpace > 0) {
            title = title.substring(0, lastSpace);
        }
        title += '...';
    }

    return title;
}

// Export functions
module.exports = {
    listConversations,
    getConversation,
    createConversation,
    updateConversation,
    deleteConversation,
    groupConversationsByTime,
    generateConversationTitle
};
