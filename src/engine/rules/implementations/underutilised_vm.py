from __future__ import annotations

from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult

_CPU_THRESHOLD_PCT = 10.0
_DEFAULT_VM_COST = 200.0
_DOWNSIZE_SAVING_PCT = 0.30


class UnderutilisedVmRule(BaseRule):
    rule_id = "RESIZE-001"
    category = RuleCategory.RIGHTSIZING
    description = "Detect VMs with CPU utilisation below 10% over 14 days — resize candidates."

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.compute/virtualmachines":
            return None

        resource_id = resource.get("resource_id", "")
        vm_metrics = (context.get("vm_metrics") or {}).get(resource_id, {})

        if not vm_metrics:
            return None

        cpu_avg_pct = vm_metrics.get("cpu_avg_pct")
        if cpu_avg_pct is None:
            return None

        try:
            cpu_avg_pct = float(cpu_avg_pct)
        except (TypeError, ValueError):
            return None

        if cpu_avg_pct >= _CPU_THRESHOLD_PCT:
            return None

        # Estimate savings from downsizing one tier (~30% cost reduction)
        metadata = resource.get("metadata") or {}
        current_sku_cost = metadata.get("current_sku_cost")
        if current_sku_cost is not None:
            try:
                current_sku_cost = float(current_sku_cost)
            except (TypeError, ValueError):
                current_sku_cost = _DEFAULT_VM_COST
        else:
            current_sku_cost = _DEFAULT_VM_COST

        savings = round(current_sku_cost * _DOWNSIZE_SAVING_PCT, 2)
        name = resource.get("name", resource_id)

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=savings,
            confidence_score=0.85,
            risk_level=RiskLevel.MEDIUM,
            effort_level=EffortLevel.MEDIUM,
            short_description="VM CPU utilisation < 10% over 14 days — candidate for right-sizing",
            detail=(
                f"VM {name} has average CPU utilisation of {cpu_avg_pct:.1f}% over 14 days. "
                f"Downsizing one tier could save ~${savings:.2f}/month."
            ),
            metadata={
                "cpu_avg_pct": cpu_avg_pct,
                "current_sku_cost": current_sku_cost,
            },
        )


underutilised_vm_rule = UnderutilisedVmRule()
