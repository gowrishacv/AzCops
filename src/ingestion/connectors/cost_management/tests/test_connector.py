"""Unit tests for Cost Management connector — all Azure calls are mocked."""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from ingestion.connectors.base import ConnectorContext
from ingestion.connectors.cost_management.connector import CostManagementConnector, _parse_cost_response, _parse_date
from ingestion.connectors.cost_management.mapper import map_cost_record, map_cost_records


def make_ctx(**kwargs) -> ConnectorContext:
    return ConnectorContext(
        tenant_id=kwargs.get("tenant_id", "tenant-abc"),
        subscription_id=kwargs.get("subscription_id", "sub-123"),
    )


MOCK_COST_COLUMNS = [
    {"name": "UsageDate"}, {"name": "ResourceGroupName"},
    {"name": "ServiceName"}, {"name": "MeterCategory"},
    {"name": "Cost"}, {"name": "Currency"},
]

MOCK_COST_ROWS = [
    [20260201, "rg-prod", "Virtual Machines", "Compute", 42.50, "USD"],
    [20260201, "rg-dev", "Storage", "Storage", 5.75, "USD"],
]

MOCK_COST_RESPONSE = {
    "properties": {
        "columns": MOCK_COST_COLUMNS,
        "rows": MOCK_COST_ROWS,
    }
}


class TestCostManagementConnector:
    @pytest.fixture
    def mock_credential(self):
        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="fake-token", expires_on=9999999999)
        return cred

    @pytest.mark.asyncio
    async def test_collect_returns_records(self, mock_credential):
        connector = CostManagementConnector(credential=mock_credential)
        connector._http.request = AsyncMock(return_value=MOCK_COST_RESPONSE)

        ctx = make_ctx()
        records = await connector.collect(ctx)

        # Two requests (actual + amortized) but one set of records
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_collect_merges_amortized_cost(self, mock_credential):
        """Amortized cost should be merged from the second API call."""
        amortized_response = {
            "properties": {
                "columns": MOCK_COST_COLUMNS,
                "rows": [
                    [20260201, "rg-prod", "Virtual Machines", "Compute", 38.00, "USD"],
                ],
            }
        }
        connector = CostManagementConnector(credential=mock_credential)
        connector._http.request = AsyncMock(side_effect=[MOCK_COST_RESPONSE, amortized_response])

        ctx = make_ctx()
        records = await connector.collect_range(ctx, date(2026, 2, 1), date(2026, 2, 1))

        vm_record = next(r for r in records if r["resource_group"] == "rg-prod")
        assert vm_record["cost"] == 42.50
        assert vm_record["amortized_cost"] == 38.00

    @pytest.mark.asyncio
    async def test_collect_empty_response(self, mock_credential):
        connector = CostManagementConnector(credential=mock_credential)
        connector._http.request = AsyncMock(return_value={"properties": {"columns": [], "rows": []}})

        ctx = make_ctx()
        records = await connector.collect(ctx)
        assert records == []


class TestCostParsing:
    def test_parse_date_integer_format(self):
        assert _parse_date(20260215) == date(2026, 2, 15)

    def test_parse_date_string_format(self):
        assert _parse_date("2026-02-15") == date(2026, 2, 15)

    def test_parse_date_string_with_extra(self):
        assert _parse_date("2026-02-15T00:00:00Z") == date(2026, 2, 15)

    def test_parse_cost_response_columns(self):
        records = _parse_cost_response(MOCK_COST_RESPONSE)
        assert len(records) == 2
        assert records[0]["resource_group"] == "rg-prod"
        assert records[0]["service_name"] == "Virtual Machines"
        assert records[0]["cost"] == 42.50
        assert records[0]["currency"] == "USD"


class TestCostMapper:
    def test_map_cost_record(self):
        row = {
            "date": date(2026, 2, 1),
            "resource_group": "rg-prod",
            "service_name": "Virtual Machines",
            "meter_category": "Compute",
            "cost": 42.50,
            "amortized_cost": 38.00,
            "currency": "USD",
        }
        result = map_cost_record(row, tenant_id="t1", subscription_db_id="db-sub-1")
        assert result["cost"] == 42.50
        assert result["amortized_cost"] == 38.00
        assert result["tenant_id"] == "t1"
        assert result["subscription_db_id"] == "db-sub-1"
        assert result["date"] == date(2026, 2, 1)

    def test_map_cost_records_batch(self):
        rows = [
            {"date": date(2026, 2, 1), "resource_group": f"rg-{i}", "service_name": "Storage",
             "meter_category": "Blob", "cost": float(i), "amortized_cost": float(i), "currency": "USD"}
            for i in range(3)
        ]
        results = map_cost_records(rows, tenant_id="t1", subscription_db_id="db1")
        assert len(results) == 3
