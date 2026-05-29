from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import (
    PaymentInvoiceStatus,
    PaymentMethod,
    PaymentPlan,
    PaymentProviderCode,
)


class PaymentInvoice(Base):
    __tablename__ = "payment_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[PaymentProviderCode] = mapped_column(
        Enum(
            PaymentProviderCode,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
    )
    plan: Mapped[PaymentPlan] = mapped_column(
        Enum(PaymentPlan, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[PaymentInvoiceStatus] = mapped_column(
        Enum(
            PaymentInvoiceStatus,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        default=PaymentInvoiceStatus.PENDING,
        server_default=PaymentInvoiceStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    provider_invoice_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255))
    payment_url: Mapped[str | None] = mapped_column(String(2048))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    invoice_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
