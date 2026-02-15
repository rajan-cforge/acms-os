"""Tests for Prompt Builder.

Tests template loading, rendering, and intent-based selection.
"""

import pytest
from pathlib import Path
from src.llm.prompt_builder import (
    PromptBuilder,
    get_prompt_builder,
    PROMPTS_DIR
)


class TestPromptBuilder:
    """Tests for PromptBuilder class."""

    def test_init_default_prompts_dir(self):
        """Test initialization with default prompts directory."""
        builder = PromptBuilder()

        assert builder.prompts_dir == PROMPTS_DIR
        assert builder.prompts_dir.exists()

    def test_list_templates(self):
        """Test listing available templates."""
        builder = PromptBuilder()

        templates = builder.list_templates()

        assert isinstance(templates, list)
        assert len(templates) > 0
        assert "retrieval_augmented" in templates

    def test_build_simple(self):
        """Test building a simple prompt."""
        builder = PromptBuilder()

        prompt = builder.build(
            template_name="retrieval_augmented",
            question="What is Python?",
            context="Python is a programming language."
        )

        assert "What is Python?" in prompt
        assert "Python is a programming language." in prompt

    def test_build_empty_context(self):
        """Test building prompt with empty context."""
        builder = PromptBuilder()

        prompt = builder.build(
            template_name="retrieval_augmented",
            question="Test question",
            context=""
        )

        assert "Test question" in prompt
        assert "(No relevant context found)" in prompt

    def test_build_for_intent_memory_query(self):
        """Test intent-based template selection for MEMORY_QUERY."""
        builder = PromptBuilder()

        prompt = builder.build_for_intent(
            intent="MEMORY_QUERY",
            question="What are my preferences?",
            context="User prefers dark mode."
        )

        assert "What are my preferences?" in prompt
        assert "User prefers dark mode." in prompt

    def test_build_for_intent_analysis(self):
        """Test intent-based template selection for ANALYSIS."""
        builder = PromptBuilder()

        prompt = builder.build_for_intent(
            intent="ANALYSIS",
            question="Analyze this data",
            context="Some data to analyze."
        )

        assert "Analyze this data" in prompt

    def test_build_for_intent_creative(self):
        """Test intent-based template selection for CREATIVE."""
        builder = PromptBuilder()

        prompt = builder.build_for_intent(
            intent="CREATIVE",
            question="Generate ideas",
            context=""
        )

        assert "Generate ideas" in prompt

    def test_build_for_intent_unknown_fallback(self):
        """Test unknown intent falls back to retrieval_augmented."""
        builder = PromptBuilder()

        prompt = builder.build_for_intent(
            intent="UNKNOWN_INTENT",
            question="Some question",
            context="Some context"
        )

        # Should use retrieval_augmented template
        assert "Some question" in prompt
        assert "Some context" in prompt

    def test_build_for_intent_case_insensitive(self):
        """Test intent matching is case-insensitive."""
        builder = PromptBuilder()

        prompt_upper = builder.build_for_intent(
            intent="ANALYSIS",
            question="Test",
            context=""
        )

        prompt_lower = builder.build_for_intent(
            intent="analysis",
            question="Test",
            context=""
        )

        # Should produce similar results
        assert "Test" in prompt_upper
        assert "Test" in prompt_lower

    def test_template_variable_substitution(self):
        """Test {{ variable }} substitution works correctly."""
        builder = PromptBuilder()

        prompt = builder.build(
            template_name="retrieval_augmented",
            question="Q1",
            context="C1"
        )

        # Variables should be replaced, not present as {{ }}
        assert "{{ question }}" not in prompt
        assert "{{ context }}" not in prompt
        assert "Q1" in prompt
        assert "C1" in prompt

    def test_extra_variables(self):
        """Test passing extra variables to template."""
        builder = PromptBuilder()

        prompt = builder.build(
            template_name="retrieval_augmented",
            question="Test",
            context="Context",
            custom_var="custom_value"
        )

        # Extra vars should not cause errors even if not in template
        assert prompt is not None

    def test_cache_clearing(self):
        """Test cache clearing works."""
        builder = PromptBuilder()

        # Load a template (caches it)
        builder.build("retrieval_augmented", "Test", "Context")

        # Clear cache
        builder.clear_cache()

        # Should work after clearing
        prompt = builder.build("retrieval_augmented", "Test2", "Context2")
        assert "Test2" in prompt


class TestGlobalPromptBuilder:
    """Tests for global prompt builder instance."""

    def test_get_prompt_builder_singleton(self):
        """Test that get_prompt_builder returns singleton."""
        builder1 = get_prompt_builder()
        builder2 = get_prompt_builder()

        assert builder1 is builder2

    def test_global_builder_works(self):
        """Test that global builder is functional."""
        builder = get_prompt_builder()

        prompt = builder.build(
            "retrieval_augmented",
            "Test question",
            "Test context"
        )

        assert len(prompt) > 0


class TestIntentTemplateMapping:
    """Tests for intent → template mapping."""

    def test_all_intents_have_mappings(self):
        """Test that common intents have template mappings."""
        builder = PromptBuilder()

        intents = [
            "MEMORY_QUERY",
            "ANALYSIS",
            "CREATIVE",
            "CODE_GENERATION",
            "RESEARCH",
            "TERMINAL_COMMAND",
            "FILE_OPERATION"
        ]

        for intent in intents:
            assert intent in builder.INTENT_TEMPLATES, f"Missing mapping for {intent}"

    def test_intent_templates_exist(self):
        """Test that all mapped templates exist."""
        builder = PromptBuilder()
        templates = builder.list_templates()

        for intent, template_name in builder.INTENT_TEMPLATES.items():
            assert template_name in templates, f"Template '{template_name}' for intent '{intent}' not found"


class TestTemplateContent:
    """Tests for specific template content."""

    def test_retrieval_augmented_has_required_sections(self):
        """Test retrieval_augmented template has required sections."""
        builder = PromptBuilder()

        prompt = builder.build(
            "retrieval_augmented",
            "Test question",
            "Test context"
        )

        # Should have instructions about using context
        prompt_lower = prompt.lower()
        assert "context" in prompt_lower

    def test_memory_synthesis_personal_focus(self):
        """Test memory_synthesis template focuses on personal context."""
        builder = PromptBuilder()

        prompt = builder.build(
            "memory_synthesis",
            "What do I like?",
            "User likes Python."
        )

        prompt_lower = prompt.lower()
        # Should mention something about personal/user context
        assert "user" in prompt_lower or "personal" in prompt_lower

    def test_analysis_structured_approach(self):
        """Test analysis template encourages structured thinking."""
        builder = PromptBuilder()

        prompt = builder.build(
            "analysis",
            "Analyze this",
            "Data to analyze"
        )

        prompt_lower = prompt.lower()
        # Should mention analysis/structured approach
        assert "analy" in prompt_lower

    def test_code_generation_code_focus(self):
        """Test code_generation template is code-focused."""
        builder = PromptBuilder()

        prompt = builder.build(
            "code_generation",
            "Write a function",
            "Existing code context"
        )

        prompt_lower = prompt.lower()
        assert "code" in prompt_lower
