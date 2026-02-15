"""AI agent wrappers for Gateway.

Available agents (Dec 2025 - Latest Models):
- ClaudeSonnetAgent: Claude Opus 4.5 - Premium tier for complex analysis, software engineering
- ChatGPTAgent: GPT-5.1 - Adaptive reasoning for creative and coding tasks
- GeminiAgent: Gemini 3 Pro - 1M context, Deep Research, multimodal
- ClaudeCodeAgent: Terminal commands, code generation (stub for Week 4)
"""

from src.gateway.agents.base_agent import BaseAgent
from src.gateway.agents.claude_sonnet import ClaudeSonnetAgent
from src.gateway.agents.chatgpt import ChatGPTAgent
from src.gateway.agents.gemini import GeminiAgent
from src.gateway.agents.claude_code import ClaudeCodeAgent

__all__ = [
    "BaseAgent",
    "ClaudeSonnetAgent",
    "ChatGPTAgent",
    "GeminiAgent",
    "ClaudeCodeAgent"
]
