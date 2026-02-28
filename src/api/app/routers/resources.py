from math import ceil

from fastapi import APIRouter, Query

from app.core.dependencies import AuthenticatedUser, DbSession, TenantId
from app.repositories.resource import ResourceRepository
from app.schemas.common import PaginatedResponse
from app.schemas.resource import ResourceResponse

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("", response_model=PaginatedResponse[ResourceResponse])
async def list_resources(
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    type: str | None = Query(default=None, description="Filter by resource type (partial match)"),
    location: str | None = Query(default=None),
    resource_group: str | None = Query(default=None),
    subscription_id: str | None = Query(default=None, description="Filter by subscription DB UUID"),
) -> PaginatedResponse[ResourceResponse]:
    """
    List all discovered Azure resources for the current tenant.
    Supports filtering by type, location, resource_group, and subscription.
    """
    repo = ResourceRepository(session)
    offset = (page - 1) * page_size
    resources = await repo.get_by_filters(
        tenant_id=tenant_id,
        offset=offset,
        limit=page_size,
        resource_type=type,
        location=location,
        resource_group=resource_group,
        subscription_db_id=subscription_id,
    )
    total = await repo.count_by_filters(
        tenant_id=tenant_id,
        resource_type=type,
        location=location,
        resource_group=resource_group,
        subscription_db_id=subscription_id,
    )
    return PaginatedResponse(
        items=[ResourceResponse.model_validate(r) for r in resources],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )
