from __future__ import annotations

from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult

# Monthly costs for common App Service Plan SKUs
_SKU_COST_LOOKUP: dict[str, float] = {
    "P1v2": 73.0,
    "P2v2": 146.0,
    "P3v2": 292.0,
    "P1v3": 95.0,
    "P2v3": 190.0,
    "P3v3": 380.0,
    "S1": 73.0,
    "S2": 146.0,
    "S3": 292.0,
}

_FREE_TIERS = {"Free", "Shared", "free", "shared"}
_SAVING_PCT = 0.30
_DEFAULT_PLAN_COST = 100.0

_OVER_PROVISIONED_SKUS = {"P1", "P2", "P3", "S2", "S3"}


def _sku_is_over_provisioned(sku_name: str | None) -> bool:
    """Return True for SKUs that are candidates for downsizing."""
    if not sku_name:
        return False
    # Check if name starts with over-provisioned prefix
    for prefix in _OVER_PROVISIONED_SKUS:
        if sku_name.startswith(prefix):
            return True
    return False


class UnderutilisedAppServiceRule(BaseRule):
    rule_id = "RESIZE-002"
    category = RuleCategory.RIGHTSIZING
    description = "Detect over-provisioned App Service Plans that can be downsized."

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.web/serverfarms":
            return None

        properties = resource.get("properties") or {}
        sku = properties.get("sku") or {}
        tier = sku.get("tier", "")
        sku_name = sku.get("name", "")

        # Skip free and shared tiers
        if tier in _FREE_TIERS:
            return None

        # Check if this SKU is a candidate for downsizing
        fires = False

        # Premium V2/V3 plans with single worker
        if "Premium" in tier or tier in ("PremiumV2", "PremiumV3"):
            fires = True

        # Over-provisioned SKU names
        if _sku_is_over_provisioned(sku_name):
            fires = True

        # Multiple workers on standard/premium plan
        num_workers = properties.get("numberOfWorkers", 1)
        try:
            num_workers = int(num_workers)
        except (TypeError, ValueError):
            num_workers = 1

        if tier in ("Standard", "Premium", "PremiumV2", "PremiumV3") and num_workers > 1:
            fires = True

        if not fires:
            return None

        # Estimate plan cost
        plan_cost = _SKU_COST_LOOKUP.get(sku_name, _DEFAULT_PLAN_COST)
        savings = round(plan_cost * _SAVING_PCT, 2)
        name = resource.get("name", resource.get("resource_id", ""))

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=savings,
            confidence_score=0.75,
            risk_level=RiskLevel.MEDIUM,
            effort_level=EffortLevel.MEDIUM,
            short_description="App Service Plan may be over-provisioned",
            detail=(
                f"App Service Plan {name} is running SKU {sku_name} (tier: {tier}) "
                f"with {num_workers} worker(s). Downsizing could save ~${savings:.2f}/month."
            ),
            metadata={
                "sku_name": sku_name,
                "tier": tier,
                "num_workers": num_workers,
                "estimated_plan_cost": plan_cost,
            },
        )


underutilised_app_service_rule = UnderutilisedAppServiceRule()
