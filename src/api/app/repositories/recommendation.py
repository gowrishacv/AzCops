from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import (
    Recommendation,
    RecommendationCategory,
    RecommendationStatus,
    RiskLevel,
    VALID_STATUS_TRANSITIONS,
)
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    """Repository for Recommendation CRUD with upsert and status transitions."""

    def __init__(self, session: AsyncSession):
        super().__init__(Recommendation, session)

    async def upsert_from_engine(self, records: list[dict[str, Any]]) -> int:
        """
        Insert or update recommendations from engine results.
        Skips (preserves) records whose status is not 'open'.
        Returns the count of rows inserted/updated.
        """
        if not records:
            return 0

        count = 0
        for rec in records:
            stmt = (
                pg_insert(Recommendation)
                .values(**rec)
                .on_conflict_do_update(
                    # Unique on rule_id + resource_id (Azure) + tenant_id
                    index_elements=["rule_id", "tenant_id"],
                    set_={
                        "title": rec.get("title", ""),
                        "description": rec.get("description", ""),
                        "estimated_monthly_savings": rec.get("estimated_monthly_savings", 0.0),
                        "confidence_score": rec.get("confidence_score", 0.0),
                        "risk_level": rec.get("risk_level"),
                        "effort_level": rec.get("effort_level"),
                        "category": rec.get("category"),
                    },
                    where=(Recommendation.status == RecommendationStatus.OPEN),
                )
            )
            await self.session.execute(stmt)
            count += 1

        await self.session.flush()
        return count

    async def get_by_filters(
        self,
        tenant_id: str,
        *,
        status: RecommendationStatus | None = None,
        category: str | None = None,
        risk_level: str | None = None,
        subscription_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Recommendation]:
        """Fetch recommendations with optional filters."""
        query = select(Recommendation).where(Recommendation.tenant_id == tenant_id)

        if status is not None:
            query = query.where(Recommendation.status == status)
        if category is not None:
            query = query.where(Recommendation.category == category)
        if risk_level is not None:
            query = query.where(Recommendation.risk_level == risk_level)

        query = (
            query.order_by(Recommendation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_filters(
        self,
        tenant_id: str,
        *,
        status: RecommendationStatus | None = None,
        category: str | None = None,
        risk_level: str | None = None,
    ) -> int:
        """Count recommendations matching filters."""
        from sqlalchemy import func
        query = (
            select(func.count())
            .select_from(Recommendation)
            .where(Recommendation.tenant_id == tenant_id)
        )
        if status is not None:
            query = query.where(Recommendation.status == status)
        if category is not None:
            query = query.where(Recommendation.category == category)
        if risk_level is not None:
            query = query.where(Recommendation.risk_level == risk_level)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def transition_status(
        self,
        rec_id: str,
        tenant_id: str,
        new_status: RecommendationStatus,
    ) -> Recommendation | None:
        """
        Validate and apply a status transition.
        Returns the updated recommendation, or None if the transition is invalid
        or the recommendation was not found.
        """
        rec = await self.get_by_id(uuid.UUID(rec_id), tenant_id=tenant_id)
        if rec is None:
            return None

        allowed = VALID_STATUS_TRANSITIONS.get(rec.status, [])
        if new_status not in allowed:
            return None

        rec.status = new_status
        await self.session.flush()
        await self.session.refresh(rec)
        return rec
