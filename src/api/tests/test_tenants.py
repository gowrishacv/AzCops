"""Tests for the /api/v1/tenants endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tenant_payload(
    name: str = "Contoso",
    azure_tenant_id: str | None = None,
    tenant_type: str = "internal",
) -> dict:
    """Return a valid TenantCreate JSON body."""
    return {
        "name": name,
        "azure_tenant_id": azure_tenant_id or str(uuid.uuid4()),
        "type": tenant_type,
    }


async def _create_tenant(client: AsyncClient, **overrides) -> dict:
    """Create a tenant via the API and return the response body."""
    payload = _tenant_payload(**overrides)
    resp = await client.post("/api/v1/tenants", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateTenant:
    """POST /api/v1/tenants"""

    async def test_create_tenant_returns_201(self, async_client: AsyncClient) -> None:
        payload = _tenant_payload()
        response = await async_client.post("/api/v1/tenants", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["azure_tenant_id"] == payload["azure_tenant_id"]
        assert data["type"] == "internal"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_tenant_external_type(self, async_client: AsyncClient) -> None:
        data = await _create_tenant(async_client, tenant_type="external")
        assert data["type"] == "external"

    async def test_duplicate_azure_tenant_id_returns_409(self, async_client: AsyncClient) -> None:
        azure_id = str(uuid.uuid4())
        await _create_tenant(async_client, azure_tenant_id=azure_id)

        # Attempt a second create with the same Azure tenant ID.
        payload = _tenant_payload(name="Duplicate", azure_tenant_id=azure_id)
        response = await async_client.post("/api/v1/tenants", json=payload)
        assert response.status_code == 409


class TestListTenants:
    """GET /api/v1/tenants"""

    async def test_list_tenants_empty(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/v1/tenants")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    async def test_list_tenants_with_data(self, async_client: AsyncClient) -> None:
        await _create_tenant(async_client, name="Tenant A")
        await _create_tenant(async_client, name="Tenant B")

        response = await async_client.get("/api/v1/tenants")
        data = response.json()

        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_tenants_pagination(self, async_client: AsyncClient) -> None:
        for i in range(3):
            await _create_tenant(async_client, name=f"Tenant {i}")

        response = await async_client.get("/api/v1/tenants", params={"page": 1, "page_size": 2})
        data = response.json()

        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 2

    async def test_list_tenants_second_page(self, async_client: AsyncClient) -> None:
        for i in range(3):
            await _create_tenant(async_client, name=f"Tenant {i}")

        response = await async_client.get("/api/v1/tenants", params={"page": 2, "page_size": 2})
        data = response.json()

        assert len(data["items"]) == 1


class TestGetTenant:
    """GET /api/v1/tenants/{tenant_id}"""

    async def test_get_tenant_by_id(self, async_client: AsyncClient) -> None:
        created = await _create_tenant(async_client)
        tenant_id = created["id"]

        response = await async_client.get(f"/api/v1/tenants/{tenant_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == tenant_id
        assert data["name"] == created["name"]

    async def test_get_nonexistent_tenant_returns_404(self, async_client: AsyncClient) -> None:
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/tenants/{fake_id}")
        assert response.status_code == 404


class TestUpdateTenant:
    """PATCH /api/v1/tenants/{tenant_id}"""

    async def test_update_tenant_name(self, async_client: AsyncClient) -> None:
        created = await _create_tenant(async_client)
        tenant_id = created["id"]

        response = await async_client.patch(
            f"/api/v1/tenants/{tenant_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_update_tenant_type(self, async_client: AsyncClient) -> None:
        created = await _create_tenant(async_client, tenant_type="internal")
        tenant_id = created["id"]

        response = await async_client.patch(
            f"/api/v1/tenants/{tenant_id}",
            json={"type": "external"},
        )
        assert response.status_code == 200
        assert response.json()["type"] == "external"

    async def test_update_tenant_is_active(self, async_client: AsyncClient) -> None:
        created = await _create_tenant(async_client)
        tenant_id = created["id"]

        response = await async_client.patch(
            f"/api/v1/tenants/{tenant_id}",
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    async def test_update_nonexistent_tenant_returns_404(self, async_client: AsyncClient) -> None:
        fake_id = str(uuid.uuid4())
        response = await async_client.patch(
            f"/api/v1/tenants/{fake_id}",
            json={"name": "Does Not Matter"},
        )
        assert response.status_code == 404


class TestDeleteTenant:
    """DELETE /api/v1/tenants/{tenant_id}"""

    async def test_delete_tenant_returns_204(self, async_client: AsyncClient) -> None:
        created = await _create_tenant(async_client)
        tenant_id = created["id"]

        response = await async_client.delete(f"/api/v1/tenants/{tenant_id}")
        assert response.status_code == 204

        # Verify it is gone.
        get_response = await async_client.get(f"/api/v1/tenants/{tenant_id}")
        assert get_response.status_code == 404

    async def test_delete_nonexistent_tenant_returns_404(self, async_client: AsyncClient) -> None:
        fake_id = str(uuid.uuid4())
        response = await async_client.delete(f"/api/v1/tenants/{fake_id}")
        assert response.status_code == 404
