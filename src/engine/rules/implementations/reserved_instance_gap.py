from __future__ import annotations

from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult

# On-demand monthly cost per RI-eligible VM size
_RI_SIZE_COST_LOOKUP: dict[str, float] = {
    "Standard_D2s_v3": 96.0,
    "Standard_D4s_v3": 192.0,
    "Standard_D8s_v3": 384.0,
    "Standard_E2s_v3": 124.0,
    "Standard_E4s_v3": 248.0,
    "Standard_F2s_v2": 85.0,
    "Standard_F4s_v2": 170.0,
}

_RI_ELIGIBLE_SIZES = set(_RI_SIZE_COST_LOOKUP.keys())
_RI_SAVING_PCT = 0.30
_DEFAULT_VM_COST = 60.0


class ReservedInstanceGapRule(BaseRule):
    rule_id = "RATE-001"
    category = RuleCategory.RATE_OPTIMIZATION
    description = "Identify VMs running RI-eligible sizes without a reserved instance."

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.compute/virtualmachines":
            return None

        properties = resource.get("properties") or {}
        hardware_profile = properties.get("hardwareProfile") or {}
        vm_size = hardware_profile.get("vmSize", "")

        if not vm_size or vm_size not in _RI_ELIGIBLE_SIZES:
            return None

        on_demand_cost = _RI_SIZE_COST_LOOKUP.get(vm_size, _DEFAULT_VM_COST)
        savings = round(on_demand_cost * _RI_SAVING_PCT, 2)
        name = resource.get("name", resource.get("resource_id", ""))

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=savings,
            confidence_score=0.80,
            risk_level=RiskLevel.LOW,
            effort_level=EffortLevel.LOW,
            short_description=f"VM {vm_size} eligible for 1-year Reserved Instance — ~30% savings",
            detail=(
                f"VM {name} is running {vm_size} at ~${on_demand_cost:.2f}/month on-demand. "
                f"Purchasing a 1-year Reserved Instance saves ~${savings:.2f}/month (30%)."
            ),
            metadata={
                "vm_size": vm_size,
                "on_demand_cost": on_demand_cost,
                "ri_saving_pct": _RI_SAVING_PCT,
            },
        )


reserved_instance_gap_rule = ReservedInstanceGapRule()
