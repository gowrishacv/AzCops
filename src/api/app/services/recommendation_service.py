from __future__ import annotations

import sys
import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import (
    Recommendation,
    RecommendationCategory,
    RecommendationStatus,
)
from app.repositories.recommendation import RecommendationRepository
from app.repositories.resource import ResourceRepository

# The engine lives outside the API package — add src root to path if needed
_WORKTREE_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _WORKTREE_ROOT not in sys.path:
    sys.path.insert(0, _WORKTREE_ROOT)

from src.engine.engine import run_engine  # noqa: E402
from src.engine.rules.base import RuleCategory  # noqa: E402


def _map_rule_category(rule_cat: RuleCategory) -> RecommendationCategory:
    """Map engine RuleCategory to DB RecommendationCategory."""
    mapping = {
        RuleCategory.WASTE: RecommendationCategory.WASTE_DETECTION,
        RuleCategory.RIGHTSIZING: RecommendationCategory.RIGHT_SIZING,
        RuleCategory.RATE_OPTIMIZATION: RecommendationCategory.RATE_OPTIMIZATION,
        RuleCategory.GOVERNANCE: RecommendationCategory.GOVERNANCE,
    }
    return mapping.get(rule_cat, RecommendationCategory.WASTE_DETECTION)


class RecommendationService:
    """Orchestrates rule engine execution and recommendation persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._resource_repo = ResourceRepository(db)
        self._rec_repo = RecommendationRepository(db)

    async def generate_for_subscription(
        self,
        tenant_id: str,
        subscription_db_id: str,
        subscription_id: str,
        vm_metrics: dict | None = None,
        compute_cost_30d: float = 0.0,
    ) -> int:
        """
        Fetch resources, run the rule engine, and upsert recommendations.
        Returns count of recommendations upserted.
        """
        # Fetch all resources for this subscription (paginate if large)
        resources_orm = await self._resource_repo.get_by_filters(
            tenant_id=tenant_id,
            subscription_db_id=subscription_db_id,
            limit=1000,
        )

        # Convert ORM objects to plain dicts for the rule engine
        resources: list[dict[str, Any]] = []
        for r in resources_orm:
            resources.append(
                {
                    "resource_id": r.resource_id,
                    "type": r.type,
                    "name": r.name,
                    "resource_group": r.resource_group,
                    "location": r.location,
                    "tags": r.tags or {},
                    "properties": r.properties or {},
                    "metadata": {},
                }
            )

        if not resources:
            return 0

        context: dict[str, Any] = {
            "tenant_id": tenant_id,
            "subscription_id": subscription_id,
            "vm_metrics": vm_metrics or {},
            "compute_cost_30d": compute_cost_30d,
        }

        engine_result = run_engine(resources, context)

        # Build records for upsert
        records: list[dict[str, Any]] = []
        for scored in engine_result.scored_results:
            r = scored.result
            records.append(
                {
                    "tenant_id": tenant_id,
                    "rule_id": r.rule_id,
                    "category": _map_rule_category(r.category),
                    "title": r.short_description,
                    "description": r.detail,
                    "estimated_monthly_savings": r.estimated_monthly_savings,
                    "confidence_score": r.confidence_score,
                    "risk_level": r.risk_level.value,
                    "effort_level": r.effort_level.value,
                    "status": RecommendationStatus.OPEN,
                }
            )

        return await self._rec_repo.upsert_from_engine(records)
