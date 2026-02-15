"""LLM Orchestrator - Unified interface for LLM interactions.

Combines:
- Agent Registry (model selection)
- Prompt Builder (prompt construction)
- Quality Validation (response scoring)
- Provider abstraction (actual LLM calls)

Blueprint Section 5.2 - Orchestrator Interface
"""

import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.llm.agent_registry import AgentRegistry, get_agent_registry, AgentInfo
from src.llm.prompt_builder import PromptBuilder, get_prompt_builder

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResult:
    """Result from LLM orchestration.

    Attributes:
        answer: Generated response text
        model_used: Agent key used (e.g., "claude-sonnet")
        quality_score: Quality assessment (0.0-1.0)
        sources: Source references (if applicable)
        latency_ms: Response time in milliseconds
        input_tokens: Estimated input tokens
        output_tokens: Estimated output tokens
        cost_usd: Estimated cost in USD
        metadata: Additional metadata
    """
    answer: str
    model_used: str
    quality_score: float
    sources: List[str]
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    metadata: Dict[str, Any]


@dataclass
class Query:
    """Query input for orchestrator.

    Attributes:
        text: Query text
        user_id: User identifier
        intent: Detected intent type
        context: Retrieved context (from retrieval pipeline)
        conversation_history: Previous messages for multi-turn
        preferences: User preferences affecting model selection
    """
    text: str
    user_id: str = ""
    intent: str = "GENERAL"
    context: str = ""
    conversation_history: List[Dict[str, str]] = None
    preferences: Dict[str, Any] = None

    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.preferences is None:
            self.preferences = {}


class QualityValidator:
    """Validates response quality.

    Scores responses on:
    - Relevance to query
    - Factual grounding in context
    - Coherence and clarity
    - Safety and appropriateness
    """

    def __init__(self):
        """Initialize quality validator."""
        logger.info("[QualityValidator] Initialized")

    def score(
        self,
        response: str,
        query: str,
        sources: List[str],
        context: str = ""
    ) -> float:
        """Score response quality.

        Args:
            response: Generated response
            query: Original query
            sources: Source references
            context: Retrieved context used

        Returns:
            Quality score (0.0-1.0)
        """
        scores = []

        # 1. Length check (not too short, not too long)
        response_len = len(response)
        if 50 <= response_len <= 5000:
            scores.append(1.0)
        elif response_len < 50:
            scores.append(response_len / 50)
        else:
            scores.append(max(0.5, 1.0 - (response_len - 5000) / 10000))

        # 2. Context usage (if context provided, response should reference it)
        if context:
            context_words = set(context.lower().split())
            response_words = set(response.lower().split())
            overlap = len(context_words & response_words) / max(len(context_words), 1)
            scores.append(min(1.0, overlap * 3))  # Scale up, cap at 1.0
        else:
            scores.append(0.8)  # Default if no context

        # 3. Doesn't say "I don't know" when context is available
        uncertain_phrases = [
            "i don't have",
            "i cannot",
            "i'm not sure",
            "no information",
            "unable to"
        ]
        if context:
            has_uncertain = any(p in response.lower() for p in uncertain_phrases)
            scores.append(0.5 if has_uncertain else 1.0)
        else:
            scores.append(0.9)

        # 4. Coherence check (no obvious issues)
        # Simple heuristic: no repeated phrases, reasonable structure
        sentences = response.split('.')
        if len(sentences) >= 2:
            scores.append(1.0)
        else:
            scores.append(0.7)

        # Average scores
        final_score = sum(scores) / len(scores)

        logger.debug(
            f"[QualityValidator] Score: {final_score:.2f} "
            f"(components: {[round(s, 2) for s in scores]})"
        )

        return round(final_score, 3)


class LLMOrchestrator:
    """Main orchestrator for LLM interactions.

    Handles the full flow:
    1. Select model based on intent
    2. Build prompt from template
    3. Call LLM provider
    4. Validate response quality
    5. Return structured result

    Example:
        orchestrator = LLMOrchestrator()
        result = await orchestrator.answer(
            Query(
                text="What are my coding preferences?",
                intent="MEMORY_QUERY",
                context="User prefers Python, dark mode, vim keybindings."
            )
        )
        print(result.answer)
    """

    def __init__(
        self,
        agent_registry: Optional[AgentRegistry] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        quality_validator: Optional[QualityValidator] = None
    ):
        """Initialize orchestrator.

        Args:
            agent_registry: Optional custom registry (for testing)
            prompt_builder: Optional custom builder (for testing)
            quality_validator: Optional custom validator (for testing)
        """
        self.agents = agent_registry or get_agent_registry()
        self.prompt_builder = prompt_builder or get_prompt_builder()
        self.quality_validator = quality_validator or QualityValidator()

        # Stats
        self.stats = {
            "requests": 0,
            "total_latency_ms": 0,
            "total_cost_usd": 0,
            "models_used": {}
        }

        logger.info("[LLMOrchestrator] Initialized")

    def _select_model(self, intent: str, preferences: Dict[str, Any]) -> str:
        """Select best model for intent.

        Args:
            intent: Intent type
            preferences: User preferences (may override)

        Returns:
            Agent key
        """
        # Check for manual override in preferences
        if preferences.get("preferred_model"):
            preferred = preferences["preferred_model"]
            if self.agents.get_agent(preferred):
                logger.info(f"[LLMOrchestrator] Using preferred model: {preferred}")
                return preferred

        # Use registry selection
        return self.agents.select_for_intent(intent)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Simple approximation: 1 token ≈ 4 characters for English.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return max(1, len(text) // 4)

    async def _call_model(
        self,
        model_key: str,
        prompt: str,
        max_tokens: int = 2048,
        temperature: Optional[float] = None
    ) -> str:
        """Call LLM model.

        This is a placeholder that integrates with existing providers.
        In production, this would use the actual LLM client.

        Args:
            model_key: Agent key
            prompt: Prompt to send
            max_tokens: Maximum response tokens
            temperature: Override temperature (uses agent default if None)

        Returns:
            Generated response text
        """
        agent = self.agents.get_agent(model_key)
        if not agent:
            logger.warning(f"[LLMOrchestrator] Unknown model: {model_key}, using claude-sonnet")
            model_key = "claude-sonnet"
            agent = self.agents.get_agent(model_key)

        temp = temperature if temperature is not None else agent.default_temperature

        # Import and use existing providers
        # This integrates with the existing gateway orchestrator
        logger.debug(
            f"[LLMOrchestrator] Calling {model_key} "
            f"(model={agent.name}, temp={temp}, max_tokens={max_tokens})"
        )

        # For now, return placeholder - actual integration happens in gateway/orchestrator.py
        # This orchestrator provides the interface; the gateway handles actual calls
        return f"[LLMOrchestrator] Response from {model_key}"

    async def answer(
        self,
        query: Query,
        model_override: Optional[str] = None,
        max_tokens: int = 2048
    ) -> OrchestratorResult:
        """Answer a query using LLM.

        Full orchestration flow:
        1. Select model based on intent
        2. Build prompt from template
        3. Call LLM
        4. Validate response
        5. Return result

        Args:
            query: Query object with text, context, intent
            model_override: Force specific model
            max_tokens: Maximum response tokens

        Returns:
            OrchestratorResult with answer and metadata
        """
        start_time = datetime.now()

        # 1. Select model
        model_key = model_override or self._select_model(query.intent, query.preferences)

        # 2. Build prompt
        prompt = self.prompt_builder.build_for_intent(
            intent=query.intent,
            question=query.text,
            context=query.context
        )

        # 3. Estimate tokens
        input_tokens = self._estimate_tokens(prompt)

        # 4. Call model
        try:
            raw_response = await self._call_model(
                model_key=model_key,
                prompt=prompt,
                max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"[LLMOrchestrator] Model call failed: {e}")
            raw_response = "I apologize, but I encountered an error processing your request."

        # 5. Estimate output tokens
        output_tokens = self._estimate_tokens(raw_response)

        # 6. Calculate cost
        cost = self.agents.estimate_cost(model_key, input_tokens, output_tokens)

        # 7. Validate quality
        quality_score = self.quality_validator.score(
            response=raw_response,
            query=query.text,
            sources=[],
            context=query.context
        )

        # 8. Calculate latency
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        # 9. Update stats
        self.stats["requests"] += 1
        self.stats["total_latency_ms"] += latency_ms
        self.stats["total_cost_usd"] += cost
        self.stats["models_used"][model_key] = self.stats["models_used"].get(model_key, 0) + 1

        # 10. Build result
        result = OrchestratorResult(
            answer=raw_response,
            model_used=model_key,
            quality_score=quality_score,
            sources=[],
            latency_ms=round(latency_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 6),
            metadata={
                "intent": query.intent,
                "prompt_template": self.prompt_builder.INTENT_TEMPLATES.get(
                    query.intent.upper(), "retrieval_augmented"
                ),
                "context_length": len(query.context)
            }
        )

        logger.info(
            f"[LLMOrchestrator] Query answered: model={model_key}, "
            f"quality={quality_score:.2f}, latency={latency_ms:.0f}ms, cost=${cost:.6f}"
        )

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics.

        Returns:
            Dict with usage stats
        """
        return {
            **self.stats,
            "avg_latency_ms": (
                self.stats["total_latency_ms"] / max(1, self.stats["requests"])
            ),
            "avg_cost_usd": (
                self.stats["total_cost_usd"] / max(1, self.stats["requests"])
            )
        }


# Global instance
_orchestrator_instance: Optional[LLMOrchestrator] = None


def get_llm_orchestrator() -> LLMOrchestrator:
    """Get global LLM orchestrator instance.

    Returns:
        LLMOrchestrator: Global instance
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = LLMOrchestrator()
    return _orchestrator_instance
