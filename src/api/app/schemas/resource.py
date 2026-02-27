import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ResourceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    subscription_db_id: uuid.UUID
    resource_id: str
    name: str
    type: str
    resource_group: str
    location: str
    tags: dict[str, Any] | None = None
    last_seen: datetime

    model_config = {"from_attributes": True}
