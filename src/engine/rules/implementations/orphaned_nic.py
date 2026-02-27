from __future__ import annotations

from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult

_MONTHLY_COST = 0.50  # Negligible but flags for cleanup


class OrphanedNicRule(BaseRule):
    rule_id = "WASTE-003"
    category = RuleCategory.WASTE
    description = "Detect network interfaces not attached to any virtual machine."

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.network/networkinterfaces":
            return None

        properties = resource.get("properties") or {}
        virtual_machine = properties.get("virtualMachine")

        if virtual_machine is not None:
            return None

        name = resource.get("name", resource.get("resource_id", ""))

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=_MONTHLY_COST,
            confidence_score=0.90,
            risk_level=RiskLevel.LOW,
            effort_level=EffortLevel.LOW,
            short_description="Orphaned NIC — not attached to any VM",
            detail=(
                f"Network interface {name} has no virtualMachine association. "
                f"Deleting saves ~${_MONTHLY_COST:.2f}/month and reduces clutter."
            ),
            metadata={"virtual_machine": virtual_machine},
        )


orphaned_nic_rule = OrphanedNicRule()
