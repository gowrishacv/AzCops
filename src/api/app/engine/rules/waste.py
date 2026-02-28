"""Waste-detection rules – flag orphaned or unused Azure resources."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.base import Rule, RuleResult
from app.models.resource import Resource

# ---------------------------------------------------------------------------
# Approximate monthly cost look-up tables (USD) used for savings estimates.
# In production these would be pulled from Azure Retail Pricing API; the
# hard-coded values give reasonable order-of-magnitude estimates until then.
# ---------------------------------------------------------------------------
_DISK_SIZE_MONTHLY_COST: dict[str, float] = {
    "P10": 19.71,
    "P15": 38.42,
    "P20": 73.22,
    "P30": 135.17,
    "P40": 259.25,
    "P50": 491.52,
    "P60": 860.16,
    "P70": 1576.96,
    "P80": 3014.66,
    "E10": 9.60,
    "E15": 19.20,
    "E20": 38.40,
    "E30": 69.12,
    "E40": 132.10,
    "E50": 245.76,
    "S10": 5.89,
    "S15": 11.32,
    "S20": 21.76,
    "S30": 40.96,
    "S40": 79.87,
    "S50": 153.60,
}

_DEFAULT_DISK_MONTHLY_COST = 30.00
_PUBLIC_IP_MONTHLY_COST = 3.65  # Static Basic SKU
_NIC_MONTHLY_COST = 0.00  # NICs are free, but they incur indirect cost
_SNAPSHOT_GB_MONTHLY_COST = 0.05


class UnattachedDisksRule(Rule):
    """WASTE-001: Flag managed disks that are not attached to any VM.

    Unattached premium/standard disks still incur storage charges.  Deleting
    or downgrading them can yield immediate savings.
    """

    rule_id = "WASTE-001"
    category = "waste_detection"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        stmt = (
            select(Resource)
            .where(
                Resource.tenant_id == tenant_id,
                Resource.type == "microsoft.compute/disks",
                Resource.properties["diskState"].as_string() == "Unattached",
            )
        )
        result = await session.execute(stmt)
        resources = result.scalars().all()

        findings: list[RuleResult] = []
        for res in resources:
            disk_tier = (res.properties or {}).get("tier", "")
            disk_size_gb = (res.properties or {}).get("diskSizeGB", 0)
            monthly_cost = _DISK_SIZE_MONTHLY_COST.get(
                disk_tier, _DEFAULT_DISK_MONTHLY_COST
            )

            findings.append(
                RuleResult(
                    resource_db_id=str(res.id),
                    rule_id=self.rule_id,
                    category=self.category,
                    title=f"Unattached managed disk: {res.name}",
                    description=(
                        f"Managed disk '{res.name}' ({disk_size_gb} GB, tier "
                        f"{disk_tier or 'unknown'}) in resource group "
                        f"'{res.resource_group}' is not attached to any VM. "
                        f"Consider deleting it or moving to a cheaper tier."
                    ),
                    estimated_monthly_savings=monthly_cost,
                    confidence_score=0.95,
                    risk_level="low",
                    effort_level="low",
                )
            )
        return findings


class OrphanedPublicIPsRule(Rule):
    """WASTE-002: Detect public IP addresses not associated with any resource.

    Static public IPs incur a small hourly charge when not associated with a
    running resource.
    """

    rule_id = "WASTE-002"
    category = "waste_detection"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        stmt = (
            select(Resource)
            .where(
                Resource.tenant_id == tenant_id,
                Resource.type == "microsoft.network/publicipaddresses",
                Resource.properties["ipConfiguration"].as_string().is_(None),
            )
        )
        result = await session.execute(stmt)
        resources = result.scalars().all()

        findings: list[RuleResult] = []
        for res in resources:
            sku = (res.properties or {}).get("sku", {}).get("name", "Basic")
            monthly = _PUBLIC_IP_MONTHLY_COST if sku == "Basic" else 3.65

            findings.append(
                RuleResult(
                    resource_db_id=str(res.id),
                    rule_id=self.rule_id,
                    category=self.category,
                    title=f"Orphaned public IP: {res.name}",
                    description=(
                        f"Public IP '{res.name}' ({sku} SKU) in resource group "
                        f"'{res.resource_group}' is not associated with any "
                        f"resource. Release it to stop incurring charges."
                    ),
                    estimated_monthly_savings=monthly,
                    confidence_score=0.90,
                    risk_level="low",
                    effort_level="low",
                )
            )
        return findings


class OrphanedNICsRule(Rule):
    """WASTE-003: Detect network interfaces not bound to a VM.

    While NICs themselves are free, orphaned NICs often indicate incomplete
    clean-up and may be associated with NSGs or public IPs that *do* cost
    money.
    """

    rule_id = "WASTE-003"
    category = "waste_detection"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        stmt = (
            select(Resource)
            .where(
                Resource.tenant_id == tenant_id,
                Resource.type == "microsoft.network/networkinterfaces",
                Resource.properties["virtualMachine"].as_string().is_(None),
            )
        )
        result = await session.execute(stmt)
        resources = result.scalars().all()

        findings: list[RuleResult] = []
        for res in resources:
            findings.append(
                RuleResult(
                    resource_db_id=str(res.id),
                    rule_id=self.rule_id,
                    category=self.category,
                    title=f"Orphaned NIC: {res.name}",
                    description=(
                        f"Network interface '{res.name}' in resource group "
                        f"'{res.resource_group}' is not attached to any VM. "
                        f"It may hold associated NSGs or public IPs that incur "
                        f"cost. Review and delete if no longer needed."
                    ),
                    estimated_monthly_savings=_NIC_MONTHLY_COST,
                    confidence_score=0.85,
                    risk_level="low",
                    effort_level="low",
                )
            )
        return findings


class StaleSnapshotsRule(Rule):
    """WASTE-004: Flag disk snapshots older than 90 days.

    Snapshots stored in Standard storage cost ~$0.05/GB/month.  Snapshots
    taken for one-off operations are often forgotten and accumulate cost
    over time.
    """

    rule_id = "WASTE-004"
    category = "waste_detection"

    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=90)

        stmt = (
            select(Resource)
            .where(
                Resource.tenant_id == tenant_id,
                Resource.type == "microsoft.compute/snapshots",
                Resource.created_at < cutoff,
            )
        )
        result = await session.execute(stmt)
        resources = result.scalars().all()

        findings: list[RuleResult] = []
        for res in resources:
            disk_size_gb = (res.properties or {}).get("diskSizeGB", 128)
            monthly_cost = disk_size_gb * _SNAPSHOT_GB_MONTHLY_COST

            age_days = (datetime.now(tz=timezone.utc) - res.created_at).days

            findings.append(
                RuleResult(
                    resource_db_id=str(res.id),
                    rule_id=self.rule_id,
                    category=self.category,
                    title=f"Stale snapshot ({age_days}d old): {res.name}",
                    description=(
                        f"Snapshot '{res.name}' ({disk_size_gb} GB) in resource "
                        f"group '{res.resource_group}' was created {age_days} "
                        f"days ago. Consider deleting it if the backup is no "
                        f"longer required."
                    ),
                    estimated_monthly_savings=round(monthly_cost, 2),
                    confidence_score=0.80,
                    risk_level="medium",
                    effort_level="low",
                )
            )
        return findings
