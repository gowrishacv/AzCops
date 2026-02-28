"""
Cost Management connector — ingests daily ActualCost and AmortizedCost
from the Azure Cost Management Query API.
Grouped by ResourceGroupName + ServiceName for curated storage.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import structlog

from ingestion.connectors.base import BaseConnector, ConnectorContext

logger = structlog.get_logger(__name__)

COST_MGMT_API_VERSION = "2023-11-01"


def _build_cost_endpoint(subscription_id: str) -> str:
    scope = f"/subscriptions/{subscription_id}"
    return (
        f"https://management.azure.com{scope}"
        f"/providers/Microsoft.CostManagement/query"
        f"?api-version={COST_MGMT_API_VERSION}"
    )


def _build_query_payload(
    cost_type: str,  # "ActualCost" | "AmortizedCost"
    from_date: date,
    to_date: date,
) -> dict[str, Any]:
    return {
        "type": cost_type,
        "timeframe": "Custom",
        "timePeriod": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        },
        "dataset": {
            "granularity": "Daily",
            "aggregation": {
                "totalCost": {"name": "Cost", "function": "Sum"},
            },
            "grouping": [
                {"type": "Dimension", "name": "ResourceGroupName"},
                {"type": "Dimension", "name": "ServiceName"},
                {"type": "Dimension", "name": "MeterCategory"},
            ],
        },
    }


class CostManagementConnector(BaseConnector):
    """
    Fetches daily cost data (ActualCost + AmortizedCost) for a subscription.
    Handles the column/row response format from Cost Management Query API.
    """

    async def collect(self, ctx: ConnectorContext) -> list[dict[str, Any]]:
        """
        Collect yesterday's costs for a subscription.
        Returns a list of normalised cost records.
        """
        ctx.operation_name = "cost_management.daily"
        yesterday = date.today() - timedelta(days=1)
        return await self.collect_range(ctx, from_date=yesterday, to_date=yesterday)

    async def collect_range(
        self,
        ctx: ConnectorContext,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """Collect costs for a custom date range."""
        import asyncio

        ctx.operation_name = "cost_management.range"
        url = _build_cost_endpoint(ctx.subscription_id)

        actual_task = self._http.request(
            "POST", url, ctx,
            json=_build_query_payload("ActualCost", from_date, to_date),
        )
        amortized_task = self._http.request(
            "POST", url, ctx,
            json=_build_query_payload("AmortizedCost", from_date, to_date),
        )

        actual_data, amortized_data = await asyncio.gather(actual_task, amortized_task)

        actual_rows = _parse_cost_response(actual_data)
        amortized_lookup = {
            (r["resource_group"], r["service_name"], r["date"]): r["cost"]
            for r in _parse_cost_response(amortized_data)
        }

        # Merge amortized cost into actual cost rows
        records: list[dict[str, Any]] = []
        for row in actual_rows:
            key = (row["resource_group"], row["service_name"], row["date"])
            row["amortized_cost"] = amortized_lookup.get(key, row["cost"])
            records.append(row)

        logger.info(
            "cost_management_collected",
            count=len(records),
            from_date=str(from_date),
            to_date=str(to_date),
            subscription_id=ctx.subscription_id,
            tenant_id=ctx.tenant_id,
        )
        return records


def _parse_cost_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse Cost Management Query API response (column/row format).
    Returns normalised list of dicts.
    """
    properties = data.get("properties", {})
    columns = properties.get("columns", [])
    rows = properties.get("rows", [])

    col_names = [c["name"] for c in columns]
    results: list[dict[str, Any]] = []

    for row in rows:
        raw = dict(zip(col_names, row))
        results.append({
            "date": _parse_date(raw.get("UsageDate") or raw.get("BillingMonth")),
            "resource_group": str(raw.get("ResourceGroupName") or "").lower(),
            "service_name": str(raw.get("ServiceName") or ""),
            "meter_category": str(raw.get("MeterCategory") or ""),
            "cost": float(raw.get("Cost") or 0.0),
            "amortized_cost": 0.0,  # filled in by caller
            "currency": str(raw.get("Currency") or "USD"),
        })

    return results


def _parse_date(raw: Any) -> date:
    """Parse YYYYMMDD integer or 'YYYY-MM-DD' string from Cost Management."""
    if raw is None:
        from datetime import date as _d
        return _d.today()
    s = str(raw)
    if len(s) == 8 and s.isdigit():
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return date.fromisoformat(s[:10])
