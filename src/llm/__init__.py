"""
LLM Provider Abstraction Layer

Provides a unified interface for multiple LLM providers:
- ChatGPT (gpt-5.1, gpt-4o-mini)
- Ollama (local LLMs)
- Claude (via existing ClaudeGenerator)

Components:
- Providers: Abstract LLM interfaces
- Agent Registry: Model capabilities and costs
- Prompt Builder: Template-based prompt construction
- Orchestrator: Unified LLM interaction interface

This allows easy switching between providers for different use cases:
- Query rewriting: ChatGPT (cheap, fast)
- Complex reasoning: Claude (high quality)
- Local/offline: Ollama (privacy, cost)
"""

from .providers import (
    LLMProvider,
    ChatGPTProvider,
    OllamaProvider,
    ClaudeProvider,
    create_llm_provider
)

from .agent_registry import (
    AgentInfo,
    AgentRegistry,
    ModelProvider,
    AGENTS,
    get_agent_registry
)

from .prompt_builder import (
    PromptBuilder,
    get_prompt_builder
)

from .orchestrator import (
    LLMOrchestrator,
    OrchestratorResult,
    Query,
    QualityValidator,
    get_llm_orchestrator
)

__all__ = [
    # Providers
    "LLMProvider",
    "ChatGPTProvider",
    "OllamaProvider",
    "ClaudeProvider",
    "create_llm_provider",
    # Agent Registry
    "AgentInfo",
    "AgentRegistry",
    "ModelProvider",
    "AGENTS",
    "get_agent_registry",
    # Prompt Builder
    "PromptBuilder",
    "get_prompt_builder",
    # Orchestrator
    "LLMOrchestrator",
    "OrchestratorResult",
    "Query",
    "QualityValidator",
    "get_llm_orchestrator",
]
