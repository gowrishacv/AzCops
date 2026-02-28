"""Rate-optimisation rules – Reserved Instances and Savings Plans."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.base import Rule, RuleResult
from app.models.cost import CostDaily
from app.models.resource import Resource

# Average RI discount is ~35-40% for 1-year, ~55-60% for 3-year terms.
_RI_DISCOUNT_1YR = 0.37
_RI_DISCOUNT_3YR = 0.57
_SAVINGS_PLAN_DISCOUNT = 0.20  # Conservative estimate for Savings Plans

# Minimum daily cost to consider a VM "always on"
_MIN_DAILY_COST_ALWAYS_ON = 1.50

# Minimum 30-day run-rate to flag for Savings Plan
_MIN_MONTHLY_SPEND_FOR_SP = 500.00


class RICoverageGapRule(Rule):
    """RATE-001: Identify VMs running consistently without Reserved Instance coverage.

    VMs that run 24/7 (or near-continuously) are prime candidates for 1-year
    or 3-year Reserved Instance commitments, which can cut compute costs by
    35-60%.
    """

    rule_id = "RATE-001"
    category = "rate_optimization"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        # Identify VMs for this tenant
        vm_stmt = (
            select(Resource)
            .where(
                Resource.tenant_id == tenant_id,
                Resource.type == "microsoft.compute/virtualmachines",
            )
        )
        vm_result = await session.execute(vm_stmt)
        vms = vm_result.scalars().all()

        findings: list[RuleResult] = []
        lookback = date.today() - timedelta(days=30)
        lookback_days = 30

        for vm in vms:
            # Check how many days in the last 30 this VM's resource group
            # generated compute cost (proxy for uptime consistency).
            cost_stmt = (
                select(
                    func.count(func.distinct(CostDaily.date)),
                    func.avg(CostDaily.cost),
                )
                .where(
                    CostDaily.tenant_id == tenant_id,
                    CostDaily.resource_group == vm.resource_group,
                    CostDaily.service_name.ilike("%virtual machines%"),
                    CostDaily.date >= lookback,
                )
            )
            cost_result = await session.execute(cost_stmt)
            row = cost_result.one_or_none()
            if row is None:
                continue

            active_days, avg_daily_cost = row
            active_days = active_days or 0
            avg_daily_cost = float(avg_daily_cost or 0)

            # Only flag VMs that ran on >= 90% of days and have meaningful cost
            if active_days < lookback_days * 0.9:
                continue
            if avg_daily_cost < _MIN_DAILY_COST_ALWAYS_ON:
                continue

            monthly_cost = avg_daily_cost * 30
            savings_1yr = round(monthly_cost * _RI_DISCOUNT_1YR, 2)

            vm_size = (vm.properties or {}).get("hardwareProfile", {}).get(
                "vmSize", "unknown"
            )

            findings.append(
                RuleResult(
                    resource_db_id=str(vm.id),
                    rule_id=self.rule_id,
                    category=self.category,
                    title=f"RI candidate (always-on VM): {vm.name}",
                    description=(
                        f"VM '{vm.name}' ({vm_size}) ran on {active_days}/{lookback_days} "
                        f"days with avg daily cost of ${avg_daily_cost:,.2f}. "
                        f"A 1-year Reserved Instance could save ~${savings_1yr:,.2f}/mo "
                        f"({_RI_DISCOUNT_1YR:.0%} discount). A 3-year RI would "
                        f"save ~${round(monthly_cost * _RI_DISCOUNT_3YR, 2):,.2f}/mo."
                    ),
                    estimated_monthly_savings=savings_1yr,
                    confidence_score=0.80,
                    risk_level="low",
                    effort_level="low",
                )
            )
        return findings


class SavingsPlanOpportunitiesRule(Rule):
    """RATE-002: Recommend Azure Savings Plans for consistent compute spend.

    Savings Plans offer flexible discounts (vs. RI's instance-level lock-in)
    when total compute spend is predictable across services.
    """

    rule_id = "RATE-002"
    category = "rate_optimization"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        lookback = date.today() - timedelta(days=30)

        # Aggregate total compute spend per day for the tenant
        spend_stmt = (
            select(
                func.count(func.distinct(CostDaily.date)).label("active_days"),
                func.avg(CostDaily.cost).label("avg_daily"),
                func.stddev(CostDaily.cost).label("stddev_daily"),
                func.sum(CostDaily.cost).label("total"),
            )
            .where(
                CostDaily.tenant_id == tenant_id,
                CostDaily.service_name.ilike("%virtual machines%"),
                CostDaily.date >= lookback,
            )
        )
        result = await session.execute(spend_stmt)
        row = result.one_or_none()

        if row is None:
            return []

        active_days = row.active_days or 0
        avg_daily = float(row.avg_daily or 0)
        stddev_daily = float(row.stddev_daily or 0)
        total_spend = float(row.total or 0)

        monthly_spend = avg_daily * 30

        if monthly_spend < _MIN_MONTHLY_SPEND_FOR_SP:
            return []

        if active_days < 20:
            return []

        # Coefficient of variation – lower means more consistent spend
        cv = stddev_daily / avg_daily if avg_daily > 0 else 1.0

        if cv > 0.5:
            # Spend is too variable to recommend a Savings Plan confidently
            return []

        savings = round(monthly_spend * _SAVINGS_PLAN_DISCOUNT, 2)
        confidence = round(min(0.90, 0.70 + (1.0 - cv) * 0.25), 2)

        return [
            RuleResult(
                resource_db_id=None,
                rule_id=self.rule_id,
                category=self.category,
                title=f"Savings Plan opportunity (${monthly_spend:,.0f}/mo compute)",
                description=(
                    f"Tenant compute spend has been consistent over the last "
                    f"30 days (${total_spend:,.2f} total, CV={cv:.2f}). "
                    f"A Compute Savings Plan could save ~${savings:,.2f}/mo "
                    f"({_SAVINGS_PLAN_DISCOUNT:.0%} discount). "
                    f"Consider a 1-year commitment at ${avg_daily:,.2f}/day."
                ),
                estimated_monthly_savings=savings,
                confidence_score=confidence,
                risk_level="low",
                effort_level="low",
            )
        ]
