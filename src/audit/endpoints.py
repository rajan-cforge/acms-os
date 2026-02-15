"""
Audit REST API Endpoints

Endpoints for viewing audit events, daily summaries, and reports.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from .models import (
    AuditEvent,
    AuditEventList,
    AuditEventFilter,
    AuditEventType,
    AuditDailySummary,
    DataClassification,
    EndOfDayReport,
    IntegrationStatus,
    PrivacyViolation,
)
from .logger import get_audit_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/audit", tags=["audit"])


# ============================================
# AUDIT EVENTS
# ============================================

@router.get("/events", response_model=AuditEventList)
async def list_audit_events(
    event_type: Optional[AuditEventType] = None,
    source: Optional[str] = None,
    destination: Optional[str] = None,
    data_classification: Optional[DataClassification] = None,
    success: Optional[bool] = None,
    correlation_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List audit events with optional filtering.

    Examples:
    - GET /api/v2/audit/events?source=gmail&limit=50
    - GET /api/v2/audit/events?event_type=egress&success=false
    - GET /api/v2/audit/events?correlation_id=...
    """
    try:
        audit = get_audit_logger()

        filter = AuditEventFilter(
            event_type=event_type,
            source=source,
            destination=destination,
            data_classification=data_classification,
            success=success,
            correlation_id=correlation_id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        result = await audit.get_events(filter)
        return result

    except Exception as e:
        logger.error(f"Failed to list audit events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/recent")
async def get_recent_events(
    limit: int = Query(default=50, le=200),
):
    """
    Get most recent audit events.
    Optimized for real-time UI display.
    """
    try:
        audit = get_audit_logger()

        filter = AuditEventFilter(limit=limit, offset=0)
        result = await audit.get_events(filter)

        # Format for UI display
        events = []
        for event in result.events:
            events.append({
                "id": str(event.id),
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "source": event.source,
                "operation": event.operation,
                "destination": event.destination,
                "item_count": event.item_count,
                "success": event.success,
                "duration_ms": event.duration_ms,
                "data_classification": event.data_classification.value if event.data_classification else None,
            })

        return {
            "status": "success",
            "events": events,
            "total_count": result.total_count,
        }

    except Exception as e:
        logger.error(f"Failed to get recent events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{event_id}")
async def get_audit_event(event_id: UUID):
    """Get a specific audit event by ID"""
    try:
        audit = get_audit_logger()

        filter = AuditEventFilter(limit=1, offset=0)
        # Note: Need to add specific ID lookup - for now use correlation_id
        # This is a simplified implementation

        raise HTTPException(status_code=501, detail="Not implemented yet")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# DAILY SUMMARIES
# ============================================

@router.get("/summary/today", response_model=AuditDailySummary)
async def get_today_summary():
    """Get today's audit summary"""
    try:
        audit = get_audit_logger()
        summary = await audit.get_daily_summary(date.today())

        if summary is None:
            return AuditDailySummary(date=date.today())

        return summary

    except Exception as e:
        logger.error(f"Failed to get today's summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{target_date}", response_model=AuditDailySummary)
async def get_daily_summary(target_date: date):
    """Get audit summary for a specific date"""
    try:
        audit = get_audit_logger()
        summary = await audit.get_daily_summary(target_date)

        if summary is None:
            return AuditDailySummary(date=target_date)

        return summary

    except Exception as e:
        logger.error(f"Failed to get daily summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/range")
async def get_summary_range(
    days: int = Query(default=7, le=90),
):
    """Get audit summaries for a date range"""
    try:
        audit = get_audit_logger()

        summaries = []
        for i in range(days):
            target_date = date.today() - timedelta(days=i)
            summary = await audit.get_daily_summary(target_date)
            if summary:
                summaries.append(summary)

        return {
            "status": "success",
            "days": days,
            "summaries": summaries,
        }

    except Exception as e:
        logger.error(f"Failed to get summary range: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# END OF DAY REPORT
# ============================================

@router.get("/report/today")
async def get_today_report():
    """Get comprehensive End of Day report for today"""
    try:
        audit = get_audit_logger()
        report = await audit.get_end_of_day_report(date.today())

        return {
            "status": "success",
            "report": report.model_dump(),
            "text_report": report.to_text(),
        }

    except Exception as e:
        logger.error(f"Failed to get today's report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{target_date}")
async def get_daily_report(target_date: date):
    """Get comprehensive End of Day report for a specific date"""
    try:
        audit = get_audit_logger()
        report = await audit.get_end_of_day_report(target_date)

        return {
            "status": "success",
            "report": report.model_dump(),
            "text_report": report.to_text(),
        }

    except Exception as e:
        logger.error(f"Failed to get daily report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# INTEGRATIONS
# ============================================

@router.get("/integrations", response_model=List[IntegrationStatus])
async def list_integrations():
    """Get status of all integrations"""
    try:
        audit = get_audit_logger()
        integrations = await audit.get_integration_statuses()
        return integrations

    except Exception as e:
        logger.error(f"Failed to get integrations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrations/{integration_id}", response_model=IntegrationStatus)
async def get_integration(integration_id: str):
    """Get status of a specific integration"""
    try:
        audit = get_audit_logger()
        integrations = await audit.get_integration_statuses()

        for integration in integrations:
            if integration.id == integration_id:
                return integration

        raise HTTPException(status_code=404, detail=f"Integration {integration_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PRIVACY
# ============================================

@router.get("/privacy/status")
async def get_privacy_status():
    """Get current privacy status - are all confidential items local?"""
    try:
        audit = get_audit_logger()
        summary = await audit.get_daily_summary(date.today())

        if summary is None:
            return {
                "status": "success",
                "privacy_status": "SECURE",
                "message": "No operations today",
                "confidential_items_processed": 0,
                "confidential_items_kept_local": 0,
                "confidential_items_external": 0,
            }

        return {
            "status": "success",
            "privacy_status": summary.privacy_status,
            "message": (
                "All confidential data stayed local"
                if summary.privacy_status == "SECURE"
                else "WARNING: Confidential data was sent externally!"
            ),
            "confidential_items_processed": summary.confidential_items_processed,
            "confidential_items_kept_local": summary.confidential_items_kept_local,
            "confidential_items_external": summary.confidential_items_external,
        }

    except Exception as e:
        logger.error(f"Failed to get privacy status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/violations")
async def get_privacy_violations(
    days: int = Query(default=7, le=90),
):
    """Get privacy violation attempts (should be empty if working correctly)"""
    try:
        from .logger import get_audit_logger

        audit = get_audit_logger()

        # Query violations from database
        query = """
            SELECT * FROM privacy_violations
            WHERE timestamp >= $1
            ORDER BY timestamp DESC
        """
        start_date = datetime.now() - timedelta(days=days)

        async with audit.db_pool.acquire() as conn:
            rows = await conn.fetch(query, start_date)

        violations = [PrivacyViolation(**dict(row)) for row in rows]

        return {
            "status": "success",
            "days": days,
            "total_violations": len(violations),
            "violations": [v.model_dump() for v in violations],
            "message": (
                "No privacy violations - all systems secure"
                if len(violations) == 0
                else f"WARNING: {len(violations)} privacy violation attempts detected and blocked"
            ),
        }

    except Exception as e:
        logger.error(f"Failed to get privacy violations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# DASHBOARD DATA
# ============================================

@router.get("/dashboard")
async def get_audit_dashboard():
    """
    Get all data needed for the Data Flow dashboard.
    Single endpoint for efficient UI loading.
    """
    try:
        audit = get_audit_logger()

        # Get today's summary
        today_summary = await audit.get_daily_summary(date.today())
        if today_summary is None:
            today_summary = AuditDailySummary(date=date.today())

        # Get last 7 days of summaries
        week_summaries = []
        for i in range(7):
            target_date = date.today() - timedelta(days=i)
            summary = await audit.get_daily_summary(target_date)
            if summary:
                week_summaries.append({
                    "date": summary.date.isoformat(),
                    "total_operations": summary.total_operations,
                    "ingress": (
                        summary.gmail_emails_fetched +
                        summary.calendar_events_synced +
                        summary.plaid_transactions_fetched +
                        summary.files_uploaded +
                        summary.chat_messages_received
                    ),
                    "egress": (
                        summary.llm_calls_claude +
                        summary.llm_calls_openai +
                        summary.llm_calls_gemini +
                        summary.browser_automations
                    ),
                    "success_rate": summary.success_rate,
                    "cost_usd": float(summary.llm_cost_usd),
                })

        # Get integrations
        integrations = await audit.get_integration_statuses()

        # Get recent events
        recent_filter = AuditEventFilter(limit=20, offset=0)
        recent_events = await audit.get_events(recent_filter)

        return {
            "status": "success",
            "today": {
                "date": today_summary.date.isoformat(),
                "total_operations": today_summary.total_operations,
                "success_rate": today_summary.success_rate,
                "privacy_status": today_summary.privacy_status,
                "ingress": {
                    "gmail_emails": today_summary.gmail_emails_fetched,
                    "calendar_events": today_summary.calendar_events_synced,
                    "plaid_transactions": today_summary.plaid_transactions_fetched,
                    "files_uploaded": today_summary.files_uploaded,
                    "chat_messages": today_summary.chat_messages_received,
                },
                "transforms": {
                    "summaries": today_summary.summaries_generated,
                    "embeddings": today_summary.embeddings_created,
                    "learning_signals": today_summary.learning_signals_captured,
                    "knowledge_facts": today_summary.knowledge_facts_extracted,
                    "memories": today_summary.memories_created,
                },
                "egress": {
                    "llm_calls_total": (
                        today_summary.llm_calls_claude +
                        today_summary.llm_calls_openai +
                        today_summary.llm_calls_gemini
                    ),
                    "llm_calls_claude": today_summary.llm_calls_claude,
                    "llm_calls_openai": today_summary.llm_calls_openai,
                    "llm_calls_gemini": today_summary.llm_calls_gemini,
                    "llm_tokens_total": today_summary.llm_tokens_input + today_summary.llm_tokens_output,
                    "llm_cost_usd": float(today_summary.llm_cost_usd),
                    "browser_automations": today_summary.browser_automations,
                },
                "errors": today_summary.failed_operations,
            },
            "week_trend": week_summaries,
            "integrations": [
                {
                    "id": i.id,
                    "is_connected": i.is_connected,
                    "health_status": i.health_status,
                    "last_sync_at": i.last_sync_at.isoformat() if i.last_sync_at else None,
                    "items_synced": i.items_synced,
                }
                for i in integrations
            ],
            "recent_events": [
                {
                    "id": str(e.id),
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type.value,
                    "source": e.source,
                    "operation": e.operation,
                    "destination": e.destination,
                    "success": e.success,
                    "duration_ms": e.duration_ms,
                }
                for e in recent_events.events
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get audit dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
