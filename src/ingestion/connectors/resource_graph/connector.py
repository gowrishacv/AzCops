"""
Resource Graph connector — discovers all Azure resources across subscriptions
using the Azure Resource Graph Query API with auto-pagination (1000 records/page).
"""
from __future__ import annotations

from typing import Any

import structlog

from ingestion.connectors.base import AzureHttpClient, BaseConnector, ConnectorContext
from ingestion.connectors.resource_graph import queries as Q

logger = structlog.get_logger(__name__)

ARG_API_VERSION = "2022-10-01"
ARG_ENDPOINT = "https://management.azure.com/providers/Microsoft.ResourceGraph/resources"
ARG_PAGE_SIZE = 1000


class ResourceGraphConnector(BaseConnector):
    """
    Queries Azure Resource Graph for full inventory snapshots.
    Handles pagination (skipToken) and cross-subscription batching.
    """

    async def collect(self, ctx: ConnectorContext) -> list[dict[str, Any]]:
        """Collect all resources for a single subscription."""
        ctx.operation_name = "resource_graph.all_resources"
        records = await self._run_query(Q.ALL_RESOURCES, ctx)
        logger.info(
            "resource_graph_collected",
            count=len(records),
            subscription_id=ctx.subscription_id,
            tenant_id=ctx.tenant_id,
        )
        return records

    async def collect_waste_candidates(self, ctx: ConnectorContext) -> dict[str, list[dict[str, Any]]]:
        """
        Run all waste-detection queries in parallel and return results by category.
        Used directly by the rule engine.
        """
        import asyncio

        ctx.operation_name = "resource_graph.waste_scan"
        results = await asyncio.gather(
            self._run_query(Q.UNATTACHED_DISKS, ctx),
            self._run_query(Q.ORPHANED_PUBLIC_IPS, ctx),
            self._run_query(Q.ORPHANED_NICS, ctx),
            self._run_query(Q.STALE_SNAPSHOTS, ctx),
            self._run_query(Q.MISSING_COST_CENTER_TAG, ctx),
        )
        return {
            "unattached_disks": results[0],
            "orphaned_public_ips": results[1],
            "orphaned_nics": results[2],
            "stale_snapshots": results[3],
            "missing_cost_center_tag": results[4],
        }

    async def collect_rightsizing_candidates(
        self, ctx: ConnectorContext
    ) -> dict[str, list[dict[str, Any]]]:
        """Run right-sizing discovery queries."""
        import asyncio

        ctx.operation_name = "resource_graph.rightsizing_scan"
        results = await asyncio.gather(
            self._run_query(Q.ALL_VMS, ctx),
            self._run_query(Q.APP_SERVICE_PLANS, ctx),
            self._run_query(Q.SQL_DATABASES, ctx),
        )
        return {
            "virtual_machines": results[0],
            "app_service_plans": results[1],
            "sql_databases": results[2],
        }

    async def _run_query(
        self,
        kql: str,
        ctx: ConnectorContext,
        *,
        subscriptions: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a KQL query against Resource Graph with skipToken pagination.
        Supports single subscription (default) or multi-subscription batch.
        """
        scope_subscriptions = subscriptions or [ctx.subscription_id]
        results: list[dict[str, Any]] = []
        skip_token: str | None = None

        while True:
            payload: dict[str, Any] = {
                "query": kql.strip(),
                "subscriptions": scope_subscriptions,
                "options": {"$top": ARG_PAGE_SIZE},
            }
            if skip_token:
                payload["options"]["$skipToken"] = skip_token

            data = await self._http.request(
                "POST",
                ARG_ENDPOINT,
                ctx,
                json=payload,
                params={"api-version": ARG_API_VERSION},
            )

            rows: list[dict[str, Any]] = data.get("data", {}).get("rows", [])
            columns: list[dict[str, Any]] = data.get("data", {}).get("columns", [])

            # Convert column/row format to list of dicts
            col_names = [c["name"] for c in columns]
            for row in rows:
                results.append(dict(zip(col_names, row)))

            skip_token = data.get("$skipToken")
            if not skip_token:
                break

            logger.debug(
                "resource_graph_paginating",
                page_results=len(rows),
                total_so_far=len(results),
                operation_name=ctx.operation_name,
                tenant_id=ctx.tenant_id,
            )

        return results
