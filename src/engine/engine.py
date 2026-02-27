from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.engine.rules.implementations import loader  # noqa: F401 — registers all rules
from src.engine.rules.registry import get_all
from src.engine.scoring.scorer import ScoredResult, score_and_rank


@dataclass
class EngineResult:
    total_resources_evaluated: int
    total_rules_fired: int
    scored_results: list[ScoredResult]
    total_estimated_monthly_savings: float


def run_engine(
    resources: list[dict[str, Any]],
    context: dict[str, Any],
) -> EngineResult:
    """
    Evaluate all registered rules against every resource.

    context keys:
        tenant_id (str): The tenant identifier.
        subscription_id (str): The Azure subscription ID.
        vm_metrics (dict[resource_id, metrics]): CPU/memory metrics per VM.
        compute_cost_30d (float): Total compute spend in the last 30 days.
    """
    rules = get_all()
    raw_results = []
    for resource in resources:
        for rule in rules:
            try:
                result = rule.evaluate(resource, context)
                if result is not None:
                    raw_results.append(result)
            except Exception:  # noqa: BLE001
                pass  # isolate rule failures

    scored = score_and_rank(raw_results)
    total_savings = sum(s.result.estimated_monthly_savings for s in scored)
    return EngineResult(
        total_resources_evaluated=len(resources),
        total_rules_fired=len(raw_results),
        scored_results=scored,
        total_estimated_monthly_savings=round(total_savings, 2),
    )
