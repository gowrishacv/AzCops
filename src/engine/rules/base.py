from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleCategory(str, Enum):
    WASTE = "waste"
    RIGHTSIZING = "rightsizing"
    RATE_OPTIMIZATION = "rate_optimization"
    GOVERNANCE = "governance"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EffortLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RuleResult:
    rule_id: str
    category: RuleCategory
    resource_id: str
    resource_type: str
    resource_name: str
    resource_group: str
    subscription_id: str
    tenant_id: str
    estimated_monthly_savings: float
    confidence_score: float  # 0.0-1.0
    risk_level: RiskLevel
    effort_level: EffortLevel
    short_description: str
    detail: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseRule(ABC):
    rule_id: str
    category: RuleCategory
    description: str

    @abstractmethod
    def evaluate(self, resource: dict[str, Any], context: dict[str, Any]) -> RuleResult | None:
        """Return RuleResult if the rule fires, None if not applicable."""
        ...

    def _make_result(self, *, resource: dict, context: dict, **kwargs) -> RuleResult:
        return RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            resource_id=resource.get("resource_id", ""),
            resource_type=resource.get("type", ""),
            resource_name=resource.get("name", resource.get("resource_id", "")),
            resource_group=resource.get("resource_group", ""),
            subscription_id=context.get("subscription_id", ""),
            tenant_id=context.get("tenant_id", ""),
            **kwargs,
        )
