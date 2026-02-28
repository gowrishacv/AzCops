import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.tenant import TenantType


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    azure_tenant_id: str = Field(..., min_length=1, max_length=255)
    type: TenantType = TenantType.INTERNAL


class TenantUpdate(BaseModel):
    """Schema for updating an existing tenant."""

    name: str | None = Field(None, min_length=1, max_length=255)
    type: TenantType | None = None
    is_active: bool | None = None


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    id: uuid.UUID
    name: str
    azure_tenant_id: str
    type: TenantType
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
