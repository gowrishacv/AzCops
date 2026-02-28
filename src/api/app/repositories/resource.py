from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource import Resource
from app.repositories.base import BaseRepository


class ResourceRepository(BaseRepository[Resource]):
    """Repository for Resource queries with filtering and pagination."""

    def __init__(self, session: AsyncSession):
        super().__init__(Resource, session)

    async def get_by_filters(
        self,
        tenant_id: str,
        offset: int = 0,
        limit: int = 50,
        resource_type: str | None = None,
        location: str | None = None,
        resource_group: str | None = None,
        subscription_db_id: str | None = None,
    ) -> list[Resource]:
        query = select(Resource).where(Resource.tenant_id == tenant_id)

        if resource_type:
            query = query.where(Resource.type.ilike(f"%{resource_type}%"))
        if location:
            query = query.where(Resource.location == location.lower())
        if resource_group:
            query = query.where(Resource.resource_group == resource_group.lower())
        if subscription_db_id:
            from sqlalchemy import cast
            from sqlalchemy.dialects.postgresql import UUID
            import uuid
            query = query.where(Resource.subscription_db_id == uuid.UUID(subscription_db_id))

        query = query.order_by(Resource.type, Resource.name).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_filters(
        self,
        tenant_id: str,
        resource_type: str | None = None,
        location: str | None = None,
        resource_group: str | None = None,
        subscription_db_id: str | None = None,
    ) -> int:
        from sqlalchemy import func
        query = select(func.count()).select_from(Resource).where(Resource.tenant_id == tenant_id)
        if resource_type:
            query = query.where(Resource.type.ilike(f"%{resource_type}%"))
        if location:
            query = query.where(Resource.location == location.lower())
        if resource_group:
            query = query.where(Resource.resource_group == resource_group.lower())
        if subscription_db_id:
            import uuid
            query = query.where(Resource.subscription_db_id == uuid.UUID(subscription_db_id))
        result = await self.session.execute(query)
        return result.scalar_one()
