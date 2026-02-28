import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.subscription import Subscription
from app.repositories.subscription import SubscriptionRepository
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate

logger = get_logger(__name__)


class SubscriptionService:
    """Business logic for subscription management."""

    def __init__(self, session: AsyncSession):
        self.repo = SubscriptionRepository(session)

    async def create_subscription(self, data: SubscriptionCreate, tenant_id: str) -> Subscription:
        """Create a new subscription after validating uniqueness."""
        existing = await self.repo.get_by_subscription_id(data.subscription_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subscription '{data.subscription_id}' already exists",
            )

        subscription = Subscription(
            tenant_db_id=data.tenant_db_id,
            subscription_id=data.subscription_id,
            display_name=data.display_name,
            billing_scope=data.billing_scope,
            tenant_id=tenant_id,
        )
        result = await self.repo.create(subscription)
        logger.info(
            "subscription_created",
            subscription_id=data.subscription_id,
            tenant_id=tenant_id,
        )
        return result

    async def get_subscription(self, id: uuid.UUID, tenant_id: str) -> Subscription:
        """Get a subscription by ID, scoped to tenant."""
        subscription = await self.repo.get_by_id(id, tenant_id=tenant_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )
        return subscription

    async def list_subscriptions(
        self, tenant_id: str, offset: int = 0, limit: int = 50
    ) -> tuple[list[Subscription], int]:
        """List all subscriptions for a tenant with pagination."""
        subscriptions = await self.repo.get_all(tenant_id=tenant_id, offset=offset, limit=limit)
        total = await self.repo.count(tenant_id=tenant_id)
        return subscriptions, total

    async def update_subscription(
        self, id: uuid.UUID, data: SubscriptionUpdate, tenant_id: str
    ) -> Subscription:
        """Update a subscription."""
        subscription = await self.get_subscription(id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return subscription
        result = await self.repo.update(subscription, update_data)
        logger.info("subscription_updated", subscription_id=str(id), tenant_id=tenant_id)
        return result

    async def delete_subscription(self, id: uuid.UUID, tenant_id: str) -> None:
        """Delete a subscription."""
        subscription = await self.get_subscription(id, tenant_id)
        await self.repo.delete(subscription)
        logger.info("subscription_deleted", subscription_id=str(id), tenant_id=tenant_id)
