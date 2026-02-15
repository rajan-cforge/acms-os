/**
 * ACMS Desktop - Login Component
 *
 * Sprint 3 Day 11-12: Authentication UI
 *
 * Features:
 * - Login form with email/password
 * - Registration form
 * - Role-based access display
 * - Token storage and refresh
 * - Session persistence
 */

const { login, register, getStoredAuth, clearAuth, refreshToken } = require('../utils/auth.js');

/**
 * Render the login screen
 * @param {HTMLElement} container - Container to render into
 * @param {Function} onLoginSuccess - Callback when login succeeds
 */
function renderLoginScreen(container, onLoginSuccess) {
    container.innerHTML = '';

    const loginContainer = document.createElement('div');
    loginContainer.className = 'login-container';

    loginContainer.innerHTML = `
        <div class="login-card">
            <div class="login-header">
                <div class="login-logo">ACMS</div>
                <p class="login-subtitle">Adaptive Context Memory System</p>
            </div>

            <div class="login-tabs">
                <button class="login-tab active" data-tab="login">Sign In</button>
                <button class="login-tab" data-tab="register">Register</button>
            </div>

            <form id="login-form" class="auth-form">
                <div class="form-group">
                    <label for="login-email">Email</label>
                    <input type="email" id="login-email" name="email" placeholder="Enter your email" required>
                </div>
                <div class="form-group">
                    <label for="login-password">Password</label>
                    <input type="password" id="login-password" name="password" placeholder="Enter your password" required>
                </div>
                <div id="login-error" class="form-error hidden"></div>
                <button type="submit" class="btn-login">Sign In</button>

                <div class="demo-accounts">
                    <p>Demo accounts:</p>
                    <div class="demo-buttons">
                        <button type="button" class="demo-btn demo-btn-primary" data-email="default@acms.local" data-password="default123!">Default (Your Data)</button>
                        <button type="button" class="demo-btn" data-email="admin@acms.local" data-password="admin123!">Admin</button>
                        <button type="button" class="demo-btn" data-email="member@acms.local" data-password="member123!">Member</button>
                    </div>
                </div>
            </form>

            <form id="register-form" class="auth-form hidden">
                <div class="form-group">
                    <label for="register-email">Email</label>
                    <input type="email" id="register-email" name="email" placeholder="Enter your email" required>
                </div>
                <div class="form-group">
                    <label for="register-username">Username (optional)</label>
                    <input type="text" id="register-username" name="username" placeholder="Choose a username">
                </div>
                <div class="form-group">
                    <label for="register-password">Password</label>
                    <input type="password" id="register-password" name="password" placeholder="Min 8 characters" required minlength="8">
                </div>
                <div class="form-group">
                    <label for="register-role">Role</label>
                    <select id="register-role" name="role">
                        <option value="member">Member (default)</option>
                        <option value="public">Public (limited access)</option>
                        <option value="admin">Admin (full access)</option>
                    </select>
                </div>
                <div id="register-error" class="form-error hidden"></div>
                <button type="submit" class="btn-login">Create Account</button>
            </form>
        </div>
    `;

    container.appendChild(loginContainer);

    // Setup tab switching
    const tabs = loginContainer.querySelectorAll('.login-tab');
    const loginForm = loginContainer.querySelector('#login-form');
    const registerForm = loginContainer.querySelector('#register-form');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            if (tab.dataset.tab === 'login') {
                loginForm.classList.remove('hidden');
                registerForm.classList.add('hidden');
            } else {
                loginForm.classList.add('hidden');
                registerForm.classList.remove('hidden');
            }
        });
    });

    // Setup demo account buttons
    const demoButtons = loginContainer.querySelectorAll('.demo-btn');
    demoButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const emailInput = loginContainer.querySelector('#login-email');
            const passwordInput = loginContainer.querySelector('#login-password');
            emailInput.value = btn.dataset.email;
            passwordInput.value = btn.dataset.password;
        });
    });

    // Handle login form submission
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errorDiv = loginContainer.querySelector('#login-error');
        errorDiv.classList.add('hidden');

        const email = loginContainer.querySelector('#login-email').value;
        const password = loginContainer.querySelector('#login-password').value;

        try {
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Signing in...';

            const result = await login(email, password);

            if (result.success) {
                console.log('Login successful:', result.user);
                onLoginSuccess(result.user);
            } else {
                errorDiv.textContent = result.error || 'Login failed';
                errorDiv.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Login error:', error);
            errorDiv.textContent = error.message || 'Login failed';
            errorDiv.classList.remove('hidden');
        } finally {
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Sign In';
        }
    });

    // Handle register form submission
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errorDiv = loginContainer.querySelector('#register-error');
        errorDiv.classList.add('hidden');

        const email = loginContainer.querySelector('#register-email').value;
        const username = loginContainer.querySelector('#register-username').value;
        const password = loginContainer.querySelector('#register-password').value;
        const role = loginContainer.querySelector('#register-role').value;

        try {
            const submitBtn = registerForm.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating account...';

            const result = await register(email, password, username, role);

            if (result.success) {
                console.log('Registration successful:', result.user);
                onLoginSuccess(result.user);
            } else {
                errorDiv.textContent = result.error || 'Registration failed';
                errorDiv.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Registration error:', error);
            errorDiv.textContent = error.message || 'Registration failed';
            errorDiv.classList.remove('hidden');
        } finally {
            const submitBtn = registerForm.querySelector('button[type="submit"]');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create Account';
        }
    });
}

/**
 * Check if user is already logged in
 * @returns {Object|null} User data if logged in, null otherwise
 */
async function checkExistingSession() {
    const auth = getStoredAuth();
    if (!auth || !auth.access_token) {
        return null;
    }

    // Try to refresh token to ensure it's valid
    try {
        const result = await refreshToken();
        if (result.success) {
            return result.user;
        }
    } catch (error) {
        console.log('Session expired, clearing auth');
        clearAuth();
    }

    return null;
}

/**
 * Create role badge element
 * @param {string} role - User role (admin, member, public)
 * @returns {HTMLElement} Badge element
 */
function createRoleBadge(role) {
    const badge = document.createElement('span');
    badge.className = `role-badge role-${role}`;
    badge.textContent = role.toUpperCase();
    return badge;
}

/**
 * Render user info in header
 * @param {Object} user - User data
 * @param {HTMLElement} container - Container to render into
 * @param {Function} onLogout - Callback when user logs out
 */
function renderUserInfo(user, container, onLogout) {
    const userInfo = document.createElement('div');
    userInfo.className = 'user-info';

    userInfo.innerHTML = `
        <span class="user-name">${user.username || user.email}</span>
        <span class="role-badge role-${user.role}">${user.role.toUpperCase()}</span>
        <button class="logout-btn" title="Sign out">
            <span class="logout-icon">&#x2192;</span>
        </button>
    `;

    // Handle logout
    userInfo.querySelector('.logout-btn').addEventListener('click', () => {
        clearAuth();
        if (onLogout) onLogout();
    });

    container.appendChild(userInfo);
}

module.exports = {
    renderLoginScreen,
    checkExistingSession,
    createRoleBadge,
    renderUserInfo
};
