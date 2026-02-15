/**
 * Renderer Process Bootstrap
 *
 * Week 5 Day 2: Modular Production-Quality Architecture
 *
 * This file initializes the ACMS Desktop app with the new component-based architecture.
 *
 * Architecture:
 * - app.js: Main application controller
 * - components/message.js: Message rendering
 * - components/input.js: Input area with agent selector
 * - components/sidebar.js: Navigation and conversation list
 * - utils/api.js: API communication
 * - styles/chat.css: Styles
 */

const { AcmsApp } = require('./app.js');

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 ACMS Desktop - Week 5 Production UI');
    console.log('📦 Loading modular components...');

    // Create and initialize app
    const app = new AcmsApp();

    // Make app instance available globally for debugging
    window.acmsApp = app;

    console.log('🎉 ACMS Desktop ready!');
});

// Handle uncaught errors
window.addEventListener('error', (e) => {
    console.error('💥 Uncaught error:', e.error);
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (e) => {
    console.error('💥 Unhandled promise rejection:', e.reason);
});
