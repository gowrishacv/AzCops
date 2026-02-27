import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    """Schema for creating a new subscription."""

    tenant_db_id: uuid.UUID
    subscription_id: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    billing_scope: str | None = None


class SubscriptionUpdate(BaseModel):
    """Schema for updating an existing subscription."""

    display_name: str | None = Field(None, min_length=1, max_length=255)
    billing_scope: str | None = None
    is_active: bool | None = None


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""

    id: uuid.UUID
    tenant_db_id: uuid.UUID
    tenant_id: str
    subscription_id: str
    display_name: str
    billing_scope: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
