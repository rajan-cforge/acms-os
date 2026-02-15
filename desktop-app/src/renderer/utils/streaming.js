/**
 * Streaming Response Handler
 *
 * Week 5 Day 3: Real-time SSE (Server-Sent Events) streaming
 * Sprint 3 Day 14: Stop Generation with AbortController
 *
 * Features:
 * - EventSource for SSE connection
 * - Real-time chunk processing
 * - Status updates (thinking steps)
 * - Error handling
 * - Connection management
 * - AbortController for stopping generation
 */

const API_BASE_URL = 'http://localhost:40080';

// Track current active stream for abort capability
let currentAbortController = null;

/**
 * Stream chat message with real-time updates
 *
 * @param {Object} params - Message parameters
 * @param {string} params.message - User message
 * @param {string} params.agent - Agent to use
 * @param {string} params.conversationId - Optional conversation ID for persistence
 * @param {Function} onChunk - Callback for each text chunk (chunk)
 * @param {Function} onStatus - Callback for status updates (status)
 * @param {Function} onComplete - Callback when done (response)
 * @param {Function} onError - Callback on error (error)
 * @returns {Function} Abort function to stop streaming
 */
function streamChatMessage(params, callbacks) {
    const { onChunk, onStatus, onComplete, onError } = callbacks;

    // Map UI agent names to API agent names
    const agentMap = {
        'auto': null,
        'claude': 'claude_sonnet',
        'gpt': 'chatgpt',
        'gemini': 'gemini',
        'ollama': 'ollama'
    };

    const manualAgent = agentMap[params.agent] || null;

    // Build query parameters
    const queryParams = new URLSearchParams({
        query: params.message,
        bypass_cache: 'false',
        context_limit: '5'
    });

    if (manualAgent) {
        queryParams.set('manual_agent', manualAgent);
    }

    // Create EventSource for SSE
    const url = `${API_BASE_URL}/gateway/ask?${queryParams}`;

    console.log('🌊 Starting SSE stream:', url);

    // Note: EventSource doesn't work with POST, need to use GET with query params
    // OR use fetch with ReadableStream

    // Using fetch with ReadableStream for POST support
    return streamWithFetch(url, params, callbacks);
}

/**
 * Stream using fetch API with ReadableStream
 *
 * This allows POST requests with SSE-like streaming
 * Sprint 3 Day 14: Added AbortController support for stop generation
 *
 * @returns {Function} Abort function to stop the stream
 */
async function streamWithFetch(baseUrl, params, callbacks) {
    const { onChunk, onStatus, onComplete, onError, onAbort } = callbacks;

    // Create AbortController for this request
    const abortController = new AbortController();
    currentAbortController = abortController;

    // Map agent names
    const agentMap = {
        'auto': null,
        'claude': 'claude_sonnet',
        'gpt': 'chatgpt',
        'gemini': 'gemini',
        'ollama': 'ollama'
    };

    const manualAgent = agentMap[params.agent] || null;

    const requestBody = {
        query: params.message,
        manual_agent: manualAgent,
        bypass_cache: false,
        context_limit: 5
    };

    // Add conversation_id if provided (for message persistence)
    if (params.conversationId) {
        requestBody.conversation_id = params.conversationId;
    }

    // Sprint 3 Day 15: Add file context for ChatGPT-style file handling
    if (params.fileContext) {
        requestBody.file_context = params.fileContext;
        console.log('📎 Including file context in request:', params.fileContext.filename);
    }

    // Dec 2025: Add cross-source toggle for Unified Intelligence
    if (params.crossSourceEnabled !== undefined) {
        requestBody.cross_source_enabled = params.crossSourceEnabled;
    }

    console.log('🌊 Starting streaming POST:', {
        ...requestBody,
        file_context: requestBody.file_context ? `[${requestBody.file_context.filename}]` : null,
        cross_source: requestBody.cross_source_enabled
    });

    let fullText = '';
    let wasAborted = false;

    try {
        const response = await fetch(`${API_BASE_URL}/gateway/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify(requestBody),
            signal: abortController.signal
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let buffer = '';
        let doneEventReceived = false;

        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                console.log('✅ Stream complete');
                break;
            }

            // Decode chunk
            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE events
            const events = buffer.split('\n\n');
            buffer = events.pop() || ''; // Keep incomplete event in buffer

            for (const eventText of events) {
                if (!eventText.trim()) continue;

                const event = parseSSEEvent(eventText);

                if (event.event === 'status' && onStatus) {
                    // Status update (thinking step)
                    onStatus(event.data);
                } else if (event.event === 'chunk' && onChunk) {
                    // Text chunk - extract text from chunk object
                    // Chunk data format: {type: "chunk", text: "..."}
                    const chunkText = event.data.text || event.data;
                    fullText += chunkText;
                    onChunk(chunkText, fullText);
                } else if (event.event === 'done' && onComplete) {
                    // Final response with metadata
                    let responseData = typeof event.data === 'string'
                        ? JSON.parse(event.data)
                        : event.data;

                    // The done event has structure: {type: "done", response: {...}}
                    // Extract the actual response object
                    const response = responseData.response || responseData;

                    // Ensure response has the full text
                    response.answer = fullText || response.answer;

                    doneEventReceived = true;
                    onComplete(response);
                } else if (event.event === 'error' && onError) {
                    // Error - properly stringify error data
                    const errorMsg = typeof event.data === 'object'
                        ? (event.data.message || event.data.error || JSON.stringify(event.data))
                        : event.data;
                    onError(new Error(errorMsg));
                }
            }
        }

        // If no 'done' event received, still complete with accumulated text
        // Note: This fallback means feedback won't work for this message
        // since we don't have a real query_id from the database
        if (fullText && onComplete && !doneEventReceived) {
            console.warn('⚠️  No done event received - feedback will not work for this message');
            onComplete({
                answer: fullText,
                query_id: null, // No real query_id available
                agent_used: params.agent || 'auto',
                from_cache: false
            });
        }

    } catch (error) {
        // Check if this was an abort
        if (error.name === 'AbortError') {
            console.log('🛑 Stream aborted by user');
            wasAborted = true;

            // Call onAbort callback if provided
            if (onAbort) {
                onAbort(fullText);
            }

            // Complete with partial response
            if (fullText && onComplete) {
                onComplete({
                    answer: fullText + '\n\n[Generation stopped]',
                    query_id: null,
                    agent_used: params.agent || 'auto',
                    from_cache: false,
                    was_aborted: true
                });
            }
        } else {
            console.error('❌ Stream error:', error);
            if (onError) {
                onError(error);
            }
        }
    } finally {
        // Clear the current abort controller
        if (currentAbortController === abortController) {
            currentAbortController = null;
        }
    }

    // Return abort function
    return () => {
        if (!wasAborted) {
            console.log('🛑 Aborting stream...');
            abortController.abort();
        }
    };
}

/**
 * Abort the current streaming request
 *
 * Sprint 3 Day 14: Stop Generation capability
 *
 * @returns {boolean} True if a stream was aborted, false if no active stream
 */
function abortCurrentStream() {
    if (currentAbortController) {
        console.log('🛑 Aborting current stream');
        currentAbortController.abort();
        currentAbortController = null;
        return true;
    }
    return false;
}

/**
 * Check if there's an active stream
 *
 * @returns {boolean} True if streaming is in progress
 */
function isStreaming() {
    return currentAbortController !== null;
}

/**
 * Parse SSE event from text
 *
 * SSE format:
 *   event: chunk
 *   data: {"text": "Hello"}
 *
 * @param {string} eventText - Raw event text
 * @returns {Object} Parsed event {event, data}
 */
function parseSSEEvent(eventText) {
    const lines = eventText.split('\n');
    const event = {
        event: 'message',
        data: null
    };

    for (const line of lines) {
        if (line.startsWith('event:')) {
            event.event = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
            const dataStr = line.substring(5).trim();
            try {
                event.data = JSON.parse(dataStr);
            } catch (e) {
                event.data = dataStr;
            }
        }
    }

    return event;
}

/**
 * Stream with EventSource (GET only)
 *
 * Note: EventSource only supports GET requests, so we need query params
 * This is kept for reference but fetch() is preferred for POST support
 */
function streamWithEventSource(url, callbacks) {
    const { onChunk, onStatus, onComplete, onError } = callbacks;

    const eventSource = new EventSource(url);
    let fullText = '';

    eventSource.addEventListener('status', (e) => {
        if (onStatus) {
            const status = JSON.parse(e.data);
            onStatus(status);
        }
    });

    eventSource.addEventListener('chunk', (e) => {
        if (onChunk) {
            const chunk = JSON.parse(e.data);
            fullText += chunk.text || chunk;
            onChunk(chunk.text || chunk, fullText);
        }
    });

    eventSource.addEventListener('done', (e) => {
        const response = JSON.parse(e.data);
        response.answer = fullText || response.answer;

        if (onComplete) {
            onComplete(response);
        }

        eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
        if (onError) {
            onError(new Error('EventSource error'));
        }
        eventSource.close();
    });

    eventSource.onerror = (e) => {
        console.error('EventSource error:', e);
        if (onError) {
            onError(new Error('Stream connection failed'));
        }
        eventSource.close();
    };

    // Return abort function
    return () => {
        eventSource.close();
    };
}

// Export functions
module.exports = {
    streamChatMessage,
    streamWithFetch,
    streamWithEventSource,
    parseSSEEvent,
    abortCurrentStream,
    isStreaming
};
