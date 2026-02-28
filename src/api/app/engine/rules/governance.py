"""Governance rules – tagging compliance and budget monitoring."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.base import Rule, RuleResult
from app.models.cost import CostDaily
from app.models.resource import Resource

# Resource types where a CostCenter tag is expected
_TAGGABLE_RESOURCE_TYPES = {
    "microsoft.compute/virtualmachines",
    "microsoft.compute/disks",
    "microsoft.sql/servers",
    "microsoft.sql/servers/databases",
    "microsoft.storage/storageaccounts",
    "microsoft.web/serverfarms",
    "microsoft.web/sites",
    "microsoft.network/virtualnetworks",
    "microsoft.network/loadbalancers",
    "microsoft.containerservice/managedclusters",
    "microsoft.dbforpostgresql/flexibleservers",
    "microsoft.dbformysql/flexibleservers",
    "microsoft.keyvault/vaults",
    "microsoft.cache/redis",
}

# Default monthly budget per tenant (in production this comes from config)
_DEFAULT_MONTHLY_BUDGET = 10_000.00
_BUDGET_WARNING_THRESHOLD = 0.80  # 80%


class MissingCostCenterTagRule(Rule):
    """GOV-001: Flag resources that lack a CostCenter tag.

    A missing CostCenter tag makes it impossible to attribute costs to
    business units and undermines FinOps show-back / charge-back processes.
    """

    rule_id = "GOV-001"
    category = "governance"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        stmt = (
            select(Resource)
            .where(
                Resource.tenant_id == tenant_id,
                Resource.type.in_(_TAGGABLE_RESOURCE_TYPES),
            )
        )
        result = await session.execute(stmt)
        resources = result.scalars().all()

        findings: list[RuleResult] = []
        for res in resources:
            tags = res.tags or {}
            # Check case-insensitively
            tag_keys_lower = {k.lower() for k in tags}
            if "costcenter" in tag_keys_lower:
                continue

            findings.append(
                RuleResult(
                    resource_db_id=str(res.id),
                    rule_id=self.rule_id,
                    category=self.category,
                    title=f"Missing CostCenter tag: {res.name}",
                    description=(
                        f"Resource '{res.name}' (type: {res.type}) in resource "
                        f"group '{res.resource_group}' does not have a "
                        f"'CostCenter' tag. Add one to enable accurate cost "
                        f"attribution and show-back reporting."
                    ),
                    estimated_monthly_savings=0.0,
                    confidence_score=0.99,
                    risk_level="low",
                    effort_level="low",
                )
            )
        return findings


class BudgetThresholdRule(Rule):
    """GOV-002: Alert when a tenant is approaching its monthly budget.

    Compares month-to-date spend against a budget threshold (default 80%)
    and raises a governance finding so stakeholders can take action before
    overspend occurs.
    """

    rule_id = "GOV-002"
    category = "governance"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        today = date.today()
        first_of_month = today.replace(day=1)
        days_in_month = 30  # Simplified; could compute actual month length
        days_elapsed = (today - first_of_month).days + 1

        # Sum month-to-date spend for the entire tenant
        spend_stmt = (
            select(func.sum(CostDaily.cost))
            .where(
                CostDaily.tenant_id == tenant_id,
                CostDaily.date >= first_of_month,
                CostDaily.date <= today,
            )
        )
        result = await session.execute(spend_stmt)
        mtd_spend = float(result.scalar() or 0.0)

        if mtd_spend <= 0:
            return []

        budget = _DEFAULT_MONTHLY_BUDGET
        budget_used_pct = mtd_spend / budget if budget > 0 else 0.0

        if budget_used_pct < _BUDGET_WARNING_THRESHOLD:
            return []

        # Project end-of-month spend based on current burn rate
        daily_rate = mtd_spend / days_elapsed
        projected_monthly = daily_rate * days_in_month
        projected_overspend = max(0.0, projected_monthly - budget)

        return [
            RuleResult(
                resource_db_id=None,
                rule_id=self.rule_id,
                category=self.category,
                title=(
                    f"Budget alert: {budget_used_pct:.0%} consumed "
                    f"({days_elapsed}d into month)"
                ),
                description=(
                    f"Month-to-date spend is ${mtd_spend:,.2f} "
                    f"({budget_used_pct:.1%} of ${budget:,.2f} budget) with "
                    f"{days_in_month - days_elapsed} days remaining. "
                    f"Projected monthly total: ${projected_monthly:,.2f}. "
                    f"Projected overspend: ${projected_overspend:,.2f}. "
                    f"Review resource usage and consider scaling down "
                    f"non-critical workloads."
                ),
                estimated_monthly_savings=round(projected_overspend, 2),
                confidence_score=0.85,
                risk_level="high",
                effort_level="high",
            )
        ]
