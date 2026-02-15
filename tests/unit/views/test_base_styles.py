# tests/unit/views/test_base_styles.py
"""
TDD Tests for ACMS Base Styles
Sprint 1: Foundation

These tests verify that the base.css file uses design tokens correctly.
"""

import pytest
import re
from pathlib import Path


class TestBaseStylesDesignTokens:
    """Tests for base.css design token usage."""

    @pytest.fixture
    def base_css(self):
        """Load the base CSS file."""
        css_path = Path(__file__).parent.parent.parent.parent / \
            "desktop-app/src/renderer/styles/base.css"
        if css_path.exists():
            return css_path.read_text()
        return None

    def test_base_css_file_exists(self, base_css):
        """Base CSS file must exist."""
        assert base_css is not None, \
            "base.css not found at desktop-app/src/renderer/styles/"

    def test_uses_font_sans_variable(self, base_css):
        """Body should use --font-sans variable."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")
        assert 'var(--font-sans)' in base_css, \
            "Base CSS should use --font-sans variable"

    def test_uses_bg_app_variable(self, base_css):
        """Body should use --bg-app for background."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")
        assert 'var(--bg-app)' in base_css, \
            "Base CSS should use --bg-app variable"

    def test_uses_text_primary_variable(self, base_css):
        """Should use --text-primary variable."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")
        assert 'var(--text-primary)' in base_css, \
            "Base CSS should use --text-primary variable"

    def test_uses_text_secondary_variable(self, base_css):
        """Should use --text-secondary variable."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")
        assert 'var(--text-secondary)' in base_css, \
            "Base CSS should use --text-secondary variable"

    def test_uses_spacing_variables(self, base_css):
        """Should use spacing variables."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        # Check for various spacing variable usage
        assert 'var(--space-2)' in base_css, "Should use --space-2"
        assert 'var(--space-4)' in base_css, "Should use --space-4"
        assert 'var(--space-6)' in base_css, "Should use --space-6"

    def test_uses_border_variables(self, base_css):
        """Should use border variables."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert 'var(--border-subtle)' in base_css, "Should use --border-subtle"
        assert 'var(--border-default)' in base_css, "Should use --border-default"

    def test_uses_shadow_variables(self, base_css):
        """Should use shadow variables."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert 'var(--shadow-sm)' in base_css or 'var(--card-shadow)' in base_css, \
            "Should use shadow variables"

    def test_uses_radius_variables(self, base_css):
        """Should use border-radius variables."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert 'var(--radius-' in base_css or 'var(--card-radius)' in base_css, \
            "Should use radius variables"

    def test_uses_transition_variables(self, base_css):
        """Should use transition variables."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert 'var(--duration-' in base_css or 'var(--ease-' in base_css, \
            "Should use transition variables"

    def test_no_hardcoded_colors_in_key_elements(self, base_css):
        """Key elements should not use hardcoded colors."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        # Look for hardcoded hex colors in body style
        body_match = re.search(r'body\s*\{([^}]+)\}', base_css, re.DOTALL)
        if body_match:
            body_content = body_match.group(1)
            # Should not have hardcoded colors like #1e1e1e in body
            hardcoded_colors = re.findall(r'#[0-9a-fA-F]{3,6}', body_content)
            assert len(hardcoded_colors) == 0, \
                f"Body should use CSS variables, not hardcoded colors: {hardcoded_colors}"


class TestBaseStylesComponents:
    """Tests for base.css component styles."""

    @pytest.fixture
    def base_css(self):
        """Load the base CSS file."""
        css_path = Path(__file__).parent.parent.parent.parent / \
            "desktop-app/src/renderer/styles/base.css"
        if css_path.exists():
            return css_path.read_text()
        return None

    def test_has_card_styles(self, base_css):
        """Should have card component styles."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.card' in base_css, "Should have .card styles"
        assert 'var(--bg-surface)' in base_css, "Card should use --bg-surface"

    def test_has_button_styles(self, base_css):
        """Should have button component styles."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.btn' in base_css, "Should have .btn styles"
        assert '.btn-primary' in base_css, "Should have .btn-primary styles"
        assert '.btn-secondary' in base_css, "Should have .btn-secondary styles"

    def test_has_input_styles(self, base_css):
        """Should have input component styles."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.input' in base_css, "Should have .input styles"
        assert 'var(--input-' in base_css, "Should use --input-* variables"

    def test_has_badge_styles(self, base_css):
        """Should have badge component styles."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.badge' in base_css, "Should have .badge styles"

    def test_has_memory_card_styles(self, base_css):
        """Should have memory card component styles."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.memory-card' in base_css, "Should have .memory-card styles"

    def test_has_knowledge_card_styles(self, base_css):
        """Should have knowledge card component styles."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.knowledge-card' in base_css, "Should have .knowledge-card styles"

    def test_has_empty_state_styles(self, base_css):
        """Should have empty state styles."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.empty-state' in base_css, "Should have .empty-state styles"

    def test_has_loading_state_styles(self, base_css):
        """Should have loading state styles."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.loading' in base_css, "Should have .loading styles"


class TestBaseStylesUtilities:
    """Tests for base.css utility classes."""

    @pytest.fixture
    def base_css(self):
        """Load the base CSS file."""
        css_path = Path(__file__).parent.parent.parent.parent / \
            "desktop-app/src/renderer/styles/base.css"
        if css_path.exists():
            return css_path.read_text()
        return None

    def test_has_spacing_utilities(self, base_css):
        """Should have spacing utility classes."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.mt-' in base_css, "Should have margin-top utilities"
        assert '.mb-' in base_css, "Should have margin-bottom utilities"
        assert '.p-' in base_css, "Should have padding utilities"

    def test_has_text_color_utilities(self, base_css):
        """Should have text color utility classes."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.text-primary' in base_css, "Should have .text-primary utility"
        assert '.text-secondary' in base_css, "Should have .text-secondary utility"

    def test_has_flex_utilities(self, base_css):
        """Should have flex utility classes."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.flex' in base_css, "Should have .flex utility"
        assert '.items-center' in base_css, "Should have .items-center utility"

    def test_has_rounded_utilities(self, base_css):
        """Should have border-radius utility classes."""
        if base_css is None:
            pytest.skip("Base CSS file not yet created")

        assert '.rounded-' in base_css, "Should have .rounded-* utilities"
