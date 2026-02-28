"""
Maps raw Cost Management rows to CostDaily model dicts for DB upsert.
"""
from __future__ import annotations

from datetime import date
from typing import Any


def map_cost_record(
    row: dict[str, Any],
    tenant_id: str,
    subscription_db_id: str,
) -> dict[str, Any]:
    """Convert a parsed cost row to a CostDaily model dict."""
    return {
        "tenant_id": tenant_id,
        "subscription_db_id": subscription_db_id,
        "date": row["date"] if isinstance(row["date"], date) else date.fromisoformat(str(row["date"])),
        "service_name": row.get("service_name") or "",
        "resource_group": row.get("resource_group") or "",
        "meter_category": row.get("meter_category"),
        "cost": float(row.get("cost") or 0.0),
        "amortized_cost": float(row.get("amortized_cost") or 0.0),
        "currency": row.get("currency") or "USD",
    }


def map_cost_records(
    rows: list[dict[str, Any]],
    tenant_id: str,
    subscription_db_id: str,
) -> list[dict[str, Any]]:
    return [map_cost_record(r, tenant_id, subscription_db_id) for r in rows]
