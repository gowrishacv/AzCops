"""Rule engine runner – orchestrates evaluation and persistence."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.base import Rule, RuleResult
from app.engine.rules import ALL_RULES
from app.models.recommendation import (
    EffortLevel,
    RecommendationCategory,
    RecommendationStatus,
    Recommendation,
    RiskLevel,
)

logger = structlog.get_logger(__name__)


class RuleEngine:
    """Discovers, executes, and persists cost-optimisation rules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._rules: list[Rule] = []
        self._register_all_rules()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def _register_all_rules(self) -> None:
        """Instantiate every known rule class and store them for execution."""
        for rule_cls in ALL_RULES:
            self._rules.append(rule_cls())
        logger.info(
            "rule_engine.rules_registered",
            count=len(self._rules),
            rule_ids=[r.rule_id for r in self._rules],
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(self, tenant_id: str) -> list[RuleResult]:
        """Evaluate every registered rule and return aggregated results.

        Individual rule failures are logged but do **not** abort the run.
        """
        all_results: list[RuleResult] = []

        for rule in self._rules:
            try:
                results = await rule.evaluate(self._session, tenant_id)
                all_results.extend(results)
                logger.info(
                    "rule_engine.rule_completed",
                    rule_id=rule.rule_id,
                    findings=len(results),
                    tenant_id=tenant_id,
                )
            except Exception:
                logger.warning(
                    "rule_engine.rule_failed",
                    rule_id=rule.rule_id,
                    tenant_id=tenant_id,
                    exc_info=True,
                )

        logger.info(
            "rule_engine.run_completed",
            tenant_id=tenant_id,
            total_findings=len(all_results),
        )
        return all_results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def run_and_persist(self, tenant_id: str) -> int:
        """Run all rules, deduplicate against existing open recommendations,
        persist new ones, and return the count of newly created records.
        """
        results = await self.run(tenant_id)

        if not results:
            return 0

        # Fetch existing open recommendations for this tenant so we can
        # de-duplicate on (rule_id, resource_db_id).
        existing_stmt = select(
            Recommendation.rule_id, Recommendation.resource_db_id
        ).where(
            Recommendation.tenant_id == tenant_id,
            Recommendation.status == RecommendationStatus.OPEN,
        )
        rows = await self._session.execute(existing_stmt)
        existing_keys: set[tuple[str, str | None]] = {
            (row.rule_id, str(row.resource_db_id) if row.resource_db_id else None)
            for row in rows
        }

        new_count = 0
        for result in results:
            dedup_key = (result.rule_id, result.resource_db_id)
            if dedup_key in existing_keys:
                continue

            rec = Recommendation(
                tenant_id=tenant_id,
                resource_db_id=result.resource_db_id,
                rule_id=result.rule_id,
                category=RecommendationCategory(result.category),
                title=result.title,
                description=result.description,
                estimated_monthly_savings=result.estimated_monthly_savings,
                confidence_score=result.confidence_score,
                risk_level=RiskLevel(result.risk_level),
                effort_level=EffortLevel(result.effort_level),
                status=RecommendationStatus.OPEN,
            )
            self._session.add(rec)
            existing_keys.add(dedup_key)
            new_count += 1

        await self._session.flush()

        logger.info(
            "rule_engine.persist_completed",
            tenant_id=tenant_id,
            new_recommendations=new_count,
            duplicates_skipped=len(results) - new_count,
        )
        return new_count
