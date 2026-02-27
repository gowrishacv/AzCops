from __future__ import annotations

import uuid
from math import ceil
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import AuthenticatedUser, DbSession, TenantId
from app.core.logging import get_logger
from app.models.recommendation import RecommendationStatus
from app.repositories.recommendation import RecommendationRepository
from app.schemas.common import PaginatedResponse
from app.schemas.recommendation import (
    GenerateRequest,
    RecommendationResponse,
    RecommendationStatusUpdate,
)
from app.services.recommendation_service import RecommendationService

logger = get_logger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


# ---------------------------------------------------------------------------
# List recommendations (paginated + filtered)
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[RecommendationResponse])
async def list_recommendations(
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
    status_filter: RecommendationStatus | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    subscription_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedResponse[RecommendationResponse]:
    """List recommendations with optional filtering and pagination."""
    repo = RecommendationRepository(session)
    offset = (page - 1) * page_size

    recs = await repo.get_by_filters(
        tenant_id,
        status=status_filter,
        category=category,
        risk_level=risk_level,
        offset=offset,
        limit=page_size,
    )
    total = await repo.count_by_filters(
        tenant_id,
        status=status_filter,
        category=category,
        risk_level=risk_level,
    )

    return PaginatedResponse(
        items=[RecommendationResponse.from_recommendation(r) for r in recs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


# ---------------------------------------------------------------------------
# Get single recommendation
# ---------------------------------------------------------------------------

@router.get("/{rec_id}", response_model=RecommendationResponse)
async def get_recommendation(
    rec_id: str,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> RecommendationResponse:
    """Get a single recommendation by ID."""
    repo = RecommendationRepository(session)
    try:
        rec_uuid = uuid.UUID(rec_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid recommendation ID")

    rec = await repo.get_by_id(rec_uuid, tenant_id=tenant_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return RecommendationResponse.from_recommendation(rec)


# ---------------------------------------------------------------------------
# Status transition helpers
# ---------------------------------------------------------------------------

async def _do_transition(
    rec_id: str,
    session: DbSession,
    tenant_id: str,
    new_status: RecommendationStatus,
) -> RecommendationResponse:
    repo = RecommendationRepository(session)
    updated = await repo.transition_status(rec_id, tenant_id, new_status)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot transition recommendation to '{new_status.value}' from its current state, or recommendation not found.",
        )
    logger.info(
        "recommendation_status_changed",
        rec_id=rec_id,
        new_status=new_status.value,
        tenant_id=tenant_id,
    )
    return RecommendationResponse.from_recommendation(updated)


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------

@router.post("/{rec_id}/approve", response_model=RecommendationResponse)
async def approve_recommendation(
    rec_id: str,
    body: RecommendationStatusUpdate,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> RecommendationResponse:
    """Transition recommendation status to approved."""
    return await _do_transition(rec_id, session, tenant_id, RecommendationStatus.APPROVED)


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------

@router.post("/{rec_id}/reject", response_model=RecommendationResponse)
async def reject_recommendation(
    rec_id: str,
    body: RecommendationStatusUpdate,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> RecommendationResponse:
    """Transition recommendation status to rejected."""
    return await _do_transition(rec_id, session, tenant_id, RecommendationStatus.REJECTED)


# ---------------------------------------------------------------------------
# Dismiss
# ---------------------------------------------------------------------------

@router.post("/{rec_id}/dismiss", response_model=RecommendationResponse)
async def dismiss_recommendation(
    rec_id: str,
    body: RecommendationStatusUpdate,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> RecommendationResponse:
    """Transition recommendation status to dismissed."""
    return await _do_transition(rec_id, session, tenant_id, RecommendationStatus.DISMISSED)


# ---------------------------------------------------------------------------
# Execute (requires approved first)
# ---------------------------------------------------------------------------

@router.post("/{rec_id}/execute", response_model=RecommendationResponse)
async def execute_recommendation(
    rec_id: str,
    body: RecommendationStatusUpdate,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> RecommendationResponse:
    """Transition recommendation status to executed (must be approved first)."""
    return await _do_transition(rec_id, session, tenant_id, RecommendationStatus.EXECUTED)


# ---------------------------------------------------------------------------
# Generate (trigger rule engine)
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=dict)
async def generate_recommendations(
    body: GenerateRequest,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> dict:
    """
    Trigger the rule engine for a subscription and upsert recommendations.
    Returns the count of recommendations generated.
    """
    svc = RecommendationService(session)
    count = await svc.generate_for_subscription(
        tenant_id=tenant_id,
        subscription_db_id=body.subscription_db_id,
        subscription_id=body.subscription_id,
        vm_metrics=body.vm_metrics,
        compute_cost_30d=body.compute_cost_30d,
    )
    logger.info(
        "recommendations_generated",
        tenant_id=tenant_id,
        subscription_id=body.subscription_id,
        count=count,
    )
    return {
        "subscription_id": body.subscription_id,
        "recommendations_generated": count,
    }
