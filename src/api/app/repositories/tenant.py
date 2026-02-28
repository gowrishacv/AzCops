from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """Repository for Tenant operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Tenant, session)

    async def get_by_azure_tenant_id(self, azure_tenant_id: str) -> Tenant | None:
        """Find a tenant by its Azure tenant ID."""
        query = select(Tenant).where(Tenant.azure_tenant_id == azure_tenant_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
