"""
Audit Integration Tests - TDD First

Tests for verifying audit events are created for all data flow operations.
Following TDD: Write tests first, then implement.

Requirements from ACMS_3.0_UNIFIED_INTELLIGENCE_PLAN.md Phase 0:
- Every API call creates audit event
- Daily summary updates correctly
- No data leaves system without audit

Test Categories:
1. EGRESS: LLM API calls (Claude, Gemini, ChatGPT)
2. INGRESS: File uploads, user queries
3. TRANSFORM: Memory writes, knowledge extraction
"""

import pytest
import pytest_asyncio
import asyncio
import asyncpg
import os
from datetime import date, datetime, timedelta
from uuid import uuid4

# Import audit components
from src.audit.models import AuditEventType, DataClassification, AuditEventFilter
from src.audit.logger import AuditLogger, init_audit_logger


# ============================================
# FIXTURES
# ============================================

@pytest_asyncio.fixture(scope="function")
async def db_pool():
    """Create database pool for tests"""
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://acms:acms_password@localhost:40432/acms"
    )
    pool = await asyncpg.create_pool(db_url)
    yield pool
    await pool.close()


@pytest_asyncio.fixture(scope="function")
async def audit_logger(db_pool):
    """Initialize audit logger with test database"""
    logger = AuditLogger(db_pool)
    yield logger


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_events(db_pool):
    """Clean up test events before and after each test"""
    # Clean before
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM audit_events WHERE source IN ('test', 'gateway', 'file', 'memory') "
            "AND created_at > NOW() - INTERVAL '1 hour'"
        )

    yield

    # Clean after
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM audit_events WHERE source IN ('test', 'gateway', 'file', 'memory') "
            "AND created_at > NOW() - INTERVAL '1 hour'"
        )


# ============================================
# TEST: AUDIT EVENT CREATION
# ============================================

class TestAuditEventCreation:
    """TDD: Verify audit events are created with correct fields"""

    @pytest.mark.asyncio
    async def test_egress_event_has_required_fields(self, audit_logger):
        """Every egress event must have source, operation, destination"""
        event = await audit_logger.log_egress(
            source="gateway",
            operation="llm_call",
            destination="claude_api",
            item_count=1,
            metadata={"input_tokens": 100, "output_tokens": 50}
        )

        assert event.source == "gateway"
        assert event.operation == "llm_call"
        assert event.destination == "claude_api"
        assert event.event_type == AuditEventType.EGRESS
        assert event.id is not None
        assert event.timestamp is not None

    @pytest.mark.asyncio
    async def test_ingress_event_has_required_fields(self, audit_logger):
        """Every ingress event must have source, operation, destination=local"""
        event = await audit_logger.log_ingress(
            source="file",
            operation="upload",
            item_count=1,
            data_classification=DataClassification.INTERNAL,
            metadata={"filename": "test.pdf", "size_bytes": 1024}
        )

        assert event.source == "file"
        assert event.operation == "upload"
        assert event.destination == "local"  # Ingress always goes to local
        assert event.event_type == AuditEventType.INGRESS

    @pytest.mark.asyncio
    async def test_transform_event_has_required_fields(self, audit_logger):
        """Every transform event must have source, operation, destination"""
        event = await audit_logger.log_transform(
            source="memory",
            operation="create",
            destination="weaviate",
            item_count=1,
            metadata={"memory_id": str(uuid4())}
        )

        assert event.source == "memory"
        assert event.operation == "create"
        assert event.destination == "weaviate"
        assert event.event_type == AuditEventType.TRANSFORM


# ============================================
# TEST: PRIVACY ENFORCEMENT
# ============================================

class TestAuditPrivacyEnforcement:
    """TDD: Verify privacy rules are enforced"""

    @pytest.mark.asyncio
    async def test_confidential_data_blocked_from_external(self, audit_logger):
        """CRITICAL: Confidential data must never go to external destinations"""
        from src.audit.privacy import PrivacyViolationError

        with pytest.raises(PrivacyViolationError):
            await audit_logger.log_egress(
                source="gateway",
                operation="llm_call",
                destination="claude_api",
                data_classification=DataClassification.CONFIDENTIAL,
            )

    @pytest.mark.asyncio
    async def test_local_only_data_blocked_from_external(self, audit_logger):
        """LOCAL_ONLY data must never go to external destinations"""
        from src.audit.privacy import PrivacyViolationError

        with pytest.raises(PrivacyViolationError):
            await audit_logger.log_egress(
                source="gateway",
                operation="llm_call",
                destination="openai_api",
                data_classification=DataClassification.LOCAL_ONLY,
            )

    @pytest.mark.asyncio
    async def test_public_data_allowed_to_external(self, audit_logger):
        """Public data can go to external destinations"""
        event = await audit_logger.log_egress(
            source="gateway",
            operation="llm_call",
            destination="gemini_api",
            data_classification=DataClassification.PUBLIC,
        )

        assert event is not None
        assert event.destination == "gemini_api"


# ============================================
# TEST: LLM CALL AUDITING
# ============================================

class TestLLMCallAuditing:
    """TDD: Verify LLM calls are properly audited"""

    @pytest.mark.asyncio
    async def test_claude_call_creates_egress_event(self, audit_logger):
        """Claude API call should create egress audit event"""
        event = await audit_logger.log_egress(
            source="gateway",
            operation="llm_call",
            destination="claude_api",
            duration_ms=1500,
            metadata={
                "agent": "claude_sonnet",
                "input_tokens": 500,
                "output_tokens": 200,
                "cost_usd": 0.015,
                "model": "claude-sonnet-4-20250514"
            }
        )

        assert event.destination == "claude_api"
        assert event.metadata["agent"] == "claude_sonnet"
        assert event.metadata["cost_usd"] == 0.015
        assert event.duration_ms == 1500

    @pytest.mark.asyncio
    async def test_gemini_call_creates_egress_event(self, audit_logger):
        """Gemini API call should create egress audit event"""
        event = await audit_logger.log_egress(
            source="gateway",
            operation="llm_call",
            destination="gemini_api",
            duration_ms=800,
            metadata={
                "agent": "gemini_flash",
                "input_tokens": 300,
                "output_tokens": 150,
                "cost_usd": 0.002,
                "model": "gemini-2.0-flash-exp"
            }
        )

        assert event.destination == "gemini_api"
        assert event.metadata["agent"] == "gemini_flash"

    @pytest.mark.asyncio
    async def test_openai_call_creates_egress_event(self, audit_logger):
        """OpenAI API call should create egress audit event"""
        event = await audit_logger.log_egress(
            source="gateway",
            operation="llm_call",
            destination="openai_api",
            duration_ms=1200,
            metadata={
                "agent": "chatgpt",
                "input_tokens": 400,
                "output_tokens": 180,
                "cost_usd": 0.008,
                "model": "gpt-4o"
            }
        )

        assert event.destination == "openai_api"
        assert event.metadata["agent"] == "chatgpt"


# ============================================
# TEST: FILE UPLOAD AUDITING
# ============================================

class TestFileUploadAuditing:
    """TDD: Verify file uploads are properly audited"""

    @pytest.mark.asyncio
    async def test_file_upload_creates_ingress_event(self, audit_logger):
        """File upload should create ingress audit event"""
        event = await audit_logger.log_ingress(
            source="file",
            operation="upload",
            item_count=1,
            data_classification=DataClassification.INTERNAL,
            metadata={
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "size_bytes": 102400,
                "memory_id": str(uuid4())
            }
        )

        assert event.source == "file"
        assert event.operation == "upload"
        assert event.event_type == AuditEventType.INGRESS
        assert event.metadata["filename"] == "report.pdf"
        assert event.metadata["size_bytes"] == 102400


# ============================================
# TEST: MEMORY WRITE AUDITING
# ============================================

class TestMemoryWriteAuditing:
    """TDD: Verify memory writes are properly audited"""

    @pytest.mark.asyncio
    async def test_memory_create_creates_transform_event(self, audit_logger):
        """Memory creation should create transform audit event"""
        memory_id = uuid4()
        event = await audit_logger.log_transform(
            source="memory",
            operation="create",
            destination="weaviate",
            item_count=1,
            metadata={
                "memory_id": str(memory_id),
                "tier": "SHORT",
                "has_embedding": True
            }
        )

        assert event.source == "memory"
        assert event.operation == "create"
        assert event.destination == "weaviate"
        assert event.event_type == AuditEventType.TRANSFORM


# ============================================
# TEST: USER QUERY AUDITING
# ============================================

class TestUserQueryAuditing:
    """TDD: Verify user queries are properly audited"""

    @pytest.mark.asyncio
    async def test_user_query_creates_ingress_event(self, audit_logger):
        """User query should create ingress audit event"""
        correlation_id = uuid4()
        event = await audit_logger.log_ingress(
            source="gateway",
            operation="user_query",
            item_count=1,
            correlation_id=correlation_id,
            metadata={
                "query_length": 150,
                "has_file_context": False,
                "conversation_id": str(uuid4())
            }
        )

        assert event.source == "gateway"
        assert event.operation == "user_query"
        assert event.correlation_id == correlation_id


# ============================================
# TEST: CORRELATION
# ============================================

class TestAuditCorrelation:
    """TDD: Verify related events can be correlated"""

    @pytest.mark.asyncio
    async def test_correlation_id_links_events(self, audit_logger):
        """Related events should share correlation ID"""
        correlation_id = uuid4()

        # Create chain of related events
        event1 = await audit_logger.log_ingress(
            source="gateway",
            operation="user_query",
            correlation_id=correlation_id
        )

        event2 = await audit_logger.log_egress(
            source="gateway",
            operation="llm_call",
            destination="claude_api",
            correlation_id=correlation_id
        )

        event3 = await audit_logger.log_transform(
            source="memory",
            operation="create",
            destination="weaviate",
            correlation_id=correlation_id
        )

        # Verify all share same correlation ID
        assert event1.correlation_id == correlation_id
        assert event2.correlation_id == correlation_id
        assert event3.correlation_id == correlation_id


# ============================================
# TEST: END-TO-END FLOW
# ============================================

class TestEndToEndAuditFlow:
    """TDD: End-to-end audit flow verification"""

    @pytest.mark.asyncio
    async def test_full_query_flow_creates_all_events(self, audit_logger):
        """
        A complete query flow should create:
        1. INGRESS: User query received
        2. EGRESS: LLM API call
        3. TRANSFORM: Memory/response stored
        """
        correlation_id = uuid4()

        # Step 1: User query ingress
        ingress_event = await audit_logger.log_ingress(
            source="gateway",
            operation="user_query",
            correlation_id=correlation_id,
            metadata={"query": "What is ACMS?"}
        )

        # Step 2: LLM call egress
        egress_event = await audit_logger.log_egress(
            source="gateway",
            operation="llm_call",
            destination="claude_api",
            correlation_id=correlation_id,
            duration_ms=1500,
            metadata={"input_tokens": 500, "output_tokens": 200}
        )

        # Step 3: Memory transform
        transform_event = await audit_logger.log_transform(
            source="memory",
            operation="create",
            destination="weaviate",
            correlation_id=correlation_id,
            metadata={"memory_id": str(uuid4())}
        )

        # Verify all events created
        assert ingress_event.event_type == AuditEventType.INGRESS
        assert egress_event.event_type == AuditEventType.EGRESS
        assert transform_event.event_type == AuditEventType.TRANSFORM

        # Verify correlation
        assert ingress_event.correlation_id == egress_event.correlation_id == transform_event.correlation_id

        # Query events by correlation ID
        result = await audit_logger.get_events(AuditEventFilter(
            correlation_id=correlation_id,
            limit=10
        ))

        assert result.total_count == 3
        assert len(result.events) == 3

    @pytest.mark.asyncio
    async def test_events_persisted_to_database(self, audit_logger, db_pool):
        """Verify events are actually persisted to database"""
        # Create an event
        event = await audit_logger.log_ingress(
            source="test",
            operation="persistence_test",
            metadata={"test_id": str(uuid4())}
        )

        # Query directly from database
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM audit_events WHERE id = $1",
                event.id
            )

        assert row is not None
        assert row['source'] == "test"
        assert row['operation'] == "persistence_test"
        assert row['event_type'] == "ingress"
