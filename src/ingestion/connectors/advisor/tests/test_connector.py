"""Unit tests for Advisor connector — all Azure calls are mocked."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ingestion.connectors.base import ConnectorContext
from ingestion.connectors.advisor.connector import AdvisorConnector
from ingestion.connectors.advisor.mapper import map_advisor_recommendation


def make_ctx(**kwargs) -> ConnectorContext:
    return ConnectorContext(
        tenant_id=kwargs.get("tenant_id", "tenant-abc"),
        subscription_id=kwargs.get("subscription_id", "sub-123"),
    )


MOCK_ADVISOR_ITEMS = [
    {
        "id": "/subscriptions/sub-123/providers/Microsoft.Advisor/recommendations/rec-1",
        "name": "rec-1",
        "properties": {
            "category": "Cost",
            "impact": "High",
            "impactedField": "Microsoft.Compute/virtualMachines",
            "impactedValue": "vm-idle-01",
            "shortDescription": {"solution": "Shut down underutilized VM", "problem": "VM is underutilized"},
            "recommendationTypeId": "e10b1381-5f0a-47ff-8c7b-37bd13d7c974",
            "resourceMetadata": {"resourceId": "/subscriptions/sub-123/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-idle-01"},
            "extendedProperties": {"savingsAmount": "240.00"},
        },
    },
    {
        "id": "/subscriptions/sub-123/providers/Microsoft.Advisor/recommendations/rec-2",
        "name": "rec-2",
        "properties": {
            "category": "Cost",
            "impact": "Medium",
            "impactedField": "Microsoft.Compute/disks",
            "impactedValue": "orphan-disk-01",
            "shortDescription": {"solution": "Delete unattached disk", "problem": "Disk not attached"},
            "recommendationTypeId": "9b2b5a80-e967-4a67-8f91-bd3bae1e8a54",
            "resourceMetadata": {"resourceId": "/subscriptions/sub-123/resourceGroups/rg/providers/Microsoft.Compute/disks/orphan-disk-01"},
            "extendedProperties": {"annualSavingsAmount": "120.00"},
        },
    },
]

MOCK_ADVISOR_RESPONSE = {"value": MOCK_ADVISOR_ITEMS}


class TestAdvisorConnector:
    @pytest.fixture
    def mock_credential(self):
        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="fake-token", expires_on=9999999999)
        return cred

    @pytest.mark.asyncio
    async def test_collect_returns_normalised_records(self, mock_credential):
        connector = AdvisorConnector(credential=mock_credential)
        connector._http.paginate = AsyncMock(return_value=MOCK_ADVISOR_ITEMS)

        ctx = make_ctx()
        records = await connector.collect(ctx)

        assert len(records) == 2
        assert records[0]["name"] == "rec-1"
        assert records[0]["impact"] == "High"

    @pytest.mark.asyncio
    async def test_collect_empty_recommendations(self, mock_credential):
        connector = AdvisorConnector(credential=mock_credential)
        connector._http.paginate = AsyncMock(return_value=[])

        ctx = make_ctx()
        records = await connector.collect(ctx)
        assert records == []

    def test_extract_savings_direct_amount(self, mock_credential):
        connector = AdvisorConnector(credential=mock_credential)
        props = {"extendedProperties": {"savingsAmount": "240.00"}, "impact": "High"}
        assert connector._extract_savings(props) == 240.0

    def test_extract_savings_annual_divided_by_12(self, mock_credential):
        connector = AdvisorConnector(credential=mock_credential)
        props = {"extendedProperties": {"annualSavingsAmount": "120.00"}, "impact": "Medium"}
        assert connector._extract_savings(props) == pytest.approx(10.0)

    def test_extract_savings_fallback_to_impact(self, mock_credential):
        connector = AdvisorConnector(credential=mock_credential)
        props = {"extendedProperties": {}, "impact": "High"}
        assert connector._extract_savings(props) == 500.0


class TestAdvisorMapper:
    def test_map_high_impact_recommendation(self):
        record = {
            "advisor_id": "/sub/rec-1",
            "name": "rec-1",
            "impact": "High",
            "short_description": "Shut down underutilized VM",
            "problem": "VM is underutilized",
            "recommendation_type_id": "type-abc",
            "estimated_monthly_savings": 240.0,
            "impacted_value": "vm-idle-01",
        }
        result = map_advisor_recommendation(record, tenant_id="t1")
        assert result["confidence_score"] == 0.9
        assert result["risk_level"] == "low"
        assert result["estimated_monthly_savings"] == 240.0
        assert result["status"] == "open"
        assert "t1" == result["tenant_id"]

    def test_map_medium_impact_recommendation(self):
        record = {
            "advisor_id": "/sub/rec-2", "name": "rec-2",
            "impact": "Medium", "short_description": "Delete disk",
            "problem": "Orphaned", "recommendation_type_id": "type-xyz",
            "estimated_monthly_savings": 10.0, "impacted_value": "disk-1",
        }
        result = map_advisor_recommendation(record, tenant_id="t1")
        assert result["confidence_score"] == 0.7
