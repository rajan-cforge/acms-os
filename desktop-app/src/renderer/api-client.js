/**
 * API Client
 * Sprint 3-6: Unified API client for new components
 *
 * Provides fetchWithAuth for authenticated API calls
 */

const API_BASE = 'http://localhost:40080';

/**
 * Make an authenticated API request
 * @param {string} endpoint - API endpoint (e.g., '/api/v2/knowledge')
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} Fetch response
 */
async function fetchWithAuth(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        return response;
    } catch (error) {
        console.error(`API Error: ${endpoint}`, error);
        throw error;
    }
}

/**
 * GET request helper
 */
async function apiGet(endpoint) {
    const response = await fetchWithAuth(endpoint);
    if (!response.ok) {
        throw new Error(`GET ${endpoint} failed: ${response.status}`);
    }
    return response.json();
}

/**
 * POST request helper
 */
async function apiPost(endpoint, data) {
    const response = await fetchWithAuth(endpoint, {
        method: 'POST',
        body: JSON.stringify(data)
    });
    if (!response.ok) {
        throw new Error(`POST ${endpoint} failed: ${response.status}`);
    }
    return response.json();
}

/**
 * DELETE request helper
 */
async function apiDelete(endpoint) {
    const response = await fetchWithAuth(endpoint, {
        method: 'DELETE'
    });
    if (!response.ok) {
        throw new Error(`DELETE ${endpoint} failed: ${response.status}`);
    }
    return response.json();
}

module.exports = {
    fetchWithAuth,
    apiGet,
    apiPost,
    apiDelete,
    API_BASE
};
