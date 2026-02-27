from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult

_STALE_DAYS = 90


def _parse_age_days(time_created: str | None) -> float | None:
    """Parse ISO timestamp and return age in days, or None if unparseable."""
    if not time_created:
        return None
    # Try common ISO formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ):
        try:
            dt = datetime.strptime(time_created, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            return (now - dt).total_seconds() / 86400
        except ValueError:
            continue
    return None


class StaleSnapshotRule(BaseRule):
    rule_id = "WASTE-004"
    category = RuleCategory.WASTE
    description = "Detect snapshots older than 90 days that are candidates for deletion."

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.compute/snapshots":
            return None

        properties = resource.get("properties") or {}
        time_created = properties.get("timeCreated")

        age_days: float | None = _parse_age_days(time_created)

        if age_days is None:
            # Fall back to metadata or default-assume stale
            metadata_age = (resource.get("metadata") or {}).get("age_days")
            if metadata_age is not None:
                try:
                    age_days = float(metadata_age)
                except (TypeError, ValueError):
                    age_days = _STALE_DAYS + 1  # default assume stale
            else:
                age_days = _STALE_DAYS + 1  # no timestamp — assume stale

        if age_days < _STALE_DAYS:
            return None

        # Determine snapshot size
        snapshot_size_gb = properties.get("diskSizeGB") or 128
        try:
            snapshot_size_gb = float(snapshot_size_gb)
        except (TypeError, ValueError):
            snapshot_size_gb = 128.0

        savings = max(snapshot_size_gb * 0.05, 5.0)
        name = resource.get("name", resource.get("resource_id", ""))

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=round(savings, 2),
            confidence_score=0.80,
            risk_level=RiskLevel.LOW,
            effort_level=EffortLevel.LOW,
            short_description="Stale snapshot older than 90 days",
            detail=(
                f"Snapshot {name} is ~{int(age_days)} days old (threshold: {_STALE_DAYS} days). "
                f"Deleting saves ~${savings:.2f}/month."
            ),
            metadata={"age_days": round(age_days, 1), "snapshot_size_gb": snapshot_size_gb},
        )


stale_snapshot_rule = StaleSnapshotRule()
