from __future__ import annotations

from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult

_COMPUTE_COST_THRESHOLD = 500.0
_SAVINGS_PLAN_PCT = 0.15


class SavingsPlanOpportunityRule(BaseRule):
    rule_id = "RATE-002"
    category = RuleCategory.RATE_OPTIMIZATION
    description = (
        "Identify subscriptions with significant compute spend where an Azure Savings Plan "
        "could reduce costs by ~15%."
    )

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.compute/virtualmachines":
            return None

        compute_cost_30d = context.get("compute_cost_30d", 0.0)
        try:
            compute_cost_30d = float(compute_cost_30d)
        except (TypeError, ValueError):
            return None

        if compute_cost_30d < _COMPUTE_COST_THRESHOLD:
            return None

        savings = round(compute_cost_30d * _SAVINGS_PLAN_PCT, 2)
        name = resource.get("name", resource.get("resource_id", ""))

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=savings,
            confidence_score=0.70,
            risk_level=RiskLevel.LOW,
            effort_level=EffortLevel.LOW,
            short_description="Subscription has significant compute spend — Savings Plan may reduce costs",
            detail=(
                f"Subscription compute spend is ~${compute_cost_30d:.2f}/month. "
                f"An Azure Savings Plan could reduce costs by ~${savings:.2f}/month (15%). "
                f"Assessed on VM {name}."
            ),
            metadata={
                "compute_cost_30d": compute_cost_30d,
                "savings_plan_pct": _SAVINGS_PLAN_PCT,
            },
        )


savings_plan_opportunity_rule = SavingsPlanOpportunityRule()
