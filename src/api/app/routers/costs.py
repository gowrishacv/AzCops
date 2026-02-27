from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.core.dependencies import AuthenticatedUser, DbSession, TenantId
from app.repositories.cost import CostRepository
from app.schemas.cost import CostSummaryResponse, CostDailyResponse
from app.schemas.common import PaginatedResponse
from math import ceil

router = APIRouter(prefix="/costs", tags=["Costs"])


@router.get("/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
) -> CostSummaryResponse:
    """
    Return cost summary with by-service breakdown and daily trend
    for the specified date range (defaults to last 30 days).
    """
    if to_date is None:
        to_date = date.today() - timedelta(days=1)
    if from_date is None:
        from_date = to_date - timedelta(days=29)

    repo = CostRepository(session)
    by_service = await repo.get_total_by_service(tenant_id, from_date, to_date)
    daily_trend = await repo.get_daily_trend(tenant_id, from_date, to_date)

    total_cost = sum(s["total_cost"] for s in by_service)
    total_amortized = sum(s["total_amortized_cost"] for s in by_service)

    return CostSummaryResponse(
        from_date=from_date,
        to_date=to_date,
        total_cost=round(total_cost, 2),
        total_amortized_cost=round(total_amortized, 2),
        by_service=by_service,
        daily_trend=daily_trend,
    )


@router.get("", response_model=PaginatedResponse[CostDailyResponse])
async def list_costs(
    session: DbSession,
    user: AuthenticatedUser,
    tenant_id: TenantId,
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    subscription_id: str | None = Query(default=None),
    service_name: str | None = Query(default=None),
    resource_group: str | None = Query(default=None),
) -> PaginatedResponse[CostDailyResponse]:
    """List raw daily cost records with filtering and pagination."""
    if to_date is None:
        to_date = date.today() - timedelta(days=1)
    if from_date is None:
        from_date = to_date - timedelta(days=29)

    repo = CostRepository(session)
    offset = (page - 1) * page_size
    records = await repo.get_by_date_range(
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=page_size,
        subscription_db_id=subscription_id,
        service_name=service_name,
        resource_group=resource_group,
    )
    total = await repo.count(tenant_id=tenant_id)
    return PaginatedResponse(
        items=[CostDailyResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )
