import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for Subscription operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Subscription, session)

    async def get_by_subscription_id(self, subscription_id: str) -> Subscription | None:
        """Find a subscription by its Azure subscription ID."""
        query = select(Subscription).where(Subscription.subscription_id == subscription_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self, tenant_db_id: uuid.UUID, tenant_id: str, offset: int = 0, limit: int = 50
    ) -> list[Subscription]:
        """Get all subscriptions for a specific tenant."""
        query = (
            select(Subscription)
            .where(Subscription.tenant_db_id == tenant_db_id)
            .where(Subscription.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
