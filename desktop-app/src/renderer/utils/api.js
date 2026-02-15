/**
 * API Utilities
 *
 * Week 5 Day 2: Centralized API communication
 *
 * Features:
 * - Health check
 * - Chat message sending
 * - Conversation management
 * - Error handling
 * - Request/response logging
 */

const API_BASE_URL = 'http://localhost:40080';
const TIMEOUT_MS = 30000; // 30 seconds

/**
 * Make API request with timeout and error handling
 *
 * @param {string} endpoint - API endpoint (e.g., '/chat')
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Response data
 */
async function makeRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    console.log(`🌐 API Request: ${options.method || 'GET'} ${endpoint}`);

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API Error ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        console.log(`✅ API Response: ${endpoint}`, data);

        return data;

    } catch (error) {
        if (error.name === 'AbortError') {
            console.error(`⏱️ API Timeout: ${endpoint}`);
            throw new Error('Request timed out. Please try again.');
        }

        console.error(`❌ API Error: ${endpoint}`, error);
        throw error;
    }
}

/**
 * Check API health status
 *
 * @returns {Promise<Object>} Health status { status: 'connected'|'disconnected' }
 */
async function checkHealth() {
    try {
        const data = await makeRequest('/health', {
            method: 'GET'
        });

        return {
            status: data.status === 'healthy' ? 'connected' : 'disconnected',
            ...data
        };
    } catch (error) {
        return {
            status: 'disconnected',
            error: error.message
        };
    }
}

/**
 * Send chat message
 *
 * @param {Object} params - Message parameters
 * @param {string} params.message - User message
 * @param {string} params.agent - Agent to use ('auto', 'claude', 'gpt', 'gemini')
 * @param {string} params.conversation_id - Conversation ID (optional)
 * @returns {Promise<Object>} Response with { response, agent, metadata, ... }
 */
async function sendChatMessage(params) {
    // Map UI agent names to API agent names
    const agentMap = {
        'auto': null,  // null = auto-routing
        'claude': 'claude_sonnet',
        'gpt': 'chatgpt',
        'gemini': 'gemini',
        'ollama': 'ollama'
    };

    const manualAgent = agentMap[params.agent] || null;

    return await makeRequest('/gateway/ask-sync', {
        method: 'POST',
        body: JSON.stringify({
            query: params.message,
            manual_agent: manualAgent,
            bypass_cache: false,
            context_limit: 5
        })
    });
}

/**
 * Load conversations list
 *
 * @param {number} limit - Max conversations to return
 * @returns {Promise<Array>} Array of conversation objects
 */
async function loadConversations(limit = 50) {
    try {
        // Note: Conversations feature coming in Week 5 Day 3
        // For now, return empty array
        console.log('📋 Conversations list: Coming in Day 3');
        return [];
    } catch (error) {
        console.error('Failed to load conversations:', error);
        return [];
    }
}

/**
 * Load specific conversation with messages
 *
 * @param {string} conversationId - Conversation ID
 * @returns {Promise<Object>} Conversation object with messages array
 */
async function loadConversation(conversationId) {
    return await makeRequest(`/conversations/${conversationId}`, {
        method: 'GET'
    });
}

/**
 * Submit feedback for a message
 *
 * @param {string} messageId - Message ID
 * @param {string} feedbackType - 'upvote' or 'downvote'
 * @returns {Promise<Object>} Response
 */
async function submitFeedback(messageId, feedbackType) {
    return await makeRequest('/feedback', {
        method: 'POST',
        body: JSON.stringify({
            message_id: messageId,
            feedback_type: feedbackType,
            timestamp: new Date().toISOString()
        })
    });
}

/**
 * Search memories
 *
 * @param {string} query - Search query
 * @param {Object} options - Search options
 * @returns {Promise<Object>} Search results
 */
async function searchMemories(query, options = {}) {
    return await makeRequest('/memories/search', {
        method: 'POST',
        body: JSON.stringify({
            query: query,
            limit: options.limit || 10,
            include_confidential: options.include_confidential !== false
        })
    });
}

// Export functions
module.exports = {
    checkHealth,
    sendChatMessage,
    loadConversations,
    loadConversation,
    submitFeedback,
    searchMemories
};
