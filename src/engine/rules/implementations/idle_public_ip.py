from __future__ import annotations

from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult

_MONTHLY_COST = 3.65  # Standard static public IP / month


class IdlePublicIpRule(BaseRule):
    rule_id = "WASTE-002"
    category = RuleCategory.WASTE
    description = "Detect orphaned public IP addresses not associated with any resource."

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.network/publicipaddresses":
            return None

        properties = resource.get("properties") or {}

        # Check for any association
        ip_configuration = properties.get("ipConfiguration")
        nat_gateway = properties.get("natGateway")

        if ip_configuration is not None or nat_gateway is not None:
            return None

        name = resource.get("name", resource.get("resource_id", ""))

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=_MONTHLY_COST,
            confidence_score=0.90,
            risk_level=RiskLevel.LOW,
            effort_level=EffortLevel.LOW,
            short_description="Orphaned public IP — not associated with any resource",
            detail=(
                f"Public IP {name} has no ipConfiguration or natGateway association. "
                f"Deleting saves ~${_MONTHLY_COST:.2f}/month."
            ),
            metadata={"ip_configuration": ip_configuration, "nat_gateway": nat_gateway},
        )


idle_public_ip_rule = IdlePublicIpRule()
