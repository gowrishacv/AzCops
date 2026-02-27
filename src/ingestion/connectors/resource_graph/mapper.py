"""
Maps raw Resource Graph API rows to Resource model dicts
ready for DB upsert.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def map_resource(row: dict[str, Any], tenant_id: str, subscription_db_id: str) -> dict[str, Any]:
    """
    Convert a Resource Graph result row into a Resource model dict.
    Handles tag coercion (ARG may return tags as string or dict).
    """
    tags = row.get("tags") or {}
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (ValueError, TypeError):
            tags = {}

    properties = row.get("properties") or {}
    if isinstance(properties, str):
        try:
            properties = json.loads(properties)
        except (ValueError, TypeError):
            properties = {}

    return {
        "tenant_id": tenant_id,
        "subscription_db_id": subscription_db_id,
        "resource_id": row.get("id", ""),
        "name": row.get("name", ""),
        "type": (row.get("type") or "").lower(),
        "resource_group": (row.get("resourceGroup") or "").lower(),
        "location": (row.get("location") or "").lower(),
        "tags": tags,
        "properties": properties,
        "last_seen": datetime.now(tz=timezone.utc),
    }


def map_resources(
    rows: list[dict[str, Any]],
    tenant_id: str,
    subscription_db_id: str,
) -> list[dict[str, Any]]:
    return [map_resource(r, tenant_id, subscription_db_id) for r in rows]
