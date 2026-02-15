"""Prompt Builder - Loads and renders prompt templates.

Separates prompt content from code for easy iteration.
Templates use {{ variable }} syntax (Jinja2-like).

Blueprint Section 5.3 - Prompt Templates
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Default prompts directory
PROMPTS_DIR = Path(__file__).parent / "prompts"


class PromptBuilder:
    """Builds prompts from templates.

    Loads templates from files and renders them with variables.
    Supports template inheritance and fallbacks.

    Example:
        builder = PromptBuilder()
        prompt = builder.build(
            template_name="retrieval_augmented",
            question="What are my coding preferences?",
            context="User prefers Python, dark mode, vim keybindings."
        )
    """

    # Intent → template mapping
    INTENT_TEMPLATES = {
        "MEMORY_QUERY": "memory_synthesis",
        "ANALYSIS": "analysis",
        "CREATIVE": "creative",
        "CODE_GENERATION": "code_generation",
        "RESEARCH": "retrieval_augmented",
        "TERMINAL_COMMAND": "code_generation",
        "FILE_OPERATION": "code_generation",
    }

    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize prompt builder.

        Args:
            prompts_dir: Custom prompts directory (for testing)
        """
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._cache: Dict[str, str] = {}

        logger.info(f"[PromptBuilder] Initialized with prompts_dir: {self.prompts_dir}")

    @lru_cache(maxsize=20)
    def _load_template(self, template_name: str) -> str:
        """Load template from file (cached).

        Args:
            template_name: Template name (without .txt extension)

        Returns:
            Template content

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        template_path = self.prompts_dir / f"{template_name}.txt"

        if not template_path.exists():
            logger.warning(f"[PromptBuilder] Template not found: {template_path}")
            # Fall back to retrieval_augmented
            fallback_path = self.prompts_dir / "retrieval_augmented.txt"
            if fallback_path.exists():
                template_path = fallback_path
            else:
                raise FileNotFoundError(f"Template not found: {template_name}")

        with open(template_path, 'r') as f:
            content = f.read()

        logger.debug(f"[PromptBuilder] Loaded template: {template_name}")
        return content

    def _render(self, template: str, **variables) -> str:
        """Render template with variables.

        Uses {{ variable }} syntax.

        Args:
            template: Template string
            **variables: Variables to substitute

        Returns:
            Rendered string
        """
        result = template

        for key, value in variables.items():
            pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
            result = re.sub(pattern, str(value), result)

        return result

    def build(
        self,
        template_name: str,
        question: str,
        context: str = "",
        **extra_vars
    ) -> str:
        """Build prompt from template.

        Args:
            template_name: Template to use
            question: User's question
            context: Retrieved context (can be empty)
            **extra_vars: Additional template variables

        Returns:
            Rendered prompt string
        """
        template = self._load_template(template_name)

        # Prepare variables
        variables = {
            "question": question,
            "context": context or "(No relevant context found)",
            **extra_vars
        }

        prompt = self._render(template, **variables)

        logger.debug(
            f"[PromptBuilder] Built prompt from '{template_name}', "
            f"question_len={len(question)}, context_len={len(context)}"
        )

        return prompt

    def build_for_intent(
        self,
        intent: str,
        question: str,
        context: str = "",
        **extra_vars
    ) -> str:
        """Build prompt using intent-based template selection.

        Args:
            intent: Intent type (ANALYSIS, CREATIVE, etc.)
            question: User's question
            context: Retrieved context
            **extra_vars: Additional template variables

        Returns:
            Rendered prompt string
        """
        template_name = self.INTENT_TEMPLATES.get(
            intent.upper(),
            "retrieval_augmented"  # Default
        )

        logger.debug(f"[PromptBuilder] Intent '{intent}' → template '{template_name}'")

        return self.build(
            template_name=template_name,
            question=question,
            context=context,
            **extra_vars
        )

    def list_templates(self) -> list:
        """List available templates.

        Returns:
            List of template names (without .txt extension)
        """
        templates = []
        if self.prompts_dir.exists():
            for f in self.prompts_dir.glob("*.txt"):
                templates.append(f.stem)
        return sorted(templates)

    def clear_cache(self):
        """Clear template cache."""
        self._load_template.cache_clear()
        logger.debug("[PromptBuilder] Cache cleared")


# Global instance
_builder_instance: Optional[PromptBuilder] = None


def get_prompt_builder() -> PromptBuilder:
    """Get global prompt builder instance.

    Returns:
        PromptBuilder: Global instance
    """
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = PromptBuilder()
    return _builder_instance
