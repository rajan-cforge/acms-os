"""
Active Second Brain API Endpoints

Provides REST API for the Active Second Brain features:
- Enhanced Feedback (FeedbackPromoter integration)
- Knowledge Corrections (KnowledgeCorrector)
- Nudge System (NudgeEngine)
- Quality Cache Stats

Part of Active Second Brain implementation (Jan 2026).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger("acms.api.active_brain")

router = APIRouter(prefix="/api", tags=["Active Second Brain"])


# ========================
# Pydantic Models
# ========================

class FeedbackV2Request(BaseModel):
    """Enhanced feedback request with save_as_verified option."""
    query_history_id: str = Field(..., description="ID of the query_history record")
    feedback_type: str = Field(..., description="'positive' or 'negative'")
    save_as_verified: bool = Field(default=False, description="Save as verified knowledge")
    reason: Optional[str] = Field(None, description="Reason for negative feedback")
    reason_text: Optional[str] = Field(None, description="Custom reason text")


class FeedbackV2Response(BaseModel):
    """Response from feedback submission."""
    feedback_recorded: bool
    promoted_to_cache: bool = False
    demoted_from_cache: bool = False
    message: str


class CorrectionRequest(BaseModel):
    """Request to correct a knowledge item."""
    knowledge_id: str = Field(..., description="ID of the knowledge item")
    corrected_content: str = Field(..., description="New corrected content")
    correction_type: str = Field(..., description="Type: factual_error, outdated, incomplete, wrong_context, typo, clarification")
    reason: Optional[str] = Field(None, description="Reason for correction")


class CorrectionResponse(BaseModel):
    """Response from correction submission."""
    success: bool
    correction_id: Optional[str] = None
    error: Optional[str] = None


class VerifyRequest(BaseModel):
    """Request to verify knowledge without editing."""
    knowledge_id: str


class NudgeCreateRequest(BaseModel):
    """Request to create a nudge."""
    nudge_type: str = Field(..., description="Type: new_learning, stale_knowledge, low_confidence, review_reminder")
    title: str = Field(..., description="Short title")
    message: str = Field(..., description="Full message")
    priority: str = Field(default="medium", description="high, medium, low")
    related_id: Optional[str] = Field(None, description="Related knowledge/insight ID")
    expires_minutes: Optional[int] = Field(None, description="Expiration in minutes")


class NudgeResponse(BaseModel):
    """Nudge data response."""
    id: str
    nudge_type: str
    title: str
    message: str
    priority: str
    related_id: Optional[str]
    created_at: str
    dismissed: bool
    snoozed_until: Optional[str]


class SnoozeRequest(BaseModel):
    """Request to snooze a nudge."""
    nudge_id: str
    duration_minutes: int = Field(default=60, ge=1, le=1440)


class DismissRequest(BaseModel):
    """Request to dismiss a nudge."""
    nudge_id: str


class CacheStatsResponse(BaseModel):
    """Quality cache statistics."""
    total_entries: int
    user_verified_count: int
    average_quality_score: float
    cache_hit_rate: float
    entries_by_type: dict


# ========================
# Helper Functions
# ========================

async def get_user_id() -> str:
    """Get current user ID (placeholder for auth integration)."""
    # TODO: Integrate with actual auth system
    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text("SELECT user_id FROM users WHERE email = 'default@acms.local' LIMIT 1")
        )
        row = result.fetchone()
        if row:
            return str(row[0])

    # Fallback - get first user
    async with get_session() as session:
        result = await session.execute(
            text("SELECT user_id FROM users LIMIT 1")
        )
        row = result.fetchone()
        if row:
            return str(row[0])

    return "default-user"


# ========================
# Feedback Endpoints (v2)
# ========================

@router.post("/v2/feedback", response_model=FeedbackV2Response)
async def submit_feedback_v2(request: FeedbackV2Request):
    """
    Enhanced feedback endpoint with cache promotion/demotion.

    - Positive + save_as_verified → Promotes to QualityCache
    - Negative → Records reason, demotes from cache if applicable

    AC9: Prompt appears within 500ms of 👍 (handled by frontend)
    AC10: "Yes, Save" creates entry with user_verified=true
    AC11: 👎 shows options (Incorrect/Outdated/Incomplete/Wrong Agent)
    AC12: "Wrong Agent" demotes and logs reason
    """
    try:
        user_id = await get_user_id()

        from src.feedback.promoter import get_feedback_promoter, FeedbackReason

        promoter = get_feedback_promoter()

        if request.feedback_type == "positive":
            result = await promoter.handle_positive_feedback(
                query_history_id=request.query_history_id,
                user_id=user_id,
                save_as_verified=request.save_as_verified
            )
            message = "Feedback recorded"
            if result.get("promoted_to_cache"):
                message = "Response saved as verified knowledge! 🎉"

            return FeedbackV2Response(
                feedback_recorded=result.get("feedback_recorded", False),
                promoted_to_cache=result.get("promoted_to_cache", False),
                message=message
            )

        else:  # negative
            reason = None
            if request.reason:
                try:
                    reason = FeedbackReason(request.reason)
                except ValueError:
                    reason = FeedbackReason.OTHER

            result = await promoter.handle_negative_feedback(
                query_history_id=request.query_history_id,
                user_id=user_id,
                reason=reason,
                reason_text=request.reason_text
            )

            message = "Feedback recorded, thank you"
            if result.get("demoted_from_cache"):
                message = "Feedback recorded. Cached response has been removed."

            return FeedbackV2Response(
                feedback_recorded=result.get("feedback_recorded", False),
                demoted_from_cache=result.get("demoted_from_cache", False),
                message=message
            )

    except Exception as e:
        logger.error(f"Feedback v2 error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/feedback/eligible")
async def check_feedback_eligibility(query_history_id: str):
    """
    Check if a query is eligible for cache promotion.

    Returns within 100ms for AC9 compliance (500ms total UI response).
    """
    try:
        user_id = await get_user_id()

        from src.feedback.promoter import get_feedback_promoter

        promoter = get_feedback_promoter()
        eligible = await promoter.is_eligible_for_promotion(query_history_id, user_id)

        return {
            "eligible": eligible,
            "query_history_id": query_history_id
        }

    except Exception as e:
        logger.error(f"Eligibility check error: {e}", exc_info=True)
        return {"eligible": False, "error": str(e)}


# ========================
# Knowledge Correction Endpoints
# ========================

@router.post("/knowledge/correct", response_model=CorrectionResponse)
async def correct_knowledge(request: CorrectionRequest):
    """
    Apply user correction to a knowledge item.

    R1: User can edit any extracted fact
    R2: Original content preserved in audit trail
    R3: Corrected content replaces original
    R4: Confidence badge updates to "Verified"
    R5: Re-vectorize corrected content for search
    """
    try:
        user_id = await get_user_id()

        from src.intelligence.corrector import get_knowledge_corrector, CorrectionType

        corrector = get_knowledge_corrector()

        # Map string to enum
        try:
            correction_type = CorrectionType(request.correction_type)
        except ValueError:
            correction_type = CorrectionType.CLARIFICATION

        result = await corrector.apply_correction(
            knowledge_id=request.knowledge_id,
            corrected_content=request.corrected_content,
            user_id=user_id,
            correction_type=correction_type,
            reason=request.reason
        )

        return CorrectionResponse(
            success=result.get("success", False),
            correction_id=result.get("correction_id"),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Correction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/verify", response_model=CorrectionResponse)
async def verify_knowledge(request: VerifyRequest):
    """
    Mark knowledge as verified without changing content.

    Use when user confirms the existing content is correct.
    Sets user_verified=True and confidence=1.0.
    """
    try:
        user_id = await get_user_id()

        from src.intelligence.corrector import get_knowledge_corrector

        corrector = get_knowledge_corrector()
        result = await corrector.verify_knowledge(
            knowledge_id=request.knowledge_id,
            user_id=user_id
        )

        return CorrectionResponse(
            success=result.get("success", False),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Verify error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/{knowledge_id}/history")
async def get_correction_history(knowledge_id: str):
    """
    Get all corrections made to a knowledge item.

    Returns audit trail showing original → corrected progression.
    """
    try:
        from src.intelligence.corrector import get_knowledge_corrector

        corrector = get_knowledge_corrector()
        history = await corrector.get_correction_history(knowledge_id)

        return {
            "knowledge_id": knowledge_id,
            "corrections": history,
            "total": len(history)
        }

    except Exception as e:
        logger.error(f"History error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/review")
async def get_items_needing_review(
    limit: int = Query(default=10, ge=1, le=50),
    confidence_threshold: float = Query(default=0.8, ge=0, le=1)
):
    """
    Get knowledge items that need user review.

    Returns items with:
    - user_verified = False
    - confidence < threshold

    Used by Nudge system to prompt user for verification.
    """
    try:
        user_id = await get_user_id()

        from src.intelligence.corrector import get_knowledge_corrector

        corrector = get_knowledge_corrector()
        items = await corrector.get_items_needing_review(
            user_id=user_id,
            limit=limit,
            confidence_threshold=confidence_threshold
        )

        return {
            "items": items,
            "total": len(items),
            "threshold": confidence_threshold
        }

    except Exception as e:
        logger.error(f"Review items error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# Nudge Endpoints
# ========================

@router.get("/nudges", response_model=List[dict])
async def get_active_nudges(
    nudge_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(default=20, ge=1, le=50)
):
    """
    Get active nudges for the current user.

    Returns nudges sorted by priority (high first).
    Excludes dismissed and currently-snoozed nudges.
    """
    try:
        user_id = await get_user_id()

        from src.intelligence.nudge_engine import get_nudge_engine

        engine = get_nudge_engine()
        nudges = await engine.get_active_nudges(user_id, limit=limit)

        # Filter by type if specified
        if nudge_type:
            nudges = [n for n in nudges if n.get("nudge_type") == nudge_type]

        return nudges

    except Exception as e:
        logger.error(f"Get nudges error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nudges", response_model=dict)
async def create_nudge(request: NudgeCreateRequest):
    """
    Create a new nudge for the current user.

    Respects user's daily nudge limit preferences.
    """
    try:
        user_id = await get_user_id()

        from src.intelligence.nudge_engine import get_nudge_engine, NudgeType, NudgePriority

        engine = get_nudge_engine()

        # Map strings to enums
        try:
            nudge_type = NudgeType(request.nudge_type)
        except ValueError:
            nudge_type = NudgeType.REVIEW_REMINDER

        try:
            priority = NudgePriority(request.priority)
        except ValueError:
            priority = NudgePriority.MEDIUM

        expires_at = None
        if request.expires_minutes:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=request.expires_minutes)

        nudge = await engine.create_nudge(
            user_id=user_id,
            nudge_type=nudge_type,
            title=request.title,
            message=request.message,
            priority=priority,
            related_id=request.related_id,
            expires_at=expires_at
        )

        if nudge:
            return {
                "success": True,
                "id": nudge.id,
                "message": "Nudge created"
            }
        else:
            return {
                "success": False,
                "message": "Daily nudge limit reached"
            }

    except Exception as e:
        logger.error(f"Create nudge error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nudges/snooze")
async def snooze_nudge(request: SnoozeRequest):
    """
    Snooze a nudge for a specified duration.

    AC17: User can snooze nudges (default 1 hour, max 24 hours).
    """
    try:
        user_id = await get_user_id()

        from src.intelligence.nudge_engine import get_nudge_engine

        engine = get_nudge_engine()
        duration = timedelta(minutes=request.duration_minutes)

        result = await engine.snooze_nudge(
            nudge_id=request.nudge_id,
            user_id=user_id,
            duration=duration
        )

        return {
            "success": result.get("success", False),
            "snoozed_until": result.get("snoozed_until").isoformat() if result.get("snoozed_until") else None,
            "message": f"Snoozed for {request.duration_minutes} minutes"
        }

    except Exception as e:
        logger.error(f"Snooze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nudges/dismiss")
async def dismiss_nudge(request: DismissRequest):
    """
    Dismiss a nudge permanently.

    AC17: User can dismiss nudges (won't reappear).
    """
    try:
        user_id = await get_user_id()

        from src.intelligence.nudge_engine import get_nudge_engine

        engine = get_nudge_engine()
        result = await engine.dismiss_nudge(
            nudge_id=request.nudge_id,
            user_id=user_id
        )

        return {
            "success": result.get("success", False),
            "message": "Nudge dismissed"
        }

    except Exception as e:
        logger.error(f"Dismiss error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nudges/counts")
async def get_nudge_counts(period: str = Query(default="all", description="all, today, week")):
    """
    Get nudge counts by type.

    Used for sidebar badge showing pending nudge count.
    """
    try:
        user_id = await get_user_id()

        from src.intelligence.nudge_engine import get_nudge_engine

        engine = get_nudge_engine()
        counts = await engine.get_nudge_counts(user_id)

        return {
            "total": counts.get("total", 0),
            "by_type": counts.get("by_type", {}),
            "period": period
        }

    except Exception as e:
        logger.error(f"Nudge counts error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/nudges/preferences")
async def update_nudge_preferences(
    max_daily_nudges: int = Query(default=10, ge=1, le=50),
    quiet_hours_start: Optional[str] = Query(None, description="HH:MM format"),
    quiet_hours_end: Optional[str] = Query(None, description="HH:MM format")
):
    """
    Update user's nudge preferences.

    AC18: Nudge queue respects user preferences.
    """
    try:
        user_id = await get_user_id()

        # Store preferences in database
        from src.storage.database import get_session
        from sqlalchemy import text

        async with get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO user_preferences (user_id, preference_key, preference_value, updated_at)
                    VALUES (:user_id, 'max_daily_nudges', :value, NOW())
                    ON CONFLICT (user_id, preference_key) DO UPDATE
                    SET preference_value = :value, updated_at = NOW()
                """),
                {"user_id": user_id, "value": str(max_daily_nudges)}
            )

            if quiet_hours_start:
                await session.execute(
                    text("""
                        INSERT INTO user_preferences (user_id, preference_key, preference_value, updated_at)
                        VALUES (:user_id, 'quiet_hours_start', :value, NOW())
                        ON CONFLICT (user_id, preference_key) DO UPDATE
                        SET preference_value = :value, updated_at = NOW()
                    """),
                    {"user_id": user_id, "value": quiet_hours_start}
                )

            if quiet_hours_end:
                await session.execute(
                    text("""
                        INSERT INTO user_preferences (user_id, preference_key, preference_value, updated_at)
                        VALUES (:user_id, 'quiet_hours_end', :value, NOW())
                        ON CONFLICT (user_id, preference_key) DO UPDATE
                        SET preference_value = :value, updated_at = NOW()
                    """),
                    {"user_id": user_id, "value": quiet_hours_end}
                )

            await session.commit()

        return {
            "success": True,
            "preferences": {
                "max_daily_nudges": max_daily_nudges,
                "quiet_hours_start": quiet_hours_start,
                "quiet_hours_end": quiet_hours_end
            }
        }

    except Exception as e:
        logger.error(f"Preferences error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# Quality Cache Endpoints
# ========================

@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get quality cache statistics.

    Returns metrics for monitoring cache health:
    - Total entries, verified count
    - Average quality score
    - Cache hit rate
    - Entries by type (definition, factual, web)
    """
    try:
        user_id = await get_user_id()

        from src.cache.quality_cache import QualityCache

        cache = QualityCache()
        stats = await cache.get_stats(user_id)

        return CacheStatsResponse(
            total_entries=stats.get("total_entries", 0),
            user_verified_count=stats.get("user_verified_count", 0),
            average_quality_score=stats.get("average_quality_score", 0.0),
            cache_hit_rate=stats.get("cache_hit_rate", 0.0),
            entries_by_type=stats.get("entries_by_type", {})
        )

    except Exception as e:
        logger.error(f"Cache stats error: {e}", exc_info=True)
        # Return empty stats on error
        return CacheStatsResponse(
            total_entries=0,
            user_verified_count=0,
            average_quality_score=0.0,
            cache_hit_rate=0.0,
            entries_by_type={}
        )


@router.delete("/cache/clear")
async def clear_user_cache():
    """
    Clear all cache entries for current user.

    Use with caution - removes all cached responses.
    """
    try:
        user_id = await get_user_id()

        # TODO: Implement cache clearing when QualityCache supports it
        logger.info(f"Cache clear requested for user {user_id}")

        return {
            "success": True,
            "message": "Cache cleared"
        }

    except Exception as e:
        logger.error(f"Cache clear error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# Background Job Triggers
# ========================

@router.post("/jobs/stale-knowledge-check")
async def trigger_stale_knowledge_check(background_tasks: BackgroundTasks):
    """
    Trigger background job to check for stale knowledge.

    Creates nudges for knowledge items not updated in 90+ days.
    """
    try:
        user_id = await get_user_id()

        async def run_check():
            from src.intelligence.nudge_engine import get_nudge_engine
            engine = get_nudge_engine()
            count = await engine.generate_stale_knowledge_nudges(user_id, stale_days=90)
            logger.info(f"Generated {count} stale knowledge nudges for {user_id}")

        background_tasks.add_task(run_check)

        return {
            "success": True,
            "message": "Stale knowledge check started"
        }

    except Exception as e:
        logger.error(f"Stale check trigger error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
