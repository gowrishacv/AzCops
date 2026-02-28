import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.repositories.tenant import TenantRepository
from app.schemas.tenant import TenantCreate, TenantUpdate

logger = get_logger(__name__)


class TenantService:
    """Business logic for tenant management."""

    def __init__(self, session: AsyncSession):
        self.repo = TenantRepository(session)

    async def create_tenant(self, data: TenantCreate, tenant_id: str) -> Tenant:
        """Create a new tenant after validating uniqueness."""
        existing = await self.repo.get_by_azure_tenant_id(data.azure_tenant_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tenant with Azure tenant ID '{data.azure_tenant_id}' already exists",
            )

        tenant = Tenant(
            name=data.name,
            azure_tenant_id=data.azure_tenant_id,
            type=data.type,
        )
        # Note: Tenant table doesn't use tenant_id scoping since it IS the tenant
        result = await self.repo.create(tenant)
        logger.info("tenant_created", tenant_name=data.name, azure_tenant_id=data.azure_tenant_id)
        return result

    async def get_tenant(self, id: uuid.UUID) -> Tenant:
        """Get a tenant by ID."""
        tenant = await self.repo.get_by_id(id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        return tenant

    async def list_tenants(self, offset: int = 0, limit: int = 50) -> tuple[list[Tenant], int]:
        """List all tenants with pagination."""
        tenants = await self.repo.get_all(offset=offset, limit=limit)
        total = await self.repo.count()
        return tenants, total

    async def update_tenant(self, id: uuid.UUID, data: TenantUpdate) -> Tenant:
        """Update a tenant."""
        tenant = await self.get_tenant(id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return tenant
        result = await self.repo.update(tenant, update_data)
        logger.info("tenant_updated", tenant_id=str(id))
        return result

    async def delete_tenant(self, id: uuid.UUID) -> None:
        """Delete a tenant."""
        tenant = await self.get_tenant(id)
        await self.repo.delete(tenant)
        logger.info("tenant_deleted", tenant_id=str(id))
