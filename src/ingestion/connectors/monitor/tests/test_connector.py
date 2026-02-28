"""Unit tests for Monitor Metrics connector — all Azure calls are mocked."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ingestion.connectors.base import ConnectorContext
from ingestion.connectors.monitor.connector import MonitorMetricsConnector
from ingestion.connectors.monitor.mapper import is_underutilised_vm


def make_ctx(**kwargs) -> ConnectorContext:
    return ConnectorContext(
        tenant_id=kwargs.get("tenant_id", "tenant-abc"),
        subscription_id=kwargs.get("subscription_id", "sub-123"),
        extra=kwargs.get("extra", {}),
    )


def _make_metric_response(metric_name: str, avg_values: list[float]) -> dict:
    """Build a mock Azure Monitor metrics response."""
    data_points = [{"average": v, "maximum": v * 1.1, "minimum": v * 0.9} for v in avg_values]
    return {
        "value": [
            {
                "name": {"value": metric_name},
                "unit": "Percent" if "CPU" in metric_name else "Bytes",
                "timeseries": [{"data": data_points}],
            }
        ]
    }


class TestMonitorMetricsConnector:
    @pytest.fixture
    def mock_credential(self):
        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="fake-token", expires_on=9999999999)
        return cred

    @pytest.mark.asyncio
    async def test_collect_no_vms_returns_empty(self, mock_credential):
        connector = MonitorMetricsConnector(credential=mock_credential)
        ctx = make_ctx()  # no vm_resource_ids in extra
        records = await connector.collect(ctx)
        assert records == []

    @pytest.mark.asyncio
    async def test_collect_vm_metrics(self, mock_credential):
        cpu_response = _make_metric_response("Percentage CPU", [5.0, 8.0, 6.0, 4.0])
        mem_response = _make_metric_response("Available Memory Bytes", [4e9, 3.5e9, 5e9])

        # Interleave: connector requests CPU+Mem in one call (both in same response)
        combined_response = {
            "value": cpu_response["value"] + mem_response["value"]
        }

        connector = MonitorMetricsConnector(credential=mock_credential)
        connector._http.request = AsyncMock(return_value=combined_response)

        ctx = make_ctx(extra={"vm_resource_ids": ["/subscriptions/sub/rg/vm1"]})
        records = await connector.collect(ctx)

        assert len(records) == 2  # CPU + Memory metrics
        metric_names = {r["metric_name"] for r in records}
        assert "Percentage CPU" in metric_names
        assert "Available Memory Bytes" in metric_names

    @pytest.mark.asyncio
    async def test_collect_handles_individual_vm_errors(self, mock_credential):
        """Errors on individual VMs should not fail the entire batch."""
        connector = MonitorMetricsConnector(credential=mock_credential)
        connector._http.request = AsyncMock(side_effect=Exception("timeout"))

        ctx = make_ctx(extra={
            "vm_resource_ids": ["/sub/rg/vm1", "/sub/rg/vm2"]
        })
        records = await connector.collect(ctx)
        # Should return empty (errors suppressed) but not raise
        assert records == []

    def test_parse_metrics_computes_stats(self, mock_credential):
        resource_id = "/sub/rg/vm1"
        response = _make_metric_response("Percentage CPU", [2.0, 4.0, 6.0, 8.0, 10.0])
        records = MonitorMetricsConnector._parse_metrics(
            resource_id, response, tenant_id="t1", subscription_id="sub-1"
        )
        assert len(records) == 1
        rec = records[0]
        assert rec["metric_name"] == "Percentage CPU"
        assert rec["avg_value"] == pytest.approx(6.0)
        assert rec["min_value"] == pytest.approx(2.0)
        assert rec["max_value"] == pytest.approx(10.0)
        assert rec["sample_count"] == 5


class TestMonitorMapper:
    def test_is_underutilised_vm_low_cpu(self):
        metrics = [
            {"metric_name": "Percentage CPU", "avg_value": 5.0, "p95_value": 8.0,
             "max_value": 12.0, "min_value": 1.0, "sample_count": 336, "lookback_days": 14},
            {"metric_name": "Available Memory Bytes", "avg_value": 8e9, "p95_value": 10e9,
             "max_value": 12e9, "min_value": 4e9, "sample_count": 336, "lookback_days": 14},
        ]
        result = is_underutilised_vm(metrics)
        assert result["is_low_cpu"] is True
        assert result["cpu_avg_pct"] == 5.0
        assert result["mem_available_avg_gb"] == pytest.approx(8e9 / (1024**3))

    def test_is_underutilised_vm_high_cpu(self):
        metrics = [
            {"metric_name": "Percentage CPU", "avg_value": 75.0, "p95_value": 90.0,
             "max_value": 100.0, "min_value": 40.0, "sample_count": 336, "lookback_days": 14},
        ]
        result = is_underutilised_vm(metrics)
        assert result["is_low_cpu"] is False

    def test_is_underutilised_vm_no_metrics(self):
        result = is_underutilised_vm([])
        assert result["cpu_avg_pct"] is None
        assert result["is_low_cpu"] is False
