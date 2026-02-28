"""Right-sizing rules – identify over-provisioned Azure resources."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.base import Rule, RuleResult
from app.models.cost import CostDaily
from app.models.resource import Resource

# ---------------------------------------------------------------------------
# Approximate monthly cost by VM size family (USD).  Real implementations
# would query the Azure Retail Pricing API; these estimates are close
# enough for MVP confidence scoring and savings projections.
# ---------------------------------------------------------------------------
_VM_SIZE_MONTHLY_COST: dict[str, float] = {
    "Standard_B1s": 7.59,
    "Standard_B1ms": 15.18,
    "Standard_B2s": 30.37,
    "Standard_B2ms": 60.74,
    "Standard_D2s_v3": 70.08,
    "Standard_D4s_v3": 140.16,
    "Standard_D8s_v3": 280.32,
    "Standard_D16s_v3": 560.64,
    "Standard_D2s_v5": 70.08,
    "Standard_D4s_v5": 140.16,
    "Standard_D8s_v5": 280.32,
    "Standard_E2s_v3": 91.98,
    "Standard_E4s_v3": 183.96,
    "Standard_E8s_v3": 367.92,
    "Standard_F2s_v2": 61.32,
    "Standard_F4s_v2": 122.64,
    "Standard_F8s_v2": 245.28,
}

_APP_SERVICE_SKU_MONTHLY_COST: dict[str, float] = {
    "F1": 0.00,
    "D1": 9.49,
    "B1": 13.14,
    "B2": 26.28,
    "B3": 52.56,
    "S1": 73.00,
    "S2": 146.00,
    "S3": 292.00,
    "P1v2": 146.00,
    "P2v2": 292.00,
    "P3v2": 584.00,
    "P1v3": 146.00,
    "P2v3": 292.00,
    "P3v3": 584.00,
}

_SQL_DTU_TIER_MONTHLY_COST: dict[str, float] = {
    "Basic": 4.99,
    "S0": 15.03,
    "S1": 30.05,
    "S2": 75.13,
    "S3": 150.25,
    "S4": 300.50,
    "P1": 465.00,
    "P2": 930.00,
    "P4": 1860.00,
    "P6": 3720.00,
}


class UnderutilizedVMsRule(Rule):
    """SIZE-001: Detect VMs whose size suggests potential for downsizing.

    In the absence of live metrics, this heuristic flags VMs on large SKUs
    where the average daily spend (from CostDaily) is low relative to the
    SKU list price, indicating possible under-utilisation.
    """

    rule_id = "SIZE-001"
    category = "right_sizing"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        # Get all VMs for this tenant
        stmt = (
            select(Resource)
            .where(
                Resource.tenant_id == tenant_id,
                Resource.type == "microsoft.compute/virtualmachines",
            )
        )
        result = await session.execute(stmt)
        vms = result.scalars().all()

        findings: list[RuleResult] = []
        lookback = date.today() - timedelta(days=30)

        for vm in vms:
            vm_size = (vm.properties or {}).get("hardwareProfile", {}).get(
                "vmSize", ""
            )
            if not vm_size:
                vm_size = (vm.properties or {}).get("vmSize", "")

            list_price = _VM_SIZE_MONTHLY_COST.get(vm_size)
            if list_price is None or list_price < 60:
                # Skip VMs we cannot price or that are already small
                continue

            # Check recent daily costs for the resource group as a proxy
            cost_stmt = (
                select(func.avg(CostDaily.cost))
                .where(
                    CostDaily.tenant_id == tenant_id,
                    CostDaily.resource_group == vm.resource_group,
                    CostDaily.service_name.ilike("%virtual machines%"),
                    CostDaily.date >= lookback,
                )
            )
            cost_result = await session.execute(cost_stmt)
            avg_daily_cost = cost_result.scalar() or 0.0

            avg_monthly_cost = float(avg_daily_cost) * 30

            # If actual spend is less than 50% of list price, flag it
            if avg_monthly_cost < list_price * 0.5:
                estimated_savings = round(list_price * 0.40, 2)
                findings.append(
                    RuleResult(
                        resource_db_id=str(vm.id),
                        rule_id=self.rule_id,
                        category=self.category,
                        title=f"Potentially underutilized VM: {vm.name}",
                        description=(
                            f"VM '{vm.name}' ({vm_size}) in resource group "
                            f"'{vm.resource_group}' appears underutilized. "
                            f"Average monthly spend (${avg_monthly_cost:,.2f}) is "
                            f"well below the SKU list price (${list_price:,.2f}/mo). "
                            f"Consider downsizing to the next smaller SKU."
                        ),
                        estimated_monthly_savings=estimated_savings,
                        confidence_score=0.70,
                        risk_level="medium",
                        effort_level="medium",
                    )
                )
        return findings


class OversizedAppServiceRule(Rule):
    """SIZE-002: Flag App Service Plans that may be over-provisioned.

    Premium-tier App Service Plans with low traffic can often be moved to
    Standard or Basic tiers for significant savings.
    """

    rule_id = "SIZE-002"
    category = "right_sizing"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        stmt = (
            select(Resource)
            .where(
                Resource.tenant_id == tenant_id,
                Resource.type == "microsoft.web/serverfarms",
            )
        )
        result = await session.execute(stmt)
        plans = result.scalars().all()

        findings: list[RuleResult] = []
        lookback = date.today() - timedelta(days=30)

        for plan in plans:
            sku_name = (plan.properties or {}).get("sku", {}).get("name", "")
            if not sku_name:
                sku_name = (plan.properties or {}).get("skuName", "")

            list_price = _APP_SERVICE_SKU_MONTHLY_COST.get(sku_name)
            if list_price is None or list_price < 100:
                # Only flag premium/standard plans worth optimising
                continue

            # Check average daily cost for this resource group + App Service
            cost_stmt = (
                select(func.avg(CostDaily.cost))
                .where(
                    CostDaily.tenant_id == tenant_id,
                    CostDaily.resource_group == plan.resource_group,
                    CostDaily.service_name.ilike("%app service%"),
                    CostDaily.date >= lookback,
                )
            )
            cost_result = await session.execute(cost_stmt)
            avg_daily_cost = cost_result.scalar() or 0.0
            avg_monthly_cost = float(avg_daily_cost) * 30

            if avg_monthly_cost < list_price * 0.4:
                savings = round(list_price * 0.50, 2)
                findings.append(
                    RuleResult(
                        resource_db_id=str(plan.id),
                        rule_id=self.rule_id,
                        category=self.category,
                        title=f"Oversized App Service Plan: {plan.name}",
                        description=(
                            f"App Service Plan '{plan.name}' (SKU {sku_name}) "
                            f"in resource group '{plan.resource_group}' has low "
                            f"utilization (avg ${avg_monthly_cost:,.2f}/mo vs "
                            f"${list_price:,.2f}/mo list price). Consider "
                            f"downgrading to a smaller SKU."
                        ),
                        estimated_monthly_savings=savings,
                        confidence_score=0.65,
                        risk_level="medium",
                        effort_level="medium",
                    )
                )
        return findings


class SQLDTUUnderutilizedRule(Rule):
    """SIZE-003: Detect SQL databases with low DTU utilisation.

    Many Azure SQL databases are provisioned at S3/P1 and above but rarely
    exceed Basic/S0 workloads.  Downsizing the service tier can cut costs
    significantly.
    """

    rule_id = "SIZE-003"
    category = "right_sizing"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        stmt = (
            select(Resource)
            .where(
                Resource.tenant_id == tenant_id,
                Resource.type == "microsoft.sql/servers/databases",
            )
        )
        result = await session.execute(stmt)
        databases = result.scalars().all()

        findings: list[RuleResult] = []
        lookback = date.today() - timedelta(days=30)

        for db in databases:
            sku = (db.properties or {}).get("currentServiceObjectiveName", "")
            if not sku:
                sku = (db.properties or {}).get("requestedServiceObjectiveName", "")

            list_price = _SQL_DTU_TIER_MONTHLY_COST.get(sku)
            if list_price is None or list_price < 30:
                continue

            # Use cost data as a utilisation proxy
            cost_stmt = (
                select(func.avg(CostDaily.cost))
                .where(
                    CostDaily.tenant_id == tenant_id,
                    CostDaily.resource_group == db.resource_group,
                    CostDaily.service_name.ilike("%sql database%"),
                    CostDaily.date >= lookback,
                )
            )
            cost_result = await session.execute(cost_stmt)
            avg_daily_cost = cost_result.scalar() or 0.0
            avg_monthly_cost = float(avg_daily_cost) * 30

            if avg_monthly_cost < list_price * 0.35:
                # Estimate savings as difference to next lower tier
                savings = round(list_price * 0.50, 2)
                findings.append(
                    RuleResult(
                        resource_db_id=str(db.id),
                        rule_id=self.rule_id,
                        category=self.category,
                        title=f"Underutilized SQL Database: {db.name}",
                        description=(
                            f"SQL Database '{db.name}' (tier {sku}) in resource "
                            f"group '{db.resource_group}' appears underutilized. "
                            f"Average monthly cost (${avg_monthly_cost:,.2f}) "
                            f"suggests the workload would fit a smaller DTU tier. "
                            f"Consider downgrading to reduce spend."
                        ),
                        estimated_monthly_savings=savings,
                        confidence_score=0.65,
                        risk_level="medium",
                        effort_level="medium",
                    )
                )
        return findings
