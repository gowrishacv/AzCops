from __future__ import annotations

from src.engine.rules.registry import register
from src.engine.rules.implementations.unattached_disk import unattached_disk_rule
from src.engine.rules.implementations.idle_public_ip import idle_public_ip_rule
from src.engine.rules.implementations.orphaned_nic import orphaned_nic_rule
from src.engine.rules.implementations.stale_snapshot import stale_snapshot_rule
from src.engine.rules.implementations.underutilised_vm import underutilised_vm_rule
from src.engine.rules.implementations.underutilised_app_service import underutilised_app_service_rule
from src.engine.rules.implementations.underutilised_sql import underutilised_sql_rule
from src.engine.rules.implementations.reserved_instance_gap import reserved_instance_gap_rule
from src.engine.rules.implementations.savings_plan_opportunity import savings_plan_opportunity_rule
from src.engine.rules.implementations.missing_cost_center_tag import missing_cost_center_tag_rule

# Register all rules
register(unattached_disk_rule)
register(idle_public_ip_rule)
register(orphaned_nic_rule)
register(stale_snapshot_rule)
register(underutilised_vm_rule)
register(underutilised_app_service_rule)
register(underutilised_sql_rule)
register(reserved_instance_gap_rule)
register(savings_plan_opportunity_rule)
register(missing_cost_center_tag_rule)

__all__ = [
    "unattached_disk_rule",
    "idle_public_ip_rule",
    "orphaned_nic_rule",
    "stale_snapshot_rule",
    "underutilised_vm_rule",
    "underutilised_app_service_rule",
    "underutilised_sql_rule",
    "reserved_instance_gap_rule",
    "savings_plan_opportunity_rule",
    "missing_cost_center_tag_rule",
]
