"""
Azure Monitor Metrics connector — collects VM CPU and memory utilisation
over a 14-day window for right-sizing analysis.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from ingestion.connectors.base import BaseConnector, ConnectorContext

logger = structlog.get_logger(__name__)

MONITOR_API_VERSION = "2023-10-01"
LOOKBACK_DAYS = 14
AGGREGATION_INTERVAL = "PT1H"  # 1-hour granularity


class MonitorMetricsConnector(BaseConnector):
    """
    Queries Azure Monitor for VM-level CPU and memory metrics
    over the past 14 days. Returns per-resource utilisation stats
    (average, p95) used by right-sizing rules.
    """

    async def collect(self, ctx: ConnectorContext) -> list[dict[str, Any]]:
        """Collect metrics for all VMs in a subscription (via resource IDs passed in ctx.extra)."""
        ctx.operation_name = "monitor.vm_metrics"
        vm_resource_ids: list[str] = ctx.extra.get("vm_resource_ids", [])

        if not vm_resource_ids:
            logger.debug(
                "monitor_no_vms",
                subscription_id=ctx.subscription_id,
                tenant_id=ctx.tenant_id,
            )
            return []

        import asyncio
        tasks = [self._collect_vm_metrics(resource_id, ctx) for resource_id in vm_resource_ids]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        records: list[dict[str, Any]] = []
        for i, result in enumerate(results_nested):
            if isinstance(result, Exception):
                logger.warning(
                    "monitor_vm_metrics_failed",
                    resource_id=vm_resource_ids[i],
                    error=str(result),
                    tenant_id=ctx.tenant_id,
                )
            else:
                records.extend(result)  # type: ignore[arg-type]

        logger.info(
            "monitor_collected",
            vms_processed=len(vm_resource_ids),
            metric_records=len(records),
            subscription_id=ctx.subscription_id,
            tenant_id=ctx.tenant_id,
        )
        return records

    async def _collect_vm_metrics(
        self,
        resource_id: str,
        ctx: ConnectorContext,
    ) -> list[dict[str, Any]]:
        """Collect CPU + memory metrics for a single VM resource."""
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=LOOKBACK_DAYS)

        url = f"https://management.azure.com{resource_id}/providers/microsoft.insights/metrics"
        params = {
            "api-version": MONITOR_API_VERSION,
            "metricnames": "Percentage CPU,Available Memory Bytes",
            "aggregation": "Average,Maximum,Minimum",
            "interval": AGGREGATION_INTERVAL,
            "timespan": f"{start.isoformat()}/{end.isoformat()}",
        }

        data = await self._http.request("GET", url, ctx, params=params)
        return self._parse_metrics(resource_id, data, ctx.tenant_id, ctx.subscription_id)

    @staticmethod
    def _parse_metrics(
        resource_id: str,
        data: dict[str, Any],
        tenant_id: str,
        subscription_id: str,
    ) -> list[dict[str, Any]]:
        """Parse Monitor API metric response into per-metric stat records."""
        records: list[dict[str, Any]] = []
        for metric in data.get("value", []):
            metric_name = metric.get("name", {}).get("value", "")
            timeseries = metric.get("timeseries", [])
            if not timeseries:
                continue

            all_values: list[float] = []
            for series in timeseries:
                for point in series.get("data", []):
                    avg = point.get("average")
                    if avg is not None:
                        all_values.append(float(avg))

            if not all_values:
                continue

            sorted_vals = sorted(all_values)
            n = len(sorted_vals)
            p95_idx = max(0, int(n * 0.95) - 1)

            records.append({
                "resource_id": resource_id,
                "tenant_id": tenant_id,
                "subscription_id": subscription_id,
                "metric_name": metric_name,
                "avg_value": round(sum(all_values) / n, 2),
                "max_value": round(sorted_vals[-1], 2),
                "min_value": round(sorted_vals[0], 2),
                "p95_value": round(sorted_vals[p95_idx], 2),
                "sample_count": n,
                "lookback_days": LOOKBACK_DAYS,
                "unit": metric.get("unit", ""),
            })

        return records
