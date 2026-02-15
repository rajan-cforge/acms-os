"""
Unit tests for Job Runner with idempotency guarantees.

Tests the advisory lock mechanism and job_runs tracking.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.jobs.job_runner import (
    _generate_lock_id,
    run_job_with_tracking
)


class TestLockIdGeneration:
    """Test lock ID generation for advisory locks."""

    def test_lock_id_is_consistent(self):
        """Same inputs should produce same lock ID."""
        id1 = _generate_lock_id("tenant1", "job1")
        id2 = _generate_lock_id("tenant1", "job1")
        assert id1 == id2

    def test_different_tenants_have_different_locks(self):
        """Different tenants should have different lock IDs."""
        id1 = _generate_lock_id("tenant1", "job1")
        id2 = _generate_lock_id("tenant2", "job1")
        assert id1 != id2

    def test_different_jobs_have_different_locks(self):
        """Different jobs should have different lock IDs."""
        id1 = _generate_lock_id("tenant1", "job1")
        id2 = _generate_lock_id("tenant1", "job2")
        assert id1 != id2

    def test_lock_id_is_int64(self):
        """Lock ID should be a valid int64."""
        lock_id = _generate_lock_id("tenant", "job")
        assert isinstance(lock_id, int)
        # int64 range: -2^63 to 2^63-1
        assert -9223372036854775808 <= lock_id <= 9223372036854775807


class TestJobTracking:
    """Test job execution tracking."""

    @pytest.fixture
    def mock_pool(self):
        """Create a mock database pool."""
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool, conn

    @pytest.mark.asyncio
    async def test_skips_when_lock_held(self, mock_pool):
        """Job should be skipped when lock is already held."""
        pool, conn = mock_pool

        # Lock not acquired
        conn.fetchval.return_value = False

        with patch('src.storage.database.get_db_pool', return_value=pool):
            result = await run_job_with_tracking(
                job_name="test_job",
                job_version="1.0",
                job_func=AsyncMock()
            )

        assert result["status"] == "skipped"
        assert result["skipped_reason"] == "lock_held_by_another_process"

    @pytest.mark.asyncio
    async def test_records_successful_job(self, mock_pool):
        """Successful job should be recorded in job_runs."""
        pool, conn = mock_pool

        # Lock acquired
        conn.fetchval.return_value = True

        # Mock job function
        mock_job = AsyncMock(return_value={"affected_count": 42})

        with patch('src.storage.database.get_db_pool', return_value=pool):
            result = await run_job_with_tracking(
                job_name="test_job",
                job_version="1.0",
                job_func=mock_job
            )

        assert result["status"] == "success"
        assert result["output_count"] == 42

        # Verify job_runs insert was called
        calls = conn.execute.call_args_list
        assert any("INSERT INTO job_runs" in str(call) for call in calls)
        assert any("UPDATE job_runs" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_records_failed_job(self, mock_pool):
        """Failed job should be recorded with error."""
        pool, conn = mock_pool

        # Lock acquired
        conn.fetchval.return_value = True

        # Mock job function that fails
        mock_job = AsyncMock(side_effect=ValueError("Test error"))

        with patch('src.storage.database.get_db_pool', return_value=pool):
            result = await run_job_with_tracking(
                job_name="test_job",
                job_version="1.0",
                job_func=mock_job
            )

        assert result["status"] == "failed"
        assert result["error_count"] == 1
        assert "Test error" in result["error_summary"]

    @pytest.mark.asyncio
    async def test_releases_lock_on_success(self, mock_pool):
        """Lock should be released after successful job."""
        pool, conn = mock_pool
        conn.fetchval.return_value = True

        with patch('src.storage.database.get_db_pool', return_value=pool):
            await run_job_with_tracking(
                job_name="test_job",
                job_version="1.0",
                job_func=AsyncMock()
            )

        # Verify unlock was called
        calls = conn.execute.call_args_list
        assert any("pg_advisory_unlock" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_releases_lock_on_failure(self, mock_pool):
        """Lock should be released even if job fails."""
        pool, conn = mock_pool
        conn.fetchval.return_value = True

        with patch('src.storage.database.get_db_pool', return_value=pool):
            await run_job_with_tracking(
                job_name="test_job",
                job_version="1.0",
                job_func=AsyncMock(side_effect=Exception("Boom"))
            )

        # Verify unlock was called despite failure
        calls = conn.execute.call_args_list
        assert any("pg_advisory_unlock" in str(call) for call in calls)


# Run with: PYTHONPATH=. pytest tests/unit/test_job_runner.py -v
