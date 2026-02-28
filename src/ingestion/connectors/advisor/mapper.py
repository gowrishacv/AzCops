"""
Maps Advisor recommendation records to Recommendation model dicts for DB upsert.
"""
from __future__ import annotations

from typing import Any


IMPACT_TO_CONFIDENCE = {"High": 0.9, "Medium": 0.7, "Low": 0.5}
IMPACT_TO_RISK = {"High": "low", "Medium": "low", "Low": "low"}


def map_advisor_recommendation(
    record: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Map an Advisor record to a Recommendation model dict."""
    impact = record.get("impact", "Low")
    return {
        "tenant_id": tenant_id,
        "rule_id": f"advisor.{record.get('recommendation_type_id', 'unknown')}",
        "category": "rate_optimization",
        "title": record.get("short_description") or "Azure Advisor Cost Recommendation",
        "description": record.get("problem") or record.get("short_description") or "",
        "estimated_monthly_savings": record.get("estimated_monthly_savings", 0.0),
        "confidence_score": IMPACT_TO_CONFIDENCE.get(impact, 0.5),
        "risk_level": "low",
        "effort_level": "low",
        "status": "open",
        "owner": None,
        "explanation": (
            f"Azure Advisor identified this resource ({record.get('impacted_value', '')}) "
            f"as having potential cost savings of ~${record.get('estimated_monthly_savings', 0):.2f}/month. "
            f"Impact: {impact}."
        ),
    }
