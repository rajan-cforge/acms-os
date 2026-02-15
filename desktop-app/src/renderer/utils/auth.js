/**
 * ACMS Desktop - Authentication Utilities
 *
 * Sprint 3 Day 11-12: Token Management
 *
 * Features:
 * - Token storage (localStorage)
 * - Login/logout/register API calls
 * - Token refresh
 * - Auth state management
 */

const API_BASE_URL = 'http://localhost:40080';

// Storage keys
const STORAGE_KEYS = {
    ACCESS_TOKEN: 'acms_access_token',
    REFRESH_TOKEN: 'acms_refresh_token',
    USER: 'acms_user'
};

/**
 * Store authentication data
 * @param {Object} authData - Auth response from API
 */
function storeAuth(authData) {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, authData.access_token);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, authData.refresh_token);
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(authData.user));
}

/**
 * Get stored authentication data
 * @returns {Object|null} Auth data or null if not logged in
 */
function getStoredAuth() {
    const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
    const userStr = localStorage.getItem(STORAGE_KEYS.USER);

    if (!accessToken) return null;

    return {
        access_token: accessToken,
        refresh_token: refreshToken,
        user: userStr ? JSON.parse(userStr) : null
    };
}

/**
 * Clear all stored authentication data
 */
function clearAuth() {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER);
}

/**
 * Get current user from storage
 * @returns {Object|null} User data or null
 */
function getCurrentUser() {
    const userStr = localStorage.getItem(STORAGE_KEYS.USER);
    return userStr ? JSON.parse(userStr) : null;
}

/**
 * Get access token for API calls
 * @returns {string|null} Access token or null
 */
function getAccessToken() {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
}

/**
 * Login with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<Object>} Result with success, user, or error
 */
async function login(email, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
            const error = await response.json();
            return {
                success: false,
                error: error.detail || 'Login failed'
            };
        }

        const data = await response.json();
        storeAuth(data);

        return {
            success: true,
            user: data.user
        };
    } catch (error) {
        console.error('Login error:', error);
        return {
            success: false,
            error: error.message || 'Network error'
        };
    }
}

/**
 * Register a new user
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {string} username - Optional username
 * @param {string} role - User role (public, member, admin)
 * @returns {Promise<Object>} Result with success, user, or error
 */
async function register(email, password, username = null, role = 'member') {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email,
                password,
                username,
                role,
                tenant_id: 'default'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            return {
                success: false,
                error: error.detail || 'Registration failed'
            };
        }

        const data = await response.json();
        storeAuth(data);

        return {
            success: true,
            user: data.user
        };
    } catch (error) {
        console.error('Registration error:', error);
        return {
            success: false,
            error: error.message || 'Network error'
        };
    }
}

/**
 * Refresh access token using refresh token
 * @returns {Promise<Object>} Result with success, user, or error
 */
async function refreshToken() {
    const auth = getStoredAuth();
    if (!auth || !auth.refresh_token) {
        return { success: false, error: 'No refresh token' };
    }

    try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                refresh_token: auth.refresh_token
            })
        });

        if (!response.ok) {
            clearAuth();
            return {
                success: false,
                error: 'Session expired'
            };
        }

        const data = await response.json();
        storeAuth(data);

        return {
            success: true,
            user: data.user
        };
    } catch (error) {
        console.error('Token refresh error:', error);
        return {
            success: false,
            error: error.message || 'Network error'
        };
    }
}

/**
 * Get current user info from API
 * @returns {Promise<Object>} Result with success, user, or error
 */
async function fetchCurrentUser() {
    const token = getAccessToken();
    if (!token) {
        return { success: false, error: 'Not authenticated' };
    }

    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                // Try to refresh token
                const refreshResult = await refreshToken();
                if (refreshResult.success) {
                    return { success: true, user: refreshResult.user };
                }
                clearAuth();
            }
            return {
                success: false,
                error: 'Failed to fetch user info'
            };
        }

        const user = await response.json();
        return {
            success: true,
            user
        };
    } catch (error) {
        console.error('Fetch user error:', error);
        return {
            success: false,
            error: error.message || 'Network error'
        };
    }
}

/**
 * Make authenticated API request
 * @param {string} endpoint - API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} Fetch response
 */
async function authFetch(endpoint, options = {}) {
    const token = getAccessToken();

    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers
    });

    // If unauthorized, try to refresh token
    if (response.status === 401 && token) {
        const refreshResult = await refreshToken();
        if (refreshResult.success) {
            // Retry with new token
            headers['Authorization'] = `Bearer ${getAccessToken()}`;
            return fetch(`${API_BASE_URL}${endpoint}`, {
                ...options,
                headers
            });
        }
    }

    return response;
}

/**
 * Check if user is authenticated
 * @returns {boolean} True if authenticated
 */
function isAuthenticated() {
    return !!getAccessToken();
}

/**
 * Get user role
 * @returns {string|null} User role or null
 */
function getUserRole() {
    const user = getCurrentUser();
    return user ? user.role : null;
}

/**
 * Check if user has required role
 * @param {string|string[]} requiredRoles - Required role(s)
 * @returns {boolean} True if user has required role
 */
function hasRole(requiredRoles) {
    const role = getUserRole();
    if (!role) return false;

    if (Array.isArray(requiredRoles)) {
        return requiredRoles.includes(role);
    }
    return role === requiredRoles;
}

/**
 * Check if user can access admin features
 * @returns {boolean} True if admin
 */
function isAdmin() {
    return getUserRole() === 'admin';
}

/**
 * Check if user can access member features
 * @returns {boolean} True if member or admin
 */
function isMemberOrAbove() {
    return hasRole(['member', 'admin']);
}

module.exports = {
    storeAuth,
    getStoredAuth,
    clearAuth,
    getCurrentUser,
    getAccessToken,
    login,
    register,
    refreshToken,
    fetchCurrentUser,
    authFetch,
    isAuthenticated,
    getUserRole,
    hasRole,
    isAdmin,
    isMemberOrAbove
};
