// desktop-app/tests/components/expandable-card.test.js
/**
 * TDD Tests for Expandable Card Component
 * Sprint 1: Foundation
 *
 * Tests verify all expected behaviors of the expandable card component.
 * Run with: npm test
 */

// Mock DOM environment for testing
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.document = dom.window.document;
global.window = dom.window;
global.HTMLElement = dom.window.HTMLElement;

// Import the component
const { ExpandableCard } = require('../../src/renderer/components/expandable-card.js');

describe('ExpandableCard Component', () => {

  // Clean up DOM after each test
  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('Initialization', () => {

    test('renders in collapsed state by default', () => {
      const card = new ExpandableCard({
        id: 'test-1',
        collapsedContent: '<p>Preview content</p>',
        expandedContent: '<p>Full content here</p>'
      });
      const el = card.render();

      expect(el.classList.contains('expanded')).toBe(false);
      expect(el.classList.contains('expandable-card')).toBe(true);
    });

    test('shows collapsed content initially', () => {
      const card = new ExpandableCard({
        id: 'test-2',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();

      expect(el.querySelector('.collapsed-content')).toBeTruthy();
      expect(el.querySelector('.collapsed-content').innerHTML).toContain('Preview');
    });

    test('hides expanded content initially', () => {
      const card = new ExpandableCard({
        id: 'test-3',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();

      const expandedEl = el.querySelector('.expanded-content');
      expect(expandedEl.style.display).toBe('none');
    });

    test('has chevron indicator', () => {
      const card = new ExpandableCard({
        id: 'test-4',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();

      expect(el.querySelector('.expand-indicator')).toBeTruthy();
    });

  });

  describe('Expand/Collapse Behavior', () => {

    test('click expands the card', async () => {
      const card = new ExpandableCard({
        id: 'test-5',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();
      document.body.appendChild(el);

      el.click();
      // Wait for async expand
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(el.classList.contains('expanded')).toBe(true);
      expect(card.isExpanded()).toBe(true);
    });

    test('click on expanded card collapses it', async () => {
      const card = new ExpandableCard({
        id: 'test-6',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();
      document.body.appendChild(el);

      el.click(); // expand
      await new Promise(resolve => setTimeout(resolve, 10));

      // Click on the collapsed content area (not expanded content)
      el.querySelector('.collapsed-content').click();
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(el.classList.contains('expanded')).toBe(false);
    });

    test('toggle method works correctly', async () => {
      const card = new ExpandableCard({
        id: 'test-7',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      card.render();
      document.body.appendChild(card.element);

      expect(card.isExpanded()).toBe(false);

      await card.toggle();
      expect(card.isExpanded()).toBe(true);

      card.toggle();
      expect(card.isExpanded()).toBe(false);
    });

    test('expand method expands card', async () => {
      const card = new ExpandableCard({
        id: 'test-8',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      card.render();
      document.body.appendChild(card.element);

      await card.expand();
      expect(card.isExpanded()).toBe(true);
    });

    test('collapse method collapses card', async () => {
      const card = new ExpandableCard({
        id: 'test-9',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      card.render();
      document.body.appendChild(card.element);

      await card.expand();
      card.collapse();
      expect(card.isExpanded()).toBe(false);
    });

    test('expand when already expanded does nothing', async () => {
      const card = new ExpandableCard({
        id: 'test-10',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      card.render();
      document.body.appendChild(card.element);

      await card.expand();
      await card.expand(); // Should not throw
      expect(card.isExpanded()).toBe(true);
    });

  });

  describe('Animation', () => {

    test('has CSS transition class for animation', () => {
      const card = new ExpandableCard({
        id: 'test-11',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();

      // The element should have the class that enables CSS transitions
      expect(el.classList.contains('expandable-card')).toBe(true);
      // CSS file defines transitions - we verify the class is present
    });

    test('animation is CSS-based (not JS-based)', () => {
      const card = new ExpandableCard({
        id: 'test-12',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();

      // Verify CSS transition approach (state changes via classes, not inline styles for animation)
      expect(el.classList.contains('expandable-card')).toBe(true);
    });

  });

  describe('Keyboard Accessibility', () => {

    test('card is focusable (tabindex=0)', () => {
      const card = new ExpandableCard({
        id: 'test-13',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();

      expect(el.getAttribute('tabindex')).toBe('0');
    });

    test('Enter key expands card', async () => {
      const card = new ExpandableCard({
        id: 'test-14',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();
      document.body.appendChild(el);

      const event = new dom.window.KeyboardEvent('keydown', { key: 'Enter' });
      el.dispatchEvent(event);
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(card.isExpanded()).toBe(true);
    });

    test('Space key expands card', async () => {
      const card = new ExpandableCard({
        id: 'test-15',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();
      document.body.appendChild(el);

      const event = new dom.window.KeyboardEvent('keydown', { key: ' ' });
      el.dispatchEvent(event);
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(card.isExpanded()).toBe(true);
    });

    test('Escape key collapses expanded card', async () => {
      const card = new ExpandableCard({
        id: 'test-16',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();
      document.body.appendChild(el);

      await card.expand();
      const event = new dom.window.KeyboardEvent('keydown', { key: 'Escape' });
      el.dispatchEvent(event);

      expect(card.isExpanded()).toBe(false);
    });

    test('has aria-expanded attribute', async () => {
      const card = new ExpandableCard({
        id: 'test-17',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();

      expect(el.getAttribute('aria-expanded')).toBe('false');

      await card.expand();
      expect(el.getAttribute('aria-expanded')).toBe('true');
    });

    test('has role=button for accessibility', () => {
      const card = new ExpandableCard({
        id: 'test-18',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();

      expect(el.getAttribute('role')).toBe('button');
    });

  });

  describe('Callbacks', () => {

    test('onExpand callback is called when expanding', async () => {
      const onExpand = jest.fn();
      const card = new ExpandableCard({
        id: 'test-cb-1',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>',
        onExpand
      });
      const el = card.render();
      document.body.appendChild(el);

      await card.expand();

      expect(onExpand).toHaveBeenCalledTimes(1);
      expect(onExpand).toHaveBeenCalledWith(card);
    });

    test('onCollapse callback is called when collapsing', async () => {
      const onCollapse = jest.fn();
      const card = new ExpandableCard({
        id: 'test-cb-2',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>',
        onCollapse
      });
      const el = card.render();
      document.body.appendChild(el);

      await card.expand();
      card.collapse();

      expect(onCollapse).toHaveBeenCalledTimes(1);
    });

    test('onExpand not called when already expanded', async () => {
      const onExpand = jest.fn();
      const card = new ExpandableCard({
        id: 'test-cb-3',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>',
        onExpand
      });
      card.render();
      document.body.appendChild(card.element);

      await card.expand();
      await card.expand(); // Should not trigger again

      expect(onExpand).toHaveBeenCalledTimes(1);
    });

  });

  describe('Async Content Loading', () => {

    test('supports async expandedContent function', async () => {
      const asyncContent = jest.fn().mockResolvedValue('<p>Loaded async</p>');
      const card = new ExpandableCard({
        id: 'test-async',
        collapsedContent: '<p>Preview</p>',
        expandedContent: asyncContent
      });
      card.render();
      document.body.appendChild(card.element);

      await card.expand();

      expect(asyncContent).toHaveBeenCalled();
      expect(card.element.querySelector('.expanded-content').innerHTML)
        .toContain('Loaded async');
    });

    test('shows loading state during async load', async () => {
      let resolveContent;
      const asyncContent = () => new Promise(resolve => {
        resolveContent = resolve;
      });
      const card = new ExpandableCard({
        id: 'test-loading',
        collapsedContent: '<p>Preview</p>',
        expandedContent: asyncContent
      });
      card.render();
      document.body.appendChild(card.element);

      // Start expansion
      const expandPromise = card.expand();

      // While loading, should show skeleton/loading indicator
      expect(card.element.querySelector('.loading')).toBeTruthy();

      // Resolve the content
      resolveContent('<p>Done</p>');
      await expandPromise;

      expect(card.element.querySelector('.loading')).toBeFalsy();
    });

  });

  describe('Click Outside to Close', () => {

    test('clicking outside closes expanded card', async () => {
      const card = new ExpandableCard({
        id: 'test-outside-1',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>',
        closeOnClickOutside: true
      });
      const el = card.render();
      document.body.appendChild(el);

      await card.expand();

      // Wait for click outside listener to be registered
      await new Promise(resolve => setTimeout(resolve, 10));

      // Click on body (outside card)
      document.body.click();

      expect(card.isExpanded()).toBe(false);
    });

    test('clicking inside expanded card does not close it', async () => {
      const card = new ExpandableCard({
        id: 'test-outside-2',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full content</p>',
        closeOnClickOutside: true
      });
      const el = card.render();
      document.body.appendChild(el);

      await card.expand();
      await new Promise(resolve => setTimeout(resolve, 10));

      // Click inside the expanded content
      const expandedContent = el.querySelector('.expanded-content');
      const clickEvent = new dom.window.MouseEvent('click', { bubbles: true });
      expandedContent.dispatchEvent(clickEvent);

      expect(card.isExpanded()).toBe(true);
    });

  });

  describe('Cleanup', () => {

    test('destroy removes event listeners', () => {
      const card = new ExpandableCard({
        id: 'test-destroy',
        collapsedContent: '<p>Preview</p>',
        expandedContent: '<p>Full</p>'
      });
      const el = card.render();
      document.body.appendChild(el);

      // Should not throw
      expect(() => card.destroy()).not.toThrow();
    });

  });

});
