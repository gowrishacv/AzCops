import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TenantType(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class Tenant(Base, TimestampMixin):
    """Azure tenant registered in the platform."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    azure_tenant_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[TenantType] = mapped_column(
        Enum(TenantType, name="tenant_type"),
        nullable=False,
        default=TenantType.INTERNAL,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    subscriptions = relationship("Subscription", back_populates="tenant", lazy="selectin")
