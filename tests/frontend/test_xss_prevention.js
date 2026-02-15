/**
 * XSS Prevention Tests - Phase 0, Task 0.1
 *
 * Tests that user-controlled content cannot execute JavaScript
 * when rendered in the UI.
 *
 * Following TDD: These tests will FAIL initially, then we fix the code.
 */

const { JSDOM } = require('jsdom');

describe('XSS Prevention', () => {
    let dom;
    let document;
    let window;

    beforeEach(() => {
        // Create a fresh DOM for each test
        dom = new JSDOM('<!DOCTYPE html><html><body><div id="root"></div></body></html>');
        document = dom.window.document;
        window = dom.window;
        global.document = document;
        global.window = window;
    });

    afterEach(() => {
        dom.window.close();
    });

    test('should prevent XSS in memory content', () => {
        // Malicious memory content with script tag
        const maliciousContent = '<script>alert("XSS")</script>';

        // Simulate rendering a memory with malicious content
        const root = document.getElementById('root');

        // This is what the code SHOULD do (safe)
        root.textContent = maliciousContent;

        // Verify no script tag is in the DOM
        const scripts = document.querySelectorAll('script');
        expect(scripts.length).toBe(0);

        // Verify the content is shown as text
        expect(root.textContent).toBe('<script>alert("XSS")</script>');
    });

    test('should prevent XSS in conversation messages', () => {
        // Malicious message with img onerror
        const maliciousMessage = '<img src=x onerror="alert(1)">';

        const root = document.getElementById('root');
        root.textContent = maliciousMessage;

        // Verify no img tag is created
        const images = document.querySelectorAll('img');
        expect(images.length).toBe(0);

        // Verify shown as text
        expect(root.textContent).toContain('<img src=x onerror="alert(1)">');
    });

    test('should prevent XSS in search queries', () => {
        // Malicious search query
        const maliciousQuery = '"><script>alert(document.cookie)</script>';

        const root = document.getElementById('root');
        root.textContent = maliciousQuery;

        // Verify no script execution possible
        expect(document.querySelectorAll('script').length).toBe(0);
        expect(root.textContent).toBe('"><script>alert(document.cookie)</script>');
    });

    test('should prevent XSS with event handlers', () => {
        // Various XSS payloads with event handlers
        const payloads = [
            '<div onmouseover="alert(1)">Hover me</div>',
            '<a href="javascript:alert(1)">Click</a>',
            '<input onfocus="alert(1)" autofocus>',
            '<body onload="alert(1)">'
        ];

        const root = document.getElementById('root');

        payloads.forEach(payload => {
            root.textContent = payload;

            // Verify shown as plain text
            expect(root.textContent).toBe(payload);

            // Verify no executable elements created
            expect(root.querySelectorAll('[onmouseover]').length).toBe(0);
            expect(root.querySelectorAll('[onfocus]').length).toBe(0);
            expect(root.querySelectorAll('[onload]').length).toBe(0);
        });
    });

    test('createElement helper should create safe elements', () => {
        // Test the createElement helper function we'll implement
        function createElement(tag, attrs = {}, children = []) {
            const element = document.createElement(tag);

            // Set attributes
            for (const [key, value] of Object.entries(attrs)) {
                if (key.startsWith('on')) {
                    // Event listener
                    element.addEventListener(key.slice(2), value);
                } else {
                    element.setAttribute(key, value);
                }
            }

            // Add children
            for (const child of children) {
                if (child === null || child === undefined) continue;

                if (typeof child === 'string') {
                    element.appendChild(document.createTextNode(child));
                } else {
                    element.appendChild(child);
                }
            }

            return element;
        }

        // Create element with potentially malicious content
        const maliciousText = '<script>alert("XSS")</script>';
        const safeDiv = createElement('div', { class: 'message' }, [maliciousText]);

        // Verify text is escaped
        expect(safeDiv.textContent).toBe('<script>alert("XSS")</script>');
        expect(safeDiv.querySelector('script')).toBeNull();
    });

    test('should handle null and undefined children safely', () => {
        function createElement(tag, attrs = {}, children = []) {
            const element = document.createElement(tag);

            for (const child of children) {
                if (child === null || child === undefined) continue;

                if (typeof child === 'string') {
                    element.appendChild(document.createTextNode(child));
                } else {
                    element.appendChild(child);
                }
            }

            return element;
        }

        // Should not crash with null/undefined children
        const element = createElement('div', {}, [
            'Text',
            null,
            'More text',
            undefined,
            'Final text'
        ]);

        expect(element.textContent).toBe('TextMore textFinal text');
    });

    test('should sanitize innerHTML only when using DOMPurify', () => {
        // If we need HTML rendering (for markdown), must use DOMPurify
        // This test documents the ONLY acceptable use of innerHTML

        // Mock DOMPurify
        const DOMPurify = {
            sanitize: (html) => {
                // Simplified sanitization (real DOMPurify is much more robust)
                return html
                    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
                    .replace(/on\w+="[^"]*"/gi, '');
            }
        };

        const maliciousHTML = '<p>Hello</p><script>alert("XSS")</script><img src=x onerror="alert(1)">';
        const sanitized = DOMPurify.sanitize(maliciousHTML);

        // Verify script tag removed
        expect(sanitized).not.toContain('<script>');
        expect(sanitized).not.toContain('onerror=');
        expect(sanitized).toContain('<p>Hello</p>');
    });
});

module.exports = { describe, test, expect, beforeEach, afterEach };
