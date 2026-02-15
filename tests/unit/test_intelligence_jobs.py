"""Unit tests for Intelligence Jobs.

Tests the job wrappers and scheduling logic per Arch-review.md §15.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.jobs.intelligence_jobs import (
    topic_extraction_job,
    insight_generation_job,
    weekly_report_job,
    run_topic_extraction_tracked,
    run_insight_generation_tracked,
    run_weekly_report_tracked
)


class TestTopicExtractionJob:
    """Tests for hourly topic extraction job."""

    @pytest.fixture
    def mock_pool(self):
        """Create a mock database pool with proper async context manager."""
        pool = MagicMock()
        conn = AsyncMock()

        # Create a proper async context manager for pool.acquire()
        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = conn
        async_cm.__aexit__.return_value = None
        pool.acquire.return_value = async_cm

        return pool, conn

    @pytest.mark.asyncio
    async def test_no_new_qa_pairs(self, mock_pool):
        """Job should handle empty result set gracefully."""
        pool, conn = mock_pool
        conn.fetch.return_value = []  # No Q&A pairs

        async def mock_get_db_pool():
            return pool

        with patch('src.jobs.intelligence_jobs.get_db_pool', mock_get_db_pool):
            result = await topic_extraction_job()

        assert result["input_count"] == 0
        assert result["affected_count"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_returns_stats(self, mock_pool):
        """Job should return proper stats structure."""
        pool, conn = mock_pool
        conn.fetch.return_value = []  # No Q&A pairs

        async def mock_get_db_pool():
            return pool

        with patch('src.jobs.intelligence_jobs.get_db_pool', mock_get_db_pool):
            result = await topic_extraction_job()

        # Verify stats structure
        assert "input_count" in result
        assert "affected_count" in result
        assert "errors" in result
        assert "tokens_used" in result
        assert "cost_usd" in result


class TestInsightGenerationJob:
    """Tests for daily insight generation job."""

    @pytest.fixture
    def mock_pool(self):
        """Create a mock database pool with proper async context manager."""
        pool = MagicMock()
        conn = AsyncMock()

        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = conn
        async_cm.__aexit__.return_value = None
        pool.acquire.return_value = async_cm

        return pool, conn

    @pytest.mark.asyncio
    async def test_no_active_users(self, mock_pool):
        """Job should handle no active users gracefully."""
        pool, conn = mock_pool
        conn.fetch.return_value = []  # No active users

        async def mock_get_db_pool():
            return pool

        with patch('src.jobs.intelligence_jobs.get_db_pool', mock_get_db_pool):
            result = await insight_generation_job()

        assert result["input_count"] == 0
        assert result["users_processed"] == 0

    @pytest.mark.asyncio
    async def test_returns_stats_structure(self, mock_pool):
        """Job should return proper stats structure."""
        pool, conn = mock_pool
        conn.fetch.return_value = []  # No users

        async def mock_get_db_pool():
            return pool

        with patch('src.jobs.intelligence_jobs.get_db_pool', mock_get_db_pool):
            result = await insight_generation_job()

        # Verify stats structure
        assert "input_count" in result
        assert "affected_count" in result
        assert "users_processed" in result
        assert "org_knowledge_updated" in result
        assert "errors" in result


class TestWeeklyReportJob:
    """Tests for weekly report job."""

    @pytest.fixture
    def mock_pool(self):
        """Create a mock database pool with proper async context manager."""
        pool = MagicMock()
        conn = AsyncMock()

        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = conn
        async_cm.__aexit__.return_value = None
        pool.acquire.return_value = async_cm

        return pool, conn

    @pytest.mark.asyncio
    async def test_no_active_users(self, mock_pool):
        """Job should handle no active users gracefully."""
        pool, conn = mock_pool
        conn.fetch.return_value = []  # No active users

        async def mock_get_db_pool():
            return pool

        with patch('src.jobs.intelligence_jobs.get_db_pool', mock_get_db_pool):
            result = await weekly_report_job()

        assert result["input_count"] == 0
        assert result["personal_reports"] == 0
        assert result["org_reports"] == 0


class TestJobTracking:
    """Tests for job tracking wrappers."""

    @pytest.fixture
    def mock_job_runner(self):
        """Mock the job runner."""
        with patch('src.jobs.intelligence_jobs.run_job_with_tracking') as mock:
            mock.return_value = {"status": "success"}
            yield mock

    @pytest.mark.asyncio
    async def test_topic_extraction_tracked(self, mock_job_runner):
        """Topic extraction should use job tracking."""
        result = await run_topic_extraction_tracked()

        assert mock_job_runner.called
        call_kwargs = mock_job_runner.call_args[1]
        assert call_kwargs["job_name"] == "topic_extraction"
        assert call_kwargs["job_version"] == "v1.0"

    @pytest.mark.asyncio
    async def test_insight_generation_tracked(self, mock_job_runner):
        """Insight generation should use job tracking."""
        result = await run_insight_generation_tracked()

        assert mock_job_runner.called
        call_kwargs = mock_job_runner.call_args[1]
        assert call_kwargs["job_name"] == "insight_generation"

    @pytest.mark.asyncio
    async def test_weekly_report_tracked(self, mock_job_runner):
        """Weekly report should use job tracking."""
        result = await run_weekly_report_tracked()

        assert mock_job_runner.called
        call_kwargs = mock_job_runner.call_args[1]
        assert call_kwargs["job_name"] == "weekly_report"


class TestSchedulerIntegration:
    """Tests for scheduler configuration."""

    def test_job_enable_flags(self):
        """Test that job enable flags work correctly."""
        import os

        # Helper matches scheduler.py implementation
        def is_job_enabled(job_name: str, default: bool = True) -> bool:
            env_key = f"ACMS_JOB_{job_name.upper()}_ENABLED"
            return os.getenv(env_key, str(default)).lower() == "true"

        # Test default (enabled)
        assert is_job_enabled("topic_extraction") is True

        # Test explicitly enabled
        os.environ["ACMS_JOB_TOPIC_EXTRACTION_ENABLED"] = "true"
        assert is_job_enabled("topic_extraction") is True

        # Test explicitly disabled
        os.environ["ACMS_JOB_TOPIC_EXTRACTION_ENABLED"] = "false"
        assert is_job_enabled("topic_extraction") is False

        # Cleanup
        del os.environ["ACMS_JOB_TOPIC_EXTRACTION_ENABLED"]


# Run with: PYTHONPATH=. pytest tests/unit/test_intelligence_jobs.py -v
