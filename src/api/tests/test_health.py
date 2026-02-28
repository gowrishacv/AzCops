"""Tests for the /health endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Verify the health-check route returns the expected payload."""

    async def test_health_returns_200(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        assert response.status_code == 200

    async def test_health_response_has_required_fields(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "database" in data

    async def test_health_status_is_healthy(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    async def test_health_version_matches_app(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        data = response.json()

        assert data["version"] == "0.1.0"
