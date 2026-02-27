"""Tests for SQLAlchemy models, enum values, and status transition rules."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantType
from app.models.subscription import Subscription
from app.models.recommendation import (
    EffortLevel,
    RecommendationCategory,
    RecommendationStatus,
    RiskLevel,
    VALID_STATUS_TRANSITIONS,
)


# ---------------------------------------------------------------------------
# TenantType enum
# ---------------------------------------------------------------------------


class TestTenantTypeEnum:
    """Verify TenantType enum members and their string values."""

    def test_internal_value(self) -> None:
        assert TenantType.INTERNAL.value == "internal"

    def test_external_value(self) -> None:
        assert TenantType.EXTERNAL.value == "external"

    def test_enum_members(self) -> None:
        members = {m.value for m in TenantType}
        assert members == {"internal", "external"}


# ---------------------------------------------------------------------------
# Tenant model
# ---------------------------------------------------------------------------


class TestTenantModel:
    """Verify Tenant ORM creation and persistence."""

    async def test_create_tenant(self, db_session: AsyncSession) -> None:
        tenant = Tenant(
            name="Contoso",
            azure_tenant_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            type=TenantType.INTERNAL,
        )
        db_session.add(tenant)
        await db_session.flush()
        await db_session.refresh(tenant)

        assert tenant.id is not None
        assert isinstance(tenant.id, uuid.UUID)
        assert tenant.name == "Contoso"
        assert tenant.azure_tenant_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        assert tenant.type == TenantType.INTERNAL
        assert tenant.is_active is True

    async def test_tenant_defaults(self, db_session: AsyncSession) -> None:
        """Default type should be INTERNAL and is_active should be True."""
        tenant = Tenant(
            name="Defaults",
            azure_tenant_id="11111111-2222-3333-4444-555555555555",
        )
        db_session.add(tenant)
        await db_session.flush()
        await db_session.refresh(tenant)

        assert tenant.type == TenantType.INTERNAL
        assert tenant.is_active is True

    async def test_tenant_has_timestamps(self, db_session: AsyncSession) -> None:
        tenant = Tenant(
            name="Timestamps",
            azure_tenant_id="eeeeeeee-ffff-0000-1111-222222222222",
        )
        db_session.add(tenant)
        await db_session.flush()
        await db_session.refresh(tenant)

        assert tenant.created_at is not None
        assert tenant.updated_at is not None

    async def test_tenant_tablename(self) -> None:
        assert Tenant.__tablename__ == "tenants"


# ---------------------------------------------------------------------------
# Subscription model
# ---------------------------------------------------------------------------


class TestSubscriptionModel:
    """Verify Subscription ORM creation and persistence."""

    async def test_create_subscription(self, db_session: AsyncSession) -> None:
        # First create a parent tenant.
        tenant = Tenant(
            name="Parent",
            azure_tenant_id="99999999-8888-7777-6666-555555555555",
        )
        db_session.add(tenant)
        await db_session.flush()
        await db_session.refresh(tenant)

        sub = Subscription(
            tenant_db_id=tenant.id,
            subscription_id="sub-001",
            display_name="Dev Subscription",
            tenant_id="test-tenant",
        )
        db_session.add(sub)
        await db_session.flush()
        await db_session.refresh(sub)

        assert sub.id is not None
        assert isinstance(sub.id, uuid.UUID)
        assert sub.tenant_db_id == tenant.id
        assert sub.subscription_id == "sub-001"
        assert sub.display_name == "Dev Subscription"
        assert sub.is_active is True
        assert sub.billing_scope is None
        assert sub.tenant_id == "test-tenant"

    async def test_subscription_has_timestamps(self, db_session: AsyncSession) -> None:
        tenant = Tenant(
            name="TS Tenant",
            azure_tenant_id="aaaaaaaa-1111-2222-3333-444444444444",
        )
        db_session.add(tenant)
        await db_session.flush()
        await db_session.refresh(tenant)

        sub = Subscription(
            tenant_db_id=tenant.id,
            subscription_id="sub-ts",
            display_name="Timestamp Sub",
            tenant_id="test-tenant",
        )
        db_session.add(sub)
        await db_session.flush()
        await db_session.refresh(sub)

        assert sub.created_at is not None
        assert sub.updated_at is not None

    async def test_subscription_tablename(self) -> None:
        assert Subscription.__tablename__ == "subscriptions"


# ---------------------------------------------------------------------------
# RecommendationStatus enum
# ---------------------------------------------------------------------------


class TestRecommendationStatusEnum:
    """Verify RecommendationStatus enum members."""

    def test_all_status_values(self) -> None:
        expected = {"open", "approved", "rejected", "executed", "dismissed"}
        actual = {s.value for s in RecommendationStatus}
        assert actual == expected

    def test_open_value(self) -> None:
        assert RecommendationStatus.OPEN.value == "open"

    def test_approved_value(self) -> None:
        assert RecommendationStatus.APPROVED.value == "approved"

    def test_rejected_value(self) -> None:
        assert RecommendationStatus.REJECTED.value == "rejected"

    def test_executed_value(self) -> None:
        assert RecommendationStatus.EXECUTED.value == "executed"

    def test_dismissed_value(self) -> None:
        assert RecommendationStatus.DISMISSED.value == "dismissed"


# ---------------------------------------------------------------------------
# Other enums
# ---------------------------------------------------------------------------


class TestRiskLevelEnum:
    def test_values(self) -> None:
        assert {r.value for r in RiskLevel} == {"low", "medium", "high"}


class TestEffortLevelEnum:
    def test_values(self) -> None:
        assert {e.value for e in EffortLevel} == {"low", "medium", "high"}


class TestRecommendationCategoryEnum:
    def test_values(self) -> None:
        expected = {"waste_detection", "right_sizing", "rate_optimization", "governance"}
        assert {c.value for c in RecommendationCategory} == expected


# ---------------------------------------------------------------------------
# VALID_STATUS_TRANSITIONS
# ---------------------------------------------------------------------------


class TestValidStatusTransitions:
    """Ensure the state machine transitions are exactly as specified."""

    def test_open_transitions(self) -> None:
        expected = {
            RecommendationStatus.APPROVED,
            RecommendationStatus.REJECTED,
            RecommendationStatus.DISMISSED,
        }
        assert set(VALID_STATUS_TRANSITIONS[RecommendationStatus.OPEN]) == expected

    def test_approved_transitions(self) -> None:
        expected = {
            RecommendationStatus.EXECUTED,
            RecommendationStatus.REJECTED,
        }
        assert set(VALID_STATUS_TRANSITIONS[RecommendationStatus.APPROVED]) == expected

    def test_rejected_transitions(self) -> None:
        expected = {RecommendationStatus.OPEN}
        assert set(VALID_STATUS_TRANSITIONS[RecommendationStatus.REJECTED]) == expected

    def test_executed_is_terminal(self) -> None:
        assert VALID_STATUS_TRANSITIONS[RecommendationStatus.EXECUTED] == []

    def test_dismissed_transitions(self) -> None:
        expected = {RecommendationStatus.OPEN}
        assert set(VALID_STATUS_TRANSITIONS[RecommendationStatus.DISMISSED]) == expected

    def test_all_statuses_have_transition_entry(self) -> None:
        """Every status must appear as a key in the transitions map."""
        for status in RecommendationStatus:
            assert status in VALID_STATUS_TRANSITIONS, (
                f"{status} missing from VALID_STATUS_TRANSITIONS"
            )

    def test_no_self_transitions(self) -> None:
        """A status should never transition to itself."""
        for source, targets in VALID_STATUS_TRANSITIONS.items():
            assert source not in targets, f"{source} has a self-transition"

    def test_executed_cannot_be_reached_from_open_directly(self) -> None:
        """OPEN should NOT directly transition to EXECUTED."""
        assert RecommendationStatus.EXECUTED not in VALID_STATUS_TRANSITIONS[
            RecommendationStatus.OPEN
        ]
