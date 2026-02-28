"""Unit tests for ResourceGraph connector — all Azure calls are mocked."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingestion.connectors.base import ConnectorContext
from ingestion.connectors.resource_graph.connector import ResourceGraphConnector
from ingestion.connectors.resource_graph.mapper import map_resource, map_resources


# --- Fixtures ---

def make_ctx(**kwargs) -> ConnectorContext:
    return ConnectorContext(
        tenant_id=kwargs.get("tenant_id", "tenant-abc"),
        subscription_id=kwargs.get("subscription_id", "sub-123"),
        correlation_id="test-corr-id",
    )


ARG_COLUMNS = [
    {"name": "id"}, {"name": "name"}, {"name": "type"},
    {"name": "resourceGroup"}, {"name": "subscriptionId"},
    {"name": "location"}, {"name": "tags"}, {"name": "properties"},
]

ARG_ROWS = [
    [
        "/subscriptions/sub-123/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm1",
        "vm1", "microsoft.compute/virtualmachines",
        "rg-prod", "sub-123", "eastus",
        {"env": "prod", "cost-center": "engineering"},
        {"hardwareProfile": {"vmSize": "Standard_D4s_v3"}},
    ],
    [
        "/subscriptions/sub-123/resourceGroups/rg-prod/providers/Microsoft.Compute/disks/disk1",
        "disk1", "microsoft.compute/disks",
        "rg-prod", "sub-123", "eastus",
        {}, {},
    ],
]

MOCK_ARG_RESPONSE = {
    "data": {"columns": ARG_COLUMNS, "rows": ARG_ROWS},
}


# --- Connector Tests ---

class TestResourceGraphConnector:
    @pytest.fixture
    def mock_credential(self):
        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="fake-token", expires_on=9999999999)
        return cred

    @pytest.mark.asyncio
    async def test_collect_returns_resource_list(self, mock_credential):
        connector = ResourceGraphConnector(credential=mock_credential)
        connector._http.request = AsyncMock(return_value=MOCK_ARG_RESPONSE)

        ctx = make_ctx()
        results = await connector.collect(ctx)

        assert len(results) == 2
        assert results[0]["name"] == "vm1"
        assert results[1]["name"] == "disk1"

    @pytest.mark.asyncio
    async def test_collect_handles_pagination(self, mock_credential):
        """Connector should follow $skipToken until exhausted."""
        page1 = {
            "data": {
                "columns": ARG_COLUMNS,
                "rows": [ARG_ROWS[0]],
            },
            "$skipToken": "token-abc",
        }
        page2 = {
            "data": {
                "columns": ARG_COLUMNS,
                "rows": [ARG_ROWS[1]],
            },
        }

        connector = ResourceGraphConnector(credential=mock_credential)
        connector._http.request = AsyncMock(side_effect=[page1, page2])

        ctx = make_ctx()
        results = await connector.collect(ctx)

        assert len(results) == 2
        assert connector._http.request.call_count == 2

    @pytest.mark.asyncio
    async def test_collect_empty_result(self, mock_credential):
        connector = ResourceGraphConnector(credential=mock_credential)
        connector._http.request = AsyncMock(return_value={"data": {"columns": ARG_COLUMNS, "rows": []}})

        ctx = make_ctx()
        results = await connector.collect(ctx)

        assert results == []

    @pytest.mark.asyncio
    async def test_collect_waste_candidates_runs_parallel_queries(self, mock_credential):
        """collect_waste_candidates should make 5 parallel ARG calls."""
        connector = ResourceGraphConnector(credential=mock_credential)
        connector._http.request = AsyncMock(return_value={"data": {"columns": ARG_COLUMNS, "rows": []}})

        ctx = make_ctx()
        result = await connector.collect_waste_candidates(ctx)

        assert set(result.keys()) == {
            "unattached_disks",
            "orphaned_public_ips",
            "orphaned_nics",
            "stale_snapshots",
            "missing_cost_center_tag",
        }
        assert connector._http.request.call_count == 5


# --- Mapper Tests ---

class TestResourceMapper:
    def test_map_resource_basic(self):
        row = {
            "id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1",
            "name": "vm1",
            "type": "Microsoft.Compute/virtualMachines",
            "resourceGroup": "RG-PROD",
            "subscriptionId": "sub-123",
            "location": "EastUS",
            "tags": {"env": "prod"},
            "properties": {"vmSize": "D4s"},
        }
        result = map_resource(row, tenant_id="t1", subscription_db_id="db-sub-1")

        assert result["name"] == "vm1"
        assert result["type"] == "microsoft.compute/virtualmachines"
        assert result["resource_group"] == "rg-prod"
        assert result["location"] == "eastus"
        assert result["tags"] == {"env": "prod"}
        assert result["tenant_id"] == "t1"

    def test_map_resource_handles_string_tags(self):
        """Tags may arrive as JSON strings from ARG."""
        row = {
            "id": "/sub/rg/r1", "name": "r1", "type": "t",
            "resourceGroup": "rg", "subscriptionId": "s1",
            "location": "westus", "tags": '{"key":"value"}', "properties": {},
        }
        result = map_resource(row, tenant_id="t1", subscription_db_id="db1")
        assert result["tags"] == {"key": "value"}

    def test_map_resource_handles_null_tags(self):
        row = {
            "id": "/sub/rg/r1", "name": "r1", "type": "t",
            "resourceGroup": "rg", "subscriptionId": "s1",
            "location": "westus", "tags": None, "properties": None,
        }
        result = map_resource(row, tenant_id="t1", subscription_db_id="db1")
        assert result["tags"] == {}

    def test_map_resources_batch(self):
        rows = [
            {"id": f"/r{i}", "name": f"r{i}", "type": "t", "resourceGroup": "rg",
             "subscriptionId": "s1", "location": "eastus", "tags": {}, "properties": {}}
            for i in range(5)
        ]
        results = map_resources(rows, tenant_id="t1", subscription_db_id="db1")
        assert len(results) == 5
