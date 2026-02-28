"""Rule registry – imports every rule class and exposes them as ALL_RULES."""

from __future__ import annotations

from app.engine.rules.governance import BudgetThresholdRule, MissingCostCenterTagRule
from app.engine.rules.rate_optimization import (
    RICoverageGapRule,
    SavingsPlanOpportunitiesRule,
)
from app.engine.rules.rightsizing import (
    OversizedAppServiceRule,
    SQLDTUUnderutilizedRule,
    UnderutilizedVMsRule,
)
from app.engine.rules.waste import (
    OrphanedNICsRule,
    OrphanedPublicIPsRule,
    StaleSnapshotsRule,
    UnattachedDisksRule,
)

ALL_RULES: list[type] = [
    # Waste detection
    UnattachedDisksRule,
    OrphanedPublicIPsRule,
    OrphanedNICsRule,
    StaleSnapshotsRule,
    # Right-sizing
    UnderutilizedVMsRule,
    OversizedAppServiceRule,
    SQLDTUUnderutilizedRule,
    # Rate optimisation
    RICoverageGapRule,
    SavingsPlanOpportunitiesRule,
    # Governance
    MissingCostCenterTagRule,
    BudgetThresholdRule,
]

__all__ = [
    "ALL_RULES",
    "UnattachedDisksRule",
    "OrphanedPublicIPsRule",
    "OrphanedNICsRule",
    "StaleSnapshotsRule",
    "UnderutilizedVMsRule",
    "OversizedAppServiceRule",
    "SQLDTUUnderutilizedRule",
    "RICoverageGapRule",
    "SavingsPlanOpportunitiesRule",
    "MissingCostCenterTagRule",
    "BudgetThresholdRule",
]
