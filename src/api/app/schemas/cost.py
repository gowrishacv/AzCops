import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class CostDailyResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    subscription_db_id: uuid.UUID
    date: date
    service_name: str
    resource_group: str
    meter_category: str | None = None
    cost: float
    amortized_cost: float
    currency: str

    model_config = {"from_attributes": True}


class CostByServiceResponse(BaseModel):
    service_name: str
    total_cost: float
    total_amortized_cost: float


class CostTrendResponse(BaseModel):
    date: str
    total_cost: float
    total_amortized_cost: float


class CostSummaryResponse(BaseModel):
    from_date: date
    to_date: date
    total_cost: float
    total_amortized_cost: float
    by_service: list[CostByServiceResponse]
    daily_trend: list[CostTrendResponse]
