"""Focused unit tests for the priority scorer."""
from __future__ import annotations

import pytest

from src.engine.rules.base import (
    EffortLevel,
    RuleCategory,
    RuleResult,
    RiskLevel,
)
from src.engine.scoring.scorer import ScoredResult, score, score_and_rank


def _make_result(
    savings: float,
    confidence: float,
    risk_level: RiskLevel,
    rule_id: str = "TEST-001",
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        category=RuleCategory.WASTE,
        resource_id="resource-1",
        resource_type="microsoft.compute/disks",
        resource_name="my-disk",
        resource_group="rg-test",
        subscription_id="sub-001",
        tenant_id="tenant-001",
        estimated_monthly_savings=savings,
        confidence_score=confidence,
        risk_level=risk_level,
        effort_level=EffortLevel.LOW,
        short_description="test description",
        detail="test detail text",
    )


class TestRiskWeights:
    def test_low_risk_weight_is_1_0(self):
        r = _make_result(100.0, 1.0, RiskLevel.LOW)
        s = score(r)
        assert s.priority_score == pytest.approx(100.0)

    def test_medium_risk_weight_is_0_7(self):
        r = _make_result(100.0, 1.0, RiskLevel.MEDIUM)
        s = score(r)
        assert s.priority_score == pytest.approx(70.0)

    def test_high_risk_weight_is_0_4(self):
        r = _make_result(100.0, 1.0, RiskLevel.HIGH)
        s = score(r)
        assert s.priority_score == pytest.approx(40.0)


class TestPriorityFormula:
    def test_priority_equals_savings_times_confidence_times_weight(self):
        # savings=500, confidence=0.9, risk=LOW(1.0) -> 500 * 0.9 * 1.0 = 450
        r = _make_result(500.0, 0.9, RiskLevel.LOW)
        s = score(r)
        assert s.priority_score == pytest.approx(450.0)

    def test_priority_with_medium_risk(self):
        # savings=200, confidence=0.85, risk=MEDIUM(0.7) -> 200 * 0.85 * 0.7 = 119.0
        r = _make_result(200.0, 0.85, RiskLevel.MEDIUM)
        s = score(r)
        assert s.priority_score == pytest.approx(119.0)

    def test_priority_with_high_risk(self):
        # savings=1000, confidence=0.7, risk=HIGH(0.4) -> 1000 * 0.7 * 0.4 = 280.0
        r = _make_result(1000.0, 0.7, RiskLevel.HIGH)
        s = score(r)
        assert s.priority_score == pytest.approx(280.0)

    def test_zero_savings_gives_zero_priority(self):
        r = _make_result(0.0, 1.0, RiskLevel.LOW)
        s = score(r)
        assert s.priority_score == pytest.approx(0.0)

    def test_scored_result_contains_original_result(self):
        r = _make_result(100.0, 0.95, RiskLevel.LOW)
        s = score(r)
        assert isinstance(s, ScoredResult)
        assert s.result is r


class TestRanking:
    def test_ranking_is_descending_by_priority_score(self):
        r1 = _make_result(50.0, 1.0, RiskLevel.LOW, "R1")
        r2 = _make_result(500.0, 1.0, RiskLevel.LOW, "R2")
        r3 = _make_result(200.0, 1.0, RiskLevel.LOW, "R3")
        ranked = score_and_rank([r1, r2, r3])
        scores = [s.priority_score for s in ranked]
        assert scores == sorted(scores, reverse=True)
        assert ranked[0].result.rule_id == "R2"
        assert ranked[1].result.rule_id == "R3"
        assert ranked[2].result.rule_id == "R1"

    def test_high_savings_low_confidence_may_rank_below_medium_savings_high_confidence(self):
        # 1000 * 0.3 * 1.0 = 300 vs 200 * 1.0 * 1.0 = 200 — high savings still wins
        high_savings = _make_result(1000.0, 0.3, RiskLevel.LOW, "HIGH-SAVINGS")
        med_savings = _make_result(200.0, 1.0, RiskLevel.LOW, "MED-SAVINGS")
        ranked = score_and_rank([med_savings, high_savings])
        assert ranked[0].result.rule_id == "HIGH-SAVINGS"

    def test_same_savings_risk_differentiates(self):
        r_low_risk = _make_result(100.0, 1.0, RiskLevel.LOW, "LOW")
        r_high_risk = _make_result(100.0, 1.0, RiskLevel.HIGH, "HIGH")
        ranked = score_and_rank([r_high_risk, r_low_risk])
        assert ranked[0].result.rule_id == "LOW"

    def test_empty_list_returns_empty(self):
        result = score_and_rank([])
        assert result == []

    def test_single_item_list(self):
        r = _make_result(100.0, 0.95, RiskLevel.LOW)
        ranked = score_and_rank([r])
        assert len(ranked) == 1
        assert ranked[0].result is r

    def test_returns_list_of_scored_results(self):
        r1 = _make_result(100.0, 1.0, RiskLevel.LOW)
        r2 = _make_result(200.0, 1.0, RiskLevel.LOW)
        ranked = score_and_rank([r1, r2])
        assert all(isinstance(s, ScoredResult) for s in ranked)
