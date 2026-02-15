/**
 * Message Persistence Utilities
 *
 * Handles saving messages to conversation history in the database.
 * Ensures conversations persist when users click "New Chat".
 */

const { createConversation, generateConversationTitle } = require('./conversations');

const API_BASE_URL = 'http://localhost:40080';
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001';

/**
 * Save a message to conversation history
 *
 * @param {string} conversationId - Conversation UUID
 * @param {string} role - 'user' or 'assistant'
 * @param {string} content - Message content
 * @param {Object} metadata - Optional metadata (query_id, agent, cost, etc.)
 * @returns {Promise<Object>} Saved message
 */
async function saveMessage(conversationId, role, content, metadata = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/conversations/${conversationId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                role,
                content,
                metadata: metadata || {}
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const message = await response.json();
        console.log('💾 Message saved to conversation:', { conversationId, role });

        return message;

    } catch (error) {
        console.error('❌ Failed to save message:', error);
        // Don't throw - allow app to continue even if save fails
        return null;
    }
}

/**
 * Ensure conversation exists, creating if needed
 *
 * @param {string|null} currentConversationId - Current conversation ID or null
 * @param {string} firstMessage - First user message (for title generation)
 * @param {string} agent - Agent being used
 * @returns {Promise<string>} Conversation ID
 */
async function ensureConversation(currentConversationId, firstMessage, agent = 'claude_sonnet') {
    // If we already have a conversation, use it
    if (currentConversationId) {
        return currentConversationId;
    }

    // Create new conversation with generated title
    try {
        const title = generateConversationTitle(firstMessage);
        const conversation = await createConversation({ agent, title });
        console.log('➕ Created new conversation:', conversation.conversation_id);
        return conversation.conversation_id;
    } catch (error) {
        console.error('❌ Failed to create conversation:', error);
        throw error;
    }
}

/**
 * Save a complete question-answer pair to conversation
 *
 * @param {string} conversationId - Conversation UUID
 * @param {string} question - User's question
 * @param {string} answer - Assistant's answer
 * @param {Object} metadata - Response metadata (agent, cost, from_cache, etc.)
 * @returns {Promise<{user: Object, assistant: Object}>} Saved messages
 */
async function saveQuestionAnswer(conversationId, question, answer, metadata = {}) {
    try {
        // Save user message
        const userMessage = await saveMessage(conversationId, 'user', question);

        // Save assistant message with metadata
        const assistantMessage = await saveMessage(conversationId, 'assistant', answer, {
            query_id: metadata.query_id,
            agent: metadata.agent || 'claude_sonnet',
            from_cache: metadata.from_cache || false,
            cost_usd: metadata.cost_usd || metadata.cost || 0,
            confidence: metadata.confidence,
            latency_ms: metadata.latency_ms,
            thinking_steps: metadata.thinking_steps || []
        });

        return {
            user: userMessage,
            assistant: assistantMessage
        };

    } catch (error) {
        console.error('❌ Failed to save Q&A pair:', error);
        return null;
    }
}

module.exports = {
    saveMessage,
    ensureConversation,
    saveQuestionAnswer
};
