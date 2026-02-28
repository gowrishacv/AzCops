from __future__ import annotations

from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult

_REQUIRED_TAG = "cost-center"


class MissingCostCenterTagRule(BaseRule):
    rule_id = "GOV-001"
    category = RuleCategory.GOVERNANCE
    description = "Enforce presence of 'cost-center' tag on all resources for cost allocation."

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        tags = resource.get("tags") or {}

        if _REQUIRED_TAG in tags:
            return None

        resource_type = resource.get("type", "")
        name = resource.get("name", resource.get("resource_id", ""))

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=0.0,
            confidence_score=1.0,
            risk_level=RiskLevel.LOW,
            effort_level=EffortLevel.LOW,
            short_description="Resource missing required 'cost-center' tag",
            detail=f"Add 'cost-center' tag to {resource_type} {name} for cost allocation.",
            metadata={"missing_tag": _REQUIRED_TAG, "existing_tags": list(tags.keys())},
        )


missing_cost_center_tag_rule = MissingCostCenterTagRule()
