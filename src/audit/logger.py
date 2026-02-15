"""
Audit Logger

Central logging service for all audit events.
Provides methods for logging ingress, transform, and egress events.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from contextlib import asynccontextmanager

import asyncpg

from .models import (
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
from .privacy import PrivacyEnforcer, PrivacyViolationError

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Central audit logging service.

    All data operations should be logged through this service.
    Provides methods for different event types and automatic
    daily summary updates via database triggers.

    Usage:
        audit = AuditLogger(db_pool)

        # Log data ingress
        await audit.log_ingress(
            source="gmail",
            operation="fetch_emails",
            item_count=47,
            data_classification="internal"
        )

        # Log data egress with privacy check
        await audit.log_egress(
            source="chat",
            operation="llm_call",
            destination="claude_api",
            data_classification="public",
            metadata={"input_tokens": 1000, "output_tokens": 500}
        )
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize audit logger.

        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool
        self.privacy_enforcer = PrivacyEnforcer()
        self._current_correlation_id: Optional[UUID] = None
        logger.info("[AuditLogger] Initialized")

    @asynccontextmanager
    async def correlation_context(self, correlation_id: Optional[UUID] = None):
        """
        Context manager for correlating related audit events.

        Usage:
            async with audit.correlation_context() as corr_id:
                await audit.log_ingress(...)  # Uses corr_id automatically
                await audit.log_transform(...)  # Same corr_id
        """
        old_id = self._current_correlation_id
        self._current_correlation_id = correlation_id or uuid4()
        try:
            yield self._current_correlation_id
        finally:
            self._current_correlation_id = old_id

    def _compute_hash(self, data: Any) -> str:
        """Compute SHA-256 hash of data for integrity verification"""
        if data is None:
            return ""
        content = str(data).encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    async def _insert_event(self, event: AuditEventCreate) -> AuditEvent:
        """Insert audit event into database"""
        query = """
            INSERT INTO audit_events (
                event_type, source, operation,
                data_classification, data_hash, data_size_bytes, item_count,
                destination, correlation_id, parent_event_id,
                user_id, session_id, request_id,
                metadata, duration_ms, success, error_message
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17
            )
            RETURNING id, timestamp, created_at
        """

        # Serialize metadata dict to JSON string for asyncpg
        metadata_json = json.dumps(event.metadata) if event.metadata else '{}'

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                event.event_type.value,
                event.source,
                event.operation,
                event.data_classification.value if event.data_classification else None,
                event.data_hash,
                event.data_size_bytes,
                event.item_count,
                event.destination,
                event.correlation_id or self._current_correlation_id,
                event.parent_event_id,
                event.user_id,
                event.session_id,
                event.request_id,
                metadata_json,
                event.duration_ms,
                event.success,
                event.error_message,
            )

        return AuditEvent(
            id=row['id'],
            timestamp=row['timestamp'],
            created_at=row['created_at'],
            **event.model_dump()
        )

    async def log_event(
        self,
        event_type: AuditEventType,
        source: str,
        operation: str,
        destination: Optional[str] = None,
        data_classification: Optional[DataClassification] = None,
        data: Any = None,
        item_count: int = 1,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
        session_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[UUID] = None,
        parent_event_id: Optional[UUID] = None,
    ) -> AuditEvent:
        """
        Log a generic audit event.

        Args:
            event_type: Type of event (ingress, transform, egress)
            source: Source system (gmail, plaid, chat, etc.)
            operation: Operation being performed
            destination: Where data is going (for egress)
            data_classification: Sensitivity level
            data: Actual data (for hash computation)
            item_count: Number of items processed
            duration_ms: Operation duration in milliseconds
            success: Whether operation succeeded
            error_message: Error message if failed
            metadata: Additional context
            user_id: User performing operation
            session_id: Session ID
            request_id: Request ID for tracing
            correlation_id: ID linking related events
            parent_event_id: Parent event for chains

        Returns:
            Created AuditEvent
        """
        # Privacy check for egress
        if event_type == AuditEventType.EGRESS and destination:
            try:
                self.privacy_enforcer.validate_egress(
                    data_classification=data_classification,
                    destination=destination
                )
            except PrivacyViolationError as e:
                # Log the violation
                await self._log_privacy_violation(
                    data_classification=data_classification,
                    destination=destination,
                    operation=operation,
                    user_id=user_id,
                    correlation_id=correlation_id or self._current_correlation_id,
                    metadata=metadata,
                )
                raise

        # Create event
        event = AuditEventCreate(
            event_type=event_type,
            source=source,
            operation=operation,
            destination=destination,
            data_classification=data_classification,
            data_hash=self._compute_hash(data) if data else None,
            data_size_bytes=len(str(data).encode('utf-8')) if data else None,
            item_count=item_count,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            correlation_id=correlation_id or self._current_correlation_id,
            parent_event_id=parent_event_id,
        )

        result = await self._insert_event(event)

        logger.debug(
            f"[Audit] {event_type.value}: {source}/{operation} -> {destination or 'local'}"
        )

        return result

    async def log_ingress(
        self,
        source: str,
        operation: str,
        item_count: int = 1,
        data_classification: Optional[DataClassification] = None,
        data: Any = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AuditEvent:
        """
        Log data entering the system.

        Examples:
            - Fetching emails from Gmail
            - Syncing transactions from Plaid
            - Uploading a file
            - Receiving a chat message
        """
        return await self.log_event(
            event_type=AuditEventType.INGRESS,
            source=source,
            operation=operation,
            destination="local",  # Ingress always goes to local first
            item_count=item_count,
            data_classification=data_classification,
            data=data,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata,
            **kwargs
        )

    async def log_transform(
        self,
        source: str,
        operation: str,
        destination: str = "local",
        item_count: int = 1,
        data_classification: Optional[DataClassification] = None,
        data: Any = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AuditEvent:
        """
        Log data transformation.

        Examples:
            - Generating a summary
            - Creating embeddings
            - Extracting knowledge
            - Capturing learning signals
        """
        return await self.log_event(
            event_type=AuditEventType.TRANSFORM,
            source=source,
            operation=operation,
            destination=destination,
            item_count=item_count,
            data_classification=data_classification,
            data=data,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata,
            **kwargs
        )

    async def log_egress(
        self,
        source: str,
        operation: str,
        destination: str,
        item_count: int = 1,
        data_classification: Optional[DataClassification] = None,
        data: Any = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AuditEvent:
        """
        Log data leaving the system.

        Privacy enforced: Confidential data cannot go to external destinations.

        Examples:
            - Calling Claude/OpenAI/Gemini API
            - Browser automation sending to external AI
            - Exporting data
        """
        return await self.log_event(
            event_type=AuditEventType.EGRESS,
            source=source,
            operation=operation,
            destination=destination,
            item_count=item_count,
            data_classification=data_classification,
            data=data,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata,
            **kwargs
        )

    async def _log_privacy_violation(
        self,
        data_classification: Optional[DataClassification],
        destination: str,
        operation: str,
        user_id: str,
        correlation_id: Optional[UUID],
        metadata: Optional[Dict[str, Any]],
    ):
        """Log a blocked privacy violation"""
        query = """
            INSERT INTO privacy_violations (
                data_classification, attempted_destination, operation,
                user_id, correlation_id, blocked, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        # Serialize metadata dict to JSON string for asyncpg
        metadata_json = json.dumps(metadata) if metadata else '{}'

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data_classification.value if data_classification else None,
                destination,
                operation,
                user_id,
                correlation_id,
                True,  # Always blocked
                metadata_json,
            )

        logger.warning(
            f"[Audit] PRIVACY VIOLATION BLOCKED: "
            f"{data_classification} data to {destination}"
        )

    async def get_events(
        self,
        filter: Optional[AuditEventFilter] = None
    ) -> AuditEventList:
        """Query audit events with filtering"""
        if filter is None:
            filter = AuditEventFilter()

        conditions = []
        params = []
        param_idx = 1

        if filter.event_type:
            conditions.append(f"event_type = ${param_idx}")
            params.append(filter.event_type.value)
            param_idx += 1

        if filter.source:
            conditions.append(f"source = ${param_idx}")
            params.append(filter.source)
            param_idx += 1

        if filter.destination:
            conditions.append(f"destination = ${param_idx}")
            params.append(filter.destination)
            param_idx += 1

        if filter.data_classification:
            conditions.append(f"data_classification = ${param_idx}")
            params.append(filter.data_classification.value)
            param_idx += 1

        if filter.success is not None:
            conditions.append(f"success = ${param_idx}")
            params.append(filter.success)
            param_idx += 1

        if filter.correlation_id:
            conditions.append(f"correlation_id = ${param_idx}")
            params.append(filter.correlation_id)
            param_idx += 1

        if filter.user_id:
            conditions.append(f"user_id = ${param_idx}")
            params.append(filter.user_id)
            param_idx += 1

        if filter.start_time:
            conditions.append(f"timestamp >= ${param_idx}")
            params.append(filter.start_time)
            param_idx += 1

        if filter.end_time:
            conditions.append(f"timestamp <= ${param_idx}")
            params.append(filter.end_time)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Count query
        count_query = f"SELECT COUNT(*) FROM audit_events WHERE {where_clause}"

        # Data query
        data_query = f"""
            SELECT * FROM audit_events
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([filter.limit, filter.offset])

        async with self.db_pool.acquire() as conn:
            total_count = await conn.fetchval(count_query, *params[:-2])
            rows = await conn.fetch(data_query, *params)

        # Parse JSON metadata back to dict
        events = []
        for row in rows:
            row_dict = dict(row)
            if isinstance(row_dict.get('metadata'), str):
                row_dict['metadata'] = json.loads(row_dict['metadata'])
            events.append(AuditEvent(**row_dict))

        return AuditEventList(
            events=events,
            total_count=total_count,
            limit=filter.limit,
            offset=filter.offset,
            has_more=(filter.offset + len(events)) < total_count
        )

    async def get_daily_summary(
        self,
        target_date: Optional[date] = None
    ) -> Optional[AuditDailySummary]:
        """Get daily summary for a specific date"""
        if target_date is None:
            target_date = date.today()

        query = "SELECT * FROM audit_daily_summary WHERE date = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, target_date)

        if row:
            return AuditDailySummary(**dict(row))
        return None

    async def get_end_of_day_report(
        self,
        target_date: Optional[date] = None
    ) -> EndOfDayReport:
        """Generate comprehensive end of day report"""
        if target_date is None:
            target_date = date.today()

        # Get daily summary
        summary = await self.get_daily_summary(target_date)
        if summary is None:
            summary = AuditDailySummary(date=target_date)

        # Get integration statuses
        integrations = await self.get_integration_statuses()

        # Get privacy violations
        violations_query = """
            SELECT * FROM privacy_violations
            WHERE DATE(timestamp) = $1
            ORDER BY timestamp DESC
        """
        async with self.db_pool.acquire() as conn:
            violation_rows = await conn.fetch(violations_query, target_date)

        violations = [PrivacyViolation(**dict(row)) for row in violation_rows]

        # Get top sources
        top_sources_query = """
            SELECT source, COUNT(*) as count
            FROM audit_events
            WHERE DATE(timestamp) = $1
            GROUP BY source
            ORDER BY count DESC
            LIMIT 5
        """
        async with self.db_pool.acquire() as conn:
            top_sources = await conn.fetch(top_sources_query, target_date)

        # Get top operations
        top_ops_query = """
            SELECT operation, COUNT(*) as count
            FROM audit_events
            WHERE DATE(timestamp) = $1
            GROUP BY operation
            ORDER BY count DESC
            LIMIT 5
        """
        async with self.db_pool.acquire() as conn:
            top_ops = await conn.fetch(top_ops_query, target_date)

        # Get error summary
        errors_query = """
            SELECT source, operation, error_message, COUNT(*) as count
            FROM audit_events
            WHERE DATE(timestamp) = $1 AND success = false
            GROUP BY source, operation, error_message
            ORDER BY count DESC
            LIMIT 10
        """
        async with self.db_pool.acquire() as conn:
            error_rows = await conn.fetch(errors_query, target_date)

        return EndOfDayReport(
            date=target_date,
            summary=summary,
            integrations=integrations,
            privacy_status=summary.privacy_status,
            privacy_violations=violations,
            top_sources=[dict(row) for row in top_sources],
            top_operations=[dict(row) for row in top_ops],
            errors_today=summary.failed_operations,
            error_summary=[dict(row) for row in error_rows],
            storage_summary={
                "postgres_bytes_added": summary.postgres_bytes_added,
                "weaviate_vectors_added": summary.weaviate_vectors_added,
                "files_bytes_added": summary.files_bytes_added,
            }
        )

    async def get_integration_statuses(self) -> List[IntegrationStatus]:
        """Get status of all integrations"""
        query = "SELECT * FROM integration_status ORDER BY id"

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query)

        integrations = []
        for row in rows:
            data = dict(row)
            # Handle NULL values for list/dict fields
            if data.get('oauth_scopes') is None:
                data['oauth_scopes'] = []
            if data.get('metadata') is None:
                data['metadata'] = {}
            elif isinstance(data.get('metadata'), str):
                import json
                data['metadata'] = json.loads(data['metadata'])
            integrations.append(IntegrationStatus(**data))
        return integrations

    async def update_integration_status(
        self,
        integration_id: str,
        **updates
    ) -> IntegrationStatus:
        """Update integration status"""
        set_clauses = []
        params = [integration_id]
        param_idx = 2

        for key, value in updates.items():
            set_clauses.append(f"{key} = ${param_idx}")
            params.append(value)
            param_idx += 1

        set_clauses.append("updated_at = NOW()")

        query = f"""
            UPDATE integration_status
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING *
        """

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return IntegrationStatus(**dict(row))


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        raise RuntimeError("AuditLogger not initialized. Call init_audit_logger first.")
    return _audit_logger


async def init_audit_logger(db_pool: asyncpg.Pool) -> AuditLogger:
    """Initialize global audit logger"""
    global _audit_logger
    _audit_logger = AuditLogger(db_pool)
    logger.info("[AuditLogger] Global audit logger initialized")
    return _audit_logger
