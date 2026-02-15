/**
 * Cognitive Architecture UI Components
 *
 * Cognitive Architecture Sprint 4-5 (Feb 2026)
 *
 * Components implementing cognitive science principles in the UI:
 *
 * 1. Cross-Domain Discovery (Sprint 5)
 *    - Displays creative recombination insights
 *    - Shows connections between distant knowledge domains
 *    - Cognitive Principle: REM Sleep Creative Discovery
 *
 * 2. Expertise Indicator (Sprint 4)
 *    - Shows user's expertise level for current topic
 *    - 🌱 Beginner → 🌿 Intermediate → 🔬 Advanced → 🏗️ Expert
 *    - Cognitive Principle: Schema-Driven Comprehension
 *
 * Usage:
 *   const cognitive = require('./components/cognitive');
 *   cognitive.initAll();
 *
 * Or individual components:
 *   const { initCrossDomainDiscovery } = require('./components/cognitive');
 *   initCrossDomainDiscovery();
 */

// Import components
const crossDomainDiscovery = require('./cross-domain-discovery');
const expertiseIndicator = require('./expertise-indicator');

/**
 * Initialize all cognitive UI components
 */
function initAll() {
    // Initialize cross-domain discovery panel
    crossDomainDiscovery.initCrossDomainDiscovery();

    // Initialize expertise indicator
    expertiseIndicator.initExpertiseIndicator();

    // Inject styles
    injectCognitiveStyles();

    console.log('All cognitive UI components initialized');
}

/**
 * Inject CSS styles for all cognitive components
 */
function injectCognitiveStyles() {
    if (document.getElementById('cognitive-styles')) return;

    const style = document.createElement('style');
    style.id = 'cognitive-styles';
    style.textContent = `
        /* Cross-Domain Discovery Styles */
        ${crossDomainDiscovery.getDiscoveryStyles()}

        /* Expertise Indicator Styles */
        ${expertiseIndicator.getExpertiseStyles()}

        /* Shared Cognitive UI Variables */
        :root {
            --cognitive-purple: #9C27B0;
            --cognitive-cyan: #00BCD4;
            --cognitive-green: #4CAF50;
            --cognitive-orange: #FF9800;
            --cognitive-blue: #2196F3;
        }

        /* Cognitive panel animations */
        .discovery-card,
        .expertise-badge {
            animation: cognitive-fade-in 0.3s ease-out;
        }

        @keyframes cognitive-fade-in {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* Cognitive hover effects */
        .discovery-card:hover,
        .expertise-badge:hover {
            box-shadow: 0 0 20px rgba(156, 39, 176, 0.2);
        }
    `;

    document.head.appendChild(style);
}

// Re-export individual component functions
module.exports = {
    // Initialization
    initAll,
    injectCognitiveStyles,

    // Cross-Domain Discovery
    initCrossDomainDiscovery: crossDomainDiscovery.initCrossDomainDiscovery,
    fetchDiscoveries: crossDomainDiscovery.fetchDiscoveries,
    createDiscoveryPanel: crossDomainDiscovery.createDiscoveryPanel,
    createDiscoveryCard: crossDomainDiscovery.createDiscoveryCard,
    getDiscoveryStyles: crossDomainDiscovery.getDiscoveryStyles,

    // Expertise Indicator
    initExpertiseIndicator: expertiseIndicator.initExpertiseIndicator,
    updateExpertiseIndicator: expertiseIndicator.updateExpertiseIndicator,
    fetchExpertiseLevel: expertiseIndicator.fetchExpertiseLevel,
    createExpertiseIndicator: expertiseIndicator.createExpertiseIndicator,
    getExpertiseStyles: expertiseIndicator.getExpertiseStyles,
    EXPERTISE_LEVELS: expertiseIndicator.EXPERTISE_LEVELS
};
