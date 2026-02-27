import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScopedMixin, TimestampMixin


class CostDaily(Base, TenantScopedMixin, TimestampMixin):
    """Daily cost data ingested from Azure Cost Management API."""

    __tablename__ = "costs_daily"
    __table_args__ = (
        Index("ix_costs_daily_sub_date", "subscription_db_id", "date"),
        Index("ix_costs_daily_date", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    subscription_db_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_group: Mapped[str] = mapped_column(String(255), nullable=False)
    meter_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    amortized_cost: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
