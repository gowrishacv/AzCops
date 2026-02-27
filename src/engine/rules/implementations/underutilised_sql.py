from __future__ import annotations

from typing import Any

from src.engine.rules.base import BaseRule, EffortLevel, RiskLevel, RuleCategory, RuleResult

# Approximate monthly costs by DTU / vCore tiers
_DTU_COST_LOOKUP: dict[str, float] = {
    "S2": 75.0,   # 50 DTU
    "S3": 150.0,  # 100 DTU
    "P1": 465.0,  # 125 DTU
    "P2": 930.0,  # 250 DTU
    "P4": 1860.0, # 500 DTU
}
_VCORE_4_COST = 610.0
_DEFAULT_DB_COST = 100.0
_SAVING_PCT = 0.40

# DTU-based tiers — use DTU threshold
_DTU_TIERS = {"Standard", "Premium"}
_DTU_THRESHOLD = 100

# vCore-based tiers — use vCore threshold
_VCORE_TIERS = {"BusinessCritical", "GeneralPurpose"}
_VCORE_THRESHOLD = 4


class UnderutilisedSqlRule(BaseRule):
    rule_id = "RESIZE-003"
    category = RuleCategory.RIGHTSIZING
    description = "Detect SQL Databases with excess DTU or vCore capacity."

    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.sql/servers/databases":
            return None

        properties = resource.get("properties") or {}
        sku = properties.get("sku") or {}
        tier = sku.get("tier", "")
        sku_name = sku.get("name", "")

        if tier not in _DTU_TIERS and tier not in _VCORE_TIERS:
            return None

        capacity = sku.get("capacity")
        if capacity is None:
            return None

        try:
            capacity = int(capacity)
        except (TypeError, ValueError):
            return None

        # Apply appropriate threshold based on tier type
        if tier in _DTU_TIERS:
            if capacity < _DTU_THRESHOLD:
                return None
        elif tier in _VCORE_TIERS:
            if capacity < _VCORE_THRESHOLD:
                return None

        # Estimate cost
        db_cost = _DTU_COST_LOOKUP.get(sku_name, None)
        if db_cost is None:
            if tier in _VCORE_TIERS and capacity >= _VCORE_THRESHOLD:
                db_cost = _VCORE_4_COST * (capacity / 4)
            else:
                db_cost = _DEFAULT_DB_COST

        savings = round(db_cost * _SAVING_PCT, 2)
        name = resource.get("name", resource.get("resource_id", ""))

        return self._make_result(
            resource=resource,
            context=context,
            estimated_monthly_savings=savings,
            confidence_score=0.70,
            risk_level=RiskLevel.HIGH,
            effort_level=EffortLevel.HIGH,
            short_description="SQL Database may have excess DTU/vCore capacity",
            detail=(
                f"SQL Database {name} is using SKU {sku_name} (tier: {tier}) "
                f"with capacity {capacity}. Right-sizing could save ~${savings:.2f}/month. "
                f"Note: database resize may cause brief downtime."
            ),
            metadata={
                "sku_name": sku_name,
                "tier": tier,
                "capacity": capacity,
                "estimated_db_cost": db_cost,
            },
        )


underutilised_sql_rule = UnderutilisedSqlRule()
