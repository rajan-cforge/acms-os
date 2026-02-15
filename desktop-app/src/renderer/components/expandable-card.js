/**
 * Expandable Card Component
 * Sprint 1: Foundation - UX Improvements
 *
 * A reusable expandable card component that:
 * - Shows collapsed preview by default
 * - Expands on click/keyboard to reveal full content
 * - Supports async content loading
 * - Full keyboard accessibility (WCAG AA compliant)
 * - Smooth CSS transitions
 *
 * Security: No innerHTML for user content, DOM-safe operations only.
 */

/**
 * ExpandableCard class
 *
 * @class
 * @param {Object} options - Configuration options
 * @param {string} options.id - Unique identifier for the card
 * @param {string} options.collapsedContent - HTML content shown when collapsed
 * @param {string|Function} options.expandedContent - HTML content or async function for expanded state
 * @param {Function} [options.onExpand] - Callback when card expands
 * @param {Function} [options.onCollapse] - Callback when card collapses
 * @param {boolean} [options.closeOnClickOutside=true] - Close when clicking outside
 */
class ExpandableCard {
    constructor(options) {
        this.id = options.id;
        this.collapsedContent = options.collapsedContent;
        this.expandedContent = options.expandedContent;
        this.onExpand = options.onExpand || null;
        this.onCollapse = options.onCollapse || null;
        this.closeOnClickOutside = options.closeOnClickOutside !== false;

        this._expanded = false;
        this._loading = false;
        this._loadedContent = null;
        this.element = null;

        // Bind methods for event listeners
        this._handleClick = this._handleClick.bind(this);
        this._handleKeydown = this._handleKeydown.bind(this);
        this._handleClickOutside = this._handleClickOutside.bind(this);
    }

    /**
     * Check if card is currently expanded
     * @returns {boolean}
     */
    isExpanded() {
        return this._expanded;
    }

    /**
     * Render the card element
     * @returns {HTMLElement}
     */
    render() {
        // Create main container
        const card = document.createElement('div');
        card.className = 'expandable-card';
        card.setAttribute('data-card-id', this.id);
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-expanded', 'false');

        // Collapsed content section
        const collapsedSection = document.createElement('div');
        collapsedSection.className = 'collapsed-content';
        collapsedSection.innerHTML = this.collapsedContent;
        card.appendChild(collapsedSection);

        // Expand indicator (chevron)
        const indicator = document.createElement('div');
        indicator.className = 'expand-indicator';
        indicator.innerHTML = '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4.5 6L8 9.5L11.5 6" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        card.appendChild(indicator);

        // Expanded content section (hidden initially)
        const expandedSection = document.createElement('div');
        expandedSection.className = 'expanded-content';
        expandedSection.style.display = 'none';
        card.appendChild(expandedSection);

        // Event listeners
        card.addEventListener('click', this._handleClick);
        card.addEventListener('keydown', this._handleKeydown);

        this.element = card;
        return card;
    }

    /**
     * Toggle expanded state
     */
    toggle() {
        if (this._expanded) {
            this.collapse();
        } else {
            this.expand();
        }
    }

    /**
     * Expand the card
     * @returns {Promise<void>}
     */
    async expand() {
        if (this._expanded || this._loading) {
            return;
        }

        this._expanded = true;
        this._updateExpandedState();

        // Register click outside listener
        if (this.closeOnClickOutside) {
            // Use setTimeout to avoid immediate trigger
            setTimeout(() => {
                document.addEventListener('click', this._handleClickOutside);
            }, 0);
        }

        // Load content if it's a function (async)
        const expandedSection = this.element.querySelector('.expanded-content');

        if (typeof this.expandedContent === 'function') {
            this._loading = true;
            this._showLoading(expandedSection);

            try {
                const content = await this.expandedContent();
                this._loadedContent = content;
                expandedSection.innerHTML = content;
            } catch (error) {
                expandedSection.innerHTML = '<p class="error">Failed to load content</p>';
                console.error('ExpandableCard content load error:', error);
            } finally {
                this._loading = false;
                this._hideLoading();
            }
        } else if (!this._loadedContent) {
            // Static content - load once
            expandedSection.innerHTML = this.expandedContent;
            this._loadedContent = this.expandedContent;
        }

        // Show expanded content
        expandedSection.style.display = 'block';

        // Trigger callback
        if (this.onExpand) {
            this.onExpand(this);
        }
    }

    /**
     * Collapse the card
     */
    collapse() {
        if (!this._expanded) {
            return;
        }

        this._expanded = false;
        this._updateExpandedState();

        // Remove click outside listener
        document.removeEventListener('click', this._handleClickOutside);

        // Hide expanded content
        const expandedSection = this.element.querySelector('.expanded-content');
        if (expandedSection) {
            expandedSection.style.display = 'none';
        }

        // Trigger callback
        if (this.onCollapse) {
            this.onCollapse(this);
        }
    }

    /**
     * Destroy the card and clean up listeners
     */
    destroy() {
        if (this.element) {
            this.element.removeEventListener('click', this._handleClick);
            this.element.removeEventListener('keydown', this._handleKeydown);
            document.removeEventListener('click', this._handleClickOutside);
        }
    }

    /**
     * Update DOM to reflect expanded state
     * @private
     */
    _updateExpandedState() {
        if (!this.element) return;

        if (this._expanded) {
            this.element.classList.add('expanded');
            this.element.setAttribute('aria-expanded', 'true');
        } else {
            this.element.classList.remove('expanded');
            this.element.setAttribute('aria-expanded', 'false');
        }
    }

    /**
     * Handle click events
     * @private
     * @param {Event} event
     */
    _handleClick(event) {
        // Don't toggle if clicking inside expanded content (unless it's the header)
        const expandedContent = this.element.querySelector('.expanded-content');
        if (this._expanded && expandedContent && expandedContent.contains(event.target)) {
            event.stopPropagation();
            return;
        }

        this.toggle();
    }

    /**
     * Handle keyboard events
     * @private
     * @param {KeyboardEvent} event
     */
    _handleKeydown(event) {
        switch (event.key) {
            case 'Enter':
            case ' ':
                event.preventDefault();
                this.toggle();
                break;
            case 'Escape':
                if (this._expanded) {
                    event.preventDefault();
                    this.collapse();
                }
                break;
        }
    }

    /**
     * Handle clicks outside the card
     * @private
     * @param {Event} event
     */
    _handleClickOutside(event) {
        if (this._expanded && this.element && !this.element.contains(event.target)) {
            this.collapse();
        }
    }

    /**
     * Show loading state
     * @private
     * @param {HTMLElement} container
     */
    _showLoading(container) {
        const loader = document.createElement('div');
        loader.className = 'loading';
        loader.innerHTML = `
            <div class="loading-spinner"></div>
            <span>Loading...</span>
        `;
        container.innerHTML = '';
        container.appendChild(loader);
        container.style.display = 'block';
    }

    /**
     * Hide loading state
     * @private
     */
    _hideLoading() {
        const loader = this.element.querySelector('.loading');
        if (loader) {
            loader.remove();
        }
    }
}

/**
 * Create an expandable card from existing DOM element
 * @param {HTMLElement} element - Existing element to enhance
 * @param {Object} options - Configuration options
 * @returns {ExpandableCard}
 */
function createExpandableCard(element, options) {
    const card = new ExpandableCard({
        id: element.getAttribute('data-card-id') || options.id,
        collapsedContent: element.querySelector('.collapsed-content')?.innerHTML || options.collapsedContent,
        expandedContent: options.expandedContent,
        onExpand: options.onExpand,
        onCollapse: options.onCollapse
    });

    // Replace the element with rendered card
    const rendered = card.render();
    element.parentNode?.replaceChild(rendered, element);

    return card;
}

/**
 * Initialize all expandable cards in a container
 * @param {HTMLElement} container - Container to search
 * @param {Object} options - Default options for all cards
 * @returns {ExpandableCard[]}
 */
function initExpandableCards(container, options = {}) {
    const elements = container.querySelectorAll('[data-expandable-card]');
    const cards = [];

    elements.forEach(element => {
        const cardOptions = {
            ...options,
            id: element.getAttribute('data-card-id'),
            collapsedContent: element.querySelector('.collapsed-content')?.innerHTML,
            expandedContent: element.querySelector('.expanded-content')?.innerHTML
        };

        const card = new ExpandableCard(cardOptions);
        const rendered = card.render();
        element.parentNode?.replaceChild(rendered, element);
        cards.push(card);
    });

    return cards;
}

// Export for CommonJS (Electron)
module.exports = {
    ExpandableCard,
    createExpandableCard,
    initExpandableCards
};
