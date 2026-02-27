"""
Ingestion management endpoints.
POST /api/v1/ingestion/trigger  — manually trigger ingestion for a tenant
GET  /api/v1/ingestion/status   — (stub) return last run metadata
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import AuthenticatedUser, DbSession, TenantId
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ingestion", tags=["Ingestion"])

# Simple in-memory run tracker (replace with DB table in production)
_run_registry: dict[str, dict] = {}


class IngestionTriggerRequest(BaseModel):
    tenant_db_id: uuid.UUID
    azure_tenant_id: str
    subscription_ids: list[str] = []  # empty = all active subscriptions


class IngestionTriggerResponse(BaseModel):
    run_id: str
    status: str = "queued"
    message: str


class IngestionStatusResponse(BaseModel):
    run_id: str
    status: str
    tenant_id: str
    started_at: str | None = None
    completed_at: str | None = None
    subscriptions_processed: int = 0
    subscriptions_failed: int = 0


async def _run_ingestion_background(
    run_id: str,
    tenant_id: str,
    azure_tenant_id: str,
    subscriptions: list[dict],
) -> None:
    """Background task that runs the full ingestion pipeline."""
    _run_registry[run_id]["status"] = "running"
    _run_registry[run_id]["started_at"] = datetime.now(tz=timezone.utc).isoformat()

    try:
        from app.core.database import async_session_factory
        from ingestion.orchestration.orchestrator import IngestionOrchestrator

        async with async_session_factory() as session:
            orchestrator = IngestionOrchestrator(session)
            result = await orchestrator.run_tenant(
                tenant_id=tenant_id,
                azure_tenant_id=azure_tenant_id,
                subscriptions=subscriptions,
                correlation_id=run_id,
            )
            await session.commit()

        _run_registry[run_id].update({
            "status": "completed",
            "completed_at": datetime.now(tz=timezone.utc).isoformat(),
            "subscriptions_processed": result.subscriptions_processed,
            "subscriptions_failed": result.subscriptions_failed,
        })
    except Exception as exc:
        logger.exception("ingestion_background_failed", run_id=run_id, error=str(exc))
        _run_registry[run_id].update({
            "status": "failed",
            "completed_at": datetime.now(tz=timezone.utc).isoformat(),
            "error": str(exc),
        })


@router.post("/trigger", response_model=IngestionTriggerResponse, status_code=202)
async def trigger_ingestion(
    request: IngestionTriggerRequest,
    background_tasks: BackgroundTasks,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> IngestionTriggerResponse:
    """
    Manually trigger ingestion for a tenant.
    Returns immediately with a run_id; ingestion runs asynchronously.
    """
    run_id = str(uuid.uuid4())

    # Load subscriptions from DB
    from sqlalchemy import select
    from app.models.subscription import Subscription

    sub_query = select(Subscription).where(
        Subscription.tenant_id == tenant_id,
        Subscription.is_active == True,  # noqa: E712
    )
    if request.subscription_ids:
        sub_query = sub_query.where(
            Subscription.subscription_id.in_(request.subscription_ids)
        )
    result = await session.execute(sub_query)
    subs = result.scalars().all()

    if not subs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscriptions found for this tenant",
        )

    subscriptions = [{"id": str(s.id), "subscription_id": s.subscription_id} for s in subs]
    _run_registry[run_id] = {
        "run_id": run_id,
        "status": "queued",
        "tenant_id": tenant_id,
        "subscriptions_processed": 0,
        "subscriptions_failed": 0,
        "started_at": None,
        "completed_at": None,
    }

    background_tasks.add_task(
        _run_ingestion_background,
        run_id,
        tenant_id,
        request.azure_tenant_id,
        subscriptions,
    )

    logger.info("ingestion_triggered", run_id=run_id, tenant_id=tenant_id)
    return IngestionTriggerResponse(
        run_id=run_id,
        status="queued",
        message=f"Ingestion queued for {len(subscriptions)} subscription(s). Use GET /ingestion/status/{run_id} to track.",
    )


@router.get("/status/{run_id}", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    run_id: str,
    user: AuthenticatedUser,
) -> IngestionStatusResponse:
    """Get the status of an ingestion run by run_id."""
    run = _run_registry.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return IngestionStatusResponse(**run)
