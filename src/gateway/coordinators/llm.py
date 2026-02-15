"""LLM Coordinator - Agent selection, prompt building, and streaming.

Responsibilities:
1. Select appropriate LLM agent based on intent/config
2. Build prompts with context and system instructions
3. Stream responses with circuit breaker protection
4. Handle fallback when primary agent fails

Part of Sprint 2 Architecture & Resilience (Days 6-7).
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, AsyncIterator, List
from enum import Enum

from src.gateway.tracing import get_trace_id
from src.gateway.circuit_breaker import get_circuit_breaker, CircuitOpenError
from src.gateway.coordinators.query_planner import QueryPlan
from src.gateway.coordinators.retrieval import RetrievalResult

logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    """Types of streaming events."""
    STARTED = "started"
    TOKEN = "token"
    THINKING = "thinking"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamEvent:
    """A streaming event from LLM."""
    event_type: StreamEventType
    content: str = ""
    agent: str = ""
    token_count: int = 0
    is_final: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.event_type.value,
            "content": self.content,
            "agent": self.agent,
            "token_count": self.token_count,
            "is_final": self.is_final,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class PromptConfig:
    """Configuration for prompt building."""
    system_prompt: str = ""
    context_template: str = "{context}"
    question_template: str = "{question}"
    max_context_chars: int = 8000
    include_sources: bool = True


class LLMCoordinator:
    """Coordinates LLM agent selection and execution.

    Provides:
    - Agent selection based on intent and availability
    - Prompt building with context injection
    - Streaming with circuit breaker protection
    - Automatic fallback to secondary agents

    Usage:
        coordinator = LLMCoordinator(
            agents={"claude": ClaudeAgent(), "gpt": GPTAgent()},
            agent_selector=get_agent_selector()
        )
        async for event in coordinator.stream(plan, context, user_id):
            handle_event(event)
    """

    def __init__(
        self,
        agents: Optional[Dict[str, Any]] = None,
        agent_selector=None,
        default_agent: str = "claude",
        fallback_agents: Optional[List[str]] = None,
        enable_circuit_breaker: bool = True
    ):
        """Initialize LLM coordinator.

        Args:
            agents: Dictionary of agent_name -> agent instance
            agent_selector: Agent selection service
            default_agent: Default agent to use
            fallback_agents: Ordered list of fallback agents
            enable_circuit_breaker: Whether to use circuit breakers
        """
        self.agents = agents or {}
        self.agent_selector = agent_selector
        self.default_agent = default_agent
        self.fallback_agents = fallback_agents or ["claude", "gpt", "gemini"]
        self.enable_circuit_breaker = enable_circuit_breaker

    async def stream(
        self,
        plan: QueryPlan,
        retrieval_result: RetrievalResult,
        user_id: str,
        preferred_agent: Optional[str] = None,
        prompt_config: Optional[PromptConfig] = None
    ) -> AsyncIterator[StreamEvent]:
        """Stream response from LLM.

        Args:
            plan: Query plan
            retrieval_result: Retrieved context
            user_id: User identifier
            preferred_agent: Preferred agent (overrides selection)
            prompt_config: Prompt configuration

        Yields:
            StreamEvent objects
        """
        trace_id = get_trace_id()
        config = prompt_config or PromptConfig()

        # Select agent
        agent_name = preferred_agent or await self._select_agent(plan)
        agent = self.agents.get(agent_name)

        if not agent:
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                error=f"Agent '{agent_name}' not available",
                agent=agent_name
            )
            return

        # Build prompt
        prompt = self._build_prompt(
            plan.sanitized_query,
            retrieval_result.sanitized_context,
            config
        )

        # Stream with circuit breaker
        yield StreamEvent(
            event_type=StreamEventType.STARTED,
            agent=agent_name,
            metadata={"trace_id": trace_id}
        )

        token_count = 0
        full_response = ""

        try:
            async for chunk in self._stream_with_fallback(
                agent_name,
                agent,
                prompt,
                plan.intent
            ):
                token_count += 1
                full_response += chunk
                yield StreamEvent(
                    event_type=StreamEventType.TOKEN,
                    content=chunk,
                    agent=agent_name,
                    token_count=token_count
                )

            yield StreamEvent(
                event_type=StreamEventType.COMPLETED,
                content=full_response,
                agent=agent_name,
                token_count=token_count,
                is_final=True
            )

        except CircuitOpenError as e:
            logger.warning(f"[{trace_id}] Circuit open for {e.service_name}, trying fallback")
            async for event in self._try_fallback(
                agent_name,
                prompt,
                plan.intent
            ):
                yield event

        except Exception as e:
            logger.error(f"[{trace_id}] LLM error: {e}")
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                error=str(e),
                agent=agent_name
            )

    async def _select_agent(self, plan: QueryPlan) -> str:
        """Select agent based on intent and availability."""
        if self.agent_selector:
            try:
                selected = self.agent_selector.select(plan.intent)
                if hasattr(selected, 'value'):
                    return selected.value
                return str(selected)
            except Exception as e:
                logger.warning(f"[{get_trace_id()}] Agent selection failed: {e}")

        return self.default_agent

    def _build_prompt(
        self,
        question: str,
        context: str,
        config: PromptConfig
    ) -> str:
        """Build prompt with context and question."""
        # Truncate context if needed
        if len(context) > config.max_context_chars:
            context = context[:config.max_context_chars] + "\n[Context truncated...]"

        prompt_parts = []

        if config.system_prompt:
            prompt_parts.append(config.system_prompt)

        if context:
            prompt_parts.append(f"\n{context}\n")

        prompt_parts.append(f"\nQuestion: {question}")

        return "\n".join(prompt_parts)

    async def _stream_with_fallback(
        self,
        agent_name: str,
        agent: Any,
        prompt: str,
        intent: str
    ) -> AsyncIterator[str]:
        """Stream from agent with circuit breaker."""
        if self.enable_circuit_breaker:
            breaker = get_circuit_breaker(
                agent_name,
                failure_threshold=3,
                recovery_timeout=30.0
            )

            # Check if circuit is open before attempting
            if breaker.state.value == "open":
                raise CircuitOpenError(agent_name, 30.0)

        try:
            async for chunk in self._call_agent(agent, prompt, intent):
                yield chunk

            # Record success
            if self.enable_circuit_breaker:
                breaker._on_success()

        except Exception as e:
            if self.enable_circuit_breaker:
                breaker._on_failure(e)
            raise

    async def _call_agent(
        self,
        agent: Any,
        prompt: str,
        intent: str
    ) -> AsyncIterator[str]:
        """Call agent and stream response."""
        # Try different agent interfaces
        if hasattr(agent, 'stream'):
            async for chunk in agent.stream(prompt):
                yield chunk
        elif hasattr(agent, 'generate_stream'):
            async for chunk in agent.generate_stream(prompt):
                yield chunk
        elif hasattr(agent, 'generate'):
            # Non-streaming fallback
            response = await agent.generate(prompt)
            yield response
        else:
            raise ValueError(f"Agent has no streaming interface")

    async def _try_fallback(
        self,
        failed_agent: str,
        prompt: str,
        intent: str
    ) -> AsyncIterator[StreamEvent]:
        """Try fallback agents when primary fails."""
        trace_id = get_trace_id()

        for fallback_name in self.fallback_agents:
            if fallback_name == failed_agent:
                continue

            fallback_agent = self.agents.get(fallback_name)
            if not fallback_agent:
                continue

            logger.info(f"[{trace_id}] Trying fallback agent: {fallback_name}")

            yield StreamEvent(
                event_type=StreamEventType.THINKING,
                content=f"Switching to {fallback_name}...",
                agent=fallback_name
            )

            try:
                token_count = 0
                full_response = ""

                async for chunk in self._call_agent(fallback_agent, prompt, intent):
                    token_count += 1
                    full_response += chunk
                    yield StreamEvent(
                        event_type=StreamEventType.TOKEN,
                        content=chunk,
                        agent=fallback_name,
                        token_count=token_count
                    )

                yield StreamEvent(
                    event_type=StreamEventType.COMPLETED,
                    content=full_response,
                    agent=fallback_name,
                    token_count=token_count,
                    is_final=True
                )
                return

            except Exception as e:
                logger.warning(f"[{trace_id}] Fallback {fallback_name} failed: {e}")
                continue

        # All fallbacks failed
        yield StreamEvent(
            event_type=StreamEventType.ERROR,
            error="All LLM agents unavailable",
            agent="none"
        )

    def get_available_agents(self) -> List[str]:
        """Get list of available agent names."""
        return list(self.agents.keys())

    def get_agent_health(self) -> Dict[str, dict]:
        """Get health status of all agents."""
        health = {}
        for name in self.agents.keys():
            if self.enable_circuit_breaker:
                breaker = get_circuit_breaker(name)
                health[name] = breaker.get_health()
            else:
                health[name] = {"state": "unknown", "circuit_breaker": False}
        return health
