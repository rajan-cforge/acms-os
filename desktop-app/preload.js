/**
 * ACMS Desktop App - Preload Script
 *
 * This script runs in a privileged context and exposes
 * only the necessary Electron APIs to the renderer process
 * through a secure contextBridge.
 *
 * Security: This prevents XSS attacks from gaining full Node.js access.
 */

const { contextBridge, ipcRenderer, shell } = require('electron');

// Expose protected methods that allow the renderer process to use
// specific Electron features without exposing the full API
contextBridge.exposeInMainWorld('electronAPI', {
    // IPC communication
    send: (channel, data) => {
        // Whitelist channels
        const validChannels = ['app-ready', 'window-minimize', 'window-close'];
        if (validChannels.includes(channel)) {
            ipcRenderer.send(channel, data);
        }
    },

    receive: (channel, callback) => {
        const validChannels = ['update-available', 'update-downloaded'];
        if (validChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => callback(...args));
        }
    },

    // Safe shell operations
    openExternal: (url) => {
        // Only allow http/https URLs
        if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
            shell.openExternal(url);
        }
    },

    // App info
    getVersion: () => {
        return process.env.npm_package_version || '1.0.0';
    },

    // Platform info
    platform: process.platform
});

// Log that preload script ran successfully
console.log('ACMS preload script loaded');
