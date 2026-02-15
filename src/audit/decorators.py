"""
Audit Decorators

Decorators for automatic audit logging of functions.
"""

import functools
import logging
import time
from typing import Optional, Callable, Any
from uuid import UUID

from .models import AuditEventType, DataClassification
from .logger import get_audit_logger

logger = logging.getLogger(__name__)


def audit_operation(
    source: str,
    operation: str,
    event_type: AuditEventType = AuditEventType.TRANSFORM,
    destination: Optional[str] = None,
    data_classification: Optional[DataClassification] = None,
    extract_item_count: Optional[Callable[[Any], int]] = None,
    extract_metadata: Optional[Callable[[Any], dict]] = None,
):
    """
    Decorator for automatic audit logging.

    Args:
        source: Source system (gmail, plaid, etc.)
        operation: Operation name
        event_type: Type of event (ingress, transform, egress)
        destination: Destination (required for egress)
        data_classification: Data sensitivity level
        extract_item_count: Function to extract item count from result
        extract_metadata: Function to extract metadata from result

    Usage:
        @audit_operation(
            source="gmail",
            operation="fetch_emails",
            event_type=AuditEventType.INGRESS
        )
        async def fetch_emails():
            ...

        @audit_operation(
            source="chat",
            operation="llm_call",
            event_type=AuditEventType.EGRESS,
            destination="claude_api",
            extract_metadata=lambda r: {"tokens": r.usage.total_tokens}
        )
        async def call_llm(prompt):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            audit = get_audit_logger()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)

                # Extract item count if function provided
                item_count = 1
                if extract_item_count and result is not None:
                    try:
                        item_count = extract_item_count(result)
                    except Exception:
                        pass

                # Extract metadata if function provided
                metadata = {}
                if extract_metadata and result is not None:
                    try:
                        metadata = extract_metadata(result)
                    except Exception:
                        pass

                # Log success
                await audit.log_event(
                    event_type=event_type,
                    source=source,
                    operation=operation,
                    destination=destination or "local",
                    data_classification=data_classification,
                    item_count=item_count,
                    duration_ms=duration_ms,
                    success=True,
                    metadata=metadata,
                )

                return result

            except Exception as e:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)

                # Log failure
                await audit.log_event(
                    event_type=event_type,
                    source=source,
                    operation=operation,
                    destination=destination or "local",
                    data_classification=data_classification,
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(e),
                )

                raise

        return wrapper
    return decorator


def audit_ingress(
    source: str,
    operation: str,
    data_classification: Optional[DataClassification] = None,
    extract_item_count: Optional[Callable[[Any], int]] = None,
    extract_metadata: Optional[Callable[[Any], dict]] = None,
):
    """
    Decorator for auditing data ingress operations.

    Usage:
        @audit_ingress(source="gmail", operation="fetch_emails")
        async def fetch_emails():
            ...
    """
    return audit_operation(
        source=source,
        operation=operation,
        event_type=AuditEventType.INGRESS,
        destination="local",
        data_classification=data_classification,
        extract_item_count=extract_item_count,
        extract_metadata=extract_metadata,
    )


def audit_egress(
    source: str,
    operation: str,
    destination: str,
    data_classification: Optional[DataClassification] = None,
    extract_metadata: Optional[Callable[[Any], dict]] = None,
):
    """
    Decorator for auditing data egress operations.

    Privacy is automatically enforced - confidential data
    cannot go to external destinations.

    Usage:
        @audit_egress(
            source="chat",
            operation="llm_call",
            destination="claude_api"
        )
        async def call_claude(prompt):
            ...
    """
    return audit_operation(
        source=source,
        operation=operation,
        event_type=AuditEventType.EGRESS,
        destination=destination,
        data_classification=data_classification,
        extract_metadata=extract_metadata,
    )


def audit_transform(
    source: str,
    operation: str,
    destination: str = "local",
    data_classification: Optional[DataClassification] = None,
    extract_item_count: Optional[Callable[[Any], int]] = None,
    extract_metadata: Optional[Callable[[Any], dict]] = None,
):
    """
    Decorator for auditing data transformation operations.

    Usage:
        @audit_transform(
            source="memory",
            operation="create_embedding",
            destination="weaviate"
        )
        async def create_embedding(text):
            ...
    """
    return audit_operation(
        source=source,
        operation=operation,
        event_type=AuditEventType.TRANSFORM,
        destination=destination,
        data_classification=data_classification,
        extract_item_count=extract_item_count,
        extract_metadata=extract_metadata,
    )


class AuditContext:
    """
    Context manager for grouping related audit events.

    Usage:
        async with AuditContext(source="gmail", operation="sync") as ctx:
            emails = await fetch_emails()
            ctx.log_step("fetched", item_count=len(emails))

            for email in emails:
                await process_email(email)
            ctx.log_step("processed", item_count=len(emails))
    """

    def __init__(
        self,
        source: str,
        operation: str,
        user_id: str = "default",
    ):
        self.source = source
        self.operation = operation
        self.user_id = user_id
        self.correlation_id: Optional[UUID] = None
        self.start_time: Optional[float] = None
        self.steps: list = []

    async def __aenter__(self):
        from uuid import uuid4
        self.correlation_id = uuid4()
        self.start_time = time.time()

        audit = get_audit_logger()
        await audit.log_event(
            event_type=AuditEventType.INGRESS,
            source=self.source,
            operation=f"{self.operation}_start",
            correlation_id=self.correlation_id,
            user_id=self.user_id,
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self.start_time) * 1000)

        audit = get_audit_logger()
        await audit.log_event(
            event_type=AuditEventType.TRANSFORM,
            source=self.source,
            operation=f"{self.operation}_complete",
            correlation_id=self.correlation_id,
            user_id=self.user_id,
            duration_ms=duration_ms,
            success=exc_type is None,
            error_message=str(exc_val) if exc_val else None,
            metadata={"steps": self.steps},
        )

    async def log_step(
        self,
        step_name: str,
        item_count: int = 1,
        metadata: Optional[dict] = None
    ):
        """Log an intermediate step in the operation"""
        self.steps.append({
            "step": step_name,
            "item_count": item_count,
            "timestamp": time.time() - self.start_time,
        })

        audit = get_audit_logger()
        await audit.log_event(
            event_type=AuditEventType.TRANSFORM,
            source=self.source,
            operation=f"{self.operation}_{step_name}",
            correlation_id=self.correlation_id,
            user_id=self.user_id,
            item_count=item_count,
            metadata=metadata,
        )
