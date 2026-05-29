from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import BillingPeriod, Plan, SubscriptionSource, SubscriptionStatus


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan: Mapped[Plan] = mapped_column(
        Enum(Plan, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
    )
    billing_period: Mapped[BillingPeriod] = mapped_column(
        Enum(BillingPeriod, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=BillingPeriod.MANUAL,
        server_default=BillingPeriod.MANUAL.value,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(
            SubscriptionStatus,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        default=SubscriptionStatus.ACTIVE,
        server_default=SubscriptionStatus.ACTIVE.value,
    )
    source: Mapped[SubscriptionSource] = mapped_column(
        Enum(
            SubscriptionSource,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        default=SubscriptionSource.MANUAL,
        server_default=SubscriptionSource.MANUAL.value,
    )
    payment_invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("payment_invoices.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
