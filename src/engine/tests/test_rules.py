"""Unit tests for all 10 AzCops cost-optimization rules."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from src.engine.rules.base import RuleCategory, RiskLevel, EffortLevel
from src.engine.rules.implementations.unattached_disk import UnattachedDiskRule
from src.engine.rules.implementations.idle_public_ip import IdlePublicIpRule
from src.engine.rules.implementations.orphaned_nic import OrphanedNicRule
from src.engine.rules.implementations.stale_snapshot import StaleSnapshotRule
from src.engine.rules.implementations.underutilised_vm import UnderutilisedVmRule
from src.engine.rules.implementations.underutilised_app_service import UnderutilisedAppServiceRule
from src.engine.rules.implementations.underutilised_sql import UnderutilisedSqlRule
from src.engine.rules.implementations.reserved_instance_gap import ReservedInstanceGapRule
from src.engine.rules.implementations.savings_plan_opportunity import SavingsPlanOpportunityRule
from src.engine.rules.implementations.missing_cost_center_tag import MissingCostCenterTagRule
from src.engine.scoring.scorer import score, score_and_rank
from src.engine.engine import run_engine


# ---------------------------------------------------------------------------
# Shared context fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def base_context():
    return {
        "tenant_id": "tenant-abc",
        "subscription_id": "sub-123",
    }


# ---------------------------------------------------------------------------
# 1. UnattachedDiskRule
# ---------------------------------------------------------------------------

class TestUnattachedDiskRule:
    rule = UnattachedDiskRule()

    def _make_disk(self, disk_state="Unattached", size_gb=256):
        return {
            "resource_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/disks/my-disk",
            "type": "microsoft.compute/disks",
            "name": "my-disk",
            "resource_group": "rg",
            "properties": {"diskState": disk_state, "diskSizeGB": size_gb},
            "tags": {},
        }

    def test_fires_for_unattached_disk(self, base_context):
        result = self.rule.evaluate(self._make_disk("Unattached", 256), base_context)
        assert result is not None
        assert result.rule_id == "WASTE-001"
        assert result.category == RuleCategory.WASTE

    def test_savings_proportional_to_size(self, base_context):
        result_small = self.rule.evaluate(self._make_disk("Unattached", 100), base_context)
        result_large = self.rule.evaluate(self._make_disk("Unattached", 500), base_context)
        assert result_small is not None
        assert result_large is not None
        assert result_large.estimated_monthly_savings > result_small.estimated_monthly_savings

    def test_savings_minimum_five_dollars(self, base_context):
        # Very small disk — minimum $5
        result = self.rule.evaluate(self._make_disk("Unattached", 10), base_context)
        assert result is not None
        assert result.estimated_monthly_savings >= 5.0

    def test_does_not_fire_for_attached_disk(self, base_context):
        result = self.rule.evaluate(self._make_disk("Attached", 256), base_context)
        assert result is None

    def test_does_not_fire_for_non_disk_resource(self, base_context):
        resource = {
            "resource_id": "/sub/rg/providers/Microsoft.Compute/virtualMachines/vm1",
            "type": "microsoft.compute/virtualmachines",
            "name": "vm1",
            "resource_group": "rg",
            "properties": {},
        }
        result = self.rule.evaluate(resource, base_context)
        assert result is None

    def test_fires_via_waste_candidates_context(self, base_context):
        resource = {
            "resource_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/disks/orphan",
            "type": "microsoft.compute/disks",
            "name": "orphan",
            "resource_group": "rg",
            "properties": {"diskState": "Reserved", "diskSizeGB": 128},
        }
        context = {
            **base_context,
            "waste_candidates": [
                {"resource_id": resource["resource_id"], "type": "unattached_disk"}
            ],
        }
        result = self.rule.evaluate(resource, context)
        assert result is not None


# ---------------------------------------------------------------------------
# 2. IdlePublicIpRule
# ---------------------------------------------------------------------------

class TestIdlePublicIpRule:
    rule = IdlePublicIpRule()

    def _make_ip(self, has_ip_config=False, has_nat=False):
        properties: dict = {}
        if has_ip_config:
            properties["ipConfiguration"] = {"id": "/some/config"}
        if has_nat:
            properties["natGateway"] = {"id": "/some/nat"}
        return {
            "resource_id": "/sub/rg/providers/Microsoft.Network/publicIPAddresses/my-ip",
            "type": "microsoft.network/publicipaddresses",
            "name": "my-ip",
            "resource_group": "rg",
            "properties": properties,
        }

    def test_fires_when_no_ip_configuration(self, base_context):
        result = self.rule.evaluate(self._make_ip(), base_context)
        assert result is not None
        assert result.rule_id == "WASTE-002"
        assert result.estimated_monthly_savings == pytest.approx(3.65)

    def test_does_not_fire_when_ip_configuration_present(self, base_context):
        result = self.rule.evaluate(self._make_ip(has_ip_config=True), base_context)
        assert result is None

    def test_does_not_fire_when_nat_gateway_present(self, base_context):
        result = self.rule.evaluate(self._make_ip(has_nat=True), base_context)
        assert result is None

    def test_does_not_fire_for_wrong_type(self, base_context):
        resource = {"type": "microsoft.compute/disks", "properties": {}}
        result = self.rule.evaluate(resource, base_context)
        assert result is None


# ---------------------------------------------------------------------------
# 3. OrphanedNicRule
# ---------------------------------------------------------------------------

class TestOrphanedNicRule:
    rule = OrphanedNicRule()

    def _make_nic(self, has_vm=False):
        properties: dict = {}
        if has_vm:
            properties["virtualMachine"] = {"id": "/sub/rg/providers/Microsoft.Compute/virtualMachines/vm1"}
        return {
            "resource_id": "/sub/rg/providers/Microsoft.Network/networkInterfaces/nic1",
            "type": "microsoft.network/networkinterfaces",
            "name": "nic1",
            "resource_group": "rg",
            "properties": properties,
        }

    def test_fires_when_no_virtual_machine(self, base_context):
        result = self.rule.evaluate(self._make_nic(has_vm=False), base_context)
        assert result is not None
        assert result.rule_id == "WASTE-003"

    def test_does_not_fire_when_vm_associated(self, base_context):
        result = self.rule.evaluate(self._make_nic(has_vm=True), base_context)
        assert result is None

    def test_does_not_fire_for_wrong_type(self, base_context):
        result = self.rule.evaluate({"type": "microsoft.compute/disks", "properties": {}}, base_context)
        assert result is None


# ---------------------------------------------------------------------------
# 4. StaleSnapshotRule
# ---------------------------------------------------------------------------

class TestStaleSnapshotRule:
    rule = StaleSnapshotRule()

    def _iso(self, days_ago: int) -> str:
        dt = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _make_snapshot(self, days_old: int | None, size_gb: int = 256):
        properties: dict = {"diskSizeGB": size_gb}
        if days_old is not None:
            properties["timeCreated"] = self._iso(days_old)
        return {
            "resource_id": "/sub/rg/providers/Microsoft.Compute/snapshots/snap1",
            "type": "microsoft.compute/snapshots",
            "name": "snap1",
            "resource_group": "rg",
            "properties": properties,
        }

    def test_fires_for_snapshot_over_90_days(self, base_context):
        result = self.rule.evaluate(self._make_snapshot(120), base_context)
        assert result is not None
        assert result.rule_id == "WASTE-004"

    def test_does_not_fire_for_fresh_snapshot(self, base_context):
        result = self.rule.evaluate(self._make_snapshot(10), base_context)
        assert result is None

    def test_does_not_fire_for_exactly_89_days(self, base_context):
        result = self.rule.evaluate(self._make_snapshot(89), base_context)
        assert result is None

    def test_handles_missing_time_created_gracefully(self, base_context):
        # No timeCreated — assume stale, should fire
        result = self.rule.evaluate(self._make_snapshot(None), base_context)
        assert result is not None

    def test_savings_proportional_to_size(self, base_context):
        r_small = self.rule.evaluate(self._make_snapshot(120, 100), base_context)
        r_large = self.rule.evaluate(self._make_snapshot(120, 500), base_context)
        assert r_small is not None and r_large is not None
        assert r_large.estimated_monthly_savings > r_small.estimated_monthly_savings

    def test_does_not_fire_for_wrong_type(self, base_context):
        result = self.rule.evaluate({"type": "microsoft.compute/disks", "properties": {}}, base_context)
        assert result is None


# ---------------------------------------------------------------------------
# 5. UnderutilisedVmRule
# ---------------------------------------------------------------------------

class TestUnderutilisedVmRule:
    rule = UnderutilisedVmRule()

    def _make_vm(self, resource_id="vm-001"):
        return {
            "resource_id": resource_id,
            "type": "microsoft.compute/virtualmachines",
            "name": "my-vm",
            "resource_group": "rg",
            "properties": {},
        }

    def test_fires_when_cpu_below_threshold(self, base_context):
        context = {**base_context, "vm_metrics": {"vm-001": {"cpu_avg_pct": 5.0}}}
        result = self.rule.evaluate(self._make_vm("vm-001"), context)
        assert result is not None
        assert result.rule_id == "RESIZE-001"
        assert result.risk_level == RiskLevel.MEDIUM

    def test_does_not_fire_when_cpu_above_threshold(self, base_context):
        context = {**base_context, "vm_metrics": {"vm-001": {"cpu_avg_pct": 45.0}}}
        result = self.rule.evaluate(self._make_vm("vm-001"), context)
        assert result is None

    def test_does_not_fire_when_no_metrics(self, base_context):
        context = {**base_context, "vm_metrics": {}}
        result = self.rule.evaluate(self._make_vm("vm-001"), context)
        assert result is None

    def test_does_not_fire_for_non_vm(self, base_context):
        context = {**base_context, "vm_metrics": {"vm-001": {"cpu_avg_pct": 1.0}}}
        resource = {"resource_id": "vm-001", "type": "microsoft.compute/disks", "properties": {}}
        result = self.rule.evaluate(resource, context)
        assert result is None

    def test_savings_uses_current_sku_cost_if_provided(self, base_context):
        context = {**base_context, "vm_metrics": {"vm-001": {"cpu_avg_pct": 3.0}}}
        resource = {**self._make_vm("vm-001"), "metadata": {"current_sku_cost": 400.0}}
        result = self.rule.evaluate(resource, context)
        assert result is not None
        assert result.estimated_monthly_savings == pytest.approx(120.0)

    def test_detail_includes_cpu_pct(self, base_context):
        context = {**base_context, "vm_metrics": {"vm-001": {"cpu_avg_pct": 7.5}}}
        result = self.rule.evaluate(self._make_vm("vm-001"), context)
        assert result is not None
        assert "7.5" in result.detail


# ---------------------------------------------------------------------------
# 6. UnderutilisedAppServiceRule
# ---------------------------------------------------------------------------

class TestUnderutilisedAppServiceRule:
    rule = UnderutilisedAppServiceRule()

    def _make_plan(self, sku_name="P2v2", tier="PremiumV2", num_workers=2):
        return {
            "resource_id": "/sub/rg/providers/Microsoft.Web/serverFarms/plan1",
            "type": "microsoft.web/serverfarms",
            "name": "plan1",
            "resource_group": "rg",
            "properties": {
                "sku": {"name": sku_name, "tier": tier},
                "numberOfWorkers": num_workers,
            },
        }

    def test_fires_for_premium_v2_plan(self, base_context):
        result = self.rule.evaluate(self._make_plan("P2v2", "PremiumV2"), base_context)
        assert result is not None
        assert result.rule_id == "RESIZE-002"

    def test_does_not_fire_for_free_tier(self, base_context):
        result = self.rule.evaluate(self._make_plan("F1", "Free", 1), base_context)
        assert result is None

    def test_does_not_fire_for_shared_tier(self, base_context):
        result = self.rule.evaluate(self._make_plan("D1", "Shared", 1), base_context)
        assert result is None

    def test_does_not_fire_for_wrong_type(self, base_context):
        result = self.rule.evaluate({"type": "microsoft.compute/disks", "properties": {}}, base_context)
        assert result is None

    def test_savings_based_on_sku_lookup(self, base_context):
        result = self.rule.evaluate(self._make_plan("P2v2", "PremiumV2"), base_context)
        assert result is not None
        # P2v2 = $146, 30% saving = $43.80
        assert result.estimated_monthly_savings == pytest.approx(43.80)


# ---------------------------------------------------------------------------
# 7. UnderutilisedSqlRule
# ---------------------------------------------------------------------------

class TestUnderutilisedSqlRule:
    rule = UnderutilisedSqlRule()

    def _make_db(self, tier="Premium", sku_name="P1", capacity=125):
        return {
            "resource_id": "/sub/rg/providers/Microsoft.Sql/servers/srv/databases/db1",
            "type": "microsoft.sql/servers/databases",
            "name": "db1",
            "resource_group": "rg",
            "properties": {
                "sku": {"tier": tier, "name": sku_name, "capacity": capacity}
            },
        }

    def test_fires_for_premium_db(self, base_context):
        result = self.rule.evaluate(self._make_db("Premium", "P1", 125), base_context)
        assert result is not None
        assert result.rule_id == "RESIZE-003"
        assert result.risk_level == RiskLevel.HIGH

    def test_does_not_fire_for_basic_tier(self, base_context):
        result = self.rule.evaluate(self._make_db("Basic", "B", 5), base_context)
        assert result is None

    def test_does_not_fire_below_capacity_threshold(self, base_context):
        # S1 = Standard tier, 20 DTU — below both thresholds
        result = self.rule.evaluate(self._make_db("Standard", "S1", 20), base_context)
        assert result is None

    def test_does_not_fire_for_wrong_type(self, base_context):
        result = self.rule.evaluate({"type": "microsoft.compute/disks", "properties": {}}, base_context)
        assert result is None

    def test_fires_for_general_purpose_vcores(self, base_context):
        result = self.rule.evaluate(self._make_db("GeneralPurpose", "GP_Gen5_4", 4), base_context)
        assert result is not None
        assert result.estimated_monthly_savings > 0


# ---------------------------------------------------------------------------
# 8. ReservedInstanceGapRule
# ---------------------------------------------------------------------------

class TestReservedInstanceGapRule:
    rule = ReservedInstanceGapRule()

    def _make_vm(self, vm_size="Standard_D4s_v3"):
        return {
            "resource_id": "/sub/rg/providers/Microsoft.Compute/virtualMachines/vm1",
            "type": "microsoft.compute/virtualmachines",
            "name": "vm1",
            "resource_group": "rg",
            "properties": {"hardwareProfile": {"vmSize": vm_size}},
        }

    def test_fires_for_d4s_v3(self, base_context):
        result = self.rule.evaluate(self._make_vm("Standard_D4s_v3"), base_context)
        assert result is not None
        assert result.rule_id == "RATE-001"
        assert result.category == RuleCategory.RATE_OPTIMIZATION

    def test_savings_for_d4s_v3(self, base_context):
        result = self.rule.evaluate(self._make_vm("Standard_D4s_v3"), base_context)
        assert result is not None
        # D4s_v3 = $192 * 0.30 = $57.60
        assert result.estimated_monthly_savings == pytest.approx(57.60)

    def test_does_not_fire_for_non_ri_eligible_size(self, base_context):
        result = self.rule.evaluate(self._make_vm("Standard_A1_v2"), base_context)
        assert result is None

    def test_does_not_fire_for_wrong_type(self, base_context):
        result = self.rule.evaluate({"type": "microsoft.compute/disks", "properties": {}}, base_context)
        assert result is None

    def test_fires_for_e4s_v3(self, base_context):
        result = self.rule.evaluate(self._make_vm("Standard_E4s_v3"), base_context)
        assert result is not None
        assert result.estimated_monthly_savings == pytest.approx(74.40)


# ---------------------------------------------------------------------------
# 9. SavingsPlanOpportunityRule
# ---------------------------------------------------------------------------

class TestSavingsPlanOpportunityRule:
    rule = SavingsPlanOpportunityRule()

    def _make_vm(self):
        return {
            "resource_id": "/sub/rg/providers/Microsoft.Compute/virtualMachines/vm1",
            "type": "microsoft.compute/virtualmachines",
            "name": "vm1",
            "resource_group": "rg",
            "properties": {},
        }

    def test_fires_when_compute_cost_above_threshold(self, base_context):
        context = {**base_context, "compute_cost_30d": 1000.0}
        result = self.rule.evaluate(self._make_vm(), context)
        assert result is not None
        assert result.rule_id == "RATE-002"

    def test_savings_is_15pct_of_compute_cost(self, base_context):
        context = {**base_context, "compute_cost_30d": 2000.0}
        result = self.rule.evaluate(self._make_vm(), context)
        assert result is not None
        assert result.estimated_monthly_savings == pytest.approx(300.0)

    def test_does_not_fire_below_threshold(self, base_context):
        context = {**base_context, "compute_cost_30d": 499.0}
        result = self.rule.evaluate(self._make_vm(), context)
        assert result is None

    def test_does_not_fire_for_wrong_type(self, base_context):
        resource = {"type": "microsoft.compute/disks", "properties": {}}
        context = {**base_context, "compute_cost_30d": 2000.0}
        result = self.rule.evaluate(resource, context)
        assert result is None

    def test_does_not_fire_when_no_compute_cost(self, base_context):
        result = self.rule.evaluate(self._make_vm(), base_context)
        assert result is None


# ---------------------------------------------------------------------------
# 10. MissingCostCenterTagRule
# ---------------------------------------------------------------------------

class TestMissingCostCenterTagRule:
    rule = MissingCostCenterTagRule()

    def _make_resource(self, tags: dict | None = None):
        return {
            "resource_id": "/sub/rg/providers/Microsoft.Compute/virtualMachines/vm1",
            "type": "microsoft.compute/virtualmachines",
            "name": "vm1",
            "resource_group": "rg",
            "properties": {},
            "tags": tags or {},
        }

    def test_fires_when_no_cost_center_tag(self, base_context):
        result = self.rule.evaluate(self._make_resource({"env": "prod"}), base_context)
        assert result is not None
        assert result.rule_id == "GOV-001"
        assert result.category == RuleCategory.GOVERNANCE

    def test_does_not_fire_when_cost_center_tag_present(self, base_context):
        result = self.rule.evaluate(
            self._make_resource({"cost-center": "engineering", "env": "prod"}), base_context
        )
        assert result is None

    def test_fires_when_tags_is_none(self, base_context):
        resource = self._make_resource()
        resource["tags"] = None
        result = self.rule.evaluate(resource, base_context)
        assert result is not None

    def test_fires_when_tags_is_missing(self, base_context):
        resource = {
            "resource_id": "/sub/rg/vm1",
            "type": "microsoft.compute/virtualmachines",
            "name": "vm1",
            "resource_group": "rg",
        }
        result = self.rule.evaluate(resource, base_context)
        assert result is not None

    def test_savings_is_zero(self, base_context):
        result = self.rule.evaluate(self._make_resource(), base_context)
        assert result is not None
        assert result.estimated_monthly_savings == 0.0

    def test_confidence_is_1(self, base_context):
        result = self.rule.evaluate(self._make_resource(), base_context)
        assert result is not None
        assert result.confidence_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 11. Scorer
# ---------------------------------------------------------------------------

class TestScorer:
    def _make_result(self, savings, confidence, risk_level, rule_id="TEST-001"):
        from src.engine.rules.base import RuleResult, RuleCategory
        return RuleResult(
            rule_id=rule_id,
            category=RuleCategory.WASTE,
            resource_id="r1",
            resource_type="microsoft.compute/disks",
            resource_name="disk1",
            resource_group="rg",
            subscription_id="sub",
            tenant_id="tenant",
            estimated_monthly_savings=savings,
            confidence_score=confidence,
            risk_level=risk_level,
            effort_level=EffortLevel.LOW,
            short_description="test",
            detail="test detail",
        )

    def test_low_risk_weight_is_1(self):
        result = self._make_result(100.0, 1.0, RiskLevel.LOW)
        scored = score(result)
        assert scored.priority_score == pytest.approx(100.0)

    def test_medium_risk_weight_is_0_7(self):
        result = self._make_result(100.0, 1.0, RiskLevel.MEDIUM)
        scored = score(result)
        assert scored.priority_score == pytest.approx(70.0)

    def test_high_risk_weight_is_0_4(self):
        result = self._make_result(100.0, 1.0, RiskLevel.HIGH)
        scored = score(result)
        assert scored.priority_score == pytest.approx(40.0)

    def test_priority_formula(self):
        # savings * confidence * risk_weight
        result = self._make_result(200.0, 0.85, RiskLevel.MEDIUM)
        scored = score(result)
        expected = 200.0 * 0.85 * 0.7
        assert scored.priority_score == pytest.approx(expected, rel=1e-4)

    def test_ranking_is_descending(self):
        r_low = self._make_result(50.0, 1.0, RiskLevel.LOW, "R1")
        r_high = self._make_result(500.0, 1.0, RiskLevel.LOW, "R2")
        r_medium = self._make_result(200.0, 1.0, RiskLevel.LOW, "R3")
        ranked = score_and_rank([r_low, r_high, r_medium])
        assert ranked[0].result.rule_id == "R2"
        assert ranked[1].result.rule_id == "R3"
        assert ranked[2].result.rule_id == "R1"

    def test_empty_list_returns_empty(self):
        result = score_and_rank([])
        assert result == []


# ---------------------------------------------------------------------------
# 12. Engine integration
# ---------------------------------------------------------------------------

class TestEngine:
    def _disk_resource(self, resource_id="disk-1", size_gb=200, tags=None):
        return {
            "resource_id": resource_id,
            "type": "microsoft.compute/disks",
            "name": "my-disk",
            "resource_group": "rg",
            "properties": {"diskState": "Unattached", "diskSizeGB": size_gb},
            "tags": tags or {},
        }

    def _vm_resource(self, resource_id="vm-1", vm_size="Standard_D4s_v3", tags=None):
        return {
            "resource_id": resource_id,
            "type": "microsoft.compute/virtualmachines",
            "name": "my-vm",
            "resource_group": "rg",
            "properties": {"hardwareProfile": {"vmSize": vm_size}},
            "tags": tags or {},
        }

    def test_engine_returns_engine_result(self):
        resources = [self._disk_resource()]
        context = {"tenant_id": "t1", "subscription_id": "s1"}
        result = run_engine(resources, context)
        assert result.total_resources_evaluated == 1
        assert result.total_rules_fired > 0
        assert result.total_estimated_monthly_savings >= 0

    def test_engine_correct_resource_count(self):
        resources = [self._disk_resource("d1"), self._disk_resource("d2"), self._vm_resource("v1")]
        context = {"tenant_id": "t1", "subscription_id": "s1"}
        result = run_engine(resources, context)
        assert result.total_resources_evaluated == 3

    def test_engine_results_sorted_by_priority(self):
        resources = [self._disk_resource(size_gb=10), self._disk_resource(size_gb=1000)]
        context = {"tenant_id": "t1", "subscription_id": "s1"}
        result = run_engine(resources, context)
        if len(result.scored_results) >= 2:
            # First result should have higher or equal priority score
            assert result.scored_results[0].priority_score >= result.scored_results[1].priority_score

    def test_engine_isolates_rule_failures(self):
        """A resource that causes an unexpected exception should not crash the engine."""
        # Pass a resource with completely unexpected structure
        resources = [{"type": None, "properties": None, "tags": None}]
        context = {"tenant_id": "t1", "subscription_id": "s1"}
        # Should not raise
        result = run_engine(resources, context)
        assert result is not None

    def test_engine_with_multiple_rule_types(self):
        # Disk fires WASTE-001, VM fires RATE-001, missing tag fires GOV-001
        resources = [
            self._disk_resource("d1", 512, {}),  # unattached disk + missing tag
            self._vm_resource("v1", "Standard_D4s_v3", {}),  # RI gap + missing tag
        ]
        context = {"tenant_id": "t1", "subscription_id": "s1"}
        result = run_engine(resources, context)
        rule_ids = {s.result.rule_id for s in result.scored_results}
        assert "WASTE-001" in rule_ids
        assert "RATE-001" in rule_ids
        assert "GOV-001" in rule_ids

    def test_engine_total_savings_is_sum_of_individual(self):
        resources = [self._disk_resource("d1", 200), self._disk_resource("d2", 400)]
        context = {"tenant_id": "t1", "subscription_id": "s1"}
        result = run_engine(resources, context)
        manual_sum = sum(s.result.estimated_monthly_savings for s in result.scored_results)
        assert result.total_estimated_monthly_savings == pytest.approx(manual_sum, rel=1e-4)
