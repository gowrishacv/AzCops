import uuid
from math import ceil

from fastapi import APIRouter, Query

from app.core.dependencies import AuthenticatedUser, DbSession, TenantId
from app.schemas.common import PaginatedResponse
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse, SubscriptionUpdate
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post("", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    data: SubscriptionCreate,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> SubscriptionResponse:
    """Register a new Azure subscription."""
    service = SubscriptionService(session)
    subscription = await service.create_subscription(data, tenant_id)
    return SubscriptionResponse.model_validate(subscription)


@router.get("", response_model=PaginatedResponse[SubscriptionResponse])
async def list_subscriptions(
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedResponse[SubscriptionResponse]:
    """List all subscriptions for the current tenant."""
    service = SubscriptionService(session)
    offset = (page - 1) * page_size
    subscriptions, total = await service.list_subscriptions(
        tenant_id=tenant_id, offset=offset, limit=page_size
    )
    return PaginatedResponse(
        items=[SubscriptionResponse.model_validate(s) for s in subscriptions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: uuid.UUID,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> SubscriptionResponse:
    """Get a specific subscription by ID."""
    service = SubscriptionService(session)
    subscription = await service.get_subscription(subscription_id, tenant_id)
    return SubscriptionResponse.model_validate(subscription)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: uuid.UUID,
    data: SubscriptionUpdate,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> SubscriptionResponse:
    """Update a subscription's details."""
    service = SubscriptionService(session)
    subscription = await service.update_subscription(subscription_id, data, tenant_id)
    return SubscriptionResponse.model_validate(subscription)


@router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: uuid.UUID,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> None:
    """Delete a subscription."""
    service = SubscriptionService(session)
    await service.delete_subscription(subscription_id, tenant_id)
