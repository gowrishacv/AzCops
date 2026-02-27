from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost import CostDaily
from app.repositories.base import BaseRepository


class CostRepository(BaseRepository[CostDaily]):
    """Repository for CostDaily with date range filtering and aggregations."""

    def __init__(self, session: AsyncSession):
        super().__init__(CostDaily, session)

    async def get_by_date_range(
        self,
        tenant_id: str,
        from_date: date,
        to_date: date,
        offset: int = 0,
        limit: int = 200,
        subscription_db_id: str | None = None,
        service_name: str | None = None,
        resource_group: str | None = None,
    ) -> list[CostDaily]:
        query = (
            select(CostDaily)
            .where(CostDaily.tenant_id == tenant_id)
            .where(CostDaily.date >= from_date)
            .where(CostDaily.date <= to_date)
        )
        if subscription_db_id:
            import uuid
            query = query.where(CostDaily.subscription_db_id == uuid.UUID(subscription_db_id))
        if service_name:
            query = query.where(CostDaily.service_name.ilike(f"%{service_name}%"))
        if resource_group:
            query = query.where(CostDaily.resource_group.ilike(f"%{resource_group}%"))

        query = query.order_by(CostDaily.date.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_by_service(
        self,
        tenant_id: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """Aggregate total cost grouped by service name."""
        query = (
            select(
                CostDaily.service_name,
                func.sum(CostDaily.cost).label("total_cost"),
                func.sum(CostDaily.amortized_cost).label("total_amortized_cost"),
            )
            .where(CostDaily.tenant_id == tenant_id)
            .where(CostDaily.date >= from_date)
            .where(CostDaily.date <= to_date)
            .group_by(CostDaily.service_name)
            .order_by(func.sum(CostDaily.cost).desc())
        )
        result = await self.session.execute(query)
        return [
            {
                "service_name": row.service_name,
                "total_cost": float(row.total_cost or 0),
                "total_amortized_cost": float(row.total_amortized_cost or 0),
            }
            for row in result.all()
        ]

    async def get_daily_trend(
        self,
        tenant_id: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """Return daily total cost for trend charts."""
        query = (
            select(
                CostDaily.date,
                func.sum(CostDaily.cost).label("total_cost"),
                func.sum(CostDaily.amortized_cost).label("total_amortized_cost"),
            )
            .where(CostDaily.tenant_id == tenant_id)
            .where(CostDaily.date >= from_date)
            .where(CostDaily.date <= to_date)
            .group_by(CostDaily.date)
            .order_by(CostDaily.date)
        )
        result = await self.session.execute(query)
        return [
            {
                "date": str(row.date),
                "total_cost": float(row.total_cost or 0),
                "total_amortized_cost": float(row.total_amortized_cost or 0),
            }
            for row in result.all()
        ]
