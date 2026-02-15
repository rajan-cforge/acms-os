"""Claude Code agent wrapper (STUB for Week 4).

Best for: Terminal commands, code generation, file operations.
Requires terminal execution capabilities - will be fully implemented in Week 4.
"""

from typing import AsyncIterator, Optional
import logging
from src.gateway.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ClaudeCodeAgent(BaseAgent):
    """Claude Code agent - Terminal commands and code generation (STUB)."""

    def __init__(self):
        """Initialize Claude Code agent stub."""
        super().__init__("Claude Code (Stub)")

        # Pricing (same as Claude Sonnet)
        self.cost_per_1m_input_tokens = 3.0
        self.cost_per_1m_output_tokens = 15.0

        logger.warning(
            "ClaudeCodeAgent is a STUB implementation. "
            "Full terminal execution will be added in Week 4."
        )

    async def generate(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate stub response (Week 4 TODO).

        Args:
            query: User question/prompt
            context: Optional context from memory system
            **kwargs: Additional parameters

        Yields:
            str: Stub response explaining Week 4 implementation
        """
        logger.info(f"Claude Code stub called with query: {query[:50]}...")

        # For now, return a placeholder response
        stub_response = f"""[Claude Code Agent - Stub Implementation]

Query detected: {query[:100]}

This is a placeholder response. The full Claude Code agent will be implemented in Week 4 with:
- Terminal command execution
- Code generation capabilities
- File operation support
- Integration with ACMS Desktop terminal

For now, terminal/code/file operations are routed here but not executed.

Week 4 Implementation Tasks:
1. Terminal command parser
2. Safe command execution sandbox
3. Code generation with validation
4. File operation handlers
5. Desktop app terminal integration

Status: STUB - Week 4 TODO
"""

        yield stub_response

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for Claude Code query.

        Args:
            input_tokens: Estimated input token count
            output_tokens: Estimated output token count

        Returns:
            float: Estimated cost in USD (same pricing as Claude Sonnet)
        """
        input_cost = (input_tokens / 1_000_000) * self.cost_per_1m_input_tokens
        output_cost = (output_tokens / 1_000_000) * self.cost_per_1m_output_tokens
        total_cost = input_cost + output_cost

        return round(total_cost, 6)

    def get_metadata(self) -> dict:
        """Get Claude Code metadata.

        Returns:
            dict: Agent capabilities and pricing
        """
        return {
            "agent_name": self.agent_name,
            "model": "claude-sonnet-4-5 (with tool execution)",
            "supports_streaming": True,
            "supports_context": True,
            "max_tokens": 8192,
            "best_for": ["terminal_command", "code_generation", "file_operation"],
            "cost_per_1m_input": self.cost_per_1m_input_tokens,
            "cost_per_1m_output": self.cost_per_1m_output_tokens,
            "average_latency_ms": 3500,
            "status": "STUB - Week 4 implementation",
            "note": "Full terminal execution coming in Week 4"
        }
