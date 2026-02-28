"""Tests for the /api/v1/subscriptions endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_tenant(client: AsyncClient, name: str = "Sub-Test Tenant") -> dict:
    """Create a tenant via the API and return the response body."""
    payload = {
        "name": name,
        "azure_tenant_id": str(uuid.uuid4()),
        "type": "internal",
    }
    resp = await client.post("/api/v1/tenants", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _subscription_payload(
    tenant_db_id: str,
    subscription_id: str | None = None,
    display_name: str = "Dev Subscription",
    billing_scope: str | None = None,
) -> dict:
    """Return a valid SubscriptionCreate JSON body."""
    return {
        "tenant_db_id": tenant_db_id,
        "subscription_id": subscription_id or str(uuid.uuid4()),
        "display_name": display_name,
        "billing_scope": billing_scope,
    }


async def _create_subscription(client: AsyncClient, tenant_db_id: str, **overrides) -> dict:
    """Create a subscription via the API and return the response body."""
    payload = _subscription_payload(tenant_db_id=tenant_db_id, **overrides)
    resp = await client.post("/api/v1/subscriptions", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateSubscription:
    """POST /api/v1/subscriptions"""

    async def test_create_subscription_returns_201(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        payload = _subscription_payload(tenant_db_id=tenant["id"])

        response = await async_client.post("/api/v1/subscriptions", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["subscription_id"] == payload["subscription_id"]
        assert data["display_name"] == "Dev Subscription"
        assert data["tenant_db_id"] == tenant["id"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_subscription_with_billing_scope(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        data = await _create_subscription(
            async_client,
            tenant_db_id=tenant["id"],
            billing_scope="/providers/Microsoft.Billing/billingAccounts/12345",
        )
        assert data["billing_scope"] == "/providers/Microsoft.Billing/billingAccounts/12345"

    async def test_duplicate_subscription_id_returns_409(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        sub_id = str(uuid.uuid4())

        await _create_subscription(async_client, tenant_db_id=tenant["id"], subscription_id=sub_id)

        # Attempt to create another subscription with the same Azure subscription ID.
        payload = _subscription_payload(tenant_db_id=tenant["id"], subscription_id=sub_id)
        response = await async_client.post("/api/v1/subscriptions", json=payload)
        assert response.status_code == 409

    async def test_create_subscription_sets_tenant_id_from_auth(
        self, async_client: AsyncClient
    ) -> None:
        """The tenant_id field should be set from the authenticated user context."""
        tenant = await _create_tenant(async_client)
        data = await _create_subscription(async_client, tenant_db_id=tenant["id"])

        # The conftest mock user has tenant_id="test-tenant"
        assert data["tenant_id"] == "test-tenant"


class TestListSubscriptions:
    """GET /api/v1/subscriptions"""

    async def test_list_subscriptions_empty(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/v1/subscriptions")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_subscriptions_with_data(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        await _create_subscription(async_client, tenant_db_id=tenant["id"], display_name="Sub A")
        await _create_subscription(async_client, tenant_db_id=tenant["id"], display_name="Sub B")

        response = await async_client.get("/api/v1/subscriptions")
        data = response.json()

        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_subscriptions_pagination(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        for i in range(3):
            await _create_subscription(
                async_client, tenant_db_id=tenant["id"], display_name=f"Sub {i}"
            )

        response = await async_client.get(
            "/api/v1/subscriptions", params={"page": 1, "page_size": 2}
        )
        data = response.json()

        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 2


class TestGetSubscription:
    """GET /api/v1/subscriptions/{subscription_id}"""

    async def test_get_subscription_by_id(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        created = await _create_subscription(async_client, tenant_db_id=tenant["id"])

        response = await async_client.get(f"/api/v1/subscriptions/{created['id']}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == created["id"]
        assert data["subscription_id"] == created["subscription_id"]

    async def test_get_nonexistent_subscription_returns_404(
        self, async_client: AsyncClient
    ) -> None:
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/subscriptions/{fake_id}")
        assert response.status_code == 404


class TestUpdateSubscription:
    """PATCH /api/v1/subscriptions/{subscription_id}"""

    async def test_update_display_name(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        created = await _create_subscription(async_client, tenant_db_id=tenant["id"])

        response = await async_client.patch(
            f"/api/v1/subscriptions/{created['id']}",
            json={"display_name": "Renamed Subscription"},
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Renamed Subscription"

    async def test_update_billing_scope(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        created = await _create_subscription(async_client, tenant_db_id=tenant["id"])

        response = await async_client.patch(
            f"/api/v1/subscriptions/{created['id']}",
            json={"billing_scope": "/new/scope"},
        )
        assert response.status_code == 200
        assert response.json()["billing_scope"] == "/new/scope"

    async def test_update_is_active(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        created = await _create_subscription(async_client, tenant_db_id=tenant["id"])

        response = await async_client.patch(
            f"/api/v1/subscriptions/{created['id']}",
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    async def test_update_nonexistent_subscription_returns_404(
        self, async_client: AsyncClient
    ) -> None:
        fake_id = str(uuid.uuid4())
        response = await async_client.patch(
            f"/api/v1/subscriptions/{fake_id}",
            json={"display_name": "Nope"},
        )
        assert response.status_code == 404


class TestDeleteSubscription:
    """DELETE /api/v1/subscriptions/{subscription_id}"""

    async def test_delete_subscription_returns_204(self, async_client: AsyncClient) -> None:
        tenant = await _create_tenant(async_client)
        created = await _create_subscription(async_client, tenant_db_id=tenant["id"])

        response = await async_client.delete(f"/api/v1/subscriptions/{created['id']}")
        assert response.status_code == 204

        # Verify it is gone.
        get_resp = await async_client.get(f"/api/v1/subscriptions/{created['id']}")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent_subscription_returns_404(
        self, async_client: AsyncClient
    ) -> None:
        fake_id = str(uuid.uuid4())
        response = await async_client.delete(f"/api/v1/subscriptions/{fake_id}")
        assert response.status_code == 404
