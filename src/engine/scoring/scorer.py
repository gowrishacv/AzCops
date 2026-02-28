from __future__ import annotations

from dataclasses import dataclass

from src.engine.rules.base import RuleResult, RiskLevel

_RISK_WEIGHT = {
    RiskLevel.LOW: 1.0,
    RiskLevel.MEDIUM: 0.7,
    RiskLevel.HIGH: 0.4,
}


@dataclass
class ScoredResult:
    result: RuleResult
    priority_score: float  # savings * confidence * risk_weight


def score(result: RuleResult) -> ScoredResult:
    risk_weight = _RISK_WEIGHT[result.risk_level]
    priority = result.estimated_monthly_savings * result.confidence_score * risk_weight
    return ScoredResult(result=result, priority_score=round(priority, 4))


def score_and_rank(results: list[RuleResult]) -> list[ScoredResult]:
    scored = [score(r) for r in results]
    return sorted(scored, key=lambda s: s.priority_score, reverse=True)
