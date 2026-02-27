"""
Ingestion orchestrator — coordinates all connectors for a given tenant's
subscriptions, writes raw data to storage, and upserts curated data to PostgreSQL.
Designed to support 100+ subscriptions with async parallel execution.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog
from azure.identity import DefaultAzureCredential
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.connectors.base import ConnectorContext
from ingestion.connectors.resource_graph.connector import ResourceGraphConnector
from ingestion.connectors.resource_graph.mapper import map_resources
from ingestion.connectors.cost_management.connector import CostManagementConnector
from ingestion.connectors.cost_management.mapper import map_cost_records
from ingestion.connectors.advisor.connector import AdvisorConnector
from ingestion.connectors.monitor.connector import MonitorMetricsConnector
from ingestion.orchestration.raw_storage import RawStorageWriter

logger = structlog.get_logger(__name__)

# Max subscriptions processed concurrently — prevents overwhelming Azure APIs
MAX_CONCURRENT_SUBSCRIPTIONS = 10


@dataclass
class SubscriptionIngestionResult:
    subscription_id: str
    resources_upserted: int = 0
    cost_records_upserted: int = 0
    advisor_records: int = 0
    monitor_records: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class TenantIngestionResult:
    tenant_id: str
    subscriptions_processed: int = 0
    subscriptions_failed: int = 0
    total_resources: int = 0
    total_cost_records: int = 0
    duration_ms: float = 0.0
    results: list[SubscriptionIngestionResult] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.results is None:
            self.results = []


class IngestionOrchestrator:
    """
    Runs full data ingestion for one or more tenants.
    Parallelises across subscriptions up to MAX_CONCURRENT_SUBSCRIPTIONS.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._credential = DefaultAzureCredential()
        self._raw_storage = RawStorageWriter()
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_SUBSCRIPTIONS)

    async def run_tenant(
        self,
        tenant_id: str,
        azure_tenant_id: str,
        subscriptions: list[dict[str, Any]],
        correlation_id: str = "",
    ) -> TenantIngestionResult:
        """
        Run ingestion for all subscriptions of a tenant.
        subscriptions: list of dicts with keys: id (DB UUID str), subscription_id (Azure GUID)
        """
        start = datetime.now(tz=timezone.utc)
        result = TenantIngestionResult(tenant_id=tenant_id)
        correlation_id = correlation_id or str(uuid.uuid4())

        logger.info(
            "ingestion_tenant_started",
            tenant_id=tenant_id,
            subscription_count=len(subscriptions),
            correlation_id=correlation_id,
        )

        tasks = [
            self._run_subscription(
                tenant_id=tenant_id,
                subscription_db_id=sub["id"],
                subscription_id=sub["subscription_id"],
                correlation_id=correlation_id,
            )
            for sub in subscriptions
        ]
        sub_results = await asyncio.gather(*tasks, return_exceptions=True)

        for sub, sub_result in zip(subscriptions, sub_results):
            if isinstance(sub_result, Exception):
                logger.error(
                    "ingestion_subscription_exception",
                    subscription_id=sub["subscription_id"],
                    error=str(sub_result),
                    tenant_id=tenant_id,
                )
                result.subscriptions_failed += 1
                result.results.append(
                    SubscriptionIngestionResult(
                        subscription_id=sub["subscription_id"],
                        errors=[str(sub_result)],
                    )
                )
            else:
                result.results.append(sub_result)  # type: ignore[arg-type]
                if sub_result.success:  # type: ignore[union-attr]
                    result.subscriptions_processed += 1
                    result.total_resources += sub_result.resources_upserted  # type: ignore[union-attr]
                    result.total_cost_records += sub_result.cost_records_upserted  # type: ignore[union-attr]
                else:
                    result.subscriptions_failed += 1

        end = datetime.now(tz=timezone.utc)
        result.duration_ms = (end - start).total_seconds() * 1000

        logger.info(
            "ingestion_tenant_completed",
            tenant_id=tenant_id,
            subscriptions_processed=result.subscriptions_processed,
            subscriptions_failed=result.subscriptions_failed,
            total_resources=result.total_resources,
            total_cost_records=result.total_cost_records,
            duration_ms=result.duration_ms,
            correlation_id=correlation_id,
        )
        return result

    async def _run_subscription(
        self,
        tenant_id: str,
        subscription_db_id: str,
        subscription_id: str,
        correlation_id: str,
    ) -> SubscriptionIngestionResult:
        """Run ingestion for a single subscription, guarded by semaphore."""
        async with self._semaphore:
            result = SubscriptionIngestionResult(subscription_id=subscription_id)
            ctx = ConnectorContext(
                tenant_id=tenant_id,
                subscription_id=subscription_id,
                correlation_id=correlation_id,
            )

            try:
                # 1. Resource Graph
                async with ResourceGraphConnector(self._credential) as rg:
                    raw_resources = await rg.collect(ctx)

                await self._raw_storage.write(tenant_id, "resource_graph", subscription_id, raw_resources)
                mapped = map_resources(raw_resources, tenant_id, subscription_db_id)
                await self._upsert_resources(mapped, subscription_db_id)
                result.resources_upserted = len(mapped)

                # 2. Cost Management
                async with CostManagementConnector(self._credential) as cm:
                    raw_costs = await cm.collect(ctx)

                await self._raw_storage.write(tenant_id, "cost_management", subscription_id, raw_costs)
                mapped_costs = map_cost_records(raw_costs, tenant_id, subscription_db_id)
                await self._upsert_costs(mapped_costs)
                result.cost_records_upserted = len(mapped_costs)

                # 3. Advisor (fire and store raw only — rules engine maps later)
                async with AdvisorConnector(self._credential) as adv:
                    raw_advisor = await adv.collect(ctx)
                await self._raw_storage.write(tenant_id, "advisor", subscription_id, raw_advisor)
                result.advisor_records = len(raw_advisor)

                # 4. Monitor metrics (VM IDs populated from resource graph results)
                vm_ids = [
                    r["resource_id"] for r in raw_resources
                    if r.get("type", "").startswith("microsoft.compute/virtualmachines")
                ]
                ctx.extra["vm_resource_ids"] = vm_ids

                async with MonitorMetricsConnector(self._credential) as mon:
                    raw_metrics = await mon.collect(ctx)
                await self._raw_storage.write(tenant_id, "monitor", subscription_id, raw_metrics)
                result.monitor_records = len(raw_metrics)

            except Exception as exc:
                logger.exception(
                    "ingestion_subscription_failed",
                    subscription_id=subscription_id,
                    tenant_id=tenant_id,
                    error=str(exc),
                )
                result.errors.append(str(exc))

            return result

    async def _upsert_resources(
        self, records: list[dict[str, Any]], subscription_db_id: str
    ) -> None:
        """Upsert resource records (insert or update on resource_id conflict)."""
        if not records:
            return
        from app.models.resource import Resource

        for record in records:
            stmt = pg_insert(Resource).values(**record)
            stmt = stmt.on_conflict_do_update(
                index_elements=["resource_id"],
                set_={
                    "name": stmt.excluded.name,
                    "type": stmt.excluded.type,
                    "resource_group": stmt.excluded.resource_group,
                    "location": stmt.excluded.location,
                    "tags": stmt.excluded.tags,
                    "properties": stmt.excluded.properties,
                    "last_seen": stmt.excluded.last_seen,
                },
            )
            await self._session.execute(stmt)
        await self._session.flush()

    async def _upsert_costs(self, records: list[dict[str, Any]]) -> None:
        """Upsert daily cost records (insert or update on sub+date+service+rg)."""
        if not records:
            return
        from app.models.cost import CostDaily

        for record in records:
            stmt = pg_insert(CostDaily).values(**record)
            stmt = stmt.on_conflict_do_update(
                # Note: unique constraint must exist on (subscription_db_id, date, service_name, resource_group)
                constraint="uq_costs_daily_sub_date_service_rg",
                set_={
                    "cost": stmt.excluded.cost,
                    "amortized_cost": stmt.excluded.amortized_cost,
                    "meter_category": stmt.excluded.meter_category,
                },
            )
            await self._session.execute(stmt)
        await self._session.flush()
