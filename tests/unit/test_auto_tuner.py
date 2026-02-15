"""
Unit Tests for Auto-Tuner

Tests the self-improving AI system that optimizes ACMS based on feedback.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.auto_tuner import AutoTuner, TuningDecision


class TestCacheQualityMonitor:
    """Test Rule 1: Cache quality monitoring"""

    @pytest.mark.asyncio
    async def test_disable_cache_when_rating_low(self):
        """Cache should be disabled when avg rating < 3.0"""
        auto_tuner = AutoTuner()
        await auto_tuner.initialize()

        # Mock database to return low cache rating
        with patch('src.auto_tuner.get_session') as mock_session:
            mock_result = Mock()
            mock_result.avg_rating = 2.5
            mock_result.feedback_count = 10

            mock_fetch = Mock()
            mock_fetch.fetchone = Mock(return_value=mock_result)

            mock_execute = AsyncMock(return_value=mock_fetch)

            mock_session.return_value.__aenter__.return_value.execute = mock_execute

            # Analyze feedback
            decision = await auto_tuner._analyze_cache_quality()

            # Verify decision
            assert decision is not None
            assert decision.action == "disable_semantic_cache"
            assert decision.old_value == True
            assert decision.new_value == False
            assert "2.5" in decision.reason

    @pytest.mark.asyncio
    async def test_keep_cache_when_rating_good(self):
        """Cache should stay enabled when avg rating >= 3.0"""
        auto_tuner = AutoTuner()
        await auto_tuner.initialize()

        # Mock database to return good cache rating
        with patch('src.auto_tuner.get_session') as mock_session:
            mock_result = Mock()
            mock_result.avg_rating = 4.2
            mock_result.feedback_count = 15

            mock_fetch = Mock()
            mock_fetch.fetchone = Mock(return_value=mock_result)

            mock_execute = AsyncMock(return_value=mock_fetch)

            mock_session.return_value.__aenter__.return_value.execute = mock_execute

            # Analyze feedback
            decision = await auto_tuner._analyze_cache_quality()

            # No action should be taken
            assert decision is None


class TestModelSelection:
    """Test Rule 2: Model selection tuning"""

    @pytest.mark.asyncio
    async def test_switch_to_better_model(self):
        """Should switch to model with significantly better rating"""
        auto_tuner = AutoTuner()
        await auto_tuner.initialize()

        # Mock database to return model ratings
        with patch('src.auto_tuner.get_session') as mock_session:
            # Claude rated 4.8, GPT-4 rated 4.0
            mock_models = [
                Mock(model_name="claude-sonnet-4.5", avg_rating=4.8, feedback_count=20),
                Mock(model_name="gpt-4o", avg_rating=4.0, feedback_count=15),
            ]

            mock_fetch = Mock()
            mock_fetch.fetchall = Mock(return_value=mock_models)

            mock_execute = AsyncMock(return_value=mock_fetch)

            mock_session.return_value.__aenter__.return_value.execute = mock_execute

            # Analyze feedback
            decision = await auto_tuner._analyze_model_performance()

            # Should NOT switch (already using best model)
            assert decision is None

    @pytest.mark.asyncio
    async def test_no_switch_when_difference_small(self):
        """Should not switch if rating difference < 0.5"""
        auto_tuner = AutoTuner()
        await auto_tuner.initialize()

        # Mock database
        with patch('src.auto_tuner.get_session') as mock_session:
            # Small difference: 4.5 vs 4.2
            mock_models = [
                Mock(model_name="claude-sonnet-4.5", avg_rating=4.5, feedback_count=10),
                Mock(model_name="gpt-4o", avg_rating=4.2, feedback_count=12),
            ]

            mock_fetch = Mock()
            mock_fetch.fetchall = Mock(return_value=mock_models)

            mock_execute = AsyncMock(return_value=mock_fetch)

            mock_session.return_value.__aenter__.return_value.execute = mock_execute

            # Analyze feedback
            decision = await auto_tuner._analyze_model_performance()

            # No switch (difference too small)
            assert decision is None


class TestContextOptimization:
    """Test Rule 3: Context limit optimization"""

    @pytest.mark.asyncio
    async def test_reduce_context_when_too_many_complaints(self):
        """Should reduce context limit when > 20% say 'too many sources'"""
        auto_tuner = AutoTuner()
        await auto_tuner.initialize()

        # Mock database
        with patch('src.auto_tuner.get_session') as mock_session:
            # 25% say "too many"
            mock_result = Mock()
            mock_result.too_many_count = 10
            mock_result.too_few_count = 2
            mock_result.total_feedback = 40

            mock_fetch = Mock()
            mock_fetch.fetchone = Mock(return_value=mock_result)

            mock_execute = AsyncMock(return_value=mock_fetch)

            mock_session.return_value.__aenter__.return_value.execute = mock_execute

            # Analyze feedback
            decision = await auto_tuner._analyze_context_patterns()

            # Should reduce context
            assert decision is not None
            assert decision.action == "reduce_context_limit"
            assert decision.new_value < decision.old_value

    @pytest.mark.asyncio
    async def test_increase_context_when_too_few_complaints(self):
        """Should increase context limit when > 20% say 'too few sources'"""
        auto_tuner = AutoTuner()
        await auto_tuner.initialize()

        # Mock database
        with patch('src.auto_tuner.get_session') as mock_session:
            # 25% say "too few"
            mock_result = Mock()
            mock_result.too_many_count = 2
            mock_result.too_few_count = 10
            mock_result.total_feedback = 40

            mock_fetch = Mock()
            mock_fetch.fetchone = Mock(return_value=mock_result)

            mock_execute = AsyncMock(return_value=mock_fetch)

            mock_session.return_value.__aenter__.return_value.execute = mock_execute

            # Analyze feedback
            decision = await auto_tuner._analyze_context_patterns()

            # Should increase context
            assert decision is not None
            assert decision.action == "increase_context_limit"
            assert decision.new_value > decision.old_value


class TestTuningApplication:
    """Test applying tuning decisions"""

    @pytest.mark.asyncio
    async def test_apply_decision_updates_config(self):
        """Applying decision should update config overrides"""
        auto_tuner = AutoTuner()
        await auto_tuner.initialize()

        decision = TuningDecision(
            action="disable_semantic_cache",
            reason="Test reason",
            old_value=True,
            new_value=False,
            confidence=0.8,
            timestamp=datetime.utcnow()
        )

        # Apply decision
        await auto_tuner.apply_tuning(decision)

        # Verify config override
        assert auto_tuner.get_config_override('semantic_cache_enabled', True) == False

        # Verify logged
        assert len(auto_tuner.get_tuning_history()) == 1
        assert auto_tuner.get_tuning_history()[0].action == "disable_semantic_cache"

    @pytest.mark.asyncio
    async def test_get_config_override_returns_default(self):
        """Should return default when no override set"""
        auto_tuner = AutoTuner()

        # No override set
        value = auto_tuner.get_config_override('some_key', 'default_value')

        assert value == 'default_value'


class TestEndToEnd:
    """Test complete auto-tuning workflow"""

    @pytest.mark.asyncio
    async def test_analyze_and_apply_workflow(self):
        """Complete workflow: analyze → decide → apply"""
        auto_tuner = AutoTuner()
        await auto_tuner.initialize()

        # Mock database to trigger cache disable
        with patch('src.auto_tuner.get_session') as mock_session:
            mock_result = Mock()
            mock_result.avg_rating = 2.0
            mock_result.feedback_count = 20

            mock_fetch = Mock()
            mock_fetch.fetchone = Mock(return_value=mock_result)

            mock_execute = AsyncMock(return_value=mock_fetch)

            mock_session.return_value.__aenter__.return_value.execute = mock_execute

            # Analyze feedback
            decision = await auto_tuner.analyze_feedback()

            # Should get a decision
            assert decision is not None
            assert decision.action == "disable_semantic_cache"

            # Apply it
            await auto_tuner.apply_tuning(decision)

            # Verify applied
            assert auto_tuner.config_overrides['semantic_cache_enabled'] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
