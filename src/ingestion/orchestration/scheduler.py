"""
Ingestion scheduler — cron-based scheduling for daily full ingestion
and hourly incremental cost ingestion.
Designed to run as an Azure Container App Job or standalone process.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from ingestion.orchestration.orchestrator import IngestionOrchestrator

logger = structlog.get_logger(__name__)


async def _load_active_tenants(session: AsyncSession) -> list[dict]:
    """Load all active tenants and their subscriptions from the database."""
    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.models.subscription import Subscription

    result = await session.execute(
        select(Tenant).where(Tenant.is_active == True)  # noqa: E712
    )
    tenants = result.scalars().all()

    tenant_data = []
    for tenant in tenants:
        subs_result = await session.execute(
            select(Subscription)
            .where(Subscription.tenant_db_id == tenant.id)
            .where(Subscription.is_active == True)  # noqa: E712
        )
        subs = subs_result.scalars().all()
        tenant_data.append({
            "id": str(tenant.id),
            "azure_tenant_id": tenant.azure_tenant_id,
            "subscriptions": [
                {"id": str(s.id), "subscription_id": s.subscription_id}
                for s in subs
            ],
        })

    return tenant_data


async def run_full_ingestion() -> None:
    """
    Run full ingestion for ALL tenants and subscriptions.
    Intended to be triggered daily (e.g. 02:00 UTC via cron).
    """
    run_id = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logger.info("scheduler_full_ingestion_start", run_id=run_id)

    async with async_session_factory() as session:
        tenants = await _load_active_tenants(session)
        orchestrator = IngestionOrchestrator(session)

        for tenant in tenants:
            await orchestrator.run_tenant(
                tenant_id=tenant["id"],
                azure_tenant_id=tenant["azure_tenant_id"],
                subscriptions=tenant["subscriptions"],
                correlation_id=f"scheduler-full-{run_id}",
            )
        await session.commit()

    logger.info("scheduler_full_ingestion_complete", run_id=run_id)


async def run_incremental_cost_ingestion() -> None:
    """
    Run cost-only ingestion for ALL tenants.
    Intended to be triggered hourly for near-real-time cost visibility.
    """
    run_id = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logger.info("scheduler_incremental_ingestion_start", run_id=run_id)

    async with async_session_factory() as session:
        tenants = await _load_active_tenants(session)
        for tenant in tenants:
            from ingestion.connectors.cost_management.connector import CostManagementConnector
            from ingestion.connectors.cost_management.mapper import map_cost_records
            from ingestion.connectors.base import ConnectorContext

            for sub in tenant["subscriptions"]:
                ctx = ConnectorContext(
                    tenant_id=tenant["id"],
                    subscription_id=sub["subscription_id"],
                    correlation_id=f"scheduler-incremental-{run_id}",
                    operation_name="incremental_cost",
                )
                async with CostManagementConnector() as cm:
                    raw_costs = await cm.collect(ctx)
                mapped = map_cost_records(raw_costs, tenant["id"], sub["id"])
                logger.info(
                    "incremental_cost_collected",
                    count=len(mapped),
                    subscription_id=sub["subscription_id"],
                )
        await session.commit()

    logger.info("scheduler_incremental_ingestion_complete", run_id=run_id)


if __name__ == "__main__":
    """Entry point for running as a standalone job."""
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    if mode == "incremental":
        asyncio.run(run_incremental_cost_ingestion())
    else:
        asyncio.run(run_full_ingestion())
