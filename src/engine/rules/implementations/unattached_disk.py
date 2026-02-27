from __future__ import annotations

from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult


class UnattachedDiskRule(BaseRule):
    rule_id = "WASTE-001"
    category = RuleCategory.WASTE
    description = "Detect unattached managed disks that are not mounted to any VM."

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.compute/disks":
            return None

        properties = resource.get("properties") or {}
        disk_state = properties.get("diskState", "")

        # Also support waste_candidates flag from ingestion layer
        waste_candidates = context.get("waste_candidates") or []
        is_waste_candidate = any(
            c.get("resource_id") == resource.get("resource_id")
            and c.get("type") == "unattached_disk"
            for c in waste_candidates
        )

        is_unattached = disk_state == "Unattached" or is_waste_candidate

        if not is_unattached:
            return None

        # Determine disk size
        disk_size_gb = (
            properties.get("diskSizeGB")
            or (resource.get("tags") or {}).get("disk_size_gb")
            or 128
        )
        try:
            disk_size_gb = float(disk_size_gb)
        except (TypeError, ValueError):
            disk_size_gb = 128.0

        savings = max(disk_size_gb * 0.05, 5.0)
        name = resource.get("name", resource.get("resource_id", ""))

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=round(savings, 2),
            confidence_score=0.95,
            risk_level=RiskLevel.LOW,
            effort_level=EffortLevel.LOW,
            short_description="Unattached managed disk — no active VM mount",
            detail=f"Disk {name} has been unattached. Deleting saves ~${savings:.2f}/month.",
            metadata={"disk_size_gb": disk_size_gb, "disk_state": disk_state},
        )


unattached_disk_rule = UnattachedDiskRule()
