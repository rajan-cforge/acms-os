"""
ACMS Audit System

Complete observability for data flow tracking.
Tracks every piece of data entering, transforming, and leaving the system.

Usage:
    from src.audit import audit_logger, audit_operation

    # Manual logging
    await audit_logger.log_ingress(
        source="gmail",
        operation="fetch_emails",
        item_count=47,
        data_classification="internal"
    )

    # Decorator-based auto-logging
    @audit_operation(source="gmail", operation="fetch_emails")
    async def fetch_emails():
        ...
"""

from .models import (
    AuditEventType,
    AuditEvent,
    AuditEventCreate,
    AuditDailySummary,
    IntegrationStatus,
    PrivacyViolation,
    EndOfDayReport,
    DataClassification,
)

from .logger import AuditLogger, get_audit_logger

from .decorators import audit_operation, audit_ingress, audit_egress, audit_transform

from .privacy import PrivacyEnforcer, PrivacyViolationError

__all__ = [
    # Models
    "AuditEventType",
    "AuditEvent",
    "AuditEventCreate",
    "AuditDailySummary",
    "IntegrationStatus",
    "PrivacyViolation",
    "EndOfDayReport",
    "DataClassification",
    # Logger
    "AuditLogger",
    "get_audit_logger",
    # Decorators
    "audit_operation",
    "audit_ingress",
    "audit_egress",
    "audit_transform",
    # Privacy
    "PrivacyEnforcer",
    "PrivacyViolationError",
]
