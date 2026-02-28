"""Base classes for the AzCops rule engine."""

from __future__ import annotations

import abc
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class RuleResult:
    """Immutable result produced by a single rule evaluation against a resource."""

    resource_db_id: str | None
    rule_id: str
    category: str
    title: str
    description: str
    estimated_monthly_savings: float
    confidence_score: float  # 0.0 – 1.0
    risk_level: str  # low | medium | high
    effort_level: str  # low | medium | high

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}"
            )
        if self.risk_level not in ("low", "medium", "high"):
            raise ValueError(
                f"risk_level must be low, medium, or high, got {self.risk_level}"
            )
        if self.effort_level not in ("low", "medium", "high"):
            raise ValueError(
                f"effort_level must be low, medium, or high, got {self.effort_level}"
            )


class Rule(abc.ABC):
    """Abstract base class that every rule must implement."""

    rule_id: str
    category: str

    @abc.abstractmethod
    async def evaluate(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> list[RuleResult]:
        """Run the rule against data for *tenant_id* and return findings.

        Implementations must never raise on empty datasets – they should
        return an empty list instead.
        """
        ...
