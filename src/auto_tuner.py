"""
Auto-Tuning System for ACMS

Automatically adjusts system behavior based on user feedback data.
Implements self-improving AI that learns from 418+ conversations and feedback.

Key Features:
- Cache quality monitoring (disable if rating < 3.0)
- Model selection tuning (route to best-performing model)
- Context optimization (adjust limits based on feedback patterns)

Usage:
    auto_tuner = AutoTuner()
    await auto_tuner.initialize()

    # Run analysis
    action = await auto_tuner.analyze_feedback()
    if action:
        await auto_tuner.apply_tuning(action)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import statistics

from src.storage.database import get_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class TuningDecision:
    """Represents an auto-tuning decision"""
    action: str
    reason: str
    old_value: Any
    new_value: Any
    confidence: float
    timestamp: datetime


class AutoTuner:
    """
    Automatically adjust ACMS behavior based on feedback data.

    Analyzes user feedback to detect quality issues and optimize:
    - Semantic cache performance
    - Model selection and routing
    - Context limits and source counts

    Rules:
    1. Cache Quality: Disable cache if avg rating < 3.0 stars
    2. Model Routing: Switch to highest-rated model
    3. Context Limits: Adjust based on "too many sources" feedback
    """

    def __init__(self):
        """Initialize Auto-Tuner"""
        self.tuning_log: List[TuningDecision] = []
        self.config_overrides: Dict[str, Any] = {}

    async def initialize(self):
        """Initialize database connection"""
        logger.info("[AutoTuner] Initialized")

    async def analyze_feedback(self) -> Optional[TuningDecision]:
        """
        Analyze user feedback to detect quality issues.

        Returns:
            TuningDecision if action needed, None otherwise
        """
        logger.info("[AutoTuner] Analyzing feedback data...")

        # Rule 1: Cache Quality Monitor
        cache_decision = await self._analyze_cache_quality()
        if cache_decision:
            return cache_decision

        # Rule 2: Model Selection Tuning
        model_decision = await self._analyze_model_performance()
        if model_decision:
            return model_decision

        # Rule 3: Context Optimization
        context_decision = await self._analyze_context_patterns()
        if context_decision:
            return context_decision

        logger.info("[AutoTuner] No tuning actions needed")
        return None

    async def _analyze_cache_quality(self) -> Optional[TuningDecision]:
        """
        Rule 1: Cache Quality Monitor

        Disable semantic cache if average rating < 3.0 stars
        """
        async with get_session() as session:
            # Get feedback for semantic cache sources
            query = text("""
                SELECT
                    AVG(rating) as avg_rating,
                    COUNT(*) as feedback_count
                FROM user_feedback
                WHERE source_info->>'source' = 'semantic_cache'
                AND rating IS NOT NULL
                AND created_at > NOW() - INTERVAL '30 days'
            """)

            result = await session.execute(query)
            row = result.fetchone()

            if not row or row.feedback_count == 0:
                logger.debug("[AutoTuner] No cache feedback data available")
                return None

            avg_rating = float(row.avg_rating) if row.avg_rating else 0.0
            feedback_count = int(row.feedback_count)

            logger.info(f"[AutoTuner] Cache quality: {avg_rating:.2f}/5.0 ({feedback_count} ratings)")

            # Decision threshold: < 3.0 stars = disable cache
            if avg_rating < 3.0 and feedback_count >= 5:
                return TuningDecision(
                    action="disable_semantic_cache",
                    reason=f"Cache quality below threshold: {avg_rating:.2f}/5.0 (n={feedback_count})",
                    old_value=True,
                    new_value=False,
                    confidence=min(feedback_count / 10.0, 1.0),  # Higher confidence with more data
                    timestamp=datetime.utcnow()
                )

        return None

    async def _analyze_model_performance(self) -> Optional[TuningDecision]:
        """
        Rule 2: Model Selection Tuning

        Route to best-performing model based on ratings
        """
        async with get_session() as session:
            # Get average rating by model
            query = text("""
                SELECT
                    source_info->>'model' as model_name,
                    AVG(rating) as avg_rating,
                    COUNT(*) as feedback_count
                FROM user_feedback
                WHERE source_info->>'model' IS NOT NULL
                AND rating IS NOT NULL
                AND created_at > NOW() - INTERVAL '30 days'
                GROUP BY source_info->>'model'
                HAVING COUNT(*) >= 3
                ORDER BY AVG(rating) DESC
            """)

            result = await session.execute(query)
            models = result.fetchall()

            if len(models) < 2:
                logger.debug("[AutoTuner] Insufficient model data for comparison")
                return None

            # Best and current model
            best_model = models[0]
            best_rating = float(best_model.avg_rating)
            best_name = best_model.model_name

            logger.info(f"[AutoTuner] Model ratings:")
            for model in models:
                logger.info(f"  {model.model_name}: {float(model.avg_rating):.2f}/5.0 (n={model.feedback_count})")

            # Decision: Switch if best model is significantly better (>0.5 stars)
            current_model = "claude-sonnet-4.5"  # Default
            current_rating = next((float(m.avg_rating) for m in models if m.model_name == current_model), None)

            if current_rating and best_rating - current_rating > 0.5:
                return TuningDecision(
                    action="switch_model",
                    reason=f"{best_name} rated {best_rating:.2f} vs {current_model} {current_rating:.2f}",
                    old_value=current_model,
                    new_value=best_name,
                    confidence=min(best_model.feedback_count / 20.0, 1.0),
                    timestamp=datetime.utcnow()
                )

        return None

    async def _analyze_context_patterns(self) -> Optional[TuningDecision]:
        """
        Rule 3: Context Optimization

        Adjust context limit based on feedback patterns
        """
        async with get_session() as session:
            # Get feedback comments mentioning "too many" or "too few"
            query = text("""
                SELECT
                    COUNT(CASE WHEN comment ILIKE '%too many%' THEN 1 END) as too_many_count,
                    COUNT(CASE WHEN comment ILIKE '%too few%' THEN 1 END) as too_few_count,
                    COUNT(*) as total_feedback
                FROM user_feedback
                WHERE comment IS NOT NULL
                AND created_at > NOW() - INTERVAL '30 days'
            """)

            result = await session.execute(query)
            row = result.fetchone()

            if not row or row.total_feedback == 0:
                logger.debug("[AutoTuner] No context feedback data available")
                return None

            too_many = int(row.too_many_count)
            too_few = int(row.too_few_count)
            total = int(row.total_feedback)

            too_many_pct = (too_many / total) * 100 if total > 0 else 0
            too_few_pct = (too_few / total) * 100 if total > 0 else 0

            logger.info(f"[AutoTuner] Context feedback: {too_many_pct:.1f}% too many, {too_few_pct:.1f}% too few (n={total})")

            current_limit = 10  # Default context limit

            # Decision: Adjust if > 20% complain
            if too_many_pct > 20 and too_many >= 5:
                return TuningDecision(
                    action="reduce_context_limit",
                    reason=f"{too_many_pct:.1f}% feedback says 'too many sources' (n={too_many})",
                    old_value=current_limit,
                    new_value=max(current_limit - 2, 5),  # Reduce by 2, min 5
                    confidence=min(too_many / 10.0, 1.0),
                    timestamp=datetime.utcnow()
                )
            elif too_few_pct > 20 and too_few >= 5:
                return TuningDecision(
                    action="increase_context_limit",
                    reason=f"{too_few_pct:.1f}% feedback says 'too few sources' (n={too_few})",
                    old_value=current_limit,
                    new_value=min(current_limit + 2, 20),  # Increase by 2, max 20
                    confidence=min(too_few / 10.0, 1.0),
                    timestamp=datetime.utcnow()
                )

        return None

    async def apply_tuning(self, decision: TuningDecision):
        """
        Apply tuning decision and log for transparency.

        Args:
            decision: TuningDecision to apply
        """
        logger.info(f"[AutoTuner] Applying decision: {decision.action}")
        logger.info(f"  Reason: {decision.reason}")
        logger.info(f"  Change: {decision.old_value} → {decision.new_value}")
        logger.info(f"  Confidence: {decision.confidence:.1%}")

        # Apply the decision
        if decision.action == "disable_semantic_cache":
            self.config_overrides['semantic_cache_enabled'] = False
            logger.warning("[AutoTuner] ⚠️  Semantic cache DISABLED due to low ratings")

        elif decision.action == "switch_model":
            self.config_overrides['default_model'] = decision.new_value
            logger.info(f"[AutoTuner] ✅ Model routing switched to: {decision.new_value}")

        elif decision.action == "reduce_context_limit":
            self.config_overrides['context_limit'] = decision.new_value
            logger.info(f"[AutoTuner] ✅ Context limit reduced to: {decision.new_value}")

        elif decision.action == "increase_context_limit":
            self.config_overrides['context_limit'] = decision.new_value
            logger.info(f"[AutoTuner] ✅ Context limit increased to: {decision.new_value}")

        # Store decision in audit log
        await self._log_tuning_decision(decision)

        # Add to in-memory log
        self.tuning_log.append(decision)

    async def _log_tuning_decision(self, decision: TuningDecision):
        """Store tuning decision in database for audit trail"""
        async with get_session() as session:
            query = text("""
                INSERT INTO auto_tuning_log
                (action, reason, old_value, new_value, confidence, created_at)
                VALUES (:action, :reason, :old_value, :new_value, :confidence, :created_at)
            """)

            try:
                await session.execute(query, {
                    'action': decision.action,
                    'reason': decision.reason,
                    'old_value': str(decision.old_value),
                    'new_value': str(decision.new_value),
                    'confidence': decision.confidence,
                    'created_at': decision.timestamp
                })
                await session.commit()
                logger.debug("[AutoTuner] Decision logged to database")
            except Exception as e:
                # Table might not exist yet - that's okay
                logger.debug(f"[AutoTuner] Could not log to database (table may not exist): {e}")

    def get_config_override(self, key: str, default: Any = None) -> Any:
        """
        Get configuration override if set by auto-tuner.

        Args:
            key: Configuration key
            default: Default value if not overridden

        Returns:
            Overridden value or default
        """
        return self.config_overrides.get(key, default)

    def get_tuning_history(self) -> List[TuningDecision]:
        """Get history of tuning decisions"""
        return self.tuning_log.copy()


# Singleton instance for use across application
_auto_tuner_instance: Optional[AutoTuner] = None


def get_auto_tuner() -> AutoTuner:
    """Get singleton AutoTuner instance"""
    global _auto_tuner_instance
    if _auto_tuner_instance is None:
        _auto_tuner_instance = AutoTuner()
    return _auto_tuner_instance
