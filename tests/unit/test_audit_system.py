"""
Unit tests for Audit System

Tests for:
- AuditLogger class
- Privacy enforcement
- Audit decorators
- Models and validation
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.audit.models import (
    AuditEventType,
    AuditEvent,
    AuditEventCreate,
    AuditDailySummary,
    AuditEventFilter,
    AuditEventList,
    EndOfDayReport,
    IntegrationStatus,
    PrivacyViolation,
    DataClassification,
)
from src.audit.privacy import PrivacyEnforcer, PrivacyViolationError


# ============================================================================
# MODELS TESTS
# ============================================================================

class TestAuditEventType:
    """Tests for AuditEventType enum"""

    def test_event_types_exist(self):
        """All required event types should exist"""
        assert AuditEventType.INGRESS == "ingress"
        assert AuditEventType.TRANSFORM == "transform"
        assert AuditEventType.EGRESS == "egress"
        assert AuditEventType.VALIDATION == "validation"


class TestDataClassification:
    """Tests for DataClassification enum"""

    def test_classification_levels_exist(self):
        """All classification levels should exist"""
        assert DataClassification.PUBLIC == "public"
        assert DataClassification.INTERNAL == "internal"
        assert DataClassification.CONFIDENTIAL == "confidential"
        assert DataClassification.LOCAL_ONLY == "local_only"


class TestAuditEventCreate:
    """Tests for AuditEventCreate model"""

    def test_minimal_event(self):
        """Should create event with minimal required fields"""
        event = AuditEventCreate(
            event_type=AuditEventType.INGRESS,
            source="gmail",
            operation="fetch_emails"
        )
        assert event.event_type == AuditEventType.INGRESS
        assert event.source == "gmail"
        assert event.operation == "fetch_emails"
        assert event.item_count == 1
        assert event.success is True

    def test_full_event(self):
        """Should create event with all fields"""
        correlation_id = uuid4()
        event = AuditEventCreate(
            event_type=AuditEventType.EGRESS,
            source="chat",
            operation="llm_call",
            data_classification=DataClassification.PUBLIC,
            item_count=5,
            destination="claude_api",
            correlation_id=correlation_id,
            user_id="user123",
            metadata={"tokens": 1000},
            duration_ms=500,
            success=True
        )
        assert event.destination == "claude_api"
        assert event.correlation_id == correlation_id
        assert event.metadata["tokens"] == 1000


class TestAuditEvent:
    """Tests for AuditEvent model"""

    def test_event_has_id_and_timestamp(self):
        """Full event should have auto-generated ID and timestamp"""
        event = AuditEvent(
            event_type=AuditEventType.TRANSFORM,
            source="memory",
            operation="create_embedding"
        )
        assert isinstance(event.id, UUID)
        assert isinstance(event.timestamp, datetime)


class TestAuditDailySummary:
    """Tests for AuditDailySummary model"""

    def test_default_values(self):
        """Summary should have sensible defaults"""
        summary = AuditDailySummary(date=date.today())
        assert summary.gmail_emails_fetched == 0
        assert summary.llm_calls_claude == 0
        assert summary.total_operations == 0
        assert summary.privacy_status == "SECURE"

    def test_privacy_status_secure(self):
        """Privacy status should be SECURE when no external confidential data"""
        summary = AuditDailySummary(
            date=date.today(),
            confidential_items_processed=100,
            confidential_items_kept_local=100,
            confidential_items_external=0
        )
        assert summary.privacy_status == "SECURE"

    def test_privacy_status_violation(self):
        """Privacy status should be VIOLATION when confidential data sent externally"""
        summary = AuditDailySummary(
            date=date.today(),
            confidential_items_processed=100,
            confidential_items_kept_local=99,
            confidential_items_external=1
        )
        assert summary.privacy_status == "VIOLATION"

    def test_success_rate_calculation(self):
        """Success rate should be calculated correctly"""
        summary = AuditDailySummary(
            date=date.today(),
            total_operations=100,
            successful_operations=90,
            failed_operations=10
        )
        assert summary.success_rate == 90.0

    def test_success_rate_zero_operations(self):
        """Success rate should be 100% when no operations"""
        summary = AuditDailySummary(date=date.today())
        assert summary.success_rate == 100.0


class TestEndOfDayReport:
    """Tests for EndOfDayReport model"""

    def test_report_to_text(self):
        """Report should generate readable text"""
        summary = AuditDailySummary(
            date=date.today(),
            gmail_emails_fetched=10,
            llm_calls_claude=5,
            total_operations=15,
            successful_operations=15
        )
        report = EndOfDayReport(
            date=date.today(),
            summary=summary,
            privacy_status="SECURE"
        )
        text = report.to_text()
        assert "DATA FLOW REPORT" in text
        assert "Gmail: 10 emails fetched" in text
        assert "SECURE" in text


class TestIntegrationStatus:
    """Tests for IntegrationStatus model"""

    def test_health_status_healthy(self):
        """Should report healthy when connected with no failures"""
        status = IntegrationStatus(
            id="gmail",
            is_connected=True,
            consecutive_failures=0
        )
        assert status.health_status == "healthy"

    def test_health_status_degraded(self):
        """Should report degraded with 2-4 failures"""
        status = IntegrationStatus(
            id="gmail",
            is_connected=True,
            consecutive_failures=3
        )
        assert status.health_status == "degraded"

    def test_health_status_failed(self):
        """Should report failed with 5+ failures"""
        status = IntegrationStatus(
            id="gmail",
            is_connected=True,
            consecutive_failures=5
        )
        assert status.health_status == "failed"

    def test_health_status_disconnected(self):
        """Should report disconnected when not connected"""
        status = IntegrationStatus(
            id="gmail",
            is_connected=False
        )
        assert status.health_status == "disconnected"


# ============================================================================
# PRIVACY ENFORCER TESTS
# ============================================================================

class TestPrivacyEnforcer:
    """Tests for PrivacyEnforcer class"""

    def setup_method(self):
        """Create fresh enforcer for each test"""
        self.enforcer = PrivacyEnforcer()

    def test_local_destination_detection(self):
        """Should correctly identify local destinations"""
        assert self.enforcer.is_local_destination("local") is True
        assert self.enforcer.is_local_destination("postgres") is True
        assert self.enforcer.is_local_destination("postgresql") is True
        assert self.enforcer.is_local_destination("weaviate") is True
        assert self.enforcer.is_local_destination("redis") is True
        assert self.enforcer.is_local_destination("file") is True
        assert self.enforcer.is_local_destination("LOCAL") is True  # Case insensitive

    def test_external_destination_detection(self):
        """Should correctly identify external destinations"""
        assert self.enforcer.is_external_destination("claude_api") is True
        assert self.enforcer.is_external_destination("openai_api") is True
        assert self.enforcer.is_external_destination("gemini_api") is True
        assert self.enforcer.is_external_destination("browser_chatgpt") is True
        assert self.enforcer.is_external_destination("webhook") is True
        assert self.enforcer.is_external_destination("custom_api") is True  # Ends with _api

    def test_public_data_allowed_anywhere(self):
        """Public data should be allowed to any destination"""
        assert self.enforcer.validate_egress(
            DataClassification.PUBLIC,
            "claude_api"
        ) is True

    def test_internal_data_allowed_anywhere(self):
        """Internal data should be allowed to any destination"""
        assert self.enforcer.validate_egress(
            DataClassification.INTERNAL,
            "claude_api"
        ) is True

    def test_confidential_data_blocked_external(self):
        """Confidential data should be blocked from external destinations"""
        with pytest.raises(PrivacyViolationError):
            self.enforcer.validate_egress(
                DataClassification.CONFIDENTIAL,
                "claude_api"
            )

    def test_confidential_data_allowed_local(self):
        """Confidential data should be allowed to local destinations"""
        assert self.enforcer.validate_egress(
            DataClassification.CONFIDENTIAL,
            "postgres"
        ) is True

    def test_local_only_data_blocked_external(self):
        """LOCAL_ONLY data should be blocked from external destinations"""
        with pytest.raises(PrivacyViolationError):
            self.enforcer.validate_egress(
                DataClassification.LOCAL_ONLY,
                "openai_api"
            )

    def test_local_only_data_allowed_local(self):
        """LOCAL_ONLY data should be allowed to local destinations"""
        assert self.enforcer.validate_egress(
            DataClassification.LOCAL_ONLY,
            "weaviate"
        ) is True

    def test_none_classification_allowed(self):
        """No classification should be treated as allowed"""
        assert self.enforcer.validate_egress(None, "claude_api") is True

    def test_validate_without_raising(self):
        """Should return False instead of raising when raise_on_violation=False"""
        result = self.enforcer.validate_egress(
            DataClassification.CONFIDENTIAL,
            "claude_api",
            raise_on_violation=False
        )
        assert result is False

    def test_classify_destination(self):
        """Should classify destinations correctly"""
        assert self.enforcer.classify_destination("postgres") == "local"
        assert self.enforcer.classify_destination("claude_api") == "external"
        assert self.enforcer.classify_destination("unknown_thing") == "unknown"

    def test_get_allowed_destinations(self):
        """Should return correct allowed destinations per classification"""
        # Public can go anywhere
        public_dests = self.enforcer.get_allowed_destinations(DataClassification.PUBLIC)
        assert "claude_api" in public_dests
        assert "postgres" in public_dests

        # Confidential only local
        conf_dests = self.enforcer.get_allowed_destinations(DataClassification.CONFIDENTIAL)
        assert "postgres" in conf_dests
        assert "claude_api" not in conf_dests

    def test_sanitize_for_external(self):
        """Should redact sensitive fields"""
        data = {
            "name": "John",
            "password": "secret123",
            "api_key": "sk-123",
            "message": "Hello world"
        }
        sanitized = self.enforcer.sanitize_for_external(data)
        assert sanitized["name"] == "John"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["message"] == "Hello world"


class TestPrivacyViolationError:
    """Tests for PrivacyViolationError exception"""

    def test_error_message(self):
        """Should have informative error message"""
        error = PrivacyViolationError(
            DataClassification.CONFIDENTIAL,
            "claude_api"
        )
        assert "confidential" in str(error).lower()
        assert "claude_api" in str(error)

    def test_error_attributes(self):
        """Should store classification and destination"""
        error = PrivacyViolationError(
            DataClassification.LOCAL_ONLY,
            "openai_api"
        )
        assert error.data_classification == DataClassification.LOCAL_ONLY
        assert error.destination == "openai_api"


# ============================================================================
# AUDIT LOGGER TESTS (with mocked database)
# ============================================================================

class TestAuditLogger:
    """Tests for AuditLogger class with mocked database"""

    @pytest.fixture
    def mock_db_pool(self):
        """Create mock database pool"""
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.acquire.return_value.__aexit__.return_value = None
        return pool

    @pytest.fixture
    def audit_logger(self, mock_db_pool):
        """Create AuditLogger with mock pool"""
        from src.audit.logger import AuditLogger
        return AuditLogger(mock_db_pool)

    @pytest.mark.asyncio
    async def test_correlation_context(self, audit_logger):
        """Correlation context should set and restore correlation ID"""
        assert audit_logger._current_correlation_id is None

        async with audit_logger.correlation_context() as corr_id:
            assert isinstance(corr_id, UUID)
            assert audit_logger._current_correlation_id == corr_id

        assert audit_logger._current_correlation_id is None

    @pytest.mark.asyncio
    async def test_correlation_context_with_id(self, audit_logger):
        """Correlation context should use provided ID"""
        my_id = uuid4()
        async with audit_logger.correlation_context(my_id) as corr_id:
            assert corr_id == my_id

    def test_compute_hash(self, audit_logger):
        """Should compute consistent SHA-256 hashes"""
        hash1 = audit_logger._compute_hash("test data")
        hash2 = audit_logger._compute_hash("test data")
        hash3 = audit_logger._compute_hash("different data")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA-256 hex length

    def test_compute_hash_none(self, audit_logger):
        """Should return empty string for None"""
        assert audit_logger._compute_hash(None) == ""


# ============================================================================
# DECORATOR TESTS
# ============================================================================

class TestAuditDecorators:
    """Tests for audit decorators"""

    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger"""
        with patch('src.audit.decorators.get_audit_logger') as mock:
            mock_logger = AsyncMock()
            mock_logger.log_event = AsyncMock()
            mock.return_value = mock_logger
            yield mock_logger

    @pytest.mark.asyncio
    async def test_audit_ingress_decorator(self, mock_audit_logger):
        """audit_ingress decorator should log ingress events"""
        from src.audit.decorators import audit_ingress

        @audit_ingress(source="gmail", operation="fetch_emails")
        async def fetch_emails():
            return ["email1", "email2"]

        result = await fetch_emails()
        assert result == ["email1", "email2"]
        mock_audit_logger.log_event.assert_called_once()
        call_args = mock_audit_logger.log_event.call_args
        assert call_args.kwargs["event_type"] == AuditEventType.INGRESS
        assert call_args.kwargs["source"] == "gmail"

    @pytest.mark.asyncio
    async def test_audit_egress_decorator(self, mock_audit_logger):
        """audit_egress decorator should log egress events"""
        from src.audit.decorators import audit_egress

        @audit_egress(source="chat", operation="llm_call", destination="claude_api")
        async def call_llm(prompt):
            return {"response": "Hello!"}

        result = await call_llm("Hi")
        assert result["response"] == "Hello!"
        mock_audit_logger.log_event.assert_called_once()
        call_args = mock_audit_logger.log_event.call_args
        assert call_args.kwargs["event_type"] == AuditEventType.EGRESS
        assert call_args.kwargs["destination"] == "claude_api"

    @pytest.mark.asyncio
    async def test_audit_transform_decorator(self, mock_audit_logger):
        """audit_transform decorator should log transform events"""
        from src.audit.decorators import audit_transform

        @audit_transform(source="memory", operation="create_embedding")
        async def create_embedding(text):
            return [0.1, 0.2, 0.3]

        result = await create_embedding("test")
        assert len(result) == 3
        mock_audit_logger.log_event.assert_called_once()
        call_args = mock_audit_logger.log_event.call_args
        assert call_args.kwargs["event_type"] == AuditEventType.TRANSFORM

    @pytest.mark.asyncio
    async def test_audit_decorator_logs_failure(self, mock_audit_logger):
        """Decorator should log failure when function raises"""
        from src.audit.decorators import audit_operation

        @audit_operation(
            source="test",
            operation="failing_op",
            event_type=AuditEventType.TRANSFORM
        )
        async def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_function()

        mock_audit_logger.log_event.assert_called_once()
        call_args = mock_audit_logger.log_event.call_args
        assert call_args.kwargs["success"] is False
        assert "Test error" in call_args.kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_audit_decorator_extracts_item_count(self, mock_audit_logger):
        """Decorator should extract item count from result"""
        from src.audit.decorators import audit_operation

        @audit_operation(
            source="test",
            operation="list_op",
            event_type=AuditEventType.INGRESS,
            extract_item_count=lambda r: len(r)
        )
        async def list_items():
            return [1, 2, 3, 4, 5]

        await list_items()
        call_args = mock_audit_logger.log_event.call_args
        assert call_args.kwargs["item_count"] == 5


# ============================================================================
# INTEGRATION TEST MARKERS
# ============================================================================

@pytest.mark.integration
class TestAuditIntegration:
    """Integration tests (require database)"""

    @pytest.mark.skip(reason="Requires database connection")
    @pytest.mark.asyncio
    async def test_full_audit_flow(self):
        """Test complete audit flow with real database"""
        # This would test:
        # 1. Initialize AuditLogger with real pool
        # 2. Log ingress event
        # 3. Log transform event
        # 4. Log egress event
        # 5. Verify events in database
        # 6. Verify daily summary updated
        pass
