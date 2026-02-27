from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.recommendation import (
    EffortLevel,
    RecommendationCategory,
    RecommendationStatus,
    RiskLevel,
)


class RecommendationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    rule_id: str
    category: RecommendationCategory
    estimated_monthly_savings: float
    confidence_score: float
    risk_level: RiskLevel
    effort_level: EffortLevel
    status: RecommendationStatus
    short_description: str  # maps to title in the DB model
    detail: str | None      # maps to description in the DB model
    resource_id: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_recommendation(cls, rec: object) -> "RecommendationResponse":
        """Build response from ORM Recommendation model."""
        return cls(
            id=rec.id,  # type: ignore[attr-defined]
            tenant_id=rec.tenant_id,  # type: ignore[attr-defined]
            rule_id=rec.rule_id,  # type: ignore[attr-defined]
            category=rec.category,  # type: ignore[attr-defined]
            estimated_monthly_savings=float(rec.estimated_monthly_savings),  # type: ignore[attr-defined]
            confidence_score=float(rec.confidence_score),  # type: ignore[attr-defined]
            risk_level=rec.risk_level,  # type: ignore[attr-defined]
            effort_level=rec.effort_level,  # type: ignore[attr-defined]
            status=rec.status,  # type: ignore[attr-defined]
            short_description=rec.title,  # type: ignore[attr-defined]
            detail=rec.description,  # type: ignore[attr-defined]
            resource_id=None,  # resource_db_id is a UUID FK; resolve separately if needed
            created_at=rec.created_at,  # type: ignore[attr-defined]
            updated_at=rec.updated_at,  # type: ignore[attr-defined]
        )


class RecommendationStatusUpdate(BaseModel):
    reason: str | None = None


class GenerateRequest(BaseModel):
    subscription_id: str
    subscription_db_id: str
    vm_metrics: dict | None = None
    compute_cost_30d: float = 0.0
