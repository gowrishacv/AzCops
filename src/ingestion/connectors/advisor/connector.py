"""
Azure Advisor connector — fetches built-in Cost recommendations
from the Azure Advisor Recommendations API.
"""
from __future__ import annotations

from typing import Any

import structlog

from ingestion.connectors.base import BaseConnector, ConnectorContext

logger = structlog.get_logger(__name__)

ADVISOR_API_VERSION = "2023-01-01"


class AdvisorConnector(BaseConnector):
    """
    Fetches Azure Advisor cost recommendations for a subscription.
    Filters to category=Cost only. Handles pagination via nextLink.
    """

    async def collect(self, ctx: ConnectorContext) -> list[dict[str, Any]]:
        """Collect all Advisor Cost recommendations for a subscription."""
        ctx.operation_name = "advisor.cost_recommendations"
        url = (
            f"https://management.azure.com/subscriptions/{ctx.subscription_id}"
            f"/providers/Microsoft.Advisor/recommendations"
        )
        params = {
            "api-version": ADVISOR_API_VERSION,
            "$filter": "Category eq 'Cost'",
        }

        items = await self._http.paginate(
            "GET", url, ctx, params=params
        )

        records = [self._normalise(item, ctx) for item in items]
        logger.info(
            "advisor_collected",
            count=len(records),
            subscription_id=ctx.subscription_id,
            tenant_id=ctx.tenant_id,
        )
        return records

    def _normalise(self, item: dict[str, Any], ctx: ConnectorContext) -> dict[str, Any]:
        """Normalise an Advisor recommendation into a flat dict."""
        props = item.get("properties", {})
        impact = props.get("impact", "Low")  # Low | Medium | High
        extended = props.get("extendedProperties", {})

        # Savings may be in different fields depending on recommendation type
        savings_amount = self._extract_savings(props)

        return {
            "advisor_id": item.get("id", ""),
            "name": item.get("name", ""),
            "category": props.get("category", "Cost"),
            "impact": impact,
            "impacted_field": props.get("impactedField", ""),
            "impacted_value": props.get("impactedValue", ""),
            "short_description": props.get("shortDescription", {}).get("solution", ""),
            "problem": props.get("shortDescription", {}).get("problem", ""),
            "recommendation_type_id": props.get("recommendationTypeId", ""),
            "estimated_monthly_savings": savings_amount,
            "resource_id": props.get("resourceMetadata", {}).get("resourceId", ""),
            "subscription_id": ctx.subscription_id,
            "tenant_id": ctx.tenant_id,
            "extended_properties": extended,
        }

    @staticmethod
    def _extract_savings(props: dict[str, Any]) -> float:
        """
        Extract estimated monthly savings from Advisor properties.
        Azure stores this in multiple possible locations depending on rule type.
        """
        # Try direct savings field
        extended = props.get("extendedProperties", {})
        for key in ("savingsAmount", "annualSavingsAmount", "monthlySavingsAmount"):
            val = extended.get(key)
            if val is not None:
                try:
                    amount = float(val)
                    # Convert annual to monthly if needed
                    if "annual" in key.lower():
                        amount = amount / 12
                    return round(amount, 2)
                except (TypeError, ValueError):
                    pass

        # Fallback to impact-based estimate
        impact = props.get("impact", "Low")
        return {"High": 500.0, "Medium": 100.0, "Low": 20.0}.get(impact, 20.0)
