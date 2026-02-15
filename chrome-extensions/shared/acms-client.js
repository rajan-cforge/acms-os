/**
 * ACMS API Client for Chrome Extensions
 *
 * Shared library for communicating with ACMS API from browser extensions.
 * Handles memory creation, privacy detection, and error handling.
 */

const ACMS_API_BASE = 'http://localhost:40080';

class ACMSClient {
  constructor(apiBase = ACMS_API_BASE) {
    this.apiBase = apiBase;
  }

  /**
   * Check if ACMS API is reachable
   * @returns {Promise<boolean>}
   */
  async checkHealth() {
    try {
      const response = await fetch(`${this.apiBase}/health`);
      return response.ok;
    } catch (error) {
      console.error('[ACMS] Health check failed:', error);
      return false;
    }
  }

  /**
   * Create a new memory in ACMS
   * @param {Object} memoryData
   * @param {string} memoryData.content - Memory content
   * @param {string[]} memoryData.tags - Tags
   * @param {string} memoryData.tier - Memory tier (SHORT/MID/LONG)
   * @param {string} memoryData.phase - Phase/context
   * @param {string} memoryData.privacy_level - Privacy level (optional, auto-detected if not provided)
   * @param {boolean} memoryData.auto_detect_privacy - Auto-detect privacy from content
   * @param {Object} memoryData.metadata - Additional metadata
   * @returns {Promise<Object>} Result with memory_id or error
   */
  async createMemory(memoryData) {
    try {
      const response = await fetch(`${this.apiBase}/memories`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(memoryData),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API returned ${response.status}: ${errorText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[ACMS] Failed to create memory:', error);
      return { error: error.message };
    }
  }

  /**
   * Search memories
   * @param {string} query - Search query
   * @param {number} limit - Max results
   * @returns {Promise<Object>} Search results
   */
  async searchMemories(query, limit = 10) {
    try {
      const response = await fetch(`${this.apiBase}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, limit }),
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[ACMS] Search failed:', error);
      return { error: error.message, results: [] };
    }
  }

  /**
   * Get system stats
   * @returns {Promise<Object>} Statistics
   */
  async getStats() {
    try {
      const response = await fetch(`${this.apiBase}/stats`);

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[ACMS] Failed to get stats:', error);
      return { error: error.message };
    }
  }
}

// Export for use in extensions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ACMSClient;
}
