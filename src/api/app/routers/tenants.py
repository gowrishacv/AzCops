import uuid
from math import ceil

from fastapi import APIRouter, Query

from app.core.dependencies import AuthenticatedUser, DbSession, TenantId
from app.schemas.common import PaginatedResponse
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    data: TenantCreate,
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
) -> TenantResponse:
    """Register a new Azure tenant in the platform."""
    service = TenantService(session)
    tenant = await service.create_tenant(data, tenant_id)
    return TenantResponse.model_validate(tenant)


@router.get("", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    session: DbSession,
    user: AuthenticatedUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedResponse[TenantResponse]:
    """List all registered tenants with pagination."""
    service = TenantService(session)
    offset = (page - 1) * page_size
    tenants, total = await service.list_tenants(offset=offset, limit=page_size)
    return PaginatedResponse(
        items=[TenantResponse.model_validate(t) for t in tenants],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    session: DbSession,
    user: AuthenticatedUser,
) -> TenantResponse:
    """Get a specific tenant by ID."""
    service = TenantService(session)
    tenant = await service.get_tenant(tenant_id)
    return TenantResponse.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    data: TenantUpdate,
    session: DbSession,
    user: AuthenticatedUser,
) -> TenantResponse:
    """Update a tenant's details."""
    service = TenantService(session)
    tenant = await service.update_tenant(tenant_id, data)
    return TenantResponse.model_validate(tenant)


@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(
    tenant_id: uuid.UUID,
    session: DbSession,
    user: AuthenticatedUser,
) -> None:
    """Delete a tenant."""
    service = TenantService(session)
    await service.delete_tenant(tenant_id)
